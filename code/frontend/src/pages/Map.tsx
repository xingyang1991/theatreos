// ============================================
// TheatreOS Map 地图页面
// ============================================

import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  MapPin,
  Navigation,
  Compass,
  ChevronRight,
  Clock,
  Users,
  Sparkles,
  Filter,
  List,
  Grid,
  Target,
  Zap,
  Eye,
  X,
  ExternalLink,
} from 'lucide-react';

// -------------------- 类型定义 --------------------

interface StageLocation {
  stage_id: string;
  name: string;
  hp_name: string;
  address: string;
  district: string;
  lat: number;
  lng: number;
  status: 'active' | 'upcoming' | 'ended' | 'rest';
  current_scene?: string;
  current_gate?: string;
  heat_level: number; // 0-100
  player_count: number;
  distance?: number; // 米
  has_event: boolean;
  event_name?: string;
  evidence_count: number; // 可收集的证物数量
}

interface MapRegion {
  region_id: string;
  name: string;
  stage_count: number;
  center_lat: number;
  center_lng: number;
}

interface MapData {
  stages: StageLocation[];
  regions: MapRegion[];
  user_location: { lat: number; lng: number } | null;
}

// -------------------- 模拟数据 --------------------

const mockMapData: MapData = {
  stages: [
    {
      stage_id: 'stage_xintiandi',
      name: '新天地',
      hp_name: '对角巷',
      address: '黄浦区新天地广场',
      district: '黄浦区',
      lat: 31.2195,
      lng: 121.4737,
      status: 'active',
      current_scene: '飞路粉商店的秘密交易',
      current_gate: '飞路粉的秘密',
      heat_level: 85,
      player_count: 47,
      distance: 1200,
      has_event: true,
      event_name: '黑市大搜查',
      evidence_count: 3,
    },
    {
      stage_id: 'stage_bund',
      name: '外滩',
      hp_name: '魔法部入口',
      address: '黄浦区中山东一路',
      district: '黄浦区',
      lat: 31.2400,
      lng: 121.4900,
      status: 'active',
      current_scene: '神秘信号追踪',
      heat_level: 72,
      player_count: 35,
      distance: 2500,
      has_event: false,
      evidence_count: 1,
    },
    {
      stage_id: 'stage_yuyuan',
      name: '豫园',
      hp_name: '古灵阁',
      address: '黄浦区豫园老街',
      district: '黄浦区',
      lat: 31.2275,
      lng: 121.4920,
      status: 'active',
      current_scene: '古老契约的解读',
      current_gate: '豫园的古老契约',
      heat_level: 68,
      player_count: 28,
      distance: 1800,
      has_event: false,
      evidence_count: 2,
    },
    {
      stage_id: 'stage_lujiazui',
      name: '陆家嘴',
      hp_name: '魔法部',
      address: '浦东新区陆家嘴环路',
      district: '浦东新区',
      lat: 31.2397,
      lng: 121.4998,
      status: 'active',
      current_scene: '预言厅的秘密',
      heat_level: 90,
      player_count: 62,
      distance: 3200,
      has_event: true,
      event_name: '预言厅开放',
      evidence_count: 4,
    },
    {
      stage_id: 'stage_jing_an',
      name: '静安寺',
      hp_name: '霍格沃茨',
      address: '静安区南京西路',
      district: '静安区',
      lat: 31.2235,
      lng: 121.4485,
      status: 'upcoming',
      heat_level: 45,
      player_count: 12,
      distance: 4500,
      has_event: false,
      evidence_count: 0,
    },
    {
      stage_id: 'stage_tianzifang',
      name: '田子坊',
      hp_name: '翻倒巷',
      address: '黄浦区泰康路',
      district: '黄浦区',
      lat: 31.2108,
      lng: 121.4680,
      status: 'active',
      current_scene: '黑市线人的情报',
      heat_level: 55,
      player_count: 19,
      distance: 2100,
      has_event: false,
      evidence_count: 2,
    },
    {
      stage_id: 'stage_nanjinglu',
      name: '南京路',
      hp_name: '破釜酒吧',
      address: '黄浦区南京东路',
      district: '黄浦区',
      lat: 31.2350,
      lng: 121.4750,
      status: 'active',
      current_scene: '酒吧里的窃窃私语',
      heat_level: 60,
      player_count: 24,
      distance: 1500,
      has_event: false,
      evidence_count: 1,
    },
    {
      stage_id: 'stage_french_concession',
      name: '法租界',
      hp_name: '格里莫广场',
      address: '徐汇区武康路',
      district: '徐汇区',
      lat: 31.2050,
      lng: 121.4450,
      status: 'rest',
      heat_level: 20,
      player_count: 5,
      distance: 5200,
      has_event: false,
      evidence_count: 0,
    },
  ],
  regions: [
    { region_id: 'huangpu', name: '黄浦区', stage_count: 5, center_lat: 31.2275, center_lng: 121.4800 },
    { region_id: 'pudong', name: '浦东新区', stage_count: 1, center_lat: 31.2397, center_lng: 121.4998 },
    { region_id: 'jingan', name: '静安区', stage_count: 1, center_lat: 31.2235, center_lng: 121.4485 },
    { region_id: 'xuhui', name: '徐汇区', stage_count: 1, center_lat: 31.2050, center_lng: 121.4450 },
  ],
  user_location: { lat: 31.2300, lng: 121.4700 },
};

