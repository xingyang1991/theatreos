// ============================================
// TheatreOS 倒计时与时间同步 Hook
// ============================================

import { useState, useEffect, useCallback, useRef } from 'react';
import { differenceInSeconds, addMinutes, format } from 'date-fns';
import type { SlotPhase } from '@/types';

// -------------------- 基础倒计时 Hook --------------------

interface UseCountdownOptions {
  targetTime: Date | null;
  onComplete?: () => void;
  interval?: number;
}

export interface CountdownResult {
  timeLeft: number;          // 剩余秒数
  hours: number;
  minutes: number;
  seconds: number;
  isExpired: boolean;
  isCritical: boolean;       // 是否临界状态 (< 30s)
  formattedTime: string;     // 格式化时间 "MM:SS" 或 "HH:MM:SS"
}

export function useCountdown({
  targetTime,
  onComplete,
  interval = 1000,
}: UseCountdownOptions): CountdownResult {
  const [timeLeft, setTimeLeft] = useState<number>(0);
  const onCompleteRef = useRef(onComplete);
  
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    if (!targetTime) {
      setTimeLeft(0);
      return;
    }

    const calculateTimeLeft = () => {
      const now = new Date();
      const diff = differenceInSeconds(targetTime, now);
      return Math.max(0, diff);
    };

    setTimeLeft(calculateTimeLeft());

    const timer = setInterval(() => {
      const newTimeLeft = calculateTimeLeft();
      setTimeLeft(newTimeLeft);
      
      if (newTimeLeft <= 0) {
        clearInterval(timer);
        onCompleteRef.current?.();
      }
    }, interval);

    return () => clearInterval(timer);
  }, [targetTime, interval]);

  const hours = Math.floor(timeLeft / 3600);
  const minutes = Math.floor((timeLeft % 3600) / 60);
  const seconds = timeLeft % 60;
  
  const formattedTime = hours > 0
    ? `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
    : `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

  return {
    timeLeft,
    hours,
    minutes,
    seconds,
    isExpired: timeLeft <= 0,
    isCritical: timeLeft > 0 && timeLeft <= 30,
    formattedTime,
  };
}

// -------------------- Slot 阶段倒计时 Hook --------------------

interface SlotPhaseConfig {
  watching: { duration: number };   // 看戏阶段时长（分钟）
  gate_lobby: { duration: number }; // 门厅阶段时长（分钟）
  settling: { duration: number };   // 结算阶段时长（分钟）
  echo: { duration: number };       // 回声阶段时长（分钟）
}

const DEFAULT_PHASE_CONFIG: SlotPhaseConfig = {
  watching: { duration: 10 },
  gate_lobby: { duration: 2 },
  settling: { duration: 0.5 },  // 30秒
  echo: { duration: 2.5 },
};

interface UseSlotPhaseOptions {
  slotStartTime: Date | null;
  phaseConfig?: SlotPhaseConfig;
  onPhaseChange?: (newPhase: SlotPhase) => void;
}

interface SlotPhaseResult {
  currentPhase: SlotPhase;
  phaseEndTime: Date | null;
  nextPhase: SlotPhase | null;
  countdown: CountdownResult;
  phaseProgress: number;       // 当前阶段进度 0-100
  slotProgress: number;        // 整个 Slot 进度 0-100
}

