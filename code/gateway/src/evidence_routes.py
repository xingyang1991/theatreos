"""
TheatreOS Evidence System API Routes
证物系统的完整API端点

核心功能:
- 用户证物列表（证物柜）
- 证物详情
- 证物验证
- 证物发放（内部调用）
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import get_db_session, Base, GUID, JSONType, engine
from auth.src.middleware import get_current_user, require_auth, AuthContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Evidence System"])


# =============================================================================
# Database Models
# =============================================================================
class EvidenceInstanceDB(Base):
    """证物实例数据库模型"""
    __tablename__ = "evidence_instance"
    
    instance_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    type_id = Column(Text, nullable=False)
    tier = Column(Text, nullable=False)  # A/B/C/D
    owner_id = Column(Text, nullable=False)
    theatre_id = Column(GUID(), nullable=False)
    
    # 来源
    source = Column(Text, nullable=False)  # SCENE/TRADE/GATE_REWARD/CREW_SHARE/SYSTEM
    source_scene_id = Column(Text, nullable=True)
    source_slot_id = Column(Text, nullable=True)
    source_stage_id = Column(Text, nullable=True)
    
    # 状态
    status = Column(Text, nullable=False, default="ACTIVE")  # ACTIVE/SUBMITTED/EXPIRED/CONSUMED
    verification_status = Column(Text, nullable=False, default="UNVERIFIED")  # UNVERIFIED/VERIFIED/FORGED/PENDING
    
    # 时间
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # 元数据
    name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    content_hash = Column(Text, nullable=True)
    metadata_json = Column(JSONType, nullable=True)
    
    # 伪造相关
    is_forged = Column(Boolean, nullable=False, default=False)


# Create tables
Base.metadata.create_all(bind=engine)


# =============================================================================
# Response Models
# =============================================================================
class EvidenceResponse(BaseModel):
    """证物响应"""
    instance_id: str
    type_id: str
    name: str
    description: Optional[str] = None
    tier: str
    tier_label: str
    status: str
    status_label: str
    verification_status: str
    
    # 来源信息
    source: str
    source_scene_id: Optional[str] = None
    source_slot_id: Optional[str] = None
    source_stage_id: Optional[str] = None
    
    # 时间
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool
    time_until_expiry: Optional[int] = None  # 秒
    
    # 可用性
    can_submit: bool
    can_verify: bool
    can_trade: bool


class EvidenceListResponse(BaseModel):
    """证物列表响应"""
    user_id: str
    total_count: int
    active_count: int
    submitted_count: int
    expired_count: int
    evidence: List[EvidenceResponse]


class EvidenceDetailResponse(BaseModel):
    """证物详情响应"""
    instance_id: str
    type_id: str
    name: str
    description: Optional[str] = None
    tier: str
    tier_label: str
    tier_description: str
    
    status: str
    status_label: str
    verification_status: str
    verification_label: str
    
    # 来源追溯
    source: str
    source_label: str
    source_scene_id: Optional[str] = None
    source_slot_id: Optional[str] = None
    source_stage_id: Optional[str] = None
    source_timestamp: str
    
    # 时间线
    created_at: str
    expires_at: Optional[str] = None
    verified_at: Optional[str] = None
    
    # 使用历史
    submission_history: List[Dict[str, Any]] = []
    
    # 元数据
    content_preview: Optional[str] = None
    metadata: Dict[str, Any] = {}


class VerifyEvidenceRequest(BaseModel):
    """验证证物请求"""
    method: str = Field(default="standard", description="验证方式: standard/location/expert")


class VerifyEvidenceResponse(BaseModel):
    """验证证物响应"""
    success: bool
    instance_id: str
    new_verification_status: str
    verification_result: str
    cost_paid: int
    timestamp: str


class GrantEvidenceRequest(BaseModel):
    """发放证物请求（内部）"""
    user_id: str
    type_id: str
    tier: str
    theatre_id: str
    source: str
    source_scene_id: Optional[str] = None
    source_slot_id: Optional[str] = None
    source_stage_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    expires_in_hours: Optional[int] = 24


# =============================================================================
# Helper Functions
# =============================================================================
TIER_INFO = {
    "A": {"label": "硬证物", "description": "关键门前置，稀缺，通常来自RingB/A或高风险场"},
    "B": {"label": "可信线索", "description": "用于读底概率与验证传闻"},
    "C": {"label": "噪声线索", "description": "可误读，推动讨论与交易"},
    "D": {"label": "碎片与环境", "description": "用于氛围与考古，不强推结算"}
}

STATUS_INFO = {
    "ACTIVE": {"label": "可用"},
    "SUBMITTED": {"label": "已提交"},
    "EXPIRED": {"label": "已过期"},
    "CONSUMED": {"label": "已消耗"},
    "TRADED": {"label": "已交易"}
}

SOURCE_INFO = {
    "SCENE": {"label": "场景产出"},
    "TRADE": {"label": "交易获得"},
    "GATE_REWARD": {"label": "门奖励"},
    "CREW_SHARE": {"label": "剧团共享"},
    "SYSTEM": {"label": "系统发放"}
}

VERIFICATION_INFO = {
    "UNVERIFIED": {"label": "未验证"},
    "VERIFIED": {"label": "已验证"},
    "FORGED": {"label": "伪造品"},
    "PENDING": {"label": "验证中"}
}


def evidence_to_response(evidence: EvidenceInstanceDB) -> EvidenceResponse:
    """将数据库模型转换为响应模型"""
    now = datetime.now(timezone.utc)
    
    expires_at = evidence.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    is_expired = expires_at and now > expires_at if expires_at else False
    time_until_expiry = None
    if expires_at and not is_expired:
        time_until_expiry = int((expires_at - now).total_seconds())
    
    tier_info = TIER_INFO.get(evidence.tier, {"label": evidence.tier})
    status_info = STATUS_INFO.get(evidence.status, {"label": evidence.status})
    
    can_submit = evidence.status == "ACTIVE" and not is_expired
    can_verify = evidence.verification_status == "UNVERIFIED" and evidence.status == "ACTIVE"
    can_trade = evidence.status == "ACTIVE" and not is_expired
    
    return EvidenceResponse(
        instance_id=str(evidence.instance_id),
        type_id=evidence.type_id,
        name=evidence.name or evidence.type_id,
        description=evidence.description,
        tier=evidence.tier,
        tier_label=tier_info["label"],
        status=evidence.status,
        status_label=status_info["label"],
        verification_status=evidence.verification_status,
        source=evidence.source,
        source_scene_id=evidence.source_scene_id,
        source_slot_id=evidence.source_slot_id,
        source_stage_id=evidence.source_stage_id,
        created_at=evidence.created_at.isoformat(),
        expires_at=expires_at.isoformat() if expires_at else None,
        is_expired=is_expired,
        time_until_expiry=time_until_expiry,
        can_submit=can_submit,
        can_verify=can_verify,
        can_trade=can_trade
    )


# =============================================================================
# API Endpoints
# =============================================================================
@router.get("/me/evidence", response_model=EvidenceListResponse)
async def get_my_evidence(
    status: Optional[str] = Query(default=None, description="筛选状态: ACTIVE/SUBMITTED/EXPIRED"),
    tier: Optional[str] = Query(default=None, description="筛选等级: A/B/C/D"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取我的证物列表（证物柜）
    """
    query = db.query(EvidenceInstanceDB).filter(
        EvidenceInstanceDB.owner_id == auth.user_id
    )
    
    if status:
        query = query.filter(EvidenceInstanceDB.status == status)
    if tier:
        query = query.filter(EvidenceInstanceDB.tier == tier)
    
    # 统计
    total_count = query.count()
    active_count = db.query(EvidenceInstanceDB).filter(
        EvidenceInstanceDB.owner_id == auth.user_id,
        EvidenceInstanceDB.status == "ACTIVE"
    ).count()
    submitted_count = db.query(EvidenceInstanceDB).filter(
        EvidenceInstanceDB.owner_id == auth.user_id,
        EvidenceInstanceDB.status == "SUBMITTED"
    ).count()
    expired_count = db.query(EvidenceInstanceDB).filter(
        EvidenceInstanceDB.owner_id == auth.user_id,
        EvidenceInstanceDB.status == "EXPIRED"
    ).count()
    
    # 分页查询
    evidence_list = query.order_by(EvidenceInstanceDB.created_at.desc()).offset(offset).limit(limit).all()
    
    return EvidenceListResponse(
        user_id=auth.user_id,
        total_count=total_count,
        active_count=active_count,
        submitted_count=submitted_count,
        expired_count=expired_count,
        evidence=[evidence_to_response(e) for e in evidence_list]
    )