// -------------------- 子组件 --------------------

// 状态标签
function StatusBadge({ status }: { status: StageLocation['status'] }) {
  const config = {
    active: { label: '进行中', color: 'bg-green-500', textColor: 'text-green-500' },
    upcoming: { label: '即将开始', color: 'bg-yellow-500', textColor: 'text-yellow-500' },
    ended: { label: '已结束', color: 'bg-slate-500', textColor: 'text-slate-500' },
    rest: { label: '休息中', color: 'bg-slate-600', textColor: 'text-slate-400' },
  };
  
  const c = config[status];
  
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full',
      `${c.color}/20`,
      c.textColor
    )}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', c.color)} />
      {c.label}
    </span>
  );
}

// 热度指示器
function HeatIndicator({ level }: { level: number }) {
  const getColor = () => {
    if (level >= 80) return 'bg-red-500';
    if (level >= 60) return 'bg-orange-500';
    if (level >= 40) return 'bg-yellow-500';
    return 'bg-slate-500';
  };
  
  return (
    <div className="flex items-center gap-1">
      <div className="w-16 h-1.5 bg-theatre-border rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all', getColor())}
          style={{ width: `${level}%` }}
        />
      </div>
      <span className="text-xs text-theatre-muted">{level}°</span>
    </div>
  );
}

// 舞台卡片（列表视图）
function StageCard({ stage, onClick }: { stage: StageLocation; onClick: () => void }) {
  const formatDistance = (meters?: number) => {
    if (!meters) return '未知';
    if (meters < 1000) return `${meters}m`;
    return `${(meters / 1000).toFixed(1)}km`;
  };
  
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      className={clsx(
        'w-full text-left bg-theatre-surface rounded-xl border p-4 transition-all',
        stage.has_event
          ? 'border-yellow-500/50 bg-gradient-to-br from-yellow-500/5 to-transparent'
          : 'border-theatre-border hover:border-theatre-accent/50'
      )}
    >
      <div className="flex items-start gap-3">
        {/* 左侧图标 */}
        <div className={clsx(
          'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
          stage.status === 'active' ? 'bg-theatre-accent/20' : 'bg-theatre-border'
        )}>
          <MapPin className={clsx(
            'w-6 h-6',
            stage.status === 'active' ? 'text-theatre-accent' : 'text-theatre-muted'
          )} />
        </div>
        
        {/* 中间内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-theatre-text">{stage.name}</h3>
            <span className="text-xs text-theatre-muted">({stage.hp_name})</span>
            <StatusBadge status={stage.status} />
          </div>
          
          {stage.current_scene && (
            <p className="text-sm text-theatre-muted mb-2 line-clamp-1">
              {stage.current_scene}
            </p>
          )}
          
          {stage.has_event && stage.event_name && (
            <div className="flex items-center gap-1 text-xs text-yellow-500 mb-2">
              <Zap className="w-3 h-3" />
              <span>{stage.event_name}</span>
            </div>
          )}
          
          <div className="flex items-center gap-4 text-xs text-theatre-muted">
            <span className="flex items-center gap-1">
              <Navigation className="w-3 h-3" />
              {formatDistance(stage.distance)}
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {stage.player_count}
            </span>
            {stage.evidence_count > 0 && (
              <span className="flex items-center gap-1 text-theatre-accent">
                <Target className="w-3 h-3" />
                {stage.evidence_count} 证物
              </span>
            )}
          </div>
        </div>
        
        {/* 右侧 */}
        <div className="flex flex-col items-end gap-2">
          <HeatIndicator level={stage.heat_level} />
          <ChevronRight className="w-5 h-5 text-theatre-muted" />
        </div>
      </div>
    </motion.button>
  );
}