export function useSlotPhase({
  slotStartTime,
  phaseConfig = DEFAULT_PHASE_CONFIG,
  onPhaseChange,
}: UseSlotPhaseOptions): SlotPhaseResult {
  const [currentPhase, setCurrentPhase] = useState<SlotPhase>('watching');
  const [phaseEndTime, setPhaseEndTime] = useState<Date | null>(null);
  const onPhaseChangeRef = useRef(onPhaseChange);

  useEffect(() => {
    onPhaseChangeRef.current = onPhaseChange;
  }, [onPhaseChange]);

  // 计算各阶段的开始和结束时间
  const calculatePhaseTimings = useCallback(() => {
    if (!slotStartTime) return null;

    const phases: { phase: SlotPhase; start: Date; end: Date }[] = [];
    let currentTime = new Date(slotStartTime);

    const phaseOrder: SlotPhase[] = ['watching', 'gate_lobby', 'settling', 'echo'];
    
    for (const phase of phaseOrder) {
      const duration = phaseConfig[phase].duration;
      const endTime = addMinutes(currentTime, duration);
      phases.push({
        phase,
        start: new Date(currentTime),
        end: endTime,
      });
      currentTime = endTime;
    }

    return phases;
  }, [slotStartTime, phaseConfig]);

  // 确定当前阶段
  useEffect(() => {
    if (!slotStartTime) return;

    const updatePhase = () => {
      const now = new Date();
      const timings = calculatePhaseTimings();
      
      if (!timings) return;

      for (const { phase, start, end } of timings) {
        if (now >= start && now < end) {
          if (phase !== currentPhase) {
            setCurrentPhase(phase);
            onPhaseChangeRef.current?.(phase);
          }
          setPhaseEndTime(end);
          return;
        }
      }

      // 如果超出所有阶段，设为 echo 结束
      const lastPhase = timings[timings.length - 1];
      if (now >= lastPhase.end) {
        setCurrentPhase('echo');
        setPhaseEndTime(null);
      }
    };

    updatePhase();
    const timer = setInterval(updatePhase, 1000);

    return () => clearInterval(timer);
  }, [slotStartTime, calculatePhaseTimings, currentPhase]);

  // 倒计时
  const countdown = useCountdown({
    targetTime: phaseEndTime,
    onComplete: () => {
      // 阶段结束时会自动切换到下一阶段
    },
  });

  // 计算进度
  const calculateProgress = useCallback(() => {
    if (!slotStartTime) return { phaseProgress: 0, slotProgress: 0 };

    const now = new Date();
    const timings = calculatePhaseTimings();
    
    if (!timings) return { phaseProgress: 0, slotProgress: 0 };

    // 当前阶段进度
    const currentTiming = timings.find((t) => t.phase === currentPhase);
    let phaseProgress = 0;
    if (currentTiming) {
      const phaseDuration = differenceInSeconds(currentTiming.end, currentTiming.start);
      const elapsed = differenceInSeconds(now, currentTiming.start);
      phaseProgress = Math.min(100, Math.max(0, (elapsed / phaseDuration) * 100));
    }

    // 整个 Slot 进度
    const slotEnd = timings[timings.length - 1].end;
    const slotDuration = differenceInSeconds(slotEnd, slotStartTime);
    const slotElapsed = differenceInSeconds(now, slotStartTime);
    const slotProgress = Math.min(100, Math.max(0, (slotElapsed / slotDuration) * 100));

    return { phaseProgress, slotProgress };
  }, [slotStartTime, calculatePhaseTimings, currentPhase]);

  const { phaseProgress, slotProgress } = calculateProgress();

  // 下一阶段
  const getNextPhase = (): SlotPhase | null => {
    const phaseOrder: SlotPhase[] = ['watching', 'gate_lobby', 'settling', 'echo'];
    const currentIndex = phaseOrder.indexOf(currentPhase);
    return currentIndex < phaseOrder.length - 1 ? phaseOrder[currentIndex + 1] : null;
  };

  return {
    currentPhase,
    phaseEndTime,
    nextPhase: getNextPhase(),
    countdown,
    phaseProgress,
    slotProgress,
  };
}

// -------------------- 服务器时间同步 Hook --------------------

interface UseServerTimeOptions {
  syncInterval?: number;  // 同步间隔（毫秒）
}

interface ServerTimeResult {
  serverTime: Date;
  offset: number;         // 客户端与服务器的时间偏移（毫秒）
  isSynced: boolean;
  sync: () => Promise<void>;
}

export function useServerTime({
  syncInterval = 60000,  // 默认每分钟同步一次
}: UseServerTimeOptions = {}): ServerTimeResult {
  const [offset, setOffset] = useState<number>(0);
  const [isSynced, setIsSynced] = useState<boolean>(false);

  const sync = useCallback(async () => {
    try {
      const clientSendTime = Date.now();
      
      // 调用服务器时间接口
      const response = await fetch('/v1/time');
      const data = await response.json();
      
      const clientReceiveTime = Date.now();
      const serverTime = new Date(data.server_time).getTime();
      
      // 计算往返时间和偏移
      const roundTripTime = clientReceiveTime - clientSendTime;
      const estimatedServerTime = serverTime + roundTripTime / 2;
      const newOffset = estimatedServerTime - clientReceiveTime;
      
      setOffset(newOffset);
      setIsSynced(true);
    } catch (error) {
      console.error('Failed to sync server time:', error);
    }
  }, []);

  useEffect(() => {
    sync();
    const timer = setInterval(sync, syncInterval);
    return () => clearInterval(timer);
  }, [sync, syncInterval]);

  const serverTime = new Date(Date.now() + offset);

  return {
    serverTime,
    offset,
    isSynced,
    sync,
  };
}

export default useCountdown;
