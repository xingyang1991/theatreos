// ============================================
// TheatreOS Archive 回声归档页面
// ============================================

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Trophy,
  TrendingUp,
  Clock,
  Filter,
  ChevronRight,
  Sparkles,
  Package,
  Target,
  BarChart3,
  Calendar,
  Coins,
  Star,
  CheckCircle,
  XCircle,
  Minus,
  Archive,
} from 'lucide-react';

// -------------------- 类型定义 --------------------

interface EchoRecord {
  echo_id: string;
  gate_id: string;
  gate_title: string;
  gate_type: 'plot' | 'lore' | 'meta';
  timestamp: string;
  result: 'win' | 'lose' | 'neutral';
  summary: string;
  thread_id: string;
  thread_name: string;
  tickets_change: number;
}

interface EvidenceItem {
  evidence_id: string;
  name: string;
  type: string;
  grade: 'common' | 'rare' | 'epic' | 'legendary';
  collected_at: string;
  from_gate: string;
}

interface ThreadProgress {
  thread_id: string;
  thread_name: string;
  progress: number;
  total_gates: number;
  completed_gates: number;
  key_moments: string[];
}

interface ArchiveStats {
  total_gates_participated: number;
  win_count: number;
  lose_count: number;
  win_rate: number;
  total_tickets_earned: number;
  total_evidences_collected: number;
  rare_evidences_count: number;
  favorite_thread: string;
  current_streak: number;
  best_streak: number;
}

interface ArchiveData {
  echoes: EchoRecord[];
  evidences: EvidenceItem[];
  thread_progress: ThreadProgress[];
  stats: ArchiveStats;
}

// -------------------- 模拟数据 --------------------

const mockArchiveData: ArchiveData = {
  echoes: [
    {
      echo_id: 'echo_001',
      gate_id: 'gate_001',
      gate_title: '飞路粉的秘密',
      gate_type: 'plot',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      result: 'win',
      summary: '蒙顿格斯的身份被揭露，飞路粉黑市即将面临整顿。',
      thread_id: 'thread_floo',
      thread_name: '飞路错拍线',
      tickets_change: 170,
    },
    {
      echo_id: 'echo_002',
      gate_id: 'gate_002',
      gate_title: '外滩的神秘信号',
      gate_type: 'lore',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      result: 'lose',
      summary: '信号来源仍是谜团，但线索指向了浦东方向。',
      thread_id: 'thread_ministry',
      thread_name: '魔法部暗线',
      tickets_change: -50,
    },
    {
      echo_id: 'echo_003',
      gate_id: 'gate_003',
      gate_title: '豫园的古老契约',
      gate_type: 'plot',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      result: 'win',
      summary: '契约的秘密被部分揭开，但更大的阴谋正在酝酿。',
      thread_id: 'thread_yuyuan',
      thread_name: '豫园秘契线',
      tickets_change: 85,
    },
    {
      echo_id: 'echo_004',
      gate_id: 'gate_004',
      gate_title: '陆家嘴的预言',
      gate_type: 'meta',
      timestamp: new Date(Date.now() - 172800000).toISOString(),
      result: 'neutral',
      summary: '预言的解读众说纷纭，真相仍在迷雾中。',
      thread_id: 'thread_prophecy',
      thread_name: '预言解读线',
      tickets_change: 10,
    },
  ],
  evidences: [
    {
      evidence_id: 'ev_001',
      name: '飞路粉配方残页',
      type: 'document',
      grade: 'rare',
      collected_at: new Date(Date.now() - 3600000).toISOString(),
      from_gate: '飞路粉的秘密',
    },
    {
      evidence_id: 'ev_002',
      name: '神秘的魔杖碎片',
      type: 'artifact',
      grade: 'epic',
      collected_at: new Date(Date.now() - 86400000).toISOString(),
      from_gate: '豫园的古老契约',
    },
    {
      evidence_id: 'ev_003',
      name: '外滩照片',
      type: 'photo',
      grade: 'common',
      collected_at: new Date(Date.now() - 7200000).toISOString(),
      from_gate: '外滩的神秘信号',
    },
    {
      evidence_id: 'ev_004',
      name: '古老的羊皮纸',
      type: 'document',
      grade: 'legendary',
      collected_at: new Date(Date.now() - 172800000).toISOString(),
      from_gate: '陆家嘴的预言',
    },
  ],
  thread_progress: [
    {
      thread_id: 'thread_floo',
      thread_name: '飞路错拍线',
      progress: 65,
      total_gates: 8,
      completed_gates: 5,
      key_moments: ['发现飞路粉异常', '追踪到翻倒巷', '揭露蒙顿格斯'],
    },
    {
      thread_id: 'thread_ministry',
      thread_name: '魔法部暗线',
      progress: 30,
      total_gates: 10,
      completed_gates: 3,
      key_moments: ['外滩信号', '浦东线索'],
    },
    {
      thread_id: 'thread_yuyuan',
      thread_name: '豫园秘契线',
      progress: 45,
      total_gates: 6,
      completed_gates: 3,
      key_moments: ['发现契约', '解读部分内容'],
    },
    {
      thread_id: 'thread_prophecy',
      thread_name: '预言解读线',
      progress: 15,
      total_gates: 12,
      completed_gates: 2,
      key_moments: ['首次预言'],
    },
  ],
  stats: {
    total_gates_participated: 13,
    win_count: 8,
    lose_count: 4,
    win_rate: 61.5,
    total_tickets_earned: 1250,
    total_evidences_collected: 24,
    rare_evidences_count: 6,
    favorite_thread: '飞路错拍线',
    current_streak: 2,
    best_streak: 5,
  },
};

