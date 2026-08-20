import httpClient from "@/services/httpClient";
import type { Attachment } from "@/types/attachment";

/** Sem envelope de paginação (mesmo padrão de Checklist/Task Members). */
export function list(taskId: string): Promise<Attachment[]> {
  return httpClient.get<Attachment[]>(`/tasks/${taskId}/attachments`).then((response) => response.data);
}

/** Corpo `multipart/form-data` — não existe `AttachmentCreate` (contracts/
 * collaboration.md: só o arquivo, sem outros campos). O axios monta o
 * `boundary` sozinho ao receber um `FormData` como corpo. */
export function upload(taskId: string, file: File): Promise<Attachment> {
  const formData = new FormData();
  formData.append("file", file);
  return httpClient
    .post<Attachment>(`/tasks/${taskId}/attachments`, formData)
    .then((response) => response.data);
}

export function remove(taskId: string, attachmentId: string): Promise<void> {
  return httpClient.delete(`/tasks/${taskId}/attachments/${attachmentId}`).then(() => undefined);
}

/** Baixa o arquivo como blob — não dá para navegar direto pra URL (a rota
 * exige `Authorization: Bearer`, que só o `httpClient` injeta) — e aciona o
 * download via um link temporário, mesmo truque de sempre para downloads
 * autenticados em SPA. */
export async function download(taskId: string, attachmentId: string, filename: string): Promise<void> {
  const response = await httpClient.get(`/tasks/${taskId}/attachments/${attachmentId}/download`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
