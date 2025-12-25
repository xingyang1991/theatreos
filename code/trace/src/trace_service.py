"""
TheatreOS Trace System
痕迹系统 - 记录玩家关键行为，使其成为可被其他玩家发现的"痕迹证物"

核心概念:
- 痕迹 = 玩家行为的持久化记录
- 痕迹可以被其他玩家发现，成为证物
- 痕迹有衰减机制，随时间逐渐消失
- 痕迹密度影响区域氛围

痕迹类型:
- VISIT: 到访痕迹（玩家访问某个舞台）
- OBSERVE: 观察痕迹（玩家观看某个场景）
- VOTE: 投票痕迹（玩家在门投票）
- TRADE: 交易痕迹（玩家进行证物交易）
- RUMOR: 谣言痕迹（玩家创建/传播谣言）
- DISCOVER: 发现痕迹（玩家发现其他玩家的痕迹）
"""
import logging
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from decimal import Decimal
import random

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class TraceType(str, Enum):
    """痕迹类型"""
    VISIT = "VISIT"           # 到访痕迹
    OBSERVE = "OBSERVE"       # 观察痕迹
    VOTE = "VOTE"             # 投票痕迹
    TRADE = "TRADE"           # 交易痕迹
    RUMOR = "RUMOR"           # 谣言痕迹
    DISCOVER = "DISCOVER"     # 发现痕迹
    SUBMIT = "SUBMIT"         # 提交痕迹
    CREW_ACTION = "CREW_ACTION"  # 剧团行动痕迹


class TraceVisibility(str, Enum):
    """痕迹可见性"""
    PUBLIC = "PUBLIC"         # 公开可见
    RING_A = "RING_A"         # 仅Ring A可见
    RING_B = "RING_B"         # Ring B及以上可见
    CREW_ONLY = "CREW_ONLY"   # 仅剧团成员可见
    PRIVATE = "PRIVATE"       # 仅自己可见


class TraceStatus(str, Enum):
    """痕迹状态"""
    ACTIVE = "ACTIVE"         # 活跃
    FADING = "FADING"         # 正在消退
    FADED = "FADED"           # 已消退
    DISCOVERED = "DISCOVERED" # 已被发现
    ARCHIVED = "ARCHIVED"     # 已归档


class DiscoveryMethod(str, Enum):
    """发现方式"""
    PROXIMITY = "PROXIMITY"   # 接近发现
    SEARCH = "SEARCH"         # 主动搜索
    RANDOM = "RANDOM"         # 随机发现
    CREW_SHARE = "CREW_SHARE" # 剧团共享
    SYSTEM = "SYSTEM"         # 系统推送


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class TraceTemplate:
    """痕迹模板（定义不同类型痕迹的属性）"""
    trace_type: TraceType
    base_intensity: float = 1.0      # 基础强度
    decay_rate: float = 0.1          # 每小时衰减率
    discovery_difficulty: float = 0.5  # 发现难度 0-1
    evidence_conversion_rate: float = 0.3  # 转化为证物的概率
    default_visibility: TraceVisibility = TraceVisibility.PUBLIC
    default_ttl_hours: int = 24      # 默认存活时间
    
    def to_dict(self) -> Dict:
        return {
            "trace_type": self.trace_type.value,
            "base_intensity": self.base_intensity,
            "decay_rate": self.decay_rate,
            "discovery_difficulty": self.discovery_difficulty,
            "evidence_conversion_rate": self.evidence_conversion_rate,
            "default_visibility": self.default_visibility.value,
            "default_ttl_hours": self.default_ttl_hours
        }


