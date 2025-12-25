"""
TheatreOS Database Models
所有需要持久化的实体的SQLAlchemy模型定义
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, 
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================

class UserRoleEnum(enum.Enum):
    GUEST = "guest"
    PLAYER = "player"
    CREW_LEADER = "crew_leader"
    MODERATOR = "moderator"
    OPERATOR = "operator"
    ADMIN = "admin"


class EvidenceGradeEnum(enum.Enum):
    A = "A"
    B = "B"
    C = "C"


class EvidenceRarityEnum(enum.Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class RumorStatusEnum(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    VIRAL = "viral"
    DEBUNKED = "debunked"
    EXPIRED = "expired"


class TraceTypeEnum(enum.Enum):
    FOOTPRINT = "footprint"
    MARK = "mark"
    MESSAGE = "message"
    OFFERING = "offering"


class CrewTierEnum(enum.Enum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


class CrewRoleEnum(enum.Enum):
    LEADER = "leader"
    OFFICER = "officer"
    MEMBER = "member"


class CampaignTypeEnum(enum.Enum):
    BONUS_DROP = "bonus_drop"
    DOUBLE_XP = "double_xp"
    SPECIAL_EVENT = "special_event"
    LIMITED_OFFER = "limited_offer"


class ContentStatusEnum(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


# =============================================================================
# User & Auth Models
# =============================================================================

class UserModel(Base):
    """用户表"""
    __tablename__ = "users"
    
    user_id = Column(String(64), primary_key=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(SQLEnum(UserRoleEnum), default=UserRoleEnum.PLAYER)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    profile = Column(JSON, default=dict)
    
    # Relationships
    evidences = relationship("EvidenceModel", back_populates="owner")
    rumors = relationship("RumorModel", back_populates="author")
    traces = relationship("TraceModel", back_populates="creator")


class TokenBlacklistModel(Base):
    """Token黑名单表（用于撤销Token）"""
    __tablename__ = "token_blacklist"
    
    jti = Column(String(64), primary_key=True)  # Token唯一ID
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # Token原过期时间，用于清理


# =============================================================================
# Evidence Models
# =============================================================================

class EvidenceModel(Base):
    """证物表"""
    __tablename__ = "evidences"
    
    evidence_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    owner_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Evidence properties
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    grade = Column(SQLEnum(EvidenceGradeEnum), default=EvidenceGradeEnum.C)
    rarity = Column(SQLEnum(EvidenceRarityEnum), default=EvidenceRarityEnum.COMMON)
    evidence_type = Column(String(32), default="document")
    
    # Source tracking
    source_scene_id = Column(String(64), nullable=True)
    source_stage_id = Column(String(64), nullable=True)
    
    # Timestamps
    obtained_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Status
    is_verified = Column(Boolean, default=False)
    is_tradeable = Column(Boolean, default=True)
    is_consumed = Column(Boolean, default=False)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    owner = relationship("UserModel", back_populates="evidences")
    
    __table_args__ = (
        Index("ix_evidence_theatre_owner", "theatre_id", "owner_id"),
    )


class EvidenceTransferModel(Base):
    """证物转移记录表"""
    __tablename__ = "evidence_transfers"
    
    transfer_id = Column(String(64), primary_key=True)
    evidence_id = Column(String(64), ForeignKey("evidences.evidence_id"), nullable=False)
    from_user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    to_user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    transfer_type = Column(String(32), default="trade")  # trade, gift, system
    transferred_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)


# =============================================================================
# Rumor Models
# =============================================================================

class RumorModel(Base):
    """谣言表"""
    __tablename__ = "rumors"
    
    rumor_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    author_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    target_thread_id = Column(String(64), nullable=True)
    target_character_id = Column(String(64), nullable=True)
    
    # Status
    status = Column(SQLEnum(RumorStatusEnum), default=RumorStatusEnum.DRAFT)
    credibility_score = Column(Float, default=0.5)
    spread_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Moderation
    is_moderated = Column(Boolean, default=False)
    moderation_result = Column(String(32), nullable=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    author = relationship("UserModel", back_populates="rumors")
    spreads = relationship("RumorSpreadModel", back_populates="rumor")


class RumorSpreadModel(Base):
    """谣言传播记录表"""
    __tablename__ = "rumor_spreads"
    
    spread_id = Column(String(64), primary_key=True)
    rumor_id = Column(String(64), ForeignKey("rumors.rumor_id"), nullable=False)
    spreader_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    stage_id = Column(String(64), nullable=True)
    spread_at = Column(DateTime, default=datetime.utcnow)
    reach_count = Column(Integer, default=0)
    
    # Relationships
    rumor = relationship("RumorModel", back_populates="spreads")


# =============================================================================
# Trace Models
# =============================================================================

class TraceModel(Base):
    """痕迹表"""
    __tablename__ = "traces"
    
    trace_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    creator_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Location
    stage_id = Column(String(64), nullable=False, index=True)
    position_hint = Column(String(128), nullable=True)
    
    # Content
    trace_type = Column(SQLEnum(TraceTypeEnum), default=TraceTypeEnum.FOOTPRINT)
    content = Column(Text, nullable=True)
    
    # Visibility
    visibility = Column(String(32), default="public")  # public, crew, private
    discovery_difficulty = Column(Float, default=0.5)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Discovery tracking
    discovery_count = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Relationships
    creator = relationship("UserModel", back_populates="traces")
    discoveries = relationship("TraceDiscoveryModel", back_populates="trace")


class TraceDiscoveryModel(Base):
    """痕迹发现记录表"""
    __tablename__ = "trace_discoveries"
    
    discovery_id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), ForeignKey("traces.trace_id"), nullable=False)
    discoverer_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trace = relationship("TraceModel", back_populates="discoveries")


# =============================================================================
# Crew Models
# =============================================================================

class CrewModel(Base):
    """剧团表"""
    __tablename__ = "crews"
    
    crew_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    
    # Basic info
    name = Column(String(64), nullable=False)
    motto = Column(String(256), nullable=True)
    tier = Column(SQLEnum(CrewTierEnum), default=CrewTierEnum.TIER_1)
    
    # Stats
    reputation = Column(Integer, default=0)
    total_contribution = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Settings
    settings = Column(JSON, default=dict)
    
    # Relationships
    members = relationship("CrewMemberModel", back_populates="crew")
    actions = relationship("CrewActionModel", back_populates="crew")


class CrewMemberModel(Base):
    """剧团成员表"""
    __tablename__ = "crew_members"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    crew_id = Column(String(64), ForeignKey("crews.crew_id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    
    # Role
    role = Column(SQLEnum(CrewRoleEnum), default=CrewRoleEnum.MEMBER)
    
    # Stats
    contribution = Column(Integer, default=0)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    crew = relationship("CrewModel", back_populates="members")
    
    __table_args__ = (
        Index("ix_crew_member_unique", "crew_id", "user_id", unique=True),
    )


class CrewActionModel(Base):
    """剧团集体行动表"""
    __tablename__ = "crew_actions"
    
    action_id = Column(String(64), primary_key=True)
    crew_id = Column(String(64), ForeignKey("crews.crew_id"), nullable=False)
    
    # Action details
    action_type = Column(String(32), nullable=False)
    target_id = Column(String(64), nullable=True)
    
    # Status
    status = Column(String(32), default="pending")  # pending, in_progress, completed, failed
    required_participants = Column(Integer, default=1)
    current_participants = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Result
    result = Column(JSON, nullable=True)
    
    # Relationships
    crew = relationship("CrewModel", back_populates="actions")


class SharedResourceModel(Base):
    """共享资源表"""
    __tablename__ = "shared_resources"
    
    resource_id = Column(String(64), primary_key=True)
    crew_id = Column(String(64), ForeignKey("crews.crew_id"), nullable=False)
    contributor_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    
    # Resource details
    resource_type = Column(String(32), nullable=False)  # evidence, currency, item
    resource_ref_id = Column(String(64), nullable=True)  # Reference to actual resource
    quantity = Column(Integer, default=1)
    
    # Status
    is_claimed = Column(Boolean, default=False)
    claimed_by = Column(String(64), nullable=True)
    
    # Timestamps
    shared_at = Column(DateTime, default=datetime.utcnow)
    claimed_at = Column(DateTime, nullable=True)


# =============================================================================
# Analytics Models
# =============================================================================

class AnalyticsEventModel(Base):
    """分析事件表"""
    __tablename__ = "analytics_events"
    
    event_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    
    # Event details
    event_type = Column(String(64), nullable=False, index=True)
    event_data = Column(JSON, default=dict)
    
    # Context
    session_id = Column(String(64), nullable=True)
    device_type = Column(String(32), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_analytics_theatre_type_time", "theatre_id", "event_type", "created_at"),
    )


# =============================================================================
# LiveOps Models
# =============================================================================

class CampaignModel(Base):
    """运营活动表"""
    __tablename__ = "campaigns"
    
    campaign_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    
    # Campaign details
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignTypeEnum), nullable=False)
    
    # Configuration
    config = Column(JSON, default=dict)
    
    # Targeting
    target_segments = Column(JSON, default=list)  # List of user segments
    
    # Schedule
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metrics
    metrics = Column(JSON, default=dict)


class ABTestModel(Base):
    """A/B测试表"""
    __tablename__ = "ab_tests"
    
    test_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    
    # Test details
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # Variants
    variants = Column(JSON, nullable=False)  # List of variant configs
    traffic_split = Column(JSON, nullable=False)  # Traffic allocation
    
    # Schedule
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(32), default="draft")  # draft, running, paused, completed
    
    # Results
    results = Column(JSON, default=dict)


# =============================================================================
# Safety Models
# =============================================================================

class ContentReviewModel(Base):
    """内容审核表"""
    __tablename__ = "content_reviews"
    
    review_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    
    # Content reference
    content_type = Column(String(32), nullable=False)  # rumor, trace, evidence
    content_id = Column(String(64), nullable=False)
    content_text = Column(Text, nullable=True)
    
    # Submitter
    submitter_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    
    # Review status
    status = Column(SQLEnum(ContentStatusEnum), default=ContentStatusEnum.PENDING)
    
    # AI review
    ai_score = Column(Float, nullable=True)
    ai_flags = Column(JSON, default=list)
    
    # Human review
    reviewer_id = Column(String(64), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class ReportModel(Base):
    """举报表"""
    __tablename__ = "reports"
    
    report_id = Column(String(64), primary_key=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    
    # Reporter
    reporter_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    
    # Target
    target_type = Column(String(32), nullable=False)  # user, rumor, trace, crew
    target_id = Column(String(64), nullable=False)
    
    # Report details
    reason = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(32), default="pending")  # pending, investigating, resolved, dismissed
    resolution = Column(Text, nullable=True)
    
    # Timestamps
    reported_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


# =============================================================================
# Wallet Models
# =============================================================================

class WalletModel(Base):
    """钱包表"""
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    theatre_id = Column(String(64), nullable=False, index=True)
    
    # Balances
    shard_balance = Column(Float, default=100.0)  # 主货币
    echo_balance = Column(Float, default=0.0)     # 高级货币
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_wallet_user_theatre", "user_id", "theatre_id", unique=True),
    )


class WalletTransactionModel(Base):
    """钱包交易记录表"""
    __tablename__ = "wallet_transactions"
    
    transaction_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    theatre_id = Column(String(64), nullable=False)
    
    # Transaction details
    transaction_type = Column(String(32), nullable=False)  # stake, reward, transfer, purchase
    currency = Column(String(16), nullable=False)  # SHARD, ECHO
    amount = Column(Float, nullable=False)
    
    # Reference
    reference_type = Column(String(32), nullable=True)  # gate, trade, system
    reference_id = Column(String(64), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Notes
    notes = Column(Text, nullable=True)