@router.get("/evidence/{instance_id}", response_model=EvidenceDetailResponse)
async def get_evidence_detail(
    instance_id: str = Path(..., description="证物实例ID"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取证物详情
    """
    try:
        evidence_uuid = uuid.UUID(instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid instance_id format")
    
    evidence = db.query(EvidenceInstanceDB).filter(
        EvidenceInstanceDB.instance_id == evidence_uuid
    ).first()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # 检查权限（只能查看自己的证物，或已验证的公开证物）
    if evidence.owner_id != auth.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this evidence")
    
    tier_info = TIER_INFO.get(evidence.tier, {"label": evidence.tier, "description": ""})
    status_info = STATUS_INFO.get(evidence.status, {"label": evidence.status})
    source_info = SOURCE_INFO.get(evidence.source, {"label": evidence.source})
    verification_info = VERIFICATION_INFO.get(evidence.verification_status, {"label": evidence.verification_status})
    
    return EvidenceDetailResponse(
        instance_id=str(evidence.instance_id),
        type_id=evidence.type_id,
        name=evidence.name or evidence.type_id,
        description=evidence.description,
        tier=evidence.tier,
        tier_label=tier_info["label"],
        tier_description=tier_info.get("description", ""),
        status=evidence.status,
        status_label=status_info["label"],
        verification_status=evidence.verification_status,
        verification_label=verification_info["label"],
        source=evidence.source,
        source_label=source_info["label"],
        source_scene_id=evidence.source_scene_id,
        source_slot_id=evidence.source_slot_id,
        source_stage_id=evidence.source_stage_id,
        source_timestamp=evidence.created_at.isoformat(),
        created_at=evidence.created_at.isoformat(),
        expires_at=evidence.expires_at.isoformat() if evidence.expires_at else None,
        verified_at=evidence.verified_at.isoformat() if evidence.verified_at else None,
        submission_history=[],  # 可扩展
        content_preview=None,
        metadata=evidence.metadata_json or {}
    )


@router.post("/evidence/{instance_id}/verify", response_model=VerifyEvidenceResponse)
async def verify_evidence(
    instance_id: str = Path(..., description="证物实例ID"),
    request: VerifyEvidenceRequest = Body(...),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    验证证物 - 确认证物真伪
    
    验证方式:
    - standard: 消耗Ticket，等待一段时间
    - location: 前往特定地点验证
    - expert: 专家验证（高成本）
    """
    try:
        evidence_uuid = uuid.UUID(instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid instance_id format")
    
    evidence = db.query(EvidenceInstanceDB).filter(
        EvidenceInstanceDB.instance_id == evidence_uuid,
        EvidenceInstanceDB.owner_id == auth.user_id
    ).first()
    
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found or not owned by you")
    
    if evidence.verification_status != "UNVERIFIED":
        raise HTTPException(status_code=400, detail=f"Evidence already {evidence.verification_status}")
    
    if evidence.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Evidence is not active")
    
    # 计算验证成本
    cost_map = {"standard": 10, "location": 0, "expert": 50}
    cost = cost_map.get(request.method, 10)
    
    # TODO: 扣除Ticket
    
    # 执行验证（P0简化：直接返回结果）
    import random
    is_genuine = not evidence.is_forged
    
    if is_genuine:
        evidence.verification_status = "VERIFIED"
        verification_result = "证物验证为真品"
    else:
        evidence.verification_status = "FORGED"
        verification_result = "警告：此证物为伪造品"
    
    evidence.verified_at = datetime.now(timezone.utc)
    db.commit()
    
    return VerifyEvidenceResponse(
        success=True,
        instance_id=str(evidence.instance_id),
        new_verification_status=evidence.verification_status,
        verification_result=verification_result,
        cost_paid=cost,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.post("/evidence/grant")
async def grant_evidence(
    request: GrantEvidenceRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """
    发放证物（内部API）
    
    由场景播放、门奖励等系统调用
    """
    # 计算过期时间
    expires_at = None
    if request.expires_in_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=request.expires_in_hours)
    
    evidence = EvidenceInstanceDB(
        type_id=request.type_id,
        tier=request.tier,
        owner_id=request.user_id,
        theatre_id=uuid.UUID(request.theatre_id),
        source=request.source,
        source_scene_id=request.source_scene_id,
        source_slot_id=request.source_slot_id,
        source_stage_id=request.source_stage_id,
        name=request.name or request.type_id,
        description=request.description,
        expires_at=expires_at,
        status="ACTIVE",
        verification_status="UNVERIFIED"
    )
    
    db.add(evidence)
    db.commit()
    
    return {
        "success": True,
        "instance_id": str(evidence.instance_id),
        "type_id": evidence.type_id,
        "tier": evidence.tier,
        "owner_id": evidence.owner_id,
        "expires_at": expires_at.isoformat() if expires_at else None
    }


@router.get("/me/evidence/summary")
async def get_evidence_summary(
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取证物摘要统计
    """
    # 按等级统计
    tier_counts = {}
    for tier in ["A", "B", "C", "D"]:
        count = db.query(EvidenceInstanceDB).filter(
            EvidenceInstanceDB.owner_id == auth.user_id,
            EvidenceInstanceDB.tier == tier,
            EvidenceInstanceDB.status == "ACTIVE"
        ).count()
        tier_counts[tier] = count
    
    # 按状态统计
    status_counts = {}
    for status in ["ACTIVE", "SUBMITTED", "EXPIRED", "CONSUMED"]:
        count = db.query(EvidenceInstanceDB).filter(
            EvidenceInstanceDB.owner_id == auth.user_id,
            EvidenceInstanceDB.status == status
        ).count()
        status_counts[status] = count
    
    # 即将过期的证物
    now = datetime.now(timezone.utc)
    expiring_soon = db.query(EvidenceInstanceDB).filter(
        EvidenceInstanceDB.owner_id == auth.user_id,
        EvidenceInstanceDB.status == "ACTIVE",
        EvidenceInstanceDB.expires_at != None,
        EvidenceInstanceDB.expires_at < now + timedelta(hours=6)
    ).count()
    
    return {
        "user_id": auth.user_id,
        "tier_counts": tier_counts,
        "status_counts": status_counts,
        "total_active": status_counts.get("ACTIVE", 0),
        "expiring_soon": expiring_soon,
        "tier_labels": {k: v["label"] for k, v in TIER_INFO.items()}
    }
