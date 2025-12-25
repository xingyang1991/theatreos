"""
TheatreOS 测试模式管理 API
提供完整的测试模式控制、参数调整和预设管理功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import os

router = APIRouter(prefix="/v1/test-mode", tags=["测试模式"])

# ============ 数据模型 ============

class TestModeConfig(BaseModel):
    """测试模式配置"""
    # 基础开关
    test_mode_enabled: bool = True
    auto_events_enabled: bool = True
    skip_location_check: bool = True
    debug_logging: bool = True
    
    # 时间参数（秒）
    scene_switch_interval: int = Field(default=30, ge=5, le=600)
    event_trigger_interval: int = Field(default=15, ge=3, le=300)
    vote_duration: int = Field(default=60, ge=10, le=300)
    gate_cooldown: int = Field(default=30, ge=5, le=120)
    
    # 游戏参数
    ring_upgrade_points: int = Field(default=100, ge=10, le=1000)
    base_choice_points: int = Field(default=50, ge=10, le=500)
    evidence_drop_rate: float = Field(default=0.8, ge=0.0, le=1.0)
    world_var_change_multiplier: float = Field(default=5.0, ge=1.0, le=20.0)
    
    # 位置参数（米）
    ring_c_radius: int = Field(default=2000, ge=100, le=10000)
    ring_b_radius: int = Field(default=1000, ge=50, le=5000)
    ring_a_radius: int = Field(default=500, ge=10, le=2000)
    
    # 舞台参数
    max_active_stages: int = Field(default=15, ge=1, le=50)

class PresetConfig(BaseModel):
    """预设配置"""
    name: str
    description: str
    config: TestModeConfig

class TriggerEventRequest(BaseModel):
    """手动触发事件请求"""
    event_type: str  # scene_change, random_event, gate_open, world_var_change
    stage_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class TestModeStatus(BaseModel):
    """测试模式状态"""
    enabled: bool
    current_preset: Optional[str]
    config: TestModeConfig
    stats: Dict[str, Any]
    last_updated: str

# ============ 全局状态 ============

# 当前配置
_current_config = TestModeConfig()
_current_preset: Optional[str] = "quick_test"
_stats = {
    "events_triggered": 0,
    "scenes_changed": 0,
    "votes_completed": 0,
    "mode_switches": 0
}

# 预设配置库
PRESETS: Dict[str, PresetConfig] = {
    "quick_test": PresetConfig(
        name="快速测试",
        description="最短时间间隔，适合快速验证功能",
        config=TestModeConfig(
            test_mode_enabled=True,
            scene_switch_interval=15,
            event_trigger_interval=10,
            vote_duration=30,
            gate_cooldown=15,
            ring_upgrade_points=50,
            base_choice_points=100,
            evidence_drop_rate=1.0,
            skip_location_check=True
        )
    ),
    "demo": PresetConfig(
        name="演示模式",
        description="适合展示和演示的参数配置",
        config=TestModeConfig(
            test_mode_enabled=True,
            scene_switch_interval=60,
            event_trigger_interval=30,
            vote_duration=90,
            gate_cooldown=30,
            skip_location_check=True,
            auto_events_enabled=True
        )
    ),
    "stress_test": PresetConfig(
        name="压力测试",
        description="高频事件触发，用于压力测试",
        config=TestModeConfig(
            test_mode_enabled=True,
            scene_switch_interval=5,
            event_trigger_interval=3,
            vote_duration=15,
            gate_cooldown=5,
            world_var_change_multiplier=10.0,
            evidence_drop_rate=1.0
        )
    ),
    "production": PresetConfig(
        name="生产模式",
        description="正式运营参数，关闭测试功能",
        config=TestModeConfig(
            test_mode_enabled=False,
            auto_events_enabled=False,
            skip_location_check=False,
            debug_logging=False,
            scene_switch_interval=300,
            event_trigger_interval=120,
            vote_duration=180,
            gate_cooldown=60,
            ring_upgrade_points=500,
            base_choice_points=25,
            evidence_drop_rate=0.3
        )
    ),
    "balanced": PresetConfig(
        name="平衡模式",
        description="平衡的测试参数，适合日常测试",
        config=TestModeConfig(
            test_mode_enabled=True,
            scene_switch_interval=45,
            event_trigger_interval=20,
            vote_duration=60,
            gate_cooldown=30,
            ring_upgrade_points=100,
            base_choice_points=50,
            evidence_drop_rate=0.6
        )
    )
}

# 自定义预设存储
_custom_presets: Dict[str, PresetConfig] = {}

# ============ API 端点 ============

@router.get("/status", response_model=TestModeStatus)
async def get_test_mode_status():
    """获取测试模式完整状态"""
    return TestModeStatus(
        enabled=_current_config.test_mode_enabled,
        current_preset=_current_preset,
        config=_current_config,
        stats=_stats,
        last_updated=datetime.now().isoformat()
    )

@router.get("/config", response_model=TestModeConfig)
async def get_test_mode_config():
    """获取当前测试模式配置"""
    return _current_config

@router.put("/config", response_model=TestModeConfig)
async def update_test_mode_config(config: TestModeConfig):
    """更新测试模式配置"""
    global _current_config, _current_preset
    _current_config = config
    _current_preset = None  # 自定义配置，清除预设标记
    return _current_config

@router.patch("/config")
async def patch_test_mode_config(updates: Dict[str, Any]):
    """部分更新测试模式配置"""
    global _current_config, _current_preset
    config_dict = _current_config.dict()
    config_dict.update(updates)
    _current_config = TestModeConfig(**config_dict)
    _current_preset = None
    return _current_config

@router.put("/toggle")
async def toggle_test_mode(enabled: Optional[bool] = None):
    """切换测试模式开关"""
    global _current_config, _stats
    if enabled is None:
        _current_config.test_mode_enabled = not _current_config.test_mode_enabled
    else:
        _current_config.test_mode_enabled = enabled
    _stats["mode_switches"] += 1
    return {
        "test_mode_enabled": _current_config.test_mode_enabled,
        "message": "测试模式已" + ("开启" if _current_config.test_mode_enabled else "关闭")
    }

@router.get("/presets")
async def list_presets():
    """获取所有可用预设"""
    all_presets = {**PRESETS, **_custom_presets}
    return {
        "builtin": list(PRESETS.keys()),
        "custom": list(_custom_presets.keys()),
        "presets": {k: {"name": v.name, "description": v.description} for k, v in all_presets.items()}
    }

@router.get("/presets/{preset_id}")
async def get_preset(preset_id: str):
    """获取指定预设详情"""
    all_presets = {**PRESETS, **_custom_presets}
    if preset_id not in all_presets:
        raise HTTPException(status_code=404, detail=f"预设 {preset_id} 不存在")
    return all_presets[preset_id]

@router.post("/presets/{preset_id}/apply")
async def apply_preset(preset_id: str):
    """应用指定预设"""
    global _current_config, _current_preset
    all_presets = {**PRESETS, **_custom_presets}
    if preset_id not in all_presets:
        raise HTTPException(status_code=404, detail=f"预设 {preset_id} 不存在")
    
    preset = all_presets[preset_id]
    _current_config = preset.config.copy()
    _current_preset = preset_id
    
    return {
        "status": "ok",
        "preset": preset_id,
        "name": preset.name,
        "config": _current_config
    }

@router.post("/presets/custom")
async def create_custom_preset(preset_id: str, preset: PresetConfig):
    """创建自定义预设"""
    if preset_id in PRESETS:
        raise HTTPException(status_code=400, detail="不能覆盖内置预设")
    _custom_presets[preset_id] = preset
    return {"status": "ok", "preset_id": preset_id}

@router.delete("/presets/custom/{preset_id}")
async def delete_custom_preset(preset_id: str):
    """删除自定义预设"""
    if preset_id not in _custom_presets:
        raise HTTPException(status_code=404, detail=f"自定义预设 {preset_id} 不存在")
    del _custom_presets[preset_id]
    return {"status": "ok"}

@router.post("/trigger")
async def trigger_event(request: TriggerEventRequest):
    """手动触发事件"""
    global _stats
    
    event_handlers = {
        "scene_change": _trigger_scene_change,
        "random_event": _trigger_random_event,
        "gate_open": _trigger_gate_open,
        "world_var_change": _trigger_world_var_change
    }
    
    if request.event_type not in event_handlers:
        raise HTTPException(
            status_code=400, 
            detail=f"未知事件类型: {request.event_type}，可用类型: {list(event_handlers.keys())}"
        )
    
    result = await event_handlers[request.event_type](request.stage_id, request.params)
    _stats["events_triggered"] += 1
    
    return {
        "status": "ok",
        "event_type": request.event_type,
        "result": result
    }

@router.post("/reset")
async def reset_test_data(
    theatre_id: Optional[str] = None,
    reset_config: bool = False,
    reset_stats: bool = True
):
    """重置测试数据"""
    global _stats, _current_config, _current_preset
    
    result = {"reset": []}
    
    if reset_stats:
        _stats = {
            "events_triggered": 0,
            "scenes_changed": 0,
            "votes_completed": 0,
            "mode_switches": 0
        }
        result["reset"].append("stats")
    
    if reset_config:
        _current_config = TestModeConfig()
        _current_preset = "quick_test"
        result["reset"].append("config")
    
    if theatre_id:
        # TODO: 重置特定剧场数据
        result["reset"].append(f"theatre:{theatre_id}")
    
    result["message"] = "测试数据已重置"
    return result

@router.get("/stats")
async def get_test_stats():
    """获取测试统计数据"""
    return {
        "stats": _stats,
        "config_summary": {
            "test_mode": _current_config.test_mode_enabled,
            "preset": _current_preset,
            "intervals": {
                "scene": _current_config.scene_switch_interval,
                "event": _current_config.event_trigger_interval,
                "vote": _current_config.vote_duration
            }
        }
    }

# ============ 事件触发器（内部函数）============

async def _trigger_scene_change(stage_id: Optional[str], params: Optional[Dict]):
    """触发场景切换"""
    global _stats
    _stats["scenes_changed"] += 1
    # TODO: 实际调用场景切换逻辑
    return {"stage_id": stage_id, "action": "scene_changed"}

async def _trigger_random_event(stage_id: Optional[str], params: Optional[Dict]):
    """触发随机事件"""
    import random
    event_types = ["npc_appear", "item_drop", "world_change", "special_gate"]
    event = random.choice(event_types)
    return {"stage_id": stage_id, "event": event}

async def _trigger_gate_open(stage_id: Optional[str], params: Optional[Dict]):
    """触发门开启"""
    return {"stage_id": stage_id, "action": "gate_opened"}

async def _trigger_world_var_change(stage_id: Optional[str], params: Optional[Dict]):
    """触发世界变量变化"""
    var_name = params.get("var_name", "secrecy_pressure") if params else "secrecy_pressure"
    change = params.get("change", 5) if params else 5
    return {"var_name": var_name, "change": change}

# ============ 工具函数 ============

def get_current_config() -> TestModeConfig:
    """获取当前配置（供其他模块调用）"""
    return _current_config

def is_test_mode_enabled() -> bool:
    """检查测试模式是否启用"""
    return _current_config.test_mode_enabled

def should_skip_location_check() -> bool:
    """检查是否跳过位置检查"""
    return _current_config.skip_location_check
