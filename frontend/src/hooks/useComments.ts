import { useCallback, useEffect, useState } from "react";

import * as commentService from "@/services/commentService";
import type { Comment, CommentCreate } from "@/types/comment";

interface UseCommentsResult {
  comments: Comment[];
  isLoading: boolean;
  error: string | null;
  addComment: (payload: CommentCreate) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Comentários de uma tarefa, já em ordem cronológica ascendente (o backend
 * ordena por `created_at`). Sem edição/exclusão neste MVP (contracts/
 * collaboration.md, refinamento #7) — só listar e criar, mesmo padrão de
 * `useTaskMembers`. `addComment` propaga o erro ao chamador (a mensagem do
 * backend, ex. "conteúdo vazio", já é acionável por si só). */
export function useComments(taskId: string): UseCommentsResult {
  const [comments, setComments] = useState<Comment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchComments = useCallback(async () => {
    if (!taskId) {
      setComments([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await commentService.list(taskId);
      setComments(result.items);
    } catch {
      setError("Não foi possível carregar os comentários desta tarefa.");
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchComments();
  }, [fetchComments]);

  const addComment = useCallback(
    async (payload: CommentCreate) => {
      await commentService.create(taskId, payload);
      await fetchComments();
    },
    [taskId, fetchComments],
  );

  return { comments, isLoading, error, addComment, refetch: fetchComments };
}
