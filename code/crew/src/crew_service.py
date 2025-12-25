"""
TheatreOS Crew System
剧团系统 - 支持玩家组建小队，进行团队协作、资源共享和集体决策

核心概念:
- 剧团 (Crew) = 玩家组成的小队
- 剧团有等级、声望和专属能力
- 剧团成员可以共享证物、谣言和痕迹
- 剧团可以发起集体行动

剧团角色:
- LEADER: 团长 - 最高权限
- OFFICER: 干部 - 管理权限
- MEMBER: 成员 - 基础权限
- RECRUIT: 新人 - 受限权限
"""
import logging
import uuid
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
class CrewRole(str, Enum):
    """剧团角色"""
    LEADER = "LEADER"         # 团长
    OFFICER = "OFFICER"       # 干部
    MEMBER = "MEMBER"         # 成员
    RECRUIT = "RECRUIT"       # 新人


class CrewStatus(str, Enum):
    """剧团状态"""
    ACTIVE = "ACTIVE"         # 活跃
    INACTIVE = "INACTIVE"     # 不活跃
    DISBANDED = "DISBANDED"   # 已解散
    SUSPENDED = "SUSPENDED"   # 被暂停


class MemberStatus(str, Enum):
    """成员状态"""
    ACTIVE = "ACTIVE"         # 活跃
    INACTIVE = "INACTIVE"     # 不活跃
    PENDING = "PENDING"       # 待审批
    BANNED = "BANNED"         # 被禁止


class ActionType(str, Enum):
    """集体行动类型"""
    VOTE = "VOTE"             # 集体投票
    INVESTIGATE = "INVESTIGATE"  # 集体调查
    SHARE = "SHARE"           # 资源共享
    RAID = "RAID"             # 突袭行动
    DEFEND = "DEFEND"         # 防御行动


class ActionStatus(str, Enum):
    """行动状态"""
    PROPOSED = "PROPOSED"     # 已提议
    VOTING = "VOTING"         # 投票中
    APPROVED = "APPROVED"     # 已通过
    REJECTED = "REJECTED"     # 已否决
    EXECUTING = "EXECUTING"   # 执行中
    COMPLETED = "COMPLETED"   # 已完成
    FAILED = "FAILED"         # 已失败
    CANCELLED = "CANCELLED"   # 已取消


class ShareType(str, Enum):
    """共享类型"""
    EVIDENCE = "EVIDENCE"     # 证物共享
    RUMOR = "RUMOR"           # 谣言共享
    TRACE = "TRACE"           # 痕迹共享
    CURRENCY = "CURRENCY"     # 货币共享


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class CrewTier:
    """剧团等级定义"""
    tier: int
    name: str
    max_members: int
    required_reputation: int
    perks: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "tier": self.tier,
            "name": self.name,
            "max_members": self.max_members,
            "required_reputation": self.required_reputation,
            "perks": self.perks
        }


@dataclass
class Crew:
    """剧团"""
    crew_id: str
    theatre_id: str
    name: str
    tag: str  # 3-5字符的简称
    
    # 基本信息
    description: str = ""
    motto: str = ""
    icon_url: Optional[str] = None
    
    # 状态
    status: CrewStatus = CrewStatus.ACTIVE
    tier: int = 1
    
    # 统计
    reputation: int = 0
    total_contribution: int = 0
    member_count: int = 0
    
    # 设置
    is_public: bool = True  # 是否公开招募
    auto_approve: bool = False  # 是否自动批准申请
    min_level_required: int = 1  # 最低等级要求
    
    # 时间
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # 元数据
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "crew_id": self.crew_id,
            "theatre_id": self.theatre_id,
            "name": self.name,
            "tag": self.tag,
            "description": self.description,
            "motto": self.motto,
            "icon_url": self.icon_url,
            "status": self.status.value,
            "tier": self.tier,
            "reputation": self.reputation,
            "total_contribution": self.total_contribution,
            "member_count": self.member_count,
            "is_public": self.is_public,
            "auto_approve": self.auto_approve,
            "min_level_required": self.min_level_required,
            "created_at": self.created_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat()
        }