// -------------------- 子组件 --------------------

// Tab切换
type TabType = 'echoes' | 'evidences' | 'threads' | 'stats';

function TabBar({ activeTab, onTabChange }: { activeTab: TabType; onTabChange: (tab: TabType) => void }) {
  const tabs: { id: TabType; label: string; icon: React.ElementType }[] = [
    { id: 'echoes', label: '回声', icon: Sparkles },
    { id: 'evidences', label: '证物', icon: Package },
    { id: 'threads', label: '故事线', icon: Target },
    { id: 'stats', label: '统计', icon: BarChart3 },
  ];
  
  return (
    <div className="flex bg-theatre-surface rounded-xl p-1 border border-theatre-border">
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={clsx(
            'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-1.5',
            activeTab === tab.id
              ? 'bg-theatre-accent text-theatre-bg'
              : 'text-theatre-muted hover:text-theatre-text'
          )}
        >
          <tab.icon className="w-4 h-4" />
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}

// 回声记录卡片
function EchoCard({ echo, onClick }: { echo: EchoRecord; onClick: () => void }) {
  const resultConfig = {
    win: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' },
    lose: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
    neutral: { icon: Minus, color: 'text-slate-400', bg: 'bg-slate-500/10' },
  };
  
  const config = resultConfig[echo.result];
  const ResultIcon = config.icon;
  
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return `${Math.floor(diff / 86400000)} 天前`;
  };
  
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className="w-full text-left bg-theatre-surface rounded-xl border border-theatre-border p-4 transition-all hover:border-theatre-accent/50"
    >
      <div className="flex items-start gap-3">
        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', config.bg)}>
          <ResultIcon className={clsx('w-5 h-5', config.color)} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-2 py-0.5 rounded-full bg-theatre-accent/20 text-theatre-accent">
              {echo.gate_type === 'plot' ? '剧情' : echo.gate_type === 'lore' ? '设定' : '元'}
            </span>
            <span className="text-xs text-theatre-muted">{echo.thread_name}</span>
          </div>
          
          <h3 className="font-medium text-theatre-text mb-1 truncate">{echo.gate_title}</h3>
          <p className="text-sm text-theatre-muted line-clamp-2">{echo.summary}</p>
          
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-theatre-muted flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTime(echo.timestamp)}
            </span>
            <span className={clsx(
              'text-sm font-medium',
              echo.tickets_change >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {echo.tickets_change >= 0 ? '+' : ''}{echo.tickets_change}
            </span>
          </div>
        </div>
        
        <ChevronRight className="w-5 h-5 text-theatre-muted flex-shrink-0" />
      </div>
    </motion.button>
  );
}

