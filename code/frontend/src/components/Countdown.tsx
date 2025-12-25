// ============================================
// TheatreOS 倒计时组件
// ============================================

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import type { CountdownResult } from '@/hooks/useCountdown';

// -------------------- 基础倒计时显示 --------------------

interface CountdownDisplayProps {
  countdown: CountdownResult;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showLabels?: boolean;
  className?: string;
}

export function CountdownDisplay({
  countdown,
  size = 'md',
  showLabels = false,
  className,
}: CountdownDisplayProps) {
  const { hours, minutes, seconds, isCritical, isExpired } = countdown;

  const sizeClasses = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-4xl',
    xl: 'text-6xl',
  };

  const digitClasses = clsx(
    'font-mono font-bold tabular-nums',
    sizeClasses[size],
    isCritical && 'text-theatre-danger animate-pulse',
    isExpired && 'text-theatre-muted',
    !isCritical && !isExpired && 'text-theatre-accent'
  );

  return (
    <div className={clsx('flex items-center gap-1', className)}>
      {hours > 0 && (
        <>
          <TimeUnit value={hours} label="时" showLabel={showLabels} className={digitClasses} />
          <span className={digitClasses}>:</span>
        </>
      )}
      <TimeUnit value={minutes} label="分" showLabel={showLabels} className={digitClasses} />
      <span className={digitClasses}>:</span>
      <TimeUnit value={seconds} label="秒" showLabel={showLabels} className={digitClasses} />
    </div>
  );
}

interface TimeUnitProps {
  value: number;
  label: string;
  showLabel: boolean;
  className: string;
}

function TimeUnit({ value, label, showLabel, className }: TimeUnitProps) {
  return (
    <div className="flex flex-col items-center">
      <AnimatePresence mode="popLayout">
        <motion.span
          key={value}
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 10, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={className}
        >
          {value.toString().padStart(2, '0')}
        </motion.span>
      </AnimatePresence>
      {showLabel && (
        <span className="text-xs text-theatre-muted mt-1">{label}</span>
      )}
    </div>
  );
}

// -------------------- 圆形进度倒计时 --------------------

interface CircularCountdownProps {
  countdown: CountdownResult;
  totalSeconds: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export function CircularCountdown({
  countdown,
  totalSeconds,
  size = 120,
  strokeWidth = 8,
  className,
}: CircularCountdownProps) {
  const { timeLeft, isCritical, isExpired, formattedTime } = countdown;
  
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = totalSeconds > 0 ? (timeLeft / totalSeconds) : 0;
  const strokeDashoffset = circumference * (1 - progress);

  const strokeColor = isCritical
    ? '#ef4444'  // danger
    : isExpired
    ? '#6b6b7a'  // muted
    : '#c9a962'; // accent

  return (
    <div className={clsx('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* 背景圆环 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#1f1f2e"
          strokeWidth={strokeWidth}
        />
        {/* 进度圆环 */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </svg>
      {/* 中心时间显示 */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span
          className={clsx(
            'font-mono font-bold text-lg',
            isCritical && 'text-theatre-danger animate-pulse',
            isExpired && 'text-theatre-muted',
            !isCritical && !isExpired && 'text-theatre-text'
          )}
        >
          {formattedTime}
        </span>
      </div>
    </div>
  );
}

// -------------------- 阶段倒计时条 --------------------

interface PhaseCountdownBarProps {
  countdown: CountdownResult;
  phaseName: string;
  nextPhaseName?: string;
  progress: number;
  className?: string;
}

export function PhaseCountdownBar({
  countdown,
  phaseName,
  nextPhaseName,
  progress,
  className,
}: PhaseCountdownBarProps) {
  const { isCritical, isExpired, formattedTime } = countdown;

  const phaseLabels: Record<string, string> = {
    watching: '🎭 观演中',
    gate_lobby: '🚪 门厅开放',
    settling: '⚖️ 结算中',
    echo: '🔔 回声时刻',
  };

  return (
    <div className={clsx('w-full', className)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-theatre-text">
            {phaseLabels[phaseName] || phaseName}
          </span>
          {nextPhaseName && (
            <span className="text-xs text-theatre-muted">
              → {phaseLabels[nextPhaseName] || nextPhaseName}
            </span>
          )}
        </div>
        <span
          className={clsx(
            'font-mono text-sm font-bold',
            isCritical && 'text-theatre-danger animate-pulse',
            isExpired && 'text-theatre-muted',
            !isCritical && !isExpired && 'text-theatre-accent'
          )}
        >
          {formattedTime}
        </span>
      </div>
      
      {/* 进度条 */}
      <div className="h-2 bg-theatre-border rounded-full overflow-hidden">
        <motion.div
          className={clsx(
            'h-full rounded-full',
            isCritical ? 'bg-theatre-danger' : 'bg-theatre-accent'
          )}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
    </div>
  );
}

// -------------------- 临界状态全屏提示 --------------------

interface CriticalCountdownOverlayProps {
  countdown: CountdownResult;
  message?: string;
  onDismiss?: () => void;
}

export function CriticalCountdownOverlay({
  countdown,
  message = '即将开始',
  onDismiss,
}: CriticalCountdownOverlayProps) {
  const { isCritical, seconds } = countdown;

  if (!isCritical) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
        onClick={onDismiss}
      >
        <motion.div
          initial={{ scale: 0.8 }}
          animate={{ scale: 1 }}
          className="text-center"
        >
          <motion.div
            key={seconds}
            initial={{ scale: 1.2, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-9xl font-bold text-theatre-accent mb-4"
          >
            {seconds}
          </motion.div>
          <p className="text-2xl text-theatre-text">{message}</p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export default CountdownDisplay;
