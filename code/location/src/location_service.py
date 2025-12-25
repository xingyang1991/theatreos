"""
TheatreOS Location & Geofence Service
Handles Ring level determination, privacy protection, and risk assessment.

Key responsibilities:
- Evaluate user location against stages
- Determine Ring level (C/B/A)
- Issue short-lived ring tokens
- Protect user privacy
- Detect location spoofing/anomalies
"""
import json
import hashlib
import logging
import uuid
import math
import secrets
import hmac
import base64
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import (
    Theatre, get_db, Base, GUID, JSONType
)

# Import SQLAlchemy components for new models
from sqlalchemy import Column, String, Integer, BigInteger, Float, DateTime, Text, Boolean, ForeignKey, Numeric
from kernel.src.database import engine, SessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# Location Models (SQLite Compatible)
# =============================================================================
class Stage(Base):
    """Stage - a geographic anchor point for scenes."""
    __tablename__ = "stage"
    
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), primary_key=True)
    stage_id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    tags_jsonb = Column(JSONType, nullable=False, default=[])
    # For SQLite, store lat/lng separately instead of PostGIS geography
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geohash6 = Column(Text, nullable=True)
    ringc_m = Column(Integer, nullable=False)  # Ring C radius in meters
    ringb_m = Column(Integer, nullable=False)  # Ring B radius in meters
    ringa_m = Column(Integer, nullable=False)  # Ring A radius in meters
    safe_only = Column(Boolean, nullable=False, default=True)
    open_hours = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="OPEN")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class StageSafetyOverride(Base):
    """Safety override for stages (emergency lockdown)."""
    __tablename__ = "stage_safety_override"
    
    override_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), nullable=False)
    stage_id = Column(Text, nullable=False)
    ringa_enabled = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)
    operator = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class UserLocationSample(Base):
    """Coarse location sample for anti-cheat (privacy-preserving)."""
    __tablename__ = "user_location_sample"
    
    sample_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), nullable=False)
    geohash6 = Column(Text, nullable=False)
    accuracy_m = Column(Integer, nullable=False)
    speed_mps = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ttl_expires_at = Column(DateTime, nullable=False)


