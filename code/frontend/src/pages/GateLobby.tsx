// ============================================
// TheatreOS Gate Lobby 门厅页面
// ============================================

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  Users,
  Coins,
  FileCheck,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

import { useTheatreStore, useAuthStore, useLocationStore } from '@/stores/useStore';
import { gateApi, evidenceApi } from '@/services/api';
import { useSlotPhase } from '@/hooks/useCountdown';
import { PhaseCountdownBar } from '@/components/Countdown';
import { GateCard } from '@/components/GateVoting';
import { EvidenceList } from '@/components/EvidenceCard';
import { RingBadge } from '@/components/RingBadge';
import type { Gate, Evidence } from '@/types';

// -------------------- Gate Lobby 主页面 --------------------

export default function GateLobbyPage() {
  const { slotId } = useParams<{ slotId: string }>();
  const navigate = useNavigate();

  const { currentSlot } = useTheatreStore();
  const { user } = useAuthStore();
  const wallet = { tickets: 100 }; // TODO: 从后端获取钱包数据
  const { currentRing } = useLocationStore();

  const [gates, setGates] = useState<Gate[]>([]);
  const [userEvidences, setUserEvidences] = useState<Evidence[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'gates' | 'evidences'>('gates');
  const [votingResult, setVotingResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  // 当前 Slot 的阶段状态
  const slotPhase = useSlotPhase({
    slotStartTime: currentSlot ? new Date(currentSlot.start_time) : null,
  });

  // 获取门和证物数据
  useEffect(() => {
    const fetchData = async () => {
      if (!slotId || !user) return;

      try {
        setIsLoading(true);
        const [gatesData, evidencesData] = await Promise.all([
          gateApi.getGates(slotId),
          evidenceApi.getMyEvidences(),
        ]);

        setGates(gatesData.gates);
        // 处理分页响应
        const evidences = 'items' in evidencesData ? evidencesData.items : [];
        setUserEvidences(evidences);
      } catch (err) {
        setError('获取数据失败');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [slotId, user]);

  // 处理投票
  const handleVote = async (gateId: string, optionId: string) => {
    if (!user) return;

    try {
      await gateApi.vote(gateId, optionId);
      setVotingResult({ success: true, message: '投票成功！' });

      // 刷新门数据
      if (slotId) {
        const gatesData = await gateApi.getGates(slotId);
        setGates(gatesData.gates);
      }
    } catch (err) {
      setVotingResult({ success: false, message: '投票失败，请重试' });
    }

    // 3秒后清除结果提示
    setTimeout(() => setVotingResult(null), 3000);
  };

  // 处理下注
  const handleBet = async (gateId: string, optionId: string, amount: number) => {
    if (!user) return;

    try {
      await gateApi.bet(gateId, optionId, amount);
      setVotingResult({ success: true, message: `下注 ${amount} 票成功！` });

      // 刷新门数据
      if (slotId) {
        const gatesData = await gateApi.getGates(slotId);
        setGates(gatesData.gates);
      }
    } catch (err) {
      setVotingResult({ success: false, message: '下注失败，请重试' });
    }

    setTimeout(() => setVotingResult(null), 3000);
  };

  // 处理提交证物
  const handleSubmitEvidence = async (gateId: string, evidenceIds: string[]) => {
    if (!user) return;

    try {
      await gateApi.submitEvidence(gateId, evidenceIds);
      setVotingResult({ success: true, message: '证物提交成功！' });

      // 刷新数据
      if (slotId) {
        const [gatesData, evidencesData] = await Promise.all([
          gateApi.getGates(slotId),
          evidenceApi.getMyEvidences(),
        ]);
        setGates(gatesData.gates);
        const evidences = 'items' in evidencesData ? evidencesData.items : [];
        setUserEvidences(evidences);
      }
    } catch (err) {
      setVotingResult({ success: false, message: '证物提交失败' });
    }

    setTimeout(() => setVotingResult(null), 3000);
  };

  // 检查是否在门厅开放时间
  const isGateLobbyOpen = slotPhase.currentPhase === 'gate_lobby';

  if (isLoading) {
    return <GateLobbySkeleton />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-theatre-danger mx-auto mb-4" />
          <p className="text-theatre-text mb-4">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-theatre-accent text-theatre-bg rounded-lg"
          >
            返回
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-theatre-bg">
      {/* 头部 */}
      <header className="sticky top-0 z-40 bg-theatre-bg/80 backdrop-blur-lg border-b border-theatre-border">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 text-theatre-text"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">门厅</span>
            </button>
            <RingBadge ring={currentRing} size="sm" />
          </div>

          {/* 阶段进度条 */}
          <PhaseCountdownBar
            countdown={slotPhase.countdown}
            phaseName={slotPhase.currentPhase}
            nextPhaseName={slotPhase.nextPhase || undefined}
            progress={slotPhase.phaseProgress}
          />
        </div>
      </header>

      {/* 统计栏 */}
      <div className="max-w-2xl mx-auto px-4 py-4">
        <div className="grid grid-cols-3 gap-4 p-4 bg-theatre-surface rounded-xl border border-theatre-border">
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-theatre-accent mb-1">
              <Users className="w-4 h-4" />
              <span className="text-lg font-bold">
                {gates.reduce((sum, g) => sum + g.total_votes, 0)}
              </span>
            </div>
            <p className="text-xs text-theatre-muted">总投票</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-theatre-accent mb-1">
              <Coins className="w-4 h-4" />
              <span className="text-lg font-bold">{wallet?.tickets || 0}</span>
            </div>
            <p className="text-xs text-theatre-muted">我的票</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-theatre-accent mb-1">
              <FileCheck className="w-4 h-4" />
              <span className="text-lg font-bold">{userEvidences.length}</span>
            </div>
            <p className="text-xs text-theatre-muted">我的证物</p>
          </div>
        </div>
      </div>

      {/* 标签切换 */}
      <div className="max-w-2xl mx-auto px-4">
        <div className="flex border-b border-theatre-border">
          <button
            onClick={() => setActiveTab('gates')}
            className={clsx(
              'flex-1 py-3 text-center font-medium transition-colors',
              activeTab === 'gates'
                ? 'text-theatre-accent border-b-2 border-theatre-accent'
                : 'text-theatre-muted'
            )}
          >
            本场门 ({gates.length})
          </button>
          <button
            onClick={() => setActiveTab('evidences')}
            className={clsx(
              'flex-1 py-3 text-center font-medium transition-colors',
              activeTab === 'evidences'
                ? 'text-theatre-accent border-b-2 border-theatre-accent'
                : 'text-theatre-muted'
            )}
          >
            我的证物 ({userEvidences.length})
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <main className="max-w-2xl mx-auto px-4 py-6">
        <AnimatePresence mode="wait">
          {activeTab === 'gates' && (
            <motion.div
              key="gates"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-6"
            >
              {!isGateLobbyOpen && (
                <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <div className="flex items-center gap-2 text-yellow-500">
                    <Clock className="w-5 h-5" />
                    <span className="font-medium">门厅尚未开放</span>
                  </div>
                  <p className="text-sm text-theatre-muted mt-1">
                    门厅将在观看阶段结束后开放，届时您可以参与投票和下注。
                  </p>
                </div>
              )}

              {gates.length === 0 ? (
                <div className="text-center py-12 text-theatre-muted">
                  <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>本场暂无开放的门</p>
                </div>
              ) : (
                gates.map((gate) => (
                  <GateCard
                    key={gate.gate_id}
                    gate={gate}
                    onVote={(optionId) => handleVote(gate.gate_id, optionId)}
                    onBet={(optionId, amount) => handleBet(gate.gate_id, optionId, amount)}
                    onSubmitEvidence={(evidenceIds) =>
                      handleSubmitEvidence(gate.gate_id, evidenceIds)
                    }
                    userTickets={wallet?.tickets || 0}
                    userEvidences={userEvidences}
                  />
                ))
              )}
            </motion.div>
          )}

          {activeTab === 'evidences' && (
            <motion.div
              key="evidences"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <EvidenceList
                evidences={userEvidences}
                emptyMessage="您还没有获得任何证物，观看场景可获得证物"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* 投票结果提示 */}
      <AnimatePresence>
        {votingResult && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="fixed bottom-20 left-4 right-4 z-50"
          >
            <div
              className={clsx(
                'max-w-md mx-auto p-4 rounded-lg flex items-center gap-3',
                votingResult.success
                  ? 'bg-green-500/20 border border-green-500/30'
                  : 'bg-red-500/20 border border-red-500/30'
              )}
            >
              {votingResult.success ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-500" />
              )}
              <span
                className={clsx(
                  'font-medium',
                  votingResult.success ? 'text-green-500' : 'text-red-500'
                )}
              >
                {votingResult.message}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// -------------------- 骨架屏 --------------------

function GateLobbySkeleton() {
  return (
    <div className="min-h-screen bg-theatre-bg">
      <header className="sticky top-0 z-40 bg-theatre-bg/80 backdrop-blur-lg border-b border-theatre-border">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="h-6 w-24 bg-theatre-border rounded animate-pulse" />
          <div className="h-8 w-full bg-theatre-border rounded animate-pulse mt-4" />
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-64 bg-theatre-surface rounded-xl animate-pulse"
          />
        ))}
      </main>
    </div>
  );
}
