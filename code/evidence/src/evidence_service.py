"""
TheatreOS Evidence System
证物系统 - 管理证物实例的生命周期，从生成、归属到过期

证物等级 (Tier):
- A: 硬证物（关键门前置），稀缺，通常来自 RingB/A 或高风险场
- B: 可信线索，用于读底概率与验证传闻
- C: 噪声线索，可误读，推动讨论与交易
- D: 碎片与环境，用于氛围与考古，不强推结算

核心功能:
- 证物实例化（从场景产出）
- 证物归属管理
- 证物验证
- 证物交易
- 证物过期处理
- 证物提交到门
"""
import logging
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from decimal import Decimal

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class EvidenceTier(str, Enum):
    A = "A"  # 硬证物，关键门前置，稀缺
    B = "B"  # 可信线索，用于读底概率
    C = "C"  # 噪声线索，可误读
    D = "D"  # 碎片与环境，氛围用


class EvidenceStatus(str, Enum):
    ACTIVE = "ACTIVE"           # 活跃可用
    SUBMITTED = "SUBMITTED"     # 已提交到门
    EXPIRED = "EXPIRED"         # 已过期
    CONSUMED = "CONSUMED"       # 已消耗（验证等）
    TRADED = "TRADED"           # 已交易（历史状态）
    FORGED = "FORGED"           # 伪造品


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"   # 未验证
    VERIFIED = "VERIFIED"       # 已验证为真
    FORGED = "FORGED"           # 已验证为伪造
    PENDING = "PENDING"         # 验证中


class EvidenceSource(str, Enum):
    SCENE = "SCENE"             # 场景产出
    TRADE = "TRADE"             # 交易获得
    GATE_REWARD = "GATE_REWARD" # 门奖励
    CREW_SHARE = "CREW_SHARE"   # 剧团共享
    SYSTEM = "SYSTEM"           # 系统发放


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class EvidenceType:
    """证物类型定义（由Theme Pack定义）"""
    type_id: str
    name: str
    description: str
    category: str  # 类别：document, object, signal, testimony
    verification_cost: int = 10  # 验证成本（Ticket）
    forgery_risk: float = 0.1  # 伪造风险
    base_value: int = 100  # 基础价值
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvidenceInstance:
    """证物实例"""
    instance_id: str
    type_id: str
    tier: EvidenceTier
    owner_id: str
    theatre_id: str
    
    # 来源信息
    source: EvidenceSource
    source_scene_id: Optional[str] = None
    source_slot_id: Optional[str] = None
    source_stage_id: Optional[str] = None
    
    # 状态
    status: EvidenceStatus = EvidenceStatus.ACTIVE
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    
    # 时间
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    
    # 元数据
    content_hash: Optional[str] = None  # 内容哈希，用于防伪
    metadata: Dict = field(default_factory=dict)
    
    # 伪造相关
    is_forged: bool = False
    forged_by: Optional[str] = None
    forgery_detected_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "instance_id": self.instance_id,
            "type_id": self.type_id,
            "tier": self.tier.value,
            "owner_id": self.owner_id,
            "theatre_id": self.theatre_id,
            "source": self.source.value,
            "source_scene_id": self.source_scene_id,
            "source_slot_id": self.source_slot_id,
            "source_stage_id": self.source_stage_id,
            "status": self.status.value,
            "verification_status": self.verification_status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "is_forged": self.is_forged
        }
    
    def is_valid(self) -> bool:
        """检查证物是否有效"""
        if self.status != EvidenceStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class EvidenceSubmission:
    """证物提交记录"""
    submission_id: str
    evidence_instance_id: str
    user_id: str
    gate_instance_id: str
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    effect_applied: bool = False
    effect_description: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "submission_id": self.submission_id,
            "evidence_instance_id": self.evidence_instance_id,
            "user_id": self.user_id,
            "gate_instance_id": self.gate_instance_id,
            "submitted_at": self.submitted_at.isoformat(),
            "effect_applied": self.effect_applied,
            "effect_description": self.effect_description
        }


