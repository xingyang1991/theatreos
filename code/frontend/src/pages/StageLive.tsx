// ============================================
// TheatreOS Stage Live 沉浸式观看页面
// ============================================

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Volume2,
  VolumeX,
  Maximize,
  Minimize,
  Gift,
  Share2,
  AlertTriangle,
  Wifi,
  WifiOff,
} from 'lucide-react';

import { useTheatreStore, useLocationStore, useAuthStore } from '@/stores/useStore';
import { stageApi, sceneApi } from '@/services/api';
import { useRealtime } from '@/hooks/useRealtime';
import { RingBadge, RingLocked } from '@/components/RingBadge';
import { EvidenceCard } from '@/components/EvidenceCard';
import type { Scene, Evidence, RingLevel } from '@/types';

// -------------------- Stage Live 主页面 --------------------

export default function StageLivePage() {
  const { stageId } = useParams<{ stageId: string }>();
  const navigate = useNavigate();

  const { currentTheatre, currentSlot } = useTheatreStore();
  const { currentRing } = useLocationStore();
  const { user } = useAuthStore();

  const [scene, setScene] = useState<Scene | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [showEvidenceDrawer, setShowEvidenceDrawer] = useState(false);
  const [collectedEvidences, setCollectedEvidences] = useState<Evidence[]>([]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // 实时连接
  const { isConnected } = useRealtime({
    theatreId: currentTheatre?.theatre_id || '',
    enabled: !!currentTheatre,
    onMessage: (event) => {
      if (event.event_type === 'evidence_drop' && event.payload?.stage_id === stageId) {
        handleEvidenceDrop(event.payload.evidence as Evidence);
      }
    },
  });

  // 获取场景数据
  useEffect(() => {
    const fetchScene = async () => {
      if (!stageId) return;

      try {
        setIsLoading(true);
        const sceneData = await stageApi.getCurrentScene(stageId);
        setScene(sceneData);
      } catch (err) {
        setError('获取场景失败');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchScene();
  }, [stageId]);

  // 自动隐藏控制栏
  useEffect(() => {
    const handleMouseMove = () => {
      setShowControls(true);
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('mousemove', handleMouseMove);
      container.addEventListener('touchstart', handleMouseMove);
    }

    return () => {
      if (container) {
        container.removeEventListener('mousemove', handleMouseMove);
        container.removeEventListener('touchstart', handleMouseMove);
      }
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, []);

  // 处理证物掉落
  const handleEvidenceDrop = (evidence: Evidence) => {
    setCollectedEvidences((prev) => [...prev, evidence]);
    setShowEvidenceDrawer(true);
    setTimeout(() => setShowEvidenceDrawer(false), 5000);
  };

  // 全屏切换
  const toggleFullscreen = () => {
    if (!containerRef.current) return;

    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // 权限检查
  const ringOrder: RingLevel[] = ['C', 'B', 'A'];
  const requiredRing = (scene as any)?.ring_required || 'C';
  const hasAccess = ringOrder.indexOf(currentRing) >= ringOrder.indexOf(requiredRing);

  if (isLoading) {
    return <StageLiveSkeleton />;
  }

  if (error || !scene) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-4">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-theatre-danger mx-auto mb-4" />
          <p className="text-white mb-4">{error || '场景不存在'}</p>
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

  if (!hasAccess) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <RingLocked
            requiredRing={requiredRing}
            currentRing={currentRing}
            onUpgrade={() => navigate('/map')}
          />
          <button
            onClick={() => navigate(-1)}
            className="mt-4 w-full py-3 border border-theatre-border text-white rounded-lg"
          >
            返回戏单
          </button>
        </div>
      </div>
    );
  }

  // 获取舞台名称
  const stageName = (scene as any)?.stage_name || '舞台';

  return (
    <div
      ref={containerRef}
      className="relative min-h-screen bg-black overflow-hidden"
    >
      {/* 媒体内容 */}
      <MediaPlayer
        scene={scene}
        isMuted={isMuted}
        videoRef={videoRef}
        currentRing={currentRing}
      />

      {/* 控制层 */}
      <AnimatePresence>
        {showControls && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 pointer-events-none"
          >
            {/* 顶部控制栏 */}
            <div className="absolute top-0 left-0 right-0 p-4 bg-gradient-to-b from-black/80 to-transparent pointer-events-auto">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => navigate(-1)}
                  className="flex items-center gap-2 text-white"
                >
                  <ArrowLeft className="w-6 h-6" />
                  <span className="font-medium">{stageName}</span>
                </button>

                <div className="flex items-center gap-3">
                  {isConnected ? (
                    <Wifi className="w-5 h-5 text-green-400" />
                  ) : (
                    <WifiOff className="w-5 h-5 text-red-400" />
                  )}
                  <RingBadge ring={currentRing} size="sm" />
                </div>
              </div>
            </div>

            {/* 底部控制栏 */}
            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent pointer-events-auto">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setIsMuted(!isMuted)}
                    className="text-white hover:text-theatre-accent transition-colors"
                  >
                    {isMuted ? (
                      <VolumeX className="w-6 h-6" />
                    ) : (
                      <Volume2 className="w-6 h-6" />
                    )}
                  </button>
                  <button
                    onClick={toggleFullscreen}
                    className="text-white hover:text-theatre-accent transition-colors"
                  >
                    {isFullscreen ? (
                      <Minimize className="w-6 h-6" />
                    ) : (
                      <Maximize className="w-6 h-6" />
                    )}
                  </button>
                </div>

                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setShowEvidenceDrawer(true)}
                    className="relative text-white hover:text-theatre-accent transition-colors"
                  >
                    <Gift className="w-6 h-6" />
                    {collectedEvidences.length > 0 && (
                      <span className="absolute -top-1 -right-1 w-4 h-4 bg-theatre-accent text-theatre-bg text-xs rounded-full flex items-center justify-center">
                        {collectedEvidences.length}
                      </span>
                    )}
                  </button>
                  <button className="text-white hover:text-theatre-accent transition-colors">
                    <Share2 className="w-6 h-6" />
                  </button>
                </div>
              </div>

              <div className="mt-4 flex items-center gap-4">
                <div className="flex-1 h-1 bg-white/20 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-theatre-accent"
                    initial={{ width: '0%' }}
                    animate={{ width: '45%' }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
                <span className="text-sm text-white/80">23:45</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 证物抽屉 */}
      <EvidenceDrawer
        isOpen={showEvidenceDrawer}
        onClose={() => setShowEvidenceDrawer(false)}
        evidences={collectedEvidences}
      />
    </div>
  );
}

// -------------------- 媒体播放器 --------------------

interface MediaPlayerProps {
  scene: Scene;
  isMuted: boolean;
  videoRef: React.RefObject<HTMLVideoElement>;
  currentRing: RingLevel;
}

function MediaPlayer({ scene, isMuted, videoRef, currentRing }: MediaPlayerProps) {
  const media = scene.media || {};
  const videoUrl = media.video_url;
  const audioUrl = media.audio_url;
  const imageUrl = media.thumbnail_url || media.fallback_images?.[0];

  const getMediaType = () => {
    if (currentRing === 'A' && videoUrl) return 'video';
    if ((currentRing === 'A' || currentRing === 'B') && audioUrl && imageUrl) return 'audio_image';
    if (imageUrl) return 'image';
    return 'text';
  };

  const mediaType = getMediaType();

  return (
    <div className="absolute inset-0">
      {mediaType === 'video' && videoUrl && (
        <video
          ref={videoRef}
          src={videoUrl}
          autoPlay
          loop
          muted={isMuted}
          playsInline
          className="w-full h-full object-cover"
        />
      )}

      {mediaType === 'audio_image' && (
        <>
          <img
            src={imageUrl}
            alt={scene.title}
            className="w-full h-full object-cover"
          />
          <audio
            src={audioUrl}
            autoPlay
            loop
            muted={isMuted}
          />
        </>
      )}

      {mediaType === 'image' && imageUrl && (
        <img
          src={imageUrl}
          alt={scene.title}
          className="w-full h-full object-cover"
        />
      )}

      {mediaType === 'text' && (
        <div className="w-full h-full flex items-center justify-center bg-theatre-bg p-8">
          <div className="max-w-2xl text-center">
            <h2 className="text-2xl font-display font-bold text-theatre-accent mb-4">
              {scene.title}
            </h2>
          </div>
        </div>
      )}

      {media.subtitle && (
        <div className="absolute bottom-24 left-0 right-0 text-center">
          <span className="inline-block px-4 py-2 bg-black/60 text-white rounded-lg">
            {media.subtitle}
          </span>
        </div>
      )}
    </div>
  );
}

// -------------------- 证物抽屉 --------------------

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  evidences: Evidence[];
}

function EvidenceDrawer({ isOpen, onClose, evidences }: EvidenceDrawerProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/40 z-40"
          />

          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 25 }}
            className="absolute bottom-0 left-0 right-0 z-50 bg-theatre-surface rounded-t-2xl max-h-[60vh] overflow-hidden"
          >
            <div className="flex justify-center py-3">
              <div className="w-12 h-1 bg-theatre-border rounded-full" />
            </div>

            <div className="px-4 pb-4 border-b border-theatre-border">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-theatre-text">
                  获得的证物
                </h3>
                <span className="text-sm text-theatre-muted">
                  {evidences.length} 件
                </span>
              </div>
            </div>

            <div className="p-4 overflow-y-auto max-h-[40vh]">
              {evidences.length === 0 ? (
                <div className="text-center py-8 text-theatre-muted">
                  <Gift className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>观看场景可获得证物</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {evidences.map((evidence) => (
                    <EvidenceCard
                      key={evidence.evidence_id}
                      evidence={evidence}
                    />
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// -------------------- 骨架屏 --------------------

function StageLiveSkeleton() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="animate-pulse text-white">加载中...</div>
    </div>
  );
}
