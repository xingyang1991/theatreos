"""
TheatreOS Theatre Kernel Service
Core service for world state management, tick engine, and delta application.

Key responsibilities:
- Manage world state (vars, threads, objects)
- Execute hourly ticks
- Apply deltas with idempotency
- Generate snapshots for replay/archaeology
"""
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from kernel.src.database import (
    Theatre, WorldVarCurrent, ThreadStateCurrent, ObjectHolderCurrent,
    WorldStateSnapshot, WorldEventLog, WorldDeltaIdempotency, get_db
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Transfer Objects
# =============================================================================
class WorldState:
    """Represents the current state of a theatre's world."""
    
    def __init__(
        self,
        theatre_id: str,
        tick_id: int,
        version: int,
        vars: Dict[str, float],
        threads: Dict[str, Dict],
        objects: Dict[str, Dict]
    ):
        self.theatre_id = theatre_id
        self.tick_id = tick_id
        self.version = version
        self.vars = vars
        self.threads = threads
        self.objects = objects
    
    def to_dict(self) -> Dict:
        return {
            "theatre_id": str(self.theatre_id),
            "tick_id": self.tick_id,
            "version": self.version,
            "vars": self.vars,
            "threads": self.threads,
            "objects": self.objects
        }


class DeltaOperation:
    """A single operation within a delta."""
    
    def __init__(self, op: str, **kwargs):
        self.op = op
        self.params = kwargs
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DeltaOperation":
        op = data.pop("op")
        return cls(op, **data)


class ApplyDeltaRequest:
    """Request to apply changes to world state."""
    
    def __init__(
        self,
        delta_id: str,
        expected_version: int,
        source: Dict[str, str],
        ops: List[Dict]
    ):
        self.delta_id = delta_id
        self.expected_version = expected_version
        self.source = source
        self.ops = [DeltaOperation.from_dict(op.copy()) for op in ops]


class ApplyDeltaResult:
    """Result of applying a delta."""
    
    def __init__(
        self,
        applied: bool,
        new_version: int,
        tick_id: int,
        event_ids: List[str],
        error: Optional[str] = None
    ):
        self.applied = applied
        self.new_version = new_version
        self.tick_id = tick_id
        self.event_ids = event_ids
        self.error = error
    
    def to_dict(self) -> Dict:
        result = {
            "applied": self.applied,
            "new_version": self.new_version,
            "tick_id": self.tick_id,
            "event_ids": self.event_ids
        }
        if self.error:
            result["error"] = self.error
        return result


# =============================================================================
# Kernel Service
# =============================================================================
class KernelService:
    """
    Theatre Kernel Service - The heart of TheatreOS.
    
    Invariants (must be guaranteed):
    - I1: All WorldState changes must be driven by WorldEvent (append-only)
    - I2: Only one final snapshot per theatre per tick_id
    - I3: ApplyDelta must be idempotent (same delta_id = same result)
    - I4: Thread branches must be rejoinable
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # Theatre Management
    # =========================================================================
    def create_theatre(
        self,
        city: str,
        theme_id: str,
        theme_version: str,
        timezone_str: str = "Asia/Shanghai",
        initial_vars: Optional[Dict[str, float]] = None,
        initial_threads: Optional[List[Dict]] = None
    ) -> Theatre:
        """Create a new theatre with initial world state."""
        theatre = Theatre(
            city=city,
            timezone=timezone_str,
            theme_id=theme_id,
            theme_version=theme_version,
            status="ACTIVE"
        )
        self.db.add(theatre)
        self.db.flush()  # Get the theatre_id
        
        # Initialize world variables
        if initial_vars:
            for var_id, value in initial_vars.items():
                world_var = WorldVarCurrent(
                    theatre_id=theatre.theatre_id,
                    var_id=var_id,
                    value=max(0, min(1, value))  # Clamp to [0, 1]
                )
                self.db.add(world_var)
        
        # Initialize thread states
        if initial_threads:
            for thread in initial_threads:
                thread_state = ThreadStateCurrent(
                    theatre_id=theatre.theatre_id,
                    thread_id=thread["thread_id"],
                    phase_id=thread.get("phase_id", "intro"),
                    progress=thread.get("progress", 0),
                    branch_bucket=thread.get("branch_bucket", "main"),
                    locks_jsonb=thread.get("locks", {})
                )
                self.db.add(thread_state)
        
        # Log creation event
        self._log_event(
            theatre.theatre_id,
            tick_id=0,
            event_type="theatre.created",
            payload={
                "city": city,
                "theme_id": theme_id,
                "theme_version": theme_version
            }
        )
        
        self.db.commit()
        logger.info(f"Created theatre {theatre.theatre_id} in {city}")
        return theatre
    
    def get_theatre(self, theatre_id: str) -> Optional[Theatre]:
        """Get a theatre by ID."""
        return self.db.query(Theatre).filter(
            Theatre.theatre_id == uuid.UUID(theatre_id)
        ).first()
    
    # =========================================================================
    # World State Reading
    # =========================================================================
    def get_world_state(self, theatre_id: str) -> Optional[WorldState]:
        """
        Get the current world state for a theatre.
        Returns vars, threads, objects, and current version.
        """
        theatre = self.get_theatre(theatre_id)
        if not theatre:
            return None
        
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Get current tick_id (latest snapshot or 0)
        latest_snapshot = self.db.query(WorldStateSnapshot).filter(
            WorldStateSnapshot.theatre_id == theatre_uuid
        ).order_by(WorldStateSnapshot.tick_id.desc()).first()
        
        tick_id = latest_snapshot.tick_id if latest_snapshot else 0
        version = latest_snapshot.version if latest_snapshot else 0
        
        # Get world variables
        vars_query = self.db.query(WorldVarCurrent).filter(
            WorldVarCurrent.theatre_id == theatre_uuid
        ).all()
        vars_dict = {v.var_id: v.value for v in vars_query}
        
        # Get thread states
        threads_query = self.db.query(ThreadStateCurrent).filter(
            ThreadStateCurrent.theatre_id == theatre_uuid
        ).all()
        threads_dict = {
            t.thread_id: {
                "phase_id": t.phase_id,
                "progress": t.progress,
                "branch_bucket": t.branch_bucket,
                "locks": t.locks_jsonb
            }
            for t in threads_query
        }
        
        # Get object holders
        objects_query = self.db.query(ObjectHolderCurrent).filter(
            ObjectHolderCurrent.theatre_id == theatre_uuid
        ).all()
        objects_dict = {
            o.object_id: {
                "holder_type": o.holder_type,
                "holder_id": o.holder_id
            }
            for o in objects_query
        }
        
        return WorldState(
            theatre_id=theatre_id,
            tick_id=tick_id,
            version=version,
            vars=vars_dict,
            threads=threads_dict,
            objects=objects_dict
        )
    
    # =========================================================================
    # Tick Engine
    # =========================================================================
    def run_tick(self, theatre_id: str) -> Tuple[int, int]:
        """
        Execute a tick for the theatre.
        
        This advances the world clock and creates a snapshot.
        Returns (new_tick_id, new_version).
        """
        theatre = self.get_theatre(theatre_id)
        if not theatre:
            raise ValueError(f"Theatre {theatre_id} not found")
        
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Calculate new tick_id (UTC hour-based)
        now = datetime.now(timezone.utc)
        new_tick_id = int(now.timestamp() // 3600)  # Hours since epoch
        
        # Get current state
        world_state = self.get_world_state(theatre_id)
        new_version = (world_state.version if world_state else 0) + 1
        
        # Log tick started event
        self._log_event(
            theatre_uuid,
            tick_id=new_tick_id,
            event_type="world.tick.started",
            payload={"started_at": now.isoformat()}
        )
        
        # Create snapshot
        snapshot_data = {
            "vars": world_state.vars if world_state else {},
            "threads": world_state.threads if world_state else {},
            "objects": world_state.objects if world_state else {},
            "tick_timestamp": now.isoformat()
        }
        
        snapshot = WorldStateSnapshot(
            theatre_id=theatre_uuid,
            tick_id=new_tick_id,
            version=new_version,
            state_jsonb=snapshot_data
        )
        self.db.merge(snapshot)  # Use merge for upsert behavior
        
        # Log tick completed event
        self._log_event(
            theatre_uuid,
            tick_id=new_tick_id,
            event_type="world.tick.completed",
            payload={
                "snapshot_version": new_version,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        self.db.commit()
        logger.info(f"Tick completed for theatre {theatre_id}: tick_id={new_tick_id}, version={new_version}")
        
        return new_tick_id, new_version
    
    # =========================================================================
    # Apply Delta (Idempotent World State Changes)
    # =========================================================================
    def apply_delta(
        self,
        theatre_id: str,
        request: ApplyDeltaRequest
    ) -> ApplyDeltaResult:
        """
        Apply a delta to the world state.
        
        This is the ONLY way to modify world state (besides tick).
        Must be idempotent: same delta_id always returns same result.
        """
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Check idempotency - if already applied, return cached result
        existing = self.db.query(WorldDeltaIdempotency).filter(
            WorldDeltaIdempotency.delta_id == request.delta_id
        ).first()
        
        if existing:
            logger.info(f"Delta {request.delta_id} already applied, returning cached result")
            # Return the previously applied result
            world_state = self.get_world_state(theatre_id)
            return ApplyDeltaResult(
                applied=True,
                new_version=world_state.version,
                tick_id=world_state.tick_id,
                event_ids=[]  # Events already logged
            )
        
        # Get current state and check version
        world_state = self.get_world_state(theatre_id)
        if not world_state:
            return ApplyDeltaResult(
                applied=False,
                new_version=0,
                tick_id=0,
                event_ids=[],
                error="THEATRE_NOT_FOUND"
            )
        
        if world_state.version != request.expected_version:
            return ApplyDeltaResult(
                applied=False,
                new_version=world_state.version,
                tick_id=world_state.tick_id,
                event_ids=[],
                error="VERSION_CONFLICT"
            )
        
        # Apply operations
        event_ids = []
        for op in request.ops:
            event_id = self._apply_operation(theatre_uuid, world_state.tick_id, op, request.delta_id)
            if event_id:
                event_ids.append(event_id)
        
        # Update version (create new snapshot with incremented version)
        new_version = world_state.version + 1
        
        # Record idempotency
        result_hash = hashlib.sha256(
            json.dumps({"version": new_version, "event_ids": event_ids}).encode()
        ).hexdigest()
        
        idempotency_record = WorldDeltaIdempotency(
            delta_id=request.delta_id,
            theatre_id=theatre_uuid,
            result_hash=result_hash
        )
        self.db.add(idempotency_record)
        
        # Log delta applied event
        self._log_event(
            theatre_uuid,
            tick_id=world_state.tick_id,
            event_type="world.delta.applied",
            payload={
                "delta_id": request.delta_id,
                "new_version": new_version,
                "source": request.source,
                "ops_count": len(request.ops)
            },
            delta_id=request.delta_id
        )
        
        self.db.commit()
        logger.info(f"Delta {request.delta_id} applied: version {world_state.version} -> {new_version}")
        
        return ApplyDeltaResult(
            applied=True,
            new_version=new_version,
            tick_id=world_state.tick_id,
            event_ids=event_ids
        )
    
    def _apply_operation(
        self,
        theatre_id: uuid.UUID,
        tick_id: int,
        op: DeltaOperation,
        delta_id: str
    ) -> Optional[str]:
        """Apply a single operation and return event_id if logged."""
        
        if op.op == "world_var_add":
            return self._op_world_var_add(theatre_id, tick_id, op.params, delta_id)
        elif op.op == "world_var_set":
            return self._op_world_var_set(theatre_id, tick_id, op.params, delta_id)
        elif op.op == "thread_advance":
            return self._op_thread_advance(theatre_id, tick_id, op.params, delta_id)
        elif op.op == "object_transfer":
            return self._op_object_transfer(theatre_id, tick_id, op.params, delta_id)
        else:
            logger.warning(f"Unknown operation type: {op.op}")
            return None
    
    def _op_world_var_add(
        self,
        theatre_id: uuid.UUID,
        tick_id: int,
        params: Dict,
        delta_id: str
    ) -> str:
        """Add to a world variable (clamped to [0, 1])."""
        var_id = params["var_id"]
        delta_value = params["delta"]
        
        var = self.db.query(WorldVarCurrent).filter(
            WorldVarCurrent.theatre_id == theatre_id,
            WorldVarCurrent.var_id == var_id
        ).first()
        
        old_value = var.value if var else 0
        new_value = max(0, min(1, old_value + delta_value))
        
        if var:
            var.value = new_value
        else:
            var = WorldVarCurrent(
                theatre_id=theatre_id,
                var_id=var_id,
                value=new_value
            )
            self.db.add(var)
        
        event_id = self._log_event(
            theatre_id, tick_id,
            event_type="world.var.changed",
            payload={"var_id": var_id, "old": old_value, "new": new_value},
            delta_id=delta_id
        )
        return event_id
    
    def _op_world_var_set(
        self,
        theatre_id: uuid.UUID,
        tick_id: int,
        params: Dict,
        delta_id: str
    ) -> str:
        """Set a world variable to a specific value."""
        var_id = params["var_id"]
        new_value = max(0, min(1, params["value"]))
        
        var = self.db.query(WorldVarCurrent).filter(
            WorldVarCurrent.theatre_id == theatre_id,
            WorldVarCurrent.var_id == var_id
        ).first()
        
        old_value = var.value if var else 0
        
        if var:
            var.value = new_value
        else:
            var = WorldVarCurrent(
                theatre_id=theatre_id,
                var_id=var_id,
                value=new_value
            )
            self.db.add(var)
        
        event_id = self._log_event(
            theatre_id, tick_id,
            event_type="world.var.changed",
            payload={"var_id": var_id, "old": old_value, "new": new_value},
            delta_id=delta_id
        )
        return event_id
    
    def _op_thread_advance(
        self,
        theatre_id: uuid.UUID,
        tick_id: int,
        params: Dict,
        delta_id: str
    ) -> str:
        """Advance a thread's state."""
        thread_id = params["thread_id"]
        
        thread = self.db.query(ThreadStateCurrent).filter(
            ThreadStateCurrent.theatre_id == theatre_id,
            ThreadStateCurrent.thread_id == thread_id
        ).first()
        
        old_state = {
            "phase_id": thread.phase_id if thread else None,
            "progress": thread.progress if thread else 0,
            "branch_bucket": thread.branch_bucket if thread else "main"
        }
        
        if thread:
            if "phase_to" in params:
                thread.phase_id = params["phase_to"]
            if "progress_add" in params:
                thread.progress += params["progress_add"]
            if "branch_bucket" in params:
                thread.branch_bucket = params["branch_bucket"]
        else:
            thread = ThreadStateCurrent(
                theatre_id=theatre_id,
                thread_id=thread_id,
                phase_id=params.get("phase_to", "intro"),
                progress=params.get("progress_add", 0),
                branch_bucket=params.get("branch_bucket", "main")
            )
            self.db.add(thread)
        
        new_state = {
            "phase_id": thread.phase_id,
            "progress": thread.progress,
            "branch_bucket": thread.branch_bucket
        }
        
        event_id = self._log_event(
            theatre_id, tick_id,
            event_type="thread.advanced",
            payload={"thread_id": thread_id, "from": old_state, "to": new_state},
            delta_id=delta_id
        )
        return event_id
    
    def _op_object_transfer(
        self,
        theatre_id: uuid.UUID,
        tick_id: int,
        params: Dict,
        delta_id: str
    ) -> str:
        """Transfer an object to a new holder."""
        object_id = params["object_id"]
        new_holder_type = params["holder_type"]
        new_holder_id = params["holder_id"]
        
        obj = self.db.query(ObjectHolderCurrent).filter(
            ObjectHolderCurrent.theatre_id == theatre_id,
            ObjectHolderCurrent.object_id == object_id
        ).first()
        
        old_holder = {
            "holder_type": obj.holder_type if obj else None,
            "holder_id": obj.holder_id if obj else None
        }
        
        if obj:
            obj.holder_type = new_holder_type
            obj.holder_id = new_holder_id
        else:
            obj = ObjectHolderCurrent(
                theatre_id=theatre_id,
                object_id=object_id,
                holder_type=new_holder_type,
                holder_id=new_holder_id
            )
            self.db.add(obj)
        
        new_holder = {
            "holder_type": new_holder_type,
            "holder_id": new_holder_id
        }
        
        event_id = self._log_event(
            theatre_id, tick_id,
            event_type="object.holder.changed",
            payload={"object_id": object_id, "old": old_holder, "new": new_holder},
            delta_id=delta_id
        )
        return event_id
    
    # =========================================================================
    # Event Logging
    # =========================================================================
    def _log_event(
        self,
        theatre_id: uuid.UUID,
        tick_id: int,
        event_type: str,
        payload: Dict,
        delta_id: Optional[str] = None
    ) -> str:
        """Log an event to the append-only event log."""
        event = WorldEventLog(
            theatre_id=theatre_id,
            tick_id=tick_id,
            type=event_type,
            payload_jsonb=payload,
            delta_id=delta_id
        )
        self.db.add(event)
        self.db.flush()
        return str(event.event_id)
    
    def get_events(
        self,
        theatre_id: str,
        from_tick: Optional[int] = None,
        to_tick: Optional[int] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query events for a theatre."""
        theatre_uuid = uuid.UUID(theatre_id)
        
        query = self.db.query(WorldEventLog).filter(
            WorldEventLog.theatre_id == theatre_uuid
        )
        
        if from_tick is not None:
            query = query.filter(WorldEventLog.tick_id >= from_tick)
        if to_tick is not None:
            query = query.filter(WorldEventLog.tick_id <= to_tick)
        if event_type:
            query = query.filter(WorldEventLog.type == event_type)
        
        events = query.order_by(WorldEventLog.created_at.desc()).limit(limit).all()
        
        return [
            {
                "event_id": str(e.event_id),
                "tick_id": e.tick_id,
                "type": e.type,
                "payload": e.payload_jsonb,
                "delta_id": e.delta_id,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]
    
    # =========================================================================
    # Snapshot Management
    # =========================================================================
    def get_snapshot(self, theatre_id: str, tick_id: int) -> Optional[Dict]:
        """Get a specific snapshot for archaeology/replay."""
        theatre_uuid = uuid.UUID(theatre_id)
        
        snapshot = self.db.query(WorldStateSnapshot).filter(
            WorldStateSnapshot.theatre_id == theatre_uuid,
            WorldStateSnapshot.tick_id == tick_id
        ).first()
        
        if not snapshot:
            return None
        
        return {
            "theatre_id": str(snapshot.theatre_id),
            "tick_id": snapshot.tick_id,
            "version": snapshot.version,
            "state": snapshot.state_jsonb,
            "created_at": snapshot.created_at.isoformat()
        }
