"""
TheatreOS Analytics System
数据分析系统 - 埋点收集、核心指标计算、用户行为分析

核心功能:
1. 事件埋点收集 (Event Tracking)
2. 核心指标计算 (KPI Metrics)
3. 用户行为分析 (User Behavior)
4. 实时仪表盘数据 (Dashboard Data)
5. 漏斗分析 (Funnel Analysis)
6. 留存分析 (Retention Analysis)
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from decimal import Decimal
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class EventCategory(str, Enum):
    """事件类别"""
    USER = "USER"                 # 用户行为事件
    CONTENT = "CONTENT"           # 内容相关事件
    SOCIAL = "SOCIAL"             # 社交相关事件
    ECONOMY = "ECONOMY"           # 经济相关事件
    SYSTEM = "SYSTEM"             # 系统事件


class EventType(str, Enum):
    """事件类型"""
    # 用户行为
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_REGISTER = "USER_REGISTER"
    SESSION_START = "SESSION_START"
    SESSION_END = "SESSION_END"
    
    # 内容交互
    SCENE_VIEW = "SCENE_VIEW"
    SCENE_COMPLETE = "SCENE_COMPLETE"
    EVIDENCE_COLLECT = "EVIDENCE_COLLECT"
    EVIDENCE_USE = "EVIDENCE_USE"
    RUMOR_CREATE = "RUMOR_CREATE"
    RUMOR_SPREAD = "RUMOR_SPREAD"
    
    # 门交互
    GATE_VIEW = "GATE_VIEW"
    GATE_VOTE = "GATE_VOTE"
    GATE_BET = "GATE_BET"
    GATE_RESULT = "GATE_RESULT"
    
    # 社交行为
    CREW_JOIN = "CREW_JOIN"
    CREW_LEAVE = "CREW_LEAVE"
    CREW_ACTION = "CREW_ACTION"
    TRACE_LEAVE = "TRACE_LEAVE"
    TRACE_DISCOVER = "TRACE_DISCOVER"
    
    # 经济行为
    WALLET_DEPOSIT = "WALLET_DEPOSIT"
    WALLET_WITHDRAW = "WALLET_WITHDRAW"
    TRADE_COMPLETE = "TRADE_COMPLETE"
    
    # 位置相关
    LOCATION_UPDATE = "LOCATION_UPDATE"
    RING_ENTER = "RING_ENTER"
    RING_EXIT = "RING_EXIT"


class MetricType(str, Enum):
    """指标类型"""
    DAU = "DAU"                   # 日活跃用户
    WAU = "WAU"                   # 周活跃用户
    MAU = "MAU"                   # 月活跃用户
    RETENTION_D1 = "RETENTION_D1"   # 次日留存
    RETENTION_D7 = "RETENTION_D7"   # 7日留存
    RETENTION_D30 = "RETENTION_D30" # 30日留存
    AVG_SESSION = "AVG_SESSION"     # 平均会话时长
    ARPU = "ARPU"                 # 每用户平均收入
    CONVERSION = "CONVERSION"     # 转化率


class AggregationPeriod(str, Enum):
    """聚合周期"""
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class AnalyticsEvent:
    """分析事件"""
    event_id: str
    theatre_id: str
    user_id: Optional[str]
    category: EventCategory
    event_type: EventType
    timestamp: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    device_info: Optional[Dict[str, str]] = None
    location_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "theatre_id": self.theatre_id,
            "user_id": self.user_id,
            "category": self.category.value if self.category else None,
            "event_type": self.event_type.value if self.event_type else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "properties": self.properties,
            "session_id": self.session_id,
            "device_info": self.device_info,
            "location_info": self.location_info
        }


@dataclass
class UserSession:
    """用户会话"""
    session_id: str
    user_id: str
    theatre_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    events_count: int = 0
    scenes_viewed: int = 0
    gates_participated: int = 0
    device_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "theatre_id": self.theatre_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "events_count": self.events_count,
            "scenes_viewed": self.scenes_viewed,
            "gates_participated": self.gates_participated,
            "device_type": self.device_type
        }


@dataclass
class MetricSnapshot:
    """指标快照"""
    metric_type: MetricType
    theatre_id: str
    period: AggregationPeriod
    period_start: datetime
    period_end: datetime
    value: float
    breakdown: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_type": self.metric_type.value,
            "theatre_id": self.theatre_id,
            "period": self.period.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "value": self.value,
            "breakdown": self.breakdown
        }


@dataclass
class FunnelStep:
    """漏斗步骤"""
    step_name: str
    event_type: EventType
    users_count: int
    conversion_rate: float  # 相对于上一步的转化率
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "event_type": self.event_type.value,
            "users_count": self.users_count,
            "conversion_rate": self.conversion_rate
        }


@dataclass
class FunnelAnalysis:
    """漏斗分析结果"""
    funnel_id: str
    funnel_name: str
    theatre_id: str
    period_start: datetime
    period_end: datetime
    steps: List[FunnelStep]
    overall_conversion: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "funnel_id": self.funnel_id,
            "funnel_name": self.funnel_name,
            "theatre_id": self.theatre_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "steps": [s.to_dict() for s in self.steps],
            "overall_conversion": self.overall_conversion
        }


@dataclass
class RetentionCohort:
    """留存队列"""
    cohort_date: datetime
    cohort_size: int
    retention_by_day: Dict[int, float]  # day -> retention rate
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cohort_date": self.cohort_date.isoformat(),
            "cohort_size": self.cohort_size,
            "retention_by_day": self.retention_by_day
        }


@dataclass
class DashboardData:
    """仪表盘数据"""
    theatre_id: str
    generated_at: datetime
    
    # 核心指标
    dau: int
    wau: int
    mau: int
    
    # 内容指标
    scenes_delivered_today: int
    gates_resolved_today: int
    evidence_collected_today: int
    rumors_created_today: int
    
    # 社交指标
    active_crews: int
    crew_actions_today: int
    traces_left_today: int
    
    # 经济指标
    total_bets_today: int
    total_trades_today: int
    
    # 趋势数据
    dau_trend: List[Dict[str, Any]] = field(default_factory=list)
    engagement_trend: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "theatre_id": self.theatre_id,
            "generated_at": self.generated_at.isoformat(),
            "core_metrics": {
                "dau": self.dau,
                "wau": self.wau,
                "mau": self.mau
            },
            "content_metrics": {
                "scenes_delivered_today": self.scenes_delivered_today,
                "gates_resolved_today": self.gates_resolved_today,
                "evidence_collected_today": self.evidence_collected_today,
                "rumors_created_today": self.rumors_created_today
            },
            "social_metrics": {
                "active_crews": self.active_crews,
                "crew_actions_today": self.crew_actions_today,
                "traces_left_today": self.traces_left_today
            },
            "economy_metrics": {
                "total_bets_today": self.total_bets_today,
                "total_trades_today": self.total_trades_today
            },
            "trends": {
                "dau_trend": self.dau_trend,
                "engagement_trend": self.engagement_trend
            }
        }


# =============================================================================
# Analytics Service
# =============================================================================
class AnalyticsService:
    """数据分析服务"""
    
    def __init__(self, db=None):
        self.db = db
        # 内存存储（演示用）
        self.events: Dict[str, AnalyticsEvent] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.user_sessions: Dict[str, List[str]] = defaultdict(list)  # user_id -> session_ids
        self.theatre_events: Dict[str, List[str]] = defaultdict(list)  # theatre_id -> event_ids
        self.daily_active_users: Dict[str, set] = defaultdict(set)  # date_str -> user_ids
        self.user_first_seen: Dict[str, datetime] = {}  # user_id -> first_seen_date
        
        logger.info("AnalyticsService initialized")
    
    # =========================================================================
    # Event Tracking
    # =========================================================================
    def track_event(
        self,
        theatre_id: str,
        event_type: EventType,
        user_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        device_info: Optional[Dict[str, str]] = None,
        location_info: Optional[Dict[str, Any]] = None
    ) -> AnalyticsEvent:
        """记录一个分析事件"""
        
        # 确定事件类别
        category = self._get_event_category(event_type)
        
        event = AnalyticsEvent(
            event_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            user_id=user_id,
            category=category,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            properties=properties or {},
            session_id=session_id,
            device_info=device_info,
            location_info=location_info
        )
        
        self.events[event.event_id] = event
        self.theatre_events[theatre_id].append(event.event_id)
        
        # 更新日活数据
        if user_id:
            date_str = event.timestamp.strftime("%Y-%m-%d")
            self.daily_active_users[date_str].add(user_id)
            
            # 记录首次出现
            if user_id not in self.user_first_seen:
                self.user_first_seen[user_id] = event.timestamp
        
        # 更新会话统计
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.events_count += 1
            if event_type == EventType.SCENE_VIEW:
                session.scenes_viewed += 1
            elif event_type in [EventType.GATE_VOTE, EventType.GATE_BET]:
                session.gates_participated += 1
        
        logger.debug(f"Event tracked: {event_type.value} for user {user_id}")
        return event
    
    def batch_track_events(
        self,
        events: List[Dict[str, Any]]
    ) -> List[AnalyticsEvent]:
        """批量记录事件"""
        results = []
        for event_data in events:
            event = self.track_event(
                theatre_id=event_data.get("theatre_id"),
                event_type=EventType(event_data.get("event_type")),
                user_id=event_data.get("user_id"),
                properties=event_data.get("properties"),
                session_id=event_data.get("session_id"),
                device_info=event_data.get("device_info"),
                location_info=event_data.get("location_info")
            )
            results.append(event)
        return results
    
    def _get_event_category(self, event_type: EventType) -> EventCategory:
        """根据事件类型确定类别"""
        user_events = {EventType.USER_LOGIN, EventType.USER_LOGOUT, 
                       EventType.USER_REGISTER, EventType.SESSION_START, 
                       EventType.SESSION_END}
        content_events = {EventType.SCENE_VIEW, EventType.SCENE_COMPLETE,
                         EventType.EVIDENCE_COLLECT, EventType.EVIDENCE_USE,
                         EventType.RUMOR_CREATE, EventType.RUMOR_SPREAD,
                         EventType.GATE_VIEW, EventType.GATE_VOTE,
                         EventType.GATE_BET, EventType.GATE_RESULT}
        social_events = {EventType.CREW_JOIN, EventType.CREW_LEAVE,
                        EventType.CREW_ACTION, EventType.TRACE_LEAVE,
                        EventType.TRACE_DISCOVER}
        economy_events = {EventType.WALLET_DEPOSIT, EventType.WALLET_WITHDRAW,
                         EventType.TRADE_COMPLETE}
        
        if event_type in user_events:
            return EventCategory.USER
        elif event_type in content_events:
            return EventCategory.CONTENT
        elif event_type in social_events:
            return EventCategory.SOCIAL
        elif event_type in economy_events:
            return EventCategory.ECONOMY
        else:
            return EventCategory.SYSTEM
    
    # =========================================================================
    # Session Management
    # =========================================================================
    def start_session(
        self,
        user_id: str,
        theatre_id: str,
        device_type: Optional[str] = None
    ) -> UserSession:
        """开始一个用户会话"""
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            theatre_id=theatre_id,
            start_time=datetime.now(timezone.utc),
            device_type=device_type
        )
        
        self.sessions[session.session_id] = session
        self.user_sessions[user_id].append(session.session_id)
        
        # 记录会话开始事件
        self.track_event(
            theatre_id=theatre_id,
            event_type=EventType.SESSION_START,
            user_id=user_id,
            session_id=session.session_id,
            properties={"device_type": device_type}
        )
        
        logger.info(f"Session started: {session.session_id} for user {user_id}")
        return session
    
    def end_session(self, session_id: str) -> Optional[UserSession]:
        """结束一个用户会话"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        session.end_time = datetime.now(timezone.utc)
        session.duration_seconds = int(
            (session.end_time - session.start_time).total_seconds()
        )
        
        # 记录会话结束事件
        self.track_event(
            theatre_id=session.theatre_id,
            event_type=EventType.SESSION_END,
            user_id=session.user_id,
            session_id=session_id,
            properties={
                "duration_seconds": session.duration_seconds,
                "events_count": session.events_count,
                "scenes_viewed": session.scenes_viewed,
                "gates_participated": session.gates_participated
            }
        )
        
        logger.info(f"Session ended: {session_id}, duration: {session.duration_seconds}s")
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """获取会话信息"""
        return self.sessions.get(session_id)
    
    def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[UserSession]:
        """获取用户的会话历史"""
        session_ids = self.user_sessions.get(user_id, [])
        sessions = [self.sessions[sid] for sid in session_ids if sid in self.sessions]
        sessions.sort(key=lambda s: s.start_time, reverse=True)
        return sessions[:limit]
    
    # =========================================================================
    # Metrics Calculation
    # =========================================================================
    def calculate_dau(
        self,
        theatre_id: str,
        date: Optional[datetime] = None
    ) -> int:
        """计算日活跃用户数"""
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_str = date.strftime("%Y-%m-%d")
        
        # 过滤特定theatre的用户
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        theatre_users = set()
        
        for event_id in theatre_event_ids:
            event = self.events.get(event_id)
            if event and event.user_id:
                event_date = event.timestamp.strftime("%Y-%m-%d")
                if event_date == date_str:
                    theatre_users.add(event.user_id)
        
        return len(theatre_users)
    
    def calculate_wau(
        self,
        theatre_id: str,
        end_date: Optional[datetime] = None
    ) -> int:
        """计算周活跃用户数"""
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        start_date = end_date - timedelta(days=7)
        
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        weekly_users = set()
        
        for event_id in theatre_event_ids:
            event = self.events.get(event_id)
            if event and event.user_id:
                if start_date <= event.timestamp <= end_date:
                    weekly_users.add(event.user_id)
        
        return len(weekly_users)
    
    def calculate_mau(
        self,
        theatre_id: str,
        end_date: Optional[datetime] = None
    ) -> int:
        """计算月活跃用户数"""
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        start_date = end_date - timedelta(days=30)
        
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        monthly_users = set()
        
        for event_id in theatre_event_ids:
            event = self.events.get(event_id)
            if event and event.user_id:
                if start_date <= event.timestamp <= end_date:
                    monthly_users.add(event.user_id)
        
        return len(monthly_users)
    
    def calculate_retention(
        self,
        theatre_id: str,
        cohort_date: datetime,
        days: int = 7
    ) -> RetentionCohort:
        """计算留存率"""
        cohort_date_str = cohort_date.strftime("%Y-%m-%d")
        
        # 找到当天新用户
        new_users = set()
        for user_id, first_seen in self.user_first_seen.items():
            if first_seen.strftime("%Y-%m-%d") == cohort_date_str:
                new_users.add(user_id)
        
        cohort_size = len(new_users)
        if cohort_size == 0:
            return RetentionCohort(
                cohort_date=cohort_date,
                cohort_size=0,
                retention_by_day={}
            )
        
        # 计算每日留存
        retention_by_day = {}
        for day in range(1, days + 1):
            target_date = cohort_date + timedelta(days=day)
            target_date_str = target_date.strftime("%Y-%m-%d")
            
            retained_users = self.daily_active_users.get(target_date_str, set())
            retained_count = len(new_users & retained_users)
            retention_by_day[day] = retained_count / cohort_size if cohort_size > 0 else 0
        
        return RetentionCohort(
            cohort_date=cohort_date,
            cohort_size=cohort_size,
            retention_by_day=retention_by_day
        )
    
    def calculate_avg_session_duration(
        self,
        theatre_id: str,
        date: Optional[datetime] = None
    ) -> float:
        """计算平均会话时长"""
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_str = date.strftime("%Y-%m-%d")
        
        durations = []
        for session in self.sessions.values():
            if session.theatre_id == theatre_id and session.end_time:
                session_date = session.start_time.strftime("%Y-%m-%d")
                if session_date == date_str:
                    durations.append(session.duration_seconds)
        
        return sum(durations) / len(durations) if durations else 0
    
    # =========================================================================
    # Funnel Analysis
    # =========================================================================
    def analyze_funnel(
        self,
        theatre_id: str,
        funnel_name: str,
        steps: List[Tuple[str, EventType]],
        start_date: datetime,
        end_date: datetime
    ) -> FunnelAnalysis:
        """执行漏斗分析"""
        
        # 收集时间范围内的事件
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        user_events: Dict[str, set] = defaultdict(set)
        
        for event_id in theatre_event_ids:
            event = self.events.get(event_id)
            if event and event.user_id:
                if start_date <= event.timestamp <= end_date:
                    user_events[event.user_id].add(event.event_type)
        
        # 计算每步的用户数
        funnel_steps = []
        previous_users = set(user_events.keys())
        
        for step_name, event_type in steps:
            current_users = {
                user_id for user_id, events in user_events.items()
                if event_type in events and user_id in previous_users
            }
            
            conversion_rate = len(current_users) / len(previous_users) if previous_users else 0
            
            funnel_steps.append(FunnelStep(
                step_name=step_name,
                event_type=event_type,
                users_count=len(current_users),
                conversion_rate=conversion_rate
            ))
            
            previous_users = current_users
        
        # 计算整体转化率
        overall_conversion = 0
        if funnel_steps and funnel_steps[0].users_count > 0:
            overall_conversion = funnel_steps[-1].users_count / funnel_steps[0].users_count
        
        return FunnelAnalysis(
            funnel_id=str(uuid.uuid4()),
            funnel_name=funnel_name,
            theatre_id=theatre_id,
            period_start=start_date,
            period_end=end_date,
            steps=funnel_steps,
            overall_conversion=overall_conversion
        )
    
    # =========================================================================
    # Dashboard Data
    # =========================================================================
    def get_dashboard_data(self, theatre_id: str) -> DashboardData:
        """获取仪表盘数据"""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        
        # 计算核心指标
        dau = self.calculate_dau(theatre_id, now)
        wau = self.calculate_wau(theatre_id, now)
        mau = self.calculate_mau(theatre_id, now)
        
        # 统计今日事件
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        today_events = defaultdict(int)
        
        for event_id in theatre_event_ids:
            event = self.events.get(event_id)
            if event and event.timestamp.strftime("%Y-%m-%d") == today_str:
                today_events[event.event_type] += 1
        
        # 生成趋势数据（最近7天）
        dau_trend = []
        for i in range(7, 0, -1):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            day_dau = self.calculate_dau(theatre_id, date)
            dau_trend.append({
                "date": date_str,
                "value": day_dau
            })
        
        return DashboardData(
            theatre_id=theatre_id,
            generated_at=now,
            dau=dau,
            wau=wau,
            mau=mau,
            scenes_delivered_today=today_events.get(EventType.SCENE_VIEW, 0),
            gates_resolved_today=today_events.get(EventType.GATE_RESULT, 0),
            evidence_collected_today=today_events.get(EventType.EVIDENCE_COLLECT, 0),
            rumors_created_today=today_events.get(EventType.RUMOR_CREATE, 0),
            active_crews=today_events.get(EventType.CREW_ACTION, 0),
            crew_actions_today=today_events.get(EventType.CREW_ACTION, 0),
            traces_left_today=today_events.get(EventType.TRACE_LEAVE, 0),
            total_bets_today=today_events.get(EventType.GATE_BET, 0),
            total_trades_today=today_events.get(EventType.TRADE_COMPLETE, 0),
            dau_trend=dau_trend
        )
    
    # =========================================================================
    # Query & Export
    # =========================================================================
    def query_events(
        self,
        theatre_id: str,
        event_types: Optional[List[EventType]] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AnalyticsEvent]:
        """查询事件"""
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        results = []
        
        for event_id in theatre_event_ids:
            event = self.events.get(event_id)
            if not event:
                continue
            
            # 应用过滤条件
            if event_types and event.event_type not in event_types:
                continue
            if user_id and event.user_id != user_id:
                continue
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue
            
            results.append(event)
        
        # 按时间倒序排列
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]
    
    def get_event_counts_by_type(
        self,
        theatre_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """按类型统计事件数量"""
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        counts = defaultdict(int)
        
        for event_id in theatre_event_ids:
            event = self.events.get(event_id)
            if not event:
                continue
            
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue
            
            counts[event.event_type.value] += 1
        
        return dict(counts)
    
    def get_statistics(self, theatre_id: str) -> Dict[str, Any]:
        """获取分析系统统计"""
        theatre_event_ids = self.theatre_events.get(theatre_id, [])
        
        return {
            "theatre_id": theatre_id,
            "total_events": len(theatre_event_ids),
            "total_sessions": len([s for s in self.sessions.values() if s.theatre_id == theatre_id]),
            "unique_users": len(set(
                self.events[eid].user_id 
                for eid in theatre_event_ids 
                if eid in self.events and self.events[eid].user_id
            )),
            "event_types_tracked": len(set(
                self.events[eid].event_type 
                for eid in theatre_event_ids 
                if eid in self.events
            ))
        }
