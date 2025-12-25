// ============================================
// TheatreOS 证物卡片组件
// ============================================

import React from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import {
  Ticket,
  Clock,
  Camera,
  FileText,
  Stamp,
  Mic,
  Image,
  CheckCircle,
  AlertCircle,
  Timer,
} from 'lucide-react';
import { format, differenceInHours, isPast } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { Evidence, EvidenceType, EvidenceGrade } from '@/types';

// -------------------- 证物类型配置 --------------------

const EVIDENCE_TYPE_CONFIG: Record<EvidenceType, {
  label: string;
  icon: React.ReactNode;
  color: string;
}> = {
  ticket: {
    label: '票据',
    icon: <Ticket className="w-4 h-4" />,
    color: 'text-blue-400',
  },
  timestamp: {
    label: '时间码',
    icon: <Clock className="w-4 h-4" />,
    color: 'text-green-400',
  },
  surveillance: {
    label: '监控帧',
    icon: <Camera className="w-4 h-4" />,
    color: 'text-red-400',
  },
  note: {
    label: '手写纸条',
    icon: <FileText className="w-4 h-4" />,
    color: 'text-yellow-400',
  },
  seal: {
    label: '印章',
    icon: <Stamp className="w-4 h-4" />,
    color: 'text-purple-400',
  },
  audio: {
    label: '音频片段',
    icon: <Mic className="w-4 h-4" />,
    color: 'text-pink-400',
  },
  photo: {
    label: '照片',
    icon: <Image className="w-4 h-4" />,
    color: 'text-cyan-400',
  },
};

// -------------------- 证物等级配置 --------------------

const GRADE_CONFIG: Record<EvidenceGrade, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
}> = {
  A: {
    label: 'A级',
    color: 'text-ring-a',
    bgColor: 'bg-ring-a/10',
    borderColor: 'border-ring-a/30',
  },
  B: {
    label: 'B级',
    color: 'text-ring-b',
    bgColor: 'bg-ring-b/10',
    borderColor: 'border-ring-b/30',
  },
  C: {
    label: 'C级',
    color: 'text-ring-c',
    bgColor: 'bg-ring-c/10',
    borderColor: 'border-ring-c/30',
  },
};

// -------------------- 证物卡片组件 --------------------

interface EvidenceCardProps {
  evidence: Evidence;
  isSelected?: boolean;
  isSelectable?: boolean;
  onSelect?: (evidenceId: string) => void;
  onClick?: (evidence: Evidence) => void;
  className?: string;
}

