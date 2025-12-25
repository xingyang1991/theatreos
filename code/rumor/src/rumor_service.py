"""
TheatreOS Rumor System
谣言系统 - 管理传闻卡的创建、流通、验证和世界影响

传闻卡 = 玩家对证物/场次的解释
- 可私藏/交换/公开广播
- 有标签：来源（目击/二手/推测）、语气（警告/引诱/求证）、有效区域、过期时间
- 能改变世界：影响玩家路线与NPC概率（通过'人群热度'输入排程器）
- 误读不是失败：误读会造成局部生态变化，成为可追溯回声

核心功能:
- 传闻创建（基于证物或场景观察）
- 传闻流通（私藏、交换、广播）
- 传闻验证（与事实对比）
- 传闻影响（影响热度和排程）
- 误读追踪（回声系统）
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
class RumorSource(str, Enum):
    """传闻来源类型"""
    EYEWITNESS = "EYEWITNESS"   # 目击 - 亲眼所见
    SECONDHAND = "SECONDHAND"   # 二手 - 从他人处获得
    INFERENCE = "INFERENCE"     # 推测 - 基于证物推断
    HEARSAY = "HEARSAY"         # 道听途说 - 未经证实


class RumorTone(str, Enum):
    """传闻语气/意图"""
    WARNING = "WARNING"         # 警告 - 提醒危险
    LURE = "LURE"               # 引诱 - 吸引前往
    INQUIRY = "INQUIRY"         # 求证 - 寻求确认
    REPORT = "REPORT"           # 报告 - 中性陈述
    SPECULATION = "SPECULATION" # 猜测 - 不确定推测


class RumorStatus(str, Enum):
    """传闻状态"""
    PRIVATE = "PRIVATE"         # 私藏
    SHARED = "SHARED"           # 已分享（给特定人/剧团）
    BROADCAST = "BROADCAST"     # 已广播（公开）
    VERIFIED_TRUE = "VERIFIED_TRUE"     # 已验证为真
    VERIFIED_FALSE = "VERIFIED_FALSE"   # 已验证为假（误读）
    EXPIRED = "EXPIRED"         # 已过期
    RETRACTED = "RETRACTED"     # 已撤回


class RumorCategory(str, Enum):
    """传闻类别"""
    LOCATION = "LOCATION"       # 地点相关
    CHARACTER = "CHARACTER"     # 人物相关
    EVENT = "EVENT"             # 事件相关
    OBJECT = "OBJECT"           # 物品相关
    PREDICTION = "PREDICTION"   # 预测类


class VerificationOutcome(str, Enum):
    """验证结果"""
    ACCURATE = "ACCURATE"       # 准确
    PARTIAL = "PARTIAL"         # 部分准确
    INACCURATE = "INACCURATE"   # 不准确
    MISLEADING = "MISLEADING"   # 误导性
    UNVERIFIABLE = "UNVERIFIABLE"  # 无法验证


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class RumorTemplate:
    """传闻模板（由Theme Pack定义）"""
    template_id: str
    category: RumorCategory
    pattern: str  # 填空模板，如 "在{location}发现了{object}的踪迹"
    required_evidence_types: List[str]  # 需要的证物类型
    credibility_base: float = 0.5  # 基础可信度
    spread_factor: float = 1.0  # 传播系数
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Rumor:
    """传闻实例"""
    rumor_id: str
    creator_id: str
    theatre_id: str
    
    # 内容
    content: str  # 传闻内容
    category: RumorCategory
    source: RumorSource
    tone: RumorTone
    
    # 关联
    based_on_evidence_ids: List[str] = field(default_factory=list)  # 基于的证物
    based_on_scene_id: Optional[str] = None  # 基于的场景
    related_stage_tags: List[str] = field(default_factory=list)  # 相关舞台标签
    
    # 状态
    status: RumorStatus = RumorStatus.PRIVATE
    
    # 可信度与影响
    credibility_score: float = 0.5  # 可信度评分 0-1
    spread_count: int = 0  # 传播次数
    view_count: int = 0  # 查看次数
    influence_score: float = 0.0  # 影响力评分
    
    # 时间
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    broadcast_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    
    # 验证
    verification_outcome: Optional[VerificationOutcome] = None
    verification_notes: Optional[str] = None
    
    # 误读追踪
    is_misread: bool = False
    misread_consequence: Optional[str] = None
    echo_id: Optional[str] = None  # 关联的回声ID
    
    # 元数据
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "rumor_id": self.rumor_id,
            "creator_id": self.creator_id,
            "theatre_id": self.theatre_id,
            "content": self.content,
            "category": self.category.value,
            "source": self.source.value,
            "tone": self.tone.value,
            "based_on_evidence_ids": self.based_on_evidence_ids,
            "based_on_scene_id": self.based_on_scene_id,
            "related_stage_tags": self.related_stage_tags,
            "status": self.status.value,
            "credibility_score": self.credibility_score,
            "spread_count": self.spread_count,
            "view_count": self.view_count,
            "influence_score": self.influence_score,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "broadcast_at": self.broadcast_at.isoformat() if self.broadcast_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_outcome": self.verification_outcome.value if self.verification_outcome else None,
            "is_misread": self.is_misread,
            "misread_consequence": self.misread_consequence
        }
    
    def is_active(self) -> bool:
        """检查传闻是否活跃"""
        if self.status in [RumorStatus.EXPIRED, RumorStatus.RETRACTED]:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class RumorShare:
    """传闻分享记录"""
    share_id: str
    rumor_id: str
    from_user_id: str
    to_user_id: Optional[str] = None  # None表示广播
    to_crew_id: Optional[str] = None
    shared_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_broadcast: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "share_id": self.share_id,
            "rumor_id": self.rumor_id,
            "from_user_id": self.from_user_id,
            "to_user_id": self.to_user_id,
            "to_crew_id": self.to_crew_id,
            "shared_at": self.shared_at.isoformat(),
            "is_broadcast": self.is_broadcast
        }


@dataclass
class RumorReaction:
    """传闻反应记录"""
    reaction_id: str
    rumor_id: str
    user_id: str
    reaction_type: str  # BELIEVE, DOUBT, INVESTIGATE, SPREAD, DEBUNK
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    comment: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "reaction_id": self.reaction_id,
            "rumor_id": self.rumor_id,
            "user_id": self.user_id,
            "reaction_type": self.reaction_type,
            "created_at": self.created_at.isoformat(),
            "comment": self.comment
        }


@dataclass
class MisreadEcho:
    """误读回声记录"""
    echo_id: str
    rumor_id: str
    theatre_id: str
    
    # 误读内容
    original_claim: str
    actual_truth: str
    deviation_type: str  # LOCATION, TIMING, IDENTITY, OUTCOME
    
    # 影响
    affected_stage_tags: List[str] = field(default_factory=list)
    consequence_description: str = ""
    world_var_changes: Dict[str, Any] = field(default_factory=dict)
    
    # 时间
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "echo_id": self.echo_id,
            "rumor_id": self.rumor_id,
            "theatre_id": self.theatre_id,
            "original_claim": self.original_claim,
            "actual_truth": self.actual_truth,
            "deviation_type": self.deviation_type,
            "affected_stage_tags": self.affected_stage_tags,
            "consequence_description": self.consequence_description,
            "world_var_changes": self.world_var_changes,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class StageHeatContribution:
    """舞台热度贡献"""
    stage_tag: str
    rumor_id: str
    contribution: float
    tone: RumorTone
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Rumor Template Registry
# =============================================================================
class RumorTemplateRegistry:
    """传闻模板注册表"""
    
    def __init__(self):
        self._templates: Dict[str, RumorTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """加载默认传闻模板"""
        default_templates = [
            RumorTemplate(
                template_id="tmpl_location_sighting",
                category=RumorCategory.LOCATION,
                pattern="有人在{location}附近看到了{subject}",
                required_evidence_types=["ev_signal", "ev_testimony"],
                credibility_base=0.6,
                spread_factor=1.2
            ),
            RumorTemplate(
                template_id="tmpl_event_prediction",
                category=RumorCategory.PREDICTION,
                pattern="据说{time}会在{location}发生{event}",
                required_evidence_types=["ev_document", "ev_communication"],
                credibility_base=0.4,
                spread_factor=1.5
            ),
            RumorTemplate(
                template_id="tmpl_character_action",
                category=RumorCategory.CHARACTER,
                pattern="{character}似乎正在{action}",
                required_evidence_types=["ev_testimony", "ev_trace"],
                credibility_base=0.5,
                spread_factor=1.0
            ),
            RumorTemplate(
                template_id="tmpl_object_discovery",
                category=RumorCategory.OBJECT,
                pattern="在{location}发现了{object}的踪迹",
                required_evidence_types=["ev_object", "ev_trace"],
                credibility_base=0.7,
                spread_factor=0.8
            ),
            RumorTemplate(
                template_id="tmpl_warning",
                category=RumorCategory.EVENT,
                pattern="警告：{location}区域可能存在{danger}",
                required_evidence_types=["ev_signal"],
                credibility_base=0.5,
                spread_factor=1.3
            )
        ]
        
        for template in default_templates:
            self._templates[template.template_id] = template
    
    def get_template(self, template_id: str) -> Optional[RumorTemplate]:
        return self._templates.get(template_id)
    
    def list_templates(self) -> List[RumorTemplate]:
        return list(self._templates.values())


# =============================================================================
# Rumor Service
# =============================================================================
class RumorService:
    """谣言系统服务"""
    
    # 默认过期时间（小时）
    DEFAULT_EXPIRY_HOURS = 48
    
    # 可信度衰减因子
    CREDIBILITY_DECAY_PER_SPREAD = 0.05
    
    # 影响力计算权重
    INFLUENCE_WEIGHTS = {
        "spread": 0.3,
        "view": 0.1,
        "credibility": 0.4,
        "verification": 0.2
    }
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.template_registry = RumorTemplateRegistry()
        
        # 内存存储
        self._rumors: Dict[str, Rumor] = {}
        self._shares: Dict[str, RumorShare] = {}
        self._reactions: Dict[str, RumorReaction] = {}
        self._echoes: Dict[str, MisreadEcho] = {}
        self._user_rumors: Dict[str, List[str]] = {}  # user_id -> [rumor_ids]
        self._user_received: Dict[str, List[str]] = {}  # user_id -> [rumor_ids received]
        self._stage_heat: Dict[str, List[StageHeatContribution]] = {}  # stage_tag -> contributions
    
    # =========================================================================
    # 传闻创建
    # =========================================================================
    def create_rumor(
        self,
        creator_id: str,
        theatre_id: str,
        content: str,
        category: str,
        source: str,
        tone: str,
        based_on_evidence_ids: Optional[List[str]] = None,
        based_on_scene_id: Optional[str] = None,
        related_stage_tags: Optional[List[str]] = None,
        expiry_hours: Optional[int] = None
    ) -> Rumor:
        """
        创建传闻
        
        Args:
            creator_id: 创建者ID
            theatre_id: 剧场ID
            content: 传闻内容
            category: 类别
            source: 来源类型
            tone: 语气
            based_on_evidence_ids: 基于的证物ID列表
            based_on_scene_id: 基于的场景ID
            related_stage_tags: 相关舞台标签
            expiry_hours: 过期时间（小时）
        
        Returns:
            创建的传闻
        """
        # 计算初始可信度
        credibility = self._calculate_initial_credibility(
            source=RumorSource(source),
            evidence_count=len(based_on_evidence_ids or [])
        )
        
        # 计算过期时间
        expiry = expiry_hours or self.DEFAULT_EXPIRY_HOURS
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry)
        
        rumor = Rumor(
            rumor_id=str(uuid.uuid4()),
            creator_id=creator_id,
            theatre_id=theatre_id,
            content=content,
            category=RumorCategory(category),
            source=RumorSource(source),
            tone=RumorTone(tone),
            based_on_evidence_ids=based_on_evidence_ids or [],
            based_on_scene_id=based_on_scene_id,
            related_stage_tags=related_stage_tags or [],
            credibility_score=credibility,
            expires_at=expires_at
        )
        
        # 存储
        self._rumors[rumor.rumor_id] = rumor
        
        # 更新用户传闻列表
        if creator_id not in self._user_rumors:
            self._user_rumors[creator_id] = []
        self._user_rumors[creator_id].append(rumor.rumor_id)
        
        logger.info(f"Rumor created: {rumor.rumor_id} by {creator_id}")
        
        return rumor
    
    def create_from_template(
        self,
        creator_id: str,
        theatre_id: str,
        template_id: str,
        fill_values: Dict[str, str],
        source: str,
        tone: str,
        based_on_evidence_ids: Optional[List[str]] = None
    ) -> Rumor:
        """
        基于模板创建传闻
        
        Args:
            creator_id: 创建者ID
            theatre_id: 剧场ID
            template_id: 模板ID
            fill_values: 填充值
            source: 来源类型
            tone: 语气
            based_on_evidence_ids: 基于的证物ID列表
        
        Returns:
            创建的传闻
        """
        template = self.template_registry.get_template(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")
        
        # 填充模板
        content = template.pattern
        for key, value in fill_values.items():
            content = content.replace(f"{{{key}}}", value)
        
        # 提取相关舞台标签
        stage_tags = []
        if "location" in fill_values:
            stage_tags.append(fill_values["location"])
        
        return self.create_rumor(
            creator_id=creator_id,
            theatre_id=theatre_id,
            content=content,
            category=template.category.value,
            source=source,
            tone=tone,
            based_on_evidence_ids=based_on_evidence_ids,
            related_stage_tags=stage_tags
        )
    
    def _calculate_initial_credibility(
        self,
        source: RumorSource,
        evidence_count: int
    ) -> float:
        """计算初始可信度"""
        # 基础可信度基于来源
        base_credibility = {
            RumorSource.EYEWITNESS: 0.7,
            RumorSource.SECONDHAND: 0.5,
            RumorSource.INFERENCE: 0.6,
            RumorSource.HEARSAY: 0.3
        }.get(source, 0.5)
        
        # 证物数量加成
        evidence_bonus = min(evidence_count * 0.1, 0.3)
        
        return min(base_credibility + evidence_bonus, 1.0)
    
    # =========================================================================
    # 传闻查询
    # =========================================================================
    def get_rumor(self, rumor_id: str) -> Optional[Rumor]:
        """获取传闻"""
        rumor = self._rumors.get(rumor_id)
        if rumor:
            rumor.view_count += 1
        return rumor
    
    def get_user_rumors(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[Rumor]:
        """获取用户创建的传闻"""
        rumor_ids = self._user_rumors.get(user_id, [])
        rumors = []
        
        for rumor_id in rumor_ids:
            rumor = self._rumors.get(rumor_id)
            if not rumor:
                continue
            if not include_expired and not rumor.is_active():
                continue
            rumors.append(rumor)
        
        return rumors
    
    def get_received_rumors(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[Rumor]:
        """获取用户收到的传闻"""
        rumor_ids = self._user_received.get(user_id, [])
        rumors = []
        
        for rumor_id in rumor_ids:
            rumor = self._rumors.get(rumor_id)
            if not rumor:
                continue
            if not include_expired and not rumor.is_active():
                continue
            rumors.append(rumor)
        
        return rumors
    
    def get_broadcast_rumors(
        self,
        theatre_id: str,
        stage_tag: Optional[str] = None,
        limit: int = 20
    ) -> List[Rumor]:
        """获取广播的传闻"""
        rumors = []
        
        for rumor in self._rumors.values():
            if rumor.theatre_id != theatre_id:
                continue
            if rumor.status != RumorStatus.BROADCAST:
                continue
            if not rumor.is_active():
                continue
            if stage_tag and stage_tag not in rumor.related_stage_tags:
                continue
            rumors.append(rumor)
        
        # 按影响力排序
        rumors.sort(key=lambda r: r.influence_score, reverse=True)
        
        return rumors[:limit]
    
    # =========================================================================
    # 传闻分享与广播
    # =========================================================================
    def share_rumor(
        self,
        rumor_id: str,
        from_user_id: str,
        to_user_id: Optional[str] = None,
        to_crew_id: Optional[str] = None
    ) -> RumorShare:
        """
        分享传闻给特定用户或剧团
        
        Args:
            rumor_id: 传闻ID
            from_user_id: 分享者ID
            to_user_id: 接收者用户ID
            to_crew_id: 接收者剧团ID
        
        Returns:
            分享记录
        """
        rumor = self._rumors.get(rumor_id)
        if not rumor:
            raise ValueError(f"Rumor not found: {rumor_id}")
        
        if not rumor.is_active():
            raise ValueError("Rumor is not active")
        
        share = RumorShare(
            share_id=str(uuid.uuid4()),
            rumor_id=rumor_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            to_crew_id=to_crew_id,
            is_broadcast=False
        )
        
        # 更新传闻状态
        if rumor.status == RumorStatus.PRIVATE:
            rumor.status = RumorStatus.SHARED
        
        # 更新传播计数和可信度
        rumor.spread_count += 1
        rumor.credibility_score = max(
            0.1,
            rumor.credibility_score - self.CREDIBILITY_DECAY_PER_SPREAD
        )
        
        # 更新接收者列表
        if to_user_id:
            if to_user_id not in self._user_received:
                self._user_received[to_user_id] = []
            self._user_received[to_user_id].append(rumor_id)
        
        # 存储
        self._shares[share.share_id] = share
        
        # 更新影响力
        self._update_influence(rumor)
        
        logger.info(f"Rumor {rumor_id} shared from {from_user_id} to {to_user_id or to_crew_id}")
        
        return share
    
    def broadcast_rumor(
        self,
        rumor_id: str,
        user_id: str
    ) -> RumorShare:
        """
        广播传闻（公开）
        
        Args:
            rumor_id: 传闻ID
            user_id: 广播者ID
        
        Returns:
            分享记录
        """
        rumor = self._rumors.get(rumor_id)
        if not rumor:
            raise ValueError(f"Rumor not found: {rumor_id}")
        
        if rumor.creator_id != user_id:
            raise ValueError("Only creator can broadcast")
        
        if not rumor.is_active():
            raise ValueError("Rumor is not active")
        
        share = RumorShare(
            share_id=str(uuid.uuid4()),
            rumor_id=rumor_id,
            from_user_id=user_id,
            is_broadcast=True
        )
        
        # 更新传闻状态
        rumor.status = RumorStatus.BROADCAST
        rumor.broadcast_at = datetime.now(timezone.utc)
        
        # 广播会大幅增加传播计数
        rumor.spread_count += 10
        
        # 存储
        self._shares[share.share_id] = share
        
        # 更新舞台热度
        self._update_stage_heat(rumor)
        
        # 更新影响力
        self._update_influence(rumor)
        
        logger.info(f"Rumor {rumor_id} broadcast by {user_id}")
        
        return share
    
    # =========================================================================
    # 传闻验证
    # =========================================================================
    def verify_rumor(
        self,
        rumor_id: str,
        verifier_id: str,
        actual_truth: str,
        is_accurate: bool,
        deviation_type: Optional[str] = None
    ) -> Tuple[VerificationOutcome, Optional[MisreadEcho]]:
        """
        验证传闻
        
        Args:
            rumor_id: 传闻ID
            verifier_id: 验证者ID
            actual_truth: 实际真相
            is_accurate: 是否准确
            deviation_type: 偏差类型（如果不准确）
        
        Returns:
            (验证结果, 误读回声（如果有）)
        """
        rumor = self._rumors.get(rumor_id)
        if not rumor:
            raise ValueError(f"Rumor not found: {rumor_id}")
        
        rumor.verified_at = datetime.now(timezone.utc)
        
        if is_accurate:
            rumor.verification_outcome = VerificationOutcome.ACCURATE
            rumor.status = RumorStatus.VERIFIED_TRUE
            rumor.credibility_score = min(1.0, rumor.credibility_score + 0.2)
            
            logger.info(f"Rumor {rumor_id} verified as accurate")
            return VerificationOutcome.ACCURATE, None
        else:
            # 误读处理
            rumor.verification_outcome = VerificationOutcome.INACCURATE
            rumor.status = RumorStatus.VERIFIED_FALSE
            rumor.is_misread = True
            
            # 创建误读回声
            echo = self._create_misread_echo(
                rumor=rumor,
                actual_truth=actual_truth,
                deviation_type=deviation_type or "UNKNOWN"
            )
            
            rumor.echo_id = echo.echo_id
            rumor.misread_consequence = echo.consequence_description
            
            logger.info(f"Rumor {rumor_id} verified as misread, echo created: {echo.echo_id}")
            return VerificationOutcome.INACCURATE, echo
    
    def _create_misread_echo(
        self,
        rumor: Rumor,
        actual_truth: str,
        deviation_type: str
    ) -> MisreadEcho:
        """创建误读回声"""
        # 根据传播程度和语气计算后果
        consequence = self._calculate_misread_consequence(rumor, deviation_type)
        
        echo = MisreadEcho(
            echo_id=str(uuid.uuid4()),
            rumor_id=rumor.rumor_id,
            theatre_id=rumor.theatre_id,
            original_claim=rumor.content,
            actual_truth=actual_truth,
            deviation_type=deviation_type,
            affected_stage_tags=rumor.related_stage_tags,
            consequence_description=consequence["description"],
            world_var_changes=consequence["world_var_changes"]
        )
        
        self._echoes[echo.echo_id] = echo
        
        return echo
    
    def _calculate_misread_consequence(
        self,
        rumor: Rumor,
        deviation_type: str
    ) -> Dict:
        """计算误读后果"""
        # 基于传播程度和语气计算影响
        spread_impact = min(rumor.spread_count / 50.0, 1.0)
        
        # 不同语气的后果
        tone_effects = {
            RumorTone.WARNING: {
                "description": "虚假警告导致区域被过度回避，资源开始积累",
                "world_var_changes": {"area_activity": -0.2, "resource_density": 0.1}
            },
            RumorTone.LURE: {
                "description": "虚假引诱导致大量玩家涌入，引起系统注意",
                "world_var_changes": {"area_activity": 0.3, "patrol_intensity": 0.2}
            },
            RumorTone.INQUIRY: {
                "description": "错误求证引发连锁调查，消耗社区资源",
                "world_var_changes": {"community_trust": -0.1}
            },
            RumorTone.REPORT: {
                "description": "错误报告被记录，可能影响后续判断",
                "world_var_changes": {"information_noise": 0.1}
            },
            RumorTone.SPECULATION: {
                "description": "错误猜测成为流行观点，扭曲认知",
                "world_var_changes": {"narrative_drift": 0.15}
            }
        }
        
        base_effect = tone_effects.get(rumor.tone, {
            "description": "误读产生了微妙的影响",
            "world_var_changes": {}
        })
        
        # 根据传播程度放大效果
        amplified_changes = {}
        for key, value in base_effect["world_var_changes"].items():
            amplified_changes[key] = value * (1 + spread_impact)
        
        return {
            "description": base_effect["description"],
            "world_var_changes": amplified_changes
        }
    
    # =========================================================================
    # 传闻反应
    # =========================================================================
    def add_reaction(
        self,
        rumor_id: str,
        user_id: str,
        reaction_type: str,
        comment: Optional[str] = None
    ) -> RumorReaction:
        """
        添加传闻反应
        
        Args:
            rumor_id: 传闻ID
            user_id: 用户ID
            reaction_type: 反应类型 (BELIEVE, DOUBT, INVESTIGATE, SPREAD, DEBUNK)
            comment: 评论
        
        Returns:
            反应记录
        """
        rumor = self._rumors.get(rumor_id)
        if not rumor:
            raise ValueError(f"Rumor not found: {rumor_id}")
        
        reaction = RumorReaction(
            reaction_id=str(uuid.uuid4()),
            rumor_id=rumor_id,
            user_id=user_id,
            reaction_type=reaction_type,
            comment=comment
        )
        
        # 根据反应类型调整可信度
        credibility_adjustments = {
            "BELIEVE": 0.02,
            "DOUBT": -0.02,
            "INVESTIGATE": 0.01,
            "SPREAD": 0.01,
            "DEBUNK": -0.05
        }
        
        adjustment = credibility_adjustments.get(reaction_type, 0)
        rumor.credibility_score = max(0, min(1, rumor.credibility_score + adjustment))
        
        # 存储
        self._reactions[reaction.reaction_id] = reaction
        
        # 更新影响力
        self._update_influence(rumor)
        
        return reaction
    
    def get_reactions(self, rumor_id: str) -> List[RumorReaction]:
        """获取传闻的所有反应"""
        return [r for r in self._reactions.values() if r.rumor_id == rumor_id]
    
    # =========================================================================
    # 舞台热度
    # =========================================================================
    def _update_stage_heat(self, rumor: Rumor):
        """更新舞台热度"""
        for stage_tag in rumor.related_stage_tags:
            contribution = StageHeatContribution(
                stage_tag=stage_tag,
                rumor_id=rumor.rumor_id,
                contribution=rumor.influence_score * 0.1,
                tone=rumor.tone
            )
            
            if stage_tag not in self._stage_heat:
                self._stage_heat[stage_tag] = []
            self._stage_heat[stage_tag].append(contribution)
    
    def get_stage_heat(self, stage_tag: str) -> Dict:
        """获取舞台热度"""
        contributions = self._stage_heat.get(stage_tag, [])
        
        # 只计算最近24小时的贡献
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent = [c for c in contributions if c.created_at > cutoff]
        
        total_heat = sum(c.contribution for c in recent)
        
        # 按语气分类
        tone_breakdown = {}
        for c in recent:
            tone = c.tone.value
            tone_breakdown[tone] = tone_breakdown.get(tone, 0) + c.contribution
        
        return {
            "stage_tag": stage_tag,
            "total_heat": total_heat,
            "contribution_count": len(recent),
            "tone_breakdown": tone_breakdown
        }
    
    def get_heat_map(self, theatre_id: str) -> Dict[str, float]:
        """获取热度地图"""
        heat_map = {}
        
        for stage_tag in self._stage_heat.keys():
            heat_data = self.get_stage_heat(stage_tag)
            heat_map[stage_tag] = heat_data["total_heat"]
        
        return heat_map
    
    # =========================================================================
    # 影响力计算
    # =========================================================================
    def _update_influence(self, rumor: Rumor):
        """更新传闻影响力"""
        spread_score = min(rumor.spread_count / 100.0, 1.0)
        view_score = min(rumor.view_count / 500.0, 1.0)
        credibility_score = rumor.credibility_score
        verification_score = 1.0 if rumor.verification_outcome == VerificationOutcome.ACCURATE else 0.5
        
        rumor.influence_score = (
            self.INFLUENCE_WEIGHTS["spread"] * spread_score +
            self.INFLUENCE_WEIGHTS["view"] * view_score +
            self.INFLUENCE_WEIGHTS["credibility"] * credibility_score +
            self.INFLUENCE_WEIGHTS["verification"] * verification_score
        )
    
    # =========================================================================
    # 过期处理
    # =========================================================================
    def process_expirations(self, theatre_id: str) -> int:
        """处理过期传闻"""
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for rumor in self._rumors.values():
            if rumor.theatre_id != theatre_id:
                continue
            
            if rumor.status in [RumorStatus.EXPIRED, RumorStatus.RETRACTED]:
                continue
            
            if rumor.expires_at and now > rumor.expires_at:
                rumor.status = RumorStatus.EXPIRED
                expired_count += 1
                logger.info(f"Rumor {rumor.rumor_id} expired")
        
        return expired_count
    
    # =========================================================================
    # 统计
    # =========================================================================
    def get_statistics(self, theatre_id: str) -> Dict:
        """获取谣言系统统计"""
        rumors = [r for r in self._rumors.values() if r.theatre_id == theatre_id]
        
        status_counts = {status.value: 0 for status in RumorStatus}
        category_counts = {cat.value: 0 for cat in RumorCategory}
        
        total_spread = 0
        total_views = 0
        misread_count = 0
        
        for rumor in rumors:
            status_counts[rumor.status.value] += 1
            category_counts[rumor.category.value] += 1
            total_spread += rumor.spread_count
            total_views += rumor.view_count
            if rumor.is_misread:
                misread_count += 1
        
        return {
            "total_rumors": len(rumors),
            "by_status": status_counts,
            "by_category": category_counts,
            "total_spread": total_spread,
            "total_views": total_views,
            "misread_count": misread_count,
            "active_echoes": len([e for e in self._echoes.values() if e.theatre_id == theatre_id])
        }
