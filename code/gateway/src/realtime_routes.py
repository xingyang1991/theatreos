"""
TheatreOS Realtime API Routes
实时推送API路由 - WebSocket和SSE端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse

from gateway.src.realtime import (
    get_realtime_service,
    RealtimeService,
    EventType,
    PushEvent
)

router = APIRouter(prefix="/v1/realtime", tags=["Realtime"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Query(..., description="用户ID"),
    theatre_id: Optional[str] = Query(None, description="剧场ID"),
    token: Optional[str] = Query(None, description="认证Token")
):
    """
    WebSocket实时连接端点
    
    连接URL示例: ws://host/v1/realtime/ws?user_id=xxx&theatre_id=yyy&token=zzz
    
    消息格式（JSON）:
    - 接收: {"event_type": "xxx", "data": {...}, "event_id": "xxx", "timestamp": "xxx"}
    - 发送: {"action": "subscribe_stage", "stage_id": "xxx"}
    """
    realtime = get_realtime_service()
    
    # TODO: 验证token
    # if token:
    #     auth_service.verify_token(token)
    
    await realtime.ws_manager.connect(websocket, user_id, theatre_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe_stage":
                stage_id = data.get("stage_id")
                if stage_id:
                    await realtime.ws_manager.subscribe_stage(user_id, stage_id)
                    await realtime.ws_manager.send_personal(
                        user_id,
                        PushEvent(
                            event_type=EventType.NOTIFICATION,
                            data={"message": f"Subscribed to stage {stage_id}"}
                        )
                    )
            
            elif action == "unsubscribe_stage":
                stage_id = data.get("stage_id")
                if stage_id:
                    await realtime.ws_manager.unsubscribe_stage(user_id, stage_id)
            
            elif action == "ping":
                await realtime.ws_manager.send_personal(
                    user_id,
                    PushEvent(
                        event_type=EventType.HEARTBEAT,
                        data={"pong": True}
                    )
                )
    
    except WebSocketDisconnect:
        await realtime.ws_manager.disconnect(websocket)
    except Exception as e:
        await realtime.ws_manager.disconnect(websocket)
        raise


@router.get("/sse")
async def sse_endpoint(
    user_id: str = Query(..., description="用户ID"),
    theatre_id: Optional[str] = Query(None, description="剧场ID"),
    token: Optional[str] = Query(None, description="认证Token")
):
    """
    SSE (Server-Sent Events) 实时连接端点
    
    连接URL示例: GET /v1/realtime/sse?user_id=xxx&theatre_id=yyy
    
    事件格式:
    event: event_type
    data: {"key": "value"}
    id: event_id
    """
    realtime = get_realtime_service()
    
    # TODO: 验证token
    
    queue = await realtime.sse_manager.create_stream(user_id, theatre_id)
    
    async def event_generator():
        try:
            while True:
                try:
                    # 等待事件，超时30秒发送心跳
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    heartbeat = PushEvent(
                        event_type=EventType.HEARTBEAT,
                        data={"keepalive": True}
                    )
                    yield heartbeat.to_sse()
        except asyncio.CancelledError:
            pass
        finally:
            await realtime.sse_manager.close_stream(user_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/stats")
async def get_realtime_stats():
    """获取实时推送服务统计信息"""
    realtime = get_realtime_service()
    return {
        "status": "ok",
        "stats": realtime.get_stats()
    }


@router.post("/test/broadcast")
async def test_broadcast(
    event_type: str = Query("notification", description="事件类型"),
    message: str = Query("Test broadcast message", description="消息内容"),
    theatre_id: Optional[str] = Query(None, description="目标剧场ID")
):
    """
    测试广播接口（仅用于开发测试）
    """
    realtime = get_realtime_service()
    
    try:
        evt_type = EventType(event_type)
    except ValueError:
        evt_type = EventType.NOTIFICATION
    
    event = PushEvent(
        event_type=evt_type,
        data={"message": message, "test": True},
        target_theatre=theatre_id
    )
    
    await realtime.push(event)
    
    return {
        "status": "ok",
        "event_id": event.event_id,
        "broadcast_to": theatre_id or "all"
    }


# 便捷函数：供其他模块调用
async def push_tick_event(theatre_id: str, tick_number: int, world_state: dict):
    """推送Tick事件（供Kernel调用）"""
    realtime = get_realtime_service()
    await realtime.push_tick(theatre_id, {
        "tick_number": tick_number,
        "world_state": world_state
    })


async def push_scene_event(theatre_id: str, scene_id: str, scene_data: dict):
    """推送场景事件（供SceneDelivery调用）"""
    realtime = get_realtime_service()
    await realtime.push_scene_started(theatre_id, {
        "scene_id": scene_id,
        **scene_data
    })


async def push_gate_event(theatre_id: str, gate_id: str, gate_data: dict):
    """推送门事件（供GateSystem调用）"""
    realtime = get_realtime_service()
    await realtime.push_gate_opened(theatre_id, {
        "gate_id": gate_id,
        **gate_data
    })


async def push_evidence_event(user_id: str, evidence_id: str, evidence_data: dict):
    """推送证物事件（供EvidenceSystem调用）"""
    realtime = get_realtime_service()
    await realtime.push_evidence_granted(user_id, {
        "evidence_id": evidence_id,
        **evidence_data
    })