class LocationRiskFlag(Base):
    """Risk flag for location anomalies."""
    __tablename__ = "location_risk_flag"
    
    user_id = Column(Text, primary_key=True)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), primary_key=True)
    risk_level = Column(Text, nullable=False)  # LOW/MEDIUM/HIGH
    reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class RingAttestation(Base):
    """Short-lived ring level attestation (token)."""
    __tablename__ = "ring_attestation"
    
    attest_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(Text, nullable=True)
    stage_id = Column(Text, nullable=False)
    ring_level = Column(Text, nullable=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    risk_score = Column(Float, nullable=False, default=0)


# Create tables
Base.metadata.create_all(bind=engine)


# =============================================================================
# Configuration
# =============================================================================
RING_TOKEN_EXPIRY_SECONDS = 600  # 10 minutes
ACCURACY_THRESHOLD_RINGB = 50  # meters
ACCURACY_THRESHOLD_RINGA = 30  # meters
SPEED_THRESHOLD_MPS = 40  # m/s (suspicious if faster)
TIMESTAMP_TOLERANCE_SECONDS = 60
TOKEN_SECRET = os.getenv("RING_TOKEN_SECRET", "theatreos_ring_secret_key_change_in_production")


# =============================================================================
# Geohash Implementation (Simple)
# =============================================================================
GEOHASH_CHARS = "0123456789bcdefghjkmnpqrstuvwxyz"

def encode_geohash(lat: float, lng: float, precision: int = 6) -> str:
    """Encode lat/lng to geohash string."""
    lat_range = (-90.0, 90.0)
    lng_range = (-180.0, 180.0)
    
    geohash = []
    bits = 0
    bit_count = 0
    even = True
    
    while len(geohash) < precision:
        if even:
            mid = (lng_range[0] + lng_range[1]) / 2
            if lng >= mid:
                bits = bits * 2 + 1
                lng_range = (mid, lng_range[1])
            else:
                bits = bits * 2
                lng_range = (lng_range[0], mid)
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                bits = bits * 2 + 1
                lat_range = (mid, lat_range[1])
            else:
                bits = bits * 2
                lat_range = (lat_range[0], mid)
        
        even = not even
        bit_count += 1
        
        if bit_count == 5:
            geohash.append(GEOHASH_CHARS[bits])
            bits = 0
            bit_count = 0
    
    return "".join(geohash)


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula."""
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


# =============================================================================
# Data Transfer Objects
# =============================================================================
class LocationEvaluateRequest:
    def __init__(
        self,
        slot_id: str,
        lat: float,
        lng: float,
        accuracy_m: int,
        timestamp_ms: int,
        requested_stage_ids: List[str] = None
    ):
        self.slot_id = slot_id
        self.lat = lat
        self.lng = lng
        self.accuracy_m = accuracy_m
        self.timestamp_ms = timestamp_ms
        self.requested_stage_ids = requested_stage_ids or []


class RingEvaluation:
    def __init__(
        self,
        stage_id: str,
        ring_level: str,
        distance_m: float,
        token: str,
        expires_in_sec: int
    ):
        self.stage_id = stage_id
        self.ring_level = ring_level
        self.distance_m = distance_m
        self.token = token
        self.expires_in_sec = expires_in_sec
    
    def to_dict(self) -> Dict:
        return {
            "stage_id": self.stage_id,
            "ring_level": self.ring_level,
            "distance_m": round(self.distance_m, 1),
            "token": self.token,
            "expires_in_sec": self.expires_in_sec
        }


class LocationEvaluateResponse:
    def __init__(
        self,
        theatre_id: str,
        slot_id: str,
        rings: List[RingEvaluation],
        global_risk_level: str,
        degrade_reason: str = None
    ):
        self.theatre_id = theatre_id
        self.slot_id = slot_id
        self.rings = rings
        self.global_risk_level = global_risk_level
        self.degrade_reason = degrade_reason
    
    def to_dict(self) -> Dict:
        return {
            "theatre_id": self.theatre_id,
            "slot_id": self.slot_id,
            "rings": [r.to_dict() for r in self.rings],
            "global_risk_level": self.global_risk_level,
            "degrade_reason": self.degrade_reason
        }


# =============================================================================
# Location Service
# =============================================================================
class LocationService:
    """
    Location Service - Ring level determination with privacy protection.
    
    Handles:
    - Evaluating user location against stages
    - Determining appropriate Ring level
    - Issuing short-lived tokens
    - Detecting anomalies
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # Stage Management
    # =========================================================================
    def create_stage(
        self,
        theatre_id: str,
        stage_id: str,
        name: str,
        lat: float,
        lng: float,
        ringc_m: int = 1000,
        ringb_m: int = 300,
        ringa_m: int = 50,
        tags: List[str] = None,
        safe_only: bool = True
    ) -> Stage:
        """Create a new stage (geographic anchor)."""
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Check if exists
        existing = self.db.query(Stage).filter(
            Stage.theatre_id == theatre_uuid,
            Stage.stage_id == stage_id
        ).first()
        
        if existing:
            return existing
        
        stage = Stage(
            theatre_id=theatre_uuid,
            stage_id=stage_id,
            name=name,
            latitude=lat,
            longitude=lng,
            geohash6=encode_geohash(lat, lng, 6),
            ringc_m=ringc_m,
            ringb_m=ringb_m,
            ringa_m=ringa_m,
            tags_jsonb=tags or [],
            safe_only=safe_only
        )
        
        self.db.add(stage)
        self.db.commit()
        
        logger.info(f"Created stage {stage_id} at ({lat}, {lng})")
        return stage
    
    def get_stages_nearby(
        self,
        theatre_id: str,
        lat: float,
        lng: float,
        radius_m: int = 5000
    ) -> List[Dict]:
        """Get stages within radius (for showbill/recommendations)."""
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Get all stages for theatre
        stages = self.db.query(Stage).filter(
            Stage.theatre_id == theatre_uuid,
            Stage.status == "OPEN"
        ).all()
        
        # Filter by distance
        nearby = []
        for stage in stages:
            distance = haversine_distance(lat, lng, stage.latitude, stage.longitude)
            if distance <= radius_m:
                nearby.append({
                    "stage_id": stage.stage_id,
                    "name": stage.name,
                    "tags": stage.tags_jsonb,
                    "distance_m": round(distance, 1),
                    "geohash6": stage.geohash6,
                    "status": stage.status
                })
        
        # Sort by distance
        nearby.sort(key=lambda x: x["distance_m"])
        return nearby
    
    # =========================================================================
    # Ring Evaluation
    # =========================================================================
    def evaluate_ring(
        self,
        theatre_id: str,
        user_id: str,
        request: LocationEvaluateRequest
    ) -> LocationEvaluateResponse:
        """
        Evaluate user's ring level for requested stages.
        
        This is the core location evaluation logic:
        1. Validate timestamp
        2. Check accuracy
        3. Calculate distance to each stage
        4. Determine ring level
        5. Check safety overrides
        6. Assess risk
        7. Issue tokens
        """
        theatre_uuid = uuid.UUID(theatre_id)
        
        # 1. Validate timestamp
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        time_diff_sec = abs(now_ms - request.timestamp_ms) / 1000
        
        risk_level = "LOW"
        degrade_reason = None
        
        if time_diff_sec > TIMESTAMP_TOLERANCE_SECONDS:
            risk_level = "MEDIUM"
            degrade_reason = "Timestamp out of tolerance"
        
        # 2. Check accuracy
        if request.accuracy_m > 80:
            risk_level = "MEDIUM"
            degrade_reason = "Low GPS accuracy"
        
        # 3. Check for speed anomalies
        speed_risk = self._check_speed_anomaly(theatre_uuid, user_id, request)
        if speed_risk:
            risk_level = "HIGH"
            degrade_reason = speed_risk
        
        # 4. Get requested stages or nearby stages
        if request.requested_stage_ids:
            stages = self.db.query(Stage).filter(
                Stage.theatre_id == theatre_uuid,
                Stage.stage_id.in_(request.requested_stage_ids),
                Stage.status == "OPEN"
            ).all()
        else:
            # Get nearby stages
            all_stages = self.db.query(Stage).filter(
                Stage.theatre_id == theatre_uuid,
                Stage.status == "OPEN"
            ).all()
            stages = [s for s in all_stages 
                     if haversine_distance(request.lat, request.lng, s.latitude, s.longitude) <= s.ringc_m]
        
        # 5. Evaluate each stage
        rings = []
        for stage in stages:
            distance = haversine_distance(request.lat, request.lng, stage.latitude, stage.longitude)
            
            # Determine ring level
            ring_level = self._determine_ring_level(
                stage=stage,
                distance_m=distance,
                accuracy_m=request.accuracy_m,
                risk_level=risk_level,
                theatre_id=theatre_uuid
            )
            
            # Issue token
            token = self._issue_ring_token(
                theatre_id=theatre_id,
                user_id=user_id,
                slot_id=request.slot_id,
                stage_id=stage.stage_id,
                ring_level=ring_level
            )
            
            rings.append(RingEvaluation(
                stage_id=stage.stage_id,
                ring_level=ring_level,
                distance_m=distance,
                token=token,
                expires_in_sec=RING_TOKEN_EXPIRY_SECONDS
            ))
        
        # 6. Record location sample (coarse, for anti-cheat)
        self._record_location_sample(theatre_uuid, user_id, request)
        
        # 7. Update risk flag if needed
        if risk_level != "LOW":
            self._update_risk_flag(theatre_uuid, user_id, risk_level, degrade_reason)
        
        return LocationEvaluateResponse(
            theatre_id=theatre_id,
            slot_id=request.slot_id,
            rings=rings,
            global_risk_level=risk_level,
            degrade_reason=degrade_reason
        )
    
    def _determine_ring_level(
        self,
        stage: Stage,
        distance_m: float,
        accuracy_m: int,
        risk_level: str,
        theatre_id: uuid.UUID
    ) -> str:
        """Determine the appropriate ring level based on distance and conditions."""
        # Check safety override
        override = self.db.query(StageSafetyOverride).filter(
            StageSafetyOverride.theatre_id == theatre_id,
            StageSafetyOverride.stage_id == stage.stage_id,
            or_(
                StageSafetyOverride.expires_at.is_(None),
                StageSafetyOverride.expires_at > datetime.utcnow()
            )
        ).order_by(StageSafetyOverride.created_at.desc()).first()
        
        ringa_enabled = override.ringa_enabled if override else True
        
        # High risk always degrades to C
        if risk_level == "HIGH":
            return "C"
        
        # Check Ring A
        if distance_m <= stage.ringa_m:
            if accuracy_m <= ACCURACY_THRESHOLD_RINGA and ringa_enabled and stage.safe_only:
                return "A"
            elif accuracy_m <= ACCURACY_THRESHOLD_RINGB:
                return "B"
            else:
                return "C"
        
        # Check Ring B
        if distance_m <= stage.ringb_m:
            if accuracy_m <= ACCURACY_THRESHOLD_RINGB:
                return "B"
            else:
                return "C"
        
        # Check Ring C
        if distance_m <= stage.ringc_m:
            return "C"
        
        # Outside all rings
        return "C"
    
    def _check_speed_anomaly(
        self,
        theatre_id: uuid.UUID,
        user_id: str,
        request: LocationEvaluateRequest
    ) -> Optional[str]:
        """Check for suspicious movement speed."""
        # Get last location sample
        last_sample = self.db.query(UserLocationSample).filter(
            UserLocationSample.theatre_id == theatre_id,
            UserLocationSample.user_id == user_id
        ).order_by(UserLocationSample.created_at.desc()).first()
        
        if not last_sample:
            return None
        
        # Calculate time difference
        sample_time = last_sample.created_at.replace(tzinfo=timezone.utc)
        request_time = datetime.fromtimestamp(request.timestamp_ms / 1000, tz=timezone.utc)
        time_diff_sec = (request_time - sample_time).total_seconds()
        
        if time_diff_sec <= 0:
            return None
        
        # Estimate distance from geohash (rough)
        # For more accurate check, we'd need to decode the geohash
        current_geohash = encode_geohash(request.lat, request.lng, 6)
        
        if current_geohash[:4] != last_sample.geohash6[:4]:
            # Moved more than ~20km (geohash4 cell), check speed
            # Rough estimate: geohash6 cell is ~1km
            estimated_distance = 5000  # Conservative estimate
            speed = estimated_distance / time_diff_sec
            
            if speed > SPEED_THRESHOLD_MPS:
                return f"Suspicious speed: {speed:.1f} m/s"
        
        return None
    
    def _record_location_sample(
        self,
        theatre_id: uuid.UUID,
        user_id: str,
        request: LocationEvaluateRequest
    ):
        """Record coarse location sample for anti-cheat (privacy-preserving)."""
        # Get previous sample to calculate speed
        last_sample = self.db.query(UserLocationSample).filter(
            UserLocationSample.theatre_id == theatre_id,
            UserLocationSample.user_id == user_id
        ).order_by(UserLocationSample.created_at.desc()).first()
        
        speed_mps = 0.0
        if last_sample:
            # Rough speed estimate
            time_diff = (datetime.utcnow() - last_sample.created_at).total_seconds()
            if time_diff > 0:
                # Estimate from geohash change
                speed_mps = 0  # Would need proper calculation
        
        sample = UserLocationSample(
            user_id=user_id,
            theatre_id=theatre_id,
            geohash6=encode_geohash(request.lat, request.lng, 6),
            accuracy_m=request.accuracy_m,
            speed_mps=speed_mps,
            ttl_expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.db.add(sample)
        self.db.commit()
    
    def _update_risk_flag(
        self,
        theatre_id: uuid.UUID,
        user_id: str,
        risk_level: str,
        reason: str
    ):
        """Update user's location risk flag."""
        flag = self.db.query(LocationRiskFlag).filter(
            LocationRiskFlag.theatre_id == theatre_id,
            LocationRiskFlag.user_id == user_id
        ).first()
        
        if flag:
            flag.risk_level = risk_level
            flag.reason = reason
            flag.updated_at = datetime.utcnow()
        else:
            flag = LocationRiskFlag(
                user_id=user_id,
                theatre_id=theatre_id,
                risk_level=risk_level,
                reason=reason
            )
            self.db.add(flag)
        
        self.db.commit()
    
    # =========================================================================
    # Token Management
    # =========================================================================
    def _issue_ring_token(
        self,
        theatre_id: str,
        user_id: str,
        slot_id: str,
        stage_id: str,
        ring_level: str
    ) -> str:
        """Issue a short-lived ring attestation token."""
        theatre_uuid = uuid.UUID(theatre_id)
        expires_at = datetime.utcnow() + timedelta(seconds=RING_TOKEN_EXPIRY_SECONDS)
        
        # Create attestation record
        attestation = RingAttestation(
            user_id=user_id,
            theatre_id=theatre_uuid,
            slot_id=slot_id,
            stage_id=stage_id,
            ring_level=ring_level,
            expires_at=expires_at
        )
        
        self.db.add(attestation)
        self.db.commit()
        
        # Generate signed token
        token_data = f"{attestation.attest_id}:{user_id}:{stage_id}:{ring_level}:{int(expires_at.timestamp())}"
        signature = hmac.new(
            TOKEN_SECRET.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        token = f"rtk_{base64.urlsafe_b64encode(token_data.encode()).decode()}_{signature}"
        return token
    
    def verify_ring_token(self, token: str) -> Optional[Dict]:
        """Verify a ring token and return its claims if valid."""
        try:
            if not token.startswith("rtk_"):
                return None
            
            parts = token[4:].rsplit("_", 1)
            if len(parts) != 2:
                return None
            
            token_data = base64.urlsafe_b64decode(parts[0]).decode()
            provided_sig = parts[1]
            
            # Verify signature
            expected_sig = hmac.new(
                TOKEN_SECRET.encode(),
                token_data.encode(),
                hashlib.sha256
            ).hexdigest()[:16]
            
            if not hmac.compare_digest(provided_sig, expected_sig):
                return None
            
            # Parse token data
            attest_id, user_id, stage_id, ring_level, expires_ts = token_data.split(":")
            expires_at = datetime.fromtimestamp(int(expires_ts), tz=timezone.utc)
            
            # Check expiry
            if datetime.now(timezone.utc) > expires_at:
                return None
            
            return {
                "attest_id": attest_id,
                "user_id": user_id,
                "stage_id": stage_id,
                "ring_level": ring_level,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    # =========================================================================
    # Safety Override Management
    # =========================================================================
    def set_safety_override(
        self,
        theatre_id: str,
        stage_id: str,
        ringa_enabled: bool,
        reason: str,
        operator: str,
        expires_hours: int = None
    ) -> StageSafetyOverride:
        """Set a safety override for a stage (emergency lockdown)."""
        theatre_uuid = uuid.UUID(theatre_id)
        
        override = StageSafetyOverride(
            theatre_id=theatre_uuid,
            stage_id=stage_id,
            ringa_enabled=ringa_enabled,
            reason=reason,
            operator=operator,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours) if expires_hours else None
        )
        
        self.db.add(override)
        self.db.commit()
        
        action = "enabled" if ringa_enabled else "disabled"
        logger.info(f"Safety override: Ring A {action} for stage {stage_id} by {operator}")
        return override
