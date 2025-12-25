"""
TheatreOS Database Connection - SQLite Version for Demo
This version uses SQLite for easy local testing without PostgreSQL.
"""
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Generator
import uuid

from sqlalchemy import create_engine, Column, String, Integer, BigInteger, Float, DateTime, Text, Boolean, ForeignKey, Index, CheckConstraint, event
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import json

# Add config to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Use SQLite for demo
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./theatreos_demo.db")

# =============================================================================
# Custom Types for SQLite Compatibility
# =============================================================================
class GUID(TypeDecorator):
    """Platform-independent GUID type using CHAR(36) for SQLite."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class JSONType(TypeDecorator):
    """JSON type that works with SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


# =============================================================================
# Database Engine and Session
# =============================================================================
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a new database session (for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Kernel Models (Theatre, WorldState, Events)
# =============================================================================
class Theatre(Base):
    """Theatre instance - represents a city's theatre with its world state."""
    __tablename__ = "theatre"
    
    theatre_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    city = Column(Text, nullable=False)
    timezone = Column(Text, nullable=False, default="Asia/Shanghai")
    theme_id = Column(Text, nullable=False)
    theme_version = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    world_vars = relationship("WorldVarCurrent", back_populates="theatre", cascade="all, delete-orphan")
    thread_states = relationship("ThreadStateCurrent", back_populates="theatre", cascade="all, delete-orphan")
    object_holders = relationship("ObjectHolderCurrent", back_populates="theatre", cascade="all, delete-orphan")


class WorldVarCurrent(Base):
    """Current value of a world variable (0-1 range)."""
    __tablename__ = "world_var_current"
    
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), primary_key=True)
    var_id = Column(Text, primary_key=True)
    value = Column(Float, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    theatre = relationship("Theatre", back_populates="world_vars")


class ThreadStateCurrent(Base):
    """Current state of a narrative thread."""
    __tablename__ = "thread_state_current"
    
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), primary_key=True)
    thread_id = Column(Text, primary_key=True)
    phase_id = Column(Text, nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    branch_bucket = Column(Text, nullable=False)
    locks_jsonb = Column(JSONType, nullable=False, default={})
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    theatre = relationship("Theatre", back_populates="thread_states")


class ObjectHolderCurrent(Base):
    """Current holder of a key object in the world."""
    __tablename__ = "object_holder_current"
    
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), primary_key=True)
    object_id = Column(Text, primary_key=True)
    holder_type = Column(Text, nullable=False)
    holder_id = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    theatre = relationship("Theatre", back_populates="object_holders")


class WorldStateSnapshot(Base):
    """Snapshot of world state at a specific tick."""
    __tablename__ = "world_state_snapshot"
    
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), primary_key=True)
    tick_id = Column(BigInteger, primary_key=True)
    version = Column(BigInteger, nullable=False)
    state_jsonb = Column(JSONType, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class WorldEventLog(Base):
    """Append-only event log for all world state changes."""
    __tablename__ = "world_event_log"
    
    event_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), nullable=False)
    tick_id = Column(BigInteger, nullable=False)
    type = Column(Text, nullable=False)
    payload_jsonb = Column(JSONType, nullable=False)
    delta_id = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class WorldDeltaIdempotency(Base):
    """Idempotency tracking for ApplyDelta operations."""
    __tablename__ = "world_delta_idempotency"
    
    delta_id = Column(Text, primary_key=True)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), nullable=False)
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    result_hash = Column(Text, nullable=False)


# =============================================================================
# Scheduler Models (HourPlan, Slots)
# =============================================================================
class HourPlan(Base):
    """Hour plan - the schedule for a specific time slot."""
    __tablename__ = "hour_plan"
    
    slot_id = Column(Text, primary_key=True)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), nullable=False)
    start_at = Column(DateTime, nullable=False)
    scenes_parallel = Column(Integer, nullable=False, default=8)
    primary_thread = Column(Text, nullable=True)
    support_threads_jsonb = Column(JSONType, nullable=False, default=[])
    target_beat_mix_jsonb = Column(JSONType, nullable=False, default={})
    hour_gate_jsonb = Column(JSONType, nullable=False, default={})
    must_drop_jsonb = Column(JSONType, nullable=False, default=[])
    status = Column(Text, nullable=False, default="SCHEDULED")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class HourPlanOverride(Base):
    """Manual override for hour plans by operators."""
    __tablename__ = "hour_plan_override"
    
    override_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    slot_id = Column(Text, ForeignKey("hour_plan.slot_id", ondelete="CASCADE"), nullable=False)
    theatre_id = Column(GUID(), nullable=False)
    override_jsonb = Column(JSONType, nullable=False)
    reason = Column(Text, nullable=True)
    operator = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PublishedSlot(Base):
    """Published slot content - the final deliverable to clients."""
    __tablename__ = "published_slot"
    
    theatre_id = Column(GUID(), primary_key=True)
    slot_id = Column(Text, primary_key=True)
    publish_version = Column(Integer, nullable=False, default=1)
    payload_jsonb = Column(JSONType, nullable=False)
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    source_job_id = Column(Text, nullable=True)


# =============================================================================
# Database Initialization
# =============================================================================
def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


def drop_db():
    """Drop all database tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped.")


if __name__ == "__main__":
    init_db()
