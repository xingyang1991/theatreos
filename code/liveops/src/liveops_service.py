"""
TheatreOS LiveOps System
运营系统 - 活动配置、内容推送、A/B测试、公告管理

核心功能:
1. 活动配置与管理 (Campaign Management)
2. 内容推送 (Push Notifications)
3. A/B测试 (A/B Testing)
4. 公告系统 (Announcement System)
5. 奖励发放 (Reward Distribution)
6. 配置热更新 (Hot Config)
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from decimal import Decimal
import random
import json

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================
class CampaignType(str, Enum):
    """活动类型"""
    DAILY_LOGIN = "DAILY_LOGIN"           # 每日登录
    WEEKLY_CHALLENGE = "WEEKLY_CHALLENGE" # 周挑战
    SPECIAL_EVENT = "SPECIAL_EVENT"       # 特殊活动
    SEASON_PASS = "SEASON_PASS"           # 赛季通行证
    FLASH_SALE = "FLASH_SALE"             # 限时促销
    COMMUNITY_GOAL = "COMMUNITY_GOAL"     # 社区目标


class CampaignStatus(str, Enum):
    """活动状态"""
    DRAFT = "DRAFT"               # 草稿
    SCHEDULED = "SCHEDULED"       # 已排期
    ACTIVE = "ACTIVE"             # 进行中
    PAUSED = "PAUSED"             # 已暂停
    COMPLETED = "COMPLETED"       # 已完成
    CANCELLED = "CANCELLED"       # 已取消


class RewardType(str, Enum):
    """奖励类型"""
    COIN = "COIN"                 # 游戏币
    EVIDENCE = "EVIDENCE"         # 证物
    BADGE = "BADGE"               # 徽章
    TITLE = "TITLE"               # 称号
    EXCLUSIVE_ACCESS = "EXCLUSIVE_ACCESS"  # 独家访问权


class NotificationType(str, Enum):
    """通知类型"""
    PUSH = "PUSH"                 # 推送通知
    IN_APP = "IN_APP"             # 应用内通知
    EMAIL = "EMAIL"               # 邮件
    SMS = "SMS"                   # 短信


class ABTestStatus(str, Enum):
    """A/B测试状态"""
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AnnouncementType(str, Enum):
    """公告类型"""
    SYSTEM = "SYSTEM"             # 系统公告
    EVENT = "EVENT"               # 活动公告
    MAINTENANCE = "MAINTENANCE"   # 维护公告
    UPDATE = "UPDATE"             # 更新公告
    STORY = "STORY"               # 剧情公告


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class Reward:
    """奖励"""
    reward_type: RewardType
    amount: int
    item_id: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reward_type": self.reward_type.value,
            "amount": self.amount,
            "item_id": self.item_id,
            "description": self.description
        }


@dataclass
class Campaign:
    """运营活动"""
    campaign_id: str
    theatre_id: str
    name: str
    campaign_type: CampaignType
    status: CampaignStatus
    description: str
    start_time: datetime
    end_time: datetime
    
    # 参与条件
    min_level: int = 1
    required_crew: bool = False
    target_user_ids: Optional[List[str]] = None
    
    # 奖励配置
    rewards: List[Reward] = field(default_factory=list)
    
    # 进度追踪
    target_value: int = 1
    current_value: int = 0
    participants_count: int = 0
    
    # 元数据
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "theatre_id": self.theatre_id,
            "name": self.name,
            "campaign_type": self.campaign_type.value,
            "status": self.status.value,
            "description": self.description,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "min_level": self.min_level,
            "required_crew": self.required_crew,
            "target_user_ids": self.target_user_ids,
            "rewards": [r.to_dict() for r in self.rewards],
            "target_value": self.target_value,
            "current_value": self.current_value,
            "participants_count": self.participants_count,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class UserCampaignProgress:
    """用户活动进度"""
    user_id: str
    campaign_id: str
    progress_value: int = 0
    is_completed: bool = False
    rewards_claimed: bool = False
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "campaign_id": self.campaign_id,
            "progress_value": self.progress_value,
            "is_completed": self.is_completed,
            "rewards_claimed": self.rewards_claimed,
            "joined_at": self.joined_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class Notification:
    """通知"""
    notification_id: str
    theatre_id: str
    notification_type: NotificationType
    title: str
    content: str
    target_user_ids: Optional[List[str]] = None  # None表示全体用户
    
    # 调度
    scheduled_time: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    
    # 统计
    sent_count: int = 0
    read_count: int = 0
    click_count: int = 0
    
    # 关联
    campaign_id: Optional[str] = None
    deep_link: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "theatre_id": self.theatre_id,
            "notification_type": self.notification_type.value,
            "title": self.title,
            "content": self.content,
            "target_user_ids": self.target_user_ids,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "sent_count": self.sent_count,
            "read_count": self.read_count,
            "click_count": self.click_count,
            "campaign_id": self.campaign_id,
            "deep_link": self.deep_link,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ABTestVariant:
    """A/B测试变体"""
    variant_id: str
    name: str
    description: str
    config: Dict[str, Any]
    traffic_percentage: float  # 0.0-1.0
    users_count: int = 0
    conversions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "traffic_percentage": self.traffic_percentage,
            "users_count": self.users_count,
            "conversions": self.conversions,
            "conversion_rate": self.conversions / self.users_count if self.users_count > 0 else 0
        }


@dataclass
class ABTest:
    """A/B测试"""
    test_id: str
    theatre_id: str
    name: str
    description: str
    status: ABTestStatus
    
    # 测试配置
    feature_key: str  # 被测试的功能键
    variants: List[ABTestVariant] = field(default_factory=list)
    
    # 时间
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 用户分配
    user_assignments: Dict[str, str] = field(default_factory=dict)  # user_id -> variant_id
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "theatre_id": self.theatre_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "feature_key": self.feature_key,
            "variants": [v.to_dict() for v in self.variants],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_users": len(self.user_assignments),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Announcement:
    """公告"""
    announcement_id: str
    theatre_id: str
    announcement_type: AnnouncementType
    title: str
    content: str
    
    # 显示控制
    priority: int = 0  # 越高越优先
    is_pinned: bool = False
    is_popup: bool = False
    
    # 时间
    publish_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expire_time: Optional[datetime] = None
    
    # 统计
    view_count: int = 0
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "announcement_id": self.announcement_id,
            "theatre_id": self.theatre_id,
            "announcement_type": self.announcement_type.value,
            "title": self.title,
            "content": self.content,
            "priority": self.priority,
            "is_pinned": self.is_pinned,
            "is_popup": self.is_popup,
            "publish_time": self.publish_time.isoformat(),
            "expire_time": self.expire_time.isoformat() if self.expire_time else None,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class HotConfig:
    """热更新配置"""
    config_key: str
    theatre_id: str
    value: Any
    version: int = 1
    description: Optional[str] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_key": self.config_key,
            "theatre_id": self.theatre_id,
            "value": self.value,
            "version": self.version,
            "description": self.description,
            "updated_at": self.updated_at.isoformat(),
            "updated_by": self.updated_by
        }


# =============================================================================
# LiveOps Service
# =============================================================================
class LiveOpsService:
    """运营服务"""
    
    def __init__(self, db=None):
        self.db = db
        # 内存存储（演示用）
        self.campaigns: Dict[str, Campaign] = {}
        self.user_progress: Dict[str, Dict[str, UserCampaignProgress]] = {}  # user_id -> {campaign_id -> progress}
        self.notifications: Dict[str, Notification] = {}
        self.ab_tests: Dict[str, ABTest] = {}
        self.announcements: Dict[str, Announcement] = {}
        self.hot_configs: Dict[str, HotConfig] = {}  # config_key -> config
        
        logger.info("LiveOpsService initialized")
    
    # =========================================================================
    # Campaign Management
    # =========================================================================
    def create_campaign(
        self,
        theatre_id: str,
        name: str,
        campaign_type: CampaignType,
        description: str,
        start_time: datetime,
        end_time: datetime,
        rewards: Optional[List[Dict[str, Any]]] = None,
        target_value: int = 1,
        min_level: int = 1,
        required_crew: bool = False,
        created_by: Optional[str] = None
    ) -> Campaign:
        """创建活动"""
        
        reward_list = []
        if rewards:
            for r in rewards:
                reward_list.append(Reward(
                    reward_type=RewardType(r.get("reward_type", "COIN")),
                    amount=r.get("amount", 0),
                    item_id=r.get("item_id"),
                    description=r.get("description")
                ))
        
        campaign = Campaign(
            campaign_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            name=name,
            campaign_type=campaign_type,
            status=CampaignStatus.DRAFT,
            description=description,
            start_time=start_time,
            end_time=end_time,
            rewards=reward_list,
            target_value=target_value,
            min_level=min_level,
            required_crew=required_crew,
            created_by=created_by
        )
        
        self.campaigns[campaign.campaign_id] = campaign
        logger.info(f"Campaign created: {name} [{campaign.campaign_id}]")
        return campaign
    
    def activate_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """激活活动"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        campaign.status = CampaignStatus.ACTIVE
        logger.info(f"Campaign activated: {campaign.name}")
        return campaign
    
    def pause_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """暂停活动"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        campaign.status = CampaignStatus.PAUSED
        return campaign
    
    def complete_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """完成活动"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        campaign.status = CampaignStatus.COMPLETED
        return campaign
    
    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """获取活动"""
        return self.campaigns.get(campaign_id)
    
    def list_campaigns(
        self,
        theatre_id: str,
        status: Optional[CampaignStatus] = None,
        campaign_type: Optional[CampaignType] = None
    ) -> List[Campaign]:
        """列出活动"""
        results = []
        for campaign in self.campaigns.values():
            if campaign.theatre_id != theatre_id:
                continue
            if status and campaign.status != status:
                continue
            if campaign_type and campaign.campaign_type != campaign_type:
                continue
            results.append(campaign)
        
        results.sort(key=lambda c: c.start_time, reverse=True)
        return results
    
    def get_active_campaigns_for_user(
        self,
        theatre_id: str,
        user_id: str,
        user_level: int = 1,
        has_crew: bool = False
    ) -> List[Dict[str, Any]]:
        """获取用户可参与的活动"""
        now = datetime.now(timezone.utc)
        results = []
        
        for campaign in self.campaigns.values():
            if campaign.theatre_id != theatre_id:
                continue
            if campaign.status != CampaignStatus.ACTIVE:
                continue
            if campaign.start_time > now or campaign.end_time < now:
                continue
            if campaign.min_level > user_level:
                continue
            if campaign.required_crew and not has_crew:
                continue
            if campaign.target_user_ids and user_id not in campaign.target_user_ids:
                continue
            
            # 获取用户进度
            progress = self.get_user_campaign_progress(user_id, campaign.campaign_id)
            
            results.append({
                "campaign": campaign.to_dict(),
                "user_progress": progress.to_dict() if progress else None
            })
        
        return results
    
    # =========================================================================
    # User Progress
    # =========================================================================
    def join_campaign(
        self,
        user_id: str,
        campaign_id: str
    ) -> Optional[UserCampaignProgress]:
        """加入活动"""
        campaign = self.campaigns.get(campaign_id)
        if not campaign or campaign.status != CampaignStatus.ACTIVE:
            return None
        
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {}
        
        if campaign_id in self.user_progress[user_id]:
            return self.user_progress[user_id][campaign_id]
        
        progress = UserCampaignProgress(
            user_id=user_id,
            campaign_id=campaign_id
        )
        
        self.user_progress[user_id][campaign_id] = progress
        campaign.participants_count += 1
        
        logger.info(f"User {user_id} joined campaign {campaign.name}")
        return progress
    
    def update_progress(
        self,
        user_id: str,
        campaign_id: str,
        increment: int = 1
    ) -> Optional[UserCampaignProgress]:
        """更新进度"""
        if user_id not in self.user_progress:
            return None
        if campaign_id not in self.user_progress[user_id]:
            return None
        
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        progress = self.user_progress[user_id][campaign_id]
        progress.progress_value += increment
        
        # 检查是否完成
        if progress.progress_value >= campaign.target_value and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = datetime.now(timezone.utc)
            logger.info(f"User {user_id} completed campaign {campaign.name}")
        
        return progress
    
    def claim_rewards(
        self,
        user_id: str,
        campaign_id: str
    ) -> Optional[List[Reward]]:
        """领取奖励"""
        if user_id not in self.user_progress:
            return None
        if campaign_id not in self.user_progress[user_id]:
            return None
        
        progress = self.user_progress[user_id][campaign_id]
        if not progress.is_completed or progress.rewards_claimed:
            return None
        
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        progress.rewards_claimed = True
        logger.info(f"User {user_id} claimed rewards for campaign {campaign.name}")
        
        return campaign.rewards
    
    def get_user_campaign_progress(
        self,
        user_id: str,
        campaign_id: str
    ) -> Optional[UserCampaignProgress]:
        """获取用户活动进度"""
        if user_id not in self.user_progress:
            return None
        return self.user_progress[user_id].get(campaign_id)
    
    # =========================================================================
    # Notifications
    # =========================================================================
    def create_notification(
        self,
        theatre_id: str,
        notification_type: NotificationType,
        title: str,
        content: str,
        target_user_ids: Optional[List[str]] = None,
        scheduled_time: Optional[datetime] = None,
        campaign_id: Optional[str] = None,
        deep_link: Optional[str] = None
    ) -> Notification:
        """创建通知"""
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            notification_type=notification_type,
            title=title,
            content=content,
            target_user_ids=target_user_ids,
            scheduled_time=scheduled_time,
            campaign_id=campaign_id,
            deep_link=deep_link
        )
        
        self.notifications[notification.notification_id] = notification
        logger.info(f"Notification created: {title}")
        return notification
    
    def send_notification(self, notification_id: str) -> Optional[Notification]:
        """发送通知"""
        notification = self.notifications.get(notification_id)
        if not notification:
            return None
        
        notification.sent_at = datetime.now(timezone.utc)
        notification.sent_count = len(notification.target_user_ids) if notification.target_user_ids else 1000  # 模拟全体用户
        
        logger.info(f"Notification sent: {notification.title} to {notification.sent_count} users")
        return notification
    
    def record_notification_read(self, notification_id: str, user_id: str):
        """记录通知已读"""
        notification = self.notifications.get(notification_id)
        if notification:
            notification.read_count += 1
    
    def record_notification_click(self, notification_id: str, user_id: str):
        """记录通知点击"""
        notification = self.notifications.get(notification_id)
        if notification:
            notification.click_count += 1
    
    def get_user_notifications(
        self,
        theatre_id: str,
        user_id: str,
        limit: int = 20
    ) -> List[Notification]:
        """获取用户通知"""
        results = []
        for notification in self.notifications.values():
            if notification.theatre_id != theatre_id:
                continue
            if notification.sent_at is None:
                continue
            if notification.target_user_ids and user_id not in notification.target_user_ids:
                continue
            results.append(notification)
        
        results.sort(key=lambda n: n.sent_at, reverse=True)
        return results[:limit]
    
    # =========================================================================
    # A/B Testing
    # =========================================================================
    def create_ab_test(
        self,
        theatre_id: str,
        name: str,
        description: str,
        feature_key: str,
        variants: List[Dict[str, Any]]
    ) -> ABTest:
        """创建A/B测试"""
        variant_list = []
        for v in variants:
            variant_list.append(ABTestVariant(
                variant_id=str(uuid.uuid4()),
                name=v.get("name", "Variant"),
                description=v.get("description", ""),
                config=v.get("config", {}),
                traffic_percentage=v.get("traffic_percentage", 0.5)
            ))
        
        ab_test = ABTest(
            test_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            name=name,
            description=description,
            status=ABTestStatus.DRAFT,
            feature_key=feature_key,
            variants=variant_list
        )
        
        self.ab_tests[ab_test.test_id] = ab_test
        logger.info(f"A/B Test created: {name}")
        return ab_test
    
    def start_ab_test(self, test_id: str) -> Optional[ABTest]:
        """启动A/B测试"""
        ab_test = self.ab_tests.get(test_id)
        if not ab_test:
            return None
        
        ab_test.status = ABTestStatus.RUNNING
        ab_test.start_time = datetime.now(timezone.utc)
        logger.info(f"A/B Test started: {ab_test.name}")
        return ab_test
    
    def stop_ab_test(self, test_id: str) -> Optional[ABTest]:
        """停止A/B测试"""
        ab_test = self.ab_tests.get(test_id)
        if not ab_test:
            return None
        
        ab_test.status = ABTestStatus.COMPLETED
        ab_test.end_time = datetime.now(timezone.utc)
        return ab_test
    
    def get_user_variant(
        self,
        test_id: str,
        user_id: str
    ) -> Optional[ABTestVariant]:
        """获取用户的测试变体"""
        ab_test = self.ab_tests.get(test_id)
        if not ab_test or ab_test.status != ABTestStatus.RUNNING:
            return None
        
        # 检查是否已分配
        if user_id in ab_test.user_assignments:
            variant_id = ab_test.user_assignments[user_id]
            for variant in ab_test.variants:
                if variant.variant_id == variant_id:
                    return variant
        
        # 随机分配
        rand = random.random()
        cumulative = 0
        selected_variant = ab_test.variants[0]
        
        for variant in ab_test.variants:
            cumulative += variant.traffic_percentage
            if rand <= cumulative:
                selected_variant = variant
                break
        
        ab_test.user_assignments[user_id] = selected_variant.variant_id
        selected_variant.users_count += 1
        
        return selected_variant
    
    def record_ab_conversion(
        self,
        test_id: str,
        user_id: str
    ):
        """记录A/B测试转化"""
        ab_test = self.ab_tests.get(test_id)
        if not ab_test:
            return
        
        if user_id in ab_test.user_assignments:
            variant_id = ab_test.user_assignments[user_id]
            for variant in ab_test.variants:
                if variant.variant_id == variant_id:
                    variant.conversions += 1
                    break
    
    def get_ab_test_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """获取A/B测试结果"""
        ab_test = self.ab_tests.get(test_id)
        if not ab_test:
            return None
        
        return {
            "test": ab_test.to_dict(),
            "winner": self._determine_winner(ab_test),
            "statistical_significance": self._calculate_significance(ab_test)
        }
    
    def _determine_winner(self, ab_test: ABTest) -> Optional[str]:
        """确定获胜变体"""
        if not ab_test.variants:
            return None
        
        best_variant = max(
            ab_test.variants,
            key=lambda v: v.conversions / v.users_count if v.users_count > 0 else 0
        )
        return best_variant.variant_id
    
    def _calculate_significance(self, ab_test: ABTest) -> float:
        """计算统计显著性（简化版）"""
        # 实际应用中应使用卡方检验或贝叶斯方法
        total_users = sum(v.users_count for v in ab_test.variants)
        if total_users < 100:
            return 0.0
        elif total_users < 1000:
            return 0.5
        else:
            return 0.95
    
    # =========================================================================
    # Announcements
    # =========================================================================
    def create_announcement(
        self,
        theatre_id: str,
        announcement_type: AnnouncementType,
        title: str,
        content: str,
        priority: int = 0,
        is_pinned: bool = False,
        is_popup: bool = False,
        publish_time: Optional[datetime] = None,
        expire_time: Optional[datetime] = None
    ) -> Announcement:
        """创建公告"""
        announcement = Announcement(
            announcement_id=str(uuid.uuid4()),
            theatre_id=theatre_id,
            announcement_type=announcement_type,
            title=title,
            content=content,
            priority=priority,
            is_pinned=is_pinned,
            is_popup=is_popup,
            publish_time=publish_time or datetime.now(timezone.utc),
            expire_time=expire_time
        )
        
        self.announcements[announcement.announcement_id] = announcement
        logger.info(f"Announcement created: {title}")
        return announcement
    
    def get_active_announcements(
        self,
        theatre_id: str,
        announcement_type: Optional[AnnouncementType] = None
    ) -> List[Announcement]:
        """获取有效公告"""
        now = datetime.now(timezone.utc)
        results = []
        
        for announcement in self.announcements.values():
            if announcement.theatre_id != theatre_id:
                continue
            if announcement.publish_time > now:
                continue
            if announcement.expire_time and announcement.expire_time < now:
                continue
            if announcement_type and announcement.announcement_type != announcement_type:
                continue
            results.append(announcement)
        
        # 按优先级和置顶排序
        results.sort(key=lambda a: (-a.is_pinned, -a.priority, a.publish_time), reverse=True)
        return results
    
    def record_announcement_view(self, announcement_id: str):
        """记录公告查看"""
        announcement = self.announcements.get(announcement_id)
        if announcement:
            announcement.view_count += 1
    
    # =========================================================================
    # Hot Config
    # =========================================================================
    def set_config(
        self,
        theatre_id: str,
        config_key: str,
        value: Any,
        description: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> HotConfig:
        """设置配置"""
        full_key = f"{theatre_id}:{config_key}"
        
        existing = self.hot_configs.get(full_key)
        version = existing.version + 1 if existing else 1
        
        config = HotConfig(
            config_key=config_key,
            theatre_id=theatre_id,
            value=value,
            version=version,
            description=description,
            updated_by=updated_by
        )
        
        self.hot_configs[full_key] = config
        logger.info(f"Config updated: {config_key} = {value} (v{version})")
        return config
    
    def get_config(
        self,
        theatre_id: str,
        config_key: str,
        default: Any = None
    ) -> Any:
        """获取配置"""
        full_key = f"{theatre_id}:{config_key}"
        config = self.hot_configs.get(full_key)
        return config.value if config else default
    
    def get_all_configs(self, theatre_id: str) -> Dict[str, Any]:
        """获取所有配置"""
        results = {}
        for full_key, config in self.hot_configs.items():
            if config.theatre_id == theatre_id:
                results[config.config_key] = config.to_dict()
        return results
    
    # =========================================================================
    # Statistics
    # =========================================================================
    def get_statistics(self, theatre_id: str) -> Dict[str, Any]:
        """获取运营统计"""
        active_campaigns = len([
            c for c in self.campaigns.values()
            if c.theatre_id == theatre_id and c.status == CampaignStatus.ACTIVE
        ])
        
        running_tests = len([
            t for t in self.ab_tests.values()
            if t.theatre_id == theatre_id and t.status == ABTestStatus.RUNNING
        ])
        
        active_announcements = len(self.get_active_announcements(theatre_id))
        
        return {
            "theatre_id": theatre_id,
            "active_campaigns": active_campaigns,
            "total_campaigns": len([c for c in self.campaigns.values() if c.theatre_id == theatre_id]),
            "running_ab_tests": running_tests,
            "active_announcements": active_announcements,
            "total_notifications_sent": sum(
                n.sent_count for n in self.notifications.values()
                if n.theatre_id == theatre_id and n.sent_at
            ),
            "config_keys": len([c for c in self.hot_configs.values() if c.theatre_id == theatre_id])
        }
