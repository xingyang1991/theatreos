"""
TheatreOS Archive System API Routes
归档系统的完整API端点

核心功能:
- 用户参与历史
- Explain Card归档
- 故事线追溯
- 成就与统计
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import get_db_session, Base, GUID, JSONType, engine
from gate.src.gate_service import GateInstance, GateVote, GateStake, GateSettlement
from auth.src.middleware import get_current_user, require_auth, AuthContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Archive System"])


# =============================================================================
# Database Models
# =============================================================================
class ArchiveEntry(Base):
    """归档条目"""
    __tablename__ = "archive_entry"
    
    entry_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False, index=True)
    theatre_id = Column(GUID(), nullable=False)
    
    # 关联
    slot_id = Column(Text, nullable=False)
    gate_instance_id = Column(GUID(), nullable=True)
    
    # 用户行为
    action_type = Column(Text, nullable=False)  # VOTE/STAKE/EVIDENCE/WATCH
    option_chosen = Column(Text, nullable=True)
    stake_amount = Column(Float, nullable=True)
    evidence_submitted = Column(JSONType, nullable=True)
    
    # 结果
    outcome = Column(Text, nullable=True)  # WIN/LOSE/NEUTRAL
    payout = Column(Float, nullable=True)
    net_delta = Column(Float, nullable=True)
    
    # Explain Card快照
    explain_card_snapshot = Column(JSONType, nullable=True)
    
    # 时间
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    slot_start_at = Column(DateTime, nullable=True)


# Create tables
Base.metadata.create_all(bind=engine)


# =============================================================================
# Response Models
# =============================================================================
class ArchiveEntryResponse(BaseModel):
    """归档条目响应"""
    entry_id: str
    slot_id: str
    gate_instance_id: Optional[str] = None
    
    # 时间
    timestamp: str
    slot_start_at: Optional[str] = None
    hour_label: str
    
    # 门信息
    gate_title: Optional[str] = None
    gate_type: Optional[str] = None
    
    # 用户行为
    action_type: str
    action_label: str
    option_chosen: Optional[str] = None
    option_label: Optional[str] = None
    stake_amount: Optional[float] = None
    
    # 结果
    outcome: Optional[str] = None
    outcome_label: Optional[str] = None
    winner_option: Optional[str] = None
    payout: Optional[float] = None
    net_delta: Optional[float] = None
    
    # 是否有详情
    has_explain_card: bool = False


class ArchiveListResponse(BaseModel):
    """归档列表响应"""
    user_id: str
    total_count: int
    page: int
    page_size: int
    entries: List[ArchiveEntryResponse]
    
    # 统计摘要
    stats: Dict[str, Any]


class ArchiveDetailResponse(BaseModel):
    """归档详情响应"""
    entry_id: str
    slot_id: str
    gate_instance_id: Optional[str] = None
    
    # 完整Explain Card
    explain_card: Optional[Dict[str, Any]] = None
    
    # 用户参与详情
    user_participation: Dict[str, Any]
    
    # 世界状态变化
    world_state_delta: Optional[Dict[str, Any]] = None
    
    # 相关条目
    related_entries: List[Dict[str, Any]] = []


class ArchiveStatsResponse(BaseModel):
    """归档统计响应"""
    user_id: str
    
    # 参与统计
    total_participations: int
    total_votes: int
    total_stakes: int
    total_evidence_submitted: int
    
    # 胜负统计
    wins: int
    losses: int
    neutral: int
    win_rate: float
    
    # 收益统计
    total_stake_amount: float
    total_payout: float
    net_profit: float
    
    # 时间统计
    first_participation: Optional[str] = None
    last_participation: Optional[str] = None
    most_active_hour: Optional[int] = None
    
    # 故事线统计
    threads_participated: List[str] = []
    favorite_gate_type: Optional[str] = None


class StorylineResponse(BaseModel):
    """故事线响应"""
    thread_id: str
    thread_name: str
    description: Optional[str] = None
    
    # 进度
    total_gates: int
    participated_gates: int
    progress_percent: float
    
    # 关键节点
    key_moments: List[Dict[str, Any]] = []
    
    # 状态
    status: str  # ONGOING/COMPLETED/BRANCHED


# =============================================================================
# Helper Functions
# =============================================================================
ACTION_LABELS = {
    "VOTE": "投票",
    "STAKE": "下注",
    "EVIDENCE": "提交证物",
    "WATCH": "观看"
}

OUTCOME_LABELS = {
    "WIN": "押中",
    "LOSE": "未中",
    "NEUTRAL": "观望"
}


def get_hour_label(dt: datetime) -> str:
    """获取小时标签"""
    if dt is None:
        return "未知时间"
    return dt.strftime("%m月%d日 %H:00")


# =============================================================================
# API Endpoints
# =============================================================================
@router.get("/me/archive", response_model=ArchiveListResponse)
async def get_my_archive(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    action_type: Optional[str] = Query(default=None, description="筛选行为类型"),
    outcome: Optional[str] = Query(default=None, description="筛选结果"),
    start_date: Optional[str] = Query(default=None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(default=None, description="结束日期 YYYY-MM-DD"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取我的参与历史归档
    """
    # 构建查询
    query = db.query(ArchiveEntry).filter(ArchiveEntry.user_id == auth.user_id)
    
    if action_type:
        query = query.filter(ArchiveEntry.action_type == action_type)
    if outcome:
        query = query.filter(ArchiveEntry.outcome == outcome)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(ArchiveEntry.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            query = query.filter(ArchiveEntry.created_at < end_dt)
        except ValueError:
            pass
    
    total_count = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    entries_db = query.order_by(ArchiveEntry.created_at.desc()).offset(offset).limit(page_size).all()
    
    # 转换响应
    entries = []
    for entry in entries_db:
        # 获取门信息
        gate_title = None
        gate_type = None
        option_label = None
        winner_option = None
        
        if entry.gate_instance_id:
            gate = db.query(GateInstance).filter(
                GateInstance.gate_instance_id == entry.gate_instance_id
            ).first()
            if gate:
                gate_title = gate.title
                gate_type = gate.type
                winner_option = gate.winner_option_id
                # 获取选项标签
                for opt in (gate.options_jsonb or []):
                    if opt.get("option_id") == entry.option_chosen:
                        option_label = opt.get("label")
                        break
        
        entries.append(ArchiveEntryResponse(
            entry_id=str(entry.entry_id),
            slot_id=entry.slot_id,
            gate_instance_id=str(entry.gate_instance_id) if entry.gate_instance_id else None,
            timestamp=entry.created_at.isoformat(),
            slot_start_at=entry.slot_start_at.isoformat() if entry.slot_start_at else None,
            hour_label=get_hour_label(entry.slot_start_at),
            gate_title=gate_title,
            gate_type=gate_type,
            action_type=entry.action_type,
            action_label=ACTION_LABELS.get(entry.action_type, entry.action_type),
            option_chosen=entry.option_chosen,
            option_label=option_label,
            stake_amount=entry.stake_amount,
            outcome=entry.outcome,
            outcome_label=OUTCOME_LABELS.get(entry.outcome) if entry.outcome else None,
            winner_option=winner_option,
            payout=entry.payout,
            net_delta=entry.net_delta,
            has_explain_card=entry.explain_card_snapshot is not None
        ))
    
    # 统计摘要
    stats = {
        "total_participations": total_count,
        "wins": db.query(ArchiveEntry).filter(
            ArchiveEntry.user_id == auth.user_id,
            ArchiveEntry.outcome == "WIN"
        ).count(),
        "losses": db.query(ArchiveEntry).filter(
            ArchiveEntry.user_id == auth.user_id,
            ArchiveEntry.outcome == "LOSE"
        ).count()
    }
    
    return ArchiveListResponse(
        user_id=auth.user_id,
        total_count=total_count,
        page=page,
        page_size=page_size,
        entries=entries,
        stats=stats
    )


@router.get("/me/archive/{entry_id}", response_model=ArchiveDetailResponse)
async def get_archive_detail(
    entry_id: str = Path(..., description="归档条目ID"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取归档详情 - 包含完整的Explain Card
    """
    try:
        entry_uuid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entry_id format")
    
    entry = db.query(ArchiveEntry).filter(
        ArchiveEntry.entry_id == entry_uuid,
        ArchiveEntry.user_id == auth.user_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Archive entry not found")
    
    # 获取完整Explain Card
    explain_card = entry.explain_card_snapshot
    
    if not explain_card and entry.gate_instance_id:
        # 从门实例获取
        gate = db.query(GateInstance).filter(
            GateInstance.gate_instance_id == entry.gate_instance_id
        ).first()
        if gate and gate.explain_card_jsonb:
            explain_card = gate.explain_card_jsonb
    
    # 用户参与详情
    user_participation = {
        "action_type": entry.action_type,
        "option_chosen": entry.option_chosen,
        "stake_amount": entry.stake_amount,
        "evidence_submitted": entry.evidence_submitted or [],
        "outcome": entry.outcome,
        "payout": entry.payout,
        "net_delta": entry.net_delta
    }
    
    # 相关条目（同一故事线的其他参与）
    related_entries = []
    
    return ArchiveDetailResponse(
        entry_id=str(entry.entry_id),
        slot_id=entry.slot_id,
        gate_instance_id=str(entry.gate_instance_id) if entry.gate_instance_id else None,
        explain_card=explain_card,
        user_participation=user_participation,
        world_state_delta=explain_card.get("world_state_delta") if explain_card else None,
        related_entries=related_entries
    )


@router.get("/me/archive/stats", response_model=ArchiveStatsResponse)
async def get_archive_stats(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取归档统计
    """
    user_id = auth.user_id
    
    # 基础统计
    total_participations = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id
    ).count()
    
    total_votes = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.action_type == "VOTE"
    ).count()
    
    total_stakes = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.action_type == "STAKE"
    ).count()
    
    total_evidence = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.action_type == "EVIDENCE"
    ).count()
    
    # 胜负统计
    wins = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.outcome == "WIN"
    ).count()
    
    losses = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.outcome == "LOSE"
    ).count()
    
    neutral = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.outcome == "NEUTRAL"
    ).count()
    
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    
    # 收益统计
    total_stake_amount = db.query(db.func.sum(ArchiveEntry.stake_amount)).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.stake_amount != None
    ).scalar() or 0.0
    
    total_payout = db.query(db.func.sum(ArchiveEntry.payout)).filter(
        ArchiveEntry.user_id == user_id,
        ArchiveEntry.payout != None
    ).scalar() or 0.0
    
    net_profit = total_payout - total_stake_amount
    
    # 时间统计
    first_entry = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id
    ).order_by(ArchiveEntry.created_at.asc()).first()
    
    last_entry = db.query(ArchiveEntry).filter(
        ArchiveEntry.user_id == user_id
    ).order_by(ArchiveEntry.created_at.desc()).first()
    
    return ArchiveStatsResponse(
        user_id=user_id,
        total_participations=total_participations,
        total_votes=total_votes,
        total_stakes=total_stakes,
        total_evidence_submitted=total_evidence,
        wins=wins,
        losses=losses,
        neutral=neutral,
        win_rate=round(win_rate, 3),
        total_stake_amount=float(total_stake_amount),
        total_payout=float(total_payout),
        net_profit=float(net_profit),
        first_participation=first_entry.created_at.isoformat() if first_entry else None,
        last_participation=last_entry.created_at.isoformat() if last_entry else None,
        most_active_hour=None,  # 可扩展
        threads_participated=[],  # 可扩展
        favorite_gate_type=None  # 可扩展
    )


