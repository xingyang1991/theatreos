// ============================================
// TheatreOS Crew 剧团/追证页面
// ============================================

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Users,
  Plus,
  Trophy,
  Target,
  MapPin,
  Clock,
  ChevronRight,
  Search,
  Crown,
  UserPlus,
  Settings,
  Bell,
  Gift,
  Compass,
  Sparkles,
  AlertCircle,
  CheckCircle,
  Star,
  Zap,
} from 'lucide-react';

// -------------------- 类型定义 --------------------

interface CrewMember {
  user_id: string;
  username: string;
  avatar?: string;
  ring: 'brass' | 'silver' | 'gold' | 'platinum';
  role: 'leader' | 'officer' | 'member';
  contribution: number;
  online: boolean;
}

interface MyCrew {
  crew_id: string;
  name: string;
  motto: string;
  level: number;
  exp: number;
  exp_to_next: number;
  members: CrewMember[];
  max_members: number;
  active_missions: number;
  total_wins: number;
  weekly_rank: number;
}

interface EvidenceHunt {
  hunt_id: string;
  title: string;
  description: string;
  target_evidence_type: string;
  target_evidence_name: string;
  hint: string;
  related_stage_id: string;
  related_stage_name: string;
  related_thread: string;
  progress: number;
  total_steps: number;
  completed_steps: number;
  reward_tickets: number;
  reward_evidence_grade: 'rare' | 'epic' | 'legendary';
  expires_at: string;
  difficulty: 'easy' | 'medium' | 'hard';
  participants: number;
}

interface RevisitSuggestion {
  suggestion_id: string;
  stage_id: string;
  stage_name: string;
  stage_hp_name: string;
  reason: string;
  reason_type: 'evidence' | 'story' | 'event' | 'crew';
  priority: 'high' | 'medium' | 'low';
  evidence_hint?: string;
  event_time?: string;
}

interface CrewData {
  my_crew: MyCrew | null;
  evidence_hunts: EvidenceHunt[];
  revisit_suggestions: RevisitSuggestion[];
  available_crews: { crew_id: string; name: string; members: number; level: number }[];
}

// -------------------- 模拟数据 --------------------

