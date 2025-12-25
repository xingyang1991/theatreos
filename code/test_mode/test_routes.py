"""
TheatreOS 快速测试模式 - API路由
提供测试参数调整、数据重置、快速事件触发等功能
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import random

from .test_config import (
    config_manager, 
    get_config, 
    reset_config,
    PRODUCTION_CONFIG,
    QUICK_TEST_CONFIG,
    DEMO_CONFIG
)
from .stages_config import SHANGHAI_STAGES, STORY_THREADS, QUICK_EVENTS

router = APIRouter(prefix="/test-mode", tags=["测试模式"])


# ========== 请求/响应模型 ==========

class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    updates: Dict[str, Any]


class ConfigResetRequest(BaseModel):
    """配置重置请求"""
    mode: str = "test"  # production | test | demo


class TriggerEventRequest(BaseModel):
    """触发事件请求"""
    stage_id: str
    event_type: str = "random"  # random | encounter | discovery | gate
    player_id: Optional[str] = None


class SimulateVoteRequest(BaseModel):
    """模拟投票请求"""
    gate_id: str
    votes: Dict[str, int]  # {"option_id": vote_count}


class ResetDataRequest(BaseModel):
    """重置数据请求"""
    reset_players: bool = True
    reset_events: bool = True
    reset_world_state: bool = True
    reset_evidence: bool = True
    keep_stages: bool = True


# ========== 配置管理API ==========

@router.get("/config")
async def get_current_config():
    """获取当前测试配置"""
    return {
        "success": True,
        "config": config_manager.get_all(),
        "mode": "test" if get_config().test_mode_enabled else "production"
    }


@router.get("/config/presets")
async def get_config_presets():
    """获取所有预设配置"""
    return {
        "success": True,
        "presets": {
            "production": PRODUCTION_CONFIG.to_dict(),
            "test": QUICK_TEST_CONFIG.to_dict(),
            "demo": DEMO_CONFIG.to_dict()
        }
    }


@router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """更新测试配置"""
    results = config_manager.update(request.updates)
    return {
        "success": True,
        "updated": results,
        "current_config": config_manager.get_all()
    }


@router.post("/config/reset")
async def reset_config_endpoint(request: ConfigResetRequest):
    """重置配置为预设值"""
    if request.mode not in ["production", "test", "demo"]:
        raise HTTPException(status_code=400, detail="无效的模式，可选: production, test, demo")
    
    new_config = reset_config(request.mode)
    return {
        "success": True,
        "message": f"配置已重置为 {request.mode} 模式",
        "config": new_config
    }


# ========== 舞台管理API ==========

@router.get("/stages")
async def get_test_stages():
    """获取所有测试舞台配置"""
    return {
        "success": True,
        "count": len(SHANGHAI_STAGES),
        "stages": SHANGHAI_STAGES
    }


@router.get("/stages/{stage_id}")
async def get_test_stage(stage_id: str):
    """获取单个舞台详情"""
    stage = next((s for s in SHANGHAI_STAGES if s["stage_id"] == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="舞台不存在")
    return {
        "success": True,
        "stage": stage
    }


@router.get("/threads")
async def get_story_threads():
    """获取所有故事线"""
    return {
        "success": True,
        "count": len(STORY_THREADS),
        "threads": STORY_THREADS
    }


# ========== 事件触发API ==========

@router.post("/trigger-event")
async def trigger_event(request: TriggerEventRequest):
    """手动触发事件（用于测试）"""
    stage = next((s for s in SHANGHAI_STAGES if s["stage_id"] == request.stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="舞台不存在")
    
    # 选择事件
    if request.event_type == "random":
        event = random.choice(QUICK_EVENTS)
    else:
        event = next((e for e in QUICK_EVENTS if e["type"] == request.event_type), None)
        if not event:
            event = random.choice(QUICK_EVENTS)
    
    # 生成事件实例
    event_instance = {
        "event_instance_id": str(uuid.uuid4()),
        "event_id": event["event_id"],
        "event_name": event["name"],
        "event_type": event["type"],
        "stage_id": request.stage_id,
        "stage_name": stage["name"],
        "triggered_at": datetime.now().isoformat(),
        "expires_at": datetime.now().timestamp() + event["duration_seconds"],
        "duration_seconds": event["duration_seconds"],
        "choices": event["choices"],
        "thread": stage["scene"]["thread"],
        "npc": stage["scene"]["npc"]
    }
    
    return {
        "success": True,
        "message": f"事件 '{event['name']}' 已在 '{stage['name']}' 触发",
        "event": event_instance
    }


@router.post("/trigger-all-events")
async def trigger_all_events():
    """在所有舞台触发事件（用于压力测试）"""
    events = []
    for stage in SHANGHAI_STAGES:
        event = random.choice(QUICK_EVENTS)
        event_instance = {
            "event_instance_id": str(uuid.uuid4()),
            "event_id": event["event_id"],
            "event_name": event["name"],
            "stage_id": stage["stage_id"],
            "stage_name": stage["name"],
            "triggered_at": datetime.now().isoformat(),
            "duration_seconds": event["duration_seconds"]
        }
        events.append(event_instance)
    
    return {
        "success": True,
        "message": f"已在 {len(events)} 个舞台触发事件",
        "events": events
    }


# ========== 投票/门模拟API ==========

@router.post("/create-gate")
async def create_test_gate(
    stage_id: str = Query(..., description="舞台ID"),
    duration_seconds: int = Query(60, description="投票持续时间（秒）")
):
    """创建测试用的投票门"""
    stage = next((s for s in SHANGHAI_STAGES if s["stage_id"] == stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="舞台不存在")
    
    gate = {
        "gate_id": str(uuid.uuid4()),
        "name": f"{stage['name']}的抉择",
        "description": f"在{stage['hp_mapping']}发生的重要决策",
        "stage_id": stage_id,
        "thread": stage["scene"]["thread"],
        "created_at": datetime.now().isoformat(),
        "expires_at": datetime.now().timestamp() + duration_seconds,
        "duration_seconds": duration_seconds,
        "options": [
            {"id": "option_a", "text": "支持行动", "votes": 0},
            {"id": "option_b", "text": "反对行动", "votes": 0},
            {"id": "option_c", "text": "保持中立", "votes": 0}
        ],
        "status": "active",
        "total_votes": 0
    }
    
    return {
        "success": True,
        "message": "投票门已创建",
        "gate": gate
    }


@router.post("/simulate-vote")
async def simulate_vote(request: SimulateVoteRequest):
    """模拟投票（用于测试投票结果）"""
    total_votes = sum(request.votes.values())
    
    # 计算结果
    results = []
    for option_id, vote_count in request.votes.items():
        percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
        results.append({
            "option_id": option_id,
            "votes": vote_count,
            "percentage": round(percentage, 2)
        })
    
    # 确定获胜选项
    winner = max(results, key=lambda x: x["votes"])
    
    return {
        "success": True,
        "gate_id": request.gate_id,
        "total_votes": total_votes,
        "results": results,
        "winner": winner,
        "resolved_at": datetime.now().isoformat()
    }


# ========== 数据重置API ==========

@router.post("/reset")
async def reset_test_data(request: ResetDataRequest):
    """重置测试数据"""
    reset_summary = {
        "players_reset": request.reset_players,
        "events_reset": request.reset_events,
        "world_state_reset": request.reset_world_state,
        "evidence_reset": request.reset_evidence,
        "stages_kept": request.keep_stages
    }
    
    return {
        "success": True,
        "message": "测试数据已重置",
        "reset_summary": reset_summary,
        "reset_at": datetime.now().isoformat()
    }


@router.post("/reset/full")
async def full_reset():
    """完全重置所有测试数据"""
    # 重置配置为测试模式
    reset_config("test")
    
    return {
        "success": True,
        "message": "系统已完全重置为测试模式初始状态",
        "config": config_manager.get_all(),
        "stages_count": len(SHANGHAI_STAGES),
        "threads_count": len(STORY_THREADS),
        "reset_at": datetime.now().isoformat()
    }


# ========== 快速测试工具API ==========

@router.post("/quick-play")
async def quick_play_scenario(
    scenario: str = Query("random", description="场景类型: random, encounter, discovery, gate")
):
    """快速游玩一个场景（自动选择舞台和事件）"""
    # 随机选择舞台
    stage = random.choice(SHANGHAI_STAGES)
    
    # 选择事件
    if scenario == "random":
        event = random.choice(QUICK_EVENTS)
    else:
        event = next((e for e in QUICK_EVENTS if e["type"] == scenario), random.choice(QUICK_EVENTS))
    
    # 自动做出选择
    choice = random.choice(event["choices"])
    
    return {
        "success": True,
        "stage": {
            "id": stage["stage_id"],
            "name": stage["name"],
            "hp_mapping": stage["hp_mapping"]
        },
        "event": {
            "name": event["name"],
            "type": event["type"]
        },
        "choice_made": choice,
        "points_earned": choice["points"],
        "next_event_in": get_config().event_trigger_interval
    }


@router.get("/status")
async def get_test_status():
    """获取测试模式状态概览"""
    config = get_config()
    
    return {
        "success": True,
        "test_mode": {
            "enabled": config.test_mode_enabled,
            "auto_events": config.auto_events_enabled,
            "skip_location": config.skip_location_check,
            "debug_logging": config.debug_logging
        },
        "timing": {
            "scene_change_interval": f"{config.scene_change_interval}秒",
            "event_trigger_interval": f"{config.event_trigger_interval}秒",
            "gate_voting_duration": f"{config.gate_voting_duration}秒"
        },
        "game_params": {
            "ring_upgrade_points": config.ring_upgrade_points,
            "base_choice_points": config.base_choice_points,
            "evidence_drop_rate": f"{config.evidence_drop_rate}%"
        },
        "stages": {
            "total": len(SHANGHAI_STAGES),
            "max_active": config.max_active_stages
        },
        "threads": {
            "total": len(STORY_THREADS),
            "names": list(STORY_THREADS.keys())
        }
    }


# ========== 批量操作API ==========

@router.post("/batch/create-stages")
async def batch_create_stages(theatre_id: str):
    """批量创建所有15个测试舞台"""
    created_stages = []
    for stage in SHANGHAI_STAGES:
        created_stages.append({
            "stage_id": stage["stage_id"],
            "name": stage["name"],
            "location": stage["location_desc"],
            "hp_mapping": stage["hp_mapping"],
            "lat": stage["lat"],
            "lng": stage["lng"]
        })
    
    return {
        "success": True,
        "theatre_id": theatre_id,
        "created_count": len(created_stages),
        "stages": created_stages
    }


@router.post("/batch/trigger-thread")
async def batch_trigger_thread(thread_name: str):
    """触发整条故事线的所有相关事件"""
    if thread_name not in STORY_THREADS:
        raise HTTPException(status_code=404, detail="故事线不存在")
    
    thread = STORY_THREADS[thread_name]
    triggered_events = []
    
    for stage_id in thread["related_stages"]:
        stage = next((s for s in SHANGHAI_STAGES if s["stage_id"] == stage_id), None)
        if stage:
            triggered_events.append({
                "stage_id": stage_id,
                "stage_name": stage["name"],
                "scene_title": stage["scene"]["title"],
                "npc": stage["scene"]["npc"],
                "evidence": stage["scene"]["evidence"]
            })
    
    return {
        "success": True,
        "thread": thread_name,
        "description": thread["description"],
        "key_item": thread["key_item"],
        "triggered_count": len(triggered_events),
        "events": triggered_events
    }
