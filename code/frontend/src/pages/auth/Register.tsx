import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuthStore } from '@/stores/useStore';
import { authApi } from '@/services/api';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await authApi.register(username, password, nickname);
      const data = response.data;
      localStorage.setItem('theatre_token', data.token);
      setToken(data.token);
      setUser({ user_id: data.user_id, username, role: 'player' });
      navigate('/');
    } catch (err) {
      setError('注册失败，用户名可能已被使用');
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
        加入剧场
      </h1>
      <p className="text-theatre-muted mb-6">创建账号，开启您的城市剧场之旅</p>

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
          <label className="block text-sm text-theatre-muted mb-1">昵称</label>
          <input
            type="text"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
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
          {isLoading ? '注册中...' : '注册'}
        </button>
      </form>

      <p className="mt-6 text-center text-theatre-muted">
        已有账号？{' '}
        <Link to="/login" className="text-theatre-accent hover:underline">
          立即登录
        </Link>
      </p>
    </motion.div>
  );
}
