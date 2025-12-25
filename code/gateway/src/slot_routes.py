"""
TheatreOS Slot & Showbill API Routes
实现Slot节拍与场景播放流程的API端点

核心功能:
- 戏单展示（未来N小时的Slot列表）
- Slot详情（包含所有舞台和门信息）
- 阶段状态与倒计时
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import get_db_session, Theatre, HourPlan, PublishedSlot
from config.settings import SLOT_DURATION_MINUTES, GATE_RESOLVE_MINUTE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Slot & Showbill"])


# =============================================================================
# Enums
# =============================================================================
class SlotPhase(str, Enum):
    """Slot阶段"""
    UPCOMING = "upcoming"      # 即将开始
    WATCHING = "watching"      # 看戏阶段 (T+0 ~ T+10)
    GATE_OPEN = "gate_open"    # 门厅开放 (T+10 ~ T+12)
    RESOLVING = "resolving"    # 结算中 (T+12)
    ECHO = "echo"              # 回声阶段 (T+12 ~ T+15)
    COMPLETED = "completed"    # 已完成


# =============================================================================
# Response Models
# =============================================================================
class StageCardResponse(BaseModel):
    """舞台卡片响应"""
    stage_id: str
    name: str
    scene_title: Optional[str] = None
    scene_type: Optional[str] = None
    ring_level: str = "C"
    thumbnail_url: Optional[str] = None
    has_gate: bool = False
    gate_type: Optional[str] = None


class SlotResponse(BaseModel):
    """Slot响应"""
    slot_id: str
    start_at: str
    end_at: str
    phase: SlotPhase
    phase_label: str
    countdown_seconds: int
    next_phase: Optional[SlotPhase] = None
    next_phase_at: Optional[str] = None
    stages: List[StageCardResponse] = []
    hour_label: str


class ShowbillResponse(BaseModel):
    """戏单响应"""
    theatre_id: str
    current_time: str
    timezone: str
    lookahead_hours: int
    slots: List[SlotResponse]
    current_slot_id: Optional[str] = None


class SlotDetailResponse(BaseModel):
    """Slot详情响应"""
    slot_id: str
    theatre_id: str
    start_at: str
    end_at: str
    phase: SlotPhase
    phase_label: str
    phase_progress: float  # 0.0 ~ 1.0
    countdown_to_gate_open: Optional[int] = None
    countdown_to_resolve: Optional[int] = None
    countdown_to_end: int
    stages: List[Dict[str, Any]]
    gate: Optional[Dict[str, Any]] = None
    world_state_snapshot: Optional[Dict[str, Any]] = None


class PhaseTimingResponse(BaseModel):
    """阶段时间响应"""
    slot_id: str
    current_phase: SlotPhase
    phases: List[Dict[str, Any]]


# =============================================================================
# Helper Functions
# =============================================================================
def calculate_slot_phase(slot_start: datetime, now: datetime = None) -> tuple:
    """
    计算Slot当前阶段
    
    Returns:
        (phase, phase_label, countdown_seconds, next_phase, next_phase_at)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    # 确保时区一致
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)
    gate_open_at = slot_start + timedelta(minutes=10)
    gate_close_at = slot_start + timedelta(minutes=GATE_RESOLVE_MINUTE)
    echo_end_at = slot_start + timedelta(minutes=15)
    
    if now < slot_start:
        # 即将开始
        countdown = int((slot_start - now).total_seconds())
        return (SlotPhase.UPCOMING, "即将开始", countdown, SlotPhase.WATCHING, slot_start.isoformat())
    
    elif now < gate_open_at:
        # 看戏阶段
        countdown = int((gate_open_at - now).total_seconds())
        return (SlotPhase.WATCHING, "正在上演", countdown, SlotPhase.GATE_OPEN, gate_open_at.isoformat())
    
    elif now < gate_close_at:
        # 门厅开放
        countdown = int((gate_close_at - now).total_seconds())
        return (SlotPhase.GATE_OPEN, "门厅开放", countdown, SlotPhase.RESOLVING, gate_close_at.isoformat())
    
    elif now < echo_end_at:
        # 结算/回声阶段
        countdown = int((echo_end_at - now).total_seconds())
        if now < gate_close_at + timedelta(seconds=30):
            return (SlotPhase.RESOLVING, "结算中", countdown, SlotPhase.ECHO, echo_end_at.isoformat())
        return (SlotPhase.ECHO, "回声时刻", countdown, SlotPhase.COMPLETED, slot_end.isoformat())
    
    else:
        # 已完成
        return (SlotPhase.COMPLETED, "已结束", 0, None, None)


