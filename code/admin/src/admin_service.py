"""
TheatreOS Admin Dashboard Service
管理后台服务 - 系统监控、配置管理、运营工具

核心功能:
1. 系统监控 (System Monitoring)
2. 配置管理 (Configuration Management)
3. 用户管理 (User Management)
4. 内容管理 (Content Management)
5. 数据导出 (Data Export)
6. 系统健康检查 (Health Check)
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import os

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class AdminRole(str, Enum):
    """管理员角色"""
    SUPER_ADMIN = "SUPER_ADMIN"       # 超级管理员
    ADMIN = "ADMIN"                   # 管理员
    MODERATOR = "MODERATOR"           # 审核员
    OPERATOR = "OPERATOR"             # 运营
    VIEWER = "VIEWER"                 # 只读


class SystemStatus(str, Enum):
    """系统状态"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    MAINTENANCE = "MAINTENANCE"


class AlertSeverity(str, Enum):
    """告警级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class AdminUser:
    """管理员用户"""
    admin_id: str
    username: str
    email: str
    role: AdminRole
    
    # 权限
    allowed_theatres: List[str] = field(default_factory=list)  # 空表示全部
    permissions: List[str] = field(default_factory=list)
    
    # 状态
    is_active: bool = True
    last_login: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "admin_id": self.admin_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "allowed_theatres": self.allowed_theatres,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SystemHealth:
    """系统健康状态"""
    service_name: str
    status: SystemStatus
    latency_ms: float
    last_check: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "last_check": self.last_check.isoformat(),
            "details": self.details,
            "error_message": self.error_message
        }


@dataclass
class Alert:
    """系统告警"""
    alert_id: str
    theatre_id: Optional[str]
    severity: AlertSeverity
    title: str
    message: str
    source: str
    
    # 状态
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "theatre_id": self.theatre_id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "is_resolved": self.is_resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SystemConfig:
    """系统配置"""
    config_key: str
    value: Any
    description: str
    category: str
    is_sensitive: bool = False
    version: int = 1
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None
    
    def to_dict(self, hide_sensitive: bool = True) -> Dict[str, Any]:
        return {
            "config_key": self.config_key,
            "value": "***" if (self.is_sensitive and hide_sensitive) else self.value,
            "description": self.description,
            "category": self.category,
            "is_sensitive": self.is_sensitive,
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
            "updated_by": self.updated_by
        }


@dataclass
class DashboardMetrics:
    """仪表盘指标"""
    theatre_id: str
    timestamp: datetime
    
    # 用户指标
    total_users: int = 0
    active_users_24h: int = 0
    new_users_24h: int = 0
    
    # 内容指标
    total_scenes: int = 0
    scenes_today: int = 0
    total_gates: int = 0
    gates_active: int = 0
    
    # 互动指标
    total_votes: int = 0
    votes_today: int = 0
    total_evidence: int = 0
    total_rumors: int = 0
    
    # 系统指标
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "theatre_id": self.theatre_id,
            "timestamp": self.timestamp.isoformat(),
            "users": {
                "total": self.total_users,
                "active_24h": self.active_users_24h,
                "new_24h": self.new_users_24h
            },
            "content": {
                "total_scenes": self.total_scenes,
                "scenes_today": self.scenes_today,
                "total_gates": self.total_gates,
                "gates_active": self.gates_active
            },
            "engagement": {
                "total_votes": self.total_votes,
                "votes_today": self.votes_today,
                "total_evidence": self.total_evidence,
                "total_rumors": self.total_rumors
            },
            "system": {
                "avg_response_time_ms": self.avg_response_time_ms,
                "error_rate": self.error_rate
            }
        }


# =============================================================================
# Admin Service
# =============================================================================
class AdminService:
    """管理后台服务"""
    
    # 默认权限映射
    ROLE_PERMISSIONS = {
        AdminRole.SUPER_ADMIN: ["*"],
        AdminRole.ADMIN: [
            "view_dashboard", "manage_users", "manage_content", 
            "manage_config", "view_analytics", "manage_campaigns"
        ],
        AdminRole.MODERATOR: [
            "view_dashboard", "moderate_content", "handle_reports",
            "view_users"
        ],
        AdminRole.OPERATOR: [
            "view_dashboard", "manage_campaigns", "send_notifications",
            "view_analytics"
        ],
        AdminRole.VIEWER: ["view_dashboard", "view_analytics"]
    }
    
    def __init__(self, services: Optional[Dict[str, Any]] = None):
        self.services = services or {}
        
        # 内存存储
        self.admin_users: Dict[str, AdminUser] = {}
        self.alerts: Dict[str, Alert] = {}
        self.system_configs: Dict[str, SystemConfig] = {}
        self.health_checks: Dict[str, SystemHealth] = {}
        
        # 初始化默认配置
        self._init_default_configs()
        
        # 创建默认超级管理员
        self._create_default_admin()
        
        logger.info("AdminService initialized")
    
    def _init_default_configs(self):
        """初始化默认配置"""
        defaults = [
            ("system.maintenance_mode", False, "系统维护模式", "system", False),
            ("system.max_concurrent_users", 10000, "最大并发用户数", "system", False),
            ("content.auto_moderation", True, "自动内容审核", "content", False),
            ("content.ai_generation_enabled", True, "AI内容生成开关", "content", False),
            ("game.tick_interval_seconds", 3600, "Tick间隔（秒）", "game", False),
            ("game.gate_vote_duration_hours", 24, "投票持续时间（小时）", "game", False),
            ("notification.push_enabled", True, "推送通知开关", "notification", False),
            ("safety.auto_ban_threshold", 100, "自动封禁风险阈值", "safety", False),
        ]
        
        for key, value, desc, category, sensitive in defaults:
            self.system_configs[key] = SystemConfig(
                config_key=key,
                value=value,
                description=desc,
                category=category,
                is_sensitive=sensitive
            )
    
    def _create_default_admin(self):
        """创建默认管理员"""
        admin = AdminUser(
            admin_id="admin_001",
            username="admin",
            email="admin@theatreos.local",
            role=AdminRole.SUPER_ADMIN,
            permissions=["*"]
        )
        self.admin_users[admin.admin_id] = admin
    
    # =========================================================================
    # Admin User Management
    # =========================================================================
    def create_admin_user(
        self,
        username: str,
        email: str,
        role: AdminRole,
        allowed_theatres: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> AdminUser:
        """创建管理员用户"""
        admin = AdminUser(
            admin_id=str(uuid.uuid4()),
            username=username,
            email=email,
            role=role,
            allowed_theatres=allowed_theatres or [],
            permissions=self.ROLE_PERMISSIONS.get(role, [])
        )
        
        self.admin_users[admin.admin_id] = admin
        logger.info(f"Admin user created: {username} ({role.value})")
        return admin
    
    def get_admin_user(self, admin_id: str) -> Optional[AdminUser]:
        """获取管理员用户"""
        return self.admin_users.get(admin_id)
    
    def list_admin_users(
        self,
        role: Optional[AdminRole] = None,
        active_only: bool = True
    ) -> List[AdminUser]:
        """列出管理员用户"""
        results = []
        for admin in self.admin_users.values():
            if active_only and not admin.is_active:
                continue
            if role and admin.role != role:
                continue
            results.append(admin)
        return results
    
    def check_permission(
        self,
        admin_id: str,
        permission: str,
        theatre_id: Optional[str] = None
    ) -> bool:
        """检查权限"""
        admin = self.admin_users.get(admin_id)
        if not admin or not admin.is_active:
            return False
        
        # 超级管理员拥有所有权限
        if "*" in admin.permissions:
            return True
        
        # 检查剧场权限
        if theatre_id and admin.allowed_theatres:
            if theatre_id not in admin.allowed_theatres:
                return False
        
        return permission in admin.permissions
    
    def record_login(self, admin_id: str):
        """记录登录"""
        admin = self.admin_users.get(admin_id)
        if admin:
            admin.last_login = datetime.now(timezone.utc)
    
    # =========================================================================
    # System Health
    # =========================================================================
    def check_service_health(
        self,
        service_name: str,
        check_func: Optional[Callable] = None
    ) -> SystemHealth:
        """检查服务健康状态"""
        start_time = datetime.now(timezone.utc)
        
        try:
            if check_func:
                result = check_func()
                status = SystemStatus.HEALTHY if result.get("healthy", True) else SystemStatus.UNHEALTHY
                details = result
                error = result.get("error")
            else:
                # 默认检查
                status = SystemStatus.HEALTHY
                details = {"message": "Service is running"}
                error = None
            
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
        except Exception as e:
            status = SystemStatus.UNHEALTHY
            details = {}
            error = str(e)
            latency = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        health = SystemHealth(
            service_name=service_name,
            status=status,
            latency_ms=latency,
            last_check=datetime.now(timezone.utc),
            details=details,
            error_message=error
        )
        
        self.health_checks[service_name] = health
        return health
    
    def get_all_health_status(self) -> Dict[str, Any]:
        """获取所有服务健康状态"""
        # 检查核心服务
        services = [
            "kernel", "scheduler", "gate", "content_factory",
            "evidence", "rumor", "trace", "crew",
            "analytics", "liveops", "safety"
        ]
        
        results = {}
        overall_status = SystemStatus.HEALTHY
        
        for service in services:
            if service in self.health_checks:
                health = self.health_checks[service]
            else:
                # 模拟健康检查
                health = SystemHealth(
                    service_name=service,
                    status=SystemStatus.HEALTHY,
                    latency_ms=10.0 + (hash(service) % 50),
                    last_check=datetime.now(timezone.utc),
                    details={"message": "Service is running"}
                )
                self.health_checks[service] = health
            
            results[service] = health.to_dict()
            
            if health.status == SystemStatus.UNHEALTHY:
                overall_status = SystemStatus.UNHEALTHY
            elif health.status == SystemStatus.DEGRADED and overall_status == SystemStatus.HEALTHY:
                overall_status = SystemStatus.DEGRADED
        
        return {
            "overall_status": overall_status.value,
            "services": results,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    # =========================================================================
    # Alerts
    # =========================================================================
    def create_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str,
        theatre_id: Optional[str] = None
    ) -> Alert:
        """创建告警"""
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            severity=severity,
            title=title,
            message=message,
            source=source
        )
        
        self.alerts[alert.alert_id] = alert
        logger.warning(f"Alert created: [{severity.value}] {title}")
        return alert
    
    def acknowledge_alert(
        self,
        alert_id: str,
        admin_id: str
    ) -> Optional[Alert]:
        """确认告警"""
        alert = self.alerts.get(alert_id)
        if not alert:
            return None
        
        alert.is_acknowledged = True
        alert.acknowledged_by = admin_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        return alert
    
    def resolve_alert(
        self,
        alert_id: str,
        admin_id: str
    ) -> Optional[Alert]:
        """解决告警"""
        alert = self.alerts.get(alert_id)
        if not alert:
            return None
        
        alert.is_resolved = True
        alert.resolved_by = admin_id
        alert.resolved_at = datetime.now(timezone.utc)
        return alert
    
    def get_active_alerts(
        self,
        theatre_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """获取活跃告警"""
        results = []
        for alert in self.alerts.values():
            if alert.is_resolved:
                continue
            if theatre_id and alert.theatre_id != theatre_id:
                continue
            if severity and alert.severity != severity:
                continue
            results.append(alert)
        
        # 按严重程度和时间排序
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.ERROR: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3
        }
        results.sort(key=lambda a: (severity_order[a.severity], a.created_at))
        return results
    
    # =========================================================================
    # Configuration Management
    # =========================================================================
    def get_config(
        self,
        config_key: str,
        default: Any = None
    ) -> Any:
        """获取配置"""
        config = self.system_configs.get(config_key)
        return config.value if config else default
    
    def set_config(
        self,
        config_key: str,
        value: Any,
        admin_id: str,
        description: Optional[str] = None
    ) -> SystemConfig:
        """设置配置"""
        existing = self.system_configs.get(config_key)
        
        if existing:
            existing.value = value
            existing.version += 1
            existing.updated_at = datetime.now(timezone.utc)
            existing.updated_by = admin_id
            if description:
                existing.description = description
            config = existing
        else:
            config = SystemConfig(
                config_key=config_key,
                value=value,
                description=description or "",
                category="custom",
                updated_by=admin_id
            )
            self.system_configs[config_key] = config
        
        logger.info(f"Config updated: {config_key} = {value} by {admin_id}")
        return config
    
    def get_all_configs(
        self,
        category: Optional[str] = None,
        hide_sensitive: bool = True
    ) -> List[Dict[str, Any]]:
        """获取所有配置"""
        results = []
        for config in self.system_configs.values():
            if category and config.category != category:
                continue
            results.append(config.to_dict(hide_sensitive=hide_sensitive))
        return results
    
    # =========================================================================
    # Dashboard Metrics
    # =========================================================================
    def get_dashboard_metrics(self, theatre_id: str) -> DashboardMetrics:
        """获取仪表盘指标"""
        # 在实际实现中，这些数据应该从各个服务聚合
        # 这里使用模拟数据
        
        import random
        
        metrics = DashboardMetrics(
            theatre_id=theatre_id,
            timestamp=datetime.now(timezone.utc),
            total_users=random.randint(1000, 5000),
            active_users_24h=random.randint(200, 800),
            new_users_24h=random.randint(10, 100),
            total_scenes=random.randint(100, 500),
            scenes_today=random.randint(5, 20),
            total_gates=random.randint(50, 200),
            gates_active=random.randint(5, 30),
            total_votes=random.randint(5000, 20000),
            votes_today=random.randint(100, 500),
            total_evidence=random.randint(10000, 50000),
            total_rumors=random.randint(500, 2000),
            avg_response_time_ms=random.uniform(50, 150),
            error_rate=random.uniform(0, 0.05)
        )
        
        return metrics
    
    def get_system_overview(self) -> Dict[str, Any]:
        """获取系统概览"""
        health = self.get_all_health_status()
        active_alerts = self.get_active_alerts()
        
        return {
            "health": health,
            "alerts": {
                "total_active": len(active_alerts),
                "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "error": len([a for a in active_alerts if a.severity == AlertSeverity.ERROR]),
                "warning": len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
                "recent": [a.to_dict() for a in active_alerts[:5]]
            },
            "admin_users": {
                "total": len(self.admin_users),
                "active": len([a for a in self.admin_users.values() if a.is_active])
            },
            "configs": {
                "total": len(self.system_configs),
                "maintenance_mode": self.get_config("system.maintenance_mode", False)
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # =========================================================================
    # Data Export
    # =========================================================================
    def export_theatre_data(
        self,
        theatre_id: str,
        include_users: bool = True,
        include_content: bool = True,
        include_analytics: bool = True
    ) -> Dict[str, Any]:
        """导出剧场数据"""
        export_data = {
            "theatre_id": theatre_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        }
        
        if include_users:
            export_data["users"] = {
                "note": "User data export placeholder",
                "count": 0
            }
        
        if include_content:
            export_data["content"] = {
                "note": "Content data export placeholder",
                "scenes_count": 0,
                "gates_count": 0
            }
        
        if include_analytics:
            export_data["analytics"] = {
                "note": "Analytics data export placeholder",
                "events_count": 0
            }
        
        return export_data
    
    # =========================================================================
    # Maintenance
    # =========================================================================
    def enable_maintenance_mode(
        self,
        admin_id: str,
        reason: str,
        estimated_duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """启用维护模式"""
        self.set_config("system.maintenance_mode", True, admin_id)
        
        # 创建维护告警
        self.create_alert(
            severity=AlertSeverity.WARNING,
            title="系统维护模式已启用",
            message=f"原因: {reason}, 预计时长: {estimated_duration_minutes}分钟",
            source="admin"
        )
        
        return {
            "maintenance_mode": True,
            "enabled_by": admin_id,
            "reason": reason,
            "estimated_duration_minutes": estimated_duration_minutes,
            "enabled_at": datetime.now(timezone.utc).isoformat()
        }
    
    def disable_maintenance_mode(self, admin_id: str) -> Dict[str, Any]:
        """禁用维护模式"""
        self.set_config("system.maintenance_mode", False, admin_id)
        
        return {
            "maintenance_mode": False,
            "disabled_by": admin_id,
            "disabled_at": datetime.now(timezone.utc).isoformat()
        }
    
    # =========================================================================
    # Statistics
    # =========================================================================
    def get_admin_statistics(self) -> Dict[str, Any]:
        """获取管理统计"""
        return {
            "admin_users": {
                "total": len(self.admin_users),
                "by_role": {
                    role.value: len([a for a in self.admin_users.values() if a.role == role])
                    for role in AdminRole
                }
            },
            "alerts": {
                "total": len(self.alerts),
                "active": len([a for a in self.alerts.values() if not a.is_resolved]),
                "acknowledged": len([a for a in self.alerts.values() if a.is_acknowledged and not a.is_resolved])
            },
            "configs": {
                "total": len(self.system_configs),
                "by_category": {}
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
