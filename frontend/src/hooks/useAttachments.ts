import { useCallback, useEffect, useState } from "react";

import * as attachmentService from "@/services/attachmentService";
import type { Attachment } from "@/types/attachment";

interface UseAttachmentsResult {
  attachments: Attachment[];
  isLoading: boolean;
  error: string | null;
  uploadFile: (file: File) => Promise<void>;
  removeAttachment: (attachmentId: string) => Promise<void>;
  downloadAttachment: (attachmentId: string, filename: string) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Anexos de uma tarefa — mesmo padrão de `useTaskMembers`/`useComments`.
 * `downloadAttachment` não recarrega a lista (não muda nenhum estado
 * observável). */
export function useAttachments(taskId: string): UseAttachmentsResult {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAttachments = useCallback(async () => {
    if (!taskId) {
      setAttachments([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await attachmentService.list(taskId);
      setAttachments(result);
    } catch {
      setError("Não foi possível carregar os anexos desta tarefa.");
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchAttachments();
  }, [fetchAttachments]);

  const uploadFile = useCallback(
    async (file: File) => {
      await attachmentService.upload(taskId, file);
      await fetchAttachments();
    },
    [taskId, fetchAttachments],
  );

  const removeAttachment = useCallback(
    async (attachmentId: string) => {
      await attachmentService.remove(taskId, attachmentId);
      await fetchAttachments();
    },
    [taskId, fetchAttachments],
  );

  const downloadAttachment = useCallback(
    async (attachmentId: string, filename: string) => {
      await attachmentService.download(taskId, attachmentId, filename);
    },
    [taskId],
  );

  return {
    attachments,
    isLoading,
    error,
    uploadFile,
    removeAttachment,
    downloadAttachment,
    refetch: fetchAttachments,
  };
}