// 证物卡片
function EvidenceCard({ evidence }: { evidence: EvidenceItem }) {
  const gradeConfig = {
    common: { label: '普通', color: 'text-slate-400', border: 'border-slate-500/30', bg: 'bg-slate-500/10' },
    rare: { label: '稀有', color: 'text-blue-400', border: 'border-blue-500/30', bg: 'bg-blue-500/10' },
    epic: { label: '史诗', color: 'text-purple-400', border: 'border-purple-500/30', bg: 'bg-purple-500/10' },
    legendary: { label: '传说', color: 'text-yellow-400', border: 'border-yellow-500/30', bg: 'bg-yellow-500/10' },
  };
  
  const config = gradeConfig[evidence.grade];
  
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className={clsx(
        'p-4 rounded-xl border transition-all',
        config.border,
        config.bg
      )}
    >
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-lg bg-theatre-bg/50 flex items-center justify-center">
          <FileText className={clsx('w-6 h-6', config.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={clsx('text-xs font-medium', config.color)}>{config.label}</span>
            <span className="text-xs text-theatre-muted">{evidence.type}</span>
          </div>
          <h4 className="font-medium text-theatre-text truncate">{evidence.name}</h4>
          <p className="text-xs text-theatre-muted mt-1">来自: {evidence.from_gate}</p>
        </div>
      </div>
    </motion.div>
  );
}

// 故事线进度卡片
function ThreadProgressCard({ thread, onClick }: { thread: ThreadProgress; onClick: () => void }) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className="w-full text-left bg-theatre-surface rounded-xl border border-theatre-border p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-theatre-text">{thread.thread_name}</h3>
        <span className="text-sm text-theatre-accent font-medium">{thread.progress}%</span>
      </div>
      
      {/* 进度条 */}
      <div className="h-2 bg-theatre-border rounded-full overflow-hidden mb-3">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${thread.progress}%` }}
          transition={{ duration: 0.5 }}
          className="h-full bg-gradient-to-r from-theatre-accent to-purple-500 rounded-full"
        />
      </div>
      
      <div className="flex items-center justify-between text-sm">
        <span className="text-theatre-muted">
          {thread.completed_gates} / {thread.total_gates} 门
        </span>
        <div className="flex items-center gap-1 text-theatre-muted">
          <span>查看详情</span>
          <ChevronRight className="w-4 h-4" />
        </div>
      </div>
      
      {/* 关键时刻 */}
      {thread.key_moments.length > 0 && (
        <div className="mt-3 pt-3 border-t border-theatre-border">
          <p className="text-xs text-theatre-muted mb-2">关键时刻</p>
          <div className="flex flex-wrap gap-1">
            {thread.key_moments.slice(0, 3).map((moment, index) => (
              <span
                key={index}
                className="text-xs px-2 py-1 bg-theatre-bg rounded-full text-theatre-text"
              >
                {moment}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.button>
  );
}

// 统计面板
function StatsPanel({ stats }: { stats: ArchiveStats }) {
  const statItems = [
    { label: '参与门数', value: stats.total_gates_participated, icon: Target },
    { label: '胜率', value: `${stats.win_rate}%`, icon: Trophy },
    { label: '总收益', value: stats.total_tickets_earned, icon: Coins },
    { label: '证物收集', value: stats.total_evidences_collected, icon: Package },
    { label: '稀有证物', value: stats.rare_evidences_count, icon: Star },
    { label: '当前连胜', value: stats.current_streak, icon: TrendingUp },
  ];
  
  return (
    <div className="space-y-4">
      {/* 主要统计 */}
      <div className="grid grid-cols-2 gap-3">
        {statItems.map((item, index) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-theatre-surface rounded-xl border border-theatre-border p-4"
          >
            <item.icon className="w-5 h-5 text-theatre-accent mb-2" />
            <p className="text-2xl font-bold text-theatre-text">{item.value}</p>
            <p className="text-xs text-theatre-muted">{item.label}</p>
          </motion.div>
        ))}
      </div>
      
      {/* 胜负统计 */}
      <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4">
        <h3 className="text-sm font-medium text-theatre-muted mb-3">胜负记录</h3>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-green-500">胜</span>
              <span className="text-green-500 font-medium">{stats.win_count}</span>
            </div>
            <div className="h-2 bg-theatre-border rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full"
                style={{ width: `${(stats.win_count / stats.total_gates_participated) * 100}%` }}
              />
            </div>
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-red-500">负</span>
              <span className="text-red-500 font-medium">{stats.lose_count}</span>
            </div>
            <div className="h-2 bg-theatre-border rounded-full overflow-hidden">
              <div
                className="h-full bg-red-500 rounded-full"
                style={{ width: `${(stats.lose_count / stats.total_gates_participated) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>
      
      {/* 最爱故事线 */}
      <div className="bg-gradient-to-br from-theatre-accent/10 to-purple-500/10 rounded-xl border border-theatre-accent/30 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Star className="w-5 h-5 text-theatre-accent" />
          <span className="text-sm text-theatre-muted">最爱故事线</span>
        </div>
        <p className="text-lg font-bold text-theatre-text">{stats.favorite_thread}</p>
      </div>
      
      {/* 最佳连胜 */}
      <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-theatre-muted mb-1">最佳连胜</p>
            <p className="text-2xl font-bold text-theatre-text">{stats.best_streak} 连胜</p>
          </div>
          <Trophy className="w-10 h-10 text-yellow-500" />
        </div>
      </div>
    </div>
  );
}