const mockCrewData: CrewData = {
  my_crew: {
    crew_id: 'crew_001',
    name: '凤凰社上海分部',
    motto: '在黑暗中寻找光明',
    level: 5,
    exp: 2350,
    exp_to_next: 3000,
    members: [
      { user_id: 'u1', username: '邓布利多的信使', ring: 'gold', role: 'leader', contribution: 1250, online: true },
      { user_id: 'u2', username: '外滩守望者', ring: 'silver', role: 'officer', contribution: 890, online: true },
      { user_id: 'u3', username: '豫园探秘人', ring: 'silver', role: 'member', contribution: 650, online: false },
      { user_id: 'u4', username: '陆家嘴预言师', ring: 'brass', role: 'member', contribution: 420, online: false },
    ],
    max_members: 10,
    active_missions: 3,
    total_wins: 47,
    weekly_rank: 12,
  },
  evidence_hunts: [
    {
      hunt_id: 'hunt_001',
      title: '追踪飞路粉源头',
      description: '蒙顿格斯被捕后，他的供应商仍在逍遥法外。追踪线索，找到真正的幕后黑手。',
      target_evidence_type: 'document',
      target_evidence_name: '飞路粉进货单',
      hint: '新天地的某个角落可能藏有线索...',
      related_stage_id: 'stage_xintiandi',
      related_stage_name: '新天地',
      related_thread: '飞路错拍线',
      progress: 60,
      total_steps: 5,
      completed_steps: 3,
      reward_tickets: 200,
      reward_evidence_grade: 'epic',
      expires_at: new Date(Date.now() + 86400000 * 2).toISOString(),
      difficulty: 'medium',
      participants: 156,
    },
    {
      hunt_id: 'hunt_002',
      title: '解读古老预言',
      description: '陆家嘴发现的预言碎片需要更多线索才能完整解读。',
      target_evidence_type: 'artifact',
      target_evidence_name: '预言水晶碎片',
      hint: '东方明珠附近的魔法波动异常强烈...',
      related_stage_id: 'stage_lujiazui',
      related_stage_name: '陆家嘴',
      related_thread: '预言解读线',
      progress: 25,
      total_steps: 8,
      completed_steps: 2,
      reward_tickets: 350,
      reward_evidence_grade: 'legendary',
      expires_at: new Date(Date.now() + 86400000 * 5).toISOString(),
      difficulty: 'hard',
      participants: 89,
    },
    {
      hunt_id: 'hunt_003',
      title: '外滩信号追踪',
      description: '神秘信号的来源已经锁定在浦东方向，需要实地调查。',
      target_evidence_type: 'photo',
      target_evidence_name: '信号源照片',
      hint: '在外滩观景台可以看到一些异常...',
      related_stage_id: 'stage_bund',
      related_stage_name: '外滩',
      related_thread: '魔法部暗线',
      progress: 80,
      total_steps: 4,
      completed_steps: 3,
      reward_tickets: 150,
      reward_evidence_grade: 'rare',
      expires_at: new Date(Date.now() + 86400000).toISOString(),
      difficulty: 'easy',
      participants: 234,
    },
  ],
  revisit_suggestions: [
    {
      suggestion_id: 'sug_001',
      stage_id: 'stage_xintiandi',
      stage_name: '新天地',
      stage_hp_name: '对角巷',
      reason: '有3件未收集的证物等待发现',
      reason_type: 'evidence',
      priority: 'high',
      evidence_hint: '飞路粉相关线索',
    },
    {
      suggestion_id: 'sug_002',
      stage_id: 'stage_yuyuan',
      stage_name: '豫园',
      stage_hp_name: '古灵阁',
      reason: '豫园秘契线有新的剧情发展',
      reason_type: 'story',
      priority: 'medium',
    },
    {
      suggestion_id: 'sug_003',
      stage_id: 'stage_lujiazui',
      stage_name: '陆家嘴',
      stage_hp_name: '魔法部',
      reason: '限时事件：预言厅开放',
      reason_type: 'event',
      priority: 'high',
      event_time: '今晚 20:00',
    },
    {
      suggestion_id: 'sug_004',
      stage_id: 'stage_bund',
      stage_name: '外滩',
      stage_hp_name: '魔法部入口',
      reason: '剧团任务目标地点',
      reason_type: 'crew',
      priority: 'medium',
    },
  ],
  available_crews: [
    { crew_id: 'crew_002', name: '格兰芬多勇士', members: 8, level: 7 },
    { crew_id: 'crew_003', name: '斯莱特林密探', members: 6, level: 4 },
    { crew_id: 'crew_004', name: '拉文克劳学者', members: 5, level: 3 },
  ],
};

// -------------------- 子组件 --------------------

// Tab切换
type TabType = 'crew' | 'hunts' | 'revisit';