def get_hour_label(dt: datetime) -> str:
    """获取小时标签，如 '14:00 - 15:00'"""
    hour_start = dt.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)
    return f"{hour_start.strftime('%H:%M')} - {hour_end.strftime('%H:%M')}"


# =============================================================================
# API Endpoints
# =============================================================================
@router.get("/theatres/{theatre_id}/showbill", response_model=ShowbillResponse)
async def get_showbill(
    theatre_id: str = Path(..., description="Theatre ID"),
    lookahead_hours: int = Query(default=2, ge=1, le=6, description="展示未来几小时"),
    db: Session = Depends(get_db_session)
):
    """
    获取戏单 - 展示未来N小时的演出安排
    
    返回按小时分组的Slot列表，每个Slot包含:
    - 阶段状态和倒计时
    - 所有舞台的卡片信息
    - 门的基本信息
    """
    try:
        theatre_uuid = uuid.UUID(theatre_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid theatre_id format")
    
    # 获取剧场
    theatre = db.query(Theatre).filter(Theatre.theatre_id == theatre_uuid).first()
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")
    
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    
    # 获取未来N小时的HourPlan
    end_time = current_hour + timedelta(hours=lookahead_hours)
    
    hour_plans = db.query(HourPlan).filter(
        HourPlan.theatre_id == theatre_uuid,
        HourPlan.start_at >= current_hour,
        HourPlan.start_at < end_time
    ).order_by(HourPlan.start_at).all()
    
    slots = []
    current_slot_id = None
    
    for hp in hour_plans:
        slot_start = hp.start_at
        if slot_start.tzinfo is None:
            slot_start = slot_start.replace(tzinfo=timezone.utc)
        
        phase, phase_label, countdown, next_phase, next_phase_at = calculate_slot_phase(slot_start, now)
        
        # 标记当前正在进行的Slot
        if phase in [SlotPhase.WATCHING, SlotPhase.GATE_OPEN, SlotPhase.RESOLVING, SlotPhase.ECHO]:
            current_slot_id = hp.slot_id
        
        # 构建舞台卡片列表
        stages = []
        scenes_config = hp.target_beat_mix_jsonb or {}
        
        # 从scenes_config中提取舞台信息
        if isinstance(scenes_config, dict):
            for stage_id, scene_info in scenes_config.items():
                if isinstance(scene_info, dict):
                    stages.append(StageCardResponse(
                        stage_id=stage_id,
                        name=scene_info.get("stage_name", stage_id),
                        scene_title=scene_info.get("title", "未知场景"),
                        scene_type=scene_info.get("beat_type", "standard"),
                        ring_level="C",
                        thumbnail_url=scene_info.get("thumbnail"),
                        has_gate=True,
                        gate_type=hp.hour_gate_jsonb.get("type", "Public") if hp.hour_gate_jsonb else "Public"
                    ))
        
        # 如果没有配置，使用默认舞台
        if not stages:
            stages = [
                StageCardResponse(
                    stage_id="default_stage",
                    name="主舞台",
                    scene_title="场景准备中",
                    scene_type="standard",
                    ring_level="C",
                    has_gate=True,
                    gate_type="Public"
                )
            ]
        
        slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)
        
        slots.append(SlotResponse(
            slot_id=hp.slot_id,
            start_at=slot_start.isoformat(),
            end_at=slot_end.isoformat(),
            phase=phase,
            phase_label=phase_label,
            countdown_seconds=countdown,
            next_phase=next_phase,
            next_phase_at=next_phase_at,
            stages=stages,
            hour_label=get_hour_label(slot_start)
        ))
    
    # 如果没有HourPlan，生成占位Slot
    if not slots:
        for i in range(lookahead_hours):
            slot_start = current_hour + timedelta(hours=i)
            slot_id = f"slot_{slot_start.strftime('%Y%m%d_%H%M')}"
            phase, phase_label, countdown, next_phase, next_phase_at = calculate_slot_phase(slot_start, now)
            
            slots.append(SlotResponse(
                slot_id=slot_id,
                start_at=slot_start.isoformat(),
                end_at=(slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)).isoformat(),
                phase=phase,
                phase_label=phase_label,
                countdown_seconds=countdown,
                next_phase=next_phase,
                next_phase_at=next_phase_at,
                stages=[
                    StageCardResponse(
                        stage_id="placeholder",
                        name="舞台准备中",
                        scene_title="敬请期待",
                        ring_level="C",
                        has_gate=False
                    )
                ],
                hour_label=get_hour_label(slot_start)
            ))
    
    return ShowbillResponse(
        theatre_id=theatre_id,
        current_time=now.isoformat(),
        timezone=theatre.timezone or "Asia/Shanghai",
        lookahead_hours=lookahead_hours,
        slots=slots,
        current_slot_id=current_slot_id
    )


