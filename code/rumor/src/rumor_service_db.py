"""
TheatreOS Rumor Service (Database Version)
谣言系统服务 - 数据库持久化版本
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from kernel.src.models import RumorModel, RumorSpreadModel, RumorStatusEnum


class RumorStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    VIRAL = "viral"
    DEBUNKED = "debunked"
    EXPIRED = "expired"


# 谣言配置
RUMOR_CONFIG = {
    "max_length": 280,
    "cooldown_minutes": 10,
    "viral_threshold": 10,
    "expire_hours": 48,
    "credibility_decay_rate": 0.1,
}


@dataclass
class Rumor:
    """谣言数据类"""
    rumor_id: str
    theatre_id: str
    author_id: str
    content: str
    target_thread_id: Optional[str]
    target_character_id: Optional[str]
    status: RumorStatus
    credibility_score: float
    spread_count: int
    created_at: datetime
    published_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_moderated: bool
    moderation_result: Optional[str]
    metadata: Dict[str, Any]
    
    @classmethod
    def from_model(cls, model: RumorModel) -> "Rumor":
        return cls(
            rumor_id=model.rumor_id,
            theatre_id=model.theatre_id,
            author_id=model.author_id,
            content=model.content,
            target_thread_id=model.target_thread_id,
            target_character_id=model.target_character_id,
            status=RumorStatus(model.status.value),
            credibility_score=model.credibility_score,
            spread_count=model.spread_count,
            created_at=model.created_at,
            published_at=model.published_at,
            expires_at=model.expires_at,
            is_moderated=model.is_moderated,
            moderation_result=model.moderation_result,
            metadata=model.metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rumor_id": self.rumor_id,
            "theatre_id": self.theatre_id,
            "author_id": self.author_id,
            "content": self.content,
            "target_thread_id": self.target_thread_id,
            "target_character_id": self.target_character_id,
            "status": self.status.value,
            "credibility_score": self.credibility_score,
            "spread_count": self.spread_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "is_viral": self.is_viral,
            "metadata": self.metadata
        }
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_viral(self) -> bool:
        return self.spread_count >= RUMOR_CONFIG["viral_threshold"]


class RumorServiceDB:
    """谣言系统服务（数据库版本）"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_rumor(
        self,
        theatre_id: str,
        author_id: str,
        content: str,
        target_thread_id: Optional[str] = None,
        target_character_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """创建谣言"""
        # 内容长度检查
        if len(content) > RUMOR_CONFIG["max_length"]:
            return {"success": False, "error": f"Content exceeds {RUMOR_CONFIG['max_length']} characters"}
        
        # 冷却检查
        cooldown_time = datetime.utcnow() - timedelta(minutes=RUMOR_CONFIG["cooldown_minutes"])
        recent_rumor = self.db.query(RumorModel).filter(
            RumorModel.author_id == author_id,
            RumorModel.created_at > cooldown_time
        ).first()
        
        if recent_rumor:
            return {"success": False, "error": "Please wait before creating another rumor"}
        
        rumor_id = f"rum_{uuid.uuid4().hex[:16]}"
        expires_at = datetime.utcnow() + timedelta(hours=RUMOR_CONFIG["expire_hours"])
        
        model = RumorModel(
            rumor_id=rumor_id,
            theatre_id=theatre_id,
            author_id=author_id,
            content=content,
            target_thread_id=target_thread_id,
            target_character_id=target_character_id,
            status=RumorStatusEnum.DRAFT,
            credibility_score=0.5,
            spread_count=0,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            is_moderated=False,
            metadata=metadata or {}
        )
        
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        
        return {
            "success": True,
            "rumor": Rumor.from_model(model).to_dict()
        }
    
    def get_rumor(self, rumor_id: str) -> Optional[Rumor]:
        """获取谣言详情"""
        model = self.db.query(RumorModel).filter(
            RumorModel.rumor_id == rumor_id
        ).first()
        
        if not model:
            return None
        
        return Rumor.from_model(model)
    
    def publish_rumor(self, rumor_id: str, author_id: str) -> Dict[str, Any]:
        """发布谣言"""
        model = self.db.query(RumorModel).filter(
            RumorModel.rumor_id == rumor_id
        ).first()
        
        if not model:
            return {"success": False, "error": "Rumor not found"}
        
        if model.author_id != author_id:
            return {"success": False, "error": "Not the author"}
        
        if model.status != RumorStatusEnum.DRAFT:
            return {"success": False, "error": "Rumor is not in draft status"}
        
        model.status = RumorStatusEnum.ACTIVE
        model.published_at = datetime.utcnow()
        self.db.commit()
        
        return {
            "success": True,
            "rumor": Rumor.from_model(model).to_dict()
        }
    
    def spread_rumor(
        self,
        rumor_id: str,
        spreader_id: str,
        stage_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """传播谣言"""
        model = self.db.query(RumorModel).filter(
            RumorModel.rumor_id == rumor_id
        ).first()
        
        if not model:
            return {"success": False, "error": "Rumor not found"}
        
        rumor = Rumor.from_model(model)
        
        if rumor.status not in [RumorStatus.ACTIVE, RumorStatus.VIRAL]:
            return {"success": False, "error": "Rumor is not active"}
        
        if rumor.is_expired:
            return {"success": False, "error": "Rumor has expired"}
        
        # 检查是否已经传播过
        existing_spread = self.db.query(RumorSpreadModel).filter(
            RumorSpreadModel.rumor_id == rumor_id,
            RumorSpreadModel.spreader_id == spreader_id
        ).first()
        
        if existing_spread:
            return {"success": False, "error": "Already spread this rumor"}
        
        # 创建传播记录
        spread_record = RumorSpreadModel(
            spread_id=f"spr_{uuid.uuid4().hex[:16]}",
            rumor_id=rumor_id,
            spreader_id=spreader_id,
            stage_id=stage_id,
            spread_at=datetime.utcnow(),
            reach_count=1
        )
        
        self.db.add(spread_record)
        
        # 更新传播计数
        model.spread_count += 1
        
        # 检查是否达到病毒传播阈值
        if model.spread_count >= RUMOR_CONFIG["viral_threshold"] and model.status == RumorStatusEnum.ACTIVE:
            model.status = RumorStatusEnum.VIRAL
        
        self.db.commit()
        
        return {
            "success": True,
            "rumor_id": rumor_id,
            "new_spread_count": model.spread_count,
            "is_viral": model.status == RumorStatusEnum.VIRAL
        }
    
    def debunk_rumor(self, rumor_id: str, debunker_id: str, evidence_ids: List[str] = None) -> Dict[str, Any]:
        """辟谣"""
        model = self.db.query(RumorModel).filter(
            RumorModel.rumor_id == rumor_id
        ).first()
        
        if not model:
            return {"success": False, "error": "Rumor not found"}
        
        if model.status == RumorStatusEnum.DEBUNKED:
            return {"success": False, "error": "Already debunked"}
        
        # 计算辟谣成功率（简化版：基于证据数量）
        evidence_count = len(evidence_ids) if evidence_ids else 0
        success_chance = min(0.3 + evidence_count * 0.2, 0.95)
        
        import random
        if random.random() < success_chance:
            model.status = RumorStatusEnum.DEBUNKED
            model.credibility_score = 0.0
            model.metadata = {
                **model.metadata,
                "debunked_by": debunker_id,
                "debunked_at": datetime.utcnow().isoformat(),
                "evidence_used": evidence_ids or []
            }
            self.db.commit()
            
            return {
                "success": True,
                "debunked": True,
                "rumor_id": rumor_id
            }
        else:
            return {
                "success": True,
                "debunked": False,
                "message": "Debunk attempt failed, need more evidence"
            }
    
    def get_theatre_rumors(
        self,
        theatre_id: str,
        status_filter: Optional[RumorStatus] = None,
        include_expired: bool = False,
        limit: int = 50
    ) -> List[Rumor]:
        """获取剧场的谣言列表"""
        query = self.db.query(RumorModel).filter(
            RumorModel.theatre_id == theatre_id
        )
        
        if status_filter:
            query = query.filter(RumorModel.status == RumorStatusEnum(status_filter.value))
        else:
            # 默认只返回活跃和病毒状态的谣言
            query = query.filter(RumorModel.status.in_([RumorStatusEnum.ACTIVE, RumorStatusEnum.VIRAL]))
        
        if not include_expired:
            query = query.filter(
                or_(
                    RumorModel.expires_at == None,
                    RumorModel.expires_at > datetime.utcnow()
                )
            )
        
        models = query.order_by(RumorModel.spread_count.desc()).limit(limit).all()
        return [Rumor.from_model(m) for m in models]
    
    def get_user_rumors(self, user_id: str, theatre_id: Optional[str] = None) -> List[Rumor]:
        """获取用户创建的谣言"""
        query = self.db.query(RumorModel).filter(
            RumorModel.author_id == user_id
        )
        
        if theatre_id:
            query = query.filter(RumorModel.theatre_id == theatre_id)
        
        models = query.order_by(RumorModel.created_at.desc()).all()
        return [Rumor.from_model(m) for m in models]
    
    def get_stage_heat(self, stage_id: str) -> Dict[str, Any]:
        """获取舞台的谣言热度"""
        # 统计该舞台相关的传播
        spread_count = self.db.query(func.count(RumorSpreadModel.spread_id)).filter(
            RumorSpreadModel.stage_id == stage_id
        ).scalar()
        
        # 获取最近的谣言
        recent_spreads = self.db.query(RumorSpreadModel).filter(
            RumorSpreadModel.stage_id == stage_id
        ).order_by(RumorSpreadModel.spread_at.desc()).limit(5).all()
        
        recent_rumor_ids = [s.rumor_id for s in recent_spreads]
        
        return {
            "stage_id": stage_id,
            "total_spreads": spread_count,
            "heat_level": "hot" if spread_count > 20 else "warm" if spread_count > 5 else "cold",
            "recent_rumor_ids": recent_rumor_ids
        }
    
    def get_theatre_stats(self, theatre_id: str) -> Dict[str, Any]:
        """获取剧场谣言统计"""
        total = self.db.query(RumorModel).filter(
            RumorModel.theatre_id == theatre_id
        ).count()
        
        active = self.db.query(RumorModel).filter(
            RumorModel.theatre_id == theatre_id,
            RumorModel.status == RumorStatusEnum.ACTIVE
        ).count()
        
        viral = self.db.query(RumorModel).filter(
            RumorModel.theatre_id == theatre_id,
            RumorModel.status == RumorStatusEnum.VIRAL
        ).count()
        
        debunked = self.db.query(RumorModel).filter(
            RumorModel.theatre_id == theatre_id,
            RumorModel.status == RumorStatusEnum.DEBUNKED
        ).count()
        
        total_spreads = self.db.query(func.sum(RumorModel.spread_count)).filter(
            RumorModel.theatre_id == theatre_id
        ).scalar() or 0
        
        return {
            "theatre_id": theatre_id,
            "total_rumors": total,
            "active_rumors": active,
            "viral_rumors": viral,
            "debunked_rumors": debunked,
            "total_spreads": total_spreads
        }