@router.get("/me/storylines")
async def get_my_storylines(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取我参与的故事线
    """
    # P0简化：返回模拟数据
    # 实际实现需要关联ThreadState和用户参与记录
    
    return {
        "user_id": auth.user_id,
        "storylines": [
            {
                "thread_id": "main_mystery",
                "thread_name": "主线：消失的密室",
                "description": "追踪神秘失踪事件的真相",
                "total_gates": 10,
                "participated_gates": 3,
                "progress_percent": 30.0,
                "status": "ONGOING",
                "key_moments": [
                    {
                        "slot_id": "slot_001",
                        "title": "第一条线索",
                        "timestamp": "2025-12-24T14:00:00Z",
                        "outcome": "发现关键证物"
                    }
                ]
            },
            {
                "thread_id": "side_quest_1",
                "thread_name": "支线：古老的预言",
                "description": "解读神秘预言的含义",
                "total_gates": 5,
                "participated_gates": 2,
                "progress_percent": 40.0,
                "status": "ONGOING",
                "key_moments": []
            }
        ]
    }


@router.post("/archive/record")
async def record_archive_entry(
    user_id: str = Query(...),
    slot_id: str = Query(...),
    gate_instance_id: Optional[str] = Query(default=None),
    action_type: str = Query(...),
    option_chosen: Optional[str] = Query(default=None),
    stake_amount: Optional[float] = Query(default=None),
    db: Session = Depends(get_db_session)
):
    """
    记录归档条目（内部API）
    
    由Gate结算等系统调用
    """
    gate_uuid = uuid.UUID(gate_instance_id) if gate_instance_id else None
    
    # 获取门信息以确定结果
    outcome = None
    payout = None
    net_delta = None
    explain_card_snapshot = None
    slot_start_at = None
    
    if gate_uuid:
        gate = db.query(GateInstance).filter(
            GateInstance.gate_instance_id == gate_uuid
        ).first()
        
        if gate:
            slot_start_at = gate.open_at - timedelta(minutes=10)  # 估算
            
            if gate.status == "RESOLVED":
                if option_chosen == gate.winner_option_id:
                    outcome = "WIN"
                elif option_chosen:
                    outcome = "LOSE"
                else:
                    outcome = "NEUTRAL"
                
                explain_card_snapshot = gate.explain_card_jsonb
                
                # 获取结算信息
                settlement = db.query(GateSettlement).filter(
                    GateSettlement.gate_instance_id == gate_uuid,
                    GateSettlement.user_id == user_id
                ).first()
                
                if settlement:
                    payout = float(settlement.payout)
                    net_delta = float(settlement.net_delta)
    
    # 创建归档条目
    entry = ArchiveEntry(
        user_id=user_id,
        theatre_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # 应从gate获取
        slot_id=slot_id,
        gate_instance_id=gate_uuid,
        action_type=action_type,
        option_chosen=option_chosen,
        stake_amount=stake_amount,
        outcome=outcome,
        payout=payout,
        net_delta=net_delta,
        explain_card_snapshot=explain_card_snapshot,
        slot_start_at=slot_start_at
    )
    
    db.add(entry)
    db.commit()
    
    return {
        "success": True,
        "entry_id": str(entry.entry_id)
    }
