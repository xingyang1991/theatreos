"""
TheatreOS Evidence Service (Database Version)
证物系统服务 - 数据库持久化版本
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from kernel.src.models import (
    EvidenceModel, EvidenceTransferModel, 
    EvidenceGradeEnum, EvidenceRarityEnum
)


class EvidenceGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class EvidenceRarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


# Grade配置
GRADE_CONFIG = {
    EvidenceGrade.A: {"ttl_hours": 168, "verify_bonus": 3.0, "trade_value": 100},
    EvidenceGrade.B: {"ttl_hours": 72, "verify_bonus": 2.0, "trade_value": 50},
    EvidenceGrade.C: {"ttl_hours": 24, "verify_bonus": 1.0, "trade_value": 10},
}

# Rarity配置
RARITY_CONFIG = {
    EvidenceRarity.COMMON: {"drop_weight": 50, "value_multiplier": 1.0},
    EvidenceRarity.UNCOMMON: {"drop_weight": 30, "value_multiplier": 1.5},
    EvidenceRarity.RARE: {"drop_weight": 15, "value_multiplier": 2.5},
    EvidenceRarity.EPIC: {"drop_weight": 4, "value_multiplier": 5.0},
    EvidenceRarity.LEGENDARY: {"drop_weight": 1, "value_multiplier": 10.0},
}


@dataclass
class Evidence:
    """证物数据类"""
    evidence_id: str
    theatre_id: str
    owner_id: str
    name: str
    description: str
    grade: EvidenceGrade
    rarity: EvidenceRarity
    evidence_type: str
    source_scene_id: Optional[str]
    source_stage_id: Optional[str]
    obtained_at: datetime
    expires_at: Optional[datetime]
    is_verified: bool
    is_tradeable: bool
    is_consumed: bool
    metadata: Dict[str, Any]
    
    @classmethod
    def from_model(cls, model: EvidenceModel) -> "Evidence":
        return cls(
            evidence_id=model.evidence_id,
            theatre_id=model.theatre_id,
            owner_id=model.owner_id,
            name=model.name,
            description=model.description or "",
            grade=EvidenceGrade(model.grade.value),
            rarity=EvidenceRarity(model.rarity.value),
            evidence_type=model.evidence_type,
            source_scene_id=model.source_scene_id,
            source_stage_id=model.source_stage_id,
            obtained_at=model.obtained_at,
            expires_at=model.expires_at,
            is_verified=model.is_verified,
            is_tradeable=model.is_tradeable,
            is_consumed=model.is_consumed,
            metadata=model.metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "theatre_id": self.theatre_id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "grade": self.grade.value,
            "rarity": self.rarity.value,
            "evidence_type": self.evidence_type,
            "source_scene_id": self.source_scene_id,
            "source_stage_id": self.source_stage_id,
            "obtained_at": self.obtained_at.isoformat() if self.obtained_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_verified": self.is_verified,
            "is_tradeable": self.is_tradeable,
            "is_consumed": self.is_consumed,
            "is_expired": self.is_expired,
            "metadata": self.metadata
        }
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class EvidenceServiceDB:
    """证物系统服务（数据库版本）"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def grant_evidence(
        self,
        theatre_id: str,
        user_id: str,
        name: str,
        description: str = "",
        grade: EvidenceGrade = EvidenceGrade.C,
        rarity: EvidenceRarity = EvidenceRarity.COMMON,
        evidence_type: str = "document",
        source_scene_id: Optional[str] = None,
        source_stage_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Evidence:
        """授予用户证物"""
        evidence_id = f"evi_{uuid.uuid4().hex[:16]}"
        
        # 计算过期时间
        ttl_hours = GRADE_CONFIG[grade]["ttl_hours"]
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        # 创建数据库记录
        model = EvidenceModel(
            evidence_id=evidence_id,
            theatre_id=theatre_id,
            owner_id=user_id,
            name=name,
            description=description,
            grade=EvidenceGradeEnum(grade.value),
            rarity=EvidenceRarityEnum(rarity.value),
            evidence_type=evidence_type,
            source_scene_id=source_scene_id,
            source_stage_id=source_stage_id,
            obtained_at=datetime.utcnow(),
            expires_at=expires_at,
            is_verified=False,
            is_tradeable=True,
            is_consumed=False,
            metadata=metadata or {}
        )
        
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        
        return Evidence.from_model(model)
    
    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """获取证物详情"""
        model = self.db.query(EvidenceModel).filter(
            EvidenceModel.evidence_id == evidence_id
        ).first()
        
        if not model:
            return None
        
        return Evidence.from_model(model)
    
    def get_user_evidences(
        self,
        user_id: str,
        theatre_id: Optional[str] = None,
        include_expired: bool = False,
        grade_filter: Optional[EvidenceGrade] = None
    ) -> List[Evidence]:
        """获取用户的证物列表"""
        query = self.db.query(EvidenceModel).filter(
            EvidenceModel.owner_id == user_id,
            EvidenceModel.is_consumed == False
        )
        
        if theatre_id:
            query = query.filter(EvidenceModel.theatre_id == theatre_id)
        
        if not include_expired:
            query = query.filter(
                or_(
                    EvidenceModel.expires_at == None,
                    EvidenceModel.expires_at > datetime.utcnow()
                )
            )
        
        if grade_filter:
            query = query.filter(EvidenceModel.grade == EvidenceGradeEnum(grade_filter.value))
        
        models = query.order_by(EvidenceModel.obtained_at.desc()).all()
        return [Evidence.from_model(m) for m in models]
    
    def verify_evidence(self, evidence_id: str, verifier_context: Optional[Dict] = None) -> Dict[str, Any]:
        """验证证物真伪"""
        model = self.db.query(EvidenceModel).filter(
            EvidenceModel.evidence_id == evidence_id
        ).first()
        
        if not model:
            return {"success": False, "error": "Evidence not found"}
        
        evidence = Evidence.from_model(model)
        
        if evidence.is_expired:
            return {"success": False, "error": "Evidence has expired"}
        
        if evidence.is_consumed:
            return {"success": False, "error": "Evidence has been consumed"}
        
        # 验证逻辑（简化版：基于元数据中的验证码）
        is_authentic = True
        confidence = 0.95
        
        if verifier_context and "challenge" in verifier_context:
            # 如果提供了挑战，进行更严格的验证
            expected_hash = hashlib.sha256(
                f"{evidence_id}:{model.metadata.get('secret', '')}".encode()
            ).hexdigest()[:8]
            is_authentic = verifier_context.get("response") == expected_hash
            confidence = 1.0 if is_authentic else 0.0
        
        # 更新验证状态
        model.is_verified = is_authentic
        self.db.commit()
        
        return {
            "success": True,
            "evidence_id": evidence_id,
            "is_authentic": is_authentic,
            "confidence": confidence,
            "grade_bonus": GRADE_CONFIG[evidence.grade]["verify_bonus"] if is_authentic else 0
        }
    
    def transfer_evidence(
        self,
        evidence_id: str,
        from_user_id: str,
        to_user_id: str,
        transfer_type: str = "trade"
    ) -> Dict[str, Any]:
        """转移证物所有权"""
        model = self.db.query(EvidenceModel).filter(
            EvidenceModel.evidence_id == evidence_id
        ).first()
        
        if not model:
            return {"success": False, "error": "Evidence not found"}
        
        evidence = Evidence.from_model(model)
        
        if evidence.owner_id != from_user_id:
            return {"success": False, "error": "Not the owner"}
        
        if not evidence.is_tradeable:
            return {"success": False, "error": "Evidence is not tradeable"}
        
        if evidence.is_expired:
            return {"success": False, "error": "Evidence has expired"}
        
        if evidence.is_consumed:
            return {"success": False, "error": "Evidence has been consumed"}
        
        # 执行转移
        model.owner_id = to_user_id
        
        # 记录转移历史
        transfer_record = EvidenceTransferModel(
            transfer_id=f"xfer_{uuid.uuid4().hex[:16]}",
            evidence_id=evidence_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            transfer_type=transfer_type,
            transferred_at=datetime.utcnow()
        )
        
        self.db.add(transfer_record)
        self.db.commit()
        
        return {
            "success": True,
            "evidence_id": evidence_id,
            "new_owner_id": to_user_id,
            "transfer_type": transfer_type
        }
    
    def consume_evidence(self, evidence_id: str, user_id: str, purpose: str = "submit") -> Dict[str, Any]:
        """消耗证物"""
        model = self.db.query(EvidenceModel).filter(
            EvidenceModel.evidence_id == evidence_id
        ).first()
        
        if not model:
            return {"success": False, "error": "Evidence not found"}
        
        evidence = Evidence.from_model(model)
        
        if evidence.owner_id != user_id:
            return {"success": False, "error": "Not the owner"}
        
        if evidence.is_consumed:
            return {"success": False, "error": "Already consumed"}
        
        if evidence.is_expired:
            return {"success": False, "error": "Evidence has expired"}
        
        # 标记为已消耗
        model.is_consumed = True
        model.metadata = {**model.metadata, "consumed_purpose": purpose, "consumed_at": datetime.utcnow().isoformat()}
        self.db.commit()
        
        return {
            "success": True,
            "evidence_id": evidence_id,
            "purpose": purpose,
            "value_returned": GRADE_CONFIG[evidence.grade]["trade_value"] * RARITY_CONFIG[evidence.rarity]["value_multiplier"]
        }
    
    def get_theatre_stats(self, theatre_id: str) -> Dict[str, Any]:
        """获取剧场证物统计"""
        total = self.db.query(EvidenceModel).filter(
            EvidenceModel.theatre_id == theatre_id
        ).count()
        
        active = self.db.query(EvidenceModel).filter(
            EvidenceModel.theatre_id == theatre_id,
            EvidenceModel.is_consumed == False,
            or_(
                EvidenceModel.expires_at == None,
                EvidenceModel.expires_at > datetime.utcnow()
            )
        ).count()
        
        verified = self.db.query(EvidenceModel).filter(
            EvidenceModel.theatre_id == theatre_id,
            EvidenceModel.is_verified == True
        ).count()
        
        # 按等级统计
        grade_stats = {}
        for grade in EvidenceGrade:
            count = self.db.query(EvidenceModel).filter(
                EvidenceModel.theatre_id == theatre_id,
                EvidenceModel.grade == EvidenceGradeEnum(grade.value)
            ).count()
            grade_stats[grade.value] = count
        
        return {
            "theatre_id": theatre_id,
            "total_evidences": total,
            "active_evidences": active,
            "verified_evidences": verified,
            "by_grade": grade_stats
        }
