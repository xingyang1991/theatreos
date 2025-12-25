"""
TheatreOS Experience Loop API Routes
体验闭环相关API：结算、回声归档、追证、复访建议

Endpoints:
- GET /v1/gates/{gate_id}/explain - 获取门结算详情
- GET /v1/users/me/archive - 获取用户档案
- GET /v1/users/me/archive/echoes - 获取回声历史
- GET /v1/users/me/archive/evidences - 获取证物收集
- GET /v1/users/me/archive/stats - 获取统计数据
- GET /v1/evidence-hunts/active - 获取活跃追证任务
- GET /v1/revisit-suggestions - 获取复访建议
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Experience Loop"])


# =============================================================================
# Pydantic Models
# =============================================================================

# --- ExplainCard ---
class GateOption(BaseModel):
    option_id: str
    text: str
    votes: int
    odds: float
    is_winner: bool


class UserParticipation(BaseModel):
    voted_option_id: Optional[str]
    bet_option_id: Optional[str]
    bet_amount: float
    submitted_evidence_ids: List[str]
    is_winner: bool


class Rewards(BaseModel):
    base_tickets: int
    bet_return: float
    evidence_bonus: int
    streak_bonus: int
    total_change: float


class NewEvidence(BaseModel):
    evidence_id: str
    name: str
    type: str
    grade: str
    description: str


class WorldImpact(BaseModel):
    variable: str
    change: float
    description: str


class Echo(BaseModel):
    echo_id: str
    title: str
    summary: str
    narrative: str
    world_impact: List[WorldImpact]
    thread_name: str


class ExplainCardResponse(BaseModel):
    gate_id: str
    gate_title: str
    gate_type: str
    gate_question: str
    settled_at: str
    options: List[GateOption]
    winning_option_id: str
    user_participation: UserParticipation
    rewards: Rewards
    new_evidences: List[NewEvidence]
    echo: Echo
    total_participants: int
    total_bets: float


# --- Archive ---
class EchoRecord(BaseModel):
    echo_id: str
    gate_id: str
    gate_title: str
    gate_type: str
    timestamp: str
    result: str
    summary: str
    thread_id: str
    thread_name: str
    tickets_change: float


class EvidenceItem(BaseModel):
    evidence_id: str
    name: str
    type: str
    grade: str
    collected_at: str
    from_gate: str


class ThreadProgress(BaseModel):
    thread_id: str
    thread_name: str
    progress: int
    total_gates: int
    completed_gates: int
    key_moments: List[str]


class ArchiveStats(BaseModel):
    total_gates_participated: int
    win_count: int
    lose_count: int
    win_rate: float
    total_tickets_earned: float
    total_evidences_collected: int
    rare_evidences_count: int
    favorite_thread: str
    current_streak: int
    best_streak: int


class ArchiveResponse(BaseModel):
    echoes: List[EchoRecord]
    evidences: List[EvidenceItem]
    thread_progress: List[ThreadProgress]
    stats: ArchiveStats


# --- Evidence Hunt ---
class EvidenceHunt(BaseModel):
    hunt_id: str
    title: str
    description: str
    target_evidence_type: str
    target_evidence_name: str
    hint: str
    related_stage_id: str
    related_stage_name: str
    related_thread: str
    progress: int
    total_steps: int
    completed_steps: int
    reward_tickets: int
    reward_evidence_grade: str
    expires_at: str
    difficulty: str
    participants: int


class EvidenceHuntsResponse(BaseModel):
    hunts: List[EvidenceHunt]
    total_active: int


# --- Revisit Suggestion ---
class RevisitSuggestion(BaseModel):
    suggestion_id: str
    stage_id: str
    stage_name: str
    stage_hp_name: str
    reason: str
    reason_type: str
    priority: str
    evidence_hint: Optional[str] = None
    event_time: Optional[str] = None


class RevisitSuggestionsResponse(BaseModel):
    suggestions: List[RevisitSuggestion]


# =============================================================================
# Mock Data Generators
# =============================================================================

def generate_mock_explain_card(gate_id: str, user_id: str) -> ExplainCardResponse:
    """生成模拟的结算卡数据"""
    return ExplainCardResponse(
        gate_id=gate_id,
        gate_title="飞路粉的秘密",
        gate_type="plot",
        gate_question="神秘的飞路粉供应商究竟是谁？",
        settled_at=datetime.now(timezone.utc).isoformat(),
        options=[
            GateOption(option_id="opt_1", text="蒙顿格斯·弗莱奇", votes=156, odds=2.5, is_winner=True),
            GateOption(option_id="opt_2", text="博金先生", votes=89, odds=3.2, is_winner=False),
            GateOption(option_id="opt_3", text="神秘的东方商人", votes=67, odds=4.1, is_winner=False),
        ],
        winning_option_id="opt_1",
        user_participation=UserParticipation(
            voted_option_id="opt_1",
            bet_option_id="opt_1",
            bet_amount=50,
            submitted_evidence_ids=["ev_001"],
            is_winner=True
        ),
        rewards=Rewards(
            base_tickets=10,
            bet_return=125,
            evidence_bonus=20,
            streak_bonus=15,
            total_change=170
        ),
        new_evidences=[
            NewEvidence(
                evidence_id="ev_new_001",
                name="飞路粉配方残页",
                type="document",
                grade="rare",
                description="一张沾满灰尘的羊皮纸，上面记载着飞路粉的部分配方..."
            )
        ],
        echo=Echo(
            echo_id="echo_001",
            title="飞路网络的裂痕",
            summary="蒙顿格斯的身份被揭露，飞路粉黑市即将面临整顿。",
            narrative="当傲罗们冲进翻倒巷的地下仓库时，蒙顿格斯·弗莱奇正试图销毁最后一批证据。这位狡猾的走私贩终于落入法网，但他背后的势力似乎远不止于此。魔法部的调查才刚刚开始...",
            world_impact=[
                WorldImpact(variable="黑市热度", change=-15, description="黑市活动暂时收敛"),
                WorldImpact(variable="飞路稳定性", change=10, description="非法飞路粉流通减少"),
            ],
            thread_name="飞路错拍线"
        ),
        total_participants=312,
        total_bets=15680
    )


def generate_mock_archive(user_id: str) -> ArchiveResponse:
    """生成模拟的档案数据"""
    now = datetime.now(timezone.utc)
    return ArchiveResponse(
        echoes=[
            EchoRecord(
                echo_id="echo_001",
                gate_id="gate_001",
                gate_title="飞路粉的秘密",
                gate_type="plot",
                timestamp=(now - timedelta(hours=1)).isoformat(),
                result="win",
                summary="蒙顿格斯的身份被揭露，飞路粉黑市即将面临整顿。",
                thread_id="thread_floo",
                thread_name="飞路错拍线",
                tickets_change=170
            ),
            EchoRecord(
                echo_id="echo_002",
                gate_id="gate_002",
                gate_title="外滩的神秘信号",
                gate_type="lore",
                timestamp=(now - timedelta(hours=2)).isoformat(),
                result="lose",
                summary="信号来源仍是谜团，但线索指向了浦东方向。",
                thread_id="thread_ministry",
                thread_name="魔法部暗线",
                tickets_change=-50
            ),
            EchoRecord(
                echo_id="echo_003",
                gate_id="gate_003",
                gate_title="豫园的古老契约",
                gate_type="plot",
                timestamp=(now - timedelta(days=1)).isoformat(),
                result="win",
                summary="契约的秘密被部分揭开，但更大的阴谋正在酝酿。",
                thread_id="thread_yuyuan",
                thread_name="豫园秘契线",
                tickets_change=85
            ),
        ],
        evidences=[
            EvidenceItem(
                evidence_id="ev_001",
                name="飞路粉配方残页",
                type="document",
                grade="rare",
                collected_at=(now - timedelta(hours=1)).isoformat(),
                from_gate="飞路粉的秘密"
            ),
            EvidenceItem(
                evidence_id="ev_002",
                name="神秘的魔杖碎片",
                type="artifact",
                grade="epic",
                collected_at=(now - timedelta(days=1)).isoformat(),
                from_gate="豫园的古老契约"
            ),
        ],
        thread_progress=[
            ThreadProgress(
                thread_id="thread_floo",
                thread_name="飞路错拍线",
                progress=65,
                total_gates=8,
                completed_gates=5,
                key_moments=["发现飞路粉异常", "追踪到翻倒巷", "揭露蒙顿格斯"]
            ),
            ThreadProgress(
                thread_id="thread_ministry",
                thread_name="魔法部暗线",
                progress=30,
                total_gates=10,
                completed_gates=3,
                key_moments=["外滩信号", "浦东线索"]
            ),
        ],
        stats=ArchiveStats(
            total_gates_participated=13,
            win_count=8,
            lose_count=4,
            win_rate=61.5,
            total_tickets_earned=1250,
            total_evidences_collected=24,
            rare_evidences_count=6,
            favorite_thread="飞路错拍线",
            current_streak=2,
            best_streak=5
        )
    )


def generate_mock_evidence_hunts() -> EvidenceHuntsResponse:
    """生成模拟的追证任务数据"""
    now = datetime.now(timezone.utc)
    return EvidenceHuntsResponse(
        hunts=[
            EvidenceHunt(
                hunt_id="hunt_001",
                title="追踪飞路粉源头",
                description="蒙顿格斯被捕后，他的供应商仍在逍遥法外。追踪线索，找到真正的幕后黑手。",
                target_evidence_type="document",
                target_evidence_name="飞路粉进货单",
                hint="新天地的某个角落可能藏有线索...",
                related_stage_id="stage_xintiandi",
                related_stage_name="新天地",
                related_thread="飞路错拍线",
                progress=60,
                total_steps=5,
                completed_steps=3,
                reward_tickets=200,
                reward_evidence_grade="epic",
                expires_at=(now + timedelta(days=2)).isoformat(),
                difficulty="medium",
                participants=156
            ),
            EvidenceHunt(
                hunt_id="hunt_002",
                title="解读古老预言",
                description="陆家嘴发现的预言碎片需要更多线索才能完整解读。",
                target_evidence_type="artifact",
                target_evidence_name="预言水晶碎片",
                hint="东方明珠附近的魔法波动异常强烈...",
                related_stage_id="stage_lujiazui",
                related_stage_name="陆家嘴",
                related_thread="预言解读线",
                progress=25,
                total_steps=8,
                completed_steps=2,
                reward_tickets=350,
                reward_evidence_grade="legendary",
                expires_at=(now + timedelta(days=5)).isoformat(),
                difficulty="hard",
                participants=89
            ),
        ],
        total_active=2
    )


def generate_mock_revisit_suggestions(user_id: str) -> RevisitSuggestionsResponse:
    """生成模拟的复访建议数据"""
    return RevisitSuggestionsResponse(
        suggestions=[
            RevisitSuggestion(
                suggestion_id="sug_001",
                stage_id="stage_xintiandi",
                stage_name="新天地",
                stage_hp_name="对角巷",
                reason="有3件未收集的证物等待发现",
                reason_type="evidence",
                priority="high",
                evidence_hint="飞路粉相关线索"
            ),
            RevisitSuggestion(
                suggestion_id="sug_002",
                stage_id="stage_yuyuan",
                stage_name="豫园",
                stage_hp_name="古灵阁",
                reason="豫园秘契线有新的剧情发展",
                reason_type="story",
                priority="medium"
            ),
            RevisitSuggestion(
                suggestion_id="sug_003",
                stage_id="stage_lujiazui",
                stage_name="陆家嘴",
                stage_hp_name="魔法部",
                reason="限时事件：预言厅开放",
                reason_type="event",
                priority="high",
                event_time="今晚 20:00"
            ),
        ]
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/gates/{gate_id}/explain", response_model=ExplainCardResponse)
async def get_gate_explain(
    gate_id: str = Path(..., description="Gate ID"),
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """
    获取门结算详情（ExplainCard）
    
    返回门的结算结果、用户参与情况、收益明细、新获得的证物和回声叙事。
    """
    try:
        # TODO: 从数据库获取真实数据
        return generate_mock_explain_card(gate_id, x_user_id)
    except Exception as e:
        logger.error(f"Failed to get explain card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/me/archive", response_model=ArchiveResponse)
async def get_user_archive(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    thread_id: Optional[str] = Query(default=None),
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """
    获取用户档案
    
    返回用户的回声历史、证物收集、故事线进度和统计数据。
    """
    try:
        # TODO: 从数据库获取真实数据
        return generate_mock_archive(x_user_id)
    except Exception as e:
        logger.error(f"Failed to get archive: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/me/archive/echoes")
async def get_user_echoes(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    thread_id: Optional[str] = Query(default=None),
    result: Optional[str] = Query(default=None, description="Filter by result: win, lose, neutral"),
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """获取用户回声历史"""
    archive = generate_mock_archive(x_user_id)
    return {"echoes": archive.echoes, "total": len(archive.echoes)}


@router.get("/users/me/archive/evidences")
async def get_user_evidences(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    grade: Optional[str] = Query(default=None, description="Filter by grade: common, rare, epic, legendary"),
    type: Optional[str] = Query(default=None, description="Filter by type"),
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """获取用户证物收集"""
    archive = generate_mock_archive(x_user_id)
    return {"evidences": archive.evidences, "total": len(archive.evidences)}


@router.get("/users/me/archive/stats", response_model=ArchiveStats)
async def get_user_stats(
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """获取用户统计数据"""
    archive = generate_mock_archive(x_user_id)
    return archive.stats


@router.get("/evidence-hunts/active", response_model=EvidenceHuntsResponse)
async def get_active_evidence_hunts(
    stage_id: Optional[str] = Query(default=None, description="Filter by stage"),
    thread_id: Optional[str] = Query(default=None, description="Filter by thread"),
    difficulty: Optional[str] = Query(default=None, description="Filter by difficulty: easy, medium, hard"),
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """
    获取活跃的追证任务
    
    返回当前可参与的追证任务列表。
    """
    try:
        # TODO: 从数据库获取真实数据
        return generate_mock_evidence_hunts()
    except Exception as e:
        logger.error(f"Failed to get evidence hunts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revisit-suggestions", response_model=RevisitSuggestionsResponse)
async def get_revisit_suggestions(
    priority: Optional[str] = Query(default=None, description="Filter by priority: high, medium, low"),
    reason_type: Optional[str] = Query(default=None, description="Filter by type: evidence, story, event, crew"),
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """
    获取复访建议
    
    根据用户的进度和当前事件，推荐需要复访的舞台。
    """
    try:
        # TODO: 从数据库获取真实数据
        return generate_mock_revisit_suggestions(x_user_id)
    except Exception as e:
        logger.error(f"Failed to get revisit suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gates/{gate_id}/claim-rewards")
async def claim_gate_rewards(
    gate_id: str = Path(..., description="Gate ID"),
    x_user_id: str = Header(default="demo_user", alias="X-User-ID")
):
    """
    领取门结算奖励
    
    领取用户在指定门中获得的奖励（票券、证物等）。
    """
    try:
        # TODO: 实现真实的奖励领取逻辑
        return {
            "success": True,
            "message": "奖励已领取",
            "rewards": {
                "tickets": 170,
                "evidences": ["ev_new_001"]
            }
        }
    except Exception as e:
        logger.error(f"Failed to claim rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Map API Endpoints
# =============================================================================

class StageLocation(BaseModel):
    stage_id: str
    name: str
    hp_name: str
    address: str
    district: str
    lat: float
    lng: float
    status: str
    current_scene: Optional[str] = None
    current_gate: Optional[str] = None
    heat_level: int
    player_count: int
    distance: Optional[float] = None
    has_event: bool
    event_name: Optional[str] = None
    evidence_count: int


class MapRegion(BaseModel):
    region_id: str
    name: str
    stage_count: int
    center_lat: float
    center_lng: float


class MapDataResponse(BaseModel):
    stages: List[StageLocation]
    regions: List[MapRegion]
    user_location: Optional[Dict[str, float]] = None


@router.get("/map/stages", response_model=MapDataResponse)
async def get_map_stages(
    lat: Optional[float] = Query(default=None, description="User latitude"),
    lng: Optional[float] = Query(default=None, description="User longitude"),
    radius: int = Query(default=5000, description="Search radius in meters"),
    x_theatre_id: str = Header(default="", alias="X-Theatre-ID")
):
    """
    获取地图舞台数据
    
    返回指定范围内的所有舞台位置和状态信息。
    """
    # 模拟数据
    stages = [
        StageLocation(
            stage_id="stage_xintiandi",
            name="新天地",
            hp_name="对角巷",
            address="黄浦区新天地广场",
            district="黄浦区",
            lat=31.2195,
            lng=121.4737,
            status="active",
            current_scene="飞路粉商店的秘密交易",
            current_gate="飞路粉的秘密",
            heat_level=85,
            player_count=47,
            distance=1200,
            has_event=True,
            event_name="黑市大搜查",
            evidence_count=3
        ),
        StageLocation(
            stage_id="stage_bund",
            name="外滩",
            hp_name="魔法部入口",
            address="黄浦区中山东一路",
            district="黄浦区",
            lat=31.2400,
            lng=121.4900,
            status="active",
            current_scene="神秘信号追踪",
            heat_level=72,
            player_count=35,
            distance=2500,
            has_event=False,
            evidence_count=1
        ),
        StageLocation(
            stage_id="stage_yuyuan",
            name="豫园",
            hp_name="古灵阁",
            address="黄浦区豫园老街",
            district="黄浦区",
            lat=31.2275,
            lng=121.4920,
            status="active",
            current_scene="古老契约的解读",
            current_gate="豫园的古老契约",
            heat_level=68,
            player_count=28,
            distance=1800,
            has_event=False,
            evidence_count=2
        ),
        StageLocation(
            stage_id="stage_lujiazui",
            name="陆家嘴",
            hp_name="魔法部",
            address="浦东新区陆家嘴环路",
            district="浦东新区",
            lat=31.2397,
            lng=121.4998,
            status="active",
            current_scene="预言厅的秘密",
            heat_level=90,
            player_count=62,
            distance=3200,
            has_event=True,
            event_name="预言厅开放",
            evidence_count=4
        ),
    ]
    
    regions = [
        MapRegion(region_id="huangpu", name="黄浦区", stage_count=5, center_lat=31.2275, center_lng=121.4800),
        MapRegion(region_id="pudong", name="浦东新区", stage_count=1, center_lat=31.2397, center_lng=121.4998),
    ]
    
    user_location = None
    if lat and lng:
        user_location = {"lat": lat, "lng": lng}
    
    return MapDataResponse(
        stages=stages,
        regions=regions,
        user_location=user_location
    )


@router.get("/map/regions")
async def get_map_regions(
    x_theatre_id: str = Header(default="", alias="X-Theatre-ID")
):
    """获取地图区域列表"""
    return {
        "regions": [
            {"region_id": "huangpu", "name": "黄浦区", "stage_count": 5},
            {"region_id": "pudong", "name": "浦东新区", "stage_count": 1},
            {"region_id": "jingan", "name": "静安区", "stage_count": 1},
            {"region_id": "xuhui", "name": "徐汇区", "stage_count": 1},
        ]
    }
