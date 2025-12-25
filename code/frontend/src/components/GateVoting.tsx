// ============================================
// TheatreOS 门（Gate）投票组件
// ============================================

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import {
  Vote,
  Coins,
  FileCheck,
  ChevronRight,
  Users,
  TrendingUp,
  Lock,
  Unlock,
} from 'lucide-react';
import type { Gate, GateOption, GateType, Evidence } from '@/types';
import { CountdownDisplay } from './Countdown';
import { useCountdown } from '@/hooks/useCountdown';

// -------------------- 门类型配置 --------------------

const GATE_TYPE_CONFIG: Record<GateType, {
  label: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: React.ReactNode;
}> = {
  public: {
    label: '公共门',
    description: '所有人可参与',
    color: 'text-gate-public',
    bgColor: 'bg-gate-public/10',
    borderColor: 'border-gate-public/30',
    icon: <Unlock className="w-4 h-4" />,
  },
  fate: {
    label: '命运门',
    description: '需要证物入场',
    color: 'text-gate-fate',
    bgColor: 'bg-gate-fate/10',
    borderColor: 'border-gate-fate/30',
    icon: <Lock className="w-4 h-4" />,
  },
  council: {
    label: '议会门',
    description: '剧团集体决策',
    color: 'text-gate-council',
    bgColor: 'bg-gate-council/10',
    borderColor: 'border-gate-council/30',
    icon: <Users className="w-4 h-4" />,
  },
};

// -------------------- 门卡片组件 --------------------

interface GateCardProps {
  gate: Gate;
  onVote?: (optionId: string) => void;
  onBet?: (optionId: string, amount: number) => void;
  onSubmitEvidence?: (evidenceIds: string[]) => void;
  userTickets?: number;
  userEvidences?: Evidence[];
  className?: string;
}

