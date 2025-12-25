"""
TheatreOS Theme Pack Data Models
主题包数据模型定义

主题包是TheatreOS内容系统的核心，包含：
- 世界观设定（World Bible）
- 故事线注册表（Thread Registry）
- 拍子模板库（Beat Library）
- 门模板库（Gate Template Library）
- 证物类型库（Evidence Library）
- 角色设定（Character Bible）
- 救援拍子库（Rescue Beats）
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


# =============================================================================
# Enums
# =============================================================================

class BeatType(str, Enum):
    """拍子类型"""
    REVEAL = "REVEAL"           # 揭示
    INVESTIGATE = "INVESTIGATE" # 调查
    DISCOVERY = "DISCOVERY"     # 发现
    CHASE = "CHASE"             # 追逐
    DUEL = "DUEL"               # 对决
    TRADE = "TRADE"             # 交易
    RITUAL = "RITUAL"           # 仪式
    COUNCIL = "COUNCIL"         # 议会
    BROADCAST = "BROADCAST"     # 广播
    INTERROGATE = "INTERROGATE" # 审讯
    PATROL = "PATROL"           # 巡逻
    PORTAL = "PORTAL"           # 传送门
    HEAL = "HEAL"               # 治疗
    HEIST = "HEIST"             # 劫案
    TRIAL = "TRIAL"             # 审判
    FORGERY = "FORGERY"         # 伪造
    MISDIRECTION = "MISDIRECTION" # 误导
    SILENCE = "SILENCE"         # 静默
    AFTERMATH = "AFTERMATH"     # 余波
    SUMMON = "SUMMON"           # 召唤


class GateType(str, Enum):
    """门类型"""
    PUBLIC_VOTE = "public_vote"     # 民意门
    FATE_GATE = "fate_gate"         # 命运门
    MAJOR_GATE = "major_gate"       # 重大门
    COUNCIL_GATE = "council_gate"   # 议会门


class EvidenceTier(str, Enum):
    """证物等级"""
    A = "A"  # 高可信度
    B = "B"  # 中等可信度
    C = "C"  # 低可信度
    D = "D"  # 误导性


class EvidenceProvenance(str, Enum):
    """证物来源"""
    ONSITE = "onsite"   # 现场获取
    RUMOR = "rumor"     # 谣言传播
    TRADE = "trade"     # 交易获得
    REWARD = "reward"   # 奖励获得


class Forgeability(str, Enum):
    """可伪造性"""
    HARD = "hard"       # 难以伪造
    MEDIUM = "medium"   # 中等难度
    EASY = "easy"       # 容易伪造


# =============================================================================
# Data Classes - World Bible
# =============================================================================

@dataclass
class WorldVariable:
    """世界变量定义"""
    id: str
    name_cn: str
    description: str
    default_value: float = 0.5
    min_value: float = 0.0
    max_value: float = 1.0
    max_change_per_hour: float = 0.15
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name_cn": self.name_cn,
            "description": self.description,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "max_change_per_hour": self.max_change_per_hour
        }


@dataclass
class KeyObject:
    """关键物品定义"""
    object_id: str
    name: str
    description: str
    related_threads: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "description": self.description,
            "related_threads": self.related_threads
        }


@dataclass
class Faction:
    """阵营定义"""
    faction_id: str
    name: str
    style: str
    related_characters: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "faction_id": self.faction_id,
            "name": self.name,
            "style": self.style,
            "related_characters": self.related_characters
        }


# =============================================================================
# Data Classes - Characters
# =============================================================================

@dataclass
class Character:
    """角色定义"""
    character_id: str
    name: str
    name_cn: str
    faction: str
    role: str
    public_goal: str
    hidden_secret: str
    voice_style: str
    visual_style: str
    forbidden_content: List[str] = field(default_factory=list)
    allowed_beat_types: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "name_cn": self.name_cn,
            "faction": self.faction,
            "role": self.role,
            "public_goal": self.public_goal,
            "hidden_secret": self.hidden_secret,
            "voice_style": self.voice_style,
            "visual_style": self.visual_style,
            "forbidden_content": self.forbidden_content,
            "allowed_beat_types": self.allowed_beat_types
        }


# =============================================================================
# Data Classes - Threads
# =============================================================================

@dataclass
class ThreadPhase:
    """故事线阶段"""
    phase: str
    name_cn: str
    goal: str
    allowed_beat_types: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "phase": self.phase,
            "name_cn": self.name_cn,
            "goal": self.goal,
            "allowed_beat_types": self.allowed_beat_types
        }


@dataclass
class Thread:
    """故事线定义"""
    thread_id: str
    name: str
    logline: str
    key_objects: List[str] = field(default_factory=list)
    key_stages: List[str] = field(default_factory=list)
    world_vars: List[str] = field(default_factory=list)
    phases: List[ThreadPhase] = field(default_factory=list)
    crosslinks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "thread_id": self.thread_id,
            "name": self.name,
            "logline": self.logline,
            "key_objects": self.key_objects,
            "key_stages": self.key_stages,
            "world_vars": self.world_vars,
            "phases": [p.to_dict() for p in self.phases],
            "crosslinks": self.crosslinks
        }


# =============================================================================
# Data Classes - Beats
# =============================================================================

@dataclass
class BeatPreconditions:
    """拍子前置条件"""
    thread_phase_in: List[str] = field(default_factory=list)
    world_conditions: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "thread_phase_in": self.thread_phase_in,
            "world_conditions": self.world_conditions
        }


@dataclass
class BeatSlots:
    """拍子槽位配置"""
    stage_tag_any: List[str] = field(default_factory=list)
    camera_style_any: List[str] = field(default_factory=list)
    mood_any: List[str] = field(default_factory=list)
    prop_any: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "stage_tag_any": self.stage_tag_any,
            "camera_style_any": self.camera_style_any,
            "mood_any": self.mood_any,
            "prop_any": self.prop_any
        }


@dataclass
class BeatEffects:
    """拍子效果"""
    thread_progress_add: int = 0
    world_var_changes: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "thread_progress_add": self.thread_progress_add,
            "world_var_changes": self.world_var_changes
        }


@dataclass
class EvidenceOutput:
    """证物产出配置"""
    evidence_type: str
    tier: str
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "evidence_type": self.evidence_type,
            "tier": self.tier,
            "tags": self.tags
        }


@dataclass
class BeatTemplate:
    """拍子模板"""
    beat_id: str
    beat_type: str
    thread_id: str
    cast_roles: List[str] = field(default_factory=list)
    preconditions: BeatPreconditions = field(default_factory=BeatPreconditions)
    slots: BeatSlots = field(default_factory=BeatSlots)
    effects: BeatEffects = field(default_factory=BeatEffects)
    evidence_outputs: List[EvidenceOutput] = field(default_factory=list)
    optional_gate: Optional[Dict] = None
    fallbacks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "beat_id": self.beat_id,
            "beat_type": self.beat_type,
            "thread_id": self.thread_id,
            "cast_roles": self.cast_roles,
            "preconditions": self.preconditions.to_dict(),
            "slots": self.slots.to_dict(),
            "effects": self.effects.to_dict(),
            "evidence_outputs": [e.to_dict() for e in self.evidence_outputs],
            "optional_gate": self.optional_gate,
            "fallbacks": self.fallbacks
        }


# =============================================================================
# Data Classes - Gates
# =============================================================================

@dataclass
class GateOption:
    """门选项"""
    option_id: str
    label: str
    
    def to_dict(self) -> Dict:
        return {
            "option_id": self.option_id,
            "label": self.label
        }


@dataclass
class GateStake:
    """门下注配置"""
    currency: str = "ticket"
    weight_rule: str = "sqrt"
    cap_by_cred: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "currency": self.currency,
            "weight_rule": self.weight_rule,
            "cap_by_cred": self.cap_by_cred
        }


@dataclass
class GateTemplate:
    """门模板"""
    gate_id: str
    gate_type: str
    title: str
    tags: List[str] = field(default_factory=list)
    options: List[GateOption] = field(default_factory=list)
    stake: GateStake = field(default_factory=GateStake)
    world_factors: List[str] = field(default_factory=list)
    resolve_algorithm: str = "public_max_weight"
    consequences_win: List[str] = field(default_factory=list)
    consequences_lose: List[str] = field(default_factory=list)
    explain_card_title: str = ""
    explain_card_bullets: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "title": self.title,
            "tags": self.tags,
            "options": [o.to_dict() for o in self.options],
            "stake": self.stake.to_dict(),
            "world_factors": self.world_factors,
            "resolve_algorithm": self.resolve_algorithm,
            "consequences_win": self.consequences_win,
            "consequences_lose": self.consequences_lose,
            "explain_card_title": self.explain_card_title,
            "explain_card_bullets": self.explain_card_bullets
        }


# =============================================================================
# Data Classes - Evidence
# =============================================================================

@dataclass
class EvidenceType:
    """证物类型定义"""
    evidence_type_id: str
    name: str
    category: str
    description: str
    default_tier: str = "B"
    provenance_default: str = "onsite"
    used_for: List[str] = field(default_factory=list)
    forgeability: str = "medium"
    expiry: str = "48h"
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "evidence_type_id": self.evidence_type_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "default_tier": self.default_tier,
            "provenance_default": self.provenance_default,
            "used_for": self.used_for,
            "forgeability": self.forgeability,
            "expiry": self.expiry,
            "notes": self.notes
        }


# =============================================================================
# Data Classes - Theme Pack
# =============================================================================

@dataclass
class ThemePackMetadata:
    """主题包元数据"""
    pack_id: str
    name: str
    version: str
    description: str
    season_id: str
    city: str = "shanghai"
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "pack_id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "season_id": self.season_id,
            "city": self.city,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class ThemePack:
    """主题包完整定义"""
    metadata: ThemePackMetadata
    world_variables: List[WorldVariable] = field(default_factory=list)
    key_objects: List[KeyObject] = field(default_factory=list)
    factions: List[Faction] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
    threads: List[Thread] = field(default_factory=list)
    beat_templates: List[BeatTemplate] = field(default_factory=list)
    gate_templates: List[GateTemplate] = field(default_factory=list)
    evidence_types: List[EvidenceType] = field(default_factory=list)
    rescue_beats: List[BeatTemplate] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "metadata": self.metadata.to_dict(),
            "world_variables": [w.to_dict() for w in self.world_variables],
            "key_objects": [o.to_dict() for o in self.key_objects],
            "factions": [f.to_dict() for f in self.factions],
            "characters": [c.to_dict() for c in self.characters],
            "threads": [t.to_dict() for t in self.threads],
            "beat_templates": [b.to_dict() for b in self.beat_templates],
            "gate_templates": [g.to_dict() for g in self.gate_templates],
            "evidence_types": [e.to_dict() for e in self.evidence_types],
            "rescue_beats": [r.to_dict() for r in self.rescue_beats]
        }
    
    # 便捷查询方法
    def get_character(self, character_id: str) -> Optional[Character]:
        for c in self.characters:
            if c.character_id == character_id:
                return c
        return None
    
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        for t in self.threads:
            if t.thread_id == thread_id:
                return t
        return None
    
    def get_beat_template(self, beat_id: str) -> Optional[BeatTemplate]:
        for b in self.beat_templates:
            if b.beat_id == beat_id:
                return b
        return None
    
    def get_gate_template(self, gate_id: str) -> Optional[GateTemplate]:
        for g in self.gate_templates:
            if g.gate_id == gate_id:
                return g
        return None
    
    def get_evidence_type(self, evidence_type_id: str) -> Optional[EvidenceType]:
        for e in self.evidence_types:
            if e.evidence_type_id == evidence_type_id:
                return e
        return None
    
    def get_world_variable(self, var_id: str) -> Optional[WorldVariable]:
        for w in self.world_variables:
            if w.id == var_id:
                return w
        return None
    
    def get_characters_by_faction(self, faction_id: str) -> List[Character]:
        return [c for c in self.characters if c.faction == faction_id]
    
    def get_beats_by_thread(self, thread_id: str) -> List[BeatTemplate]:
        return [b for b in self.beat_templates if b.thread_id == thread_id]
    
    def get_beats_by_type(self, beat_type: str) -> List[BeatTemplate]:
        return [b for b in self.beat_templates if b.beat_type == beat_type]
