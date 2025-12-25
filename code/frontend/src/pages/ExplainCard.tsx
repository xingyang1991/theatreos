// ============================================
// TheatreOS ExplainCard 结算展示页面
// ============================================

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Trophy,
  TrendingUp,
  TrendingDown,
  Minus,
  Gift,
  FileText,
  Sparkles,
  ChevronRight,
  Clock,
  Users,
  Coins,
  BookOpen,
  Share2,
} from 'lucide-react';

import { useTheatreStore, useAuthStore } from '@/stores/useStore';
import { RingBadge } from '@/components/RingBadge';

// -------------------- 类型定义 --------------------

interface GateOption {
  option_id: string;
  text: string;
  votes: number;
  odds: number;
  is_winner: boolean;
}

interface ExplainCardData {
  gate_id: string;
  gate_title: string;
  gate_type: 'plot' | 'lore' | 'meta';
  gate_question: string;
  settled_at: string;
  
  // 选项结果
  options: GateOption[];
  winning_option_id: string;
  
  // 用户参与
  user_participation: {
    voted_option_id: string | null;
    bet_option_id: string | null;
    bet_amount: number;
    submitted_evidence_ids: string[];
    is_winner: boolean;
  };
  
  // 收益结算
  rewards: {
    base_tickets: number;
    bet_return: number;
    evidence_bonus: number;
    streak_bonus: number;
    total_change: number;
  };
  
  // 新获得的证物
  new_evidences: {
    evidence_id: string;
    name: string;
    type: string;
    grade: 'common' | 'rare' | 'epic' | 'legendary';
    description: string;
  }[];
  
  // 回声
  echo: {
    echo_id: string;
    title: string;
    summary: string;
    narrative: string;
    world_impact: {
      variable: string;
      change: number;
      description: string;
    }[];
    thread_name: string;
  };
  
  // 统计
  total_participants: number;
  total_bets: number;
}

// -------------------- 模拟数据 --------------------

const mockExplainData: ExplainCardData = {
  gate_id: 'gate_001',
  gate_title: '飞路粉的秘密',
  gate_type: 'plot',
  gate_question: '神秘的飞路粉供应商究竟是谁？',
  settled_at: new Date().toISOString(),
  
  options: [
    { option_id: 'opt_1', text: '蒙顿格斯·弗莱奇', votes: 156, odds: 2.5, is_winner: true },
    { option_id: 'opt_2', text: '博金先生', votes: 89, odds: 3.2, is_winner: false },
    { option_id: 'opt_3', text: '神秘的东方商人', votes: 67, odds: 4.1, is_winner: false },
  ],
  winning_option_id: 'opt_1',
  
  user_participation: {
    voted_option_id: 'opt_1',
    bet_option_id: 'opt_1',
    bet_amount: 50,
    submitted_evidence_ids: ['ev_001'],
    is_winner: true,
  },
  
  rewards: {
    base_tickets: 10,
    bet_return: 125,
    evidence_bonus: 20,
    streak_bonus: 15,
    total_change: 170,
  },
  
  new_evidences: [
    {
      evidence_id: 'ev_new_001',
      name: '飞路粉配方残页',
      type: 'document',
      grade: 'rare',
      description: '一张沾满灰尘的羊皮纸，上面记载着飞路粉的部分配方...',
    },
  ],
  
  echo: {
    echo_id: 'echo_001',
    title: '飞路网络的裂痕',
    summary: '蒙顿格斯的身份被揭露，飞路粉黑市即将面临整顿。',
    narrative: '当傲罗们冲进翻倒巷的地下仓库时，蒙顿格斯·弗莱奇正试图销毁最后一批证据。这位狡猾的走私贩终于落入法网，但他背后的势力似乎远不止于此。魔法部的调查才刚刚开始...',
    world_impact: [
      { variable: '黑市热度', change: -15, description: '黑市活动暂时收敛' },
      { variable: '飞路稳定性', change: +10, description: '非法飞路粉流通减少' },
    ],
    thread_name: '飞路错拍线',
  },
  
  total_participants: 312,
  total_bets: 15680,
};

