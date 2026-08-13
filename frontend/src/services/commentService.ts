import httpClient from "@/services/httpClient";
import type { Comment, CommentCreate } from "@/types/comment";
import type { PaginatedResponse } from "@/types/common";

/** Envelope paginado (contracts/collaboration.md: "lista paginada de
 * CommentRead") — mesmo atalho já usado no backend (`page=1`, sem
 * paginação real em SQL); o frontend também não implementa paginação, só
 * lista tudo de uma vez. */
export function list(taskId: string): Promise<PaginatedResponse<Comment>> {
  return httpClient
    .get<PaginatedResponse<Comment>>(`/tasks/${taskId}/comments`)
    .then((response) => response.data);
}

export function create(taskId: string, payload: CommentCreate): Promise<Comment> {
  return httpClient
    .post<Comment>(`/tasks/${taskId}/comments`, payload)
    .then((response) => response.data);
}