// 舞台卡片（网格视图）
function StageGridCard({ stage, onClick }: { stage: StageLocation; onClick: () => void }) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        'text-left bg-theatre-surface rounded-xl border p-3 transition-all',
        stage.has_event
          ? 'border-yellow-500/50'
          : 'border-theatre-border hover:border-theatre-accent/50'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <StatusBadge status={stage.status} />
        {stage.has_event && <Zap className="w-4 h-4 text-yellow-500" />}
      </div>
      
      <h3 className="font-medium text-theatre-text mb-1">{stage.name}</h3>
      <p className="text-xs text-theatre-muted mb-2">{stage.hp_name}</p>
      
      <div className="flex items-center justify-between text-xs text-theatre-muted">
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          {stage.player_count}
        </span>
        <HeatIndicator level={stage.heat_level} />
      </div>
    </motion.button>
  );
}

// 区域筛选器
function RegionFilter({ 
  regions, 
  selectedRegion, 
  onSelect 
}: { 
  regions: MapRegion[]; 
  selectedRegion: string | null;
  onSelect: (regionId: string | null) => void;
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      <button
        onClick={() => onSelect(null)}
        className={clsx(
          'px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-all',
          selectedRegion === null
            ? 'bg-theatre-accent text-theatre-bg'
            : 'bg-theatre-surface border border-theatre-border text-theatre-muted'
        )}
      >
        全部
      </button>
      {regions.map(region => (
        <button
          key={region.region_id}
          onClick={() => onSelect(region.region_id)}
          className={clsx(
            'px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-all',
            selectedRegion === region.region_id
              ? 'bg-theatre-accent text-theatre-bg'
              : 'bg-theatre-surface border border-theatre-border text-theatre-muted'
          )}
        >
          {region.name} ({region.stage_count})
        </button>
      ))}
    </div>
  );
}