// -------------------- 子组件 --------------------

// 结果横幅
function ResultBanner({ isWinner, totalChange }: { isWinner: boolean; totalChange: number }) {
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={clsx(
        'relative overflow-hidden rounded-2xl p-6 text-center',
        isWinner
          ? 'bg-gradient-to-br from-yellow-500/20 to-amber-600/20 border border-yellow-500/30'
          : 'bg-gradient-to-br from-slate-500/20 to-slate-600/20 border border-slate-500/30'
      )}
    >
      {/* 背景装饰 */}
      {isWinner && (
        <div className="absolute inset-0 overflow-hidden">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] bg-gradient-conic from-yellow-500/10 via-transparent to-yellow-500/10"
          />
        </div>
      )}
      
      <div className="relative z-10">
        <motion.div
          initial={{ y: -20 }}
          animate={{ y: 0 }}
          transition={{ delay: 0.2 }}
        >
          {isWinner ? (
            <Trophy className="w-16 h-16 mx-auto mb-3 text-yellow-500" />
          ) : (
            <Minus className="w-16 h-16 mx-auto mb-3 text-slate-400" />
          )}
        </motion.div>
        
        <h2 className={clsx(
          'text-2xl font-display font-bold mb-2',
          isWinner ? 'text-yellow-500' : 'text-slate-400'
        )}>
          {isWinner ? '预测成功！' : '未能命中'}
        </h2>
        
        <div className={clsx(
          'text-3xl font-bold flex items-center justify-center gap-2',
          totalChange >= 0 ? 'text-green-500' : 'text-red-500'
        )}>
          {totalChange >= 0 ? (
            <TrendingUp className="w-6 h-6" />
          ) : (
            <TrendingDown className="w-6 h-6" />
          )}
          <span>{totalChange >= 0 ? '+' : ''}{totalChange}</span>
          <Coins className="w-5 h-5" />
        </div>
      </div>
    </motion.div>
  );
}

// 选项结果卡片
function OptionResultCard({ option, userVoted, userBet }: {
  option: GateOption;
  userVoted: boolean;
  userBet: boolean;
}) {
  return (
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className={clsx(
        'p-4 rounded-xl border transition-all',
        option.is_winner
          ? 'bg-green-500/10 border-green-500/30'
          : 'bg-theatre-surface border-theatre-border'
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            {option.is_winner && (
              <span className="px-2 py-0.5 bg-green-500 text-white text-xs rounded-full font-medium">
                胜出
              </span>
            )}
            {userVoted && (
              <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                已投票
              </span>
            )}
            {userBet && (
              <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded-full">
                已下注
              </span>
            )}
          </div>
          <p className={clsx(
            'font-medium',
            option.is_winner ? 'text-green-400' : 'text-theatre-text'
          )}>
            {option.text}
          </p>
        </div>
        <div className="text-right">
          <p className="text-lg font-bold text-theatre-accent">{option.odds}x</p>
          <p className="text-xs text-theatre-muted">{option.votes} 票</p>
        </div>
      </div>
      
      {/* 投票比例条 */}
      <div className="h-2 bg-theatre-border rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(option.votes / 312) * 100}%` }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className={clsx(
            'h-full rounded-full',
            option.is_winner ? 'bg-green-500' : 'bg-theatre-muted'
          )}
        />
      </div>
    </motion.div>
  );
}

