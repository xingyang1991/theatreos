"""
TheatreOS Gate System API Routes
门投票结算系统的完整API端点

核心功能:
- 门实例查询
- 投票/下注提交
- 证物提交
- 结算与Explain Card
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import get_db_session, Theatre, HourPlan
from gate.src.gate_service import (
    GateService, GateInstance, GateVote, GateStake, 
    GateEvidenceSubmission, GateSettlement, WalletBalance,
    VoteRequest, StakeRequest
)
from auth.src.middleware import get_current_user, require_auth, AuthContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Gate System"])


# =============================================================================
# Request/Response Models
# =============================================================================
class VoteRequestModel(BaseModel):
    """投票请求"""
    option_id: str = Field(..., description="选项ID")
    ring_level: str = Field(default="C", description="Ring等级")
    idempotency_key: Optional[str] = Field(default=None, description="幂等键")


class StakeRequestModel(BaseModel):
    """下注请求"""
    option_id: str = Field(..., description="选项ID")
    currency: str = Field(default="ticket", description="货币类型")
    amount: float = Field(..., gt=0, description="下注金额")
    ring_level: str = Field(default="C", description="Ring等级")
    idempotency_key: Optional[str] = Field(default=None, description="幂等键")


class EvidenceSubmitRequestModel(BaseModel):
    """证物提交请求"""
    evidence_instance_id: str = Field(..., description="证物实例ID")
    idempotency_key: Optional[str] = Field(default=None, description="幂等键")


class GateOptionResponse(BaseModel):
    """门选项响应"""
    option_id: str
    label: str
    description: Optional[str] = None
    vote_count: int = 0
    stake_total: float = 0.0
    probability: Optional[float] = None


class GateLobbyResponse(BaseModel):
    """门厅响应"""
    gate_instance_id: str
    slot_id: str
    theatre_id: str
    type: str
    title: str
    status: str
    open_at: str
    close_at: str
    resolve_at: str
    options: List[GateOptionResponse]
    evidence_slots: int
    stake_allowed: bool
    risk_hint: Optional[str] = None
    user_participation: Optional[Dict[str, Any]] = None
    countdown_to_close: int
    is_open: bool


class VoteResultResponse(BaseModel):
    """投票结果响应"""
    success: bool
    message: str
    vote_id: Optional[str] = None
    option_id: str
    timestamp: str


class StakeResultResponse(BaseModel):
    """下注结果响应"""
    success: bool
    message: str
    amount_locked: float
    new_balance: float
    timestamp: str


class EvidenceSubmitResultResponse(BaseModel):
    """证物提交结果响应"""
    success: bool
    message: str
    submission_id: Optional[str] = None
    evidence_instance_id: str
    advantage_granted: Optional[str] = None


class ExplainCardResponse(BaseModel):
    """Explain Card响应"""
    gate_instance_id: str
    slot_id: str
    resolved_at: str
    winner_option_id: str
    winner_label: str
    
    # 结果解释
    result_summary: str
    why_explanation: str
    consequence: str
    
    # 统计数据
    total_votes: int
    total_stake: float
    vote_distribution: Dict[str, int]
    stake_distribution: Dict[str, float]
    
    # 证物影响
    evidence_impact: List[Dict[str, Any]]
    
    # 世界状态变化
    world_state_delta: Dict[str, Any]
    
    # 回声线索
    echo_hints: List[Dict[str, Any]]
    
    # 用户个人结算
    user_settlement: Optional[Dict[str, Any]] = None


class UserParticipationResponse(BaseModel):
    """用户参与情况响应"""
    gate_instance_id: str
    user_id: str
    has_voted: bool
    vote_option_id: Optional[str] = None
    has_staked: bool
    stake_amount: float = 0.0
    stake_option_id: Optional[str] = None
    evidence_submitted: List[str] = []
    can_participate: bool
    reason: Optional[str] = None


# =============================================================================
# API Endpoints
# =============================================================================
@router.get("/gates/{gate_instance_id}/lobby", response_model=GateLobbyResponse)
async def get_gate_lobby(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    auth: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    获取门厅信息 - 展示门的选项、状态和用户参与情况
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate = db.query(GateInstance).filter(GateInstance.gate_instance_id == gate_uuid).first()
    
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    now = datetime.now(timezone.utc)
    close_at = gate.close_at
    if close_at.tzinfo is None:
        close_at = close_at.replace(tzinfo=timezone.utc)
    
    countdown_to_close = max(0, int((close_at - now).total_seconds()))
    is_open = gate.status == "OPEN" and now < close_at
    
    # 获取选项统计
    options_data = gate.options_jsonb or []
    options = []
    
    for opt in options_data:
        option_id = opt.get("option_id")
        
        # 统计投票数
        vote_count = db.query(GateVote).filter(
            GateVote.gate_instance_id == gate_uuid,
            GateVote.option_id == option_id
        ).count()
        
        # 统计下注总额
        stake_total = db.query(GateStake).filter(
            GateStake.gate_instance_id == gate_uuid,
            GateStake.option_id == option_id
        ).with_entities(func.sum(GateStake.amount_locked)).scalar() or 0
        
        options.append(GateOptionResponse(
            option_id=option_id,
            label=opt.get("label", option_id),
            description=opt.get("description"),
            vote_count=vote_count,
            stake_total=float(stake_total),
            probability=opt.get("base_prob")
        ))
    
    # 获取用户参与情况
    user_participation = None
    if auth and auth.user_id:
        user_vote = db.query(GateVote).filter(
            GateVote.gate_instance_id == gate_uuid,
            GateVote.user_id == auth.user_id
        ).first()
        
        user_stake = db.query(GateStake).filter(
            GateStake.gate_instance_id == gate_uuid,
            GateStake.user_id == auth.user_id
        ).first()
        
        user_evidence = db.query(GateEvidenceSubmission).filter(
            GateEvidenceSubmission.gate_instance_id == gate_uuid,
            GateEvidenceSubmission.user_id == auth.user_id
        ).all()
        
        user_participation = {
            "has_voted": user_vote is not None,
            "vote_option_id": user_vote.option_id if user_vote else None,
            "has_staked": user_stake is not None,
            "stake_amount": float(user_stake.amount_locked) if user_stake else 0,
            "stake_option_id": user_stake.option_id if user_stake else None,
            "evidence_submitted": [e.evidence_instance_id for e in user_evidence]
        }
    
    return GateLobbyResponse(
        gate_instance_id=str(gate.gate_instance_id),
        slot_id=gate.slot_id,
        theatre_id=str(gate.theatre_id),
        type=gate.type,
        title=gate.title,
        status=gate.status,
        open_at=gate.open_at.isoformat(),
        close_at=gate.close_at.isoformat(),
        resolve_at=gate.resolve_at.isoformat(),
        options=options,
        evidence_slots=1,  # 可配置
        stake_allowed=gate.type in ["Fate", "FateMajor", "Council"],
        risk_hint="此门的结果将影响世界状态",
        user_participation=user_participation,
        countdown_to_close=countdown_to_close,
        is_open=is_open
    )


@router.post("/gates/{gate_instance_id}/vote", response_model=VoteResultResponse)
async def submit_vote(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    request: VoteRequestModel = Body(...),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    提交投票 - 每用户每门只能投一次票
    
    幂等性：相同的idempotency_key会返回相同的结果
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate_service = GateService(db)
    
    # 检查门是否存在且开放
    gate = db.query(GateInstance).filter(GateInstance.gate_instance_id == gate_uuid).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    now = datetime.now(timezone.utc)
    open_at = gate.open_at.replace(tzinfo=timezone.utc) if gate.open_at.tzinfo is None else gate.open_at
    close_at = gate.close_at.replace(tzinfo=timezone.utc) if gate.close_at.tzinfo is None else gate.close_at
    
    if now < open_at:
        raise HTTPException(status_code=400, detail="Gate not yet open")
    if now > close_at:
        raise HTTPException(status_code=400, detail="Gate already closed")
    
    # 验证选项
    valid_options = [opt.get("option_id") for opt in (gate.options_jsonb or [])]
    if request.option_id not in valid_options:
        raise HTTPException(status_code=400, detail=f"Invalid option_id. Valid options: {valid_options}")
    
    # 检查幂等性
    idempotency_key = request.idempotency_key or str(uuid.uuid4())
    existing_vote = db.query(GateVote).filter(
        GateVote.gate_instance_id == gate_uuid,
        GateVote.user_id == auth.user_id
    ).first()
    
    if existing_vote:
        if existing_vote.idempotency_key == idempotency_key:
            return VoteResultResponse(
                success=True,
                message="Vote already recorded (idempotent)",
                vote_id=f"{gate_instance_id}_{auth.user_id}",
                option_id=existing_vote.option_id,
                timestamp=existing_vote.created_at.isoformat()
            )
        else:
            raise HTTPException(status_code=400, detail="You have already voted on this gate")
    
    # 创建投票记录
    vote = GateVote(
        gate_instance_id=gate_uuid,
        user_id=auth.user_id,
        option_id=request.option_id,
        ring_level=request.ring_level,
        idempotency_key=idempotency_key
    )
    
    db.add(vote)
    db.commit()
    
    return VoteResultResponse(
        success=True,
        message="Vote recorded successfully",
        vote_id=f"{gate_instance_id}_{auth.user_id}",
        option_id=request.option_id,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.post("/gates/{gate_instance_id}/stake", response_model=StakeResultResponse)
async def submit_stake(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    request: StakeRequestModel = Body(...),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    提交下注 - 锁定代币并记录下注
    
    幂等性：相同的idempotency_key会返回相同的结果
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate = db.query(GateInstance).filter(GateInstance.gate_instance_id == gate_uuid).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    # 检查门类型是否允许下注
    if gate.type not in ["Fate", "FateMajor", "Council"]:
        raise HTTPException(status_code=400, detail="This gate type does not allow staking")
    
    now = datetime.now(timezone.utc)
    open_at = gate.open_at.replace(tzinfo=timezone.utc) if gate.open_at.tzinfo is None else gate.open_at
    close_at = gate.close_at.replace(tzinfo=timezone.utc) if gate.close_at.tzinfo is None else gate.close_at
    
    if now < open_at:
        raise HTTPException(status_code=400, detail="Gate not yet open")
    if now > close_at:
        raise HTTPException(status_code=400, detail="Gate already closed")
    
    # 验证选项
    valid_options = [opt.get("option_id") for opt in (gate.options_jsonb or [])]
    if request.option_id not in valid_options:
        raise HTTPException(status_code=400, detail=f"Invalid option_id")
    
    # 检查幂等性
    idempotency_key = request.idempotency_key or str(uuid.uuid4())
    existing_stake = db.query(GateStake).filter(
        GateStake.gate_instance_id == gate_uuid,
        GateStake.user_id == auth.user_id,
        GateStake.currency == request.currency
    ).first()
    
    if existing_stake:
        if existing_stake.idempotency_key == idempotency_key:
            return StakeResultResponse(
                success=True,
                message="Stake already recorded (idempotent)",
                amount_locked=float(existing_stake.amount_locked),
                new_balance=0,  # 需要查询钱包
                timestamp=existing_stake.created_at.isoformat()
            )
        else:
            raise HTTPException(status_code=400, detail="You have already staked on this gate")
    
    # 检查余额
    wallet = db.query(WalletBalance).filter(
        WalletBalance.user_id == auth.user_id,
        WalletBalance.currency == request.currency
    ).first()
    
    current_balance = float(wallet.balance) if wallet else 0
    
    if current_balance < request.amount:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Current: {current_balance}")
    
    # 扣除余额并锁定
    if wallet:
        wallet.balance = Decimal(str(current_balance - request.amount))
    else:
        # 创建钱包记录（余额不足的情况已经处理）
        pass
    
    # 创建下注记录
    stake = GateStake(
        gate_instance_id=gate_uuid,
        user_id=auth.user_id,
        currency=request.currency,
        option_id=request.option_id,
        amount_locked=Decimal(str(request.amount)),
        ring_level=request.ring_level,
        idempotency_key=idempotency_key
    )
    
    db.add(stake)
    db.commit()
    
    new_balance = float(wallet.balance) if wallet else 0
    
    return StakeResultResponse(
        success=True,
        message="Stake recorded successfully",
        amount_locked=request.amount,
        new_balance=new_balance,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.post("/gates/{gate_instance_id}/evidence", response_model=EvidenceSubmitResultResponse)
async def submit_evidence(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    request: EvidenceSubmitRequestModel = Body(...),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    提交证物 - 将证物提交到门以获得优势
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate = db.query(GateInstance).filter(GateInstance.gate_instance_id == gate_uuid).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    now = datetime.now(timezone.utc)
    close_at = gate.close_at.replace(tzinfo=timezone.utc) if gate.close_at.tzinfo is None else gate.close_at
    
    if now > close_at:
        raise HTTPException(status_code=400, detail="Gate already closed")
    
    # 检查幂等性
    idempotency_key = request.idempotency_key or str(uuid.uuid4())
    existing = db.query(GateEvidenceSubmission).filter(
        GateEvidenceSubmission.gate_instance_id == gate_uuid,
        GateEvidenceSubmission.user_id == auth.user_id,
        GateEvidenceSubmission.evidence_instance_id == request.evidence_instance_id
    ).first()
    
    if existing:
        return EvidenceSubmitResultResponse(
            success=True,
            message="Evidence already submitted (idempotent)",
            submission_id=str(existing.submission_id),
            evidence_instance_id=request.evidence_instance_id,
            advantage_granted="probability_boost"
        )
    
    # 创建提交记录
    submission = GateEvidenceSubmission(
        gate_instance_id=gate_uuid,
        user_id=auth.user_id,
        evidence_instance_id=request.evidence_instance_id,
        tier="B",  # 应该从证物实例获取
        idempotency_key=idempotency_key
    )
    
    db.add(submission)
    db.commit()
    
    return EvidenceSubmitResultResponse(
        success=True,
        message="Evidence submitted successfully",
        submission_id=str(submission.submission_id),
        evidence_instance_id=request.evidence_instance_id,
        advantage_granted="probability_boost"
    )


@router.get("/gates/{gate_instance_id}/explain", response_model=ExplainCardResponse)
async def get_explain_card(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    auth: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    获取Explain Card - 门结算后的结果解释
    
    包含:
    - 结果摘要
    - 原因分析
    - 世界状态变化
    - 回声线索
    - 用户个人结算
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate = db.query(GateInstance).filter(GateInstance.gate_instance_id == gate_uuid).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    if gate.status != "RESOLVED":
        raise HTTPException(status_code=400, detail="Gate not yet resolved")
    
    # 获取存储的Explain Card
    explain_card = gate.explain_card_jsonb or {}
    
    # 获取投票分布
    vote_distribution = {}
    stake_distribution = {}
    
    for opt in (gate.options_jsonb or []):
        option_id = opt.get("option_id")
        vote_count = db.query(GateVote).filter(
            GateVote.gate_instance_id == gate_uuid,
            GateVote.option_id == option_id
        ).count()
        vote_distribution[option_id] = vote_count
        
        stake_total = db.query(GateStake).filter(
            GateStake.gate_instance_id == gate_uuid,
            GateStake.option_id == option_id
        ).with_entities(func.sum(GateStake.amount_locked)).scalar() or 0
        stake_distribution[option_id] = float(stake_total)
    
    total_votes = sum(vote_distribution.values())
    total_stake = sum(stake_distribution.values())
    
    # 获取获胜选项标签
    winner_label = gate.winner_option_id
    for opt in (gate.options_jsonb or []):
        if opt.get("option_id") == gate.winner_option_id:
            winner_label = opt.get("label", gate.winner_option_id)
            break
    
    # 获取用户个人结算
    user_settlement = None
    if auth and auth.user_id:
        settlement = db.query(GateSettlement).filter(
            GateSettlement.gate_instance_id == gate_uuid,
            GateSettlement.user_id == auth.user_id
        ).first()
        
        if settlement:
            user_settlement = {
                "stake": float(settlement.stake),
                "payout": float(settlement.payout),
                "net_delta": float(settlement.net_delta),
                "currency": settlement.currency
            }
    
    return ExplainCardResponse(
        gate_instance_id=str(gate.gate_instance_id),
        slot_id=gate.slot_id,
        resolved_at=gate.resolve_at.isoformat(),
        winner_option_id=gate.winner_option_id or "unknown",
        winner_label=winner_label,
        result_summary=explain_card.get("result_summary", f"选项 {winner_label} 获胜"),
        why_explanation=explain_card.get("why_explanation", "根据投票和证物综合判定"),
        consequence=explain_card.get("consequence", "世界状态已更新"),
        total_votes=total_votes,
        total_stake=total_stake,
        vote_distribution=vote_distribution,
        stake_distribution=stake_distribution,
        evidence_impact=explain_card.get("evidence_impact", []),
        world_state_delta=explain_card.get("world_state_delta", {}),
        echo_hints=explain_card.get("echo_hints", [
            {
                "type": "next_slot",
                "message": "下一小时将揭示更多真相",
                "target_slot_id": None
            }
        ]),
        user_settlement=user_settlement
    )


@router.get("/gates/{gate_instance_id}/participation", response_model=UserParticipationResponse)
async def get_user_participation(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    获取用户在该门的参与情况
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate = db.query(GateInstance).filter(GateInstance.gate_instance_id == gate_uuid).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    # 查询用户投票
    user_vote = db.query(GateVote).filter(
        GateVote.gate_instance_id == gate_uuid,
        GateVote.user_id == auth.user_id
    ).first()
    
    # 查询用户下注
    user_stake = db.query(GateStake).filter(
        GateStake.gate_instance_id == gate_uuid,
        GateStake.user_id == auth.user_id
    ).first()
    
    # 查询用户提交的证物
    user_evidence = db.query(GateEvidenceSubmission).filter(
        GateEvidenceSubmission.gate_instance_id == gate_uuid,
        GateEvidenceSubmission.user_id == auth.user_id
    ).all()
    
    # 检查是否可以参与
    now = datetime.now(timezone.utc)
    close_at = gate.close_at.replace(tzinfo=timezone.utc) if gate.close_at.tzinfo is None else gate.close_at
    can_participate = now < close_at and gate.status == "OPEN"
    reason = None
    if not can_participate:
        if now >= close_at:
            reason = "门已关闭"
        elif gate.status != "OPEN":
            reason = f"门状态: {gate.status}"
    
    return UserParticipationResponse(
        gate_instance_id=str(gate.gate_instance_id),
        user_id=auth.user_id,
        has_voted=user_vote is not None,
        vote_option_id=user_vote.option_id if user_vote else None,
        has_staked=user_stake is not None,
        stake_amount=float(user_stake.amount_locked) if user_stake else 0,
        stake_option_id=user_stake.option_id if user_stake else None,
        evidence_submitted=[e.evidence_instance_id for e in user_evidence],
        can_participate=can_participate,
        reason=reason
    )


@router.post("/gates/{gate_instance_id}/resolve")
async def trigger_resolve(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    db: Session = Depends(get_db_session)
):
    """
    触发门结算 - 通常由调度器自动调用
    
    幂等性：多次调用返回相同结果
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate_service = GateService(db)
    result = gate_service.resolve_gate(str(gate_uuid))
    
    if result.success:
        return {
            "success": True,
            "winner_option_id": result.winner_option_id,
            "explain_card_available": result.explain_card is not None
        }
    else:
        raise HTTPException(status_code=400, detail=result.error or "Resolution failed")


