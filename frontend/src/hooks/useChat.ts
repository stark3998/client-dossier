// frontend/src/hooks/useChat.ts
import { useRef, useCallback, useEffect } from 'react';
import { useClientStore } from '@/stores/clientStore';
import type { WSMessage, ChatMessage } from '@/types';

export function useChat() {
  const wsRef = useRef<WebSocket | null>(null);
  const {
    messages, isStreaming, streamBuffer,
    addMessage, appendToken, addStreamSource,
    startStream, finalizeStream, activeClient,
  } = useClientStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/chat`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);

      if (msg.type === 'token' && msg.content) {
        appendToken(msg.content);
      } else if (msg.type === 'source' && msg.source) {
        addStreamSource(msg.source);
      } else if (msg.type === 'done') {
        finalizeStream();
      } else if (msg.type === 'error') {
        finalizeStream();
        console.error('Chat error:', msg.message);
      }
    };

    ws.onclose = () => {
      setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [appendToken, addStreamSource, finalizeStream]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    if (!content.trim()) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      sources: [],
      timestamp: new Date().toISOString(),
    };
    addMessage(userMsg);
    startStream();

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content,
      client_name: activeClient,
    }));
  }, [addMessage, startStream, activeClient]);

  return {
    messages,
    isStreaming,
    streamBuffer,
    sendMessage,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}
