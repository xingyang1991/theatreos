"""
TheatreOS 快速测试模式 - 可调整参数配置
所有参数都可以通过API动态调整，也可以一键重置为默认值
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# 配置文件路径
CONFIG_FILE = Path(__file__).parent / "current_config.json"
DEFAULT_CONFIG_FILE = Path(__file__).parent / "default_config.json"


@dataclass
class TestModeConfig:
    """测试模式配置参数"""
    
    # ========== 时间参数（秒）==========
    # 场景切换间隔（默认5分钟，测试模式30秒）
    scene_change_interval: int = 30
    
    # 事件触发间隔（默认10分钟，测试模式15秒）
    event_trigger_interval: int = 15
    
    # 投票/门持续时间（默认24小时，测试模式60秒）
    gate_voting_duration: int = 60
    
    # 证物收集冷却时间（默认30分钟，测试模式10秒）
    evidence_cooldown: int = 10
    
    # NPC对话冷却时间（默认5分钟，测试模式5秒）
    npc_dialogue_cooldown: int = 5
    
    # ========== 游戏参数 ==========
    # Ring升级所需积分（默认1000，测试模式100）
    ring_upgrade_points: int = 100
    
    # 每次选择获得的基础积分（默认10，测试模式50）
    base_choice_points: int = 50
    
    # 投票最少参与人数（默认10，测试模式1）
    min_vote_participants: int = 1
    
    # 证物掉落概率（0-100，默认30%，测试模式80%）
    evidence_drop_rate: int = 80
    
    # 稀有证物掉落概率（0-100，默认5%，测试模式30%）
    rare_evidence_drop_rate: int = 30
    
    # ========== 舞台参数 ==========
    # Ring C 半径（米，默认500，测试模式2000）
    ring_c_radius: int = 2000
    
    # Ring B 半径（米，默认200，测试模式1000）
    ring_b_radius: int = 1000
    
    # Ring A 半径（米，默认50，测试模式500）
    ring_a_radius: int = 500
    
    # 舞台同时激活数量（默认3，测试模式15）
    max_active_stages: int = 15
    
    # ========== 世界变量参数 ==========
    # 世界变量变化速度倍率（默认1.0，测试模式5.0）
    world_var_change_multiplier: float = 5.0
    
    # 世界变量自动衰减间隔（秒，默认3600，测试模式60）
    world_var_decay_interval: int = 60
    
    # ========== 测试模式开关 ==========
    # 是否启用测试模式
    test_mode_enabled: bool = True
    
    # 是否启用自动事件触发
    auto_events_enabled: bool = True
    
    # 是否启用调试日志
    debug_logging: bool = True
    
    # 是否跳过位置验证（测试时可以在任意位置触发）
    skip_location_check: bool = True
    
    # 是否启用快速Ring升级
    fast_ring_upgrade: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestModeConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# 默认配置（生产环境）
PRODUCTION_CONFIG = TestModeConfig(
    scene_change_interval=300,      # 5分钟
    event_trigger_interval=600,     # 10分钟
    gate_voting_duration=86400,     # 24小时
    evidence_cooldown=1800,         # 30分钟
    npc_dialogue_cooldown=300,      # 5分钟
    ring_upgrade_points=1000,
    base_choice_points=10,
    min_vote_participants=10,
    evidence_drop_rate=30,
    rare_evidence_drop_rate=5,
    ring_c_radius=500,
    ring_b_radius=200,
    ring_a_radius=50,
    max_active_stages=3,
    world_var_change_multiplier=1.0,
    world_var_decay_interval=3600,
    test_mode_enabled=False,
    auto_events_enabled=False,
    debug_logging=False,
    skip_location_check=False,
    fast_ring_upgrade=False
)

# 快速测试配置
QUICK_TEST_CONFIG = TestModeConfig(
    scene_change_interval=30,       # 30秒
    event_trigger_interval=15,      # 15秒
    gate_voting_duration=60,        # 1分钟
    evidence_cooldown=10,           # 10秒
    npc_dialogue_cooldown=5,        # 5秒
    ring_upgrade_points=100,
    base_choice_points=50,
    min_vote_participants=1,
    evidence_drop_rate=80,
    rare_evidence_drop_rate=30,
    ring_c_radius=2000,
    ring_b_radius=1000,
    ring_a_radius=500,
    max_active_stages=15,
    world_var_change_multiplier=5.0,
    world_var_decay_interval=60,
    test_mode_enabled=True,
    auto_events_enabled=True,
    debug_logging=True,
    skip_location_check=True,
    fast_ring_upgrade=True
)

# 极速测试配置（用于演示）
DEMO_CONFIG = TestModeConfig(
    scene_change_interval=10,       # 10秒
    event_trigger_interval=5,       # 5秒
    gate_voting_duration=30,        # 30秒
    evidence_cooldown=3,            # 3秒
    npc_dialogue_cooldown=2,        # 2秒
    ring_upgrade_points=50,
    base_choice_points=100,
    min_vote_participants=1,
    evidence_drop_rate=100,         # 100%掉落
    rare_evidence_drop_rate=50,
    ring_c_radius=5000,
    ring_b_radius=3000,
    ring_a_radius=1000,
    max_active_stages=15,
    world_var_change_multiplier=10.0,
    world_var_decay_interval=30,
    test_mode_enabled=True,
    auto_events_enabled=True,
    debug_logging=True,
    skip_location_check=True,
    fast_ring_upgrade=True
)


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional['ConfigManager'] = None
    _config: TestModeConfig = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._config = TestModeConfig.from_dict(data)
            except Exception as e:
                print(f"加载配置失败: {e}, 使用默认测试配置")
                self._config = QUICK_TEST_CONFIG
        else:
            self._config = QUICK_TEST_CONFIG
            self._save_config()
    
    def _save_config(self):
        """保存配置"""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._config.to_dict(), f, ensure_ascii=False, indent=2)
    
    @property
    def config(self) -> TestModeConfig:
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return getattr(self._config, key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            self._save_config()
            return True
        return False
    
    def update(self, updates: Dict[str, Any]) -> Dict[str, bool]:
        """批量更新配置"""
        results = {}
        for key, value in updates.items():
            results[key] = self.set(key, value)
        return results
    
    def reset_to_default(self, mode: str = 'test') -> TestModeConfig:
        """重置为默认配置
        
        Args:
            mode: 'production' | 'test' | 'demo'
        """
        if mode == 'production':
            self._config = PRODUCTION_CONFIG
        elif mode == 'demo':
            self._config = DEMO_CONFIG
        else:
            self._config = QUICK_TEST_CONFIG
        self._save_config()
        return self._config
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.to_dict()
    
    def get_preset(self, preset: str) -> Dict[str, Any]:
        """获取预设配置"""
        presets = {
            'production': PRODUCTION_CONFIG,
            'test': QUICK_TEST_CONFIG,
            'demo': DEMO_CONFIG
        }
        return presets.get(preset, QUICK_TEST_CONFIG).to_dict()


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> TestModeConfig:
    """获取当前配置"""
    return config_manager.config


def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return config_manager.get(key, default)


def set_config_value(key: str, value: Any) -> bool:
    """设置配置值"""
    return config_manager.set(key, value)


def reset_config(mode: str = 'test') -> Dict[str, Any]:
    """重置配置"""
    return config_manager.reset_to_default(mode).to_dict()