function TabBar({ activeTab, onTabChange }: { activeTab: TabType; onTabChange: (tab: TabType) => void }) {
  const tabs: { id: TabType; label: string; icon: React.ElementType }[] = [
    { id: 'crew', label: '我的剧团', icon: Users },
    { id: 'hunts', label: '追证任务', icon: Target },
    { id: 'revisit', label: '复访建议', icon: Compass },
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

// 剧团成员卡片
function MemberCard({ member }: { member: CrewMember }) {
  const ringColors = {
    brass: 'text-amber-600',
    silver: 'text-slate-400',
    gold: 'text-yellow-500',
    platinum: 'text-purple-400',
  };
  
  const roleIcons = {
    leader: Crown,
    officer: Star,
    member: Users,
  };
  
  const RoleIcon = roleIcons[member.role];
  
  return (
    <div className="flex items-center gap-3 p-3 bg-theatre-bg rounded-lg">
      <div className="relative">
        <div className="w-10 h-10 rounded-full bg-theatre-surface flex items-center justify-center">
          <span className="text-lg">{member.username.charAt(0)}</span>
        </div>
        {member.online && (
          <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full border-2 border-theatre-bg" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-theatre-text truncate">{member.username}</span>
          <RoleIcon className={clsx('w-4 h-4', member.role === 'leader' ? 'text-yellow-500' : 'text-theatre-muted')} />
        </div>
        <div className="flex items-center gap-2 text-xs text-theatre-muted">
          <span className={ringColors[member.ring]}>{member.ring.toUpperCase()}</span>
          <span>·</span>
          <span>贡献 {member.contribution}</span>
        </div>
      </div>
    </div>
  );
}

// 剧团面板
function CrewPanel({ crew }: { crew: MyCrew }) {
  return (
    <div className="space-y-4">
      {/* 剧团信息卡 */}
      <div className="bg-gradient-to-br from-theatre-accent/10 to-purple-500/10 rounded-xl border border-theatre-accent/30 p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-xl font-display font-bold text-theatre-text">{crew.name}</h2>
            <p className="text-sm text-theatre-muted italic">"{crew.motto}"</p>
          </div>
          <button className="p-2 text-theatre-muted hover:text-theatre-text">
            <Settings className="w-5 h-5" />
          </button>
        </div>
        
        {/* 等级进度 */}
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-theatre-muted">Lv.{crew.level}</span>
            <span className="text-theatre-accent">{crew.exp} / {crew.exp_to_next}</span>
          </div>
          <div className="h-2 bg-theatre-border rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-theatre-accent to-purple-500 rounded-full"
              style={{ width: `${(crew.exp / crew.exp_to_next) * 100}%` }}
            />
          </div>
        </div>
        
        {/* 统计 */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-2 bg-theatre-bg/50 rounded-lg">
            <p className="text-lg font-bold text-theatre-text">{crew.members.length}/{crew.max_members}</p>
            <p className="text-xs text-theatre-muted">成员</p>
          </div>
          <div className="text-center p-2 bg-theatre-bg/50 rounded-lg">
            <p className="text-lg font-bold text-theatre-text">{crew.total_wins}</p>
            <p className="text-xs text-theatre-muted">总胜场</p>
          </div>
          <div className="text-center p-2 bg-theatre-bg/50 rounded-lg">
            <p className="text-lg font-bold text-theatre-text">#{crew.weekly_rank}</p>
            <p className="text-xs text-theatre-muted">周榜</p>
          </div>
        </div>
      </div>
      
      {/* 成员列表 */}
      <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-theatre-text">成员 ({crew.members.length})</h3>
          <button className="flex items-center gap-1 text-sm text-theatre-accent">
            <UserPlus className="w-4 h-4" />
            <span>邀请</span>
          </button>
        </div>
        <div className="space-y-2">
          {crew.members.map(member => (
            <MemberCard key={member.user_id} member={member} />
          ))}
        </div>
      </div>
    </div>
  );
}

// 无剧团状态
function NoCrewPanel({ availableCrews, onCreateCrew }: { 
  availableCrews: CrewData['available_crews']; 
  onCreateCrew: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="text-center py-8">
        <Users className="w-16 h-16 text-theatre-muted mx-auto mb-4" />
        <h2 className="text-xl font-display font-bold text-theatre-text mb-2">加入或创建剧团</h2>
        <p className="text-theatre-muted mb-6">与志同道合的伙伴一起探索魔法世界</p>
        <button
          onClick={onCreateCrew}
          className="px-6 py-3 bg-theatre-accent text-theatre-bg rounded-xl font-medium flex items-center gap-2 mx-auto"
        >
          <Plus className="w-5 h-5" />
          创建剧团
        </button>
      </div>
      
      {/* 推荐剧团 */}
      <div className="bg-theatre-surface rounded-xl border border-theatre-border p-4">
        <h3 className="font-medium text-theatre-text mb-3">推荐剧团</h3>
        <div className="space-y-2">
          {availableCrews.map(crew => (
            <button
              key={crew.crew_id}
              className="w-full flex items-center justify-between p-3 bg-theatre-bg rounded-lg hover:bg-theatre-border/50 transition-colors"
            >
              <div>
                <p className="font-medium text-theatre-text">{crew.name}</p>
                <p className="text-xs text-theatre-muted">Lv.{crew.level} · {crew.members} 成员</p>
              </div>
              <ChevronRight className="w-5 h-5 text-theatre-muted" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// 追证任务卡片
function HuntCard({ hunt, onClick }: { hunt: EvidenceHunt; onClick: () => void }) {
  const difficultyConfig = {
    easy: { label: '简单', color: 'text-green-500', bg: 'bg-green-500/10' },
    medium: { label: '中等', color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
    hard: { label: '困难', color: 'text-red-500', bg: 'bg-red-500/10' },
  };
  
  const gradeConfig = {
    rare: { label: '稀有', color: 'text-blue-400' },
    epic: { label: '史诗', color: 'text-purple-400' },
    legendary: { label: '传说', color: 'text-yellow-400' },
  };
  
  const config = difficultyConfig[hunt.difficulty];
  const rewardConfig = gradeConfig[hunt.reward_evidence_grade];
  
  // 计算剩余时间
  const getTimeRemaining = () => {
    const diff = new Date(hunt.expires_at).getTime() - Date.now();
    if (diff <= 0) return '已过期';
    const hours = Math.floor(diff / 3600000);
    if (hours < 24) return `${hours} 小时`;
    return `${Math.floor(hours / 24)} 天`;
  };
  
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className="w-full text-left bg-theatre-surface rounded-xl border border-theatre-border p-4"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={clsx('text-xs px-2 py-0.5 rounded-full', config.bg, config.color)}>
            {config.label}
          </span>
          <span className="text-xs text-theatre-muted">{hunt.related_thread}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-theatre-muted">
          <Clock className="w-3 h-3" />
          <span>{getTimeRemaining()}</span>
        </div>
      </div>
      
      <h3 className="font-medium text-theatre-text mb-1">{hunt.title}</h3>
      <p className="text-sm text-theatre-muted mb-3 line-clamp-2">{hunt.description}</p>
      
      {/* 进度条 */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-theatre-muted">进度 {hunt.completed_steps}/{hunt.total_steps}</span>
          <span className="text-theatre-accent">{hunt.progress}%</span>
        </div>
        <div className="h-2 bg-theatre-border rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-theatre-accent to-purple-500 rounded-full"
            style={{ width: `${hunt.progress}%` }}
          />
        </div>
      </div>
      
      {/* 提示 */}
      <div className="p-2 bg-theatre-bg rounded-lg mb-3">
        <p className="text-xs text-theatre-muted">
          <span className="text-theatre-accent">提示:</span> {hunt.hint}
        </p>
      </div>
      
      {/* 底部信息 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-theatre-muted">
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {hunt.related_stage_name}
          </span>
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" />
            {hunt.participants} 人参与
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-theatre-accent">+{hunt.reward_tickets}</span>
          <span className={clsx('text-xs', rewardConfig.color)}>{rewardConfig.label}证物</span>
        </div>
      </div>
    </motion.button>
  );
}

// 复访建议卡片
function RevisitCard({ suggestion, onClick }: { suggestion: RevisitSuggestion; onClick: () => void }) {
  const typeConfig = {
    evidence: { icon: Target, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    story: { icon: Sparkles, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    event: { icon: Zap, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
    crew: { icon: Users, color: 'text-green-400', bg: 'bg-green-500/10' },
  };
  
  const priorityConfig = {
    high: { label: '高优先', color: 'text-red-500' },
    medium: { label: '中优先', color: 'text-yellow-500' },
    low: { label: '低优先', color: 'text-slate-400' },
  };
  
  const config = typeConfig[suggestion.reason_type];
  const TypeIcon = config.icon;
  
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className="w-full text-left bg-theatre-surface rounded-xl border border-theatre-border p-4"
    >
      <div className="flex items-start gap-3">
        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', config.bg)}>
          <TypeIcon className={clsx('w-5 h-5', config.color)} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-theatre-text">{suggestion.stage_name}</h3>
            <span className="text-xs text-theatre-muted">({suggestion.stage_hp_name})</span>
          </div>
          
          <p className="text-sm text-theatre-muted mb-2">{suggestion.reason}</p>
          
          {suggestion.evidence_hint && (
            <p className="text-xs text-theatre-accent">
              线索: {suggestion.evidence_hint}
            </p>
          )}
          
          {suggestion.event_time && (
            <p className="text-xs text-yellow-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {suggestion.event_time}
            </p>
          )}
        </div>
        
        <div className="flex flex-col items-end gap-2">
          <span className={clsx('text-xs', priorityConfig[suggestion.priority].color)}>
            {priorityConfig[suggestion.priority].label}
          </span>
          <ChevronRight className="w-5 h-5 text-theatre-muted" />
        </div>
      </div>
    </motion.button>
  );
}

// -------------------- 主页面 --------------------

export default function CrewPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('crew');
  const [data, setData] = useState<CrewData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // 获取数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        // TODO: 调用真实API
        await new Promise(resolve => setTimeout(resolve, 300));
        setData(mockCrewData);
      } catch (err) {
        console.error('获取剧团数据失败:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  const handleCreateCrew = () => {
    // TODO: 打开创建剧团对话框
    console.log('创建剧团');
  };
  
  const handleHuntClick = (hunt: EvidenceHunt) => {
    // 跳转到相关舞台
    navigate(`/map?highlight=${hunt.related_stage_id}`);
  };
  
  const handleRevisitClick = (suggestion: RevisitSuggestion) => {
    // 跳转到舞台
    navigate(`/stage/${suggestion.stage_id}`);
  };
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center">
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-12 h-12 border-2 border-theatre-accent border-t-transparent rounded-full mx-auto mb-4"
          />
          <p className="text-theatre-muted">加载中...</p>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-theatre-muted mx-auto mb-4" />
          <p className="text-theatre-text mb-4">加载失败</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-theatre-accent text-theatre-bg rounded-lg"
          >
            重试
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
              <span className="font-display font-bold text-lg">剧团</span>
            </button>
            <button className="p-2 text-theatre-muted hover:text-theatre-text">
              <Bell className="w-5 h-5" />
            </button>
          </div>
          
          {/* Tab切换 */}
          <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </header>
      
      <main className="max-w-2xl mx-auto px-4 py-6">
        <AnimatePresence mode="wait">
          {/* 我的剧团 */}
          {activeTab === 'crew' && (
            <motion.div
              key="crew"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              {data.my_crew ? (
                <CrewPanel crew={data.my_crew} />
              ) : (
                <NoCrewPanel
                  availableCrews={data.available_crews}
                  onCreateCrew={handleCreateCrew}
                />
              )}
            </motion.div>
          )}
          
          {/* 追证任务 */}
          {activeTab === 'hunts' && (
            <motion.div
              key="hunts"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {data.evidence_hunts.length === 0 ? (
                <div className="text-center py-12">
                  <Target className="w-12 h-12 text-theatre-muted mx-auto mb-3" />
                  <p className="text-theatre-muted">暂无追证任务</p>
                </div>
              ) : (
                data.evidence_hunts.map(hunt => (
                  <HuntCard
                    key={hunt.hunt_id}
                    hunt={hunt}
                    onClick={() => handleHuntClick(hunt)}
                  />
                ))
              )}
            </motion.div>
          )}
          
          {/* 复访建议 */}
          {activeTab === 'revisit' && (
            <motion.div
              key="revisit"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {data.revisit_suggestions.length === 0 ? (
                <div className="text-center py-12">
                  <Compass className="w-12 h-12 text-theatre-muted mx-auto mb-3" />
                  <p className="text-theatre-muted">暂无复访建议</p>
                </div>
              ) : (
                <>
                  <p className="text-sm text-theatre-muted mb-2">
                    根据您的进度和当前事件，推荐以下舞台复访
                  </p>
                  {data.revisit_suggestions.map(suggestion => (
                    <RevisitCard
                      key={suggestion.suggestion_id}
                      suggestion={suggestion}
                      onClick={() => handleRevisitClick(suggestion)}
                    />
                  ))}
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
