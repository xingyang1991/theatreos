// ============================================
// TheatreOS 实时连接 Hook (WebSocket/SSE)
// ============================================

import { useEffect, useRef, useCallback, useState } from 'react';
import { useRealtimeStore } from '@/stores/useStore';
import { realtimeApi } from '@/services/api';
import type { RealtimeEvent } from '@/types';

// -------------------- WebSocket Hook --------------------

interface UseWebSocketOptions {
  theatreId: string;
  onMessage?: (event: RealtimeEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  enabled?: boolean;
}

interface WebSocketResult {
  isConnected: boolean;
  send: (data: any) => void;
  disconnect: () => void;
  reconnect: () => void;
}

export function useWebSocket({
  theatreId,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnectAttempts = 5,
  reconnectInterval = 3000,
  enabled = true,
}: UseWebSocketOptions): WebSocketResult {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  
  const { setConnected, pushEvent } = useRealtimeStore();
  const [isConnected, setIsConnected] = useState(false);

  // 使用ref存储回调，避免依赖变化导致重连
  const callbacksRef = useRef({ onMessage, onConnect, onDisconnect, onError });
  callbacksRef.current = { onMessage, onConnect, onDisconnect, onError };

  const connect = useCallback(() => {
    if (!enabled || !theatreId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const token = localStorage.getItem('theatreos_token');
    const wsUrl = `${realtimeApi.getWebSocketUrl(theatreId)}?token=${token}`;
    
    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!mountedRef.current) return;
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        setConnected(true);
        reconnectCountRef.current = 0;
        callbacksRef.current.onConnect?.();
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data: RealtimeEvent = JSON.parse(event.data);
          pushEvent(data);
          callbacksRef.current.onMessage?.(data);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        console.log('[WebSocket] Disconnected');
        setIsConnected(false);
        setConnected(false);
        callbacksRef.current.onDisconnect?.();

        // 尝试重连
        if (reconnectCountRef.current < reconnectAttempts && mountedRef.current) {
          reconnectCountRef.current += 1;
          console.log(`[WebSocket] Reconnecting... (${reconnectCountRef.current}/${reconnectAttempts})`);
          reconnectTimerRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        callbacksRef.current.onError?.(error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
    }
  }, [theatreId, enabled, reconnectAttempts, reconnectInterval, setConnected, pushEvent]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    reconnectCountRef.current = reconnectAttempts; // 阻止重连
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
    setConnected(false);
  }, [reconnectAttempts, setConnected]);

  const reconnect = useCallback(() => {
    reconnectCountRef.current = 0;
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send: not connected');
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled && theatreId) {
      connect();
    }
    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [theatreId, enabled]); // 只依赖theatreId和enabled

  return {
    isConnected,
    send,
    disconnect,
    reconnect,
  };
}

// -------------------- 简化的 Realtime Hook --------------------

interface UseRealtimeOptions {
  theatreId: string;
  onMessage?: (event: RealtimeEvent) => void;
  preferWebSocket?: boolean;
  enabled?: boolean;
}

export function useRealtime({
  theatreId,
  onMessage,
  preferWebSocket = true,
  enabled = true,
}: UseRealtimeOptions) {
  // 直接使用 WebSocket，简化逻辑避免无限循环
  const ws = useWebSocket({
    theatreId,
    onMessage,
    reconnectAttempts: 3,
    enabled: enabled && !!theatreId,
  });

  return {
    isConnected: ws.isConnected,
    connectionType: 'websocket' as const,
    send: ws.send,
    reconnect: ws.reconnect,
  };
}

export default useRealtime;