// -------------------- 主页面 --------------------

export default function ArchivePage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('echoes');
  const [data, setData] = useState<ArchiveData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);
  
  // 获取档案数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        // TODO: 调用真实API
        // const response = await fetch('/v1/users/me/archive');
        // const data = await response.json();
        
        // 使用模拟数据
        await new Promise(resolve => setTimeout(resolve, 300));
        setData(mockArchiveData);
      } catch (err) {
        console.error('获取档案数据失败:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-12 h-12 border-2 border-theatre-accent border-t-transparent rounded-full mx-auto mb-4"
          />
          <p className="text-theatre-muted">加载档案中...</p>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
        <div className="text-center">
          <BookOpen className="w-16 h-16 text-theatre-muted mx-auto mb-4" />
          <p className="text-theatre-text mb-2">暂无档案记录</p>
          <p className="text-theatre-muted text-sm mb-4">参与门的投票和下注后，记录会出现在这里</p>
          <button
            onClick={() => navigate('/showbill')}
            className="px-4 py-2 bg-theatre-accent text-theatre-bg rounded-lg"
          >
            去探索
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-theatre-bg pb-20">
      {/* 头部 */}
      <header className="sticky top-0 z-40 bg-theatre-bg/80 backdrop-blur-lg border-b border-theatre-border">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 text-theatre-text"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-display font-bold text-lg">我的档案</span>
            </button>
            <button className="p-2 text-theatre-muted hover:text-theatre-text">
              <Filter className="w-5 h-5" />
            </button>
          </div>
          
          {/* Tab切换 */}
          <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </header>
      
      <main className="max-w-2xl mx-auto px-4 py-6">
        <AnimatePresence mode="wait">
          {/* 回声列表 */}
          {activeTab === 'echoes' && (
            <motion.div
              key="echoes"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {data.echoes.length === 0 ? (
                <div className="text-center py-12">
                  <Sparkles className="w-12 h-12 text-theatre-muted mx-auto mb-3" />
                  <p className="text-theatre-muted">暂无回声记录</p>
                </div>
              ) : (
                data.echoes.map(echo => (
                  <EchoCard
                    key={echo.echo_id}
                    echo={echo}
                    onClick={() => navigate(`/explain/${echo.gate_id}`)}
                  />
                ))
              )}
            </motion.div>
          )}
          
          {/* 证物收集 */}
          {activeTab === 'evidences' && (
            <motion.div
              key="evidences"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              {/* 收集进度 */}
              <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-theatre-muted">收集进度</span>
                  <span className="text-sm text-theatre-accent font-medium">
                    {data.stats.total_evidences_collected} / 74
                  </span>
                </div>
                <div className="h-2 bg-theatre-border rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-theatre-accent to-purple-500 rounded-full"
                    style={{ width: `${(data.stats.total_evidences_collected / 74) * 100}%` }}
                  />
                </div>
              </div>
              
              {/* 证物网格 */}
              <div className="grid grid-cols-1 gap-3">
                {data.evidences.map(evidence => (
                  <EvidenceCard key={evidence.evidence_id} evidence={evidence} />
                ))}
              </div>
            </motion.div>
          )}
          
          {/* 故事线进度 */}
          {activeTab === 'threads' && (
            <motion.div
              key="threads"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {data.thread_progress.map(thread => (
                <ThreadProgressCard
                  key={thread.thread_id}
                  thread={thread}
                  onClick={() => {/* TODO: 跳转到故事线详情 */}}
                />
              ))}
            </motion.div>
          )}
          
          {/* 统计面板 */}
          {activeTab === 'stats' && (
            <motion.div
              key="stats"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <StatsPanel stats={data.stats} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