@dataclass
class CrewMember:
    """剧团成员"""
    member_id: str
    crew_id: str
    user_id: str
    
    # 角色和状态
    role: CrewRole = CrewRole.RECRUIT
    status: MemberStatus = MemberStatus.ACTIVE
    
    # 贡献
    contribution: int = 0
    actions_participated: int = 0
    shares_made: int = 0
    
    # 时间
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    promoted_at: Optional[datetime] = None
    
    # 备注
    nickname: Optional[str] = None
    note: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "member_id": self.member_id,
            "crew_id": self.crew_id,
            "user_id": self.user_id,
            "role": self.role.value,
            "status": self.status.value,
            "contribution": self.contribution,
            "actions_participated": self.actions_participated,
            "shares_made": self.shares_made,
            "joined_at": self.joined_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat(),
            "nickname": self.nickname
        }
    
    def has_permission(self, required_role: CrewRole) -> bool:
        """检查是否有权限"""
        role_hierarchy = {
            CrewRole.LEADER: 4,
            CrewRole.OFFICER: 3,
            CrewRole.MEMBER: 2,
            CrewRole.RECRUIT: 1
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)


@dataclass
class CrewAction:
    """剧团集体行动"""
    action_id: str
    crew_id: str
    theatre_id: str
    
    # 行动信息
    action_type: ActionType
    title: str
    description: str
    
    # 目标
    target_stage_id: Optional[str] = None
    target_gate_id: Optional[str] = None
    target_user_id: Optional[str] = None
    
    # 状态
    status: ActionStatus = ActionStatus.PROPOSED
    
    # 发起者
    proposer_id: str = ""
    
    # 投票
    votes_required: int = 3
    votes_for: int = 0
    votes_against: int = 0
    voters: List[str] = field(default_factory=list)
    
    # 参与者
    participants: List[str] = field(default_factory=list)
    min_participants: int = 1
    max_participants: int = 10
    
    # 资源
    cost_per_participant: int = 0
    total_cost: int = 0
    reward_pool: int = 0
    
    # 结果
    success_rate: float = 0.0
    outcome: Optional[str] = None
    rewards_distributed: Dict[str, int] = field(default_factory=dict)
    
    # 时间
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    voting_deadline: Optional[datetime] = None
    execution_time: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "crew_id": self.crew_id,
            "theatre_id": self.theatre_id,
            "action_type": self.action_type.value,
            "title": self.title,
            "description": self.description,
            "target_stage_id": self.target_stage_id,
            "target_gate_id": self.target_gate_id,
            "status": self.status.value,
            "proposer_id": self.proposer_id,
            "votes_required": self.votes_required,
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "participant_count": len(self.participants),
            "min_participants": self.min_participants,
            "max_participants": self.max_participants,
            "cost_per_participant": self.cost_per_participant,
            "success_rate": self.success_rate,
            "outcome": self.outcome,
            "created_at": self.created_at.isoformat(),
            "voting_deadline": self.voting_deadline.isoformat() if self.voting_deadline else None,
            "execution_time": self.execution_time.isoformat() if self.execution_time else None
        }


@dataclass
class CrewShare:
    """剧团资源共享记录"""
    share_id: str
    crew_id: str
    sharer_id: str
    
    # 共享内容
    share_type: ShareType
    resource_id: str  # 证物/谣言/痕迹的ID
    
    # 接收者
    recipient_ids: List[str] = field(default_factory=list)  # 空表示全团共享
    
    # 状态
    is_claimed: bool = False
    claimed_by: List[str] = field(default_factory=list)
    
    # 时间
    shared_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    # 备注
    message: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "share_id": self.share_id,
            "crew_id": self.crew_id,
            "sharer_id": self.sharer_id,
            "share_type": self.share_type.value,
            "resource_id": self.resource_id,
            "recipient_ids": self.recipient_ids,
            "is_claimed": self.is_claimed,
            "claimed_count": len(self.claimed_by),
            "shared_at": self.shared_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "message": self.message
        }


@dataclass
class JoinApplication:
    """入团申请"""
    application_id: str
    crew_id: str
    applicant_id: str
    
    # 申请信息
    message: str = ""
    
    # 状态
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, WITHDRAWN
    
    # 处理
    processed_by: Optional[str] = None
    processed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # 时间
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            "application_id": self.application_id,
            "crew_id": self.crew_id,
            "applicant_id": self.applicant_id,
            "message": self.message,
            "status": self.status,
            "processed_by": self.processed_by,
            "applied_at": self.applied_at.isoformat()
        }