@router.get("/slots/{slot_id}/details", response_model=SlotDetailResponse)
async def get_slot_details(
    slot_id: str = Path(..., description="Slot ID"),
    db: Session = Depends(get_db_session)
):
    """
    获取Slot详情 - 包含所有舞台和门的详细信息
    
    返回:
    - 阶段状态和进度
    - 各阶段倒计时
    - 所有舞台的详细场景信息
    - 门的配置和状态
    """
    # 查找HourPlan
    hour_plan = db.query(HourPlan).filter(HourPlan.slot_id == slot_id).first()
    
    if not hour_plan:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    now = datetime.now(timezone.utc)
    slot_start = hour_plan.start_at
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)
    
    slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MINUTES)
    gate_open_at = slot_start + timedelta(minutes=10)
    gate_close_at = slot_start + timedelta(minutes=GATE_RESOLVE_MINUTE)
    
    phase, phase_label, _, _, _ = calculate_slot_phase(slot_start, now)
    
    # 计算阶段进度
    if phase == SlotPhase.UPCOMING:
        phase_progress = 0.0
    elif phase == SlotPhase.WATCHING:
        elapsed = (now - slot_start).total_seconds()
        phase_progress = min(elapsed / 600, 1.0)  # 10分钟
    elif phase == SlotPhase.GATE_OPEN:
        elapsed = (now - gate_open_at).total_seconds()
        phase_progress = min(elapsed / 120, 1.0)  # 2分钟
    elif phase in [SlotPhase.RESOLVING, SlotPhase.ECHO]:
        phase_progress = 1.0
    else:
        phase_progress = 1.0
    
    # 计算各阶段倒计时
    countdown_to_gate_open = max(0, int((gate_open_at - now).total_seconds())) if now < gate_open_at else None
    countdown_to_resolve = max(0, int((gate_close_at - now).total_seconds())) if now < gate_close_at else None
    countdown_to_end = max(0, int((slot_end - now).total_seconds()))
    
    # 构建舞台详情
    stages = []
    scenes_config = hour_plan.target_beat_mix_jsonb or {}
    
    if isinstance(scenes_config, dict):
        for stage_id, scene_info in scenes_config.items():
            if isinstance(scene_info, dict):
                stages.append({
                    "stage_id": stage_id,
                    "name": scene_info.get("stage_name", stage_id),
                    "scene": {
                        "scene_id": scene_info.get("scene_id", f"scene_{slot_id}_{stage_id}"),
                        "title": scene_info.get("title", "未知场景"),
                        "beat_type": scene_info.get("beat_type", "standard"),
                        "media_url": scene_info.get("media_url"),
                        "thumbnail_url": scene_info.get("thumbnail"),
                        "duration_seconds": scene_info.get("duration", 600),
                        "fallback_available": True
                    },
                    "ring_level": "C",
                    "is_live": phase in [SlotPhase.WATCHING, SlotPhase.GATE_OPEN]
                })
    
    # 构建门信息
    gate_info = None
    if hour_plan.hour_gate_jsonb:
        gate_config = hour_plan.hour_gate_jsonb
        gate_info = {
            "gate_template_id": gate_config.get("template_id", "default"),
            "type": gate_config.get("type", "Public"),
            "title": gate_config.get("title", f"本小时之门"),
            "options": gate_config.get("options", [
                {"option_id": "opt_a", "label": "选项A"},
                {"option_id": "opt_b", "label": "选项B"}
            ]),
            "open_at": gate_open_at.isoformat(),
            "close_at": gate_close_at.isoformat(),
            "status": "open" if phase == SlotPhase.GATE_OPEN else ("closed" if phase in [SlotPhase.RESOLVING, SlotPhase.ECHO, SlotPhase.COMPLETED] else "scheduled"),
            "evidence_slots": gate_config.get("evidence_slots", 1),
            "stake_allowed": gate_config.get("stake_allowed", True),
            "risk_hint": gate_config.get("risk_hint", "此门将影响世界状态")
        }
    
    return SlotDetailResponse(
        slot_id=slot_id,
        theatre_id=str(hour_plan.theatre_id),
        start_at=slot_start.isoformat(),
        end_at=slot_end.isoformat(),
        phase=phase,
        phase_label=phase_label,
        phase_progress=phase_progress,
        countdown_to_gate_open=countdown_to_gate_open,
        countdown_to_resolve=countdown_to_resolve,
        countdown_to_end=countdown_to_end,
        stages=stages,
        gate=gate_info,
        world_state_snapshot=None  # 可选：当前世界状态快照
    )


