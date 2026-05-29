import { useRef, useEffect } from 'react';
import { useChat } from '@/hooks/useChat';
import { useClientStore } from '@/stores/clientStore';
import { MessageBubble } from './MessageBubble';
import { StreamingResponse } from './StreamingResponse';
import { ChatInput } from './ChatInput';

export function ChatTerminal() {
  const { messages, isStreaming, sendMessage } = useChat();
  const { streamBuffer, streamSources } = useClientStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamBuffer]);

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-text-muted">
              <p className="text-lg mb-2">Client Intelligence Agent</p>
              <p className="text-sm">Ask about your client documents, generate reports, or explore insights.</p>
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isStreaming && streamBuffer && (
          <StreamingResponse content={streamBuffer} sources={streamSources} />
        )}
        <div ref={bottomRef} />
      </div>
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
