import React from 'react';
import { User, Settings, LogOut } from 'lucide-react';
import { useAuthStore } from '@/stores/useStore';
import { useNavigate } from 'react-router-dom';

export default function ProfilePage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    localStorage.removeItem('theatre_token');
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-theatre-bg p-4">
      <header className="max-w-2xl mx-auto mb-6">
        <h1 className="text-2xl font-display font-bold text-theatre-accent">个人中心</h1>
      </header>
      <main className="max-w-2xl mx-auto space-y-4">
        <div className="bg-theatre-surface rounded-xl p-6 border border-theatre-border">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-theatre-accent/20 flex items-center justify-center">
              <User className="w-8 h-8 text-theatre-accent" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-theatre-text">{user?.username || '访客'}</h2>
              <p className="text-theatre-muted">@{user?.username || 'guest'}</p>
            </div>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="w-full p-4 bg-theatre-surface rounded-xl border border-theatre-border flex items-center gap-3 text-red-500 hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>退出登录</span>
        </button>
      </main>
    </div>
  );
}
