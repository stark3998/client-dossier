import { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { VscSend } from 'react-icons/vsc';

interface Props {
  onSend: (content: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input, disabled, onSend]);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  };

  return (
    <div className="border-t border-border-default bg-bg-secondary p-3">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        <div className="flex gap-1.5 mb-1">
          {['Summarise client', 'List action items', 'Generate report'].map((action) => (
            <button
              key={action}
              onClick={() => { onSend(action); }}
              disabled={disabled}
              className="px-2 py-1 text-[10px] rounded border border-border-default text-text-muted hover:text-text-primary hover:border-accent/50 transition-colors disabled:opacity-50"
            >
              {action}
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-end gap-2 max-w-4xl mx-auto mt-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your client..."
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-bg-panel border border-border-default rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted font-mono focus:outline-none focus:border-accent disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          aria-label="Send message"
          className="p-2 rounded-md bg-accent text-bg-primary hover:bg-accent-bright transition-colors disabled:opacity-30 disabled:hover:bg-accent shrink-0"
        >
          <VscSend size={18} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
