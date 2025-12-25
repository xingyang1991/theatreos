"""
TheatreOS Scene Delivery Service
Handles content publishing and delivery to clients.

Key responsibilities:
- Publish slot content (from Content Factory)
- Serve slot details with ring-based filtering
- Manage published slot versions
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import (
    Theatre, HourPlan, PublishedSlot, get_db
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Transfer Objects
# =============================================================================
class SceneContent:
    """Content for a single scene."""
    
    def __init__(
        self,
        scene_id: str,
        stage_id: str,
        ring_min: str,
        media_level: str,
        title: str,
        scene_text: str,
        media_urls: Dict[str, str],
        evidence_outputs: List[Dict]
    ):
        self.scene_id = scene_id
        self.stage_id = stage_id
        self.ring_min = ring_min
        self.media_level = media_level
        self.title = title
        self.scene_text = scene_text
        self.media_urls = media_urls
        self.evidence_outputs = evidence_outputs
    
    def to_dict(self, include_full: bool = True) -> Dict:
        result = {
            "scene_id": self.scene_id,
            "stage_id": self.stage_id,
            "ring_min": self.ring_min,
            "media_level": self.media_level,
            "title": self.title
        }
        if include_full:
            result["scene_text"] = self.scene_text
            result["media_urls"] = self.media_urls
            result["evidence_outputs"] = self.evidence_outputs
        return result


class SlotBundle:
    """Complete bundle for a published slot."""
    
    def __init__(
        self,
        slot_id: str,
        theatre_id: str,
        publish_version: int,
        scenes: List[SceneContent],
        gate_instance_id: str,
        gate_config: Dict,
        notes: Optional[str] = None
    ):
        self.slot_id = slot_id
        self.theatre_id = theatre_id
        self.publish_version = publish_version
        self.scenes = scenes
        self.gate_instance_id = gate_instance_id
        self.gate_config = gate_config
        self.notes = notes
    
    def to_dict(self) -> Dict:
        return {
            "slot_id": self.slot_id,
            "theatre_id": self.theatre_id,
            "publish_version": self.publish_version,
            "scenes": [s.to_dict() for s in self.scenes],
            "gate_instance_id": self.gate_instance_id,
            "gate_config": self.gate_config,
            "notes": self.notes
        }


# =============================================================================
# Scene Delivery Service
# =============================================================================
class SceneDeliveryService:
    """
    Scene Delivery Service - Content distribution to clients.
    
    Handles:
    - Publishing slot content
    - Serving content with ring-based filtering
    - Version management for rollback support
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # Content Publishing
    # =========================================================================
    def publish_slot(
        self,
        theatre_id: str,
        slot_id: str,
        scenes: List[Dict],
        gate_instance_id: str,
        gate_config: Dict,
        source_job_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> PublishedSlot:
        """
        Publish content for a slot.
        
        This is called by Content Factory after generation/compilation.
        Creates or updates the published_slot record.
        """
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Check if already published
        existing = self.db.query(PublishedSlot).filter(
            PublishedSlot.theatre_id == theatre_uuid,
            PublishedSlot.slot_id == slot_id
        ).first()
        
        # Build payload
        payload = {
            "scenes": scenes,
            "gate_instance_id": gate_instance_id,
            "gate_config": gate_config,
            "notes": notes,
            "published_at": datetime.now(timezone.utc).isoformat()
        }
        
        if existing:
            # Update with new version
            existing.publish_version += 1
            existing.payload_jsonb = payload
            existing.published_at = datetime.now(timezone.utc)
            existing.source_job_id = source_job_id
            published = existing
            logger.info(f"Updated slot {slot_id} to version {existing.publish_version}")
        else:
            # Create new
            published = PublishedSlot(
                theatre_id=theatre_uuid,
                slot_id=slot_id,
                publish_version=1,
                payload_jsonb=payload,
                source_job_id=source_job_id
            )
            self.db.add(published)
            logger.info(f"Published new slot {slot_id}")
        
        # Update hour_plan status
        hour_plan = self.db.query(HourPlan).filter(
            HourPlan.slot_id == slot_id
        ).first()
        if hour_plan:
            hour_plan.status = "PUBLISHED"
        
        self.db.commit()
        return published
    
    def publish_rescue_slot(
        self,
        theatre_id: str,
        slot_id: str,
        rescue_type: str = "L4"
    ) -> PublishedSlot:
        """
        Publish a rescue/fallback slot when generation fails.
        
        Rescue types:
        - L3: Rescue beat template (minimal content)
        - L4: Silent slot (only gate + explanation)
        """
        # Generate minimal rescue content
        if rescue_type == "L4":
            scenes = [{
                "scene_id": f"rescue_{slot_id}_001",
                "stage_id": "stg_void",
                "ring_min": "C",
                "media_level": "L4",
                "title": "信号被迷雾吞没",
                "scene_text": "这一刻，城市的信号被一层薄雾笼罩。我们暂时失去了画面，但世界仍在运转。",
                "media_urls": {
                    "placeholder": "/static/fog_placeholder.jpg"
                },
                "evidence_outputs": []
            }]
        else:  # L3
            scenes = [{
                "scene_id": f"rescue_{slot_id}_001",
                "stage_id": "stg_echo",
                "ring_min": "C",
                "media_level": "L3",
                "title": "余波",
                "scene_text": "上一幕的回响仍在城市中流转。有人说在某个角落看到了什么，但无法确认。",
                "media_urls": {
                    "silhouette": "/static/silhouette_placeholder.jpg",
                    "audio": "/static/ambient_echo.mp3"
                },
                "evidence_outputs": [{
                    "evidence_type_id": "ev_echo_fragment",
                    "tier": "C",
                    "ttl_hours": 12
                }]
            }]
        
        # Generate rescue gate
        gate_instance_id = f"gate_rescue_{slot_id}"
        gate_config = {
            "type": "Public",
            "resolve_minute": 12,
            "options": [
                {"option_id": "opt_wait", "label": "静待迷雾散去"},
                {"option_id": "opt_search", "label": "尝试寻找信号"}
            ],
            "is_rescue": True
        }
        
        return self.publish_slot(
            theatre_id=theatre_id,
            slot_id=slot_id,
            scenes=scenes,
            gate_instance_id=gate_instance_id,
            gate_config=gate_config,
            notes=f"Rescue slot ({rescue_type})"
        )
    
    # =========================================================================
    # Content Retrieval
    # =========================================================================
    def get_slot_detail(
        self,
        slot_id: str,
        user_ring_level: str = "C"
    ) -> Optional[Dict]:
        """
        Get slot details with ring-based content filtering.
        
        Ring levels:
        - C: Basic content (everyone)
        - B: Enhanced content (nearby)
        - A: Full content (at location)
        """
        published = self.db.query(PublishedSlot).filter(
            PublishedSlot.slot_id == slot_id
        ).first()
        
        if not published:
            return None
        
        payload = published.payload_jsonb
        scenes = payload.get("scenes", [])
        
        # Filter scenes based on ring level
        ring_order = {"C": 0, "B": 1, "A": 2}
        user_ring_value = ring_order.get(user_ring_level, 0)
        
        filtered_scenes = []
        for scene in scenes:
            scene_ring_min = scene.get("ring_min", "C")
            scene_ring_value = ring_order.get(scene_ring_min, 0)
            
            if user_ring_value >= scene_ring_value:
                # User has sufficient ring level
                filtered_scenes.append(self._filter_scene_content(scene, user_ring_level))
            else:
                # User doesn't have access - show teaser
                filtered_scenes.append({
                    "scene_id": scene["scene_id"],
                    "stage_id": scene["stage_id"],
                    "ring_min": scene_ring_min,
                    "media_level": scene.get("media_level", "L0"),
                    "title": scene.get("title", "???"),
                    "locked": True,
                    "unlock_hint": f"需要到达 Ring{scene_ring_min} 解锁完整内容"
                })
        
        return {
            "slot_id": slot_id,
            "theatre_id": str(published.theatre_id),
            "publish_version": published.publish_version,
            "scenes": filtered_scenes,
            "gate_instance_id": payload.get("gate_instance_id"),
            "notes": payload.get("notes")
        }
    
    def _filter_scene_content(self, scene: Dict, ring_level: str) -> Dict:
        """Filter scene content based on ring level."""
        result = {
            "scene_id": scene["scene_id"],
            "stage_id": scene["stage_id"],
            "ring_min": scene.get("ring_min", "C"),
            "media_level": scene.get("media_level", "L0"),
            "title": scene.get("title", ""),
            "locked": False
        }
        
        # Add content based on ring level
        if ring_level in ["C", "B", "A"]:
            result["scene_text"] = scene.get("scene_text", "")
            result["media_urls"] = scene.get("media_urls", {})
        
        if ring_level in ["B", "A"]:
            # Enhanced details for nearby users
            result["evidence_outputs"] = scene.get("evidence_outputs", [])
        
        if ring_level == "A":
            # Full details for users at location
            result["full_access"] = True
            result["dialogue"] = scene.get("dialogue", [])
        
        return result
    
    # =========================================================================
    # Showbill (戏单) Generation
    # =========================================================================
    def get_showbill(
        self,
        theatre_id: str,
        hours: int = 2
    ) -> Dict:
        """
        Get the showbill (戏单) for upcoming slots.
        
        Returns a list of upcoming slots with their status.
        """
        from scheduler.src.scheduler_service import SchedulerService
        
        scheduler = SchedulerService(self.db)
        upcoming_slots = scheduler.get_upcoming_slots(theatre_id, hours)
        
        return {
            "theatre_id": theatre_id,
            "now_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
            "slots": upcoming_slots
        }
    
    # =========================================================================
    # Version Management
    # =========================================================================
    def rollback_slot(
        self,
        slot_id: str,
        target_version: int
    ) -> bool:
        """
        Rollback a slot to a previous version.
        
        Note: In production, we'd need to store version history.
        For M1, we just note that rollback was requested.
        """
        published = self.db.query(PublishedSlot).filter(
            PublishedSlot.slot_id == slot_id
        ).first()
        
        if not published:
            return False
        
        # For M1, just log the rollback request
        # In production, we'd restore from version history
        logger.warning(f"Rollback requested for {slot_id} to version {target_version}")
        
        # Add rollback note to payload
        payload = published.payload_jsonb
        payload["rollback_note"] = f"Rollback to v{target_version} requested at {datetime.now(timezone.utc).isoformat()}"
        published.payload_jsonb = payload
        
        self.db.commit()
        return True


# =============================================================================
# Static Content Generator (M1 Demo)
# =============================================================================
class StaticContentGenerator:
    """
    Generate static demo content for M1.
    
    In M2, this will be replaced by the AI Content Factory.
    """
    
    # Demo scenes for different beat types
    DEMO_SCENES = {
        "reveal": {
            "title": "意外发现",
            "scene_text": "监控画面中，一个模糊的身影出现在仓库后门。时间戳显示这是凌晨3:17。这个时间点，本不应该有人在那里。",
            "media_level": "L1"
        },
        "tension": {
            "title": "暗流涌动",
            "scene_text": "会议室的灯光忽明忽暗。桌上的文件被风吹散，但所有的窗户都是关着的。有人在这里待过，而且就在不久之前。",
            "media_level": "L1"
        },
        "action": {
            "title": "追逐",
            "scene_text": "脚步声在空旷的停车场回响。追逐者和被追者之间的距离正在缩短。转角处，一辆黑色轿车突然启动。",
            "media_level": "L0"
        },
        "quiet": {
            "title": "片刻宁静",
            "scene_text": "咖啡馆的角落，两个人低声交谈。窗外的雨已经停了，但天空依然阴沉。有些话，只能在这样的时刻说出口。",
            "media_level": "L1"
        },
        "echo": {
            "title": "回响",
            "scene_text": "昨天的事件在城市中留下了涟漪。社交媒体上开始出现各种猜测，有人声称看到了什么，但没有人能确定真相。",
            "media_level": "L2"
        }
    }
    
    @classmethod
    def generate_demo_slot(
        cls,
        slot_id: str,
        theatre_id: str,
        hour_plan: HourPlan
    ) -> SlotBundle:
        """Generate demo content for a slot based on HourPlan."""
        scenes = []
        beat_mix = hour_plan.target_beat_mix_jsonb
        
        # Generate scenes based on beat mix
        scene_count = 0
        for beat_type, weight in beat_mix.items():
            # Number of scenes for this beat type
            num_scenes = max(1, int(hour_plan.scenes_parallel * weight))
            
            for i in range(num_scenes):
                if scene_count >= hour_plan.scenes_parallel:
                    break
                
                demo = cls.DEMO_SCENES.get(beat_type, cls.DEMO_SCENES["quiet"])
                
                scene = SceneContent(
                    scene_id=f"scn_{slot_id}_{scene_count:03d}",
                    stage_id=f"stg_{(scene_count % 5) + 1:03d}",
                    ring_min="C" if beat_type in ["quiet", "echo"] else "B",
                    media_level=demo["media_level"],
                    title=f"{demo['title']} #{scene_count + 1}",
                    scene_text=demo["scene_text"],
                    media_urls={
                        "thumbnail": f"/static/demo/{beat_type}_thumb.jpg",
                        "video": f"/static/demo/{beat_type}_video.mp4"
                    },
                    evidence_outputs=hour_plan.must_drop_jsonb if scene_count == 0 else []
                )
                scenes.append(scene)
                scene_count += 1
        
        # Generate gate
        gate_config = hour_plan.hour_gate_jsonb
        gate_instance_id = f"gate_{slot_id}"
        
        gate_config["options"] = [
            {"option_id": "opt_a", "label": "选项A：追查线索", "hint": "这条路可能很危险"},
            {"option_id": "opt_b", "label": "选项B：静观其变", "hint": "有时候等待也是一种选择"}
        ]
        if gate_config.get("options_count", 2) >= 3:
            gate_config["options"].append(
                {"option_id": "opt_c", "label": "选项C：另辟蹊径", "hint": "也许有第三条路"}
            )
        
        return SlotBundle(
            slot_id=slot_id,
            theatre_id=theatre_id,
            publish_version=1,
            scenes=scenes,
            gate_instance_id=gate_instance_id,
            gate_config=gate_config,
            notes="Demo content for M1"
        )