// 舞台详情弹窗
function StageDetailModal({ 
  stage, 
  onClose, 
  onNavigate 
}: { 
  stage: StageLocation; 
  onClose: () => void;
  onNavigate: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        onClick={e => e.stopPropagation()}
        className="w-full max-w-lg bg-theatre-surface rounded-t-2xl p-6"
      >
        {/* 头部 */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-xl font-display font-bold text-theatre-text">{stage.name}</h2>
              <StatusBadge status={stage.status} />
            </div>
            <p className="text-theatre-muted">{stage.hp_name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-theatre-muted hover:text-theatre-text"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* 地址 */}
        <div className="flex items-center gap-2 text-sm text-theatre-muted mb-4">
          <MapPin className="w-4 h-4" />
          <span>{stage.address}</span>
        </div>
        
        {/* 当前场景 */}
        {stage.current_scene && (
          <div className="bg-theatre-bg rounded-xl p-4 mb-4">
            <p className="text-xs text-theatre-muted mb-1">当前场景</p>
            <p className="text-theatre-text">{stage.current_scene}</p>
            {stage.current_gate && (
              <p className="text-sm text-theatre-accent mt-2">
                门: {stage.current_gate}
              </p>
            )}
          </div>
        )}
        
        {/* 事件 */}
        {stage.has_event && stage.event_name && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-4">
            <div className="flex items-center gap-2 text-yellow-500">
              <Zap className="w-5 h-5" />
              <span className="font-medium">{stage.event_name}</span>
            </div>
          </div>
        )}
        
        {/* 统计 */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="text-center p-3 bg-theatre-bg rounded-xl">
            <p className="text-lg font-bold text-theatre-text">{stage.player_count}</p>
            <p className="text-xs text-theatre-muted">在场玩家</p>
          </div>
          <div className="text-center p-3 bg-theatre-bg rounded-xl">
            <p className="text-lg font-bold text-theatre-text">{stage.heat_level}°</p>
            <p className="text-xs text-theatre-muted">热度</p>
          </div>
          <div className="text-center p-3 bg-theatre-bg rounded-xl">
            <p className="text-lg font-bold text-theatre-accent">{stage.evidence_count}</p>
            <p className="text-xs text-theatre-muted">可收集证物</p>
          </div>
        </div>
        
        {/* 操作按钮 */}
        <div className="flex gap-3">
          <button
            onClick={() => {
              // 打开地图导航
              const url = `https://uri.amap.com/marker?position=${stage.lng},${stage.lat}&name=${encodeURIComponent(stage.name)}`;
              window.open(url, '_blank');
            }}
            className="flex-1 py-3 px-4 bg-theatre-bg border border-theatre-border rounded-xl text-theatre-text font-medium flex items-center justify-center gap-2"
          >
            <Navigation className="w-5 h-5" />
            导航
          </button>
          <button
            onClick={onNavigate}
            className="flex-1 py-3 px-4 bg-theatre-accent text-theatre-bg rounded-xl font-medium flex items-center justify-center gap-2"
          >
            <Eye className="w-5 h-5" />
            进入舞台
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// 简易地图视图（使用CSS模拟）
function SimpleMapView({ 
  stages, 
  selectedStage,
  onStageClick 
}: { 
  stages: StageLocation[];
  selectedStage: string | null;
  onStageClick: (stage: StageLocation) => void;
}) {
  // 计算坐标范围
  const bounds = useMemo(() => {
    const lats = stages.map(s => s.lat);
    const lngs = stages.map(s => s.lng);
    return {
      minLat: Math.min(...lats) - 0.01,
      maxLat: Math.max(...lats) + 0.01,
      minLng: Math.min(...lngs) - 0.01,
      maxLng: Math.max(...lngs) + 0.01,
    };
  }, [stages]);
  
  const getPosition = (lat: number, lng: number) => {
    const x = ((lng - bounds.minLng) / (bounds.maxLng - bounds.minLng)) * 100;
    const y = ((bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat)) * 100;
    return { x, y };
  };
  
  return (
    <div className="relative w-full h-64 bg-theatre-surface rounded-xl border border-theatre-border overflow-hidden">
      {/* 网格背景 */}
      <div className="absolute inset-0 opacity-10">
        <svg width="100%" height="100%">
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="currentColor" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>
      
      {/* 舞台标记 */}
      {stages.map(stage => {
        const pos = getPosition(stage.lat, stage.lng);
        const isSelected = selectedStage === stage.stage_id;
        
        return (
          <motion.button
            key={stage.stage_id}
            onClick={() => onStageClick(stage)}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className={clsx(
              'absolute transform -translate-x-1/2 -translate-y-1/2 z-10',
              'w-8 h-8 rounded-full flex items-center justify-center',
              'transition-all cursor-pointer',
              isSelected
                ? 'bg-theatre-accent scale-125 ring-4 ring-theatre-accent/30'
                : stage.status === 'active'
                  ? 'bg-green-500'
                  : 'bg-theatre-muted'
            )}
            style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
          >
            <MapPin className="w-4 h-4 text-white" />
            {stage.has_event && (
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-500 rounded-full animate-pulse" />
            )}
          </motion.button>
        );
      })}
      
      {/* 图例 */}
      <div className="absolute bottom-2 left-2 flex items-center gap-3 text-xs text-theatre-muted">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          进行中
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-theatre-muted" />
          休息
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
          有事件
        </span>
      </div>
    </div>
  );
}

// -------------------- 主页面 --------------------

export default function MapPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightStageId = searchParams.get('highlight');
  
  const [data, setData] = useState<MapData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [selectedStage, setSelectedStage] = useState<StageLocation | null>(null);
  const [sortBy, setSortBy] = useState<'distance' | 'heat' | 'players'>('distance');
  
  // 获取数据
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        // TODO: 调用真实API
        await new Promise(resolve => setTimeout(resolve, 300));
        setData(mockMapData);
        
        // 如果有高亮舞台，自动选中
        if (highlightStageId) {
          const stage = mockMapData.stages.find(s => s.stage_id === highlightStageId);
          if (stage) {
            setSelectedStage(stage);
          }
        }
      } catch (err) {
        console.error('获取地图数据失败:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, [highlightStageId]);
  
  // 筛选和排序舞台
  const filteredStages = useMemo(() => {
    if (!data) return [];
    
    let stages = [...data.stages];
    
    // 区域筛选
    if (selectedRegion) {
      const region = data.regions.find(r => r.region_id === selectedRegion);
      if (region) {
        stages = stages.filter(s => s.district === region.name);
      }
    }
    
    // 排序
    stages.sort((a, b) => {
      switch (sortBy) {
        case 'distance':
          return (a.distance || 0) - (b.distance || 0);
        case 'heat':
          return b.heat_level - a.heat_level;
        case 'players':
          return b.player_count - a.player_count;
        default:
          return 0;
      }
    });
    
    return stages;
  }, [data, selectedRegion, sortBy]);
  
  const handleStageClick = (stage: StageLocation) => {
    setSelectedStage(stage);
  };
  
  const handleNavigateToStage = () => {
    if (selectedStage) {
      navigate(`/stage/${selectedStage.stage_id}`);
    }
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
          <p className="text-theatre-muted">加载地图中...</p>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
        <div className="text-center">
          <Compass className="w-16 h-16 text-theatre-muted mx-auto mb-4" />
          <p className="text-theatre-text mb-4">无法加载地图</p>
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
              <span className="font-display font-bold text-lg">城市地图</span>
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode(viewMode === 'list' ? 'grid' : 'list')}
                className="p-2 text-theatre-muted hover:text-theatre-text"
              >
                {viewMode === 'list' ? <Grid className="w-5 h-5" /> : <List className="w-5 h-5" />}
              </button>
            </div>
          </div>
          
          {/* 区域筛选 */}
          <RegionFilter
            regions={data.regions}
            selectedRegion={selectedRegion}
            onSelect={setSelectedRegion}
          />
        </div>
      </header>
      
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {/* 简易地图 */}
        <SimpleMapView
          stages={filteredStages}
          selectedStage={selectedStage?.stage_id || null}
          onStageClick={handleStageClick}
        />
        
        {/* 排序选项 */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-theatre-muted">
            {filteredStages.length} 个舞台
          </p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-theatre-muted">排序:</span>
            {(['distance', 'heat', 'players'] as const).map(sort => (
              <button
                key={sort}
                onClick={() => setSortBy(sort)}
                className={clsx(
                  'text-xs px-2 py-1 rounded-full transition-all',
                  sortBy === sort
                    ? 'bg-theatre-accent text-theatre-bg'
                    : 'text-theatre-muted hover:text-theatre-text'
                )}
              >
                {sort === 'distance' ? '距离' : sort === 'heat' ? '热度' : '人数'}
              </button>
            ))}
          </div>
        </div>
        
        {/* 舞台列表 */}
        <AnimatePresence mode="wait">
          {viewMode === 'list' ? (
            <motion.div
              key="list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              {filteredStages.map(stage => (
                <StageCard
                  key={stage.stage_id}
                  stage={stage}
                  onClick={() => handleStageClick(stage)}
                />
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="grid"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-2 gap-3"
            >
              {filteredStages.map(stage => (
                <StageGridCard
                  key={stage.stage_id}
                  stage={stage}
                  onClick={() => handleStageClick(stage)}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
      
      {/* 舞台详情弹窗 */}
      <AnimatePresence>
        {selectedStage && (
          <StageDetailModal
            stage={selectedStage}
            onClose={() => setSelectedStage(null)}
            onNavigate={handleNavigateToStage}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
