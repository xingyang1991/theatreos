"""
TheatreOS Realtime Push Service - Enhanced
增强的实时推送服务 - 支持完整的E2E闭环事件

新增事件类型:
- SLOT_PHASE_CHANGED: Slot阶段变更（看戏->门厅->结算->回声）
- GATE_STATE_CHANGED: 门状态变更
- EXPLAIN_READY: Explain Card准备就绪
- COUNTDOWN_UPDATE: 倒计时更新
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from enum import Enum

# 导入基础实现
from gateway.src.realtime import (
    RealtimeService, PushEvent, EventType, 
    ConnectionManager, SSEManager, get_realtime_service
)


# =============================================================================
# 扩展事件类型
# =============================================================================
class E2EEventType(str, Enum):
    """E2E闭环扩展事件类型"""
    # Slot相关
    SLOT_PHASE_CHANGED = "slot.phase.changed"
    SLOT_COUNTDOWN = "slot.countdown"
    
    # Gate相关
    GATE_STATE_CHANGED = "gate.state.changed"
    GATE_VOTE_UPDATE = "gate.vote.update"
    GATE_STAKE_UPDATE = "gate.stake.update"
    
    # 结算相关
    EXPLAIN_READY = "explain.ready"
    SETTLEMENT_COMPLETE = "settlement.complete"
    
    # 证物相关
    EVIDENCE_RECEIVED = "evidence.received"
    EVIDENCE_EXPIRING_SOON = "evidence.expiring_soon"
    
    # 系统提醒
    SYSTEM_ALERT = "system.alert"
    PHASE_REMINDER = "phase.reminder"


# =============================================================================
# E2E闭环推送服务
# =============================================================================
class E2ERealtimeService:
    """
    E2E闭环实时推送服务
    
    封装常用的闭环事件推送逻辑
    """
    
    def __init__(self, realtime: RealtimeService = None):
        self.realtime = realtime or get_realtime_service()
    
    # =========================================================================
    # Slot阶段事件
    # =========================================================================
    async def push_slot_phase_changed(
        self,
        theatre_id: str,
        slot_id: str,
        old_phase: str,
        new_phase: str,
        countdown_to_next: int,
        next_phase_at: str = None
    ):
        """
        推送Slot阶段变更事件
        
        触发时机:
        - T+0: 开始看戏
        - T+10: 门厅开启
        - T+12: 开始结算
        - T+15: 进入回声/结束
        """
        event = PushEvent(
            event_type=EventType.NOTIFICATION,  # 使用基础类型
            data={
                "type": E2EEventType.SLOT_PHASE_CHANGED.value,
                "slot_id": slot_id,
                "old_phase": old_phase,
                "new_phase": new_phase,
                "countdown_seconds": countdown_to_next,
                "next_phase_at": next_phase_at,
                "message": self._get_phase_message(new_phase)
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)
    
    def _get_phase_message(self, phase: str) -> str:
        """获取阶段提示消息"""
        messages = {
            "watching": "🎭 演出开始！",
            "gate_open": "🚪 门厅已开启，快来参与决策！",
            "resolving": "⏳ 结算进行中...",
            "echo": "📜 回声时刻，查看结果！",
            "completed": "✅ 本场演出已结束"
        }
        return messages.get(phase, f"阶段变更: {phase}")
    
    async def push_slot_countdown(
        self,
        theatre_id: str,
        slot_id: str,
        current_phase: str,
        countdown_seconds: int
    ):
        """
        推送倒计时更新
        
        用于前端同步显示倒计时
        """
        event = PushEvent(
            event_type=EventType.NOTIFICATION,
            data={
                "type": E2EEventType.SLOT_COUNTDOWN.value,
                "slot_id": slot_id,
                "current_phase": current_phase,
                "countdown_seconds": countdown_seconds
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)
    
    # =========================================================================
    # Gate门事件
    # =========================================================================
    async def push_gate_state_changed(
        self,
        theatre_id: str,
        gate_instance_id: str,
        old_state: str,
        new_state: str,
        countdown_to_close: int = None
    ):
        """
        推送门状态变更事件
        
        状态流转: SCHEDULED -> OPEN -> CLOSING -> RESOLVED
        """
        event = PushEvent(
            event_type=EventType.NOTIFICATION,
            data={
                "type": E2EEventType.GATE_STATE_CHANGED.value,
                "gate_instance_id": gate_instance_id,
                "old_state": old_state,
                "new_state": new_state,
                "countdown_to_close": countdown_to_close,
                "message": self._get_gate_state_message(new_state)
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)
    
    def _get_gate_state_message(self, state: str) -> str:
        """获取门状态消息"""
        messages = {
            "OPEN": "🚪 门已开启，投票开始！",
            "CLOSING": "⚠️ 门即将关闭，最后机会！",
            "RESOLVED": "🎲 结算完成，查看结果！"
        }
        return messages.get(state, f"门状态: {state}")
    
    async def push_gate_vote_update(
        self,
        theatre_id: str,
        gate_instance_id: str,
        vote_distribution: Dict[str, int],
        total_votes: int
    ):
        """
        推送投票更新（实时显示投票分布）
        """
        event = PushEvent(
            event_type=EventType.VOTE_UPDATE,
            data={
                "type": E2EEventType.GATE_VOTE_UPDATE.value,
                "gate_instance_id": gate_instance_id,
                "vote_distribution": vote_distribution,
                "total_votes": total_votes
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)
    
    async def push_gate_stake_update(
        self,
        theatre_id: str,
        gate_instance_id: str,
        stake_distribution: Dict[str, float],
        total_stake: float
    ):
        """
        推送下注更新（实时显示下注分布）
        """
        event = PushEvent(
            event_type=EventType.NOTIFICATION,
            data={
                "type": E2EEventType.GATE_STAKE_UPDATE.value,
                "gate_instance_id": gate_instance_id,
                "stake_distribution": stake_distribution,
                "total_stake": total_stake
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)
    
    # =========================================================================
    # 结算事件
    # =========================================================================
    async def push_explain_ready(
        self,
        theatre_id: str,
        gate_instance_id: str,
        winner_option_id: str,
        winner_label: str,
        result_summary: str
    ):
        """
        推送Explain Card准备就绪事件
        
        触发前端自动跳转到结算页面
        """
        event = PushEvent(
            event_type=EventType.GATE_RESOLVED,
            data={
                "type": E2EEventType.EXPLAIN_READY.value,
                "gate_instance_id": gate_instance_id,
                "winner_option_id": winner_option_id,
                "winner_label": winner_label,
                "result_summary": result_summary,
                "message": f"🎭 结算完成！{winner_label} 获胜"
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)
    
    async def push_user_settlement(
        self,
        user_id: str,
        gate_instance_id: str,
        outcome: str,  # WIN/LOSE/NEUTRAL
        payout: float,
        net_delta: float
    ):
        """
        推送用户个人结算结果
        """
        outcome_messages = {
            "WIN": "🎉 恭喜！你押中了！",
            "LOSE": "😢 很遗憾，下次好运！",
            "NEUTRAL": "📊 你选择了观望"
        }
        
        event = PushEvent(
            event_type=EventType.NOTIFICATION,
            data={
                "type": E2EEventType.SETTLEMENT_COMPLETE.value,
                "gate_instance_id": gate_instance_id,
                "outcome": outcome,
                "payout": payout,
                "net_delta": net_delta,
                "message": outcome_messages.get(outcome, "结算完成")
            },
            target_users=[user_id]
        )
        await self.realtime.push(event)
    
    # =========================================================================
    # 证物事件
    # =========================================================================
    async def push_evidence_received(
        self,
        user_id: str,
        evidence_instance_id: str,
        evidence_name: str,
        tier: str,
        source: str
    ):
        """
        推送获得证物事件
        """
        tier_labels = {"A": "硬证物", "B": "可信线索", "C": "噪声线索", "D": "碎片"}
        
        event = PushEvent(
            event_type=EventType.EVIDENCE_GRANTED,
            data={
                "type": E2EEventType.EVIDENCE_RECEIVED.value,
                "evidence_instance_id": evidence_instance_id,
                "evidence_name": evidence_name,
                "tier": tier,
                "tier_label": tier_labels.get(tier, tier),
                "source": source,
                "message": f"🔍 获得新证物：{evidence_name} ({tier_labels.get(tier, tier)})"
            },
            target_users=[user_id]
        )
        await self.realtime.push(event)
    
    async def push_evidence_expiring_soon(
        self,
        user_id: str,
        evidence_instance_id: str,
        evidence_name: str,
        expires_in_minutes: int
    ):
        """
        推送证物即将过期提醒
        """
        event = PushEvent(
            event_type=EventType.EVIDENCE_EXPIRING,
            data={
                "type": E2EEventType.EVIDENCE_EXPIRING_SOON.value,
                "evidence_instance_id": evidence_instance_id,
                "evidence_name": evidence_name,
                "expires_in_minutes": expires_in_minutes,
                "message": f"⏰ 证物 {evidence_name} 将在 {expires_in_minutes} 分钟后过期！"
            },
            target_users=[user_id]
        )
        await self.realtime.push(event)
    
    # =========================================================================
    # 系统提醒
    # =========================================================================
    async def push_phase_reminder(
        self,
        theatre_id: str,
        reminder_type: str,
        message: str,
        countdown_seconds: int = None,
        action_url: str = None
    ):
        """
        推送阶段提醒
        
        用于在关键时间点提醒用户
        """
        event = PushEvent(
            event_type=EventType.NOTIFICATION,
            data={
                "type": E2EEventType.PHASE_REMINDER.value,
                "reminder_type": reminder_type,
                "message": message,
                "countdown_seconds": countdown_seconds,
                "action_url": action_url
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)
    
    async def push_system_alert(
        self,
        theatre_id: str,
        alert_level: str,  # info/warning/error
        message: str,
        details: Dict[str, Any] = None
    ):
        """
        推送系统警报
        
        用于通知媒体降级、服务异常等情况
        """
        event = PushEvent(
            event_type=EventType.NOTIFICATION,
            data={
                "type": E2EEventType.SYSTEM_ALERT.value,
                "alert_level": alert_level,
                "message": message,
                "details": details or {}
            },
            target_theatre=theatre_id
        )
        await self.realtime.push(event)


# =============================================================================
# 全局单例
# =============================================================================
_e2e_realtime_instance = None

def get_e2e_realtime_service() -> E2ERealtimeService:
    """获取E2E实时推送服务单例"""
    global _e2e_realtime_instance
    if _e2e_realtime_instance is None:
        _e2e_realtime_instance = E2ERealtimeService()
    return _e2e_realtime_instance


# =============================================================================
# 便捷函数（供其他模块调用）
# =============================================================================
async def notify_slot_phase_changed(theatre_id: str, slot_id: str, old_phase: str, new_phase: str, countdown: int):
    """通知Slot阶段变更"""
    service = get_e2e_realtime_service()
    await service.push_slot_phase_changed(theatre_id, slot_id, old_phase, new_phase, countdown)


async def notify_gate_opened(theatre_id: str, gate_instance_id: str, countdown_to_close: int):
    """通知门开启"""
    service = get_e2e_realtime_service()
    await service.push_gate_state_changed(theatre_id, gate_instance_id, "SCHEDULED", "OPEN", countdown_to_close)


async def notify_explain_ready(theatre_id: str, gate_instance_id: str, winner_option_id: str, winner_label: str, summary: str):
    """通知Explain Card准备就绪"""
    service = get_e2e_realtime_service()
    await service.push_explain_ready(theatre_id, gate_instance_id, winner_option_id, winner_label, summary)


async def notify_evidence_received(user_id: str, evidence_id: str, name: str, tier: str, source: str):
    """通知获得证物"""
    service = get_e2e_realtime_service()
    await service.push_evidence_received(user_id, evidence_id, name, tier, source)
