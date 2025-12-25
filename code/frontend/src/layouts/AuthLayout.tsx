// ============================================
// TheatreOS 认证布局组件
// ============================================

import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useUserStore } from '@/stores/useStore';

export default function AuthLayout() {
  const { isAuthenticated } = useUserStore();

  // 已登录用户重定向到首页
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Outlet />
      </div>
    </div>
  );
}