# =============================================================================
# Crew Tier Registry
# =============================================================================
class CrewTierRegistry:
    """剧团等级注册表"""
    
    def __init__(self):
        self._tiers: Dict[int, CrewTier] = {}
        self._load_default_tiers()
    
    def _load_default_tiers(self):
        """加载默认等级"""
        default_tiers = [
            CrewTier(
                tier=1,
                name="新生剧团",
                max_members=5,
                required_reputation=0,
                perks=["基础共享"]
            ),
            CrewTier(
                tier=2,
                name="成长剧团",
                max_members=10,
                required_reputation=100,
                perks=["基础共享", "集体投票"]
            ),
            CrewTier(
                tier=3,
                name="成熟剧团",
                max_members=15,
                required_reputation=500,
                perks=["基础共享", "集体投票", "集体调查"]
            ),
            CrewTier(
                tier=4,
                name="精英剧团",
                max_members=20,
                required_reputation=1500,
                perks=["基础共享", "集体投票", "集体调查", "突袭行动"]
            ),
            CrewTier(
                tier=5,
                name="传奇剧团",
                max_members=30,
                required_reputation=5000,
                perks=["基础共享", "集体投票", "集体调查", "突袭行动", "防御行动", "专属徽章"]
            )
        ]
        
        for tier in default_tiers:
            self._tiers[tier.tier] = tier
    
    def get_tier(self, tier: int) -> Optional[CrewTier]:
        return self._tiers.get(tier)
    
    def get_tier_for_reputation(self, reputation: int) -> CrewTier:
        """根据声望获取等级"""
        result = self._tiers[1]
        for tier in sorted(self._tiers.values(), key=lambda t: t.tier):
            if reputation >= tier.required_reputation:
                result = tier
        return result
    
    def list_tiers(self) -> List[CrewTier]:
        return list(self._tiers.values())