@router.get("/slots/{slot_id}/gate")
async def get_slot_gate(
    slot_id: str = Path(..., description="Slot ID"),
    db: Session = Depends(get_db_session)
):
    """
    获取Slot对应的门实例
    """
    gate = db.query(GateInstance).filter(GateInstance.slot_id == slot_id).first()
    
    if not gate:
        raise HTTPException(status_code=404, detail="No gate found for this slot")
    
    return {
        "gate_instance_id": str(gate.gate_instance_id),
        "slot_id": gate.slot_id,
        "type": gate.type,
        "title": gate.title,
        "status": gate.status,
        "open_at": gate.open_at.isoformat(),
        "close_at": gate.close_at.isoformat()
    }


@router.post("/gates/{gate_instance_id}/claim-rewards")
async def claim_rewards(
    gate_instance_id: str = Path(..., description="Gate Instance ID"),
    auth: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db_session)
):
    """
    领取奖励 - 用户在门结算后领取赢得的奖励
    
    幂等性：多次调用返回相同结果
    """
    try:
        gate_uuid = uuid.UUID(gate_instance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid gate_instance_id format")
    
    gate = db.query(GateInstance).filter(GateInstance.gate_instance_id == gate_uuid).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    if gate.status != "RESOLVED":
        raise HTTPException(status_code=400, detail="Gate not yet resolved, cannot claim rewards")
    
    # 查询用户结算记录
    settlement = db.query(GateSettlement).filter(
        GateSettlement.gate_instance_id == gate_uuid,
        GateSettlement.user_id == auth.user_id
    ).first()
    
    if not settlement:
        # 用户没有参与这个门
        return {
            "success": False,
            "message": "No participation record found",
            "claimed": False,
            "amount": 0,
            "currency": "TICKET"
        }
    
    if settlement.claimed:
        # 已经领取过了（幂等）
        return {
            "success": True,
            "message": "Rewards already claimed",
            "claimed": True,
            "amount": float(settlement.payout),
            "currency": settlement.currency,
            "claimed_at": settlement.claimed_at.isoformat() if settlement.claimed_at else None
        }
    
    # 执行领取
    payout = float(settlement.payout)
    
    if payout > 0:
        # 增加用户钱包余额
        wallet = db.query(WalletBalance).filter(
            WalletBalance.user_id == auth.user_id,
            WalletBalance.currency == settlement.currency
        ).first()
        
        if wallet:
            wallet.balance = wallet.balance + Decimal(str(payout))
        else:
            wallet = WalletBalance(
                user_id=auth.user_id,
                currency=settlement.currency,
                balance=Decimal(str(payout))
            )
            db.add(wallet)
    
    # 标记已领取
    settlement.claimed = True
    settlement.claimed_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Rewards claimed successfully",
        "claimed": True,
        "amount": payout,
        "currency": settlement.currency,
        "claimed_at": settlement.claimed_at.isoformat()
    }
