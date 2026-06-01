// frontend/src/hooks/useChat.ts
import { useRef, useCallback, useEffect } from 'react';
import { useClientStore } from '@/stores/clientStore';
import type { WSMessage, ChatMessage } from '@/types';

export function useChat() {
  const wsRef = useRef<WebSocket | null>(null);
  const destroyedRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const {
    messages, isStreaming, streamBuffer,
    addMessage, appendToken, addStreamSource,
    startStream, finalizeStream, activeClient,
    addReasoningStep,
  } = useClientStore();

  const connect = useCallback(() => {
    if (destroyedRef.current) return;
    const state = wsRef.current?.readyState;
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return;

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
      } else if (msg.type === 'thought' || msg.type === 'plan' || msg.type === 'plan_step' || msg.type === 'tool_call' || msg.type === 'tool_result') {
        addReasoningStep({
          type: msg.type,
          content: msg.content || '',
          tool_name: msg.tool_name,
          tool_args: msg.tool_args,
          step_number: msg.step_number,
          step_total: msg.step_total,
          plan_steps: msg.plan_steps,
        });
      }
    };

    ws.onclose = () => {
      if (!destroyedRef.current) {
        reconnectTimerRef.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [appendToken, addStreamSource, finalizeStream, addReasoningStep]);

  useEffect(() => {
    destroyedRef.current = false;
    connect();
    return () => {
      destroyedRef.current = true;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
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