# =============================================================================
# Crew Service
# =============================================================================
class CrewService:
    """剧团系统服务"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.tier_registry = CrewTierRegistry()
        
        # 内存存储
        self._crews: Dict[str, Crew] = {}
        self._members: Dict[str, CrewMember] = {}
        self._actions: Dict[str, CrewAction] = {}
        self._shares: Dict[str, CrewShare] = {}
        self._applications: Dict[str, JoinApplication] = {}
        
        # 索引
        self._user_crews: Dict[str, str] = {}  # user_id -> crew_id
        self._crew_members: Dict[str, List[str]] = {}  # crew_id -> [member_ids]
        self._crew_actions: Dict[str, List[str]] = {}  # crew_id -> [action_ids]
        self._crew_shares: Dict[str, List[str]] = {}  # crew_id -> [share_ids]
    
    # =========================================================================
    # 剧团管理
    # =========================================================================
    def create_crew(
        self,
        theatre_id: str,
        creator_id: str,
        name: str,
        tag: str,
        description: str = "",
        motto: str = "",
        is_public: bool = True
    ) -> Tuple[Crew, CrewMember]:
        """
        创建剧团
        
        Args:
            theatre_id: 剧场ID
            creator_id: 创建者ID
            name: 剧团名称
            tag: 剧团简称 (3-5字符)
            description: 描述
            motto: 口号
            is_public: 是否公开招募
        
        Returns:
            (剧团, 创建者的成员记录)
        """
        # 检查用户是否已有剧团
        if creator_id in self._user_crews:
            raise ValueError("User already in a crew")
        
        # 验证tag
        if len(tag) < 3 or len(tag) > 5:
            raise ValueError("Tag must be 3-5 characters")
        
        # 检查tag是否已存在
        for crew in self._crews.values():
            if crew.tag.lower() == tag.lower() and crew.theatre_id == theatre_id:
                raise ValueError("Tag already exists")
        
        crew = Crew(
            crew_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            name=name,
            tag=tag.upper(),
            description=description,
            motto=motto,
            is_public=is_public,
            member_count=1
        )
        
        # 创建者成为团长
        member = CrewMember(
            member_id=str(uuid.uuid4()),
            crew_id=crew.crew_id,
            user_id=creator_id,
            role=CrewRole.LEADER,
            status=MemberStatus.ACTIVE
        )
        
        # 存储
        self._crews[crew.crew_id] = crew
        self._members[member.member_id] = member
        self._user_crews[creator_id] = crew.crew_id
        self._crew_members[crew.crew_id] = [member.member_id]
        
        logger.info(f"Crew created: {crew.name} [{crew.tag}] by {creator_id}")
        
        return crew, member
    
    def get_crew(self, crew_id: str) -> Optional[Crew]:
        """获取剧团"""
        return self._crews.get(crew_id)
    
    def get_crew_by_tag(self, theatre_id: str, tag: str) -> Optional[Crew]:
        """通过tag获取剧团"""
        for crew in self._crews.values():
            if crew.tag.lower() == tag.lower() and crew.theatre_id == theatre_id:
                return crew
        return None
    
    def update_crew(
        self,
        crew_id: str,
        operator_id: str,
        **updates
    ) -> Crew:
        """更新剧团信息"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        # 检查权限
        member = self._get_member_by_user(crew_id, operator_id)
        if not member or not member.has_permission(CrewRole.OFFICER):
            raise ValueError("No permission to update crew")
        
        # 允许更新的字段
        allowed_fields = ["name", "description", "motto", "icon_url", "is_public", "auto_approve", "min_level_required"]
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(crew, key, value)
        
        return crew
    
    def disband_crew(self, crew_id: str, operator_id: str) -> bool:
        """解散剧团"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        # 只有团长可以解散
        member = self._get_member_by_user(crew_id, operator_id)
        if not member or member.role != CrewRole.LEADER:
            raise ValueError("Only leader can disband crew")
        
        # 更新状态
        crew.status = CrewStatus.DISBANDED
        
        # 移除所有成员
        member_ids = self._crew_members.get(crew_id, [])
        for member_id in member_ids:
            m = self._members.get(member_id)
            if m:
                del self._user_crews[m.user_id]
        
        logger.info(f"Crew disbanded: {crew.name}")
        
        return True
    
    def list_crews(
        self,
        theatre_id: str,
        public_only: bool = True,
        limit: int = 20
    ) -> List[Crew]:
        """列出剧团"""
        crews = []
        for crew in self._crews.values():
            if crew.theatre_id != theatre_id:
                continue
            if crew.status != CrewStatus.ACTIVE:
                continue
            if public_only and not crew.is_public:
                continue
            crews.append(crew)
        
        # 按声望排序
        crews.sort(key=lambda c: c.reputation, reverse=True)
        
        return crews[:limit]
    
    # =========================================================================
    # 成员管理
    # =========================================================================
    def apply_to_join(
        self,
        crew_id: str,
        applicant_id: str,
        message: str = ""
    ) -> JoinApplication:
        """申请加入剧团"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        if crew.status != CrewStatus.ACTIVE:
            raise ValueError("Crew is not active")
        
        if not crew.is_public:
            raise ValueError("Crew is not accepting applications")
        
        # 检查是否已有剧团
        if applicant_id in self._user_crews:
            raise ValueError("Already in a crew")
        
        # 检查是否已有待处理申请
        for app in self._applications.values():
            if app.crew_id == crew_id and app.applicant_id == applicant_id and app.status == "PENDING":
                raise ValueError("Already has pending application")
        
        application = JoinApplication(
            application_id=str(uuid.uuid4()),
            crew_id=crew_id,
            applicant_id=applicant_id,
            message=message
        )
        
        self._applications[application.application_id] = application
        
        # 如果自动批准
        if crew.auto_approve:
            return self.process_application(application.application_id, applicant_id, True)
        
        return application
    
    def process_application(
        self,
        application_id: str,
        processor_id: str,
        approve: bool,
        rejection_reason: str = ""
    ) -> JoinApplication:
        """处理入团申请"""
        application = self._applications.get(application_id)
        if not application:
            raise ValueError("Application not found")
        
        if application.status != "PENDING":
            raise ValueError("Application already processed")
        
        crew = self._crews.get(application.crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        # 检查权限（团长或干部可以处理，或者是自动批准的情况）
        if processor_id != application.applicant_id:  # 不是自动批准
            member = self._get_member_by_user(application.crew_id, processor_id)
            if not member or not member.has_permission(CrewRole.OFFICER):
                raise ValueError("No permission to process application")
        
        if approve:
            # 检查人数上限
            tier = self.tier_registry.get_tier(crew.tier)
            if tier and crew.member_count >= tier.max_members:
                raise ValueError("Crew is full")
            
            # 创建成员
            new_member = CrewMember(
                member_id=str(uuid.uuid4()),
                crew_id=application.crew_id,
                user_id=application.applicant_id,
                role=CrewRole.RECRUIT,
                status=MemberStatus.ACTIVE
            )
            
            self._members[new_member.member_id] = new_member
            self._user_crews[application.applicant_id] = application.crew_id
            
            if application.crew_id not in self._crew_members:
                self._crew_members[application.crew_id] = []
            self._crew_members[application.crew_id].append(new_member.member_id)
            
            crew.member_count += 1
            
            application.status = "APPROVED"
        else:
            application.status = "REJECTED"
            application.rejection_reason = rejection_reason
        
        application.processed_by = processor_id
        application.processed_at = datetime.now(timezone.utc)
        
        return application
    
    def invite_member(
        self,
        crew_id: str,
        inviter_id: str,
        invitee_id: str
    ) -> CrewMember:
        """邀请成员（直接加入，无需申请）"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        # 检查权限
        inviter = self._get_member_by_user(crew_id, inviter_id)
        if not inviter or not inviter.has_permission(CrewRole.OFFICER):
            raise ValueError("No permission to invite")
        
        # 检查被邀请者是否已有剧团
        if invitee_id in self._user_crews:
            raise ValueError("Invitee already in a crew")
        
        # 检查人数上限
        tier = self.tier_registry.get_tier(crew.tier)
        if tier and crew.member_count >= tier.max_members:
            raise ValueError("Crew is full")
        
        new_member = CrewMember(
            member_id=str(uuid.uuid4()),
            crew_id=crew_id,
            user_id=invitee_id,
            role=CrewRole.RECRUIT,
            status=MemberStatus.ACTIVE
        )
        
        self._members[new_member.member_id] = new_member
        self._user_crews[invitee_id] = crew_id
        
        if crew_id not in self._crew_members:
            self._crew_members[crew_id] = []
        self._crew_members[crew_id].append(new_member.member_id)
        
        crew.member_count += 1
        
        return new_member
    
    def leave_crew(self, crew_id: str, user_id: str) -> bool:
        """离开剧团"""
        member = self._get_member_by_user(crew_id, user_id)
        if not member:
            raise ValueError("Not a member of this crew")
        
        # 团长不能直接离开，必须先转让或解散
        if member.role == CrewRole.LEADER:
            raise ValueError("Leader cannot leave. Transfer leadership or disband first.")
        
        # 移除成员
        del self._members[member.member_id]
        del self._user_crews[user_id]
        
        if crew_id in self._crew_members:
            self._crew_members[crew_id].remove(member.member_id)
        
        crew = self._crews.get(crew_id)
        if crew:
            crew.member_count -= 1
        
        return True
    
    def kick_member(
        self,
        crew_id: str,
        operator_id: str,
        target_user_id: str,
        reason: str = ""
    ) -> bool:
        """踢出成员"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        operator = self._get_member_by_user(crew_id, operator_id)
        target = self._get_member_by_user(crew_id, target_user_id)
        
        if not operator or not target:
            raise ValueError("Member not found")
        
        # 检查权限
        if not operator.has_permission(CrewRole.OFFICER):
            raise ValueError("No permission to kick")
        
        # 不能踢比自己等级高或相同的人
        if target.has_permission(operator.role):
            raise ValueError("Cannot kick member with same or higher role")
        
        # 移除成员
        del self._members[target.member_id]
        del self._user_crews[target_user_id]
        
        if crew_id in self._crew_members:
            self._crew_members[crew_id].remove(target.member_id)
        
        crew.member_count -= 1
        
        logger.info(f"Member {target_user_id} kicked from {crew.name} by {operator_id}")
        
        return True
    
    def promote_member(
        self,
        crew_id: str,
        operator_id: str,
        target_user_id: str,
        new_role: str
    ) -> CrewMember:
        """晋升成员"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        operator = self._get_member_by_user(crew_id, operator_id)
        target = self._get_member_by_user(crew_id, target_user_id)
        
        if not operator or not target:
            raise ValueError("Member not found")
        
        new_role_enum = CrewRole(new_role)
        
        # 只有团长可以晋升为干部或转让团长
        if new_role_enum in [CrewRole.OFFICER, CrewRole.LEADER]:
            if operator.role != CrewRole.LEADER:
                raise ValueError("Only leader can promote to officer or leader")
        
        # 转让团长
        if new_role_enum == CrewRole.LEADER:
            operator.role = CrewRole.OFFICER
            operator.promoted_at = datetime.now(timezone.utc)
        
        target.role = new_role_enum
        target.promoted_at = datetime.now(timezone.utc)
        
        return target
    
    def get_members(self, crew_id: str) -> List[CrewMember]:
        """获取剧团成员列表"""
        member_ids = self._crew_members.get(crew_id, [])
        members = []
        
        for member_id in member_ids:
            member = self._members.get(member_id)
            if member and member.status == MemberStatus.ACTIVE:
                members.append(member)
        
        # 按角色排序
        role_order = {CrewRole.LEADER: 0, CrewRole.OFFICER: 1, CrewRole.MEMBER: 2, CrewRole.RECRUIT: 3}
        members.sort(key=lambda m: role_order.get(m.role, 99))
        
        return members
    
    def get_user_crew(self, user_id: str) -> Optional[Tuple[Crew, CrewMember]]:
        """获取用户所在的剧团"""
        crew_id = self._user_crews.get(user_id)
        if not crew_id:
            return None
        
        crew = self._crews.get(crew_id)
        member = self._get_member_by_user(crew_id, user_id)
        
        if crew and member:
            return crew, member
        return None
    
    def _get_member_by_user(self, crew_id: str, user_id: str) -> Optional[CrewMember]:
        """通过用户ID获取成员"""
        member_ids = self._crew_members.get(crew_id, [])
        for member_id in member_ids:
            member = self._members.get(member_id)
            if member and member.user_id == user_id:
                return member
        return None
    
    # =========================================================================
    # 集体行动
    # =========================================================================
    def propose_action(
        self,
        crew_id: str,
        proposer_id: str,
        action_type: str,
        title: str,
        description: str,
        target_stage_id: Optional[str] = None,
        target_gate_id: Optional[str] = None,
        execution_time: Optional[datetime] = None,
        cost_per_participant: int = 0
    ) -> CrewAction:
        """发起集体行动"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        proposer = self._get_member_by_user(crew_id, proposer_id)
        if not proposer:
            raise ValueError("Not a member of this crew")
        
        # 检查权限
        if not proposer.has_permission(CrewRole.MEMBER):
            raise ValueError("Recruits cannot propose actions")
        
        action_type_enum = ActionType(action_type)
        
        # 检查剧团等级是否支持此行动
        tier = self.tier_registry.get_tier(crew.tier)
        action_perk_map = {
            ActionType.VOTE: "集体投票",
            ActionType.INVESTIGATE: "集体调查",
            ActionType.SHARE: "基础共享",
            ActionType.RAID: "突袭行动",
            ActionType.DEFEND: "防御行动"
        }
        required_perk = action_perk_map.get(action_type_enum)
        if tier and required_perk and required_perk not in tier.perks:
            raise ValueError(f"Crew tier does not support {action_type}")
        
        # 计算投票截止时间
        voting_deadline = datetime.now(timezone.utc) + timedelta(hours=24)
        
        action = CrewAction(
            action_id=str(uuid.uuid4()),
            crew_id=crew_id,
            theatre_id=crew.theatre_id,
            action_type=action_type_enum,
            title=title,
            description=description,
            target_stage_id=target_stage_id,
            target_gate_id=target_gate_id,
            status=ActionStatus.VOTING,
            proposer_id=proposer_id,
            votes_required=max(3, crew.member_count // 2),
            cost_per_participant=cost_per_participant,
            voting_deadline=voting_deadline,
            execution_time=execution_time or (datetime.now(timezone.utc) + timedelta(hours=48))
        )
        
        # 发起者自动投赞成票
        action.votes_for = 1
        action.voters.append(proposer_id)
        
        self._actions[action.action_id] = action
        
        if crew_id not in self._crew_actions:
            self._crew_actions[crew_id] = []
        self._crew_actions[crew_id].append(action.action_id)
        
        return action
    
    def vote_on_action(
        self,
        action_id: str,
        voter_id: str,
        vote_for: bool
    ) -> CrewAction:
        """对行动投票"""
        action = self._actions.get(action_id)
        if not action:
            raise ValueError("Action not found")
        
        if action.status != ActionStatus.VOTING:
            raise ValueError("Action is not in voting phase")
        
        if datetime.now(timezone.utc) > action.voting_deadline:
            raise ValueError("Voting deadline passed")
        
        voter = self._get_member_by_user(action.crew_id, voter_id)
        if not voter:
            raise ValueError("Not a member of this crew")
        
        if voter_id in action.voters:
            raise ValueError("Already voted")
        
        action.voters.append(voter_id)
        if vote_for:
            action.votes_for += 1
        else:
            action.votes_against += 1
        
        # 检查是否达到通过条件
        if action.votes_for >= action.votes_required:
            action.status = ActionStatus.APPROVED
        
        # 检查是否被否决
        crew = self._crews.get(action.crew_id)
        if crew and action.votes_against > crew.member_count - action.votes_required:
            action.status = ActionStatus.REJECTED
        
        return action
    
    def join_action(
        self,
        action_id: str,
        participant_id: str
    ) -> CrewAction:
        """参与行动"""
        action = self._actions.get(action_id)
        if not action:
            raise ValueError("Action not found")
        
        if action.status != ActionStatus.APPROVED:
            raise ValueError("Action is not approved")
        
        participant = self._get_member_by_user(action.crew_id, participant_id)
        if not participant:
            raise ValueError("Not a member of this crew")
        
        if participant_id in action.participants:
            raise ValueError("Already participating")
        
        if len(action.participants) >= action.max_participants:
            raise ValueError("Action is full")
        
        action.participants.append(participant_id)
        action.total_cost += action.cost_per_participant
        
        # 更新成员贡献
        participant.actions_participated += 1
        
        return action
    
    def execute_action(self, action_id: str) -> CrewAction:
        """执行行动"""
        action = self._actions.get(action_id)
        if not action:
            raise ValueError("Action not found")
        
        if action.status != ActionStatus.APPROVED:
            raise ValueError("Action is not approved")
        
        if len(action.participants) < action.min_participants:
            action.status = ActionStatus.FAILED
            action.outcome = "Not enough participants"
            return action
        
        action.status = ActionStatus.EXECUTING
        
        # 计算成功率
        base_rate = 0.5
        participant_bonus = min(0.3, len(action.participants) * 0.05)
        action.success_rate = base_rate + participant_bonus
        
        # 模拟执行结果
        if random.random() < action.success_rate:
            action.status = ActionStatus.COMPLETED
            action.outcome = "Success"
            
            # 分配奖励
            reward_per_person = action.reward_pool // max(1, len(action.participants))
            for p_id in action.participants:
                action.rewards_distributed[p_id] = reward_per_person
            
            # 增加剧团声望
            crew = self._crews.get(action.crew_id)
            if crew:
                crew.reputation += 10
                crew.total_contribution += action.total_cost
        else:
            action.status = ActionStatus.FAILED
            action.outcome = "Failed"
        
        action.completed_at = datetime.now(timezone.utc)
        
        return action
    
    def get_crew_actions(
        self,
        crew_id: str,
        status: Optional[str] = None
    ) -> List[CrewAction]:
        """获取剧团行动列表"""
        action_ids = self._crew_actions.get(crew_id, [])
        actions = []
        
        for action_id in action_ids:
            action = self._actions.get(action_id)
            if not action:
                continue
            if status and action.status.value != status:
                continue
            actions.append(action)
        
        # 按创建时间排序
        actions.sort(key=lambda a: a.created_at, reverse=True)
        
        return actions
    
    # =========================================================================
    # 资源共享
    # =========================================================================
    def share_resource(
        self,
        crew_id: str,
        sharer_id: str,
        share_type: str,
        resource_id: str,
        recipient_ids: Optional[List[str]] = None,
        message: str = "",
        expiry_hours: int = 24
    ) -> CrewShare:
        """共享资源"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        sharer = self._get_member_by_user(crew_id, sharer_id)
        if not sharer:
            raise ValueError("Not a member of this crew")
        
        share = CrewShare(
            share_id=str(uuid.uuid4()),
            crew_id=crew_id,
            sharer_id=sharer_id,
            share_type=ShareType(share_type),
            resource_id=resource_id,
            recipient_ids=recipient_ids or [],
            message=message,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        )
        
        self._shares[share.share_id] = share
        
        if crew_id not in self._crew_shares:
            self._crew_shares[crew_id] = []
        self._crew_shares[crew_id].append(share.share_id)
        
        # 更新成员贡献
        sharer.shares_made += 1
        sharer.contribution += 5
        
        return share
    
    def claim_share(
        self,
        share_id: str,
        claimer_id: str
    ) -> CrewShare:
        """领取共享资源"""
        share = self._shares.get(share_id)
        if not share:
            raise ValueError("Share not found")
        
        # 检查是否过期
        if share.expires_at and datetime.now(timezone.utc) > share.expires_at:
            raise ValueError("Share has expired")
        
        # 检查是否是剧团成员
        claimer = self._get_member_by_user(share.crew_id, claimer_id)
        if not claimer:
            raise ValueError("Not a member of this crew")
        
        # 检查是否已领取
        if claimer_id in share.claimed_by:
            raise ValueError("Already claimed")
        
        # 检查是否是指定接收者
        if share.recipient_ids and claimer_id not in share.recipient_ids:
            raise ValueError("Not a designated recipient")
        
        share.claimed_by.append(claimer_id)
        
        return share
    
    def get_crew_shares(
        self,
        crew_id: str,
        user_id: str,
        include_expired: bool = False
    ) -> List[CrewShare]:
        """获取剧团共享资源"""
        share_ids = self._crew_shares.get(crew_id, [])
        shares = []
        
        for share_id in share_ids:
            share = self._shares.get(share_id)
            if not share:
                continue
            
            # 过期检查
            if not include_expired and share.expires_at and datetime.now(timezone.utc) > share.expires_at:
                continue
            
            # 接收者检查
            if share.recipient_ids and user_id not in share.recipient_ids and user_id != share.sharer_id:
                continue
            
            shares.append(share)
        
        # 按时间排序
        shares.sort(key=lambda s: s.shared_at, reverse=True)
        
        return shares
    
    # =========================================================================
    # 统计
    # =========================================================================
    def get_crew_statistics(self, crew_id: str) -> Dict:
        """获取剧团统计"""
        crew = self._crews.get(crew_id)
        if not crew:
            raise ValueError("Crew not found")
        
        members = self.get_members(crew_id)
        actions = self.get_crew_actions(crew_id)
        
        # 成员角色分布
        role_distribution = {role.value: 0 for role in CrewRole}
        total_contribution = 0
        
        for member in members:
            role_distribution[member.role.value] += 1
            total_contribution += member.contribution
        
        # 行动统计
        action_stats = {status.value: 0 for status in ActionStatus}
        for action in actions:
            action_stats[action.status.value] += 1
        
        # 共享统计
        share_ids = self._crew_shares.get(crew_id, [])
        total_shares = len(share_ids)
        
        return {
            "crew_id": crew_id,
            "name": crew.name,
            "tag": crew.tag,
            "tier": crew.tier,
            "reputation": crew.reputation,
            "member_count": crew.member_count,
            "role_distribution": role_distribution,
            "total_contribution": total_contribution,
            "action_stats": action_stats,
            "total_actions": len(actions),
            "total_shares": total_shares
        }
    
    def get_leaderboard(self, theatre_id: str, limit: int = 10) -> List[Dict]:
        """获取剧团排行榜"""
        crews = [c for c in self._crews.values() if c.theatre_id == theatre_id and c.status == CrewStatus.ACTIVE]
        crews.sort(key=lambda c: c.reputation, reverse=True)
        
        leaderboard = []
        for i, crew in enumerate(crews[:limit]):
            leaderboard.append({
                "rank": i + 1,
                "crew_id": crew.crew_id,
                "name": crew.name,
                "tag": crew.tag,
                "tier": crew.tier,
                "reputation": crew.reputation,
                "member_count": crew.member_count
            })
        
        return leaderboard