@dataclass
class TradeOffer:
    """交易报价"""
    offer_id: str
    seller_id: str
    evidence_instance_id: str
    asking_price: Decimal
    currency: str = "SHARD"
    status: str = "OPEN"  # OPEN, ACCEPTED, CANCELLED, EXPIRED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    buyer_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "offer_id": self.offer_id,
            "seller_id": self.seller_id,
            "evidence_instance_id": self.evidence_instance_id,
            "asking_price": float(self.asking_price),
            "currency": self.currency,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "buyer_id": self.buyer_id,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class VerificationResult:
    """验证结果"""
    success: bool
    is_authentic: bool
    confidence: float
    cost_paid: int
    message: str
    detected_forgery: bool = False
    forgery_source: Optional[str] = None


# =============================================================================
# Evidence Type Registry
# =============================================================================
class EvidenceTypeRegistry:
    """证物类型注册表"""
    
    def __init__(self):
        self._types: Dict[str, EvidenceType] = {}
        self._load_default_types()
    
    def _load_default_types(self):
        """加载默认证物类型"""
        default_types = [
            EvidenceType(
                type_id="ev_signal",
                name="异常信号",
                description="监控系统捕捉到的异常信号片段",
                category="signal",
                verification_cost=5,
                forgery_risk=0.15,
                base_value=80
            ),
            EvidenceType(
                type_id="ev_document",
                name="文档碎片",
                description="残缺的文档或记录",
                category="document",
                verification_cost=10,
                forgery_risk=0.2,
                base_value=120
            ),
            EvidenceType(
                type_id="ev_testimony",
                name="目击证词",
                description="目击者的陈述记录",
                category="testimony",
                verification_cost=15,
                forgery_risk=0.3,
                base_value=150
            ),
            EvidenceType(
                type_id="ev_object",
                name="物证",
                description="与事件相关的实物证据",
                category="object",
                verification_cost=20,
                forgery_risk=0.1,
                base_value=200
            ),
            EvidenceType(
                type_id="ev_trace",
                name="痕迹样本",
                description="现场采集的痕迹样本",
                category="signal",
                verification_cost=8,
                forgery_risk=0.12,
                base_value=90
            ),
            EvidenceType(
                type_id="ev_communication",
                name="通讯记录",
                description="截获的通讯内容",
                category="document",
                verification_cost=12,
                forgery_risk=0.25,
                base_value=130
            )
        ]
        
        for ev_type in default_types:
            self._types[ev_type.type_id] = ev_type
    
    def get_type(self, type_id: str) -> Optional[EvidenceType]:
        return self._types.get(type_id)
    
    def register_type(self, ev_type: EvidenceType):
        self._types[ev_type.type_id] = ev_type
    
    def list_types(self) -> List[EvidenceType]:
        return list(self._types.values())


