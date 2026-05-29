// frontend/src/components/ClientWorkspace.tsx
import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useClientStore } from '@/stores/clientStore';
import { AppShell } from '@/components/layout/AppShell';
import type { ChatMessage } from '@/types';

export function ClientWorkspace() {
  const { clientName } = useParams<{ clientName: string }>();
  const navigate = useNavigate();
  const activeClient = useClientStore((s) => s.activeClient);
  const messages = useClientStore((s) => s.messages);
  const setActiveClient = useClientStore((s) => s.setActiveClient);
  const clearMessages = useClientStore((s) => s.clearMessages);
  const setClientMemory = useClientStore((s) => s.setClientMemory);
  const setFileTree = useClientStore((s) => s.setFileTree);
  const addMessage = useClientStore((s) => s.addMessage);

  // Sync URL param to store on mount / param change
  useEffect(() => {
    if (!clientName) {
      navigate('/');
      return;
    }

    const decoded = decodeURIComponent(clientName);
    if (decoded !== activeClient) {
      // Load persisted chat from localStorage
      const key = `chat_history_${decoded}`;
      const saved = localStorage.getItem(key);
      clearMessages();
      if (saved) {
        try {
          const msgs: ChatMessage[] = JSON.parse(saved);
          msgs.forEach((m) => addMessage(m));
        } catch {
          // ignore corrupt data
        }
      }

      setClientMemory(null);
      setFileTree(null);
      setActiveClient(decoded);
    }
  }, [clientName, activeClient, setActiveClient, clearMessages, setClientMemory, setFileTree, addMessage, navigate]);

  // Persist chat messages to localStorage when they change
  useEffect(() => {
    if (activeClient && messages.length > 0) {
      localStorage.setItem(`chat_history_${activeClient}`, JSON.stringify(messages));
    }
  }, [messages, activeClient]);

  if (!clientName) return null;

  return <AppShell />;
}
