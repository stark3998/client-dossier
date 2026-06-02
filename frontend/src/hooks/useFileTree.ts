// frontend/src/hooks/useFileTree.ts
import { useEffect, useCallback, useState } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { useApiFetch } from '@/hooks/useApiFetch';

export function useFileTree() {
  const { activeClient, setFileTree } = useClientStore();
  const [isLoading, setIsLoading] = useState(false);
  const { apiFetch } = useApiFetch();

  const fetchTree = useCallback(async () => {
    if (!activeClient) return;
    setIsLoading(true);
    try {
      const res = await apiFetch(`/api/files/tree?path=${encodeURIComponent(activeClient)}`);
      if (res.ok) {
        const tree = await res.json();
        setFileTree(tree);
      }
    } catch (err) {
      console.error('Failed to fetch file tree:', err);
    } finally {
      setIsLoading(false);
    }
  }, [activeClient, setFileTree, apiFetch]);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

  return { isLoading, refresh: fetchTree };
}
