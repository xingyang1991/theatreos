"""
TheatreOS Safety System
安全系统 - UGC审核、反作弊、举报处理、风控

核心功能:
1. UGC内容审核 (Content Moderation)
2. 反作弊检测 (Anti-Cheat)
3. 举报处理 (Report Handling)
4. 用户处罚 (User Punishment)
5. 风险评估 (Risk Assessment)
6. 审计日志 (Audit Log)
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import re
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class ContentType(str, Enum):
    """内容类型"""
    RUMOR = "RUMOR"               # 谣言
    TRACE_DESC = "TRACE_DESC"     # 痕迹描述
    CREW_NAME = "CREW_NAME"       # 剧团名称
    CREW_DESC = "CREW_DESC"       # 剧团描述
    USER_NICKNAME = "USER_NICKNAME"  # 用户昵称
    CHAT_MESSAGE = "CHAT_MESSAGE"    # 聊天消息


class ModerationStatus(str, Enum):
    """审核状态"""
    PENDING = "PENDING"           # 待审核
    APPROVED = "APPROVED"         # 已通过
    REJECTED = "REJECTED"         # 已拒绝
    AUTO_APPROVED = "AUTO_APPROVED"  # 自动通过
    AUTO_REJECTED = "AUTO_REJECTED"  # 自动拒绝


class ModerationReason(str, Enum):
    """审核原因"""
    CLEAN = "CLEAN"               # 内容干净
    PROFANITY = "PROFANITY"       # 脏话
    HARASSMENT = "HARASSMENT"     # 骚扰
    SPAM = "SPAM"                 # 垃圾信息
    SENSITIVE = "SENSITIVE"       # 敏感内容
    ILLEGAL = "ILLEGAL"           # 违法内容
    SPOILER = "SPOILER"           # 剧透
    OFF_TOPIC = "OFF_TOPIC"       # 跑题


class ReportType(str, Enum):
    """举报类型"""
    INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT"  # 不当内容
    CHEATING = "CHEATING"         # 作弊
    HARASSMENT = "HARASSMENT"     # 骚扰
    SPAM = "SPAM"                 # 垃圾信息
    IMPERSONATION = "IMPERSONATION"  # 冒充
    OTHER = "OTHER"               # 其他


class ReportStatus(str, Enum):
    """举报状态"""
    PENDING = "PENDING"           # 待处理
    INVESTIGATING = "INVESTIGATING"  # 调查中
    RESOLVED = "RESOLVED"         # 已解决
    DISMISSED = "DISMISSED"       # 已驳回


class PunishmentType(str, Enum):
    """处罚类型"""
    WARNING = "WARNING"           # 警告
    MUTE = "MUTE"                 # 禁言
    TEMP_BAN = "TEMP_BAN"         # 临时封禁
    PERM_BAN = "PERM_BAN"         # 永久封禁
    CONTENT_REMOVAL = "CONTENT_REMOVAL"  # 内容删除
    REPUTATION_PENALTY = "REPUTATION_PENALTY"  # 声望惩罚


class CheatType(str, Enum):
    """作弊类型"""
    LOCATION_SPOOFING = "LOCATION_SPOOFING"  # 位置欺骗
    MULTI_ACCOUNT = "MULTI_ACCOUNT"  # 多账号
    BOT_BEHAVIOR = "BOT_BEHAVIOR"    # 机器人行为
    EXPLOIT = "EXPLOIT"              # 漏洞利用
    COLLUSION = "COLLUSION"          # 串通


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class ModerationTask:
    """审核任务"""
    task_id: str
    theatre_id: str
    content_type: ContentType
    content_id: str
    content_text: str
    creator_id: str
    
    status: ModerationStatus = ModerationStatus.PENDING
    reason: Optional[ModerationReason] = None
    confidence: float = 0.0
    
    # 审核信息
    moderator_id: Optional[str] = None
    moderated_at: Optional[datetime] = None
    moderator_notes: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "theatre_id": self.theatre_id,
            "content_type": self.content_type.value,
            "content_id": self.content_id,
            "content_text": self.content_text,
            "creator_id": self.creator_id,
            "status": self.status.value,
            "reason": self.reason.value if self.reason else None,
            "confidence": self.confidence,
            "moderator_id": self.moderator_id,
            "moderated_at": self.moderated_at.isoformat() if self.moderated_at else None,
            "moderator_notes": self.moderator_notes,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Report:
    """举报"""
    report_id: str
    theatre_id: str
    reporter_id: str
    report_type: ReportType
    
    # 被举报对象
    target_user_id: Optional[str] = None
    target_content_id: Optional[str] = None
    target_content_type: Optional[ContentType] = None
    
    description: str = ""
    evidence_urls: List[str] = field(default_factory=list)
    
    status: ReportStatus = ReportStatus.PENDING
    
    # 处理信息
    handler_id: Optional[str] = None
    handled_at: Optional[datetime] = None
    resolution: Optional[str] = None
    punishment_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "theatre_id": self.theatre_id,
            "reporter_id": self.reporter_id,
            "report_type": self.report_type.value,
            "target_user_id": self.target_user_id,
            "target_content_id": self.target_content_id,
            "target_content_type": self.target_content_type.value if self.target_content_type else None,
            "description": self.description,
            "evidence_urls": self.evidence_urls,
            "status": self.status.value,
            "handler_id": self.handler_id,
            "handled_at": self.handled_at.isoformat() if self.handled_at else None,
            "resolution": self.resolution,
            "punishment_id": self.punishment_id,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Punishment:
    """处罚"""
    punishment_id: str
    theatre_id: str
    user_id: str
    punishment_type: PunishmentType
    reason: str
    
    # 时间
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_hours: Optional[int] = None
    
    # 关联
    report_id: Optional[str] = None
    issued_by: Optional[str] = None
    
    # 状态
    is_active: bool = True
    appealed: bool = False
    appeal_result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "punishment_id": self.punishment_id,
            "theatre_id": self.theatre_id,
            "user_id": self.user_id,
            "punishment_type": self.punishment_type.value,
            "reason": self.reason,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": self.duration_hours,
            "report_id": self.report_id,
            "issued_by": self.issued_by,
            "is_active": self.is_active,
            "appealed": self.appealed,
            "appeal_result": self.appeal_result
        }


@dataclass
class CheatDetection:
    """作弊检测"""
    detection_id: str
    theatre_id: str
    user_id: str
    cheat_type: CheatType
    confidence: float
    
    evidence: Dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    
    # 处理
    reviewed: bool = False
    reviewer_id: Optional[str] = None
    is_confirmed: Optional[bool] = None
    punishment_id: Optional[str] = None
    
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "theatre_id": self.theatre_id,
            "user_id": self.user_id,
            "cheat_type": self.cheat_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "risk_level": self.risk_level.value,
            "reviewed": self.reviewed,
            "reviewer_id": self.reviewer_id,
            "is_confirmed": self.is_confirmed,
            "punishment_id": self.punishment_id,
            "detected_at": self.detected_at.isoformat()
        }


@dataclass
class UserRiskProfile:
    """用户风险档案"""
    user_id: str
    theatre_id: str
    
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    
    # 历史统计
    total_reports_received: int = 0
    total_reports_confirmed: int = 0
    total_punishments: int = 0
    total_content_rejected: int = 0
    cheat_detections: int = 0
    
    # 标记
    is_flagged: bool = False
    is_trusted: bool = False
    
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "theatre_id": self.theatre_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "total_reports_received": self.total_reports_received,
            "total_reports_confirmed": self.total_reports_confirmed,
            "total_punishments": self.total_punishments,
            "total_content_rejected": self.total_content_rejected,
            "cheat_detections": self.cheat_detections,
            "is_flagged": self.is_flagged,
            "is_trusted": self.is_trusted,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str
    theatre_id: str
    action: str
    actor_id: str
    target_type: str
    target_id: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "theatre_id": self.theatre_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# Safety Service
# =============================================================================
class SafetyService:
    """安全服务"""
    
    # 敏感词列表（简化版）
    PROFANITY_PATTERNS = [
        r'\b(fuck|shit|damn|ass)\b',
        r'傻[逼比]',
        r'操你',
        r'去死',
    ]
    
    SPAM_PATTERNS = [
        r'(.)\1{5,}',  # 重复字符
        r'(https?://\S+){3,}',  # 多个链接
        r'加微信|加QQ|私聊',
    ]
    
    def __init__(self, db=None):
        self.db = db
        # 内存存储（演示用）
        self.moderation_tasks: Dict[str, ModerationTask] = {}
        self.reports: Dict[str, Report] = {}
        self.punishments: Dict[str, Punishment] = {}
        self.cheat_detections: Dict[str, CheatDetection] = {}
        self.user_risk_profiles: Dict[str, UserRiskProfile] = {}
        self.audit_logs: List[AuditLog] = []
        
        # 用户行为追踪
        self.user_action_history: Dict[str, List[Dict]] = defaultdict(list)
        self.user_location_history: Dict[str, List[Dict]] = defaultdict(list)
        
        logger.info("SafetyService initialized")
    
    # =========================================================================
    # Content Moderation
    # =========================================================================
    def submit_for_moderation(
        self,
        theatre_id: str,
        content_type: ContentType,
        content_id: str,
        content_text: str,
        creator_id: str
    ) -> ModerationTask:
        """提交内容审核"""
        
        # 自动审核
        auto_result = self._auto_moderate(content_text)
        
        task = ModerationTask(
            task_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            content_type=content_type,
            content_id=content_id,
            content_text=content_text,
            creator_id=creator_id,
            status=auto_result["status"],
            reason=auto_result["reason"],
            confidence=auto_result["confidence"]
        )
        
        self.moderation_tasks[task.task_id] = task
        
        # 更新用户风险档案
        if task.status in [ModerationStatus.AUTO_REJECTED, ModerationStatus.REJECTED]:
            self._update_user_risk(theatre_id, creator_id, "content_rejected")
        
        logger.info(f"Content submitted for moderation: {task.task_id}, status: {task.status.value}")
        return task
    
    def _auto_moderate(self, content: str) -> Dict[str, Any]:
        """自动审核内容"""
        content_lower = content.lower()
        
        # 检查脏话
        for pattern in self.PROFANITY_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return {
                    "status": ModerationStatus.AUTO_REJECTED,
                    "reason": ModerationReason.PROFANITY,
                    "confidence": 0.9
                }
        
        # 检查垃圾信息
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, content):
                return {
                    "status": ModerationStatus.AUTO_REJECTED,
                    "reason": ModerationReason.SPAM,
                    "confidence": 0.85
                }
        
        # 检查内容长度
        if len(content) < 2:
            return {
                "status": ModerationStatus.AUTO_REJECTED,
                "reason": ModerationReason.SPAM,
                "confidence": 0.95
                }
        
        # 通过自动审核
        return {
            "status": ModerationStatus.AUTO_APPROVED,
            "reason": ModerationReason.CLEAN,
            "confidence": 0.8
        }
    
    def manual_moderate(
        self,
        task_id: str,
        moderator_id: str,
        approve: bool,
        reason: Optional[ModerationReason] = None,
        notes: Optional[str] = None
    ) -> Optional[ModerationTask]:
        """人工审核"""
        task = self.moderation_tasks.get(task_id)
        if not task:
            return None
        
        task.status = ModerationStatus.APPROVED if approve else ModerationStatus.REJECTED
        task.reason = reason or (ModerationReason.CLEAN if approve else ModerationReason.SENSITIVE)
        task.moderator_id = moderator_id
        task.moderated_at = datetime.now(timezone.utc)
        task.moderator_notes = notes
        task.confidence = 1.0
        
        # 记录审计日志
        self._log_audit(
            theatre_id=task.theatre_id,
            action="MANUAL_MODERATE",
            actor_id=moderator_id,
            target_type="CONTENT",
            target_id=task.content_id,
            details={"approve": approve, "reason": reason.value if reason else None}
        )
        
        return task
    
    def get_pending_moderation_tasks(
        self,
        theatre_id: str,
        content_type: Optional[ContentType] = None,
        limit: int = 50
    ) -> List[ModerationTask]:
        """获取待审核任务"""
        results = []
        for task in self.moderation_tasks.values():
            if task.theatre_id != theatre_id:
                continue
            if task.status != ModerationStatus.PENDING:
                continue
            if content_type and task.content_type != content_type:
                continue
            results.append(task)
        
        results.sort(key=lambda t: t.created_at)
        return results[:limit]
    
    # =========================================================================
    # Report Handling
    # =========================================================================
    def submit_report(
        self,
        theatre_id: str,
        reporter_id: str,
        report_type: ReportType,
        target_user_id: Optional[str] = None,
        target_content_id: Optional[str] = None,
        target_content_type: Optional[ContentType] = None,
        description: str = "",
        evidence_urls: Optional[List[str]] = None
    ) -> Report:
        """提交举报"""
        
        report = Report(
            report_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            reporter_id=reporter_id,
            report_type=report_type,
            target_user_id=target_user_id,
            target_content_id=target_content_id,
            target_content_type=target_content_type,
            description=description,
            evidence_urls=evidence_urls or []
        )
        
        self.reports[report.report_id] = report
        
        # 更新被举报用户的风险档案
        if target_user_id:
            self._update_user_risk(theatre_id, target_user_id, "report_received")
        
        logger.info(f"Report submitted: {report.report_id} by {reporter_id}")
        return report
    
    def handle_report(
        self,
        report_id: str,
        handler_id: str,
        resolution: str,
        dismiss: bool = False,
        punishment_type: Optional[PunishmentType] = None,
        punishment_duration: Optional[int] = None
    ) -> Tuple[Optional[Report], Optional[Punishment]]:
        """处理举报"""
        report = self.reports.get(report_id)
        if not report:
            return None, None
        
        report.handler_id = handler_id
        report.handled_at = datetime.now(timezone.utc)
        report.resolution = resolution
        
        punishment = None
        
        if dismiss:
            report.status = ReportStatus.DISMISSED
        else:
            report.status = ReportStatus.RESOLVED
            
            # 如果需要处罚
            if punishment_type and report.target_user_id:
                punishment = self.issue_punishment(
                    theatre_id=report.theatre_id,
                    user_id=report.target_user_id,
                    punishment_type=punishment_type,
                    reason=resolution,
                    duration_hours=punishment_duration,
                    report_id=report_id,
                    issued_by=handler_id
                )
                report.punishment_id = punishment.punishment_id
                
                # 更新风险档案
                self._update_user_risk(
                    report.theatre_id, 
                    report.target_user_id, 
                    "report_confirmed"
                )
        
        # 记录审计日志
        self._log_audit(
            theatre_id=report.theatre_id,
            action="HANDLE_REPORT",
            actor_id=handler_id,
            target_type="REPORT",
            target_id=report_id,
            details={"dismiss": dismiss, "resolution": resolution}
        )
        
        return report, punishment
    
    def get_pending_reports(
        self,
        theatre_id: str,
        report_type: Optional[ReportType] = None,
        limit: int = 50
    ) -> List[Report]:
        """获取待处理举报"""
        results = []
        for report in self.reports.values():
            if report.theatre_id != theatre_id:
                continue
            if report.status not in [ReportStatus.PENDING, ReportStatus.INVESTIGATING]:
                continue
            if report_type and report.report_type != report_type:
                continue
            results.append(report)
        
        results.sort(key=lambda r: r.created_at)
        return results[:limit]
    
    # =========================================================================
    # Punishment
    # =========================================================================
    def issue_punishment(
        self,
        theatre_id: str,
        user_id: str,
        punishment_type: PunishmentType,
        reason: str,
        duration_hours: Optional[int] = None,
        report_id: Optional[str] = None,
        issued_by: Optional[str] = None
    ) -> Punishment:
        """发放处罚"""
        
        end_time = None
        if duration_hours and punishment_type in [PunishmentType.MUTE, PunishmentType.TEMP_BAN]:
            end_time = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        punishment = Punishment(
            punishment_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            user_id=user_id,
            punishment_type=punishment_type,
            reason=reason,
            end_time=end_time,
            duration_hours=duration_hours,
            report_id=report_id,
            issued_by=issued_by
        )
        
        self.punishments[punishment.punishment_id] = punishment
        
        # 更新风险档案
        self._update_user_risk(theatre_id, user_id, "punishment_received")
        
        # 记录审计日志
        self._log_audit(
            theatre_id=theatre_id,
            action="ISSUE_PUNISHMENT",
            actor_id=issued_by or "SYSTEM",
            target_type="USER",
            target_id=user_id,
            details={
                "punishment_type": punishment_type.value,
                "duration_hours": duration_hours
            }
        )
        
        logger.info(f"Punishment issued: {punishment_type.value} to {user_id}")
        return punishment
    
    def revoke_punishment(
        self,
        punishment_id: str,
        revoked_by: str,
        reason: str
    ) -> Optional[Punishment]:
        """撤销处罚"""
        punishment = self.punishments.get(punishment_id)
        if not punishment:
            return None
        
        punishment.is_active = False
        punishment.appeal_result = f"Revoked: {reason}"
        
        self._log_audit(
            theatre_id=punishment.theatre_id,
            action="REVOKE_PUNISHMENT",
            actor_id=revoked_by,
            target_type="PUNISHMENT",
            target_id=punishment_id,
            details={"reason": reason}
        )
        
        return punishment
    
    def get_user_punishments(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Punishment]:
        """获取用户处罚记录"""
        results = []
        now = datetime.now(timezone.utc)
        
        for punishment in self.punishments.values():
            if punishment.user_id != user_id:
                continue
            
            # 检查是否过期
            if punishment.end_time and punishment.end_time < now:
                punishment.is_active = False
            
            if active_only and not punishment.is_active:
                continue
            
            results.append(punishment)
        
        return results
    
    def check_user_banned(self, user_id: str) -> Tuple[bool, Optional[Punishment]]:
        """检查用户是否被封禁"""
        active_punishments = self.get_user_punishments(user_id, active_only=True)
        
        for punishment in active_punishments:
            if punishment.punishment_type in [PunishmentType.TEMP_BAN, PunishmentType.PERM_BAN]:
                return True, punishment
        
        return False, None
    
    # =========================================================================
    # Anti-Cheat
    # =========================================================================
    def detect_location_spoofing(
        self,
        theatre_id: str,
        user_id: str,
        current_location: Dict[str, float],
        timestamp: datetime
    ) -> Optional[CheatDetection]:
        """检测位置欺骗"""
        
        # 获取历史位置
        history = self.user_location_history[user_id]
        
        if history:
            last_location = history[-1]
            last_time = datetime.fromisoformat(last_location["timestamp"])
            time_diff = (timestamp - last_time).total_seconds()
            
            if time_diff > 0:
                # 计算速度（简化版，假设平面距离）
                lat_diff = abs(current_location["lat"] - last_location["lat"])
                lng_diff = abs(current_location["lng"] - last_location["lng"])
                distance_deg = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                distance_km = distance_deg * 111  # 粗略转换
                speed_kmh = (distance_km / time_diff) * 3600
                
                # 如果速度超过500km/h，可能是位置欺骗
                if speed_kmh > 500:
                    detection = CheatDetection(
                        detection_id=str(uuid.uuid4()),
                        theatre_id=theatre_id,
                        user_id=user_id,
                        cheat_type=CheatType.LOCATION_SPOOFING,
                        confidence=min(0.95, speed_kmh / 1000),
                        evidence={
                            "speed_kmh": speed_kmh,
                            "time_diff_seconds": time_diff,
                            "from": last_location,
                            "to": current_location
                        },
                        risk_level=RiskLevel.HIGH if speed_kmh > 1000 else RiskLevel.MEDIUM
                    )
                    
                    self.cheat_detections[detection.detection_id] = detection
                    self._update_user_risk(theatre_id, user_id, "cheat_detected")
                    
                    logger.warning(f"Location spoofing detected for {user_id}: {speed_kmh} km/h")
                    return detection
        
        # 记录位置
        history.append({
            "lat": current_location["lat"],
            "lng": current_location["lng"],
            "timestamp": timestamp.isoformat()
        })
        
        # 只保留最近100条
        if len(history) > 100:
            self.user_location_history[user_id] = history[-100:]
        
        return None
    
    def detect_bot_behavior(
        self,
        theatre_id: str,
        user_id: str,
        action: str,
        timestamp: datetime
    ) -> Optional[CheatDetection]:
        """检测机器人行为"""
        
        history = self.user_action_history[user_id]
        history.append({
            "action": action,
            "timestamp": timestamp.isoformat()
        })
        
        # 只保留最近1000条
        if len(history) > 1000:
            self.user_action_history[user_id] = history[-1000:]
        
        # 检测规律性行为
        if len(history) >= 10:
            recent = history[-10:]
            intervals = []
            for i in range(1, len(recent)):
                t1 = datetime.fromisoformat(recent[i-1]["timestamp"])
                t2 = datetime.fromisoformat(recent[i]["timestamp"])
                intervals.append((t2 - t1).total_seconds())
            
            # 如果间隔非常规律（标准差很小），可能是机器人
            if intervals:
                avg = sum(intervals) / len(intervals)
                variance = sum((x - avg) ** 2 for x in intervals) / len(intervals)
                std_dev = variance ** 0.5
                
                if std_dev < 0.5 and avg < 2:  # 间隔非常规律且很短
                    detection = CheatDetection(
                        detection_id=str(uuid.uuid4()),
                        theatre_id=theatre_id,
                        user_id=user_id,
                        cheat_type=CheatType.BOT_BEHAVIOR,
                        confidence=0.8,
                        evidence={
                            "avg_interval": avg,
                            "std_dev": std_dev,
                            "sample_size": len(intervals)
                        },
                        risk_level=RiskLevel.MEDIUM
                    )
                    
                    self.cheat_detections[detection.detection_id] = detection
                    logger.warning(f"Bot behavior detected for {user_id}")
                    return detection
        
        return None
    
    def review_cheat_detection(
        self,
        detection_id: str,
        reviewer_id: str,
        is_confirmed: bool,
        punishment_type: Optional[PunishmentType] = None
    ) -> Tuple[Optional[CheatDetection], Optional[Punishment]]:
        """审核作弊检测"""
        detection = self.cheat_detections.get(detection_id)
        if not detection:
            return None, None
        
        detection.reviewed = True
        detection.reviewer_id = reviewer_id
        detection.is_confirmed = is_confirmed
        
        punishment = None
        if is_confirmed and punishment_type:
            punishment = self.issue_punishment(
                theatre_id=detection.theatre_id,
                user_id=detection.user_id,
                punishment_type=punishment_type,
                reason=f"Confirmed {detection.cheat_type.value}",
                issued_by=reviewer_id
            )
            detection.punishment_id = punishment.punishment_id
        
        return detection, punishment
    
    # =========================================================================
    # Risk Assessment
    # =========================================================================
    def get_user_risk_profile(
        self,
        theatre_id: str,
        user_id: str
    ) -> UserRiskProfile:
        """获取用户风险档案"""
        key = f"{theatre_id}:{user_id}"
        
        if key not in self.user_risk_profiles:
            self.user_risk_profiles[key] = UserRiskProfile(
                user_id=user_id,
                theatre_id=theatre_id
            )
        
        return self.user_risk_profiles[key]
    
    def _update_user_risk(
        self,
        theatre_id: str,
        user_id: str,
        event: str
    ):
        """更新用户风险"""
        profile = self.get_user_risk_profile(theatre_id, user_id)
        
        if event == "report_received":
            profile.total_reports_received += 1
            profile.risk_score += 5
        elif event == "report_confirmed":
            profile.total_reports_confirmed += 1
            profile.risk_score += 15
        elif event == "punishment_received":
            profile.total_punishments += 1
            profile.risk_score += 20
        elif event == "content_rejected":
            profile.total_content_rejected += 1
            profile.risk_score += 3
        elif event == "cheat_detected":
            profile.cheat_detections += 1
            profile.risk_score += 25
        
        # 更新风险等级
        if profile.risk_score >= 100:
            profile.risk_level = RiskLevel.CRITICAL
            profile.is_flagged = True
        elif profile.risk_score >= 50:
            profile.risk_level = RiskLevel.HIGH
            profile.is_flagged = True
        elif profile.risk_score >= 20:
            profile.risk_level = RiskLevel.MEDIUM
        else:
            profile.risk_level = RiskLevel.LOW
        
        profile.last_updated = datetime.now(timezone.utc)
    
    def get_high_risk_users(
        self,
        theatre_id: str,
        min_risk_level: RiskLevel = RiskLevel.MEDIUM
    ) -> List[UserRiskProfile]:
        """获取高风险用户"""
        risk_order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3
        }
        
        min_order = risk_order[min_risk_level]
        
        results = []
        for profile in self.user_risk_profiles.values():
            if profile.theatre_id != theatre_id:
                continue
            if risk_order[profile.risk_level] >= min_order:
                results.append(profile)
        
        results.sort(key=lambda p: p.risk_score, reverse=True)
        return results
    
    # =========================================================================
    # Audit Log
    # =========================================================================
    def _log_audit(
        self,
        theatre_id: str,
        action: str,
        actor_id: str,
        target_type: str,
        target_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """记录审计日志"""
        log = AuditLog(
            log_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            action=action,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            ip_address=ip_address
        )
        
        self.audit_logs.append(log)
    
    def get_audit_logs(
        self,
        theatre_id: str,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """获取审计日志"""
        results = []
        
        for log in self.audit_logs:
            if log.theatre_id != theatre_id:
                continue
            if action and log.action != action:
                continue
            if actor_id and log.actor_id != actor_id:
                continue
            if start_time and log.timestamp < start_time:
                continue
            if end_time and log.timestamp > end_time:
                continue
            results.append(log)
        
        results.sort(key=lambda l: l.timestamp, reverse=True)
        return results[:limit]
    
    # =========================================================================
    # Statistics
    # =========================================================================
    def get_statistics(self, theatre_id: str) -> Dict[str, Any]:
        """获取安全统计"""
        pending_moderation = len([
            t for t in self.moderation_tasks.values()
            if t.theatre_id == theatre_id and t.status == ModerationStatus.PENDING
        ])
        
        pending_reports = len([
            r for r in self.reports.values()
            if r.theatre_id == theatre_id and r.status in [ReportStatus.PENDING, ReportStatus.INVESTIGATING]
        ])
        
        active_bans = len([
            p for p in self.punishments.values()
            if p.theatre_id == theatre_id and p.is_active and 
            p.punishment_type in [PunishmentType.TEMP_BAN, PunishmentType.PERM_BAN]
        ])
        
        unreviewed_cheats = len([
            d for d in self.cheat_detections.values()
            if d.theatre_id == theatre_id and not d.reviewed
        ])
        
        high_risk_users = len(self.get_high_risk_users(theatre_id, RiskLevel.HIGH))
        
        return {
            "theatre_id": theatre_id,
            "pending_moderation_tasks": pending_moderation,
            "pending_reports": pending_reports,
            "active_bans": active_bans,
            "unreviewed_cheat_detections": unreviewed_cheats,
            "high_risk_users": high_risk_users,
            "total_audit_logs": len([l for l in self.audit_logs if l.theatre_id == theatre_id])
        }
