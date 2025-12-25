import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuthStore } from '@/stores/useStore';
import { authApi } from '@/services/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await authApi.login(username, password);
      // ApiResponse<T> 格式: { success, data?: T, error?, message? }
      // 后端实际返回: { success, token, user, error }
      // 需要兼容两种格式
      const data = (response as any).data || response;
      const token = data.token;
      const user = data.user;
      const userId = user?.user_id || data.user_id;
      
      if (!token) {
        throw new Error('No token received');
      }
      
      // 使用正确的 localStorage key
      localStorage.setItem('theatreos_token', token);
      localStorage.setItem('theatre_token', token); // 兼容旧key
      setToken(token);
      setUser({ 
        user_id: userId, 
        username: user?.username || username, 
        role: user?.role || 'player' 
      });
      navigate('/');
    } catch (err) {
      console.error('Login error:', err);
      setError('登录失败，请检查用户名和密码');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-theatre-surface rounded-xl p-8 border border-theatre-border"
    >
      <h1 className="text-2xl font-display font-bold text-theatre-accent mb-2">
        欢迎回来
      </h1>
      <p className="text-theatre-muted mb-6">登录以继续您的剧场之旅</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-theatre-muted mb-1">用户名</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-4 py-3 bg-theatre-bg border border-theatre-border rounded-lg text-theatre-text focus:border-theatre-accent focus:outline-none"
            required
          />
        </div>
        <div>
          <label className="block text-sm text-theatre-muted mb-1">密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 bg-theatre-bg border border-theatre-border rounded-lg text-theatre-text focus:border-theatre-accent focus:outline-none"
            required
          />
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-3 bg-theatre-accent text-theatre-bg rounded-lg font-medium hover:opacity-90 disabled:opacity-50"
        >
          {isLoading ? '登录中...' : '登录'}
        </button>
      </form>

      <p className="mt-6 text-center text-theatre-muted">
        还没有账号？{' '}
        <Link to="/register" className="text-theatre-accent hover:underline">
          立即注册
        </Link>
      </p>
    </motion.div>
  );
}
