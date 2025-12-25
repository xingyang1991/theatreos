// ============================================
// TheatreOS 前端应用入口
// ============================================

import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';

import { useAuthStore, useTheatreStore, useLocationStore } from '@/stores/useStore';
import { authApi, theatreApi } from '@/services/api';

// 页面组件
import ShowbillPage from '@/pages/Showbill';
import StageLivePage from '@/pages/StageLive';
import GateLobbyPage from '@/pages/GateLobby';

// 布局组件
import MainLayout from '@/layouts/MainLayout';
import AuthLayout from '@/layouts/AuthLayout';

// 测试模式控制面板
import TestModePanel from '@/components/TestModePanel';

// 认证页面
import LoginPage from '@/pages/auth/Login';
import RegisterPage from '@/pages/auth/Register';

// 其他页面
import ArchivePage from '@/pages/Archive';
import CrewPage from '@/pages/Crew';
import ProfilePage from '@/pages/Profile';
import MapPage from '@/pages/Map';
import ExplainCardPage from '@/pages/ExplainCard';

// 默认剧场配置
const DEFAULT_CITY = 'shanghai';

// -------------------- 应用入口 --------------------

export default function App() {
  const { user, setUser, isAuthenticated } = useAuthStore();
  const { currentTheatre, setCurrentTheatre } = useTheatreStore();
  const { setLocation } = useLocationStore();
  const [isInitializing, setIsInitializing] = useState(true);
  const [initError, setInitError] = useState<string | null>(null);

  // 初始化：检查登录状态
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('theatreos_token');
      if (token) {
        try {
          const userData = await authApi.getMe();
          setUser(userData);
        } catch (err) {
          localStorage.removeItem('theatreos_token');
        }
      }
    };

    initAuth();
  }, [setUser]);

  // 初始化：获取或创建默认剧场
  useEffect(() => {
    const initTheatre = async () => {
      try {
        setIsInitializing(true);
        setInitError(null);

        // 检查本地存储是否有剧场ID
        let theatreId = localStorage.getItem('theatreos_theatre_id');

        // 如果没有，创建新剧场
        if (!theatreId) {
          console.log('Creating new theatre...');
          const result = await theatreApi.create(DEFAULT_CITY);
          theatreId = result.theatre_id;
          localStorage.setItem('theatreos_theatre_id', theatreId);
          console.log('Theatre created:', theatreId);
        }

        // 获取剧场详情
        console.log('Fetching theatre:', theatreId);
        const theatreData = await theatreApi.getTheatre(theatreId);
        
        // 构建完整的Theatre对象
        const theatre = {
          theatre_id: theatreData.theatre_id || theatreId,
          name: theatreData.name || `${DEFAULT_CITY.charAt(0).toUpperCase() + DEFAULT_CITY.slice(1)} Theatre`,
          city: theatreData.city || DEFAULT_CITY,
          timezone: theatreData.timezone || 'Asia/Shanghai',
          theme_id: theatreData.theme_id || 'hp_shanghai_s1',
          status: theatreData.status || 'ACTIVE',
          ...theatreData,
        };

        setCurrentTheatre(theatre);
        console.log('Theatre initialized:', theatre);

      } catch (err: any) {
        console.error('Failed to initialize theatre:', err);
        
        // 如果获取失败，尝试重新创建
        if (err.response?.status === 404) {
          localStorage.removeItem('theatreos_theatre_id');
          try {
            const result = await theatreApi.create(DEFAULT_CITY);
            const theatreId = result.theatre_id;
            localStorage.setItem('theatreos_theatre_id', theatreId);
            
            const theatreData = await theatreApi.getTheatre(theatreId);
            const theatre = {
              theatre_id: theatreData.theatre_id || theatreId,
              name: theatreData.name || `${DEFAULT_CITY.charAt(0).toUpperCase() + DEFAULT_CITY.slice(1)} Theatre`,
              city: theatreData.city || DEFAULT_CITY,
              timezone: theatreData.timezone || 'Asia/Shanghai',
              theme_id: theatreData.theme_id || 'hp_shanghai_s1',
              status: theatreData.status || 'ACTIVE',
              ...theatreData,
            };
            setCurrentTheatre(theatre);
          } catch (retryErr) {
            setInitError('无法连接到服务器，请稍后重试');
          }
        } else {
          setInitError('初始化失败，请刷新页面重试');
        }
      } finally {
        setIsInitializing(false);
      }
    };

    initTheatre();
  }, [setCurrentTheatre]);

  // 初始化：获取位置权限
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.watchPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
        },
        (error) => {
          console.warn('Geolocation error:', error);
        },
        { enableHighAccuracy: true, maximumAge: 30000 }
      );
    }
  }, [setLocation]);

  // 显示初始化错误
  if (initError) {
    return (
      <div className="min-h-screen bg-theatre-bg flex items-center justify-center p-4">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">连接失败</h2>
          <p className="text-grey-400 mb-4">{initError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-theatre-accent text-black rounded-lg font-medium hover:bg-theatre-accent/90 transition-colors"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      {/* 测试模式控制面板 - 全局浮动按钮 */}
      <TestModePanel />
      
      <AnimatePresence mode="wait">
        <Routes>
          {/* 认证路由 */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* 主应用路由 */}
          <Route element={<MainLayout />}>
            {/* 戏单（首页） */}
            <Route path="/" element={<ShowbillPage />} />
            <Route path="/showbill" element={<ShowbillPage />} />

            {/* 舞台观看 */}
            <Route path="/stage/:stageId" element={<StageLivePage />} />

            {/* 门厅 */}
            <Route path="/gate-lobby/:slotId" element={<GateLobbyPage />} />

            {/* 解释卡 */}
            <Route path="/explain/:gateId" element={<ExplainCardPage />} />

            {/* 档案 */}
            <Route path="/archive" element={<ArchivePage />} />

            {/* 剧团 */}
            <Route path="/crew" element={<CrewPage />} />
            <Route path="/crew/:crewId" element={<CrewPage />} />

            {/* 地图 */}
            <Route path="/map" element={<MapPage />} />

            {/* 个人中心 */}
            <Route path="/profile" element={<ProfilePage />} />
          </Route>

          {/* 404 重定向 */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </BrowserRouter>
  );
}