export function GateCard({
  gate,
  onVote,
  onBet,
  onSubmitEvidence,
  userTickets = 0,
  userEvidences = [],
  className,
}: GateCardProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [betAmount, setBetAmount] = useState<number>(1);
  const [selectedEvidences, setSelectedEvidences] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'vote' | 'bet' | 'evidence'>('vote');

  // 确保gate_type有有效值
  const safeGateType = gate.gate_type && GATE_TYPE_CONFIG[gate.gate_type] ? gate.gate_type : 'public';
  const typeConfig = GATE_TYPE_CONFIG[safeGateType];
  
  const closeCountdown = useCountdown({
    targetTime: new Date(gate.close_time),
  });

  const isOpen = gate.status === 'open';
  const isClosed = gate.status === 'closed' || gate.status === 'settled';

  const handleVote = () => {
    if (selectedOption && onVote) {
      onVote(selectedOption);
    }
  };

  const handleBet = () => {
    if (selectedOption && onBet) {
      onBet(selectedOption, betAmount);
    }
  };

  const handleSubmitEvidence = () => {
    if (selectedEvidences.length > 0 && onSubmitEvidence) {
      onSubmitEvidence(selectedEvidences);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'rounded-xl border overflow-hidden',
        'bg-theatre-surface',
        typeConfig.borderColor,
        className
      )}
    >
      {/* 头部 */}
      <div className={clsx('p-4', typeConfig.bgColor)}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className={typeConfig.color}>{typeConfig.icon}</span>
            <span className={clsx('text-sm font-medium', typeConfig.color)}>
              {typeConfig.label}
            </span>
          </div>
          {isOpen && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-theatre-muted">剩余</span>
              <CountdownDisplay countdown={closeCountdown} size="sm" />
            </div>
          )}
          {isClosed && (
            <span className="text-xs text-theatre-muted">已结束</span>
          )}
        </div>
        <h3 className="text-lg font-bold text-theatre-text">{gate.question}</h3>
      </div>

      {/* 统计信息 */}
      <div className="flex items-center justify-around py-3 border-b border-theatre-border">
        <div className="text-center">
          <p className="text-lg font-bold text-theatre-text">{gate.total_votes}</p>
          <p className="text-xs text-theatre-muted">投票数</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-theatre-accent">{gate.total_bets}</p>
          <p className="text-xs text-theatre-muted">下注额</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-theatre-text">
            {gate.submitted_evidences}/{gate.evidence_slots}
          </p>
          <p className="text-xs text-theatre-muted">证物</p>
        </div>
      </div>

      {/* 选项列表 */}
      <div className="p-4 space-y-2">
        {gate.options.map((option) => (
          <GateOptionItem
            key={option.option_id}
            option={option}
            isSelected={selectedOption === option.option_id}
            onSelect={() => setSelectedOption(option.option_id)}
            totalVotes={gate.total_votes}
            disabled={!isOpen}
          />
        ))}
      </div>

      {/* 操作区域 */}
      {isOpen && (
        <div className="border-t border-theatre-border">
          {/* 标签切换 */}
          <div className="flex border-b border-theatre-border">
            <TabButton
              active={activeTab === 'vote'}
              onClick={() => setActiveTab('vote')}
              icon={<Vote className="w-4 h-4" />}
              label="投票"
            />
            <TabButton
              active={activeTab === 'bet'}
              onClick={() => setActiveTab('bet')}
              icon={<Coins className="w-4 h-4" />}
              label="下注"
            />
            {gate.evidence_slots > 0 && (
              <TabButton
                active={activeTab === 'evidence'}
                onClick={() => setActiveTab('evidence')}
                icon={<FileCheck className="w-4 h-4" />}
                label="提交证物"
              />
            )}
          </div>

          {/* 操作内容 */}
          <div className="p-4">
            <AnimatePresence mode="wait">
              {activeTab === 'vote' && (
                <motion.div
                  key="vote"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <button
                    onClick={handleVote}
                    disabled={!selectedOption}
                    className={clsx(
                      'w-full py-3 rounded-lg font-medium transition-all',
                      selectedOption
                        ? 'bg-theatre-accent text-theatre-bg hover:opacity-90'
                        : 'bg-theatre-border text-theatre-muted cursor-not-allowed'
                    )}
                  >
                    确认投票
                  </button>
                </motion.div>
              )}

              {activeTab === 'bet' && (
                <motion.div
                  key="bet"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-theatre-muted">下注数量</span>
                    <span className="text-sm text-theatre-text">
                      余额: {userTickets} 票
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setBetAmount(Math.max(1, betAmount - 1))}
                      className="w-10 h-10 rounded-lg bg-theatre-border text-theatre-text hover:bg-theatre-muted/20"
                    >
                      -
                    </button>
                    <input
                      type="number"
                      value={betAmount}
                      onChange={(e) => setBetAmount(Math.max(1, parseInt(e.target.value) || 1))}
                      className="flex-1 h-10 px-4 rounded-lg bg-theatre-bg border border-theatre-border text-center text-theatre-text"
                    />
                    <button
                      onClick={() => setBetAmount(Math.min(userTickets, betAmount + 1))}
                      className="w-10 h-10 rounded-lg bg-theatre-border text-theatre-text hover:bg-theatre-muted/20"
                    >
                      +
                    </button>
                  </div>
                  <button
                    onClick={handleBet}
                    disabled={!selectedOption || betAmount > userTickets}
                    className={clsx(
                      'w-full py-3 rounded-lg font-medium transition-all',
                      selectedOption && betAmount <= userTickets
                        ? 'bg-theatre-accent text-theatre-bg hover:opacity-90'
                        : 'bg-theatre-border text-theatre-muted cursor-not-allowed'
                    )}
                  >
                    下注 {betAmount} 票
                  </button>
                </motion.div>
              )}

              {activeTab === 'evidence' && (
                <motion.div
                  key="evidence"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-3"
                >
                  <p className="text-sm text-theatre-muted">
                    选择要提交的证物（最多 {gate.evidence_slots - gate.submitted_evidences} 个）
                  </p>
                  <div className="max-h-40 overflow-y-auto space-y-2">
                    {userEvidences.map((evidence) => (
                      <label
                        key={evidence.evidence_id}
                        className={clsx(
                          'flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors',
                          selectedEvidences.includes(evidence.evidence_id)
                            ? 'bg-theatre-accent/20 border border-theatre-accent'
                            : 'bg-theatre-bg hover:bg-theatre-border'
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={selectedEvidences.includes(evidence.evidence_id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedEvidences([...selectedEvidences, evidence.evidence_id]);
                            } else {
                              setSelectedEvidences(selectedEvidences.filter(id => id !== evidence.evidence_id));
                            }
                          }}
                          className="sr-only"
                        />
                        <span className="text-sm text-theatre-text">{evidence.title}</span>
                        <span className="text-xs text-theatre-muted ml-auto">{evidence.grade}级</span>
                      </label>
                    ))}
                  </div>
                  <button
                    onClick={handleSubmitEvidence}
                    disabled={selectedEvidences.length === 0}
                    className={clsx(
                      'w-full py-3 rounded-lg font-medium transition-all',
                      selectedEvidences.length > 0
                        ? 'bg-theatre-accent text-theatre-bg hover:opacity-90'
                        : 'bg-theatre-border text-theatre-muted cursor-not-allowed'
                    )}
                  >
                    提交 {selectedEvidences.length} 个证物
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}
    </motion.div>
  );
}

// -------------------- 选项组件 --------------------

interface GateOptionItemProps {
  option: GateOption;
  isSelected: boolean;
  onSelect: () => void;
  totalVotes: number;
  disabled?: boolean;
}

function GateOptionItem({
  option,
  isSelected,
  onSelect,
  totalVotes,
  disabled,
}: GateOptionItemProps) {
  const percentage = totalVotes > 0 ? (option.vote_count / totalVotes) * 100 : 0;

  return (
    <motion.button
      onClick={onSelect}
      disabled={disabled}
      whileHover={!disabled ? { scale: 1.01 } : {}}
      whileTap={!disabled ? { scale: 0.99 } : {}}
      className={clsx(
        'relative w-full p-4 rounded-lg text-left transition-all overflow-hidden',
        isSelected
          ? 'border-2 border-theatre-accent bg-theatre-accent/10'
          : 'border border-theatre-border bg-theatre-bg hover:border-theatre-muted',
        disabled && 'cursor-not-allowed opacity-70'
      )}
    >
      {/* 进度条背景 */}
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${percentage}%` }}
        className="absolute inset-0 bg-theatre-accent/10"
      />

      {/* 内容 */}
      <div className="relative flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              'w-5 h-5 rounded-full border-2 flex items-center justify-center',
              isSelected
                ? 'border-theatre-accent bg-theatre-accent'
                : 'border-theatre-muted'
            )}
          >
            {isSelected && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="w-2 h-2 rounded-full bg-theatre-bg"
              />
            )}
          </div>
          <div>
            <p className="font-medium text-theatre-text">{option.label}</p>
            {option.description && (
              <p className="text-xs text-theatre-muted">{option.description}</p>
            )}
          </div>
        </div>

        <div className="text-right">
          <p className="font-bold text-theatre-text">{percentage.toFixed(1)}%</p>
          <p className="text-xs text-theatre-muted">{option.vote_count} 票</p>
        </div>
      </div>

      {/* 赔率显示 */}
      {option.odds && (
        <div className="relative mt-2 flex items-center gap-1 text-xs text-theatre-accent">
          <TrendingUp className="w-3 h-3" />
          <span>赔率 {option.odds.toFixed(2)}x</span>
        </div>
      )}
    </motion.button>
  );
}

// -------------------- 标签按钮 --------------------

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex-1 flex items-center justify-center gap-2 py-3 transition-colors',
        active
          ? 'text-theatre-accent border-b-2 border-theatre-accent'
          : 'text-theatre-muted hover:text-theatre-text'
      )}
    >
      {icon}
      <span className="text-sm font-medium">{label}</span>
    </button>
  );
}

export default GateCard;
