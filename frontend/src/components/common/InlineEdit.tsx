import { useState, useRef, useEffect } from 'react';
import { VscEdit } from 'react-icons/vsc';

interface Props {
  value: string;
  onSave: (newValue: string) => Promise<void>;
  type?: 'text' | 'textarea' | 'select';
  options?: string[];
  className?: string;
}

export default function InlineEdit({ value, onSave, type = 'text', options, className = '' }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editing]);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  const handleSave = async () => {
    if (draft === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(draft);
    } catch {
      setDraft(value);
    }
    setSaving(false);
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && type !== 'textarea') handleSave();
    if (e.key === 'Escape') {
      setDraft(value);
      setEditing(false);
    }
  };

  if (!editing) {
    return (
      <span
        className={`group inline-flex items-center gap-1 cursor-pointer hover:text-accent ${className}`}
        onClick={() => setEditing(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setEditing(true)}
      >
        <span>{value || <span className="text-text-muted italic">empty</span>}</span>
        <VscEdit className="w-3 h-3 opacity-0 group-hover:opacity-50 transition-opacity" />
      </span>
    );
  }

  const inputClasses = "bg-bg-primary border border-accent rounded px-2 py-1 text-sm text-text-primary outline-none w-full";

  if (type === 'select' && options) {
    return (
      <select
        ref={inputRef as React.RefObject<HTMLSelectElement>}
        value={draft}
        onChange={(e) => { setDraft(e.target.value); }}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className={inputClasses}
        disabled={saving}
      >
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  }

  if (type === 'textarea') {
    return (
      <textarea
        ref={inputRef as React.RefObject<HTMLTextAreaElement>}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className={`${inputClasses} min-h-[60px]`}
        disabled={saving}
      />
    );
  }

  return (
    <input
      ref={inputRef as React.RefObject<HTMLInputElement>}
      type="text"
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={handleSave}
      onKeyDown={handleKeyDown}
      className={inputClasses}
      disabled={saving}
    />
  );
}
