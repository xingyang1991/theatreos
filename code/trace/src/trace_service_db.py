"""
TheatreOS Trace Service (Database Version)
痕迹系统服务 - 数据库持久化版本
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from kernel.src.models import TraceModel, TraceDiscoveryModel, TraceTypeEnum


class TraceType(str, Enum):
    FOOTPRINT = "footprint"
    MARK = "mark"
    MESSAGE = "message"
    OFFERING = "offering"


class TraceVisibility(str, Enum):
    PUBLIC = "public"
    CREW = "crew"
    PRIVATE = "private"


# 痕迹配置
TRACE_CONFIG = {
    TraceType.FOOTPRINT: {"ttl_hours": 24, "difficulty": 0.3, "discovery_xp": 5},
    TraceType.MARK: {"ttl_hours": 72, "difficulty": 0.5, "discovery_xp": 10},
    TraceType.MESSAGE: {"ttl_hours": 48, "difficulty": 0.4, "discovery_xp": 15},
    TraceType.OFFERING: {"ttl_hours": 168, "difficulty": 0.7, "discovery_xp": 25},
}


@dataclass
class Trace:
    """痕迹数据类"""
    trace_id: str
    theatre_id: str
    creator_id: str
    stage_id: str
    position_hint: Optional[str]
    trace_type: TraceType
    content: Optional[str]
    visibility: str
    discovery_difficulty: float
    created_at: datetime
    expires_at: Optional[datetime]
    discovery_count: int
    metadata: Dict[str, Any]
    
    @classmethod
    def from_model(cls, model: TraceModel) -> "Trace":
        return cls(
            trace_id=model.trace_id,
            theatre_id=model.theatre_id,
            creator_id=model.creator_id,
            stage_id=model.stage_id,
            position_hint=model.position_hint,
            trace_type=TraceType(model.trace_type.value),
            content=model.content,
            visibility=model.visibility,
            discovery_difficulty=model.discovery_difficulty,
            created_at=model.created_at,
            expires_at=model.expires_at,
            discovery_count=model.discovery_count,
            metadata=model.metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "theatre_id": self.theatre_id,
            "creator_id": self.creator_id,
            "stage_id": self.stage_id,
            "position_hint": self.position_hint,
            "trace_type": self.trace_type.value,
            "content": self.content,
            "visibility": self.visibility,
            "discovery_difficulty": self.discovery_difficulty,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "discovery_count": self.discovery_count,
            "is_expired": self.is_expired,
            "metadata": self.metadata
        }
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class TraceServiceDB:
    """痕迹系统服务（数据库版本）"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def leave_trace(
        self,
        theatre_id: str,
        creator_id: str,
        stage_id: str,
        trace_type: TraceType = TraceType.FOOTPRINT,
        content: Optional[str] = None,
        position_hint: Optional[str] = None,
        visibility: str = "public",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """留下痕迹"""
        trace_id = f"trc_{uuid.uuid4().hex[:16]}"
        
        config = TRACE_CONFIG[trace_type]
        expires_at = datetime.utcnow() + timedelta(hours=config["ttl_hours"])
        
        model = TraceModel(
            trace_id=trace_id,
            theatre_id=theatre_id,
            creator_id=creator_id,
            stage_id=stage_id,
            position_hint=position_hint,
            trace_type=TraceTypeEnum(trace_type.value),
            content=content,
            visibility=visibility,
            discovery_difficulty=config["difficulty"],
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            discovery_count=0,
            metadata=metadata or {}
        )
        
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        
        return {
            "success": True,
            "trace": Trace.from_model(model).to_dict()
        }
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取痕迹详情"""
        model = self.db.query(TraceModel).filter(
            TraceModel.trace_id == trace_id
        ).first()
        
        if not model:
            return None
        
        return Trace.from_model(model)
    
    def discover_trace(self, trace_id: str, discoverer_id: str) -> Dict[str, Any]:
        """发现痕迹"""
        model = self.db.query(TraceModel).filter(
            TraceModel.trace_id == trace_id
        ).first()
        
        if not model:
            return {"success": False, "error": "Trace not found"}
        
        trace = Trace.from_model(model)
        
        if trace.is_expired:
            return {"success": False, "error": "Trace has expired"}
        
        # 检查是否已经发现过
        existing_discovery = self.db.query(TraceDiscoveryModel).filter(
            TraceDiscoveryModel.trace_id == trace_id,
            TraceDiscoveryModel.discoverer_id == discoverer_id
        ).first()
        
        if existing_discovery:
            return {"success": False, "error": "Already discovered this trace"}
        
        # 发现难度检查（简化版：随机）
        import random
        if random.random() > trace.discovery_difficulty:
            # 创建发现记录
            discovery = TraceDiscoveryModel(
                discovery_id=f"disc_{uuid.uuid4().hex[:16]}",
                trace_id=trace_id,
                discoverer_id=discoverer_id,
                discovered_at=datetime.utcnow()
            )
            
            self.db.add(discovery)
            
            # 更新发现计数
            model.discovery_count += 1
            self.db.commit()
            
            config = TRACE_CONFIG[trace.trace_type]
            
            return {
                "success": True,
                "discovered": True,
                "trace": trace.to_dict(),
                "xp_earned": config["discovery_xp"]
            }
        else:
            return {
                "success": True,
                "discovered": False,
                "message": "Failed to discover trace, try again"
            }
    
    def get_stage_traces(
        self,
        stage_id: str,
        viewer_id: Optional[str] = None,
        include_expired: bool = False
    ) -> List[Trace]:
        """获取舞台上的痕迹"""
        query = self.db.query(TraceModel).filter(
            TraceModel.stage_id == stage_id
        )
        
        if not include_expired:
            query = query.filter(
                or_(
                    TraceModel.expires_at == None,
                    TraceModel.expires_at > datetime.utcnow()
                )
            )
        
        # 可见性过滤
        if viewer_id:
            query = query.filter(
                or_(
                    TraceModel.visibility == "public",
                    TraceModel.creator_id == viewer_id
                )
            )
        else:
            query = query.filter(TraceModel.visibility == "public")
        
        models = query.order_by(TraceModel.created_at.desc()).all()
        return [Trace.from_model(m) for m in models]
    
    def get_user_traces(self, user_id: str, theatre_id: Optional[str] = None) -> List[Trace]:
        """获取用户留下的痕迹"""
        query = self.db.query(TraceModel).filter(
            TraceModel.creator_id == user_id
        )
        
        if theatre_id:
            query = query.filter(TraceModel.theatre_id == theatre_id)
        
        models = query.order_by(TraceModel.created_at.desc()).all()
        return [Trace.from_model(m) for m in models]
    
    def get_user_discoveries(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户发现的痕迹"""
        discoveries = self.db.query(TraceDiscoveryModel).filter(
            TraceDiscoveryModel.discoverer_id == user_id
        ).order_by(TraceDiscoveryModel.discovered_at.desc()).all()
        
        result = []
        for disc in discoveries:
            trace = self.get_trace(disc.trace_id)
            if trace:
                result.append({
                    "discovery_id": disc.discovery_id,
                    "discovered_at": disc.discovered_at.isoformat(),
                    "trace": trace.to_dict()
                })
        
        return result
    
    def get_stage_density(self, stage_id: str) -> Dict[str, Any]:
        """获取舞台痕迹密度"""
        total = self.db.query(TraceModel).filter(
            TraceModel.stage_id == stage_id,
            or_(
                TraceModel.expires_at == None,
                TraceModel.expires_at > datetime.utcnow()
            )
        ).count()
        
        # 按类型统计
        type_counts = {}
        for trace_type in TraceType:
            count = self.db.query(TraceModel).filter(
                TraceModel.stage_id == stage_id,
                TraceModel.trace_type == TraceTypeEnum(trace_type.value),
                or_(
                    TraceModel.expires_at == None,
                    TraceModel.expires_at > datetime.utcnow()
                )
            ).count()
            type_counts[trace_type.value] = count
        
        # 计算热度等级
        if total >= 20:
            heat_level = "very_high"
        elif total >= 10:
            heat_level = "high"
        elif total >= 5:
            heat_level = "medium"
        elif total > 0:
            heat_level = "low"
        else:
            heat_level = "none"
        
        return {
            "stage_id": stage_id,
            "total_traces": total,
            "by_type": type_counts,
            "heat_level": heat_level
        }
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户痕迹档案"""
        traces_left = self.db.query(TraceModel).filter(
            TraceModel.creator_id == user_id
        ).count()
        
        traces_discovered = self.db.query(TraceDiscoveryModel).filter(
            TraceDiscoveryModel.discoverer_id == user_id
        ).count()
        
        # 计算总XP
        total_xp = 0
        for trace_type in TraceType:
            count = self.db.query(TraceDiscoveryModel).join(TraceModel).filter(
                TraceDiscoveryModel.discoverer_id == user_id,
                TraceModel.trace_type == TraceTypeEnum(trace_type.value)
            ).count()
            total_xp += count * TRACE_CONFIG[trace_type]["discovery_xp"]
        
        return {
            "user_id": user_id,
            "traces_left": traces_left,
            "traces_discovered": traces_discovered,
            "discovery_xp": total_xp
        }
    
    def get_theatre_stats(self, theatre_id: str) -> Dict[str, Any]:
        """获取剧场痕迹统计"""
        total = self.db.query(TraceModel).filter(
            TraceModel.theatre_id == theatre_id
        ).count()
        
        active = self.db.query(TraceModel).filter(
            TraceModel.theatre_id == theatre_id,
            or_(
                TraceModel.expires_at == None,
                TraceModel.expires_at > datetime.utcnow()
            )
        ).count()
        
        total_discoveries = self.db.query(TraceDiscoveryModel).join(TraceModel).filter(
            TraceModel.theatre_id == theatre_id
        ).count()
        
        return {
            "theatre_id": theatre_id,
            "total_traces": total,
            "active_traces": active,
            "total_discoveries": total_discoveries
        }
