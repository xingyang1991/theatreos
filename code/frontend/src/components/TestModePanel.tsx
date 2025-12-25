import React, { useState, useEffect } from 'react';

// 后端API返回的实际格式
interface TestModeAPIResponse {
  success: boolean;
  test_mode: {
    enabled: boolean;
    auto_events: boolean;
    skip_location: boolean;
    debug_logging: boolean;
  };
  timing: {
    scene_change_interval: string;
    event_trigger_interval: string;
    gate_voting_duration: string;
  };
  game_params: {
    ring_upgrade_points: number;
    base_choice_points: number;
    evidence_drop_rate: string;
  };
  stages: {
    total: number;
    max_active: number;
  };
  threads: {
    total: number;
    names: string[];
  };
}

interface Preset {
  name: string;
  description: string;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

// 预设图标映射
const presetIcons: Record<string, string> = {
  quick_test: '⚡',
  demo: '🎭',
  stress_test: '🔥',
  production: '🏭',
  balanced: '⚖️'
};

// 测试模式控制面板组件
const TestModePanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<TestModeAPIResponse | null>(null);
  const [presets, setPresets] = useState<Record<string, Preset>>({});
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'status' | 'actions'>('status');
  const [error, setError] = useState<string | null>(null);

  // 获取状态
  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/test-mode/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        setError(null);
      } else {
        setError('获取状态失败');
      }
    } catch (e) {
      console.error('获取测试模式状态失败', e);
      setError('网络错误');
    }
  };

  // 获取预设列表
  const fetchPresets = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/test-mode/presets`);
      if (res.ok) {
        const data = await res.json();
        if (data.presets) {
          setPresets(data.presets);
        }
      }
    } catch (e) {
      console.error('获取预设列表失败', e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      fetchPresets();
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      const interval = setInterval(fetchStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  // 切换测试模式
  const toggleTestMode = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/test-mode/toggle`, { method: 'PUT' });
      if (res.ok) {
        await fetchStatus();
      }
    } catch (e) {
      console.error('切换测试模式失败', e);
    } finally {
      setLoading(false);
    }
  };

  // 应用预设
  const applyPreset = async (presetId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/test-mode/presets/${presetId}/apply`, { method: 'POST' });
      if (res.ok) {
        await fetchStatus();
      }
    } catch (e) {
      console.error('应用预设失败', e);
    } finally {
      setLoading(false);
    }
  };

  // 触发事件
  const triggerEvent = async (eventType: string) => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/v1/test-mode/trigger/${eventType}`, { method: 'POST' });
      await fetchStatus();
    } catch (e) {
      console.error('触发事件失败', e);
    } finally {
      setLoading(false);
    }
  };

  // 重置数据
  const resetData = async () => {
    if (!confirm('确定要重置测试数据吗？')) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/v1/test-mode/reset`, { method: 'POST' });
      await fetchStatus();
      alert('测试数据已重置');
    } catch (e) {
      console.error('重置数据失败', e);
    } finally {
      setLoading(false);
    }
  };

  const isEnabled = status?.test_mode?.enabled ?? false;

  return (
    <>
      {/* 浮动按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '96px',
          right: '16px',
          zIndex: 9999,
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: isEnabled 
            ? 'linear-gradient(135deg, #22c55e, #16a34a)' 
            : 'linear-gradient(135deg, #9333ea, #ec4899)',
          border: 'none',
          boxShadow: isEnabled 
            ? '0 4px 15px rgba(34, 197, 94, 0.4)' 
            : '0 4px 15px rgba(147, 51, 234, 0.4)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '24px',
          color: 'white',
          transition: 'all 0.3s ease'
        }}
      >
        {isEnabled ? '🧪' : '⚙️'}
      </button>

      {/* 控制面板 */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '160px',
            right: '16px',
            zIndex: 9998,
            width: '320px',
            maxHeight: '70vh',
            background: 'rgba(17, 24, 39, 0.98)',
            backdropFilter: 'blur(10px)',
            borderRadius: '16px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
            border: '1px solid rgba(75, 85, 99, 0.5)',
            overflow: 'hidden'
          }}
        >
          {/* 头部 */}
          <div style={{ padding: '16px', borderBottom: '1px solid rgba(75, 85, 99, 0.5)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', color: 'white' }}>
                🧪 测试模式
              </h3>
              <button
                onClick={toggleTestMode}
                disabled={loading}
                style={{
                  padding: '6px 16px',
                  borderRadius: '20px',
                  fontSize: '14px',
                  fontWeight: '600',
                  border: 'none',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  background: isEnabled ? '#16a34a' : '#4b5563',
                  color: 'white',
                  transition: 'all 0.2s'
                }}
              >
                {loading ? '...' : isEnabled ? '✓ 已启用' : '○ 已关闭'}
              </button>
            </div>
            
            {/* 状态指示器 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px' }}>
              <div style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: isEnabled ? '#22c55e' : '#6b7280',
                boxShadow: isEnabled ? '0 0 10px #22c55e' : 'none'
              }} />
              <span style={{ fontSize: '13px', color: '#9ca3af' }}>
                {isEnabled ? '测试模式运行中' : '测试模式已关闭'}
              </span>
            </div>

            {error && (
              <div style={{ 
                marginTop: '8px', 
                padding: '8px', 
                background: 'rgba(239, 68, 68, 0.2)', 
                borderRadius: '8px',
                fontSize: '12px',
                color: '#fca5a5'
              }}>
                ⚠️ {error}
              </div>
            )}
          </div>

          {/* 标签页 */}
          <div style={{ display: 'flex', borderBottom: '1px solid rgba(75, 85, 99, 0.5)' }}>
            {(['status', 'actions'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  flex: 1,
                  padding: '10px',
                  fontSize: '14px',
                  fontWeight: '500',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  color: activeTab === tab ? '#a855f7' : '#9ca3af',
                  borderBottom: activeTab === tab ? '2px solid #a855f7' : '2px solid transparent',
                  transition: 'all 0.2s'
                }}
              >
                {tab === 'status' ? '📊 状态' : '🎮 操作'}
              </button>
            ))}
          </div>

          {/* 内容区 */}
          <div style={{ padding: '16px', overflowY: 'auto', maxHeight: '45vh' }}>
            {/* 状态标签页 */}
            {activeTab === 'status' && status && (
              <>
                {/* 时间参数 */}
                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                    ⏱️ 时间参数
                  </h4>
                  <div style={{ 
                    background: 'rgba(31, 41, 55, 0.5)', 
                    borderRadius: '10px', 
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>场景切换</span>
                      <span style={{ fontSize: '13px', color: '#a855f7', fontWeight: '600' }}>
                        {status.timing?.scene_change_interval || '30秒'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>事件触发</span>
                      <span style={{ fontSize: '13px', color: '#22c55e', fontWeight: '600' }}>
                        {status.timing?.event_trigger_interval || '15秒'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>投票时长</span>
                      <span style={{ fontSize: '13px', color: '#eab308', fontWeight: '600' }}>
                        {status.timing?.gate_voting_duration || '60秒'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 游戏参数 */}
                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                    🎯 游戏参数
                  </h4>
                  <div style={{ 
                    background: 'rgba(31, 41, 55, 0.5)', 
                    borderRadius: '10px', 
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>Ring升级积分</span>
                      <span style={{ fontSize: '13px', color: '#3b82f6', fontWeight: '600' }}>
                        {status.game_params?.ring_upgrade_points || 100}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>基础选择积分</span>
                      <span style={{ fontSize: '13px', color: '#3b82f6', fontWeight: '600' }}>
                        {status.game_params?.base_choice_points || 50}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>证物掉落率</span>
                      <span style={{ fontSize: '13px', color: '#f97316', fontWeight: '600' }}>
                        {status.game_params?.evidence_drop_rate || '80%'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 舞台信息 */}
                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                    🎭 舞台信息
                  </h4>
                  <div style={{ 
                    background: 'rgba(31, 41, 55, 0.5)', 
                    borderRadius: '10px', 
                    padding: '12px',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '12px'
                  }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#a855f7' }}>
                        {status.stages?.total || 0}
                      </div>
                      <div style={{ fontSize: '12px', color: '#9ca3af' }}>总舞台数</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#22c55e' }}>
                        {status.threads?.total || 0}
                      </div>
                      <div style={{ fontSize: '12px', color: '#9ca3af' }}>故事线数</div>
                    </div>
                  </div>
                </div>

                {/* 故事线列表 */}
                {status.threads?.names && status.threads.names.length > 0 && (
                  <div>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                      📖 故事线
                    </h4>
                    <div style={{ 
                      background: 'rgba(31, 41, 55, 0.5)', 
                      borderRadius: '10px', 
                      padding: '12px',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '6px'
                    }}>
                      {status.threads.names.map((name, i) => (
                        <span key={i} style={{
                          fontSize: '11px',
                          padding: '4px 8px',
                          background: 'rgba(147, 51, 234, 0.3)',
                          borderRadius: '4px',
                          color: '#d8b4fe'
                        }}>
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* 开关选项 */}
                <div style={{ marginTop: '16px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                    🔧 开关选项
                  </h4>
                  <div style={{ 
                    background: 'rgba(31, 41, 55, 0.5)', 
                    borderRadius: '10px', 
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>自动事件</span>
                      <span style={{ 
                        fontSize: '12px', 
                        padding: '2px 8px', 
                        borderRadius: '10px',
                        background: status.test_mode?.auto_events ? '#16a34a' : '#4b5563',
                        color: 'white'
                      }}>
                        {status.test_mode?.auto_events ? '开' : '关'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>跳过位置检查</span>
                      <span style={{ 
                        fontSize: '12px', 
                        padding: '2px 8px', 
                        borderRadius: '10px',
                        background: status.test_mode?.skip_location ? '#16a34a' : '#4b5563',
                        color: 'white'
                      }}>
                        {status.test_mode?.skip_location ? '开' : '关'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '13px', color: '#d1d5db' }}>调试日志</span>
                      <span style={{ 
                        fontSize: '12px', 
                        padding: '2px 8px', 
                        borderRadius: '10px',
                        background: status.test_mode?.debug_logging ? '#16a34a' : '#4b5563',
                        color: 'white'
                      }}>
                        {status.test_mode?.debug_logging ? '开' : '关'}
                      </span>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* 操作标签页 */}
            {activeTab === 'actions' && (
              <>
                {/* 预设选择 */}
                {Object.keys(presets).length > 0 && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                      📦 快速预设
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      {Object.entries(presets).map(([id, preset]) => (
                        <button
                          key={id}
                          onClick={() => applyPreset(id)}
                          disabled={loading}
                          style={{
                            padding: '10px',
                            borderRadius: '8px',
                            border: '1px solid rgba(75, 85, 99, 0.5)',
                            background: 'rgba(31, 41, 55, 0.5)',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.2s'
                          }}
                        >
                          <div style={{ fontSize: '18px', marginBottom: '4px' }}>
                            {presetIcons[id] || '📦'}
                          </div>
                          <div style={{ fontSize: '13px', fontWeight: '500', color: 'white' }}>
                            {preset.name}
                          </div>
                          <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                            {preset.description}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* 触发事件 */}
                <div style={{ marginBottom: '16px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                    🎬 触发事件
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <button
                      onClick={() => triggerEvent('scene_change')}
                      disabled={loading}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid rgba(34, 197, 94, 0.3)',
                        background: 'rgba(34, 197, 94, 0.15)',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        color: '#86efac',
                        fontSize: '13px',
                        fontWeight: '500'
                      }}
                    >
                      🎭 切换场景
                    </button>
                    <button
                      onClick={() => triggerEvent('gate_open')}
                      disabled={loading}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        background: 'rgba(59, 130, 246, 0.15)',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        color: '#93c5fd',
                        fontSize: '13px',
                        fontWeight: '500'
                      }}
                    >
                      🚪 开启门
                    </button>
                    <button
                      onClick={() => triggerEvent('evidence_drop')}
                      disabled={loading}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid rgba(234, 179, 8, 0.3)',
                        background: 'rgba(234, 179, 8, 0.15)',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        color: '#fde047',
                        fontSize: '13px',
                        fontWeight: '500'
                      }}
                    >
                      📜 掉落证物
                    </button>
                    <button
                      onClick={() => triggerEvent('world_event')}
                      disabled={loading}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid rgba(168, 85, 247, 0.3)',
                        background: 'rgba(168, 85, 247, 0.15)',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        color: '#d8b4fe',
                        fontSize: '13px',
                        fontWeight: '500'
                      }}
                    >
                      🌍 世界事件
                    </button>
                  </div>
                </div>

                {/* 危险操作 */}
                <div>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#9ca3af', fontWeight: '600' }}>
                    ⚠️ 危险操作
                  </h4>
                  <button
                    onClick={resetData}
                    disabled={loading}
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      background: 'rgba(239, 68, 68, 0.15)',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      color: '#fca5a5',
                      fontSize: '13px',
                      fontWeight: '500'
                    }}
                  >
                    🗑️ 重置测试数据
                  </button>
                </div>
              </>
            )}
          </div>

          {/* 关闭按钮 */}
          <button
            onClick={() => setIsOpen(false)}
            style={{
              position: 'absolute',
              top: '12px',
              right: '12px',
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              border: 'none',
              background: 'rgba(75, 85, 99, 0.5)',
              cursor: 'pointer',
              color: '#9ca3af',
              fontSize: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
          >
            ✕
          </button>
        </div>
      )}
    </>
  );
};

export default TestModePanel;
