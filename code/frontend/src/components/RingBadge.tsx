// ============================================
// TheatreOS Ring 权限徽章组件
// ============================================

import React from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import { Eye, MapPin, Star } from 'lucide-react';
import type { RingLevel } from '@/types';

// -------------------- Ring 配置 --------------------

const RING_CONFIG: Record<RingLevel, {
  label: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: React.ReactNode;
}> = {
  C: {
    label: 'Ring C',
    description: '远观者',
    color: 'text-ring-c',
    bgColor: 'bg-ring-c/10',
    borderColor: 'border-ring-c/30',
    icon: <Eye className="w-4 h-4" />,
  },
  B: {
    label: 'Ring B',
    description: '靠近者',
    color: 'text-ring-b',
    bgColor: 'bg-ring-b/10',
    borderColor: 'border-ring-b/30',
    icon: <MapPin className="w-4 h-4" />,
  },
  A: {
    label: 'Ring A',
    description: '核心圈',
    color: 'text-ring-a',
    bgColor: 'bg-ring-a/10',
    borderColor: 'border-ring-a/30',
    icon: <Star className="w-4 h-4" />,
  },
};

// -------------------- 基础 Ring 徽章 --------------------

interface RingBadgeProps {
  ring: RingLevel;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  showDescription?: boolean;
  animated?: boolean;
  className?: string;
}

export function RingBadge({
  ring,
  size = 'md',
  showLabel = true,
  showDescription = false,
  animated = false,
  className,
}: RingBadgeProps) {
  // 确保ring有有效值，默认为'C'
  const safeRing = ring && RING_CONFIG[ring] ? ring : 'C';
  const config = RING_CONFIG[safeRing];

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  const Badge = animated ? motion.div : 'div';
  const animationProps = animated
    ? {
        initial: { scale: 0.9, opacity: 0 },
        animate: { scale: 1, opacity: 1 },
        whileHover: { scale: 1.05 },
      }
    : {};

  return (
    <Badge
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border',
        config.bgColor,
        config.borderColor,
        config.color,
        sizeClasses[size],
        className
      )}
      {...animationProps}
    >
      {config.icon}
      {showLabel && <span className="font-medium">{config.label}</span>}
      {showDescription && (
        <span className="text-theatre-muted">· {config.description}</span>
      )}
    </Badge>
  );
}

// -------------------- Ring 权限对比 --------------------

interface RingComparisonProps {
  currentRing: RingLevel;
  requiredRing: RingLevel;
  className?: string;
}

export function RingComparison({
  currentRing,
  requiredRing,
  className,
}: RingComparisonProps) {
  const ringOrder: RingLevel[] = ['C', 'B', 'A'];
  const currentIndex = ringOrder.indexOf(currentRing);
  const requiredIndex = ringOrder.indexOf(requiredRing);
  const hasAccess = currentIndex >= requiredIndex;

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <RingBadge ring={currentRing} size="sm" />
      <span className="text-theatre-muted">→</span>
      <RingBadge ring={requiredRing} size="sm" />
      {hasAccess ? (
        <span className="text-xs text-theatre-success">✓ 可访问</span>
      ) : (
        <span className="text-xs text-theatre-danger">✗ 需要更近</span>
      )}
    </div>
  );
}

// -------------------- Ring 进度指示器 --------------------

interface RingProgressProps {
  currentRing: RingLevel;
  className?: string;
}

export function RingProgress({ currentRing, className }: RingProgressProps) {
  const ringOrder: RingLevel[] = ['C', 'B', 'A'];
  // 确保safeRing有有效值
  const safeRing = currentRing && RING_CONFIG[currentRing] ? currentRing : 'C';
  const currentIndex = ringOrder.indexOf(safeRing);

  return (
    <div className={clsx('flex items-center gap-1', className)}>
      {ringOrder.map((ring, index) => {
        const isActive = index <= currentIndex;
        const config = RING_CONFIG[ring];

        return (
          <React.Fragment key={ring}>
            <motion.div
              className={clsx(
                'w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors',
                isActive
                  ? `${config.bgColor} ${config.borderColor} ${config.color}`
                  : 'bg-theatre-surface border-theatre-border text-theatre-muted'
              )}
              animate={isActive ? { scale: [1, 1.1, 1] } : {}}
              transition={{ duration: 0.3 }}
            >
              {config.icon}
            </motion.div>
            {index < ringOrder.length - 1 && (
              <div
                className={clsx(
                  'w-8 h-0.5 transition-colors',
                  index < currentIndex
                    ? 'bg-theatre-accent'
                    : 'bg-theatre-border'
                )}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// -------------------- Ring 锁定提示 --------------------

interface RingLockedProps {
  requiredRing: RingLevel;
  currentRing: RingLevel;
  onUpgrade?: () => void;
  className?: string;
}

export function RingLocked({
  requiredRing,
  currentRing,
  onUpgrade,
  className,
}: RingLockedProps) {
  // 确保ring有有效值
  const safeRequiredRing = requiredRing && RING_CONFIG[requiredRing] ? requiredRing : 'C';
  const config = RING_CONFIG[safeRequiredRing];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'p-4 rounded-lg border bg-theatre-surface/50 backdrop-blur',
        config.borderColor,
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className={clsx('p-2 rounded-full', config.bgColor, config.color)}>
          {config.icon}
        </div>
        <div className="flex-1">
          <h4 className="font-medium text-theatre-text mb-1">
            需要 {config.label} 权限
          </h4>
          <p className="text-sm text-theatre-muted mb-3">
            此内容仅对 {config.description} 开放。请靠近舞台位置以获取更高权限。
          </p>
          <RingComparison currentRing={currentRing} requiredRing={requiredRing} />
          {onUpgrade && (
            <button
              onClick={onUpgrade}
              className={clsx(
                'mt-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                config.bgColor,
                config.color,
                'hover:opacity-80'
              )}
            >
              查看如何获取权限
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default RingBadge;