export function EvidenceCard({
  evidence,
  isSelected = false,
  isSelectable = false,
  onSelect,
  onClick,
  className,
}: EvidenceCardProps) {
  const typeConfig = EVIDENCE_TYPE_CONFIG[evidence.evidence_type] || EVIDENCE_TYPE_CONFIG['物证'];
  const safeGrade = evidence.grade && GRADE_CONFIG[evidence.grade] ? evidence.grade : 'C';
  const gradeConfig = GRADE_CONFIG[safeGrade];
  
  const isExpired = evidence.expires_at ? isPast(new Date(evidence.expires_at)) : false;
  const hoursUntilExpiry = evidence.expires_at
    ? differenceInHours(new Date(evidence.expires_at), new Date())
    : null;

  const handleClick = () => {
    if (isSelectable && onSelect) {
      onSelect(evidence.evidence_id);
    } else if (onClick) {
      onClick(evidence);
    }
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={handleClick}
      className={clsx(
        'relative p-4 rounded-lg border cursor-pointer transition-all',
        'bg-theatre-surface hover:bg-theatre-surface/80',
        isSelected
          ? 'border-theatre-accent ring-2 ring-theatre-accent/30'
          : 'border-theatre-border',
        isExpired && 'opacity-50',
        className
      )}
    >
      {/* 选中指示器 */}
      {isSelectable && (
        <div
          className={clsx(
            'absolute top-2 right-2 w-5 h-5 rounded-full border-2 flex items-center justify-center',
            isSelected
              ? 'bg-theatre-accent border-theatre-accent'
              : 'border-theatre-muted'
          )}
        >
          {isSelected && <CheckCircle className="w-3 h-3 text-theatre-bg" />}
        </div>
      )}

      {/* 证物图片 */}
      {evidence.image_url && (
        <div className="relative mb-3 rounded-md overflow-hidden aspect-video bg-theatre-bg">
          <img
            src={evidence.image_url}
            alt={evidence.title}
            className="w-full h-full object-cover"
          />
          {/* 等级标签 */}
          <div
            className={clsx(
              'absolute top-2 left-2 px-2 py-0.5 rounded text-xs font-bold',
              gradeConfig.bgColor,
              gradeConfig.color
            )}
          >
            {gradeConfig.label}
          </div>
        </div>
      )}

      {/* 证物信息 */}
      <div className="space-y-2">
        {/* 类型和标题 */}
        <div className="flex items-start gap-2">
          <span className={clsx('mt-0.5', typeConfig.color)}>{typeConfig.icon}</span>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-theatre-text truncate">
              {evidence.title}
            </h4>
            <p className="text-xs text-theatre-muted">{typeConfig.label}</p>
          </div>
        </div>

        {/* 描述 */}
        {evidence.description && (
          <p className="text-sm text-theatre-muted line-clamp-2">
            {evidence.description}
          </p>
        )}

        {/* 底部信息 */}
        <div className="flex items-center justify-between pt-2 border-t border-theatre-border">
          {/* 验证状态 */}
          <div className="flex items-center gap-1">
            {evidence.is_verified ? (
              <>
                <CheckCircle className="w-3 h-3 text-theatre-success" />
                <span className="text-xs text-theatre-success">已验证</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3 h-3 text-theatre-muted" />
                <span className="text-xs text-theatre-muted">待验证</span>
              </>
            )}
          </div>

          {/* 过期时间 */}
          {hoursUntilExpiry !== null && (
            <div
              className={clsx(
                'flex items-center gap-1 text-xs',
                hoursUntilExpiry <= 2
                  ? 'text-theatre-danger'
                  : hoursUntilExpiry <= 6
                  ? 'text-yellow-400'
                  : 'text-theatre-muted'
              )}
            >
              <Timer className="w-3 h-3" />
              {isExpired ? (
                <span>已过期</span>
              ) : hoursUntilExpiry < 1 ? (
                <span>即将过期</span>
              ) : (
                <span>{hoursUntilExpiry}h</span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// -------------------- 证物列表组件 --------------------

interface EvidenceListProps {
  evidences: Evidence[];
  selectedIds?: string[];
  isSelectable?: boolean;
  onSelect?: (evidenceId: string) => void;
  onEvidenceClick?: (evidence: Evidence) => void;
  emptyMessage?: string;
  className?: string;
}

export function EvidenceList({
  evidences,
  selectedIds = [],
  isSelectable = false,
  onSelect,
  onEvidenceClick,
  emptyMessage = '暂无证物',
  className,
}: EvidenceListProps) {
  if (evidences.length === 0) {
    return (
      <div className={clsx('text-center py-8 text-theatre-muted', className)}>
        <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={clsx('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4', className)}>
      {evidences.map((evidence) => (
        <EvidenceCard
          key={evidence.evidence_id}
          evidence={evidence}
          isSelected={selectedIds.includes(evidence.evidence_id)}
          isSelectable={isSelectable}
          onSelect={onSelect}
          onClick={onEvidenceClick}
        />
      ))}
    </div>
  );
}

// -------------------- 证物详情弹窗 --------------------

interface EvidenceDetailProps {
  evidence: Evidence;
  onClose: () => void;
  onVerify?: () => void;
  onShare?: () => void;
}

export function EvidenceDetail({
  evidence,
  onClose,
  onVerify,
  onShare,
}: EvidenceDetailProps) {
  const typeConfig = EVIDENCE_TYPE_CONFIG[evidence.evidence_type];
  const gradeConfig = GRADE_CONFIG[evidence.grade];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-theatre-surface rounded-xl border border-theatre-border overflow-hidden"
      >
        {/* 图片区域 */}
        {evidence.image_url && (
          <div className="relative aspect-video bg-theatre-bg">
            <img
              src={evidence.image_url}
              alt={evidence.title}
              className="w-full h-full object-contain"
            />
          </div>
        )}

        {/* 内容区域 */}
        <div className="p-6 space-y-4">
          {/* 头部 */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={clsx('p-2 rounded-lg', gradeConfig.bgColor)}>
                <span className={typeConfig.color}>{typeConfig.icon}</span>
              </div>
              <div>
                <h3 className="text-lg font-bold text-theatre-text">
                  {evidence.title}
                </h3>
                <p className="text-sm text-theatre-muted">
                  {typeConfig.label} · {gradeConfig.label}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-theatre-border transition-colors"
            >
              ✕
            </button>
          </div>

          {/* 描述 */}
          {evidence.description && (
            <p className="text-theatre-text">{evidence.description}</p>
          )}

          {/* 元数据 */}
          <div className="grid grid-cols-2 gap-4 p-4 bg-theatre-bg rounded-lg">
            <div>
              <p className="text-xs text-theatre-muted mb-1">获取时间</p>
              <p className="text-sm text-theatre-text">
                {format(new Date(evidence.created_at), 'yyyy/MM/dd HH:mm', {
                  locale: zhCN,
                })}
              </p>
            </div>
            {evidence.expires_at && (
              <div>
                <p className="text-xs text-theatre-muted mb-1">过期时间</p>
                <p className="text-sm text-theatre-text">
                  {format(new Date(evidence.expires_at), 'yyyy/MM/dd HH:mm', {
                    locale: zhCN,
                  })}
                </p>
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-3">
            {!evidence.is_verified && onVerify && (
              <button
                onClick={onVerify}
                className="flex-1 py-2 px-4 bg-theatre-accent text-theatre-bg rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                验证证物
              </button>
            )}
            {onShare && (
              <button
                onClick={onShare}
                className="flex-1 py-2 px-4 border border-theatre-border text-theatre-text rounded-lg font-medium hover:bg-theatre-border transition-colors"
              >
                分享给剧团
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default EvidenceCard;
