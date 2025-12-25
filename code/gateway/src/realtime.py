"""
TheatreOS Realtime Push Service
实时推送服务 - WebSocket和SSE支持
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse


class EventType(str, Enum):
    """推送事件类型"""
    # 系统事件
    CONNECTED = "connected"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    
    # 世界事件
    TICK = "tick"
    WORLD_STATE_CHANGED = "world_state_changed"
    TENSION_CHANGED = "tension_changed"
    
    # 场景事件
    SCENE_STARTED = "scene_started"
    SCENE_ENDED = "scene_ended"
    NEW_CONTENT = "new_content"
    
    # 门事件
    GATE_OPENED = "gate_opened"
    GATE_CLOSING = "gate_closing"
    GATE_RESOLVED = "gate_resolved"
    VOTE_UPDATE = "vote_update"
    
    # 证物事件
    EVIDENCE_GRANTED = "evidence_granted"
    EVIDENCE_EXPIRING = "evidence_expiring"
    EVIDENCE_TRANSFERRED = "evidence_transferred"
    
    # 谣言事件
    RUMOR_VIRAL = "rumor_viral"
    RUMOR_DEBUNKED = "rumor_debunked"
    
    # 剧团事件
    CREW_ACTION_STARTED = "crew_action_started"
    CREW_ACTION_COMPLETED = "crew_action_completed"
    CREW_MEMBER_JOINED = "crew_member_joined"
    
    # 痕迹事件
    TRACE_DISCOVERED = "trace_discovered"
    
    # 通知
    NOTIFICATION = "notification"
    ANNOUNCEMENT = "announcement"


@dataclass
class PushEvent:
    """推送事件"""
    event_type: EventType
    data: Dict[str, Any]
    target_users: Optional[List[str]] = None  # None表示广播
    target_theatre: Optional[str] = None
    target_stage: Optional[str] = None
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_sse(self) -> str:
        """转换为SSE格式"""
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.data, ensure_ascii=False)}\nid: {self.event_id}\n\n"


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接: user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 剧场订阅: theatre_id -> Set[user_id]
        self.theatre_subscriptions: Dict[str, Set[str]] = {}
        # 舞台订阅: stage_id -> Set[user_id]
        self.stage_subscriptions: Dict[str, Set[str]] = {}
        # 连接元数据: WebSocket -> Dict
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # 锁
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        theatre_id: Optional[str] = None
    ):
        """建立WebSocket连接"""
        await websocket.accept()
        
        async with self._lock:
            # 添加到活跃连接
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            
            # 存储元数据
            self.connection_metadata[websocket] = {
                "user_id": user_id,
                "theatre_id": theatre_id,
                "connected_at": datetime.utcnow().isoformat()
            }
            
            # 订阅剧场
            if theatre_id:
                if theatre_id not in self.theatre_subscriptions:
                    self.theatre_subscriptions[theatre_id] = set()
                self.theatre_subscriptions[theatre_id].add(user_id)
        
        # 发送连接成功事件
        await self.send_personal(
            user_id,
            PushEvent(
                event_type=EventType.CONNECTED,
                data={
                    "user_id": user_id,
                    "theatre_id": theatre_id,
                    "message": "Connected to TheatreOS realtime service"
                }
            )
        )
    
    async def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        async with self._lock:
            metadata = self.connection_metadata.pop(websocket, {})
            user_id = metadata.get("user_id")
            theatre_id = metadata.get("theatre_id")
            
            if user_id and user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    
                    # 清理订阅
                    if theatre_id and theatre_id in self.theatre_subscriptions:
                        self.theatre_subscriptions[theatre_id].discard(user_id)
    
    async def subscribe_stage(self, user_id: str, stage_id: str):
        """订阅舞台事件"""
        async with self._lock:
            if stage_id not in self.stage_subscriptions:
                self.stage_subscriptions[stage_id] = set()
            self.stage_subscriptions[stage_id].add(user_id)
    
    async def unsubscribe_stage(self, user_id: str, stage_id: str):
        """取消订阅舞台事件"""
        async with self._lock:
            if stage_id in self.stage_subscriptions:
                self.stage_subscriptions[stage_id].discard(user_id)
    
    async def send_personal(self, user_id: str, event: PushEvent):
        """发送个人消息"""
        if user_id not in self.active_connections:
            return
        
        message = event.to_json()
        dead_connections = []
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                dead_connections.append(websocket)
        
        # 清理死连接
        for ws in dead_connections:
            await self.disconnect(ws)
    
    async def broadcast_theatre(self, theatre_id: str, event: PushEvent):
        """向剧场内所有用户广播"""
        if theatre_id not in self.theatre_subscriptions:
            return
        
        tasks = []
        for user_id in self.theatre_subscriptions[theatre_id]:
            tasks.append(self.send_personal(user_id, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_stage(self, stage_id: str, event: PushEvent):
        """向舞台订阅者广播"""
        if stage_id not in self.stage_subscriptions:
            return
        
        tasks = []
        for user_id in self.stage_subscriptions[stage_id]:
            tasks.append(self.send_personal(user_id, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_all(self, event: PushEvent):
        """全局广播"""
        tasks = []
        for user_id in self.active_connections.keys():
            tasks.append(self.send_personal(user_id, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def push_event(self, event: PushEvent):
        """智能推送事件"""
        if event.target_users:
            # 定向推送
            tasks = [self.send_personal(uid, event) for uid in event.target_users]
            await asyncio.gather(*tasks, return_exceptions=True)
        elif event.target_stage:
            # 舞台广播
            await self.broadcast_stage(event.target_stage, event)
        elif event.target_theatre:
            # 剧场广播
            await self.broadcast_theatre(event.target_theatre, event)
        else:
            # 全局广播
            await self.broadcast_all(event)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        return {
            "total_users": len(self.active_connections),
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "theatre_subscriptions": {k: len(v) for k, v in self.theatre_subscriptions.items()},
            "stage_subscriptions": {k: len(v) for k, v in self.stage_subscriptions.items()}
        }


class SSEManager:
    """SSE (Server-Sent Events) 管理器"""
    
    def __init__(self):
        # 活跃的SSE流: user_id -> asyncio.Queue
        self.active_streams: Dict[str, asyncio.Queue] = {}
        # 剧场订阅
        self.theatre_subscriptions: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
    
    async def create_stream(self, user_id: str, theatre_id: Optional[str] = None) -> asyncio.Queue:
        """创建SSE流"""
        async with self._lock:
            queue = asyncio.Queue()
            self.active_streams[user_id] = queue
            
            if theatre_id:
                if theatre_id not in self.theatre_subscriptions:
                    self.theatre_subscriptions[theatre_id] = set()
                self.theatre_subscriptions[theatre_id].add(user_id)
        
        # 发送连接事件
        await queue.put(PushEvent(
            event_type=EventType.CONNECTED,
            data={"user_id": user_id, "theatre_id": theatre_id}
        ))
        
        return queue
    
    async def close_stream(self, user_id: str):
        """关闭SSE流"""
        async with self._lock:
            if user_id in self.active_streams:
                del self.active_streams[user_id]
            
            # 清理订阅
            for theatre_id, users in self.theatre_subscriptions.items():
                users.discard(user_id)
    
    async def push_event(self, event: PushEvent):
        """推送事件到SSE流"""
        if event.target_users:
            for user_id in event.target_users:
                if user_id in self.active_streams:
                    await self.active_streams[user_id].put(event)
        elif event.target_theatre:
            if event.target_theatre in self.theatre_subscriptions:
                for user_id in self.theatre_subscriptions[event.target_theatre]:
                    if user_id in self.active_streams:
                        await self.active_streams[user_id].put(event)
        else:
            for queue in self.active_streams.values():
                await queue.put(event)


class RealtimeService:
    """实时推送服务（统一接口）"""
    
    def __init__(self):
        self.ws_manager = ConnectionManager()
        self.sse_manager = SSEManager()
        self._heartbeat_task = None
    
    async def start_heartbeat(self, interval: int = 30):
        """启动心跳任务"""
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(interval)
                event = PushEvent(
                    event_type=EventType.HEARTBEAT,
                    data={"timestamp": datetime.utcnow().isoformat()}
                )
                await self.broadcast(event)
        
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    async def stop_heartbeat(self):
        """停止心跳任务"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
    
    async def push(self, event: PushEvent):
        """推送事件（同时推送到WebSocket和SSE）"""
        await asyncio.gather(
            self.ws_manager.push_event(event),
            self.sse_manager.push_event(event),
            return_exceptions=True
        )
    
    async def broadcast(self, event: PushEvent):
        """广播事件"""
        await self.push(event)
    
    async def notify_user(self, user_id: str, event_type: EventType, data: Dict[str, Any]):
        """通知特定用户"""
        event = PushEvent(
            event_type=event_type,
            data=data,
            target_users=[user_id]
        )
        await self.push(event)
    
    async def notify_theatre(self, theatre_id: str, event_type: EventType, data: Dict[str, Any]):
        """通知剧场内所有用户"""
        event = PushEvent(
            event_type=event_type,
            data=data,
            target_theatre=theatre_id
        )
        await self.push(event)
    
    # 便捷方法：常用事件推送
    async def push_tick(self, theatre_id: str, tick_data: Dict[str, Any]):
        """推送Tick事件"""
        await self.notify_theatre(theatre_id, EventType.TICK, tick_data)
    
    async def push_scene_started(self, theatre_id: str, scene_data: Dict[str, Any]):
        """推送场景开始事件"""
        await self.notify_theatre(theatre_id, EventType.SCENE_STARTED, scene_data)
    
    async def push_gate_opened(self, theatre_id: str, gate_data: Dict[str, Any]):
        """推送门开启事件"""
        await self.notify_theatre(theatre_id, EventType.GATE_OPENED, gate_data)
    
    async def push_evidence_granted(self, user_id: str, evidence_data: Dict[str, Any]):
        """推送证物获得事件"""
        await self.notify_user(user_id, EventType.EVIDENCE_GRANTED, evidence_data)
    
    async def push_rumor_viral(self, theatre_id: str, rumor_data: Dict[str, Any]):
        """推送谣言病毒传播事件"""
        await self.notify_theatre(theatre_id, EventType.RUMOR_VIRAL, rumor_data)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        return {
            "websocket": self.ws_manager.get_stats(),
            "sse": {
                "active_streams": len(self.sse_manager.active_streams)
            }
        }


# 全局单例
_realtime_service_instance = None

def get_realtime_service() -> RealtimeService:
    """获取实时推送服务单例"""
    global _realtime_service_instance
    if _realtime_service_instance is None:
        _realtime_service_instance = RealtimeService()
    return _realtime_service_instance
