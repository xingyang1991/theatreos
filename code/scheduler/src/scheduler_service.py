"""
TheatreOS Scheduler Service
Generates HourPlans based on world state and theme pack rules.

Key responsibilities:
- Generate HourPlans for upcoming slots
- Determine primary/support threads based on world state
- Calculate beat mix and gate configurations
- Handle manual overrides
"""
import json
import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
import random

from sqlalchemy.orm import Session
from sqlalchemy import func

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import (
    Theatre, HourPlan, HourPlanOverride, PublishedSlot, 
    WorldVarCurrent, ThreadStateCurrent, get_db
)
from config.settings import (
    SCHEDULE_LOOKAHEAD_HOURS, DEFAULT_PARALLEL_SCENES,
    GOLDEN_HOURS, GATE_RESOLVE_MINUTE, SLOT_DURATION_MINUTES
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Transfer Objects
# =============================================================================
class SlotConfig:
    """Configuration for a single slot."""
    
    def __init__(
        self,
        slot_id: str,
        start_at: datetime,
        scenes_parallel: int,
        primary_thread: Optional[str],
        support_threads: List[str],
        target_beat_mix: Dict[str, float],
        hour_gate: Dict,
        must_drop: List[Dict]
    ):
        self.slot_id = slot_id
        self.start_at = start_at
        self.scenes_parallel = scenes_parallel
        self.primary_thread = primary_thread
        self.support_threads = support_threads
        self.target_beat_mix = target_beat_mix
        self.hour_gate = hour_gate
        self.must_drop = must_drop
    
    def to_dict(self) -> Dict:
        return {
            "slot_id": self.slot_id,
            "start_at": self.start_at.isoformat(),
            "scenes_parallel": self.scenes_parallel,
            "primary_thread": self.primary_thread,
            "support_threads": self.support_threads,
            "target_beat_mix": self.target_beat_mix,
            "hour_gate": self.hour_gate,
            "must_drop": self.must_drop
        }


# =============================================================================
# Beat Mix Templates (from Theme Pack)
# =============================================================================
# In production, these would come from the Theme Pack
BEAT_MIX_TEMPLATES = {
    "standard": {
        "reveal": 0.25,
        "tension": 0.30,
        "action": 0.20,
        "quiet": 0.15,
        "echo": 0.10
    },
    "high_tension": {
        "reveal": 0.15,
        "tension": 0.45,
        "action": 0.25,
        "quiet": 0.10,
        "echo": 0.05
    },
    "revelation": {
        "reveal": 0.45,
        "tension": 0.20,
        "action": 0.15,
        "quiet": 0.10,
        "echo": 0.10
    },
    "aftermath": {
        "reveal": 0.10,
        "tension": 0.15,
        "action": 0.10,
        "quiet": 0.35,
        "echo": 0.30
    }
}

# Gate type configurations
GATE_TYPES = {
    "Public": {
        "weight": 0.6,
        "stake_allowed": False,
        "evidence_required": False
    },
    "Fate": {
        "weight": 0.3,
        "stake_allowed": True,
        "evidence_required": False
    },
    "FateMajor": {
        "weight": 0.08,
        "stake_allowed": True,
        "evidence_required": True
    },
    "Council": {
        "weight": 0.02,
        "stake_allowed": True,
        "evidence_required": True
    }
}


# =============================================================================
# Scheduler Service
# =============================================================================
class SchedulerService:
    """
    Scheduler Service - The director's assistant.
    
    Generates HourPlans that tell Content Factory what to produce.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # Slot ID Generation
    # =========================================================================
    def generate_slot_id(self, theatre_id: str, start_time: datetime) -> str:
        """
        Generate a deterministic slot_id based on theatre and time.
        Format: W{week}_D{day}_{hour}{minute}
        Example: W2_D5_2300 (Week 2, Friday, 23:00)
        """
        # Get week number within the season (assuming season starts at theatre creation)
        week_num = (start_time.isocalendar()[1] % 4) + 1  # 1-4 cycle
        day_num = start_time.isoweekday()  # 1=Monday, 7=Sunday
        hour = start_time.hour
        minute = start_time.minute
        
        return f"W{week_num}_D{day_num}_{hour:02d}{minute:02d}"
    
    # =========================================================================
    # HourPlan Generation
    # =========================================================================
    def generate_hour_plan(
        self,
        theatre_id: str,
        target_time: datetime,
        world_state: Optional[Dict] = None
    ) -> HourPlan:
        """
        Generate an HourPlan for a specific time slot.
        
        Uses world state to determine:
        - Which threads are active and their priorities
        - What beat mix is appropriate
        - What gate type to use
        - What evidence must drop
        """
        theatre = self.db.query(Theatre).filter(
            Theatre.theatre_id == uuid.UUID(theatre_id)
        ).first()
        
        if not theatre:
            raise ValueError(f"Theatre {theatre_id} not found")
        
        # Generate slot_id
        slot_id = self.generate_slot_id(theatre_id, target_time)
        
        # Check if plan already exists
        existing = self.db.query(HourPlan).filter(
            HourPlan.slot_id == slot_id
        ).first()
        
        if existing:
            logger.info(f"HourPlan {slot_id} already exists")
            return existing
        
        # Get world state if not provided
        if world_state is None:
            world_state = self._get_world_state_dict(theatre_id)
        
        # Determine thread priorities
        primary_thread, support_threads = self._select_threads(theatre_id, world_state)
        
        # Determine beat mix based on world tension and time
        beat_mix = self._calculate_beat_mix(world_state, target_time)
        
        # Determine gate type
        hour_gate = self._determine_gate(world_state, target_time)
        
        # Determine must-drop evidence
        must_drop = self._calculate_must_drop(world_state, primary_thread)
        
        # Calculate parallel scenes (more during golden hours)
        scenes_parallel = self._calculate_parallel_scenes(target_time)
        
        # Create HourPlan
        hour_plan = HourPlan(
            slot_id=slot_id,
            theatre_id=uuid.UUID(theatre_id),
            start_at=target_time,
            scenes_parallel=scenes_parallel,
            primary_thread=primary_thread,
            support_threads_jsonb=support_threads,
            target_beat_mix_jsonb=beat_mix,
            hour_gate_jsonb=hour_gate,
            must_drop_jsonb=must_drop,
            status="SCHEDULED"
        )
        
        self.db.add(hour_plan)
        self.db.commit()
        
        logger.info(f"Generated HourPlan {slot_id} for theatre {theatre_id}")
        return hour_plan
    
    def generate_upcoming_plans(
        self,
        theatre_id: str,
        hours_ahead: int = SCHEDULE_LOOKAHEAD_HOURS
    ) -> List[HourPlan]:
        """Generate HourPlans for the next N hours."""
        plans = []
        now = datetime.now(timezone.utc)
        
        # Round to next hour
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        for i in range(hours_ahead):
            target_time = next_hour + timedelta(hours=i)
            plan = self.generate_hour_plan(theatre_id, target_time)
            plans.append(plan)
        
        return plans
    
    # =========================================================================
    # Thread Selection
    # =========================================================================
    def _select_threads(
        self,
        theatre_id: str,
        world_state: Dict
    ) -> Tuple[Optional[str], List[str]]:
        """
        Select primary and support threads based on world state.
        
        Priority rules:
        1. Threads with high progress get priority (momentum)
        2. Threads affected by recent gate outcomes get boosted
        3. Ensure variety - don't repeat same primary too often
        """
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Get all active threads
        threads = self.db.query(ThreadStateCurrent).filter(
            ThreadStateCurrent.theatre_id == theatre_uuid
        ).all()
        
        if not threads:
            # Default threads for new theatre
            return "thread_01", ["thread_02", "thread_03"]
        
        # Score threads
        thread_scores = []
        for thread in threads:
            score = 0
            
            # Progress bonus (threads with momentum)
            score += thread.progress * 0.5
            
            # Phase bonus (later phases are more important)
            phase_num = int(thread.phase_id.split("_")[-1]) if "_" in thread.phase_id else 1
            score += phase_num * 2
            
            # Variety penalty (check recent plans)
            recent_primary_count = self._count_recent_primary(theatre_id, thread.thread_id)
            score -= recent_primary_count * 3
            
            thread_scores.append((thread.thread_id, score))
        
        # Sort by score
        thread_scores.sort(key=lambda x: x[1], reverse=True)
        
        primary = thread_scores[0][0] if thread_scores else None
        support = [t[0] for t in thread_scores[1:4]]  # Top 3 support threads
        
        return primary, support
    
    def _count_recent_primary(self, theatre_id: str, thread_id: str, hours: int = 6) -> int:
        """Count how many times a thread was primary in recent hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        count = self.db.query(HourPlan).filter(
            HourPlan.theatre_id == uuid.UUID(theatre_id),
            HourPlan.primary_thread == thread_id,
            HourPlan.start_at >= cutoff
        ).count()
        
        return count
    
    # =========================================================================
    # Beat Mix Calculation
    # =========================================================================
    def _calculate_beat_mix(
        self,
        world_state: Dict,
        target_time: datetime
    ) -> Dict[str, float]:
        """
        Calculate target beat mix based on world state and time.
        
        Factors:
        - World tension level (var: tension)
        - Time of day (evening = more tension)
        - Day of week (Friday = climax, Sunday = aftermath)
        """
        # Get world tension
        tension = world_state.get("vars", {}).get("tension", 0.5)
        
        # Time factors
        hour = target_time.hour
        day = target_time.isoweekday()
        
        # Select base template
        if day == 5 and hour >= 20:  # Friday night
            template = "high_tension"
        elif day == 7:  # Sunday
            template = "aftermath"
        elif tension > 0.7:
            template = "high_tension"
        elif tension < 0.3:
            template = "aftermath"
        else:
            template = "standard"
        
        # Get base mix
        beat_mix = BEAT_MIX_TEMPLATES[template].copy()
        
        # Adjust based on tension
        if tension > 0.5:
            # Increase tension beats
            beat_mix["tension"] = min(0.5, beat_mix["tension"] + (tension - 0.5) * 0.2)
            beat_mix["quiet"] = max(0.05, beat_mix["quiet"] - (tension - 0.5) * 0.1)
        
        # Normalize to sum to 1
        total = sum(beat_mix.values())
        beat_mix = {k: v / total for k, v in beat_mix.items()}
        
        return beat_mix
    
    # =========================================================================
    # Gate Determination
    # =========================================================================
    def _determine_gate(
        self,
        world_state: Dict,
        target_time: datetime
    ) -> Dict:
        """
        Determine gate type and configuration for the slot.
        
        Rules:
        - Council gates only on Sunday (议会)
        - FateMajor gates on Friday nights
        - Higher tension = more Fate gates
        """
        hour = target_time.hour
        day = target_time.isoweekday()
        tension = world_state.get("vars", {}).get("tension", 0.5)
        
        # Determine gate type
        if day == 7 and hour >= 18:  # Sunday evening
            gate_type = "Council"
        elif day == 5 and hour >= 21:  # Friday late night
            gate_type = "FateMajor"
        elif tension > 0.6 or (hour in GOLDEN_HOURS and random.random() < 0.3):
            gate_type = "Fate"
        else:
            gate_type = "Public"
        
        # Build gate config
        gate_config = {
            "type": gate_type,
            "resolve_minute": GATE_RESOLVE_MINUTE,
            "options_count": 2 if gate_type == "Public" else 3,
            "stake_allowed": GATE_TYPES[gate_type]["stake_allowed"],
            "evidence_required": GATE_TYPES[gate_type]["evidence_required"]
        }
        
        return gate_config
    
    # =========================================================================
    # Must-Drop Evidence
    # =========================================================================
    def _calculate_must_drop(
        self,
        world_state: Dict,
        primary_thread: Optional[str]
    ) -> List[Dict]:
        """
        Calculate evidence that must drop in this slot.
        
        Rules:
        - Each slot should drop 1-3 evidence pieces
        - Higher tier evidence is rarer
        - Evidence should relate to active threads
        """
        must_drop = []
        
        # Always drop at least one C-tier evidence
        must_drop.append({
            "evidence_type_id": f"ev_{primary_thread or 'generic'}_clue",
            "tier": "C",
            "ttl_hours": 24
        })
        
        # 50% chance of B-tier
        if random.random() < 0.5:
            must_drop.append({
                "evidence_type_id": f"ev_{primary_thread or 'generic'}_fragment",
                "tier": "B",
                "ttl_hours": 48
            })
        
        # 10% chance of A-tier (rare)
        if random.random() < 0.1:
            must_drop.append({
                "evidence_type_id": f"ev_{primary_thread or 'generic'}_key",
                "tier": "A",
                "ttl_hours": 72
            })
        
        return must_drop
    
    # =========================================================================
    # Parallel Scenes Calculation
    # =========================================================================
    def _calculate_parallel_scenes(self, target_time: datetime) -> int:
        """Calculate number of parallel scenes based on expected activity."""
        hour = target_time.hour
        day = target_time.isoweekday()
        
        base = DEFAULT_PARALLEL_SCENES
        
        # Golden hours get more scenes
        if hour in GOLDEN_HOURS:
            base += 4
        
        # Weekend bonus
        if day >= 6:
            base += 2
        
        # Late night reduction
        if hour >= 2 and hour <= 6:
            base = max(4, base - 4)
        
        return base
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    def _get_world_state_dict(self, theatre_id: str) -> Dict:
        """Get world state as a dictionary."""
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Get vars
        vars_query = self.db.query(WorldVarCurrent).filter(
            WorldVarCurrent.theatre_id == theatre_uuid
        ).all()
        vars_dict = {v.var_id: v.value for v in vars_query}
        
        # Get threads
        threads_query = self.db.query(ThreadStateCurrent).filter(
            ThreadStateCurrent.theatre_id == theatre_uuid
        ).all()
        threads_dict = {
            t.thread_id: {
                "phase_id": t.phase_id,
                "progress": t.progress,
                "branch_bucket": t.branch_bucket
            }
            for t in threads_query
        }
        
        return {
            "vars": vars_dict,
            "threads": threads_dict
        }
    
    # =========================================================================
    # Override Management
    # =========================================================================
    def apply_override(
        self,
        slot_id: str,
        override_data: Dict,
        reason: str,
        operator: str
    ) -> HourPlanOverride:
        """Apply a manual override to an HourPlan."""
        hour_plan = self.db.query(HourPlan).filter(
            HourPlan.slot_id == slot_id
        ).first()
        
        if not hour_plan:
            raise ValueError(f"HourPlan {slot_id} not found")
        
        # Create override record
        override = HourPlanOverride(
            slot_id=slot_id,
            theatre_id=hour_plan.theatre_id,
            override_jsonb=override_data,
            reason=reason,
            operator=operator
        )
        self.db.add(override)
        
        # Apply override to hour_plan
        if "primary_thread" in override_data:
            hour_plan.primary_thread = override_data["primary_thread"]
        if "support_threads" in override_data:
            hour_plan.support_threads_jsonb = override_data["support_threads"]
        if "target_beat_mix" in override_data:
            hour_plan.target_beat_mix_jsonb = override_data["target_beat_mix"]
        if "hour_gate" in override_data:
            hour_plan.hour_gate_jsonb = override_data["hour_gate"]
        if "must_drop" in override_data:
            hour_plan.must_drop_jsonb = override_data["must_drop"]
        
        self.db.commit()
        logger.info(f"Override applied to {slot_id} by {operator}: {reason}")
        
        return override
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    def get_upcoming_slots(
        self,
        theatre_id: str,
        hours: int = 2
    ) -> List[Dict]:
        """Get upcoming slots for the showbill."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours)
        
        plans = self.db.query(HourPlan).filter(
            HourPlan.theatre_id == uuid.UUID(theatre_id),
            HourPlan.start_at >= now,
            HourPlan.start_at <= cutoff
        ).order_by(HourPlan.start_at).all()
        
        result = []
        for plan in plans:
            # Check if published
            published = self.db.query(PublishedSlot).filter(
                PublishedSlot.theatre_id == plan.theatre_id,
                PublishedSlot.slot_id == plan.slot_id
            ).first()
            
            result.append({
                "slot_id": plan.slot_id,
                "start_at_ms": int(plan.start_at.timestamp() * 1000),
                "end_at_ms": int((plan.start_at + timedelta(minutes=SLOT_DURATION_MINUTES)).timestamp() * 1000),
                "theatre_mode": "Flagship",  # TODO: Support multiple modes
                "gate_type": plan.hour_gate_jsonb.get("type", "Public"),
                "scenes_parallel": plan.scenes_parallel,
                "published": published is not None
            })
        
        return result
    
    def get_hour_plan(self, slot_id: str) -> Optional[HourPlan]:
        """Get a specific HourPlan."""
        return self.db.query(HourPlan).filter(
            HourPlan.slot_id == slot_id
        ).first()
