"""
TheatreOS API Gateway
FastAPI application providing REST API for TheatreOS.

M1 Endpoints:
- Theatre management
- World state queries
- Showbill (戏单)
- Slot details
- Gate System (投票/下注/结算)
- Location & Geofence (定位与围栏)
- Demo tick execution
"""
import logging
import sys
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import API_HOST, API_PORT, DEBUG, LOG_LEVEL, LOG_FORMAT
from config.service_registry import get_service, TRACE_SERVICE, CREW_SERVICE
from kernel.src.database import get_db_session, init_db, Theatre, HourPlan
from kernel.src.kernel_service import KernelService, ApplyDeltaRequest, WorldState
from scheduler.src.scheduler_service import SchedulerService
from gateway.src.scene_delivery import SceneDeliveryService, StaticContentGenerator
from trace.src.trace_service import TraceService
from crew.src.crew_service import CrewService
from auth.src.auth_service import get_auth_service, UserRole
from auth.src.middleware import (
    get_current_user, require_auth, require_player, 
    require_moderator, require_operator, require_admin, AuthContext
)
from gateway.src.auth_routes import router as auth_router
from gateway.src.realtime_routes import router as realtime_router
from gateway.src.storage_routes import router as storage_router

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models (Request/Response)
# =============================================================================

# --- Theatre ---
class CreateTheatreRequest(BaseModel):
    city: str = Field(..., description="City name")
    theme_id: str = Field(default="hp_shanghai_s1", description="Theme pack ID")
    theme_version: str = Field(default="1.0.0", description="Theme pack version")
    timezone: str = Field(default="Asia/Shanghai", description="Timezone")
    initial_vars: Optional[Dict[str, float]] = Field(default=None, description="Initial world variables")
    initial_threads: Optional[List[Dict]] = Field(default=None, description="Initial narrative threads")


class TheatreResponse(BaseModel):
    theatre_id: str
    city: str
    timezone: str
    theme_id: str
    theme_version: str
    status: str
    created_at: str


# --- World State ---
class WorldStateResponse(BaseModel):
    theatre_id: str
    tick_id: int
    version: int
    vars: Dict[str, float]
    threads: Dict[str, Dict]
    objects: Dict[str, Dict]


# --- Apply Delta ---
class ApplyDeltaRequestModel(BaseModel):
    delta_id: str = Field(..., description="Unique delta identifier for idempotency")
    expected_version: int = Field(..., description="Expected current version")
    source: Dict[str, str] = Field(..., description="Source of the delta (e.g., gate_id)")
    ops: List[Dict] = Field(..., description="List of operations to apply")


class ApplyDeltaResponse(BaseModel):
    applied: bool
    new_version: int
    tick_id: int
    event_ids: List[str]
    error: Optional[str] = None


# --- Showbill ---
class SlotSummary(BaseModel):
    slot_id: str
    start_at_ms: int
    end_at_ms: int
    theatre_mode: str
    gate_type: str
    scenes_parallel: int
    published: bool


class ShowbillResponse(BaseModel):
    theatre_id: str
    now_ms: int
    slots: List[SlotSummary]


# --- Slot Detail ---
class SceneSummary(BaseModel):
    scene_id: str
    stage_id: str
    ring_min: str
    media_level: str
    title: Optional[str] = None
    locked: Optional[bool] = None
    unlock_hint: Optional[str] = None
    scene_text: Optional[str] = None
    media_urls: Optional[Dict[str, str]] = None
    evidence_outputs: Optional[List[Dict]] = None


class SlotDetailResponse(BaseModel):
    slot_id: str
    theatre_id: str
    publish_version: int
    scenes: List[SceneSummary]
    gate_instance_id: str
    notes: Optional[str] = None


# --- Demo/Admin ---
class RunTickResponse(BaseModel):
    theatre_id: str
    tick_id: int
    version: int
    message: str


class GeneratePlanResponse(BaseModel):
    slot_id: str
    theatre_id: str
    start_at: str
    scenes_parallel: int
    primary_thread: Optional[str]
    gate_type: str
    status: str


class PublishSlotResponse(BaseModel):
    slot_id: str
    theatre_id: str
    publish_version: int
    scenes_count: int
    message: str


# --- Gate System ---
class GateLobbyResponse(BaseModel):
    gate_instance_id: str
    slot_id: str
    type: str
    status: str
    title: str
    options: List[Dict]
    vote_distribution: Dict[str, str]
    open_at_ms: int
    close_at_ms: int
    resolve_at_ms: int
    is_open: bool
    winner_option_id: Optional[str] = None
    explain_card: Optional[Dict] = None


class VoteRequestModel(BaseModel):
    option_id: str = Field(..., description="Option to vote for")
    ring_level: str = Field(default="C", description="User's ring level")


class VoteResponse(BaseModel):
    success: bool
    message: str
    vote_id: Optional[str] = None


class StakeRequestModel(BaseModel):
    option_id: str = Field(..., description="Option to stake on")
    currency: str = Field(default="SHARD", description="Currency to stake")
    amount: float = Field(..., gt=0, description="Amount to stake")
    ring_level: str = Field(default="C", description="User's ring level")


class StakeResponse(BaseModel):
    success: bool
    message: str
    amount_locked: Optional[float] = None


class ResolveResponse(BaseModel):
    success: bool
    winner_option_id: Optional[str] = None
    explain_card: Optional[Dict] = None
    error: Optional[str] = None


class WalletBalanceResponse(BaseModel):
    user_id: str
    balances: Dict[str, float]


# --- Location System ---
class RingEvaluateRequestModel(BaseModel):
    slot_id: str = Field(..., description="Current slot ID")
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    accuracy_m: int = Field(..., description="GPS accuracy in meters")
    timestamp_ms: int = Field(..., description="Location timestamp in milliseconds")
    requested_stage_ids: Optional[List[str]] = Field(default=None, description="Specific stages to evaluate")


class RingEvaluationItem(BaseModel):
    stage_id: str
    ring_level: str
    distance_m: float
    token: str
    expires_in_sec: int


class RingEvaluateResponse(BaseModel):
    theatre_id: str
    slot_id: str
    rings: List[RingEvaluationItem]
    global_risk_level: str
    degrade_reason: Optional[str] = None


class NearbyStageItem(BaseModel):
    stage_id: str
    name: str
    tags: List[str]
    distance_m: float
    geohash6: str
    status: str


class NearbyStagesResponse(BaseModel):
    theatre_id: str
    stages: List[NearbyStageItem]


class CreateStageRequest(BaseModel):
    stage_id: str = Field(..., description="Unique stage ID")
    name: str = Field(..., description="Stage name")
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    ringc_m: int = Field(default=1000, description="Ring C radius in meters")
    ringb_m: int = Field(default=300, description="Ring B radius in meters")
    ringa_m: int = Field(default=50, description="Ring A radius in meters")
    tags: Optional[List[str]] = Field(default=None, description="Stage tags")
    safe_only: bool = Field(default=True, description="Only allow Ring A in safe areas")


class StageResponse(BaseModel):
    theatre_id: str
    stage_id: str
    name: str
    latitude: float
    longitude: float
    ringc_m: int
    ringb_m: int
    ringa_m: int
    status: str


# =============================================================================
# Application Lifecycle
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("TheatreOS API Gateway starting...")
    # Initialize database tables
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization note: {e}")
    yield
    logger.info("TheatreOS API Gateway shutting down...")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="TheatreOS API",
    description="TheatreOS M1 - Core Engine API with Gate and Location Systems",
    version="1.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Auth routes
app.include_router(auth_router)

# Register Realtime routes
app.include_router(realtime_router)

# Register Storage routes
app.include_router(storage_router)

# Register Data Pack routes
try:
    from gateway.src.datapack_routes import router as datapack_router
    app.include_router(datapack_router)
    logger.info("Data pack routes registered successfully")
except ImportError as e:
    logger.info(f"Data pack routes not available: {e}")

# Register Slot & Showbill routes
try:
    from gateway.src.slot_routes import router as slot_router
    app.include_router(slot_router)
    logger.info("Slot routes registered successfully")
except ImportError as e:
    logger.warning(f"Slot routes not available: {e}")

# Register Gate routes
try:
    from gateway.src.gate_routes import router as gate_router
    app.include_router(gate_router)
    logger.info("Gate routes registered successfully")
except ImportError as e:
    logger.warning(f"Gate routes not available: {e}")

# Register Evidence routes
try:
    from gateway.src.evidence_routes import router as evidence_router
    app.include_router(evidence_router)
    logger.info("Evidence routes registered successfully")
except ImportError as e:
    logger.warning(f"Evidence routes not available: {e}")

# Register Archive routes
try:
    from gateway.src.archive_routes import router as archive_router
    app.include_router(archive_router)
    logger.info("Archive routes registered successfully")
except ImportError as e:
    logger.warning(f"Archive routes not available: {e}")

# Register Test Mode routes (if available)
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from test_mode import test_router
    app.include_router(test_router, prefix="/v1")
    logger.info("Test mode routes registered successfully")
except ImportError as e:
    logger.info(f"Test mode not available: {e}")


