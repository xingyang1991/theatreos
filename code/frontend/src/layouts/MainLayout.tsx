// ============================================
// TheatreOS 主布局组件
// ============================================

import React from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import {
  Calendar,
  Archive,
  Users,
  Map,
  User,
} from 'lucide-react';

// -------------------- 主布局 --------------------

export default function MainLayout() {
  const location = useLocation();

  // 全屏页面不显示底部导航
  const isFullscreenPage = location.pathname.startsWith('/stage/');

  return (
    <div className="min-h-screen bg-theatre-bg">
      {/* 主内容区域 */}
      <main className={clsx(!isFullscreenPage && 'pb-20')}>
        <Outlet />
      </main>

      {/* 底部导航栏 */}
      {!isFullscreenPage && <BottomNavigation />}
    </div>
  );
}

// -------------------- 底部导航栏 --------------------

function BottomNavigation() {
  const navItems = [
    { path: '/showbill', icon: Calendar, label: '戏单' },
    { path: '/archive', icon: Archive, label: '档案' },
    { path: '/crew', icon: Users, label: '剧团' },
    { path: '/map', icon: Map, label: '地图' },
    { path: '/profile', icon: User, label: '我的' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-theatre-surface/90 backdrop-blur-lg border-t border-theatre-border safe-area-bottom">
      <div className="max-w-2xl mx-auto px-4">
        <div className="flex items-center justify-around py-2">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  'flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors',
                  isActive
                    ? 'text-theatre-accent'
                    : 'text-theatre-muted hover:text-theatre-text'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <motion.div
                    animate={isActive ? { scale: 1.1 } : { scale: 1 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                  >
                    <item.icon className="w-6 h-6" />
                  </motion.div>
                  <span className="text-xs font-medium">{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute -bottom-0.5 w-8 h-1 bg-theatre-accent rounded-full"
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
