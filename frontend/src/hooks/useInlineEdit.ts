// frontend/src/hooks/useInlineEdit.ts
import { useState, useRef, useCallback } from 'react';
import { showToast } from '@/components/common/Toast';

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? '';
const DEBOUNCE_MS = 500;

/**
 * Generic optimistic inline editing hook.
 * Debounces PATCH requests by 500ms so rapid keystrokes collapse into a single call.
 */
export function useInlineEdit() {
  const [isEditing, setIsEditing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const edit = useCallback(
    (endpoint: string, field: string, value: unknown): Promise<void> => {
      return new Promise<void>((resolve) => {
        if (timerRef.current) {
          clearTimeout(timerRef.current);
        }

        setIsEditing(true);

        timerRef.current = setTimeout(async () => {
          try {
            const res = await fetch(`${BASE_URL}${endpoint}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ [field]: value }),
            });

            if (!res.ok) {
              throw new Error(`Edit failed (${res.status})`);
            }
          } catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error';
            showToast({
              type: 'error',
              title: 'Edit failed',
              message,
            });
          } finally {
            setIsEditing(false);
            resolve();
          }
        }, DEBOUNCE_MS);
      });
    },
    [],
  );

  return { edit, isEditing };
}