# =============================================================================
# Health Check
# =============================================================================
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "TheatreOS API Gateway",
        "version": "M1.1",
        "systems": ["Kernel", "Scheduler", "SceneDelivery", "Gate", "Location", "Auth"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# Theatre Endpoints
# =============================================================================
@app.post("/v1/theatres", response_model=TheatreResponse, tags=["Theatre"])
async def create_theatre(
    request: CreateTheatreRequest,
    db: Session = Depends(get_db_session)
):
    """Create a new theatre instance."""
    kernel = KernelService(db)
    
    # Default initial state if not provided
    initial_vars = request.initial_vars or {
        "tension": 0.5,
        "mystery": 0.6,
        "trust_authority": 0.4,
        "chaos": 0.3
    }
    
    initial_threads = request.initial_threads or [
        {"thread_id": "thread_01", "phase_id": "phase_1", "progress": 0, "branch_bucket": "main"},
        {"thread_id": "thread_02", "phase_id": "phase_1", "progress": 0, "branch_bucket": "main"},
        {"thread_id": "thread_03", "phase_id": "phase_1", "progress": 0, "branch_bucket": "main"}
    ]
    
    theatre = kernel.create_theatre(
        city=request.city,
        theme_id=request.theme_id,
        theme_version=request.theme_version,
        timezone_str=request.timezone,
        initial_vars=initial_vars,
        initial_threads=initial_threads
    )
    
    return TheatreResponse(
        theatre_id=str(theatre.theatre_id),
        city=theatre.city,
        timezone=theatre.timezone,
        theme_id=theatre.theme_id,
        theme_version=theatre.theme_version,
        status=theatre.status,
        created_at=theatre.created_at.isoformat()
    )


@app.get("/v1/theatres/{theatre_id}", response_model=TheatreResponse, tags=["Theatre"])
async def get_theatre(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get theatre details."""
    kernel = KernelService(db)
    theatre = kernel.get_theatre(theatre_id)
    
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")
    
    return TheatreResponse(
        theatre_id=str(theatre.theatre_id),
        city=theatre.city,
        timezone=theatre.timezone,
        theme_id=theatre.theme_id,
        theme_version=theatre.theme_version,
        status=theatre.status,
        created_at=theatre.created_at.isoformat()
    )


# =============================================================================
# World State Endpoints
# =============================================================================
@app.get("/v1/theatres/{theatre_id}/world", response_model=WorldStateResponse, tags=["World State"])
async def get_world_state(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get current world state for a theatre."""
    kernel = KernelService(db)
    world_state = kernel.get_world_state(theatre_id)
    
    if not world_state:
        raise HTTPException(status_code=404, detail="Theatre not found")
    
    return WorldStateResponse(
        theatre_id=world_state.theatre_id,
        tick_id=world_state.tick_id,
        version=world_state.version,
        vars=world_state.vars,
        threads=world_state.threads,
        objects=world_state.objects
    )


@app.post("/v1/theatres/{theatre_id}/world/delta", response_model=ApplyDeltaResponse, tags=["World State"])
async def apply_delta(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: ApplyDeltaRequestModel = Body(...),
    db: Session = Depends(get_db_session)
):
    """Apply a delta to the world state (idempotent)."""
    kernel = KernelService(db)
    
    delta_request = ApplyDeltaRequest(
        delta_id=request.delta_id,
        expected_version=request.expected_version,
        source=request.source,
        ops=request.ops
    )
    
    result = kernel.apply_delta(theatre_id, delta_request)
    
    if result.error == "VERSION_CONFLICT":
        raise HTTPException(status_code=409, detail="Version conflict - world state has changed")
    elif result.error == "THEATRE_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Theatre not found")
    
    return ApplyDeltaResponse(
        applied=result.applied,
        new_version=result.new_version,
        tick_id=result.tick_id,
        event_ids=result.event_ids,
        error=result.error
    )


@app.get("/v1/theatres/{theatre_id}/events", tags=["World State"])
async def get_events(
    theatre_id: str = Path(..., description="Theatre ID"),
    from_tick: Optional[int] = Query(None, description="Start tick ID"),
    to_tick: Optional[int] = Query(None, description="End tick ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, le=1000, description="Maximum events to return"),
    db: Session = Depends(get_db_session)
):
    """Query world events for a theatre."""
    kernel = KernelService(db)
    events = kernel.get_events(
        theatre_id=theatre_id,
        from_tick=from_tick,
        to_tick=to_tick,
        event_type=event_type,
        limit=limit
    )
    
    return {"theatre_id": theatre_id, "events": events}


# =============================================================================
# Showbill & Slot Endpoints
# =============================================================================
@app.get("/v1/theatres/{theatre_id}/slots/next", response_model=ShowbillResponse, tags=["Showbill"])
async def get_showbill(
    theatre_id: str = Path(..., description="Theatre ID"),
    hours: int = Query(2, ge=1, le=24, description="Hours to look ahead"),
    db: Session = Depends(get_db_session)
):
    """Get upcoming slots (showbill/戏单)."""
    delivery = SceneDeliveryService(db)
    showbill = delivery.get_showbill(theatre_id, hours)
    
    return ShowbillResponse(
        theatre_id=showbill["theatre_id"],
        now_ms=showbill["now_ms"],
        slots=[SlotSummary(**s) for s in showbill["slots"]]
    )


@app.get("/v1/slots/{slot_id}", response_model=SlotDetailResponse, tags=["Showbill"])
async def get_slot_detail(
    slot_id: str = Path(..., description="Slot ID"),
    ring_level: str = Query("C", description="User's ring level (C/B/A)"),
    db: Session = Depends(get_db_session)
):
    """Get slot details with ring-based content filtering."""
    delivery = SceneDeliveryService(db)
    detail = delivery.get_slot_detail(slot_id, ring_level)
    
    if not detail:
        raise HTTPException(status_code=404, detail="Slot not found or not published")
    
    return SlotDetailResponse(
        slot_id=detail["slot_id"],
        theatre_id=detail["theatre_id"],
        publish_version=detail["publish_version"],
        scenes=[SceneSummary(**s) for s in detail["scenes"]],
        gate_instance_id=detail["gate_instance_id"],
        notes=detail.get("notes")
    )


# =============================================================================
# Gate System Endpoints
# =============================================================================
@app.get("/v1/gates/{gate_instance_id}", response_model=GateLobbyResponse, tags=["Gate"])
async def get_gate_lobby(
    gate_instance_id: str = Path(..., description="Gate instance ID"),
    db: Session = Depends(get_db_session)
):
    """Get gate lobby information (options, countdown, status)."""
    from gate.src.gate_service import GateService
    
    gate_service = GateService(db)
    lobby = gate_service.get_gate_lobby(gate_instance_id)
    
    if "error" in lobby:
        raise HTTPException(status_code=404, detail=lobby["error"])
    
    return GateLobbyResponse(**lobby)


@app.post("/v1/gates/{gate_instance_id}/vote", response_model=VoteResponse, tags=["Gate"])
async def submit_vote(
    gate_instance_id: str = Path(..., description="Gate instance ID"),
    request: VoteRequestModel = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    x_idempotency_key: str = Header(None, alias="Idempotency-Key", description="Idempotency key"),
    db: Session = Depends(get_db_session)
):
    """Submit or update a vote for a gate."""
    from gate.src.gate_service import GateService, VoteRequest
    
    gate_service = GateService(db)
    vote_request = VoteRequest(
        option_id=request.option_id,
        ring_level=request.ring_level,
        idempotency_key=x_idempotency_key
    )
    
    result = gate_service.submit_vote(gate_instance_id, x_user_id, vote_request)
    
    return VoteResponse(
        success=result.success,
        message=result.message,
        vote_id=result.vote_id
    )


@app.post("/v1/gates/{gate_instance_id}/stake", response_model=StakeResponse, tags=["Gate"])
async def submit_stake(
    gate_instance_id: str = Path(..., description="Gate instance ID"),
    request: StakeRequestModel = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    x_idempotency_key: str = Header(None, alias="Idempotency-Key", description="Idempotency key"),
    db: Session = Depends(get_db_session)
):
    """Submit or increase a stake for a gate."""
    from gate.src.gate_service import GateService, StakeRequest
    
    gate_service = GateService(db)
    stake_request = StakeRequest(
        option_id=request.option_id,
        currency=request.currency,
        amount=Decimal(str(request.amount)),
        ring_level=request.ring_level,
        idempotency_key=x_idempotency_key
    )
    
    result = gate_service.submit_stake(gate_instance_id, x_user_id, stake_request)
    
    return StakeResponse(
        success=result.success,
        message=result.message,
        amount_locked=float(result.amount_locked) if result.amount_locked else None
    )


@app.get("/v1/gates/{gate_instance_id}/result", tags=["Gate"])
async def get_gate_result(
    gate_instance_id: str = Path(..., description="Gate instance ID"),
    db: Session = Depends(get_db_session)
):
    """Get gate result and Explain Card after resolution."""
    from gate.src.gate_service import GateService
    
    gate_service = GateService(db)
    gate = gate_service.get_gate_instance(gate_instance_id)
    
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    if gate.status != "RESOLVED":
        raise HTTPException(status_code=400, detail=f"Gate not yet resolved (status: {gate.status})")
    
    return {
        "gate_instance_id": str(gate.gate_instance_id),
        "winner_option_id": gate.winner_option_id,
        "explain_card": gate.explain_card_jsonb,
        "resolved_at": gate.updated_at.isoformat()
    }


@app.post("/v1/internal/gates/{gate_instance_id}/resolve", response_model=ResolveResponse, tags=["Gate Internal"])
async def resolve_gate(
    gate_instance_id: str = Path(..., description="Gate instance ID"),
    db: Session = Depends(get_db_session)
):
    """Internal: Resolve a gate (called by scheduler/cron)."""
    from gate.src.gate_service import GateService
    
    gate_service = GateService(db)
    result = gate_service.resolve_gate(gate_instance_id)
    
    return ResolveResponse(
        success=result.success,
        winner_option_id=result.winner_option_id,
        explain_card=result.explain_card,
        error=result.error
    )


@app.get("/v1/users/{user_id}/wallet", response_model=WalletBalanceResponse, tags=["Gate"])
async def get_wallet_balance(
    user_id: str = Path(..., description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Get user's wallet balances."""
    from gate.src.gate_service import WalletBalance
    
    balances = db.query(WalletBalance).filter(WalletBalance.user_id == user_id).all()
    
    return WalletBalanceResponse(
        user_id=user_id,
        balances={b.currency: float(b.balance) for b in balances}
    )


@app.post("/v1/admin/users/{user_id}/grant", tags=["Admin"])
async def grant_initial_balance(
    user_id: str = Path(..., description="User ID"),
    currency: str = Query(default="SHARD", description="Currency to grant"),
    amount: float = Query(default=100, description="Amount to grant"),
    db: Session = Depends(get_db_session)
):
    """Admin: Grant initial balance to a user."""
    from gate.src.gate_service import GateService
    
    gate_service = GateService(db)
    gate_service.grant_initial_balance(user_id, currency, Decimal(str(amount)))
    
    return {"success": True, "user_id": user_id, "granted": {currency: amount}}


# =============================================================================
# Location & Geofence Endpoints
# =============================================================================
@app.post("/v1/theatres/{theatre_id}/ring/evaluate", response_model=RingEvaluateResponse, tags=["Location"])
async def evaluate_ring(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: RingEvaluateRequestModel = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Evaluate user's ring level for stages."""
    from location.src.location_service import LocationService, LocationEvaluateRequest
    
    location_service = LocationService(db)
    eval_request = LocationEvaluateRequest(
        slot_id=request.slot_id,
        lat=request.lat,
        lng=request.lng,
        accuracy_m=request.accuracy_m,
        timestamp_ms=request.timestamp_ms,
        requested_stage_ids=request.requested_stage_ids
    )
    
    result = location_service.evaluate_ring(theatre_id, x_user_id, eval_request)
    
    return RingEvaluateResponse(
        theatre_id=result.theatre_id,
        slot_id=result.slot_id,
        rings=[RingEvaluationItem(**r.to_dict()) for r in result.rings],
        global_risk_level=result.global_risk_level,
        degrade_reason=result.degrade_reason
    )


@app.get("/v1/theatres/{theatre_id}/stages/nearby", response_model=NearbyStagesResponse, tags=["Location"])
async def get_nearby_stages(
    theatre_id: str = Path(..., description="Theatre ID"),
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_m: int = Query(default=5000, description="Search radius in meters"),
    db: Session = Depends(get_db_session)
):
    """Get stages near a location."""
    from location.src.location_service import LocationService
    
    location_service = LocationService(db)
    stages = location_service.get_stages_nearby(theatre_id, lat, lng, radius_m)
    
    return NearbyStagesResponse(
        theatre_id=theatre_id,
        stages=[NearbyStageItem(**s) for s in stages]
    )


@app.post("/v1/theatres/{theatre_id}/stages", response_model=StageResponse, tags=["Location"])
async def create_stage(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: CreateStageRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """Create a new stage (geographic anchor)."""
    from location.src.location_service import LocationService
    
    location_service = LocationService(db)
    stage = location_service.create_stage(
        theatre_id=theatre_id,
        stage_id=request.stage_id,
        name=request.name,
        lat=request.lat,
        lng=request.lng,
        ringc_m=request.ringc_m,
        ringb_m=request.ringb_m,
        ringa_m=request.ringa_m,
        tags=request.tags,
        safe_only=request.safe_only
    )
    
    return StageResponse(
        theatre_id=str(stage.theatre_id),
        stage_id=stage.stage_id,
        name=stage.name,
        latitude=stage.latitude,
        longitude=stage.longitude,
        ringc_m=stage.ringc_m,
        ringb_m=stage.ringb_m,
        ringa_m=stage.ringa_m,
        status=stage.status
    )


@app.post("/v1/ring/verify", tags=["Location"])
async def verify_ring_token(
    token: str = Query(..., description="Ring token to verify"),
    db: Session = Depends(get_db_session)
):
    """Verify a ring attestation token."""
    from location.src.location_service import LocationService
    
    location_service = LocationService(db)
    claims = location_service.verify_ring_token(token)
    
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {"valid": True, "claims": claims}


@app.post("/v1/admin/theatres/{theatre_id}/stages/{stage_id}/safety-override", tags=["Admin"])
async def set_safety_override(
    theatre_id: str = Path(..., description="Theatre ID"),
    stage_id: str = Path(..., description="Stage ID"),
    ringa_enabled: bool = Query(..., description="Enable or disable Ring A"),
    reason: str = Query(..., description="Reason for override"),
    operator: str = Query(..., description="Operator name"),
    expires_hours: Optional[int] = Query(None, description="Hours until expiry"),
    db: Session = Depends(get_db_session)
):
    """Admin: Set safety override for a stage (emergency lockdown)."""
    from location.src.location_service import LocationService
    
    location_service = LocationService(db)
    override = location_service.set_safety_override(
        theatre_id=theatre_id,
        stage_id=stage_id,
        ringa_enabled=ringa_enabled,
        reason=reason,
        operator=operator,
        expires_hours=expires_hours
    )
    
    action = "enabled" if ringa_enabled else "disabled"
    return {
        "success": True,
        "message": f"Ring A {action} for stage {stage_id}",
        "override_id": str(override.override_id),
        "expires_at": override.expires_at.isoformat() if override.expires_at else None
    }


# =============================================================================
# Demo/Admin Endpoints (M1 Testing)
# =============================================================================
@app.post("/v1/admin/theatres/{theatre_id}/tick", response_model=RunTickResponse, tags=["Admin"])
async def run_tick(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Manually trigger a tick for testing."""
    kernel = KernelService(db)
    
    try:
        tick_id, version = kernel.run_tick(theatre_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return RunTickResponse(
        theatre_id=theatre_id,
        tick_id=tick_id,
        version=version,
        message=f"Tick completed: tick_id={tick_id}, version={version}"
    )


@app.post("/v1/admin/theatres/{theatre_id}/generate-plan", response_model=GeneratePlanResponse, tags=["Admin"])
async def generate_plan(
    theatre_id: str = Path(..., description="Theatre ID"),
    hours_ahead: int = Query(1, ge=1, le=24, description="Hours ahead to generate"),
    db: Session = Depends(get_db_session)
):
    """Generate HourPlan for upcoming slots."""
    scheduler = SchedulerService(db)
    
    try:
        plans = scheduler.generate_upcoming_plans(theatre_id, hours_ahead)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    if not plans:
        raise HTTPException(status_code=500, detail="Failed to generate plans")
    
    plan = plans[0]  # Return first plan
    return GeneratePlanResponse(
        slot_id=plan.slot_id,
        theatre_id=str(plan.theatre_id),
        start_at=plan.start_at.isoformat(),
        scenes_parallel=plan.scenes_parallel,
        primary_thread=plan.primary_thread,
        gate_type=plan.hour_gate_jsonb.get("type", "Public"),
        status=plan.status
    )


@app.post("/v1/admin/slots/{slot_id}/publish", response_model=PublishSlotResponse, tags=["Admin"])
async def publish_slot_demo(
    slot_id: str = Path(..., description="Slot ID"),
    db: Session = Depends(get_db_session)
):
    """Publish demo content for a slot (M1 static content)."""
    # Get the hour plan
    hour_plan = db.query(HourPlan).filter(HourPlan.slot_id == slot_id).first()
    
    if not hour_plan:
        raise HTTPException(status_code=404, detail="HourPlan not found")
    
    # Generate demo content
    slot_bundle = StaticContentGenerator.generate_demo_slot(
        slot_id=slot_id,
        theatre_id=str(hour_plan.theatre_id),
        hour_plan=hour_plan
    )
    
    # Publish
    delivery = SceneDeliveryService(db)
    published = delivery.publish_slot(
        theatre_id=str(hour_plan.theatre_id),
        slot_id=slot_id,
        scenes=[s.to_dict() for s in slot_bundle.scenes],
        gate_instance_id=slot_bundle.gate_instance_id,
        gate_config=slot_bundle.gate_config,
        notes=slot_bundle.notes
    )
    
    return PublishSlotResponse(
        slot_id=slot_id,
        theatre_id=str(published.theatre_id),
        publish_version=published.publish_version,
        scenes_count=len(slot_bundle.scenes),
        message=f"Published {len(slot_bundle.scenes)} scenes for slot {slot_id}"
    )


@app.post("/v1/admin/theatres/{theatre_id}/demo-cycle", tags=["Admin"])
async def run_demo_cycle(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """
    Run a complete demo cycle: tick -> generate plan -> publish.
    
    This demonstrates the full M1 flow in one call.
    """
    kernel = KernelService(db)
    scheduler = SchedulerService(db)
    delivery = SceneDeliveryService(db)
    
    # 1. Run tick
    try:
        tick_id, version = kernel.run_tick(theatre_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # 2. Generate plan
    plans = scheduler.generate_upcoming_plans(theatre_id, 1)
    if not plans:
        raise HTTPException(status_code=500, detail="Failed to generate plan")
    
    hour_plan = plans[0]
    
    # 3. Generate and publish demo content
    slot_bundle = StaticContentGenerator.generate_demo_slot(
        slot_id=hour_plan.slot_id,
        theatre_id=theatre_id,
        hour_plan=hour_plan
    )
    
    published = delivery.publish_slot(
        theatre_id=theatre_id,
        slot_id=hour_plan.slot_id,
        scenes=[s.to_dict() for s in slot_bundle.scenes],
        gate_instance_id=slot_bundle.gate_instance_id,
        gate_config=slot_bundle.gate_config,
        notes=slot_bundle.notes
    )
    
    # 4. Create gate instance for the slot
    from gate.src.gate_service import GateService
    gate_service = GateService(db)
    gate = gate_service.create_gate_instance(
        theatre_id=theatre_id,
        slot_id=hour_plan.slot_id,
        gate_config=slot_bundle.gate_config,
        slot_start_at=hour_plan.start_at
    )
    
    return {
        "success": True,
        "theatre_id": theatre_id,
        "tick": {"tick_id": tick_id, "version": version},
        "plan": {
            "slot_id": hour_plan.slot_id,
            "start_at": hour_plan.start_at.isoformat(),
            "primary_thread": hour_plan.primary_thread,
            "gate_type": hour_plan.hour_gate_jsonb.get("type")
        },
        "published": {
            "slot_id": published.slot_id,
            "version": published.publish_version,
            "scenes_count": len(slot_bundle.scenes)
        },
        "gate": {
            "gate_instance_id": str(gate.gate_instance_id),
            "status": gate.status,
            "open_at": gate.open_at.isoformat(),
            "close_at": gate.close_at.isoformat()
        },
        "message": "Demo cycle completed successfully!"
    }


@app.post("/v1/admin/theatres/{theatre_id}/demo-full-cycle", tags=["Admin"])
async def run_full_demo_cycle(
    theatre_id: str = Path(..., description="Theatre ID"),
    user_id: str = Query(default="demo_user_001", description="Demo user ID"),
    db: Session = Depends(get_db_session)
):
    """
    Run a complete demo cycle including Gate voting and resolution.
    
    This demonstrates the full M1 flow with Gate system.
    """
    from gate.src.gate_service import GateService, VoteRequest
    from location.src.location_service import LocationService
    
    kernel = KernelService(db)
    scheduler = SchedulerService(db)
    delivery = SceneDeliveryService(db)
    gate_service = GateService(db)
    location_service = LocationService(db)
    
    # 1. Run tick
    try:
        tick_id, version = kernel.run_tick(theatre_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # 2. Generate plan
    plans = scheduler.generate_upcoming_plans(theatre_id, 1)
    if not plans:
        raise HTTPException(status_code=500, detail="Failed to generate plan")
    
    hour_plan = plans[0]
    
    # 3. Generate and publish demo content
    slot_bundle = StaticContentGenerator.generate_demo_slot(
        slot_id=hour_plan.slot_id,
        theatre_id=theatre_id,
        hour_plan=hour_plan
    )
    
    published = delivery.publish_slot(
        theatre_id=theatre_id,
        slot_id=hour_plan.slot_id,
        scenes=[s.to_dict() for s in slot_bundle.scenes],
        gate_instance_id=slot_bundle.gate_instance_id,
        gate_config=slot_bundle.gate_config,
        notes=slot_bundle.notes
    )
    
    # 4. Create gate instance
    gate = gate_service.create_gate_instance(
        theatre_id=theatre_id,
        slot_id=hour_plan.slot_id,
        gate_config=slot_bundle.gate_config,
        slot_start_at=hour_plan.start_at
    )
    
    # 5. Create demo stages
    demo_stages = [
        {"stage_id": "stg_001", "name": "外滩观景台", "lat": 31.2397, "lng": 121.4908},
        {"stage_id": "stg_002", "name": "南京路步行街", "lat": 31.2352, "lng": 121.4747},
        {"stage_id": "stg_003", "name": "豫园", "lat": 31.2272, "lng": 121.4922},
    ]
    
    created_stages = []
    for stage_data in demo_stages:
        stage = location_service.create_stage(
            theatre_id=theatre_id,
            **stage_data
        )
        created_stages.append(stage.stage_id)
    
    # 6. Grant user initial balance
    gate_service.grant_initial_balance(user_id, "SHARD", Decimal("100"))
    
    # 7. Force open gate and submit demo votes
    gate.status = "OPEN"
    db.commit()
    
    # Submit demo votes
    demo_votes = [
        {"user_id": user_id, "option_id": "opt_a"},
        {"user_id": "demo_user_002", "option_id": "opt_b"},
        {"user_id": "demo_user_003", "option_id": "opt_a"},
    ]
    
    for vote_data in demo_votes:
        vote_req = VoteRequest(option_id=vote_data["option_id"])
        gate_service.submit_vote(str(gate.gate_instance_id), vote_data["user_id"], vote_req)
    
    # 8. Resolve gate
    resolve_result = gate_service.resolve_gate(str(gate.gate_instance_id))
    
    return {
        "success": True,
        "theatre_id": theatre_id,
        "tick": {"tick_id": tick_id, "version": version},
        "plan": {
            "slot_id": hour_plan.slot_id,
            "start_at": hour_plan.start_at.isoformat(),
            "primary_thread": hour_plan.primary_thread,
            "gate_type": hour_plan.hour_gate_jsonb.get("type")
        },
        "published": {
            "slot_id": published.slot_id,
            "version": published.publish_version,
            "scenes_count": len(slot_bundle.scenes)
        },
        "gate": {
            "gate_instance_id": str(gate.gate_instance_id),
            "status": gate.status,
            "winner_option_id": resolve_result.winner_option_id,
            "explain_card": resolve_result.explain_card
        },
        "stages_created": created_stages,
        "demo_user": {
            "user_id": user_id,
            "initial_balance": {"SHARD": 100}
        },
        "message": "Full demo cycle completed with Gate resolution!"
    }


# =============================================================================
# Error Handlers
# =============================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc)}
    )


# =============================================================================
# Main Entry Point
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)


# =============================================================================
# Content Factory Endpoints (M2)
# =============================================================================

# --- Content Factory Request/Response Models ---
class GenerateSlotRequest(BaseModel):
    slot_id: str = Field(..., description="Slot ID to generate content for")
    target_level: str = Field(default="L0", description="Target degrade level (L0-L4)")
    use_ai: bool = Field(default=True, description="Whether to use AI generation")


class GenerateSlotResponse(BaseModel):
    job_id: str
    slot_id: str
    theatre_id: str
    status: str
    degrade_level: str
    scenes_count: int
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    theatre_id: str
    slot_id: str
    status: str
    degrade_level: str
    attempt: int
    deadline_at: Optional[str]
    fail_reason: Optional[str]
    steps: List[Dict]


class CompileRequest(BaseModel):
    scene_drafts: List[Dict] = Field(..., description="Scene drafts to compile")
    evidence_list: List[Dict] = Field(default=[], description="Evidence list")
    gate_config: Dict = Field(default={}, description="Gate configuration")
    world_state: Dict = Field(default={}, description="Current world state")


class CompileResponse(BaseModel):
    status: str
    score: float
    violations: List[Dict]
    warnings: List[Dict]
    budgets: Dict
    auto_fixes_applied: List[str]
    compile_time_ms: int


class RenderRequest(BaseModel):
    scenes: List[Dict] = Field(..., description="Scenes to render")
    target_level: str = Field(default="L0", description="Target degrade level")


class RenderResponse(BaseModel):
    target_level: str
    final_level: str
    total_scenes: int
    success_count: int
    results: List[Dict]


class DegradeLadderResponse(BaseModel):
    levels: List[Dict]


# --- Content Factory API Endpoints ---
@app.post("/v1/content-factory/generate", response_model=GenerateSlotResponse, tags=["Content Factory"])
async def generate_slot_content(
    theatre_id: str = Query(..., description="Theatre ID"),
    request: GenerateSlotRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """
    Generate content for a slot using AI Content Factory.
    
    This endpoint triggers the full content generation workflow:
    1. BeatPicker - Select beat templates
    2. SlotFiller - Fill stage/camera/props
    3. SceneWriter - Generate scene text (AI)
    4. EvidenceInstantiator - Create evidence instances
    5. GatePlanner - Generate gate lobby copy
    6. CanonGuard Compile - Check continuity/safety
    7. Render Pipeline - Generate media assets
    8. Moderation - Content review
    9. Publish - Publish slot bundle
    """
    try:
        from content_factory.src.orchestrator import ContentFactoryService
        
        # Get hour plan for the slot
        hour_plan = db.query(HourPlan).filter(
            HourPlan.theatre_id == theatre_id,
            HourPlan.slot_id == request.slot_id
        ).first()
        
        if not hour_plan:
            raise HTTPException(status_code=404, detail=f"HourPlan not found for slot {request.slot_id}")
        
        # Get world state
        kernel = KernelService(db)
        world_state = kernel.get_world_state(theatre_id)
        if not world_state:
            raise HTTPException(status_code=404, detail=f"Theatre {theatre_id} not found")
        
        # Run content factory
        factory = ContentFactoryService(db)
        slot_bundle = factory.generate_slot(
            theatre_id=theatre_id,
            slot_id=request.slot_id,
            hour_plan=hour_plan,
            world_state=world_state.to_dict()
        )
        
        # Publish the generated content
        delivery = SceneDeliveryService(db)
        published = delivery.publish_slot(
            theatre_id=theatre_id,
            slot_id=request.slot_id,
            scenes=[s.to_dict() for s in slot_bundle.scenes],
            gate_instance_id=slot_bundle.gate_instance_id,
            gate_config=slot_bundle.gate_config,
            notes=slot_bundle.notes
        )
        
        return GenerateSlotResponse(
            job_id=slot_bundle.source_job_id,
            slot_id=request.slot_id,
            theatre_id=theatre_id,
            status="SUCCESS",
            degrade_level=slot_bundle.degrade_level,
            scenes_count=len(slot_bundle.scenes),
            message=f"Content generated and published successfully at level {slot_bundle.degrade_level}"
        )
        
    except ImportError as e:
        logger.warning(f"Content Factory not available: {e}")
        raise HTTPException(status_code=501, detail="Content Factory module not available")
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/content-factory/jobs/{job_id}", response_model=JobStatusResponse, tags=["Content Factory"])
async def get_job_status(
    job_id: str = Path(..., description="Generation job ID"),
    db: Session = Depends(get_db_session)
):
    """Get the status of a content generation job."""
    try:
        from content_factory.src.orchestrator import ContentFactoryService
        
        factory = ContentFactoryService(db)
        status = factory.get_job_status(job_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        return JobStatusResponse(**status)
        
    except ImportError as e:
        raise HTTPException(status_code=501, detail="Content Factory module not available")


@app.post("/v1/content-factory/compile", response_model=CompileResponse, tags=["Content Factory"])
async def compile_scenes(
    request: CompileRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """
    Compile scene drafts through CanonGuard.
    
    This endpoint validates scene drafts against:
    - Hard rules (character conflicts, safety, entity whitelist)
    - Budget limits (intensity, evidence tiers)
    - Soft rules (scoring)
    """
    try:
        from content_factory.src.canon_guard import CanonGuardCompiler, EntityRegistry
        
        compiler = CanonGuardCompiler(EntityRegistry())
        result = compiler.compile(
            scene_drafts=request.scene_drafts,
            evidence_list=request.evidence_list,
            gate_config=request.gate_config,
            world_state=request.world_state,
            hour_plan={}
        )
        
        return CompileResponse(
            status=result.status,
            score=result.score,
            violations=[v.to_dict() for v in result.violations],
            warnings=[w.to_dict() for w in result.warnings],
            budgets={k: {"name": v.name, "limit": v.limit, "current": v.current, "exceeded": v.exceeded} for k, v in result.budgets.items()},
            auto_fixes_applied=result.auto_fixes_applied,
            compile_time_ms=result.compile_time_ms
        )
        
    except ImportError as e:
        raise HTTPException(status_code=501, detail="CanonGuard module not available")


@app.post("/v1/content-factory/render", response_model=RenderResponse, tags=["Content Factory"])
async def render_scenes(
    request: RenderRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """
    Render scenes through the Render Pipeline.
    
    Supports degrade levels:
    - L0: Full media (video + image + audio + text)
    - L1: Light degrade (image + audio + text, no video)
    - L2: Heavy degrade (silhouette + audio + evidence card)
    - L3: Rescue beat (template only)
    - L4: Silent slot (placeholder only)
    """
    try:
        from content_factory.src.render_pipeline import RenderPipelineService
        
        service = RenderPipelineService()
        result = service.render_scenes(
            scenes=request.scenes,
            target_level=request.target_level
        )
        
        return RenderResponse(**result)
        
    except ImportError as e:
        raise HTTPException(status_code=501, detail="Render Pipeline module not available")


@app.get("/v1/content-factory/degrade-ladder", response_model=DegradeLadderResponse, tags=["Content Factory"])
async def get_degrade_ladder():
    """Get the degrade ladder configuration."""
    try:
        from content_factory.src.render_pipeline import RenderPipelineService
        
        service = RenderPipelineService()
        levels = service.get_degrade_ladder()
        
        return DegradeLadderResponse(levels=levels)
        
    except ImportError as e:
        # Return static configuration if module not available
        return DegradeLadderResponse(levels=[
            {"level": "L0", "name": "正常", "assets": ["视频", "图片", "音频", "文本", "证物卡"], "description": "最强代入感，完整媒体体验"},
            {"level": "L1", "name": "轻降级", "assets": ["图片", "音频", "文本", "证物卡"], "description": "无视频，渲染失败常见兜底"},
            {"level": "L2", "name": "强降级", "assets": ["剪影图", "音轨", "证物卡"], "description": "内容仍可读懂，神秘感保持"},
            {"level": "L3", "name": "救援拍子", "assets": ["救援模板"], "description": "保证 slot 结构完整"},
            {"level": "L4", "name": "静默 slot", "assets": ["占位图", "门", "Explain"], "description": "最后兜底，仍可结算与回声"}
        ])


@app.post("/v1/admin/theatres/{theatre_id}/demo-ai-cycle", tags=["Admin"])
async def run_demo_ai_cycle(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """
    Run a complete demo cycle with AI content generation.
    
    This demonstrates the full M2 workflow:
    1. Tick the world
    2. Generate hour plan
    3. Generate AI content
    4. Compile through CanonGuard
    5. Render media assets
    6. Publish slot
    7. Create and resolve gate
    """
    try:
        from content_factory.src.orchestrator import ContentFactoryService
        from gate.src.gate_service import GateService, VoteRequest
        from location.src.location_service import LocationService
        
        kernel = KernelService(db)
        scheduler = SchedulerService(db)
        delivery = SceneDeliveryService(db)
        factory = ContentFactoryService(db)
        gate_service = GateService(db)
        location_service = LocationService(db)
        
        user_id = f"demo_user_{uuid.uuid4().hex[:8]}"
        
        # 1. Run tick
        tick_id, version = kernel.run_tick(theatre_id)
        
        # 2. Generate plan
        plans = scheduler.generate_upcoming_plans(theatre_id, 1)
        if not plans:
            raise HTTPException(status_code=500, detail="Failed to generate plan")
        
        hour_plan = plans[0]
        
        # 3. Get world state
        world_state = kernel.get_world_state(theatre_id)
        
        # 4. Generate AI content
        slot_bundle = factory.generate_slot(
            theatre_id=theatre_id,
            slot_id=hour_plan.slot_id,
            hour_plan=hour_plan,
            world_state=world_state.to_dict()
        )
        
        # 5. Publish
        published = delivery.publish_slot(
            theatre_id=theatre_id,
            slot_id=hour_plan.slot_id,
            scenes=[s.to_dict() for s in slot_bundle.scenes],
            gate_instance_id=slot_bundle.gate_instance_id,
            gate_config=slot_bundle.gate_config,
            notes=f"AI Generated at {slot_bundle.degrade_level}"
        )
        
        # 6. Create gate
        gate = gate_service.create_gate_instance(
            theatre_id=theatre_id,
            slot_id=hour_plan.slot_id,
            gate_config=slot_bundle.gate_config,
            slot_start_at=hour_plan.start_at
        )
        
        # 7. Grant balance and submit votes
        gate_service.grant_initial_balance(user_id, "SHARD", Decimal("100"))
        gate.status = "OPEN"
        db.commit()
        
        vote_req = VoteRequest(option_id="opt_a")
        gate_service.submit_vote(str(gate.gate_instance_id), user_id, vote_req)
        
        # 8. Resolve gate
        resolve_result = gate_service.resolve_gate(str(gate.gate_instance_id))
        
        return {
            "success": True,
            "theatre_id": theatre_id,
            "tick": {"tick_id": tick_id, "version": version},
            "plan": {
                "slot_id": hour_plan.slot_id,
                "start_at": hour_plan.start_at.isoformat(),
                "primary_thread": hour_plan.primary_thread
            },
            "content_factory": {
                "job_id": slot_bundle.source_job_id,
                "degrade_level": slot_bundle.degrade_level,
                "scenes_count": len(slot_bundle.scenes),
                "scenes_preview": [
                    {
                        "scene_id": s.scene_id,
                        "stage_id": s.stage_id,
                        "mood": s.mood,
                        "text_preview": s.scene_text[:100] + "..." if len(s.scene_text) > 100 else s.scene_text
                    }
                    for s in slot_bundle.scenes[:3]
                ]
            },
            "published": {
                "slot_id": published.slot_id,
                "version": published.publish_version
            },
            "gate": {
                "gate_instance_id": str(gate.gate_instance_id),
                "winner_option_id": resolve_result.winner_option_id
            },
            "message": "AI-powered demo cycle completed successfully!"
        }
        
    except ImportError as e:
        logger.warning(f"Some modules not available: {e}")
        raise HTTPException(status_code=501, detail=f"Required module not available: {e}")
    except Exception as e:
        logger.error(f"AI demo cycle failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# M3: Evidence System API Endpoints
# =============================================================================

# --- Evidence Pydantic Models ---
class CreateEvidenceRequest(BaseModel):
    type_id: str = Field(..., description="Evidence type ID")
    tier: str = Field(..., description="Evidence tier (A/B/C/D)")
    owner_id: str = Field(..., description="Owner user ID")
    source: str = Field(default="SCENE", description="Evidence source")
    source_scene_id: Optional[str] = Field(default=None, description="Source scene ID")
    source_slot_id: Optional[str] = Field(default=None, description="Source slot ID")
    source_stage_id: Optional[str] = Field(default=None, description="Source stage ID")
    metadata: Optional[Dict] = Field(default=None, description="Additional metadata")


class EvidenceResponse(BaseModel):
    instance_id: str
    type_id: str
    tier: str
    owner_id: str
    theatre_id: str
    source: str
    status: str
    verification_status: str
    credibility_score: Optional[float] = None
    created_at: str
    expires_at: Optional[str] = None
    is_forged: bool = False


class VerifyEvidenceRequest(BaseModel):
    pay_cost: bool = Field(default=True, description="Whether to pay verification cost")


class VerifyEvidenceResponse(BaseModel):
    success: bool
    is_authentic: bool
    confidence: float
    cost_paid: int
    message: str
    detected_forgery: bool = False


class SubmitEvidenceRequest(BaseModel):
    gate_instance_id: str = Field(..., description="Gate instance to submit to")


class SubmitEvidenceResponse(BaseModel):
    submission_id: str
    evidence_instance_id: str
    gate_instance_id: str
    submitted_at: str
    message: str


class CreateTradeOfferRequest(BaseModel):
    evidence_instance_id: str = Field(..., description="Evidence to sell")
    asking_price: float = Field(..., gt=0, description="Asking price")
    currency: str = Field(default="SHARD", description="Currency")
    duration_hours: int = Field(default=24, description="Offer duration in hours")


class TradeOfferResponse(BaseModel):
    offer_id: str
    seller_id: str
    evidence_instance_id: str
    asking_price: float
    currency: str
    status: str
    created_at: str
    expires_at: Optional[str] = None


class AcceptTradeRequest(BaseModel):
    buyer_id: str = Field(..., description="Buyer user ID")


class AcceptTradeResponse(BaseModel):
    success: bool
    message: str


class EvidenceStatsResponse(BaseModel):
    total_instances: int
    by_tier: Dict[str, int]
    by_status: Dict[str, int]
    active_offers: int
    total_submissions: int


# Evidence API Endpoints
@app.post("/v1/theatres/{theatre_id}/evidence", response_model=EvidenceResponse, tags=["Evidence"])
async def create_evidence(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: CreateEvidenceRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """Create a new evidence instance."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        instance = evidence_service.create_evidence(
            type_id=request.type_id,
            tier=request.tier,
            owner_id=request.owner_id,
            theatre_id=theatre_id,
            source=request.source,
            source_scene_id=request.source_scene_id,
            source_slot_id=request.source_slot_id,
            source_stage_id=request.source_stage_id,
            metadata=request.metadata
        )
        
        return EvidenceResponse(
            instance_id=instance.instance_id,
            type_id=instance.type_id,
            tier=instance.tier.value,
            owner_id=instance.owner_id,
            theatre_id=instance.theatre_id,
            source=instance.source.value,
            status=instance.status.value,
            verification_status=instance.verification_status.value,
            created_at=instance.created_at.isoformat(),
            expires_at=instance.expires_at.isoformat() if instance.expires_at else None,
            is_forged=instance.is_forged
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/evidence/{instance_id}", response_model=EvidenceResponse, tags=["Evidence"])
async def get_evidence(
    instance_id: str = Path(..., description="Evidence instance ID"),
    db: Session = Depends(get_db_session)
):
    """Get evidence instance details."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        instance = evidence_service.get_evidence(instance_id)
        
        if not instance:
            raise HTTPException(status_code=404, detail="Evidence not found")
        
        return EvidenceResponse(
            instance_id=instance.instance_id,
            type_id=instance.type_id,
            tier=instance.tier.value,
            owner_id=instance.owner_id,
            theatre_id=instance.theatre_id,
            source=instance.source.value,
            status=instance.status.value,
            verification_status=instance.verification_status.value,
            created_at=instance.created_at.isoformat(),
            expires_at=instance.expires_at.isoformat() if instance.expires_at else None,
            is_forged=instance.is_forged
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/evidence", response_model=List[EvidenceResponse], tags=["Evidence"])
async def get_user_evidence(
    user_id: str = Path(..., description="User ID"),
    include_expired: bool = Query(default=False, description="Include expired evidence"),
    tier: Optional[str] = Query(default=None, description="Filter by tier"),
    db: Session = Depends(get_db_session)
):
    """Get user's evidence inventory."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        instances = evidence_service.get_user_evidence(
            user_id=user_id,
            include_expired=include_expired,
            tier_filter=tier
        )
        
        return [
            EvidenceResponse(
                instance_id=inst.instance_id,
                type_id=inst.type_id,
                tier=inst.tier.value,
                owner_id=inst.owner_id,
                theatre_id=inst.theatre_id,
                source=inst.source.value,
                status=inst.status.value,
                verification_status=inst.verification_status.value,
                created_at=inst.created_at.isoformat(),
                expires_at=inst.expires_at.isoformat() if inst.expires_at else None,
                is_forged=inst.is_forged
            )
            for inst in instances
        ]
    except Exception as e:
        logger.error(f"Failed to get user evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/evidence/{instance_id}/verify", response_model=VerifyEvidenceResponse, tags=["Evidence"])
async def verify_evidence(
    instance_id: str = Path(..., description="Evidence instance ID"),
    request: VerifyEvidenceRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Verify evidence authenticity."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        result = evidence_service.verify_evidence(
            instance_id=instance_id,
            user_id=x_user_id,
            pay_cost=request.pay_cost
        )
        
        return VerifyEvidenceResponse(
            success=result.success,
            is_authentic=result.is_authentic,
            confidence=result.confidence,
            cost_paid=result.cost_paid,
            message=result.message,
            detected_forgery=result.detected_forgery
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to verify evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/evidence/{instance_id}/submit", response_model=SubmitEvidenceResponse, tags=["Evidence"])
async def submit_evidence_to_gate(
    instance_id: str = Path(..., description="Evidence instance ID"),
    request: SubmitEvidenceRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Submit evidence to a gate."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        submission = evidence_service.submit_to_gate(
            instance_id=instance_id,
            user_id=x_user_id,
            gate_instance_id=request.gate_instance_id
        )
        
        return SubmitEvidenceResponse(
            submission_id=submission.submission_id,
            evidence_instance_id=submission.evidence_instance_id,
            gate_instance_id=submission.gate_instance_id,
            submitted_at=submission.submitted_at.isoformat(),
            message="Evidence submitted successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/evidence/trade/offers", response_model=TradeOfferResponse, tags=["Evidence"])
async def create_trade_offer(
    request: CreateTradeOfferRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Seller user ID"),
    db: Session = Depends(get_db_session)
):
    """Create a trade offer for evidence."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        offer = evidence_service.create_trade_offer(
            seller_id=x_user_id,
            instance_id=request.evidence_instance_id,
            asking_price=request.asking_price,
            currency=request.currency,
            duration_hours=request.duration_hours
        )
        
        return TradeOfferResponse(
            offer_id=offer.offer_id,
            seller_id=offer.seller_id,
            evidence_instance_id=offer.evidence_instance_id,
            asking_price=float(offer.asking_price),
            currency=offer.currency,
            status=offer.status,
            created_at=offer.created_at.isoformat(),
            expires_at=offer.expires_at.isoformat() if offer.expires_at else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create trade offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/evidence/trade/offers", response_model=List[TradeOfferResponse], tags=["Evidence"])
async def list_trade_offers(
    theatre_id: Optional[str] = Query(default=None, description="Filter by theatre"),
    tier: Optional[str] = Query(default=None, description="Filter by tier"),
    db: Session = Depends(get_db_session)
):
    """List open trade offers."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        offers = evidence_service.get_open_offers(
            theatre_id=theatre_id,
            tier_filter=tier
        )
        
        return [
            TradeOfferResponse(
                offer_id=offer.offer_id,
                seller_id=offer.seller_id,
                evidence_instance_id=offer.evidence_instance_id,
                asking_price=float(offer.asking_price),
                currency=offer.currency,
                status=offer.status,
                created_at=offer.created_at.isoformat(),
                expires_at=offer.expires_at.isoformat() if offer.expires_at else None
            )
            for offer in offers
        ]
    except Exception as e:
        logger.error(f"Failed to list trade offers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/evidence/trade/offers/{offer_id}/accept", response_model=AcceptTradeResponse, tags=["Evidence"])
async def accept_trade_offer(
    offer_id: str = Path(..., description="Trade offer ID"),
    request: AcceptTradeRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """Accept a trade offer."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        success, message = evidence_service.accept_trade_offer(
            offer_id=offer_id,
            buyer_id=request.buyer_id
        )
        
        return AcceptTradeResponse(success=success, message=message)
    except Exception as e:
        logger.error(f"Failed to accept trade offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/evidence/stats", response_model=EvidenceStatsResponse, tags=["Evidence"])
async def get_evidence_stats(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get evidence system statistics."""
    try:
        from evidence.src.evidence_service import EvidenceService
        
        evidence_service = EvidenceService(db)
        stats = evidence_service.get_statistics(theatre_id)
        
        return EvidenceStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get evidence stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# M3: Rumor System API Endpoints
# =============================================================================

# --- Rumor Pydantic Models ---
class CreateRumorRequest(BaseModel):
    content: str = Field(..., description="Rumor content")
    category: str = Field(..., description="Rumor category")
    source: str = Field(..., description="Rumor source type")
    tone: str = Field(..., description="Rumor tone")
    based_on_evidence_ids: Optional[List[str]] = Field(default=None, description="Evidence IDs this rumor is based on")
    based_on_scene_id: Optional[str] = Field(default=None, description="Scene ID this rumor is based on")
    related_stage_tags: Optional[List[str]] = Field(default=None, description="Related stage tags")
    expiry_hours: Optional[int] = Field(default=None, description="Expiry time in hours")


class RumorResponse(BaseModel):
    rumor_id: str
    creator_id: str
    theatre_id: str
    content: str
    category: str
    source: str
    tone: str
    status: str
    credibility_score: float
    spread_count: int
    view_count: int
    influence_score: float
    created_at: str
    expires_at: Optional[str] = None
    is_misread: bool = False
    verification_outcome: Optional[str] = None


class CreateRumorFromTemplateRequest(BaseModel):
    template_id: str = Field(..., description="Template ID")
    fill_values: Dict[str, str] = Field(..., description="Values to fill in template")
    source: str = Field(..., description="Rumor source type")
    tone: str = Field(..., description="Rumor tone")
    based_on_evidence_ids: Optional[List[str]] = Field(default=None, description="Evidence IDs")


class ShareRumorRequest(BaseModel):
    to_user_id: Optional[str] = Field(default=None, description="Target user ID")
    to_crew_id: Optional[str] = Field(default=None, description="Target crew ID")


class ShareRumorResponse(BaseModel):
    share_id: str
    rumor_id: str
    from_user_id: str
    to_user_id: Optional[str] = None
    to_crew_id: Optional[str] = None
    is_broadcast: bool
    shared_at: str


class VerifyRumorRequest(BaseModel):
    actual_truth: str = Field(..., description="The actual truth")
    is_accurate: bool = Field(..., description="Whether the rumor is accurate")
    deviation_type: Optional[str] = Field(default=None, description="Type of deviation if inaccurate")


class VerifyRumorResponse(BaseModel):
    outcome: str
    echo_id: Optional[str] = None
    consequence: Optional[str] = None


class AddReactionRequest(BaseModel):
    reaction_type: str = Field(..., description="Reaction type (BELIEVE, DOUBT, INVESTIGATE, SPREAD, DEBUNK)")
    comment: Optional[str] = Field(default=None, description="Optional comment")


class ReactionResponse(BaseModel):
    reaction_id: str
    rumor_id: str
    user_id: str
    reaction_type: str
    created_at: str


class StageHeatResponse(BaseModel):
    stage_tag: str
    total_heat: float
    contribution_count: int
    tone_breakdown: Dict[str, float]


class RumorStatsResponse(BaseModel):
    total_rumors: int
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    total_spread: int
    total_views: int
    misread_count: int
    active_echoes: int


# Rumor API Endpoints
@app.post("/v1/theatres/{theatre_id}/rumors", response_model=RumorResponse, tags=["Rumor"])
async def create_rumor(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: CreateRumorRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Creator user ID"),
    db: Session = Depends(get_db_session)
):
    """Create a new rumor."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        rumor = rumor_service.create_rumor(
            creator_id=x_user_id,
            theatre_id=theatre_id,
            content=request.content,
            category=request.category,
            source=request.source,
            tone=request.tone,
            based_on_evidence_ids=request.based_on_evidence_ids,
            based_on_scene_id=request.based_on_scene_id,
            related_stage_tags=request.related_stage_tags,
            expiry_hours=request.expiry_hours
        )
        
        return RumorResponse(
            rumor_id=rumor.rumor_id,
            creator_id=rumor.creator_id,
            theatre_id=rumor.theatre_id,
            content=rumor.content,
            category=rumor.category.value,
            source=rumor.source.value,
            tone=rumor.tone.value,
            status=rumor.status.value,
            credibility_score=rumor.credibility_score,
            spread_count=rumor.spread_count,
            view_count=rumor.view_count,
            influence_score=rumor.influence_score,
            created_at=rumor.created_at.isoformat(),
            expires_at=rumor.expires_at.isoformat() if rumor.expires_at else None,
            is_misread=rumor.is_misread
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create rumor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/theatres/{theatre_id}/rumors/from-template", response_model=RumorResponse, tags=["Rumor"])
async def create_rumor_from_template(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: CreateRumorFromTemplateRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Creator user ID"),
    db: Session = Depends(get_db_session)
):
    """Create a rumor from a template."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        rumor = rumor_service.create_from_template(
            creator_id=x_user_id,
            theatre_id=theatre_id,
            template_id=request.template_id,
            fill_values=request.fill_values,
            source=request.source,
            tone=request.tone,
            based_on_evidence_ids=request.based_on_evidence_ids
        )
        
        return RumorResponse(
            rumor_id=rumor.rumor_id,
            creator_id=rumor.creator_id,
            theatre_id=rumor.theatre_id,
            content=rumor.content,
            category=rumor.category.value,
            source=rumor.source.value,
            tone=rumor.tone.value,
            status=rumor.status.value,
            credibility_score=rumor.credibility_score,
            spread_count=rumor.spread_count,
            view_count=rumor.view_count,
            influence_score=rumor.influence_score,
            created_at=rumor.created_at.isoformat(),
            expires_at=rumor.expires_at.isoformat() if rumor.expires_at else None,
            is_misread=rumor.is_misread
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create rumor from template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/rumors/{rumor_id}", response_model=RumorResponse, tags=["Rumor"])
async def get_rumor(
    rumor_id: str = Path(..., description="Rumor ID"),
    db: Session = Depends(get_db_session)
):
    """Get rumor details."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        rumor = rumor_service.get_rumor(rumor_id)
        
        if not rumor:
            raise HTTPException(status_code=404, detail="Rumor not found")
        
        return RumorResponse(
            rumor_id=rumor.rumor_id,
            creator_id=rumor.creator_id,
            theatre_id=rumor.theatre_id,
            content=rumor.content,
            category=rumor.category.value,
            source=rumor.source.value,
            tone=rumor.tone.value,
            status=rumor.status.value,
            credibility_score=rumor.credibility_score,
            spread_count=rumor.spread_count,
            view_count=rumor.view_count,
            influence_score=rumor.influence_score,
            created_at=rumor.created_at.isoformat(),
            expires_at=rumor.expires_at.isoformat() if rumor.expires_at else None,
            is_misread=rumor.is_misread,
            verification_outcome=rumor.verification_outcome.value if rumor.verification_outcome else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rumor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/rumors/broadcast", response_model=List[RumorResponse], tags=["Rumor"])
async def get_broadcast_rumors(
    theatre_id: str = Path(..., description="Theatre ID"),
    stage_tag: Optional[str] = Query(default=None, description="Filter by stage tag"),
    limit: int = Query(default=20, description="Maximum results"),
    db: Session = Depends(get_db_session)
):
    """Get broadcast rumors for a theatre."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        rumors = rumor_service.get_broadcast_rumors(
            theatre_id=theatre_id,
            stage_tag=stage_tag,
            limit=limit
        )
        
        return [
            RumorResponse(
                rumor_id=r.rumor_id,
                creator_id=r.creator_id,
                theatre_id=r.theatre_id,
                content=r.content,
                category=r.category.value,
                source=r.source.value,
                tone=r.tone.value,
                status=r.status.value,
                credibility_score=r.credibility_score,
                spread_count=r.spread_count,
                view_count=r.view_count,
                influence_score=r.influence_score,
                created_at=r.created_at.isoformat(),
                expires_at=r.expires_at.isoformat() if r.expires_at else None,
                is_misread=r.is_misread
            )
            for r in rumors
        ]
    except Exception as e:
        logger.error(f"Failed to get broadcast rumors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/rumors", response_model=List[RumorResponse], tags=["Rumor"])
async def get_user_rumors(
    user_id: str = Path(..., description="User ID"),
    include_expired: bool = Query(default=False, description="Include expired rumors"),
    db: Session = Depends(get_db_session)
):
    """Get rumors created by a user."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        rumors = rumor_service.get_user_rumors(
            user_id=user_id,
            include_expired=include_expired
        )
        
        return [
            RumorResponse(
                rumor_id=r.rumor_id,
                creator_id=r.creator_id,
                theatre_id=r.theatre_id,
                content=r.content,
                category=r.category.value,
                source=r.source.value,
                tone=r.tone.value,
                status=r.status.value,
                credibility_score=r.credibility_score,
                spread_count=r.spread_count,
                view_count=r.view_count,
                influence_score=r.influence_score,
                created_at=r.created_at.isoformat(),
                expires_at=r.expires_at.isoformat() if r.expires_at else None,
                is_misread=r.is_misread
            )
            for r in rumors
        ]
    except Exception as e:
        logger.error(f"Failed to get user rumors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rumors/{rumor_id}/share", response_model=ShareRumorResponse, tags=["Rumor"])
async def share_rumor(
    rumor_id: str = Path(..., description="Rumor ID"),
    request: ShareRumorRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Sharer user ID"),
    db: Session = Depends(get_db_session)
):
    """Share a rumor with another user or crew."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        share = rumor_service.share_rumor(
            rumor_id=rumor_id,
            from_user_id=x_user_id,
            to_user_id=request.to_user_id,
            to_crew_id=request.to_crew_id
        )
        
        return ShareRumorResponse(
            share_id=share.share_id,
            rumor_id=share.rumor_id,
            from_user_id=share.from_user_id,
            to_user_id=share.to_user_id,
            to_crew_id=share.to_crew_id,
            is_broadcast=share.is_broadcast,
            shared_at=share.shared_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to share rumor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rumors/{rumor_id}/broadcast", response_model=ShareRumorResponse, tags=["Rumor"])
async def broadcast_rumor(
    rumor_id: str = Path(..., description="Rumor ID"),
    x_user_id: str = Header(..., alias="X-User-ID", description="Broadcaster user ID"),
    db: Session = Depends(get_db_session)
):
    """Broadcast a rumor publicly."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        share = rumor_service.broadcast_rumor(
            rumor_id=rumor_id,
            user_id=x_user_id
        )
        
        return ShareRumorResponse(
            share_id=share.share_id,
            rumor_id=share.rumor_id,
            from_user_id=share.from_user_id,
            to_user_id=share.to_user_id,
            to_crew_id=share.to_crew_id,
            is_broadcast=share.is_broadcast,
            shared_at=share.shared_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to broadcast rumor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rumors/{rumor_id}/verify", response_model=VerifyRumorResponse, tags=["Rumor"])
async def verify_rumor(
    rumor_id: str = Path(..., description="Rumor ID"),
    request: VerifyRumorRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Verifier user ID"),
    db: Session = Depends(get_db_session)
):
    """Verify a rumor against the truth."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        outcome, echo = rumor_service.verify_rumor(
            rumor_id=rumor_id,
            verifier_id=x_user_id,
            actual_truth=request.actual_truth,
            is_accurate=request.is_accurate,
            deviation_type=request.deviation_type
        )
        
        return VerifyRumorResponse(
            outcome=outcome.value,
            echo_id=echo.echo_id if echo else None,
            consequence=echo.consequence_description if echo else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to verify rumor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rumors/{rumor_id}/reactions", response_model=ReactionResponse, tags=["Rumor"])
async def add_reaction(
    rumor_id: str = Path(..., description="Rumor ID"),
    request: AddReactionRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Add a reaction to a rumor."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        reaction = rumor_service.add_reaction(
            rumor_id=rumor_id,
            user_id=x_user_id,
            reaction_type=request.reaction_type,
            comment=request.comment
        )
        
        return ReactionResponse(
            reaction_id=reaction.reaction_id,
            rumor_id=reaction.rumor_id,
            user_id=reaction.user_id,
            reaction_type=reaction.reaction_type,
            created_at=reaction.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add reaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/heat-map", response_model=Dict[str, float], tags=["Rumor"])
async def get_heat_map(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get stage heat map based on rumors."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        heat_map = rumor_service.get_heat_map(theatre_id)
        
        return heat_map
    except Exception as e:
        logger.error(f"Failed to get heat map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/stages/{stage_tag}/heat", response_model=StageHeatResponse, tags=["Rumor"])
async def get_stage_heat(
    stage_tag: str = Path(..., description="Stage tag"),
    db: Session = Depends(get_db_session)
):
    """Get heat details for a specific stage."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        heat_data = rumor_service.get_stage_heat(stage_tag)
        
        return StageHeatResponse(**heat_data)
    except Exception as e:
        logger.error(f"Failed to get stage heat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/rumors/stats", response_model=RumorStatsResponse, tags=["Rumor"])
async def get_rumor_stats(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get rumor system statistics."""
    try:
        from rumor.src.rumor_service import RumorService
        
        rumor_service = RumorService(db)
        stats = rumor_service.get_statistics(theatre_id)
        
        return RumorStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get rumor stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# =============================================================================
# Trace System API Endpoints
# =============================================================================

# --- Trace Models ---
class LeaveTraceRequest(BaseModel):
    trace_type: str = Field(..., description="Trace type: VISIT, OBSERVE, VOTE, TRADE, RUMOR, DISCOVER, SUBMIT, CREW_ACTION")
    stage_id: str = Field(..., description="Stage ID where trace is left")
    stage_tag: str = Field(..., description="Stage tag")
    description: str = Field(default="", description="Trace description")
    related_scene_id: Optional[str] = Field(default=None, description="Related scene ID")
    related_gate_id: Optional[str] = Field(default=None, description="Related gate ID")
    related_evidence_id: Optional[str] = Field(default=None, description="Related evidence ID")
    related_rumor_id: Optional[str] = Field(default=None, description="Related rumor ID")
    visibility: Optional[str] = Field(default=None, description="Visibility: PUBLIC, RING_A, RING_B, CREW_ONLY, PRIVATE")
    metadata: Optional[Dict] = Field(default=None, description="Additional metadata")


class TraceResponse(BaseModel):
    trace_id: str
    theatre_id: str
    creator_id: str
    trace_type: str
    stage_id: str
    stage_tag: str
    status: str
    visibility: str
    intensity: float
    decay_rate: float
    discovery_difficulty: float
    discovery_count: int
    description: str
    created_at: str
    expires_at: Optional[str]


class DiscoverTraceRequest(BaseModel):
    method: str = Field(default="PROXIMITY", description="Discovery method: PROXIMITY, SEARCH, RANDOM, CREW_SHARE, SYSTEM")
    discoverer_ring: str = Field(default="C", description="Discoverer's ring level")
    discoverer_stage_id: Optional[str] = Field(default=None, description="Discoverer's current stage")


class TraceDiscoveryResponse(BaseModel):
    discovery_id: str
    trace_id: str
    discoverer_id: str
    method: str
    discovered_at: str
    converted_to_evidence: bool
    evidence_instance_id: Optional[str]


class SearchTracesRequest(BaseModel):
    stage_id: str = Field(..., description="Stage to search")
    search_intensity: float = Field(default=0.5, description="Search intensity 0-1")
    searcher_ring: str = Field(default="C", description="Searcher's ring level")


class SearchTraceResult(BaseModel):
    trace_id: str
    trace_type: str
    intensity: float
    discovery_probability: float
    description: str


class StageDensityResponse(BaseModel):
    stage_id: str
    stage_tag: str
    total_traces: int
    active_traces: int
    total_intensity: float
    density_score: float
    type_distribution: Dict[str, int]
    last_trace_at: Optional[str]
    recent_discoveries: int


class UserTraceProfileResponse(BaseModel):
    user_id: str
    theatre_id: str
    traces_left: int
    traces_active: int
    traces_discovered: int
    evidence_converted: int
    frequent_stages: List[str]
    active_hours: Dict[int, int]


class TraceStatsResponse(BaseModel):
    total_traces: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    total_intensity: float
    average_intensity: float
    total_discoveries: int
    unique_discoverers: int


@app.post("/v1/theatres/{theatre_id}/traces", response_model=TraceResponse, tags=["Trace"])
async def leave_trace(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: LeaveTraceRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Leave a trace at a stage."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        trace = trace_service.leave_trace(
            theatre_id=theatre_id,
            creator_id=x_user_id,
            trace_type=request.trace_type,
            stage_id=request.stage_id,
            stage_tag=request.stage_tag,
            description=request.description,
            related_scene_id=request.related_scene_id,
            related_gate_id=request.related_gate_id,
            related_evidence_id=request.related_evidence_id,
            related_rumor_id=request.related_rumor_id,
            visibility=request.visibility,
            metadata=request.metadata
        )
        
        return TraceResponse(**trace.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to leave trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/traces/{trace_id}", response_model=TraceResponse, tags=["Trace"])
async def get_trace(
    trace_id: str = Path(..., description="Trace ID"),
    db: Session = Depends(get_db_session)
):
    """Get trace details."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        trace = trace_service.get_trace(trace_id)
        
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return TraceResponse(**trace.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/traces", response_model=List[TraceResponse], tags=["Trace"])
async def get_user_traces(
    user_id: str = Path(..., description="User ID"),
    include_faded: bool = Query(default=False, description="Include faded traces"),
    db: Session = Depends(get_db_session)
):
    """Get traces left by a user."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        traces = trace_service.get_user_traces(user_id, include_faded)
        
        return [TraceResponse(**t.to_dict()) for t in traces]
    except Exception as e:
        logger.error(f"Failed to get user traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/stages/{stage_id}/traces", response_model=List[TraceResponse], tags=["Trace"])
async def get_stage_traces(
    stage_id: str = Path(..., description="Stage ID"),
    viewer_ring: str = Query(default="C", description="Viewer's ring level"),
    include_faded: bool = Query(default=False, description="Include faded traces"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID", description="Viewer user ID"),
    db: Session = Depends(get_db_session)
):
    """Get traces at a stage."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        traces = trace_service.get_stage_traces(
            stage_id=stage_id,
            viewer_id=x_user_id,
            viewer_ring=viewer_ring,
            include_faded=include_faded
        )
        
        return [TraceResponse(**t.to_dict()) for t in traces]
    except Exception as e:
        logger.error(f"Failed to get stage traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/traces/{trace_id}/discover", response_model=TraceDiscoveryResponse, tags=["Trace"])
async def discover_trace(
    trace_id: str = Path(..., description="Trace ID"),
    request: DiscoverTraceRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Discoverer user ID"),
    db: Session = Depends(get_db_session)
):
    """Discover a trace."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        discovery, evidence_info = trace_service.discover_trace(
            trace_id=trace_id,
            discoverer_id=x_user_id,
            method=request.method,
            discoverer_ring=request.discoverer_ring,
            discoverer_stage_id=request.discoverer_stage_id
        )
        
        return TraceDiscoveryResponse(**discovery.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to discover trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/theatres/{theatre_id}/traces/search", response_model=List[SearchTraceResult], tags=["Trace"])
async def search_traces(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: SearchTracesRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Searcher user ID"),
    db: Session = Depends(get_db_session)
):
    """Search for traces at a stage."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        results = trace_service.search_traces(
            theatre_id=theatre_id,
            searcher_id=x_user_id,
            stage_id=request.stage_id,
            searcher_ring=request.searcher_ring,
            search_intensity=request.search_intensity
        )
        
        return [
            SearchTraceResult(
                trace_id=trace.trace_id,
                trace_type=trace.trace_type.value,
                intensity=trace.intensity,
                discovery_probability=prob,
                description=trace.description
            )
            for trace, prob in results
        ]
    except Exception as e:
        logger.error(f"Failed to search traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/stages/{stage_id}/density", response_model=StageDensityResponse, tags=["Trace"])
async def get_stage_density(
    stage_id: str = Path(..., description="Stage ID"),
    stage_tag: str = Query(..., description="Stage tag"),
    db: Session = Depends(get_db_session)
):
    """Get trace density for a stage."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        density = trace_service.get_stage_density(stage_id, stage_tag)
        
        return StageDensityResponse(**density.to_dict())
    except Exception as e:
        logger.error(f"Failed to get stage density: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/density-map", tags=["Trace"])
async def get_density_map(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get trace density map for a theatre."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        density_map = trace_service.get_density_map(theatre_id)
        
        return density_map
    except Exception as e:
        logger.error(f"Failed to get density map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/trace-profile", response_model=UserTraceProfileResponse, tags=["Trace"])
async def get_user_trace_profile(
    user_id: str = Path(..., description="User ID"),
    theatre_id: str = Query(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get user's trace profile."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        profile = trace_service.get_user_profile(user_id, theatre_id)
        
        return UserTraceProfileResponse(**profile.to_dict())
    except Exception as e:
        logger.error(f"Failed to get user trace profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/admin/theatres/{theatre_id}/traces/decay", tags=["Admin"])
async def process_trace_decay(
    theatre_id: str = Path(..., description="Theatre ID"),
    hours_passed: float = Query(default=1.0, description="Hours passed"),
    db: Session = Depends(get_db_session)
):
    """Admin: Process trace decay for a theatre."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        result = trace_service.process_decay(theatre_id, hours_passed)
        
        return result
    except Exception as e:
        logger.error(f"Failed to process trace decay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/traces/stats", response_model=TraceStatsResponse, tags=["Trace"])
async def get_trace_stats(
    theatre_id: str = Path(..., description="Theatre ID"),
    db: Session = Depends(get_db_session)
):
    """Get trace system statistics."""
    try:
        trace_service = get_service(TRACE_SERVICE, TraceService, db)
        stats = trace_service.get_statistics(theatre_id)
        
        return TraceStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get trace stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Crew System API Endpoints
# =============================================================================

# --- Crew Models ---
class CreateCrewRequest(BaseModel):
    name: str = Field(..., description="Crew name")
    tag: str = Field(..., description="Crew tag (3-5 characters)")
    description: str = Field(default="", description="Crew description")
    motto: str = Field(default="", description="Crew motto")
    is_public: bool = Field(default=True, description="Whether crew is publicly recruitable")


class CrewResponse(BaseModel):
    crew_id: str
    theatre_id: str
    name: str
    tag: str
    description: str
    motto: str
    icon_url: Optional[str]
    status: str
    tier: int
    reputation: int
    total_contribution: int
    member_count: int
    is_public: bool
    auto_approve: bool
    min_level_required: int
    created_at: str
    last_active_at: str


class CrewMemberResponse(BaseModel):
    member_id: str
    crew_id: str
    user_id: str
    role: str
    status: str
    contribution: int
    actions_participated: int
    shares_made: int
    joined_at: str
    last_active_at: str
    nickname: Optional[str]


class JoinApplicationRequest(BaseModel):
    message: str = Field(default="", description="Application message")


class JoinApplicationResponse(BaseModel):
    application_id: str
    crew_id: str
    applicant_id: str
    message: str
    status: str
    processed_by: Optional[str]
    applied_at: str


class ProcessApplicationRequest(BaseModel):
    approve: bool = Field(..., description="Whether to approve the application")
    rejection_reason: str = Field(default="", description="Reason for rejection")


class PromoteMemberRequest(BaseModel):
    new_role: str = Field(..., description="New role: LEADER, OFFICER, MEMBER, RECRUIT")


class ProposeActionRequest(BaseModel):
    action_type: str = Field(..., description="Action type: VOTE, INVESTIGATE, SHARE, RAID, DEFEND")
    title: str = Field(..., description="Action title")
    description: str = Field(..., description="Action description")
    target_stage_id: Optional[str] = Field(default=None, description="Target stage ID")
    target_gate_id: Optional[str] = Field(default=None, description="Target gate ID")
    cost_per_participant: int = Field(default=0, description="Cost per participant")


class CrewActionResponse(BaseModel):
    action_id: str
    crew_id: str
    theatre_id: str
    action_type: str
    title: str
    description: str
    target_stage_id: Optional[str]
    target_gate_id: Optional[str]
    status: str
    proposer_id: str
    votes_required: int
    votes_for: int
    votes_against: int
    participant_count: int
    min_participants: int
    max_participants: int
    cost_per_participant: int
    success_rate: float
    outcome: Optional[str]
    created_at: str
    voting_deadline: Optional[str]
    execution_time: Optional[str]


class VoteOnActionRequest(BaseModel):
    vote_for: bool = Field(..., description="Whether to vote for the action")


class ShareResourceRequest(BaseModel):
    share_type: str = Field(..., description="Share type: EVIDENCE, RUMOR, TRACE, CURRENCY")
    resource_id: str = Field(..., description="Resource ID to share")
    recipient_ids: Optional[List[str]] = Field(default=None, description="Specific recipients (empty for all)")
    message: str = Field(default="", description="Share message")
    expiry_hours: int = Field(default=24, description="Hours until expiry")


class CrewShareResponse(BaseModel):
    share_id: str
    crew_id: str
    sharer_id: str
    share_type: str
    resource_id: str
    recipient_ids: List[str]
    is_claimed: bool
    claimed_count: int
    shared_at: str
    expires_at: Optional[str]
    message: str


class CrewStatsResponse(BaseModel):
    crew_id: str
    name: str
    tag: str
    tier: int
    reputation: int
    member_count: int
    role_distribution: Dict[str, int]
    total_contribution: int
    action_stats: Dict[str, int]
    total_actions: int
    total_shares: int


class CrewLeaderboardEntry(BaseModel):
    rank: int
    crew_id: str
    name: str
    tag: str
    tier: int
    reputation: int
    member_count: int


@app.post("/v1/theatres/{theatre_id}/crews", response_model=CrewResponse, tags=["Crew"])
async def create_crew(
    theatre_id: str = Path(..., description="Theatre ID"),
    request: CreateCrewRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Creator user ID"),
    db: Session = Depends(get_db_session)
):
    """Create a new crew."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        crew, member = crew_service.create_crew(
            theatre_id=theatre_id,
            creator_id=x_user_id,
            name=request.name,
            tag=request.tag,
            description=request.description,
            motto=request.motto,
            is_public=request.is_public
        )
        
        return CrewResponse(**crew.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/crews/{crew_id}", response_model=CrewResponse, tags=["Crew"])
async def get_crew(
    crew_id: str = Path(..., description="Crew ID"),
    db: Session = Depends(get_db_session)
):
    """Get crew details."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        crew = crew_service.get_crew(crew_id)
        
        if not crew:
            raise HTTPException(status_code=404, detail="Crew not found")
        
        return CrewResponse(**crew.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/crews", response_model=List[CrewResponse], tags=["Crew"])
async def list_crews(
    theatre_id: str = Path(..., description="Theatre ID"),
    public_only: bool = Query(default=True, description="Only show public crews"),
    limit: int = Query(default=20, description="Max results"),
    db: Session = Depends(get_db_session)
):
    """List crews in a theatre."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        crews = crew_service.list_crews(theatre_id, public_only, limit)
        
        return [CrewResponse(**c.to_dict()) for c in crews]
    except Exception as e:
        logger.error(f"Failed to list crews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/crews/{crew_id}/members", response_model=List[CrewMemberResponse], tags=["Crew"])
async def get_crew_members(
    crew_id: str = Path(..., description="Crew ID"),
    db: Session = Depends(get_db_session)
):
    """Get crew members."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        members = crew_service.get_members(crew_id)
        
        return [CrewMemberResponse(**m.to_dict()) for m in members]
    except Exception as e:
        logger.error(f"Failed to get crew members: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/crew", tags=["Crew"])
async def get_user_crew(
    user_id: str = Path(..., description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Get user's current crew."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        result = crew_service.get_user_crew(user_id)
        
        if not result:
            return {"crew": None, "member": None}
        
        crew, member = result
        return {
            "crew": crew.to_dict(),
            "member": member.to_dict()
        }
    except Exception as e:
        logger.error(f"Failed to get user crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/applications", response_model=JoinApplicationResponse, tags=["Crew"])
async def apply_to_join_crew(
    crew_id: str = Path(..., description="Crew ID"),
    request: JoinApplicationRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Applicant user ID"),
    db: Session = Depends(get_db_session)
):
    """Apply to join a crew."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        application = crew_service.apply_to_join(
            crew_id=crew_id,
            applicant_id=x_user_id,
            message=request.message
        )
        
        return JoinApplicationResponse(**application.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to apply to crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/applications/{application_id}/process", response_model=JoinApplicationResponse, tags=["Crew"])
async def process_application(
    application_id: str = Path(..., description="Application ID"),
    request: ProcessApplicationRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Processor user ID"),
    db: Session = Depends(get_db_session)
):
    """Process a join application."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        application = crew_service.process_application(
            application_id=application_id,
            processor_id=x_user_id,
            approve=request.approve,
            rejection_reason=request.rejection_reason
        )
        
        return JoinApplicationResponse(**application.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/invite", response_model=CrewMemberResponse, tags=["Crew"])
async def invite_member(
    crew_id: str = Path(..., description="Crew ID"),
    invitee_id: str = Query(..., description="User ID to invite"),
    x_user_id: str = Header(..., alias="X-User-ID", description="Inviter user ID"),
    db: Session = Depends(get_db_session)
):
    """Invite a user to join the crew."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        member = crew_service.invite_member(
            crew_id=crew_id,
            inviter_id=x_user_id,
            invitee_id=invitee_id
        )
        
        return CrewMemberResponse(**member.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to invite member: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/leave", tags=["Crew"])
async def leave_crew(
    crew_id: str = Path(..., description="Crew ID"),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Leave a crew."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        crew_service.leave_crew(crew_id, x_user_id)
        
        return {"success": True, "message": "Left crew successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to leave crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/kick", tags=["Crew"])
async def kick_member(
    crew_id: str = Path(..., description="Crew ID"),
    target_user_id: str = Query(..., description="User ID to kick"),
    reason: str = Query(default="", description="Reason for kicking"),
    x_user_id: str = Header(..., alias="X-User-ID", description="Operator user ID"),
    db: Session = Depends(get_db_session)
):
    """Kick a member from the crew."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        crew_service.kick_member(crew_id, x_user_id, target_user_id, reason)
        
        return {"success": True, "message": "Member kicked successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to kick member: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/promote", response_model=CrewMemberResponse, tags=["Crew"])
async def promote_member(
    crew_id: str = Path(..., description="Crew ID"),
    target_user_id: str = Query(..., description="User ID to promote"),
    request: PromoteMemberRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Operator user ID"),
    db: Session = Depends(get_db_session)
):
    """Promote a crew member."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        member = crew_service.promote_member(
            crew_id=crew_id,
            operator_id=x_user_id,
            target_user_id=target_user_id,
            new_role=request.new_role
        )
        
        return CrewMemberResponse(**member.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to promote member: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/disband", tags=["Crew"])
async def disband_crew(
    crew_id: str = Path(..., description="Crew ID"),
    x_user_id: str = Header(..., alias="X-User-ID", description="Leader user ID"),
    db: Session = Depends(get_db_session)
):
    """Disband a crew (leader only)."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        crew_service.disband_crew(crew_id, x_user_id)
        
        return {"success": True, "message": "Crew disbanded successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to disband crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/actions", response_model=CrewActionResponse, tags=["Crew"])
async def propose_action(
    crew_id: str = Path(..., description="Crew ID"),
    request: ProposeActionRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Proposer user ID"),
    db: Session = Depends(get_db_session)
):
    """Propose a crew action."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        action = crew_service.propose_action(
            crew_id=crew_id,
            proposer_id=x_user_id,
            action_type=request.action_type,
            title=request.title,
            description=request.description,
            target_stage_id=request.target_stage_id,
            target_gate_id=request.target_gate_id,
            cost_per_participant=request.cost_per_participant
        )
        
        return CrewActionResponse(**action.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to propose action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/crews/{crew_id}/actions", response_model=List[CrewActionResponse], tags=["Crew"])
async def get_crew_actions(
    crew_id: str = Path(..., description="Crew ID"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    db: Session = Depends(get_db_session)
):
    """Get crew actions."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        actions = crew_service.get_crew_actions(crew_id, status)
        
        return [CrewActionResponse(**a.to_dict()) for a in actions]
    except Exception as e:
        logger.error(f"Failed to get crew actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/actions/{action_id}/vote", response_model=CrewActionResponse, tags=["Crew"])
async def vote_on_action(
    action_id: str = Path(..., description="Action ID"),
    request: VoteOnActionRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Voter user ID"),
    db: Session = Depends(get_db_session)
):
    """Vote on a crew action."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        action = crew_service.vote_on_action(
            action_id=action_id,
            voter_id=x_user_id,
            vote_for=request.vote_for
        )
        
        return CrewActionResponse(**action.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to vote on action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/actions/{action_id}/join", response_model=CrewActionResponse, tags=["Crew"])
async def join_action(
    action_id: str = Path(..., description="Action ID"),
    x_user_id: str = Header(..., alias="X-User-ID", description="Participant user ID"),
    db: Session = Depends(get_db_session)
):
    """Join a crew action."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        action = crew_service.join_action(action_id, x_user_id)
        
        return CrewActionResponse(**action.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to join action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/admin/crews/actions/{action_id}/execute", response_model=CrewActionResponse, tags=["Admin"])
async def execute_action(
    action_id: str = Path(..., description="Action ID"),
    db: Session = Depends(get_db_session)
):
    """Admin: Execute a crew action."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        action = crew_service.execute_action(action_id)
        
        return CrewActionResponse(**action.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/{crew_id}/shares", response_model=CrewShareResponse, tags=["Crew"])
async def share_resource(
    crew_id: str = Path(..., description="Crew ID"),
    request: ShareResourceRequest = Body(...),
    x_user_id: str = Header(..., alias="X-User-ID", description="Sharer user ID"),
    db: Session = Depends(get_db_session)
):
    """Share a resource with the crew."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        share = crew_service.share_resource(
            crew_id=crew_id,
            sharer_id=x_user_id,
            share_type=request.share_type,
            resource_id=request.resource_id,
            recipient_ids=request.recipient_ids,
            message=request.message,
            expiry_hours=request.expiry_hours
        )
        
        return CrewShareResponse(**share.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to share resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/crews/{crew_id}/shares", response_model=List[CrewShareResponse], tags=["Crew"])
async def get_crew_shares(
    crew_id: str = Path(..., description="Crew ID"),
    include_expired: bool = Query(default=False, description="Include expired shares"),
    x_user_id: str = Header(..., alias="X-User-ID", description="User ID"),
    db: Session = Depends(get_db_session)
):
    """Get crew shares."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        shares = crew_service.get_crew_shares(crew_id, x_user_id, include_expired)
        
        return [CrewShareResponse(**s.to_dict()) for s in shares]
    except Exception as e:
        logger.error(f"Failed to get crew shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/crews/shares/{share_id}/claim", response_model=CrewShareResponse, tags=["Crew"])
async def claim_share(
    share_id: str = Path(..., description="Share ID"),
    x_user_id: str = Header(..., alias="X-User-ID", description="Claimer user ID"),
    db: Session = Depends(get_db_session)
):
    """Claim a shared resource."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        share = crew_service.claim_share(share_id, x_user_id)
        
        return CrewShareResponse(**share.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to claim share: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/crews/{crew_id}/stats", response_model=CrewStatsResponse, tags=["Crew"])
async def get_crew_stats(
    crew_id: str = Path(..., description="Crew ID"),
    db: Session = Depends(get_db_session)
):
    """Get crew statistics."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        stats = crew_service.get_crew_statistics(crew_id)
        
        return CrewStatsResponse(**stats)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get crew stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/theatres/{theatre_id}/crews/leaderboard", response_model=List[CrewLeaderboardEntry], tags=["Crew"])
async def get_crew_leaderboard(
    theatre_id: str = Path(..., description="Theatre ID"),
    limit: int = Query(default=10, description="Max results"),
    db: Session = Depends(get_db_session)
):
    """Get crew leaderboard."""
    try:
        crew_service = get_service(CREW_SERVICE, CrewService, db)
        leaderboard = crew_service.get_leaderboard(theatre_id, limit)
        
        return [CrewLeaderboardEntry(**entry) for entry in leaderboard]
    except Exception as e:
        logger.error(f"Failed to get crew leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# M4 System Imports
# =============================================================================
from analytics.src.analytics_service import AnalyticsService, EventType
from liveops.src.liveops_service import (
    LiveOpsService, CampaignType, CampaignStatus, 
    NotificationType, AnnouncementType
)
from safety.src.safety_service import (
    SafetyService, ContentType, ModerationStatus,
    ReportType, PunishmentType, RiskLevel
)
from admin.src.admin_service import AdminService, AdminRole, AlertSeverity

# Initialize M4 services (singletons)
_analytics_service = None
_liveops_service = None
_safety_service = None
_admin_service = None

def get_analytics_service():
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service

def get_liveops_service():
    global _liveops_service
    if _liveops_service is None:
        _liveops_service = LiveOpsService()
    return _liveops_service

def get_safety_service():
    global _safety_service
    if _safety_service is None:
        _safety_service = SafetyService()
    return _safety_service

def get_admin_service():
    global _admin_service
    if _admin_service is None:
        _admin_service = AdminService()
    return _admin_service


# =============================================================================
# M4 Pydantic Models
# =============================================================================

# --- Analytics ---
class TrackEventRequest(BaseModel):
    user_id: str
    event_type: str
    event_name: str
    properties: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

class QueryMetricsRequest(BaseModel):
    metric_name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    dimensions: Optional[Dict[str, str]] = None

# --- LiveOps ---
class CreateCampaignRequest(BaseModel):
    name: str
    campaign_type: str
    description: str
    start_time: str
    end_time: str
    rewards: Optional[List[Dict[str, Any]]] = None
    target_value: int = 1
    min_level: int = 1

class CreateNotificationRequest(BaseModel):
    notification_type: str
    title: str
    content: str
    target_user_ids: Optional[List[str]] = None
    scheduled_time: Optional[str] = None
    deep_link: Optional[str] = None

class CreateAnnouncementRequest(BaseModel):
    announcement_type: str
    title: str
    content: str
    priority: int = 0
    is_pinned: bool = False
    is_popup: bool = False
    expire_time: Optional[str] = None

class CreateABTestRequest(BaseModel):
    name: str
    description: str
    feature_key: str
    variants: List[Dict[str, Any]]

class SetConfigRequest(BaseModel):
    config_key: str
    value: Any
    description: Optional[str] = None

# --- Safety ---
class SubmitModerationRequest(BaseModel):
    content_type: str
    content_id: str
    content_text: str
    creator_id: str

class ManualModerateRequest(BaseModel):
    moderator_id: str
    approve: bool
    reason: Optional[str] = None
    notes: Optional[str] = None

class SubmitReportRequest(BaseModel):
    reporter_id: str
    report_type: str
    target_user_id: Optional[str] = None
    target_content_id: Optional[str] = None
    target_content_type: Optional[str] = None
    description: str = ""
    evidence_urls: Optional[List[str]] = None

class HandleReportRequest(BaseModel):
    handler_id: str
    resolution: str
    dismiss: bool = False
    punishment_type: Optional[str] = None
    punishment_duration: Optional[int] = None

class IssuePunishmentRequest(BaseModel):
    user_id: str
    punishment_type: str
    reason: str
    duration_hours: Optional[int] = None
    issued_by: str

class LocationCheckRequest(BaseModel):
    user_id: str
    lat: float
    lng: float

# --- Admin ---
class CreateAdminUserRequest(BaseModel):
    username: str
    email: str
    role: str
    allowed_theatres: Optional[List[str]] = None

class AdminSetConfigRequest(BaseModel):
    config_key: str
    value: Any
    description: Optional[str] = None

class CreateAlertRequest(BaseModel):
    severity: str
    title: str
    message: str
    source: str

class MaintenanceModeRequest(BaseModel):
    reason: str
    estimated_duration_minutes: int = 30


# =============================================================================
# Analytics API Endpoints
# =============================================================================

@app.post("/v1/theatres/{theatre_id}/analytics/events", tags=["Analytics"])
async def track_event(
    theatre_id: str,
    request: TrackEventRequest
):
    """追踪用户事件"""
    service = get_analytics_service()
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        # 如果事件类型无效，使用SESSION_START作为默认值
        event_type = EventType.SESSION_START
    
    # 将event_name添加到properties中
    props = request.properties or {}
    props["event_name"] = request.event_name
    
    event = service.track_event(
        theatre_id=theatre_id,
        user_id=request.user_id,
        event_type=event_type,
        properties=props,
        session_id=request.session_id
    )
    return {"success": True, "event_id": event.event_id}


@app.get("/v1/theatres/{theatre_id}/analytics/metrics/{metric_name}", tags=["Analytics"])
async def get_metric(
    theatre_id: str,
    metric_name: str,
    time_range: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d")
):
    """获取指标数据"""
    service = get_analytics_service()
    result = service.get_metric(theatre_id, metric_name, time_range)
    return result


@app.get("/v1/theatres/{theatre_id}/analytics/dashboard", tags=["Analytics"])
async def get_analytics_dashboard(theatre_id: str):
    """获取分析仪表盘"""
    service = get_analytics_service()
    data = service.get_dashboard_data(theatre_id)
    return data.to_dict()


@app.get("/v1/theatres/{theatre_id}/analytics/funnel/{funnel_name}", tags=["Analytics"])
async def get_funnel_analysis(
    theatre_id: str,
    funnel_name: str
):
    """获取漏斗分析"""
    service = get_analytics_service()
    return service.get_funnel_analysis(theatre_id, funnel_name)


@app.get("/v1/theatres/{theatre_id}/analytics/retention", tags=["Analytics"])
async def get_retention_analysis(
    theatre_id: str,
    cohort_date: Optional[str] = None
):
    """获取留存分析"""
    service = get_analytics_service()
    return service.get_retention_analysis(theatre_id, cohort_date)


@app.get("/v1/users/{user_id}/analytics/profile", tags=["Analytics"])
async def get_user_analytics_profile(user_id: str):
    """获取用户分析档案"""
    service = get_analytics_service()
    profile = service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return profile.to_dict()


# =============================================================================
# LiveOps API Endpoints
# =============================================================================

@app.post("/v1/theatres/{theatre_id}/campaigns", tags=["LiveOps"])
async def create_campaign(
    theatre_id: str,
    request: CreateCampaignRequest
):
    """创建运营活动"""
    service = get_liveops_service()
    try:
        campaign_type = CampaignType(request.campaign_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid campaign type: {request.campaign_type}")
    
    campaign = service.create_campaign(
        theatre_id=theatre_id,
        name=request.name,
        campaign_type=campaign_type,
        description=request.description,
        start_time=datetime.fromisoformat(request.start_time.replace('Z', '+00:00')),
        end_time=datetime.fromisoformat(request.end_time.replace('Z', '+00:00')),
        rewards=request.rewards,
        target_value=request.target_value,
        min_level=request.min_level
    )
    return campaign.to_dict()


@app.get("/v1/theatres/{theatre_id}/campaigns", tags=["LiveOps"])
async def list_campaigns(
    theatre_id: str,
    status: Optional[str] = None
):
    """列出活动"""
    service = get_liveops_service()
    status_enum = CampaignStatus(status) if status else None
    campaigns = service.list_campaigns(theatre_id, status=status_enum)
    return {"campaigns": [c.to_dict() for c in campaigns]}


@app.post("/v1/campaigns/{campaign_id}/activate", tags=["LiveOps"])
async def activate_campaign(campaign_id: str):
    """激活活动"""
    service = get_liveops_service()
    campaign = service.activate_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.to_dict()


@app.post("/v1/campaigns/{campaign_id}/join", tags=["LiveOps"])
async def join_campaign(
    campaign_id: str,
    user_id: str = Query(..., description="User ID")
):
    """加入活动"""
    service = get_liveops_service()
    progress = service.join_campaign(user_id, campaign_id)
    if not progress:
        raise HTTPException(status_code=400, detail="Cannot join campaign")
    return progress.to_dict()


@app.post("/v1/campaigns/{campaign_id}/progress", tags=["LiveOps"])
async def update_campaign_progress(
    campaign_id: str,
    user_id: str = Query(..., description="User ID"),
    increment: int = Query(1, description="Progress increment")
):
    """更新活动进度"""
    service = get_liveops_service()
    progress = service.update_progress(user_id, campaign_id, increment)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress.to_dict()


@app.post("/v1/campaigns/{campaign_id}/claim", tags=["LiveOps"])
async def claim_campaign_rewards(
    campaign_id: str,
    user_id: str = Query(..., description="User ID")
):
    """领取活动奖励"""
    service = get_liveops_service()
    rewards = service.claim_rewards(user_id, campaign_id)
    if rewards is None:
        raise HTTPException(status_code=400, detail="Cannot claim rewards")
    return {"rewards": [r.to_dict() for r in rewards]}


@app.get("/v1/users/{user_id}/campaigns", tags=["LiveOps"])
async def get_user_campaigns(
    user_id: str,
    theatre_id: str = Query(..., description="Theatre ID")
):
    """获取用户可参与的活动"""
    service = get_liveops_service()
    campaigns = service.get_active_campaigns_for_user(theatre_id, user_id)
    return {"campaigns": campaigns}


@app.post("/v1/theatres/{theatre_id}/notifications", tags=["LiveOps"])
async def create_notification(
    theatre_id: str,
    request: CreateNotificationRequest
):
    """创建通知"""
    service = get_liveops_service()
    try:
        notification_type = NotificationType(request.notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid notification type")
    
    scheduled = None
    if request.scheduled_time:
        scheduled = datetime.fromisoformat(request.scheduled_time.replace('Z', '+00:00'))
    
    notification = service.create_notification(
        theatre_id=theatre_id,
        notification_type=notification_type,
        title=request.title,
        content=request.content,
        target_user_ids=request.target_user_ids,
        scheduled_time=scheduled,
        deep_link=request.deep_link
    )
    return notification.to_dict()


@app.post("/v1/notifications/{notification_id}/send", tags=["LiveOps"])
async def send_notification(notification_id: str):
    """发送通知"""
    service = get_liveops_service()
    notification = service.send_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification.to_dict()


@app.post("/v1/theatres/{theatre_id}/announcements", tags=["LiveOps"])
async def create_announcement(
    theatre_id: str,
    request: CreateAnnouncementRequest
):
    """创建公告"""
    service = get_liveops_service()
    try:
        announcement_type = AnnouncementType(request.announcement_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid announcement type")
    
    expire = None
    if request.expire_time:
        expire = datetime.fromisoformat(request.expire_time.replace('Z', '+00:00'))
    
    announcement = service.create_announcement(
        theatre_id=theatre_id,
        announcement_type=announcement_type,
        title=request.title,
        content=request.content,
        priority=request.priority,
        is_pinned=request.is_pinned,
        is_popup=request.is_popup,
        expire_time=expire
    )
    return announcement.to_dict()


@app.get("/v1/theatres/{theatre_id}/announcements", tags=["LiveOps"])
async def get_announcements(theatre_id: str):
    """获取公告列表"""
    service = get_liveops_service()
    announcements = service.get_active_announcements(theatre_id)
    return {"announcements": [a.to_dict() for a in announcements]}


@app.post("/v1/theatres/{theatre_id}/ab-tests", tags=["LiveOps"])
async def create_ab_test(
    theatre_id: str,
    request: CreateABTestRequest
):
    """创建A/B测试"""
    service = get_liveops_service()
    ab_test = service.create_ab_test(
        theatre_id=theatre_id,
        name=request.name,
        description=request.description,
        feature_key=request.feature_key,
        variants=request.variants
    )
    return ab_test.to_dict()


@app.post("/v1/ab-tests/{test_id}/start", tags=["LiveOps"])
async def start_ab_test(test_id: str):
    """启动A/B测试"""
    service = get_liveops_service()
    ab_test = service.start_ab_test(test_id)
    if not ab_test:
        raise HTTPException(status_code=404, detail="A/B test not found")
    return ab_test.to_dict()


@app.get("/v1/ab-tests/{test_id}/variant", tags=["LiveOps"])
async def get_user_ab_variant(
    test_id: str,
    user_id: str = Query(..., description="User ID")
):
    """获取用户的A/B测试变体"""
    service = get_liveops_service()
    variant = service.get_user_variant(test_id, user_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant.to_dict()


@app.get("/v1/ab-tests/{test_id}/results", tags=["LiveOps"])
async def get_ab_test_results(test_id: str):
    """获取A/B测试结果"""
    service = get_liveops_service()
    results = service.get_ab_test_results(test_id)
    if not results:
        raise HTTPException(status_code=404, detail="A/B test not found")
    return results


@app.post("/v1/theatres/{theatre_id}/config", tags=["LiveOps"])
async def set_hot_config(
    theatre_id: str,
    request: SetConfigRequest
):
    """设置热更新配置"""
    service = get_liveops_service()
    config = service.set_config(
        theatre_id=theatre_id,
        config_key=request.config_key,
        value=request.value,
        description=request.description
    )
    return config.to_dict()


@app.get("/v1/theatres/{theatre_id}/config", tags=["LiveOps"])
async def get_all_hot_configs(theatre_id: str):
    """获取所有热更新配置"""
    service = get_liveops_service()
    configs = service.get_all_configs(theatre_id)
    return {"configs": configs}


@app.get("/v1/theatres/{theatre_id}/liveops/statistics", tags=["LiveOps"])
async def get_liveops_statistics(theatre_id: str):
    """获取运营统计"""
    service = get_liveops_service()
    return service.get_statistics(theatre_id)


# =============================================================================
# Safety API Endpoints
# =============================================================================

@app.post("/v1/theatres/{theatre_id}/moderation/submit", tags=["Safety"])
async def submit_for_moderation(
    theatre_id: str,
    request: SubmitModerationRequest
):
    """提交内容审核"""
    service = get_safety_service()
    try:
        content_type = ContentType(request.content_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid content type")
    
    task = service.submit_for_moderation(
        theatre_id=theatre_id,
        content_type=content_type,
        content_id=request.content_id,
        content_text=request.content_text,
        creator_id=request.creator_id
    )
    return task.to_dict()


@app.get("/v1/theatres/{theatre_id}/moderation/pending", tags=["Safety"])
async def get_pending_moderation(
    theatre_id: str,
    limit: int = Query(50, description="Max results")
):
    """获取待审核任务"""
    service = get_safety_service()
    tasks = service.get_pending_moderation_tasks(theatre_id, limit=limit)
    return {"tasks": [t.to_dict() for t in tasks]}


@app.post("/v1/moderation/{task_id}/review", tags=["Safety"])
async def manual_moderate(
    task_id: str,
    request: ManualModerateRequest
):
    """人工审核"""
    service = get_safety_service()
    reason = None
    if request.reason:
        try:
            from safety.src.safety_service import ModerationReason
            reason = ModerationReason(request.reason)
        except ValueError:
            pass
    
    task = service.manual_moderate(
        task_id=task_id,
        moderator_id=request.moderator_id,
        approve=request.approve,
        reason=reason,
        notes=request.notes
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.post("/v1/theatres/{theatre_id}/reports", tags=["Safety"])
async def submit_report(
    theatre_id: str,
    request: SubmitReportRequest
):
    """提交举报"""
    service = get_safety_service()
    try:
        report_type = ReportType(request.report_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid report type")
    
    content_type = None
    if request.target_content_type:
        try:
            content_type = ContentType(request.target_content_type)
        except ValueError:
            pass
    
    report = service.submit_report(
        theatre_id=theatre_id,
        reporter_id=request.reporter_id,
        report_type=report_type,
        target_user_id=request.target_user_id,
        target_content_id=request.target_content_id,
        target_content_type=content_type,
        description=request.description,
        evidence_urls=request.evidence_urls
    )
    return report.to_dict()


@app.get("/v1/theatres/{theatre_id}/reports/pending", tags=["Safety"])
async def get_pending_reports(
    theatre_id: str,
    limit: int = Query(50, description="Max results")
):
    """获取待处理举报"""
    service = get_safety_service()
    reports = service.get_pending_reports(theatre_id, limit=limit)
    return {"reports": [r.to_dict() for r in reports]}


@app.post("/v1/reports/{report_id}/handle", tags=["Safety"])
async def handle_report(
    report_id: str,
    request: HandleReportRequest
):
    """处理举报"""
    service = get_safety_service()
    punishment_type = None
    if request.punishment_type:
        try:
            punishment_type = PunishmentType(request.punishment_type)
        except ValueError:
            pass
    
    report, punishment = service.handle_report(
        report_id=report_id,
        handler_id=request.handler_id,
        resolution=request.resolution,
        dismiss=request.dismiss,
        punishment_type=punishment_type,
        punishment_duration=request.punishment_duration
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "report": report.to_dict(),
        "punishment": punishment.to_dict() if punishment else None
    }


@app.post("/v1/theatres/{theatre_id}/punishments", tags=["Safety"])
async def issue_punishment(
    theatre_id: str,
    request: IssuePunishmentRequest
):
    """发放处罚"""
    service = get_safety_service()
    try:
        punishment_type = PunishmentType(request.punishment_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid punishment type")
    
    punishment = service.issue_punishment(
        theatre_id=theatre_id,
        user_id=request.user_id,
        punishment_type=punishment_type,
        reason=request.reason,
        duration_hours=request.duration_hours,
        issued_by=request.issued_by
    )
    return punishment.to_dict()


@app.get("/v1/users/{user_id}/punishments", tags=["Safety"])
async def get_user_punishments(
    user_id: str,
    active_only: bool = Query(True, description="Only active punishments")
):
    """获取用户处罚记录"""
    service = get_safety_service()
    punishments = service.get_user_punishments(user_id, active_only=active_only)
    return {"punishments": [p.to_dict() for p in punishments]}


@app.get("/v1/users/{user_id}/banned", tags=["Safety"])
async def check_user_banned(user_id: str):
    """检查用户是否被封禁"""
    service = get_safety_service()
    is_banned, punishment = service.check_user_banned(user_id)
    return {
        "is_banned": is_banned,
        "punishment": punishment.to_dict() if punishment else None
    }


@app.post("/v1/theatres/{theatre_id}/anti-cheat/location", tags=["Safety"])
async def check_location_spoofing(
    theatre_id: str,
    request: LocationCheckRequest
):
    """检测位置欺骗"""
    service = get_safety_service()
    detection = service.detect_location_spoofing(
        theatre_id=theatre_id,
        user_id=request.user_id,
        current_location={"lat": request.lat, "lng": request.lng},
        timestamp=datetime.now(timezone.utc)
    )
    return {
        "spoofing_detected": detection is not None,
        "detection": detection.to_dict() if detection else None
    }


@app.get("/v1/theatres/{theatre_id}/users/{user_id}/risk-profile", tags=["Safety"])
async def get_user_risk_profile(
    theatre_id: str,
    user_id: str
):
    """获取用户风险档案"""
    service = get_safety_service()
    profile = service.get_user_risk_profile(theatre_id, user_id)
    return profile.to_dict()


@app.get("/v1/theatres/{theatre_id}/high-risk-users", tags=["Safety"])
async def get_high_risk_users(
    theatre_id: str,
    min_risk_level: str = Query("MEDIUM", description="Minimum risk level")
):
    """获取高风险用户"""
    service = get_safety_service()
    try:
        risk_level = RiskLevel(min_risk_level)
    except ValueError:
        risk_level = RiskLevel.MEDIUM
    
    users = service.get_high_risk_users(theatre_id, min_risk_level=risk_level)
    return {"users": [u.to_dict() for u in users]}


@app.get("/v1/theatres/{theatre_id}/audit-logs", tags=["Safety"])
async def get_audit_logs(
    theatre_id: str,
    action: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = Query(100, description="Max results")
):
    """获取审计日志"""
    service = get_safety_service()
    logs = service.get_audit_logs(
        theatre_id=theatre_id,
        action=action,
        actor_id=actor_id,
        limit=limit
    )
    return {"logs": [l.to_dict() for l in logs]}


@app.get("/v1/theatres/{theatre_id}/safety/statistics", tags=["Safety"])
async def get_safety_statistics(theatre_id: str):
    """获取安全统计"""
    service = get_safety_service()
    return service.get_statistics(theatre_id)


# =============================================================================
# Admin API Endpoints
# =============================================================================

@app.post("/v1/admin/users", tags=["Admin"])
async def create_admin_user(request: CreateAdminUserRequest):
    """创建管理员用户"""
    service = get_admin_service()
    try:
        role = AdminRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role")
    
    admin = service.create_admin_user(
        username=request.username,
        email=request.email,
        role=role,
        allowed_theatres=request.allowed_theatres
    )
    return admin.to_dict()


@app.get("/v1/admin/users", tags=["Admin"])
async def list_admin_users(
    role: Optional[str] = None,
    active_only: bool = Query(True, description="Only active users")
):
    """列出管理员用户"""
    service = get_admin_service()
    role_enum = AdminRole(role) if role else None
    admins = service.list_admin_users(role=role_enum, active_only=active_only)
    return {"admins": [a.to_dict() for a in admins]}


@app.get("/v1/admin/health", tags=["Admin"])
async def get_system_health():
    """获取系统健康状态"""
    service = get_admin_service()
    return service.get_all_health_status()


@app.get("/v1/admin/overview", tags=["Admin"])
async def get_system_overview():
    """获取系统概览"""
    service = get_admin_service()
    return service.get_system_overview()


@app.post("/v1/admin/alerts", tags=["Admin"])
async def create_alert(request: CreateAlertRequest):
    """创建告警"""
    service = get_admin_service()
    try:
        severity = AlertSeverity(request.severity)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid severity")
    
    alert = service.create_alert(
        severity=severity,
        title=request.title,
        message=request.message,
        source=request.source
    )
    return alert.to_dict()


@app.get("/v1/admin/alerts", tags=["Admin"])
async def get_active_alerts(
    severity: Optional[str] = None
):
    """获取活跃告警"""
    service = get_admin_service()
    severity_enum = AlertSeverity(severity) if severity else None
    alerts = service.get_active_alerts(severity=severity_enum)
    return {"alerts": [a.to_dict() for a in alerts]}


@app.post("/v1/admin/alerts/{alert_id}/acknowledge", tags=["Admin"])
async def acknowledge_alert(
    alert_id: str,
    admin_id: str = Query(..., description="Admin ID")
):
    """确认告警"""
    service = get_admin_service()
    alert = service.acknowledge_alert(alert_id, admin_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.to_dict()


@app.post("/v1/admin/alerts/{alert_id}/resolve", tags=["Admin"])
async def resolve_alert(
    alert_id: str,
    admin_id: str = Query(..., description="Admin ID")
):
    """解决告警"""
    service = get_admin_service()
    alert = service.resolve_alert(alert_id, admin_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert.to_dict()


@app.get("/v1/admin/config", tags=["Admin"])
async def get_all_system_configs(
    category: Optional[str] = None
):
    """获取所有系统配置"""
    service = get_admin_service()
    configs = service.get_all_configs(category=category)
    return {"configs": configs}


@app.post("/v1/admin/config", tags=["Admin"])
async def set_system_config(
    request: AdminSetConfigRequest,
    admin_id: str = Query(..., description="Admin ID")
):
    """设置系统配置"""
    service = get_admin_service()
    config = service.set_config(
        config_key=request.config_key,
        value=request.value,
        admin_id=admin_id,
        description=request.description
    )
    return config.to_dict()


@app.get("/v1/admin/theatres/{theatre_id}/dashboard", tags=["Admin"])
async def get_admin_dashboard(theatre_id: str):
    """获取管理仪表盘"""
    service = get_admin_service()
    metrics = service.get_dashboard_metrics(theatre_id)
    return metrics.to_dict()


@app.post("/v1/admin/maintenance/enable", tags=["Admin"])
async def enable_maintenance_mode(
    request: MaintenanceModeRequest,
    admin_id: str = Query(..., description="Admin ID")
):
    """启用维护模式"""
    service = get_admin_service()
    result = service.enable_maintenance_mode(
        admin_id=admin_id,
        reason=request.reason,
        estimated_duration_minutes=request.estimated_duration_minutes
    )
    return result


@app.post("/v1/admin/maintenance/disable", tags=["Admin"])
async def disable_maintenance_mode(
    admin_id: str = Query(..., description="Admin ID")
):
    """禁用维护模式"""
    service = get_admin_service()
    result = service.disable_maintenance_mode(admin_id)
    return result


@app.get("/v1/admin/statistics", tags=["Admin"])
async def get_admin_statistics():
    """获取管理统计"""
    service = get_admin_service()
    return service.get_admin_statistics()


@app.post("/v1/admin/theatres/{theatre_id}/export", tags=["Admin"])
async def export_theatre_data(
    theatre_id: str,
    include_users: bool = Query(True),
    include_content: bool = Query(True),
    include_analytics: bool = Query(True)
):
    """导出剧场数据"""
    service = get_admin_service()
    data = service.export_theatre_data(
        theatre_id=theatre_id,
        include_users=include_users,
        include_content=include_content,
        include_analytics=include_analytics
    )
    return data