@dataclass
class Trace:
    """痕迹实例"""
    trace_id: str
    theatre_id: str
    creator_id: str
    
    # 类型和位置
    trace_type: TraceType
    stage_id: str
    stage_tag: str
    
    # 关联信息
    related_scene_id: Optional[str] = None
    related_gate_id: Optional[str] = None
    related_evidence_id: Optional[str] = None
    related_rumor_id: Optional[str] = None
    
    # 状态
    status: TraceStatus = TraceStatus.ACTIVE
    visibility: TraceVisibility = TraceVisibility.PUBLIC
    
    # 强度和衰减
    intensity: float = 1.0           # 当前强度 0-1
    decay_rate: float = 0.1          # 每小时衰减率
    
    # 发现相关
    discovery_difficulty: float = 0.5
    discovered_by: List[str] = field(default_factory=list)
    discovery_count: int = 0
    
    # 描述
    description: str = ""
    metadata: Dict = field(default_factory=dict)
    
    # 时间
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_decay_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "theatre_id": self.theatre_id,
            "creator_id": self.creator_id,
            "trace_type": self.trace_type.value,
            "stage_id": self.stage_id,
            "stage_tag": self.stage_tag,
            "related_scene_id": self.related_scene_id,
            "related_gate_id": self.related_gate_id,
            "related_evidence_id": self.related_evidence_id,
            "related_rumor_id": self.related_rumor_id,
            "status": self.status.value,
            "visibility": self.visibility.value,
            "intensity": self.intensity,
            "decay_rate": self.decay_rate,
            "discovery_difficulty": self.discovery_difficulty,
            "discovery_count": self.discovery_count,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    def is_active(self) -> bool:
        """检查痕迹是否活跃"""
        if self.status in [TraceStatus.FADED, TraceStatus.ARCHIVED]:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        if self.intensity <= 0:
            return False
        return True
    
    def apply_decay(self, hours_passed: float = 1.0) -> float:
        """应用衰减，返回新强度"""
        decay_amount = self.decay_rate * hours_passed
        self.intensity = max(0, self.intensity - decay_amount)
        self.last_decay_at = datetime.now(timezone.utc)
        
        if self.intensity <= 0.1:
            self.status = TraceStatus.FADING
        if self.intensity <= 0:
            self.status = TraceStatus.FADED
        
        return self.intensity


@dataclass
class TraceDiscovery:
    """痕迹发现记录"""
    discovery_id: str
    trace_id: str
    discoverer_id: str
    method: DiscoveryMethod
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # 发现时的上下文
    discoverer_ring: str = "C"
    discoverer_stage_id: Optional[str] = None
    
    # 转化结果
    converted_to_evidence: bool = False
    evidence_instance_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "discovery_id": self.discovery_id,
            "trace_id": self.trace_id,
            "discoverer_id": self.discoverer_id,
            "method": self.method.value,
            "discovered_at": self.discovered_at.isoformat(),
            "discoverer_ring": self.discoverer_ring,
            "converted_to_evidence": self.converted_to_evidence,
            "evidence_instance_id": self.evidence_instance_id
        }


@dataclass
class StageDensity:
    """舞台痕迹密度"""
    stage_id: str
    stage_tag: str
    total_traces: int = 0
    active_traces: int = 0
    total_intensity: float = 0.0
    density_score: float = 0.0
    
    # 按类型分布
    type_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 最近活动
    last_trace_at: Optional[datetime] = None
    recent_discoveries: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "stage_id": self.stage_id,
            "stage_tag": self.stage_tag,
            "total_traces": self.total_traces,
            "active_traces": self.active_traces,
            "total_intensity": self.total_intensity,
            "density_score": self.density_score,
            "type_distribution": self.type_distribution,
            "last_trace_at": self.last_trace_at.isoformat() if self.last_trace_at else None,
            "recent_discoveries": self.recent_discoveries
        }


@dataclass
class UserTraceProfile:
    """用户痕迹档案"""
    user_id: str
    theatre_id: str
    
    # 留下的痕迹
    traces_left: int = 0
    traces_active: int = 0
    
    # 发现的痕迹
    traces_discovered: int = 0
    evidence_converted: int = 0
    
    # 最常访问的舞台
    frequent_stages: List[str] = field(default_factory=list)
    
    # 活跃时段
    active_hours: Dict[int, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "theatre_id": self.theatre_id,
            "traces_left": self.traces_left,
            "traces_active": self.traces_active,
            "traces_discovered": self.traces_discovered,
            "evidence_converted": self.evidence_converted,
            "frequent_stages": self.frequent_stages,
            "active_hours": self.active_hours
        }