// 收益明细卡片
function RewardsBreakdown({ rewards }: { rewards: ExplainCardData['rewards'] }) {
  const items = [
    { label: '基础奖励', value: rewards.base_tickets, icon: Gift },
    { label: '下注收益', value: rewards.bet_return, icon: Coins },
    { label: '证物加成', value: rewards.evidence_bonus, icon: FileText },
    { label: '连胜奖励', value: rewards.streak_bonus, icon: Sparkles },
  ].filter(item => item.value !== 0);
  
  return (
    <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4">
      <h3 className="text-sm font-medium text-theatre-muted mb-3">收益明细</h3>
      <div className="space-y-2">
        {items.map((item, index) => (
          <motion.div
            key={item.label}
            initial={{ x: -10, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-2 text-theatre-text">
              <item.icon className="w-4 h-4 text-theatre-muted" />
              <span>{item.label}</span>
            </div>
            <span className={clsx(
              'font-medium',
              item.value >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {item.value >= 0 ? '+' : ''}{item.value}
            </span>
          </motion.div>
        ))}
        <div className="border-t border-theatre-border pt-2 mt-2 flex items-center justify-between">
          <span className="font-medium text-theatre-text">总计</span>
          <span className={clsx(
            'text-lg font-bold',
            rewards.total_change >= 0 ? 'text-green-500' : 'text-red-500'
          )}>
            {rewards.total_change >= 0 ? '+' : ''}{rewards.total_change}
          </span>
        </div>
      </div>
    </div>
  );
}

// 新证物展示
function NewEvidenceCard({ evidence }: { evidence: ExplainCardData['new_evidences'][0] }) {
  const gradeColors = {
    common: 'from-slate-500/20 to-slate-600/20 border-slate-500/30',
    rare: 'from-blue-500/20 to-blue-600/20 border-blue-500/30',
    epic: 'from-purple-500/20 to-purple-600/20 border-purple-500/30',
    legendary: 'from-yellow-500/20 to-amber-600/20 border-yellow-500/30',
  };
  
  const gradeLabels = {
    common: '普通',
    rare: '稀有',
    epic: '史诗',
    legendary: '传说',
  };
  
  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={clsx(
        'p-4 rounded-xl border bg-gradient-to-br',
        gradeColors[evidence.grade]
      )}
    >
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-lg bg-theatre-bg/50 flex items-center justify-center">
          <FileText className="w-6 h-6 text-theatre-accent" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-2 py-0.5 rounded-full bg-theatre-bg/50 text-theatre-muted">
              {gradeLabels[evidence.grade]}
            </span>
            <span className="text-xs text-theatre-muted">{evidence.type}</span>
          </div>
          <h4 className="font-medium text-theatre-text mb-1">{evidence.name}</h4>
          <p className="text-sm text-theatre-muted line-clamp-2">{evidence.description}</p>
        </div>
      </div>
    </motion.div>
  );
}

// 回声叙事卡片
function EchoNarrativeCard({ echo }: { echo: ExplainCardData['echo'] }) {
  return (
    <div className="bg-gradient-to-br from-theatre-accent/10 to-purple-500/10 rounded-xl border border-theatre-accent/30 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BookOpen className="w-5 h-5 text-theatre-accent" />
        <h3 className="font-display font-bold text-theatre-accent">{echo.title}</h3>
      </div>
      
      <p className="text-theatre-text mb-4 leading-relaxed">{echo.narrative}</p>
      
      {/* 世界影响 */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-theatre-muted">世界影响</h4>
        {echo.world_impact.map((impact, index) => (
          <div key={index} className="flex items-center justify-between p-2 bg-theatre-bg/50 rounded-lg">
            <span className="text-sm text-theatre-text">{impact.variable}</span>
            <span className={clsx(
              'text-sm font-medium',
              impact.change >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {impact.change >= 0 ? '+' : ''}{impact.change}
            </span>
          </div>
        ))}
      </div>
      
      <div className="mt-3 pt-3 border-t border-theatre-border/50 flex items-center justify-between">
        <span className="text-xs text-theatre-muted">故事线: {echo.thread_name}</span>
        <span className="text-xs text-theatre-muted">回声 #{echo.echo_id.slice(-4)}</span>
      </div>
    </div>
  );
}

// -------------------- 主页面 --------------------

export default function ExplainCardPage() {
  const { gateId } = useParams<{ gateId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [data, setData] = useState<ExplainCardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showEcho, setShowEcho] = useState(false);
  
  // 获取结算数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        // TODO: 调用真实API
        // const response = await fetch(`/v1/gates/${gateId}/explain`);
        // const data = await response.json();
        
        // 使用模拟数据
        await new Promise(resolve => setTimeout(resolve, 500));
        setData(mockExplainData);
      } catch (err) {
        console.error('获取结算数据失败:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, [gateId]);
  
  // 延迟显示回声
  useEffect(() => {
    if (data) {
      const timer = setTimeout(() => setShowEcho(true), 1500);
      return () => clearTimeout(timer);
    }
  }, [data]);
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-12 h-12 border-2 border-theatre-accent border-t-transparent rounded-full mx-auto mb-4"
          />
          <p className="text-theatre-muted">正在结算...</p>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-theatre-text mb-4">无法获取结算数据</p>
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
    <div className="min-h-screen bg-theatre-bg pb-24">
      {/* 头部 */}
      <header className="sticky top-0 z-40 bg-theatre-bg/80 backdrop-blur-lg border-b border-theatre-border">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 text-theatre-text"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">结算</span>
            </button>
            <button className="p-2 text-theatre-muted hover:text-theatre-text">
              <Share2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>
      
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* 门标题 */}
        <div className="text-center">
          <span className="text-xs px-2 py-1 rounded-full bg-theatre-accent/20 text-theatre-accent mb-2 inline-block">
            {data.gate_type === 'plot' ? '剧情门' : data.gate_type === 'lore' ? '设定门' : '元门'}
          </span>
          <h1 className="text-xl font-display font-bold text-theatre-text mb-2">
            {data.gate_title}
          </h1>
          <p className="text-theatre-muted">{data.gate_question}</p>
        </div>
        
        {/* 结果横幅 */}
        <ResultBanner
          isWinner={data.user_participation.is_winner}
          totalChange={data.rewards.total_change}
        />
        
        {/* 统计信息 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4 text-center">
            <Users className="w-5 h-5 text-theatre-muted mx-auto mb-1" />
            <p className="text-lg font-bold text-theatre-text">{data.total_participants}</p>
            <p className="text-xs text-theatre-muted">参与人数</p>
          </div>
          <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4 text-center">
            <Coins className="w-5 h-5 text-theatre-muted mx-auto mb-1" />
            <p className="text-lg font-bold text-theatre-text">{data.total_bets}</p>
            <p className="text-xs text-theatre-muted">总下注</p>
          </div>
        </div>
        
        {/* 选项结果 */}
        <div>
          <h3 className="text-sm font-medium text-theatre-muted mb-3">投票结果</h3>
          <div className="space-y-3">
            {data.options.map((option, index) => (
              <OptionResultCard
                key={option.option_id}
                option={option}
                userVoted={data.user_participation.voted_option_id === option.option_id}
                userBet={data.user_participation.bet_option_id === option.option_id}
              />
            ))}
          </div>
        </div>
        
        {/* 收益明细 */}
        <RewardsBreakdown rewards={data.rewards} />
        
        {/* 新获得的证物 */}
        {data.new_evidences.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-theatre-muted mb-3 flex items-center gap-2">
              <Gift className="w-4 h-4" />
              新获得的证物
            </h3>
            <div className="space-y-3">
              {data.new_evidences.map(evidence => (
                <NewEvidenceCard key={evidence.evidence_id} evidence={evidence} />
              ))}
            </div>
          </div>
        )}
        
        {/* 回声叙事 */}
        <AnimatePresence>
          {showEcho && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <h3 className="text-sm font-medium text-theatre-muted mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                回声
              </h3>
              <EchoNarrativeCard echo={data.echo} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
      
      {/* 底部操作栏 */}
      <div className="fixed bottom-0 left-0 right-0 bg-theatre-bg/80 backdrop-blur-lg border-t border-theatre-border p-4">
        <div className="max-w-2xl mx-auto flex gap-3">
          <button
            onClick={() => navigate('/archive')}
            className="flex-1 py-3 px-4 bg-theatre-surface border border-theatre-border rounded-xl text-theatre-text font-medium flex items-center justify-center gap-2"
          >
            <BookOpen className="w-5 h-5" />
            查看档案
          </button>
          <button
            onClick={() => navigate('/showbill')}
            className="flex-1 py-3 px-4 bg-theatre-accent text-theatre-bg rounded-xl font-medium flex items-center justify-center gap-2"
          >
            继续探索
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