@router.get("/slots/{slot_id}/phase", response_model=PhaseTimingResponse)
async def get_slot_phase_timing(
    slot_id: str = Path(..., description="Slot ID"),
    db: Session = Depends(get_db_session)
):
    """
    获取Slot阶段时间线 - 用于前端倒计时和状态切换
    
    返回所有阶段的时间点和当前阶段
    """
    hour_plan = db.query(HourPlan).filter(HourPlan.slot_id == slot_id).first()
    
    if not hour_plan:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    now = datetime.now(timezone.utc)
    slot_start = hour_plan.start_at
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)
    
    phase, _, _, _, _ = calculate_slot_phase(slot_start, now)
    
    # 构建阶段时间线
    phases = [
        {
            "phase": SlotPhase.UPCOMING.value,
            "label": "即将开始",
            "start_at": None,
            "end_at": slot_start.isoformat()
        },
        {
            "phase": SlotPhase.WATCHING.value,
            "label": "看戏阶段",
            "start_at": slot_start.isoformat(),
            "end_at": (slot_start + timedelta(minutes=10)).isoformat()
        },
        {
            "phase": SlotPhase.GATE_OPEN.value,
            "label": "门厅开放",
            "start_at": (slot_start + timedelta(minutes=10)).isoformat(),
            "end_at": (slot_start + timedelta(minutes=GATE_RESOLVE_MINUTE)).isoformat()
        },
        {
            "phase": SlotPhase.RESOLVING.value,
            "label": "结算中",
            "start_at": (slot_start + timedelta(minutes=GATE_RESOLVE_MINUTE)).isoformat(),
            "end_at": (slot_start + timedelta(minutes=GATE_RESOLVE_MINUTE, seconds=30)).isoformat()
        },
        {
            "phase": SlotPhase.ECHO.value,
            "label": "回声时刻",
            "start_at": (slot_start + timedelta(minutes=GATE_RESOLVE_MINUTE, seconds=30)).isoformat(),
            "end_at": (slot_start + timedelta(minutes=15)).isoformat()
        },
        {
            "phase": SlotPhase.COMPLETED.value,
            "label": "已结束",
            "start_at": (slot_start + timedelta(minutes=15)).isoformat(),
            "end_at": None
        }
    ]
    
    return PhaseTimingResponse(
        slot_id=slot_id,
        current_phase=phase,
        phases=phases
    )


@router.get("/theatres/{theatre_id}/current-slot")
async def get_current_slot(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """
    获取当前正在进行的Slot
    
    返回当前Slot的ID和阶段，如果没有正在进行的Slot则返回下一个即将开始的Slot
    """
    try:
        theatre_uuid = uuid.UUID(theatre_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid theatre_id format")
    
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    
    # 查找当前小时的HourPlan
    hour_plan = db.query(HourPlan).filter(
        HourPlan.theatre_id == theatre_uuid,
        HourPlan.start_at >= current_hour,
        HourPlan.start_at < current_hour + timedelta(hours=1)
    ).first()
    
    if not hour_plan:
        # 查找下一个HourPlan
        hour_plan = db.query(HourPlan).filter(
            HourPlan.theatre_id == theatre_uuid,
            HourPlan.start_at >= now
        ).order_by(HourPlan.start_at).first()
    
    if not hour_plan:
        return {
            "has_current": False,
            "next_slot_id": None,
            "message": "暂无演出安排"
        }
    
    slot_start = hour_plan.start_at
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=timezone.utc)
    
    phase, phase_label, countdown, _, _ = calculate_slot_phase(slot_start, now)
    
    return {
        "has_current": phase not in [SlotPhase.UPCOMING, SlotPhase.COMPLETED],
        "slot_id": hour_plan.slot_id,
        "phase": phase.value,
        "phase_label": phase_label,
        "countdown_seconds": countdown,
        "start_at": slot_start.isoformat()
    }
