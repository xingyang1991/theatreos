// ============================================
// TheatreOS Showbill 戏单页面
// ============================================

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  Clock,
  MapPin,
  ChevronRight,
  Sparkles,
  Users,
  AlertCircle,
  Theater,
  Info,
} from 'lucide-react';
import { format, addHours, isWithinInterval } from 'date-fns';
import { zhCN } from 'date-fns/locale';

import { useTheatreStore, useLocationStore } from '@/stores/useStore';
import { scheduleApi, stageApi } from '@/services/api';
import { useCountdown, useSlotPhase } from '@/hooks/useCountdown';
import { CountdownDisplay, PhaseCountdownBar } from '@/components/Countdown';
import { RingBadge } from '@/components/RingBadge';
import type { Slot, Stage, RingLevel } from '@/types';

// -------------------- Showbill 主页面 --------------------

export default function ShowbillPage() {
  const navigate = useNavigate();
  const { currentTheatre, currentSlot, setCurrentSlot, stages, setStages } = useTheatreStore();
  const { currentRing } = useLocationStore();
  
  const [upcomingSlots, setUpcomingSlots] = useState<Slot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 获取戏单数据
  useEffect(() => {
    const fetchShowbill = async () => {
      if (!currentTheatre) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        
        // 并行获取戏单和舞台数据
        const [showbillData, stagesData] = await Promise.all([
          scheduleApi.getShowbill(currentTheatre.theatre_id, 3).catch(() => ({ slots: [] })),
          stageApi.getStages(currentTheatre.theatre_id).catch(() => ({ stages: [] })),
        ]);

        setUpcomingSlots(showbillData.slots || []);
        setStages(stagesData.stages || []);

        // 设置当前 Slot
        const now = new Date();
        const slots = showbillData.slots || [];
        const currentSlotData = slots.find((slot) =>
          isWithinInterval(now, {
            start: new Date(slot.start_time),
            end: new Date(slot.end_time),
          })
        );
        if (currentSlotData) {
          setCurrentSlot(currentSlotData);
        }
      } catch (err) {
        console.error('获取戏单失败:', err);
        // 不设置错误，显示空状态
      } finally {
        setIsLoading(false);
      }
    };

    fetchShowbill();
    const interval = setInterval(fetchShowbill, 60000); // 每分钟刷新

    return () => clearInterval(interval);
  }, [currentTheatre, setCurrentSlot, setStages]);

  // 当前 Slot 的阶段状态
  const slotPhase = useSlotPhase({
    slotStartTime: currentSlot ? new Date(currentSlot.start_time) : null,
  });

  if (isLoading) {
    return <ShowbillSkeleton />;
  }

  // 空状态：没有剧场
  if (!currentTheatre) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <Theater className="w-16 h-16 text-theatre-muted mx-auto mb-4" />
          <h2 className="text-xl font-bold text-theatre-text mb-2">正在连接剧场...</h2>
          <p className="text-theatre-muted mb-4">请稍候，系统正在初始化</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-theatre-accent text-theatre-bg rounded-lg"
          >
            刷新页面
          </button>
        </div>
      </div>
    );
  }

  // 空状态：没有演出数据
  const hasContent = upcomingSlots.length > 0 || stages.length > 0;

  return (
    <div className="min-h-screen bg-theatre-bg">
      {/* 头部 */}
      <header className="sticky top-0 z-40 bg-theatre-bg/80 backdrop-blur-lg border-b border-theatre-border">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-display font-bold text-theatre-accent">
                今日戏单
              </h1>
              <p className="text-sm text-theatre-muted">
                {format(new Date(), 'yyyy年MM月dd日 EEEE', { locale: zhCN })}
              </p>
            </div>
            <RingBadge ring={currentRing} size="sm" />
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {!hasContent ? (
          // 空状态显示
          <EmptyStateCard theatreId={currentTheatre.theatre_id} />
        ) : (
          <>
            {/* 当前时段 */}
            {currentSlot && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-5 h-5 text-theatre-accent" />
                  <h2 className="text-lg font-bold text-theatre-text">正在上演</h2>
                </div>

                <CurrentSlotCard
                  slot={currentSlot}
                  stages={stages}
                  slotPhase={slotPhase}
                  currentRing={currentRing}
                  onStageClick={(stageId) => navigate(`/stage/${stageId}`)}
                  onGateLobbyClick={() => navigate(`/gate-lobby/${currentSlot.slot_id}`)}
                />
              </section>
            )}

            {/* 即将上演 */}
            {upcomingSlots.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Calendar className="w-5 h-5 text-theatre-muted" />
                  <h2 className="text-lg font-bold text-theatre-text">即将上演</h2>
                </div>

                <div className="space-y-4">
                  {upcomingSlots
                    .filter((slot) => new Date(slot.start_time) > new Date())
                    .slice(0, 3)
                    .map((slot) => (
                      <UpcomingSlotCard
                        key={slot.slot_id}
                        slot={slot}
                        stages={stages}
                        currentRing={currentRing}
                      />
                    ))}
                </div>
              </section>
            )}

            {/* 舞台列表 */}
            {stages.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <MapPin className="w-5 h-5 text-theatre-muted" />
                  <h2 className="text-lg font-bold text-theatre-text">城中舞台</h2>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {stages.map((stage) => (
                    <StageCard
                      key={stage.stage_id}
                      stage={stage}
                      currentRing={currentRing}
                      onClick={() => navigate(`/stage/${stage.stage_id}`)}
                    />
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {/* 系统信息 */}
        <section className="pt-4 border-t border-theatre-border">
          <div className="flex items-center gap-2 text-xs text-theatre-muted">
            <Info className="w-4 h-4" />
            <span>剧场ID: {currentTheatre.theatre_id.slice(0, 8)}...</span>
            <span>•</span>
            <span>主题: {currentTheatre.theme_id || 'hp_shanghai_s1'}</span>
          </div>
        </section>
      </main>
    </div>
  );
}

// -------------------- 空状态卡片 --------------------

interface EmptyStateCardProps {
  theatreId: string;
}

function EmptyStateCard({ theatreId }: EmptyStateCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-theatre-surface rounded-xl border border-theatre-border p-8 text-center"
    >
      <Theater className="w-16 h-16 text-theatre-muted mx-auto mb-4" />
      <h3 className="text-lg font-bold text-theatre-text mb-2">
        剧场已就绪
      </h3>
      <p className="text-theatre-muted mb-6 max-w-sm mx-auto">
        当前没有正在进行的演出。演出开始后，这里将显示戏单和舞台信息。
      </p>
      
      <div className="space-y-3">
        <div className="p-4 bg-theatre-bg rounded-lg text-left">
          <h4 className="text-sm font-medium text-theatre-accent mb-2">系统状态</h4>
          <ul className="space-y-2 text-sm text-theatre-muted">
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              后端服务运行中
            </li>
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              主题包已加载
            </li>
            <li className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
              等待演出数据
            </li>
          </ul>
        </div>
        
        <p className="text-xs text-theatre-muted">
          剧场ID: {theatreId}
        </p>
      </div>
    </motion.div>
  );
}

// -------------------- 当前时段卡片 --------------------

interface CurrentSlotCardProps {
  slot: Slot;
  stages: Stage[];
  slotPhase: ReturnType<typeof useSlotPhase>;
  currentRing: RingLevel;
  onStageClick: (stageId: string) => void;
  onGateLobbyClick: () => void;
}

function CurrentSlotCard({
  slot,
  stages,
  slotPhase,
  currentRing,
  onStageClick,
  onGateLobbyClick,
}: CurrentSlotCardProps) {
  const { currentPhase, nextPhase, countdown, phaseProgress } = slotPhase;

  const activeStages = stages.filter((s) =>
    slot.stages?.some((ss) => ss.stage_id === s.stage_id)
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-theatre-surface rounded-xl border border-theatre-accent/30 overflow-hidden"
    >
      {/* 阶段进度条 */}
      <div className="p-4 bg-theatre-accent/5">
        <PhaseCountdownBar
          countdown={countdown}
          phaseName={currentPhase}
          nextPhaseName={nextPhase || undefined}
          progress={phaseProgress}
        />
      </div>

      {/* 舞台列表 */}
      <div className="p-4 space-y-3">
        {activeStages.slice(0, 3).map((stage) => (
          <motion.button
            key={stage.stage_id}
            onClick={() => onStageClick(stage.stage_id)}
            whileHover={{ x: 4 }}
            className="w-full flex items-center gap-3 p-3 rounded-lg bg-theatre-bg hover:bg-theatre-border transition-colors"
          >
            <div className="w-12 h-12 rounded-lg bg-theatre-border flex items-center justify-center">
              <MapPin className="w-6 h-6 text-theatre-muted" />
            </div>
            <div className="flex-1 text-left">
              <h4 className="font-medium text-theatre-text">{stage.name}</h4>
              <p className="text-xs text-theatre-muted">{stage.location}</p>
            </div>
            <RingBadge ring={stage.ring_required} size="sm" showLabel={false} />
            <ChevronRight className="w-5 h-5 text-theatre-muted" />
          </motion.button>
        ))}
      </div>

      {/* 门厅入口 */}
      {(currentPhase === 'gate_lobby' || currentPhase === 'watching') && (
        <div className="p-4 border-t border-theatre-border">
          <button
            onClick={onGateLobbyClick}
            className={clsx(
              'w-full py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2',
              currentPhase === 'gate_lobby'
                ? 'bg-theatre-accent text-theatre-bg animate-pulse'
                : 'bg-theatre-border text-theatre-text hover:bg-theatre-muted/20'
            )}
          >
            <Users className="w-5 h-5" />
            {currentPhase === 'gate_lobby' ? '门厅已开放 - 立即参与' : '查看本场门'}
          </button>
        </div>
      )}
    </motion.div>
  );
}

// -------------------- 即将上演卡片 --------------------

interface UpcomingSlotCardProps {
  slot: Slot;
  stages: Stage[];
  currentRing: RingLevel;
}

function UpcomingSlotCard({ slot, stages, currentRing }: UpcomingSlotCardProps) {
  const startTime = new Date(slot.start_time);
  const countdown = useCountdown({ targetTime: startTime });

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-4 p-4 rounded-xl bg-theatre-surface border border-theatre-border"
    >
      {/* 时间 */}
      <div className="text-center min-w-[60px]">
        <p className="text-2xl font-bold text-theatre-text">
          {format(startTime, 'HH:mm')}
        </p>
        <p className="text-xs text-theatre-muted">
          {countdown.isExpired ? '即将开始' : `${countdown.formattedTime}`}
        </p>
      </div>

      {/* 分隔线 */}
      <div className="w-px h-12 bg-theatre-border" />

      {/* 内容 */}
      <div className="flex-1">
        <p className="font-medium text-theatre-text mb-1">
          {slot.stages?.length || 0} 个舞台同时上演
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          {slot.stages?.slice(0, 3).map((stage) => (
            <span
              key={stage.stage_id}
              className="text-xs px-2 py-0.5 rounded bg-theatre-border text-theatre-muted"
            >
              {stage.name}
            </span>
          ))}
        </div>
      </div>

      {/* 倒计时 */}
      <div className="text-right">
        <CountdownDisplay countdown={countdown} size="sm" />
      </div>
    </motion.div>
  );
}

// -------------------- 舞台卡片 --------------------

interface StageCardProps {
  stage: Stage;
  currentRing: RingLevel;
  onClick: () => void;
}

function StageCard({ stage, currentRing, onClick }: StageCardProps) {
  const ringOrder: RingLevel[] = ['C', 'B', 'A'];
  const hasAccess = ringOrder.indexOf(currentRing) >= ringOrder.indexOf(stage.ring_required);

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        'p-4 rounded-xl text-left transition-all',
        'bg-theatre-surface border',
        hasAccess ? 'border-theatre-border' : 'border-theatre-border/50 opacity-60'
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="w-10 h-10 rounded-lg bg-theatre-border flex items-center justify-center">
          <MapPin className="w-5 h-5 text-theatre-muted" />
        </div>
        <RingBadge ring={stage.ring_required} size="sm" showLabel={false} />
      </div>
      <h4 className="font-medium text-theatre-text mb-1">{stage.name}</h4>
      <p className="text-xs text-theatre-muted line-clamp-2">{stage.description}</p>
      {stage.is_active && (
        <div className="mt-2 flex items-center gap-1 text-xs text-theatre-accent">
          <span className="w-2 h-2 rounded-full bg-theatre-accent animate-pulse" />
          正在上演
        </div>
      )}
    </motion.button>
  );
}

// -------------------- 骨架屏 --------------------

function ShowbillSkeleton() {
  return (
    <div className="min-h-screen bg-theatre-bg">
      <header className="sticky top-0 z-40 bg-theatre-bg/80 backdrop-blur-lg border-b border-theatre-border">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="h-6 w-32 bg-theatre-border rounded animate-pulse" />
          <div className="h-4 w-48 bg-theatre-border rounded animate-pulse mt-2" />
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        <div className="h-64 bg-theatre-surface rounded-xl animate-pulse" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-theatre-surface rounded-xl animate-pulse" />
          ))}
        </div>
      </main>
    </div>
  );
}