# =============================================================================
# Trace Template Registry
# =============================================================================
class TraceTemplateRegistry:
    """痕迹模板注册表"""
    
    def __init__(self):
        self._templates: Dict[TraceType, TraceTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """加载默认痕迹模板"""
        default_templates = [
            TraceTemplate(
                trace_type=TraceType.VISIT,
                base_intensity=0.5,
                decay_rate=0.15,
                discovery_difficulty=0.3,
                evidence_conversion_rate=0.1,
                default_visibility=TraceVisibility.PUBLIC,
                default_ttl_hours=12
            ),
            TraceTemplate(
                trace_type=TraceType.OBSERVE,
                base_intensity=0.7,
                decay_rate=0.1,
                discovery_difficulty=0.4,
                evidence_conversion_rate=0.2,
                default_visibility=TraceVisibility.RING_B,
                default_ttl_hours=24
            ),
            TraceTemplate(
                trace_type=TraceType.VOTE,
                base_intensity=0.8,
                decay_rate=0.08,
                discovery_difficulty=0.5,
                evidence_conversion_rate=0.3,
                default_visibility=TraceVisibility.PUBLIC,
                default_ttl_hours=48
            ),
            TraceTemplate(
                trace_type=TraceType.TRADE,
                base_intensity=0.6,
                decay_rate=0.12,
                discovery_difficulty=0.6,
                evidence_conversion_rate=0.25,
                default_visibility=TraceVisibility.RING_A,
                default_ttl_hours=36
            ),
            TraceTemplate(
                trace_type=TraceType.RUMOR,
                base_intensity=0.9,
                decay_rate=0.05,
                discovery_difficulty=0.2,
                evidence_conversion_rate=0.4,
                default_visibility=TraceVisibility.PUBLIC,
                default_ttl_hours=72
            ),
            TraceTemplate(
                trace_type=TraceType.DISCOVER,
                base_intensity=0.4,
                decay_rate=0.2,
                discovery_difficulty=0.7,
                evidence_conversion_rate=0.15,
                default_visibility=TraceVisibility.CREW_ONLY,
                default_ttl_hours=12
            ),
            TraceTemplate(
                trace_type=TraceType.SUBMIT,
                base_intensity=1.0,
                decay_rate=0.03,
                discovery_difficulty=0.3,
                evidence_conversion_rate=0.5,
                default_visibility=TraceVisibility.PUBLIC,
                default_ttl_hours=96
            ),
            TraceTemplate(
                trace_type=TraceType.CREW_ACTION,
                base_intensity=0.8,
                decay_rate=0.06,
                discovery_difficulty=0.4,
                evidence_conversion_rate=0.35,
                default_visibility=TraceVisibility.CREW_ONLY,
                default_ttl_hours=48
            )
        ]
        
        for template in default_templates:
            self._templates[template.trace_type] = template
    
    def get_template(self, trace_type: TraceType) -> Optional[TraceTemplate]:
        return self._templates.get(trace_type)
    
    def list_templates(self) -> List[TraceTemplate]:
        return list(self._templates.values())


# =============================================================================
# Trace Service
# =============================================================================
class TraceService:
    """痕迹系统服务"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.template_registry = TraceTemplateRegistry()
        
        # 内存存储
        self._traces: Dict[str, Trace] = {}
        self._discoveries: Dict[str, TraceDiscovery] = {}
        self._user_traces: Dict[str, List[str]] = {}  # user_id -> [trace_ids]
        self._stage_traces: Dict[str, List[str]] = {}  # stage_id -> [trace_ids]
        self._user_discoveries: Dict[str, List[str]] = {}  # user_id -> [discovery_ids]
    
    # =========================================================================
    # 痕迹创建
    # =========================================================================
    def leave_trace(
        self,
        theatre_id: str,
        creator_id: str,
        trace_type: str,
        stage_id: str,
        stage_tag: str,
        description: str = "",
        related_scene_id: Optional[str] = None,
        related_gate_id: Optional[str] = None,
        related_evidence_id: Optional[str] = None,
        related_rumor_id: Optional[str] = None,
        visibility: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Trace:
        """
        留下痕迹
        
        Args:
            theatre_id: 剧场ID
            creator_id: 创建者ID
            trace_type: 痕迹类型
            stage_id: 舞台ID
            stage_tag: 舞台标签
            description: 描述
            related_*: 关联的其他实体ID
            visibility: 可见性
            metadata: 元数据
        
        Returns:
            创建的痕迹
        """
        trace_type_enum = TraceType(trace_type)
        template = self.template_registry.get_template(trace_type_enum)
        
        if not template:
            raise ValueError(f"Unknown trace type: {trace_type}")
        
        # 计算过期时间
        expires_at = datetime.now(timezone.utc) + timedelta(hours=template.default_ttl_hours)
        
        # 确定可见性
        vis = TraceVisibility(visibility) if visibility else template.default_visibility
        
        trace = Trace(
            trace_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            creator_id=creator_id,
            trace_type=trace_type_enum,
            stage_id=stage_id,
            stage_tag=stage_tag,
            related_scene_id=related_scene_id,
            related_gate_id=related_gate_id,
            related_evidence_id=related_evidence_id,
            related_rumor_id=related_rumor_id,
            status=TraceStatus.ACTIVE,
            visibility=vis,
            intensity=template.base_intensity,
            decay_rate=template.decay_rate,
            discovery_difficulty=template.discovery_difficulty,
            description=description or self._generate_description(trace_type_enum, stage_tag),
            metadata=metadata or {},
            expires_at=expires_at
        )
        
        # 存储
        self._traces[trace.trace_id] = trace
        
        # 更新索引
        if creator_id not in self._user_traces:
            self._user_traces[creator_id] = []
        self._user_traces[creator_id].append(trace.trace_id)
        
        if stage_id not in self._stage_traces:
            self._stage_traces[stage_id] = []
        self._stage_traces[stage_id].append(trace.trace_id)
        
        logger.info(f"Trace left: {trace.trace_id} by {creator_id} at {stage_tag}")
        
        return trace
    
    def _generate_description(self, trace_type: TraceType, stage_tag: str) -> str:
        """生成痕迹描述"""
        descriptions = {
            TraceType.VISIT: f"有人曾在{stage_tag}附近徘徊",
            TraceType.OBSERVE: f"有人在{stage_tag}仔细观察过什么",
            TraceType.VOTE: f"有人在{stage_tag}参与了一次重要决定",
            TraceType.TRADE: f"有人在{stage_tag}进行了一次交易",
            TraceType.RUMOR: f"有人在{stage_tag}散播了一些消息",
            TraceType.DISCOVER: f"有人在{stage_tag}发现了什么",
            TraceType.SUBMIT: f"有人在{stage_tag}提交了重要证据",
            TraceType.CREW_ACTION: f"一群人在{stage_tag}采取了行动"
        }
        return descriptions.get(trace_type, f"有人在{stage_tag}留下了痕迹")
    
    # =========================================================================
    # 痕迹查询
    # =========================================================================
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取痕迹"""
        return self._traces.get(trace_id)
    
    def get_user_traces(
        self,
        user_id: str,
        include_faded: bool = False
    ) -> List[Trace]:
        """获取用户留下的痕迹"""
        trace_ids = self._user_traces.get(user_id, [])
        traces = []
        
        for trace_id in trace_ids:
            trace = self._traces.get(trace_id)
            if not trace:
                continue
            if not include_faded and not trace.is_active():
                continue
            traces.append(trace)
        
        return traces
    
    def get_stage_traces(
        self,
        stage_id: str,
        viewer_id: Optional[str] = None,
        viewer_ring: str = "C",
        viewer_crew_id: Optional[str] = None,
        include_faded: bool = False
    ) -> List[Trace]:
        """
        获取舞台上的痕迹
        
        Args:
            stage_id: 舞台ID
            viewer_id: 查看者ID（用于过滤可见性）
            viewer_ring: 查看者的Ring等级
            viewer_crew_id: 查看者的剧团ID
            include_faded: 是否包含已消退的痕迹
        
        Returns:
            可见的痕迹列表
        """
        trace_ids = self._stage_traces.get(stage_id, [])
        traces = []
        
        for trace_id in trace_ids:
            trace = self._traces.get(trace_id)
            if not trace:
                continue
            if not include_faded and not trace.is_active():
                continue
            
            # 检查可见性
            if not self._check_visibility(trace, viewer_id, viewer_ring, viewer_crew_id):
                continue
            
            traces.append(trace)
        
        # 按强度排序
        traces.sort(key=lambda t: t.intensity, reverse=True)
        
        return traces
    
    def _check_visibility(
        self,
        trace: Trace,
        viewer_id: Optional[str],
        viewer_ring: str,
        viewer_crew_id: Optional[str]
    ) -> bool:
        """检查痕迹对查看者是否可见"""
        # 创建者总是可见
        if viewer_id and trace.creator_id == viewer_id:
            return True
        
        # 公开痕迹
        if trace.visibility == TraceVisibility.PUBLIC:
            return True
        
        # Ring限制
        if trace.visibility == TraceVisibility.RING_A:
            return viewer_ring == "A"
        if trace.visibility == TraceVisibility.RING_B:
            return viewer_ring in ["A", "B"]
        
        # 剧团限制
        if trace.visibility == TraceVisibility.CREW_ONLY:
            # 需要在同一剧团（这里简化处理）
            return viewer_crew_id is not None
        
        # 私有
        if trace.visibility == TraceVisibility.PRIVATE:
            return viewer_id and trace.creator_id == viewer_id
        
        return False
    
    # =========================================================================
    # 痕迹发现
    # =========================================================================
    def discover_trace(
        self,
        trace_id: str,
        discoverer_id: str,
        method: str = "PROXIMITY",
        discoverer_ring: str = "C",
        discoverer_stage_id: Optional[str] = None
    ) -> Tuple[TraceDiscovery, Optional[Dict]]:
        """
        发现痕迹
        
        Args:
            trace_id: 痕迹ID
            discoverer_id: 发现者ID
            method: 发现方式
            discoverer_ring: 发现者Ring等级
            discoverer_stage_id: 发现者所在舞台
        
        Returns:
            (发现记录, 转化的证物信息（如果有）)
        """
        trace = self._traces.get(trace_id)
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        
        if not trace.is_active():
            raise ValueError("Trace is not active")
        
        # 检查是否已经发现过
        if discoverer_id in trace.discovered_by:
            raise ValueError("Already discovered this trace")
        
        # 创建发现记录
        discovery = TraceDiscovery(
            discovery_id=str(uuid.uuid4()),
            trace_id=trace_id,
            discoverer_id=discoverer_id,
            method=DiscoveryMethod(method),
            discoverer_ring=discoverer_ring,
            discoverer_stage_id=discoverer_stage_id
        )
        
        # 更新痕迹
        trace.discovered_by.append(discoverer_id)
        trace.discovery_count += 1
        
        # 存储
        self._discoveries[discovery.discovery_id] = discovery
        
        if discoverer_id not in self._user_discoveries:
            self._user_discoveries[discoverer_id] = []
        self._user_discoveries[discoverer_id].append(discovery.discovery_id)
        
        # 尝试转化为证物
        evidence_info = None
        template = self.template_registry.get_template(trace.trace_type)
        if template and random.random() < template.evidence_conversion_rate:
            evidence_info = self._convert_to_evidence(trace, discovery)
            discovery.converted_to_evidence = True
            discovery.evidence_instance_id = evidence_info.get("instance_id")
        
        logger.info(f"Trace {trace_id} discovered by {discoverer_id}")
        
        return discovery, evidence_info
    
    def _convert_to_evidence(self, trace: Trace, discovery: TraceDiscovery) -> Dict:
        """将痕迹转化为证物（返回证物信息，实际创建由Evidence System完成）"""
        # 根据痕迹类型确定证物类型
        evidence_type_mapping = {
            TraceType.VISIT: "ev_trace",
            TraceType.OBSERVE: "ev_testimony",
            TraceType.VOTE: "ev_record",
            TraceType.TRADE: "ev_transaction",
            TraceType.RUMOR: "ev_communication",
            TraceType.DISCOVER: "ev_trace",
            TraceType.SUBMIT: "ev_document",
            TraceType.CREW_ACTION: "ev_trace"
        }
        
        # 根据痕迹强度确定证物等级
        if trace.intensity >= 0.8:
            tier = "B"
        elif trace.intensity >= 0.5:
            tier = "C"
        else:
            tier = "D"
        
        return {
            "instance_id": str(uuid.uuid4()),
            "type_id": evidence_type_mapping.get(trace.trace_type, "ev_trace"),
            "tier": tier,
            "source": "TRACE_DISCOVERY",
            "source_trace_id": trace.trace_id,
            "description": f"从痕迹中发现: {trace.description}"
        }
    
    def search_traces(
        self,
        theatre_id: str,
        searcher_id: str,
        stage_id: str,
        searcher_ring: str = "C",
        search_intensity: float = 0.5
    ) -> List[Tuple[Trace, float]]:
        """
        主动搜索痕迹
        
        Args:
            theatre_id: 剧场ID
            searcher_id: 搜索者ID
            stage_id: 搜索的舞台ID
            searcher_ring: 搜索者Ring等级
            search_intensity: 搜索强度 0-1
        
        Returns:
            [(痕迹, 发现概率)]
        """
        traces = self.get_stage_traces(
            stage_id=stage_id,
            viewer_id=searcher_id,
            viewer_ring=searcher_ring
        )
        
        results = []
        for trace in traces:
            # 已发现的跳过
            if searcher_id in trace.discovered_by:
                continue
            
            # 计算发现概率
            # 基础概率 = (1 - 发现难度) * 痕迹强度 * 搜索强度
            base_prob = (1 - trace.discovery_difficulty) * trace.intensity * search_intensity
            
            # Ring加成
            ring_bonus = {"A": 0.3, "B": 0.15, "C": 0}.get(searcher_ring, 0)
            
            discovery_prob = min(1.0, base_prob + ring_bonus)
            
            if discovery_prob > 0:
                results.append((trace, discovery_prob))
        
        # 按发现概率排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    # =========================================================================
    # 痕迹衰减
    # =========================================================================
    def process_decay(self, theatre_id: str, hours_passed: float = 1.0) -> Dict:
        """
        处理痕迹衰减
        
        Args:
            theatre_id: 剧场ID
            hours_passed: 经过的小时数
        
        Returns:
            处理结果统计
        """
        decayed_count = 0
        faded_count = 0
        
        for trace in self._traces.values():
            if trace.theatre_id != theatre_id:
                continue
            
            if not trace.is_active():
                continue
            
            old_intensity = trace.intensity
            new_intensity = trace.apply_decay(hours_passed)
            
            if new_intensity < old_intensity:
                decayed_count += 1
            
            if trace.status == TraceStatus.FADED:
                faded_count += 1
        
        logger.info(f"Decay processed: {decayed_count} decayed, {faded_count} faded")
        
        return {
            "decayed_count": decayed_count,
            "faded_count": faded_count,
            "hours_passed": hours_passed
        }
    
    # =========================================================================
    # 舞台密度
    # =========================================================================
    def get_stage_density(self, stage_id: str, stage_tag: str) -> StageDensity:
        """获取舞台痕迹密度"""
        trace_ids = self._stage_traces.get(stage_id, [])
        
        density = StageDensity(
            stage_id=stage_id,
            stage_tag=stage_tag
        )
        
        type_dist: Dict[str, int] = {}
        
        for trace_id in trace_ids:
            trace = self._traces.get(trace_id)
            if not trace:
                continue
            
            density.total_traces += 1
            
            if trace.is_active():
                density.active_traces += 1
                density.total_intensity += trace.intensity
            
            # 类型分布
            t_type = trace.trace_type.value
            type_dist[t_type] = type_dist.get(t_type, 0) + 1
            
            # 最近活动
            if not density.last_trace_at or trace.created_at > density.last_trace_at:
                density.last_trace_at = trace.created_at
        
        density.type_distribution = type_dist
        
        # 计算密度分数
        if density.active_traces > 0:
            density.density_score = density.total_intensity / max(1, density.active_traces)
        
        # 统计最近发现
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for discovery in self._discoveries.values():
            trace = self._traces.get(discovery.trace_id)
            if trace and trace.stage_id == stage_id and discovery.discovered_at > cutoff:
                density.recent_discoveries += 1
        
        return density
    
    def get_density_map(self, theatre_id: str) -> Dict[str, float]:
        """获取剧场痕迹密度地图"""
        density_map = {}
        
        for stage_id in self._stage_traces.keys():
            # 获取该舞台的任意一个痕迹来获取stage_tag
            trace_ids = self._stage_traces.get(stage_id, [])
            if not trace_ids:
                continue
            
            trace = self._traces.get(trace_ids[0])
            if not trace or trace.theatre_id != theatre_id:
                continue
            
            density = self.get_stage_density(stage_id, trace.stage_tag)
            density_map[trace.stage_tag] = density.density_score
        
        return density_map
    
    # =========================================================================
    # 用户档案
    # =========================================================================
    def get_user_profile(self, user_id: str, theatre_id: str) -> UserTraceProfile:
        """获取用户痕迹档案"""
        profile = UserTraceProfile(
            user_id=user_id,
            theatre_id=theatre_id
        )
        
        # 统计留下的痕迹
        trace_ids = self._user_traces.get(user_id, [])
        stage_counts: Dict[str, int] = {}
        hour_counts: Dict[int, int] = {}
        
        for trace_id in trace_ids:
            trace = self._traces.get(trace_id)
            if not trace or trace.theatre_id != theatre_id:
                continue
            
            profile.traces_left += 1
            if trace.is_active():
                profile.traces_active += 1
            
            # 舞台统计
            stage_counts[trace.stage_tag] = stage_counts.get(trace.stage_tag, 0) + 1
            
            # 时段统计
            hour = trace.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # 最常访问的舞台
        sorted_stages = sorted(stage_counts.items(), key=lambda x: x[1], reverse=True)
        profile.frequent_stages = [s[0] for s in sorted_stages[:5]]
        profile.active_hours = hour_counts
        
        # 统计发现
        discovery_ids = self._user_discoveries.get(user_id, [])
        for discovery_id in discovery_ids:
            discovery = self._discoveries.get(discovery_id)
            if not discovery:
                continue
            
            trace = self._traces.get(discovery.trace_id)
            if not trace or trace.theatre_id != theatre_id:
                continue
            
            profile.traces_discovered += 1
            if discovery.converted_to_evidence:
                profile.evidence_converted += 1
        
        return profile
    
    # =========================================================================
    # 统计
    # =========================================================================
    def get_statistics(self, theatre_id: str) -> Dict:
        """获取痕迹系统统计"""
        traces = [t for t in self._traces.values() if t.theatre_id == theatre_id]
        
        status_counts = {status.value: 0 for status in TraceStatus}
        type_counts = {t.value: 0 for t in TraceType}
        
        total_intensity = 0.0
        total_discoveries = 0
        
        for trace in traces:
            status_counts[trace.status.value] += 1
            type_counts[trace.trace_type.value] += 1
            total_intensity += trace.intensity
            total_discoveries += trace.discovery_count
        
        return {
            "total_traces": len(traces),
            "by_status": status_counts,
            "by_type": type_counts,
            "total_intensity": total_intensity,
            "average_intensity": total_intensity / max(1, len(traces)),
            "total_discoveries": total_discoveries,
            "unique_discoverers": len(self._user_discoveries)
        }