# =============================================================================
# Evidence Service
# =============================================================================
class EvidenceService:
    """证物系统服务"""
    
    # 不同等级证物的过期时间（小时）
    TIER_EXPIRY_HOURS = {
        EvidenceTier.A: 168,  # 7天
        EvidenceTier.B: 72,   # 3天
        EvidenceTier.C: 24,   # 1天
        EvidenceTier.D: 12    # 12小时
    }
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.type_registry = EvidenceTypeRegistry()
        
        # 内存存储（实际应使用数据库）
        self._instances: Dict[str, EvidenceInstance] = {}
        self._submissions: Dict[str, EvidenceSubmission] = {}
        self._trade_offers: Dict[str, TradeOffer] = {}
        self._user_inventory: Dict[str, List[str]] = {}  # user_id -> [instance_ids]
    
    # =========================================================================
    # 证物创建
    # =========================================================================
    def create_evidence(
        self,
        type_id: str,
        tier: str,
        owner_id: str,
        theatre_id: str,
        source: str = "SCENE",
        source_scene_id: Optional[str] = None,
        source_slot_id: Optional[str] = None,
        source_stage_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> EvidenceInstance:
        """
        创建证物实例
        
        Args:
            type_id: 证物类型ID
            tier: 证物等级 (A/B/C/D)
            owner_id: 所有者用户ID
            theatre_id: 剧场ID
            source: 来源类型
            source_scene_id: 来源场景ID
            source_slot_id: 来源时段ID
            source_stage_id: 来源舞台ID
            metadata: 额外元数据
        
        Returns:
            创建的证物实例
        """
        # 验证证物类型
        ev_type = self.type_registry.get_type(type_id)
        if not ev_type:
            raise ValueError(f"Unknown evidence type: {type_id}")
        
        # 计算过期时间
        tier_enum = EvidenceTier(tier)
        expiry_hours = self.TIER_EXPIRY_HOURS.get(tier_enum, 24)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        
        # 生成内容哈希（用于防伪）
        content_hash = self._generate_content_hash(
            type_id, tier, source_scene_id, source_slot_id
        )
        
        instance = EvidenceInstance(
            instance_id=str(uuid.uuid4()),
            type_id=type_id,
            tier=tier_enum,
            owner_id=owner_id,
            theatre_id=theatre_id,
            source=EvidenceSource(source),
            source_scene_id=source_scene_id,
            source_slot_id=source_slot_id,
            source_stage_id=source_stage_id,
            expires_at=expires_at,
            content_hash=content_hash,
            metadata=metadata or {}
        )
        
        # 存储
        self._instances[instance.instance_id] = instance
        
        # 更新用户库存
        if owner_id not in self._user_inventory:
            self._user_inventory[owner_id] = []
        self._user_inventory[owner_id].append(instance.instance_id)
        
        logger.info(f"Created evidence {instance.instance_id} (Tier {tier}) for user {owner_id}")
        
        return instance
    
    def _generate_content_hash(
        self,
        type_id: str,
        tier: str,
        scene_id: Optional[str],
        slot_id: Optional[str]
    ) -> str:
        """生成内容哈希"""
        content = f"{type_id}:{tier}:{scene_id}:{slot_id}:{uuid.uuid4()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # =========================================================================
    # 证物查询
    # =========================================================================
    def get_evidence(self, instance_id: str) -> Optional[EvidenceInstance]:
        """获取证物实例"""
        return self._instances.get(instance_id)
    
    def get_user_evidence(
        self,
        user_id: str,
        include_expired: bool = False,
        tier_filter: Optional[str] = None
    ) -> List[EvidenceInstance]:
        """获取用户的证物列表"""
        instance_ids = self._user_inventory.get(user_id, [])
        instances = []
        
        for instance_id in instance_ids:
            instance = self._instances.get(instance_id)
            if not instance:
                continue
            
            # 过滤过期
            if not include_expired and not instance.is_valid():
                continue
            
            # 过滤等级
            if tier_filter and instance.tier.value != tier_filter:
                continue
            
            instances.append(instance)
        
        return instances
    
    def get_evidence_by_scene(
        self,
        scene_id: str,
        theatre_id: str
    ) -> List[EvidenceInstance]:
        """获取场景产出的证物"""
        return [
            inst for inst in self._instances.values()
            if inst.source_scene_id == scene_id and inst.theatre_id == theatre_id
        ]
    
    # =========================================================================
    # 证物验证
    # =========================================================================
    def verify_evidence(
        self,
        instance_id: str,
        user_id: str,
        pay_cost: bool = True
    ) -> VerificationResult:
        """
        验证证物真伪
        
        Args:
            instance_id: 证物实例ID
            user_id: 验证者用户ID
            pay_cost: 是否支付验证成本
        
        Returns:
            验证结果
        """
        instance = self._instances.get(instance_id)
        if not instance:
            return VerificationResult(
                success=False,
                is_authentic=False,
                confidence=0,
                cost_paid=0,
                message="Evidence not found"
            )
        
        # 获取证物类型
        ev_type = self.type_registry.get_type(instance.type_id)
        if not ev_type:
            return VerificationResult(
                success=False,
                is_authentic=False,
                confidence=0,
                cost_paid=0,
                message="Unknown evidence type"
            )
        
        # 计算验证成本
        cost = ev_type.verification_cost if pay_cost else 0
        
        # 执行验证
        if instance.is_forged:
            # 伪造品被发现
            instance.verification_status = VerificationStatus.FORGED
            instance.forgery_detected_at = datetime.now(timezone.utc)
            
            return VerificationResult(
                success=True,
                is_authentic=False,
                confidence=0.95,
                cost_paid=cost,
                message="Forgery detected!",
                detected_forgery=True,
                forgery_source=instance.forged_by
            )
        else:
            # 真品
            instance.verification_status = VerificationStatus.VERIFIED
            instance.verified_at = datetime.now(timezone.utc)
            
            return VerificationResult(
                success=True,
                is_authentic=True,
                confidence=0.98,
                cost_paid=cost,
                message="Evidence verified as authentic"
            )
    
    # =========================================================================
    # 证物提交（到门）
    # =========================================================================
    def submit_to_gate(
        self,
        instance_id: str,
        user_id: str,
        gate_instance_id: str
    ) -> EvidenceSubmission:
        """
        提交证物到门
        
        Args:
            instance_id: 证物实例ID
            user_id: 用户ID
            gate_instance_id: 门实例ID
        
        Returns:
            提交记录
        """
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Evidence not found: {instance_id}")
        
        if instance.owner_id != user_id:
            raise ValueError("You don't own this evidence")
        
        if not instance.is_valid():
            raise ValueError("Evidence is not valid (expired or already used)")
        
        # 创建提交记录
        submission = EvidenceSubmission(
            submission_id=str(uuid.uuid4()),
            evidence_instance_id=instance_id,
            user_id=user_id,
            gate_instance_id=gate_instance_id
        )
        
        # 更新证物状态
        instance.status = EvidenceStatus.SUBMITTED
        
        # 存储
        self._submissions[submission.submission_id] = submission
        
        logger.info(f"Evidence {instance_id} submitted to gate {gate_instance_id}")
        
        return submission
    
    def get_gate_submissions(self, gate_instance_id: str) -> List[EvidenceSubmission]:
        """获取门的所有证物提交"""
        return [
            sub for sub in self._submissions.values()
            if sub.gate_instance_id == gate_instance_id
        ]
    
    # =========================================================================
    # 证物交易
    # =========================================================================
    def create_trade_offer(
        self,
        seller_id: str,
        instance_id: str,
        asking_price: float,
        currency: str = "SHARD",
        duration_hours: int = 24
    ) -> TradeOffer:
        """
        创建交易报价
        
        Args:
            seller_id: 卖家ID
            instance_id: 证物实例ID
            asking_price: 要价
            currency: 货币类型
            duration_hours: 报价有效期（小时）
        
        Returns:
            交易报价
        """
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Evidence not found: {instance_id}")
        
        if instance.owner_id != seller_id:
            raise ValueError("You don't own this evidence")
        
        if not instance.is_valid():
            raise ValueError("Evidence is not valid for trading")
        
        offer = TradeOffer(
            offer_id=str(uuid.uuid4()),
            seller_id=seller_id,
            evidence_instance_id=instance_id,
            asking_price=Decimal(str(asking_price)),
            currency=currency,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        )
        
        self._trade_offers[offer.offer_id] = offer
        
        logger.info(f"Trade offer created: {offer.offer_id} for evidence {instance_id}")
        
        return offer
    
    def accept_trade_offer(
        self,
        offer_id: str,
        buyer_id: str
    ) -> Tuple[bool, str]:
        """
        接受交易报价
        
        Args:
            offer_id: 报价ID
            buyer_id: 买家ID
        
        Returns:
            (成功与否, 消息)
        """
        offer = self._trade_offers.get(offer_id)
        if not offer:
            return False, "Offer not found"
        
        if offer.status != "OPEN":
            return False, f"Offer is not open (status: {offer.status})"
        
        if offer.expires_at and datetime.now(timezone.utc) > offer.expires_at:
            offer.status = "EXPIRED"
            return False, "Offer has expired"
        
        if offer.seller_id == buyer_id:
            return False, "Cannot buy your own evidence"
        
        # 获取证物
        instance = self._instances.get(offer.evidence_instance_id)
        if not instance or not instance.is_valid():
            offer.status = "CANCELLED"
            return False, "Evidence is no longer valid"
        
        # 执行交易
        # 1. 从卖家库存移除
        if offer.seller_id in self._user_inventory:
            self._user_inventory[offer.seller_id].remove(offer.evidence_instance_id)
        
        # 2. 添加到买家库存
        if buyer_id not in self._user_inventory:
            self._user_inventory[buyer_id] = []
        self._user_inventory[buyer_id].append(offer.evidence_instance_id)
        
        # 3. 更新证物所有者
        instance.owner_id = buyer_id
        
        # 4. 更新报价状态
        offer.status = "ACCEPTED"
        offer.buyer_id = buyer_id
        offer.completed_at = datetime.now(timezone.utc)
        
        logger.info(f"Trade completed: {offer_id}, evidence {instance.instance_id} transferred to {buyer_id}")
        
        return True, f"Trade completed. Evidence transferred to {buyer_id}"
    
    def get_open_offers(
        self,
        theatre_id: Optional[str] = None,
        tier_filter: Optional[str] = None
    ) -> List[TradeOffer]:
        """获取公开的交易报价"""
        offers = []
        
        for offer in self._trade_offers.values():
            if offer.status != "OPEN":
                continue
            
            if offer.expires_at and datetime.now(timezone.utc) > offer.expires_at:
                offer.status = "EXPIRED"
                continue
            
            instance = self._instances.get(offer.evidence_instance_id)
            if not instance:
                continue
            
            if theatre_id and instance.theatre_id != theatre_id:
                continue
            
            if tier_filter and instance.tier.value != tier_filter:
                continue
            
            offers.append(offer)
        
        return offers
    
    # =========================================================================
    # 证物转移（剧团共享等）
    # =========================================================================
    def transfer_evidence(
        self,
        instance_id: str,
        from_user_id: str,
        to_user_id: str,
        reason: str = "transfer"
    ) -> bool:
        """
        转移证物所有权
        
        Args:
            instance_id: 证物实例ID
            from_user_id: 原所有者
            to_user_id: 新所有者
            reason: 转移原因
        
        Returns:
            是否成功
        """
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        
        if instance.owner_id != from_user_id:
            return False
        
        # 更新库存
        if from_user_id in self._user_inventory:
            self._user_inventory[from_user_id].remove(instance_id)
        
        if to_user_id not in self._user_inventory:
            self._user_inventory[to_user_id] = []
        self._user_inventory[to_user_id].append(instance_id)
        
        # 更新所有者
        instance.owner_id = to_user_id
        
        logger.info(f"Evidence {instance_id} transferred from {from_user_id} to {to_user_id} ({reason})")
        
        return True
    
    # =========================================================================
    # 证物过期处理
    # =========================================================================
    def process_expirations(self, theatre_id: str) -> int:
        """
        处理过期证物
        
        Args:
            theatre_id: 剧场ID
        
        Returns:
            处理的过期证物数量
        """
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for instance in self._instances.values():
            if instance.theatre_id != theatre_id:
                continue
            
            if instance.status != EvidenceStatus.ACTIVE:
                continue
            
            if instance.expires_at and now > instance.expires_at:
                instance.status = EvidenceStatus.EXPIRED
                expired_count += 1
                logger.info(f"Evidence {instance.instance_id} expired")
        
        return expired_count
    
    # =========================================================================
    # 伪造证物（高级功能）
    # =========================================================================
    def create_forged_evidence(
        self,
        type_id: str,
        tier: str,
        forger_id: str,
        theatre_id: str,
        original_instance_id: Optional[str] = None
    ) -> EvidenceInstance:
        """
        创建伪造证物（需要特殊权限和成本）
        
        Args:
            type_id: 证物类型ID
            tier: 证物等级
            forger_id: 伪造者ID
            theatre_id: 剧场ID
            original_instance_id: 原始证物ID（如果是复制伪造）
        
        Returns:
            伪造的证物实例
        """
        instance = self.create_evidence(
            type_id=type_id,
            tier=tier,
            owner_id=forger_id,
            theatre_id=theatre_id,
            source="SYSTEM",
            metadata={"forged": True, "original_id": original_instance_id}
        )
        
        # 标记为伪造
        instance.is_forged = True
        instance.forged_by = forger_id
        
        logger.warning(f"Forged evidence created: {instance.instance_id} by {forger_id}")
        
        return instance
    
    # =========================================================================
    # 统计
    # =========================================================================
    def get_statistics(self, theatre_id: str) -> Dict:
        """获取证物系统统计"""
        instances = [i for i in self._instances.values() if i.theatre_id == theatre_id]
        
        tier_counts = {tier.value: 0 for tier in EvidenceTier}
        status_counts = {status.value: 0 for status in EvidenceStatus}
        
        for inst in instances:
            tier_counts[inst.tier.value] += 1
            status_counts[inst.status.value] += 1
        
        return {
            "total_instances": len(instances),
            "by_tier": tier_counts,
            "by_status": status_counts,
            "active_offers": len([o for o in self._trade_offers.values() if o.status == "OPEN"]),
            "total_submissions": len(self._submissions)
        }
