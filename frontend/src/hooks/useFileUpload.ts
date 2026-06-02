// src/hooks/useFileUpload.ts
import { useCallback } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { useApiFetch } from '@/hooks/useApiFetch';

export function useFileUpload() {
  const { activeClient, setUpload, clearUpload } = useClientStore();
  const { apiFetch } = useApiFetch();

  const uploadFile = useCallback(async (file: File) => {
    if (!activeClient) return;

    const fileId = crypto.randomUUID();
    setUpload(fileId, {
      fileId,
      fileName: file.name,
      percent: 0,
      status: 'uploading',
    });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_name', activeClient);

    try {
      // No Content-Type header — browser sets multipart/form-data boundary automatically
      const res = await apiFetch('/api/files/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        setUpload(fileId, { fileId, fileName: file.name, percent: 0, status: 'error', error: err.detail });
        return;
      }

      setUpload(fileId, { fileId, fileName: file.name, percent: 100, status: 'analyzing' });

      // Auto-clear after 10 seconds
      setTimeout(() => {
        setUpload(fileId, { fileId, fileName: file.name, percent: 100, status: 'done' });
        setTimeout(() => clearUpload(fileId), 5000);
      }, 8000);

    } catch (err) {
      setUpload(fileId, { fileId, fileName: file.name, percent: 0, status: 'error', error: String(err) });
    }
  }, [activeClient, setUpload, clearUpload, apiFetch]);

  return { uploadFile };
}
