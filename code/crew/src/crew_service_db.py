"""
TheatreOS Crew Service (Database Version)
剧团系统服务 - 数据库持久化版本
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from kernel.src.models import (
    CrewModel, CrewMemberModel, CrewActionModel, SharedResourceModel,
    CrewTierEnum, CrewRoleEnum
)


class CrewTier(int, Enum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


class CrewRole(str, Enum):
    LEADER = "leader"
    OFFICER = "officer"
    MEMBER = "member"


# 剧团配置
TIER_CONFIG = {
    CrewTier.TIER_1: {"max_members": 5, "action_types": ["share_evidence", "group_vote"]},
    CrewTier.TIER_2: {"max_members": 10, "action_types": ["share_evidence", "group_vote", "coordinate_spread", "pool_resources"]},
    CrewTier.TIER_3: {"max_members": 20, "action_types": ["share_evidence", "group_vote", "coordinate_spread", "pool_resources", "territory_claim", "mass_action"]},
}


@dataclass
class Crew:
    """剧团数据类"""
    crew_id: str
    theatre_id: str
    name: str
    motto: Optional[str]
    tier: CrewTier
    reputation: int
    total_contribution: int
    created_at: datetime
    settings: Dict[str, Any]
    member_count: int = 0
    
    @classmethod
    def from_model(cls, model: CrewModel, member_count: int = 0) -> "Crew":
        return cls(
            crew_id=model.crew_id,
            theatre_id=model.theatre_id,
            name=model.name,
            motto=model.motto,
            tier=CrewTier(model.tier.value),
            reputation=model.reputation,
            total_contribution=model.total_contribution,
            created_at=model.created_at,
            settings=model.settings or {},
            member_count=member_count
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "crew_id": self.crew_id,
            "theatre_id": self.theatre_id,
            "name": self.name,
            "motto": self.motto,
            "tier": self.tier.value,
            "reputation": self.reputation,
            "total_contribution": self.total_contribution,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "member_count": self.member_count,
            "max_members": TIER_CONFIG[self.tier]["max_members"],
            "available_actions": TIER_CONFIG[self.tier]["action_types"]
        }


class CrewServiceDB:
    """剧团系统服务（数据库版本）"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_crew(
        self,
        theatre_id: str,
        leader_id: str,
        name: str,
        motto: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建剧团"""
        # 检查用户是否已经在其他剧团
        existing_membership = self.db.query(CrewMemberModel).join(CrewModel).filter(
            CrewMemberModel.user_id == leader_id,
            CrewModel.theatre_id == theatre_id
        ).first()
        
        if existing_membership:
            return {"success": False, "error": "Already in a crew in this theatre"}
        
        crew_id = f"crew_{uuid.uuid4().hex[:12]}"
        
        # 创建剧团
        crew_model = CrewModel(
            crew_id=crew_id,
            theatre_id=theatre_id,
            name=name,
            motto=motto,
            tier=CrewTierEnum.TIER_1,
            reputation=0,
            total_contribution=0,
            created_at=datetime.utcnow(),
            settings={}
        )
        
        self.db.add(crew_model)
        
        # 添加创建者为队长
        member_model = CrewMemberModel(
            crew_id=crew_id,
            user_id=leader_id,
            role=CrewRoleEnum.LEADER,
            contribution=0,
            joined_at=datetime.utcnow()
        )
        
        self.db.add(member_model)
        self.db.commit()
        self.db.refresh(crew_model)
        
        return {
            "success": True,
            "crew": Crew.from_model(crew_model, member_count=1).to_dict()
        }
    
    def get_crew(self, crew_id: str) -> Optional[Crew]:
        """获取剧团详情"""
        model = self.db.query(CrewModel).filter(
            CrewModel.crew_id == crew_id
        ).first()
        
        if not model:
            return None
        
        member_count = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id
        ).count()
        
        return Crew.from_model(model, member_count)
    
    def invite_member(self, crew_id: str, inviter_id: str, invitee_id: str) -> Dict[str, Any]:
        """邀请成员"""
        crew_model = self.db.query(CrewModel).filter(
            CrewModel.crew_id == crew_id
        ).first()
        
        if not crew_model:
            return {"success": False, "error": "Crew not found"}
        
        # 检查邀请者权限
        inviter_membership = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id,
            CrewMemberModel.user_id == inviter_id
        ).first()
        
        if not inviter_membership or inviter_membership.role not in [CrewRoleEnum.LEADER, CrewRoleEnum.OFFICER]:
            return {"success": False, "error": "No permission to invite"}
        
        # 检查被邀请者是否已在剧团
        existing = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id,
            CrewMemberModel.user_id == invitee_id
        ).first()
        
        if existing:
            return {"success": False, "error": "User already in crew"}
        
        # 检查人数上限
        member_count = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id
        ).count()
        
        tier = CrewTier(crew_model.tier.value)
        max_members = TIER_CONFIG[tier]["max_members"]
        
        if member_count >= max_members:
            return {"success": False, "error": f"Crew is full (max {max_members} members)"}
        
        # 添加成员
        member_model = CrewMemberModel(
            crew_id=crew_id,
            user_id=invitee_id,
            role=CrewRoleEnum.MEMBER,
            contribution=0,
            joined_at=datetime.utcnow()
        )
        
        self.db.add(member_model)
        self.db.commit()
        
        return {
            "success": True,
            "crew_id": crew_id,
            "new_member_id": invitee_id,
            "current_members": member_count + 1
        }
    
    def leave_crew(self, crew_id: str, user_id: str) -> Dict[str, Any]:
        """离开剧团"""
        membership = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id,
            CrewMemberModel.user_id == user_id
        ).first()
        
        if not membership:
            return {"success": False, "error": "Not a member of this crew"}
        
        if membership.role == CrewRoleEnum.LEADER:
            # 队长离开需要转让或解散
            member_count = self.db.query(CrewMemberModel).filter(
                CrewMemberModel.crew_id == crew_id
            ).count()
            
            if member_count > 1:
                return {"success": False, "error": "Leader must transfer leadership before leaving"}
            else:
                # 只有队长一人，解散剧团
                self.db.query(CrewMemberModel).filter(
                    CrewMemberModel.crew_id == crew_id
                ).delete()
                self.db.query(CrewModel).filter(
                    CrewModel.crew_id == crew_id
                ).delete()
                self.db.commit()
                return {"success": True, "message": "Crew disbanded"}
        
        self.db.delete(membership)
        self.db.commit()
        
        return {"success": True, "message": "Left crew successfully"}
    
    def get_members(self, crew_id: str) -> List[Dict[str, Any]]:
        """获取剧团成员列表"""
        members = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id
        ).order_by(CrewMemberModel.joined_at).all()
        
        return [{
            "user_id": m.user_id,
            "role": m.role.value,
            "contribution": m.contribution,
            "joined_at": m.joined_at.isoformat()
        } for m in members]
    
    def initiate_action(
        self,
        crew_id: str,
        initiator_id: str,
        action_type: str,
        target_id: Optional[str] = None,
        required_participants: int = 1
    ) -> Dict[str, Any]:
        """发起集体行动"""
        crew_model = self.db.query(CrewModel).filter(
            CrewModel.crew_id == crew_id
        ).first()
        
        if not crew_model:
            return {"success": False, "error": "Crew not found"}
        
        # 检查发起者是否是成员
        membership = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id,
            CrewMemberModel.user_id == initiator_id
        ).first()
        
        if not membership:
            return {"success": False, "error": "Not a member of this crew"}
        
        # 检查行动类型是否支持
        tier = CrewTier(crew_model.tier.value)
        if action_type not in TIER_CONFIG[tier]["action_types"]:
            return {"success": False, "error": f"Action type '{action_type}' not available for tier {tier.value}"}
        
        action_id = f"act_{uuid.uuid4().hex[:12]}"
        
        action_model = CrewActionModel(
            action_id=action_id,
            crew_id=crew_id,
            action_type=action_type,
            target_id=target_id,
            status="pending",
            required_participants=required_participants,
            current_participants=1,  # 发起者自动参与
            created_at=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.db.add(action_model)
        self.db.commit()
        
        return {
            "success": True,
            "action_id": action_id,
            "action_type": action_type,
            "required_participants": required_participants,
            "current_participants": 1
        }
    
    def join_action(self, action_id: str, user_id: str) -> Dict[str, Any]:
        """加入集体行动"""
        action_model = self.db.query(CrewActionModel).filter(
            CrewActionModel.action_id == action_id
        ).first()
        
        if not action_model:
            return {"success": False, "error": "Action not found"}
        
        if action_model.status != "pending":
            return {"success": False, "error": "Action is not pending"}
        
        # 检查是否是剧团成员
        membership = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == action_model.crew_id,
            CrewMemberModel.user_id == user_id
        ).first()
        
        if not membership:
            return {"success": False, "error": "Not a member of this crew"}
        
        action_model.current_participants += 1
        
        # 检查是否达到所需人数
        if action_model.current_participants >= action_model.required_participants:
            action_model.status = "in_progress"
        
        self.db.commit()
        
        return {
            "success": True,
            "action_id": action_id,
            "current_participants": action_model.current_participants,
            "status": action_model.status
        }
    
    def share_resource(
        self,
        crew_id: str,
        contributor_id: str,
        resource_type: str,
        resource_ref_id: Optional[str] = None,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """共享资源"""
        # 检查是否是成员
        membership = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == crew_id,
            CrewMemberModel.user_id == contributor_id
        ).first()
        
        if not membership:
            return {"success": False, "error": "Not a member of this crew"}
        
        resource_id = f"res_{uuid.uuid4().hex[:12]}"
        
        resource_model = SharedResourceModel(
            resource_id=resource_id,
            crew_id=crew_id,
            contributor_id=contributor_id,
            resource_type=resource_type,
            resource_ref_id=resource_ref_id,
            quantity=quantity,
            is_claimed=False,
            shared_at=datetime.utcnow()
        )
        
        self.db.add(resource_model)
        
        # 增加贡献值
        membership.contribution += quantity * 10
        
        self.db.commit()
        
        return {
            "success": True,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "quantity": quantity
        }
    
    def claim_resource(self, resource_id: str, claimer_id: str) -> Dict[str, Any]:
        """领取共享资源"""
        resource_model = self.db.query(SharedResourceModel).filter(
            SharedResourceModel.resource_id == resource_id
        ).first()
        
        if not resource_model:
            return {"success": False, "error": "Resource not found"}
        
        if resource_model.is_claimed:
            return {"success": False, "error": "Resource already claimed"}
        
        # 检查是否是剧团成员
        membership = self.db.query(CrewMemberModel).filter(
            CrewMemberModel.crew_id == resource_model.crew_id,
            CrewMemberModel.user_id == claimer_id
        ).first()
        
        if not membership:
            return {"success": False, "error": "Not a member of this crew"}
        
        resource_model.is_claimed = True
        resource_model.claimed_by = claimer_id
        resource_model.claimed_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "resource_id": resource_id,
            "resource_type": resource_model.resource_type,
            "quantity": resource_model.quantity
        }
    
    def get_theatre_crews(self, theatre_id: str) -> List[Crew]:
        """获取剧场的所有剧团"""
        models = self.db.query(CrewModel).filter(
            CrewModel.theatre_id == theatre_id
        ).order_by(CrewModel.reputation.desc()).all()
        
        result = []
        for model in models:
            member_count = self.db.query(CrewMemberModel).filter(
                CrewMemberModel.crew_id == model.crew_id
            ).count()
            result.append(Crew.from_model(model, member_count))
        
        return result
    
    def get_user_crew(self, user_id: str, theatre_id: str) -> Optional[Crew]:
        """获取用户在指定剧场的剧团"""
        membership = self.db.query(CrewMemberModel).join(CrewModel).filter(
            CrewMemberModel.user_id == user_id,
            CrewModel.theatre_id == theatre_id
        ).first()
        
        if not membership:
            return None
        
        return self.get_crew(membership.crew_id)
    
    def get_crew_stats(self, crew_id: str) -> Dict[str, Any]:
        """获取剧团统计"""
        crew = self.get_crew(crew_id)
        if not crew:
            return {"error": "Crew not found"}
        
        members = self.get_members(crew_id)
        
        total_actions = self.db.query(CrewActionModel).filter(
            CrewActionModel.crew_id == crew_id
        ).count()
        
        completed_actions = self.db.query(CrewActionModel).filter(
            CrewActionModel.crew_id == crew_id,
            CrewActionModel.status == "completed"
        ).count()
        
        shared_resources = self.db.query(SharedResourceModel).filter(
            SharedResourceModel.crew_id == crew_id
        ).count()
        
        return {
            "crew": crew.to_dict(),
            "member_count": len(members),
            "total_actions": total_actions,
            "completed_actions": completed_actions,
            "shared_resources": shared_resources,
            "top_contributors": sorted(members, key=lambda x: x["contribution"], reverse=True)[:5]
        }
    
    def get_leaderboard(self, theatre_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取剧团排行榜"""
        crews = self.db.query(CrewModel).filter(
            CrewModel.theatre_id == theatre_id
        ).order_by(CrewModel.reputation.desc()).limit(limit).all()
        
        result = []
        for i, crew_model in enumerate(crews):
            member_count = self.db.query(CrewMemberModel).filter(
                CrewMemberModel.crew_id == crew_model.crew_id
            ).count()
            
            result.append({
                "rank": i + 1,
                "crew": Crew.from_model(crew_model, member_count).to_dict()
            })
        
        return result
