# Contracts: Comments, Checklists, Attachments, Task History

Ver convenções gerais em [`_conventions.md`](./_conventions.md), especialmente
"Visibilidade versus participação".
Cobre módulos: **Comments**, **Checklists**, **Attachments**, **Task History**.
Requisitos relacionados: FR-027 a FR-029 (Comments), FR-035 a FR-038 (Checklists/
Attachments), FR-041, FR-042 (Task History). Participantes de tarefa (`TaskMember`,
FR-030 a FR-034) são tratados em `projects-and-tasks.md`, não neste arquivo.

**Regra geral deste grupo (refinamento #8 — colaboração ≠ visibilidade)**:

- **Leitura** (`GET`, em todos os sub-recursos abaixo): `require_workspace_member` — ou
  o criador, para tarefa pessoal. Qualquer membro do workspace pode **ver**
  comentários/checklist/anexos/histórico de qualquer tarefa do workspace.
- **Escrita** (`POST`/`PATCH`/`DELETE` de comentário, checklist e anexo, exceto onde
  indicado): `require_task_participant` — responsável (`assignee`) **ou** participante
  explícito (`TaskMember`); para tarefa pessoal, apenas o criador (que é o único
  "participante" possível). Owner/Admin do workspace **não** ganham esse direito
  automaticamente só por sua role — precisam ser adicionados como participantes da
  tarefa (`POST /tasks/{task_id}/members`) para colaborar, exceto nas ações
  administrativas explicitamente listadas abaixo (remoção de anexo de terceiro).

## Comments

**Fora do MVP (refinamento #7)**: edição e exclusão de comentários — apenas criação e
listagem existem nesta API.

### `GET /api/v1/tasks/{task_id}/comments`

- **Auth**: `require_workspace_member` (visibilidade).
- Paginação padrão, ordenado por `created_at` ascendente.
- **Respostas**: `200` (lista paginada de `CommentRead`: `id`, `author`, `content`,
  `created_at`) · `404`.

### `POST /api/v1/tasks/{task_id}/comments`

- **Auth**: `require_task_participant` (colaboração).
- **Body** (`CommentCreate`): `content`.
- **Regras**: `content` MUST NOT ser vazio ou apenas espaços em branco — validado no
  Schema (Pydantic `min_length` + `strip`) e reforçado por `CHECK` no banco (FR-029).
- **Respostas**: `201` (`CommentRead`) · `400` (conteúdo vazio) · `403` (membro do
  workspace sem ser participante/responsável) · `404`.

## Checklist

**Fora do MVP (refinamento #7)**: edição textual separada de um item — apenas criar,
marcar concluído/pendente e remover.

### `GET /api/v1/tasks/{task_id}/checklist`

- **Auth**: `require_workspace_member` (visibilidade).
- **Respostas**: `200` (lista de `ChecklistItemRead`: `id`, `description`, `is_done`,
  `completed_at`) · `404`. Sem paginação (volume esperado baixo por tarefa).

### `POST /api/v1/tasks/{task_id}/checklist`

- **Auth**: `require_task_participant` (colaboração).
- **Body** (`ChecklistItemCreate`): `description`.
- **Respostas**: `201` (`ChecklistItemRead`) · `403` · `404`.

### `PATCH /api/v1/tasks/{task_id}/checklist/{item_id}`

- **Auth**: `require_task_participant`.
- **Body** (`ChecklistItemUpdate`): `is_done` (único campo suportado — sem edição
  textual de `description` neste MVP, conforme refinamento #7).
- **Regras**: `is_done: true` → preenche `completed_at`; `is_done: false` → limpa.
- **Respostas**: `200` (`ChecklistItemRead`) · `403` · `404`.

### `DELETE /api/v1/tasks/{task_id}/checklist/{item_id}`

- **Auth**: `require_task_participant`.
- **Respostas**: `204` · `403` · `404`.

## Attachments

**Fora do MVP (refinamento #7)**: substituição de arquivo.

### `GET /api/v1/tasks/{task_id}/attachments`

- **Auth**: `require_workspace_member` (visibilidade).
- **Respostas**: `200` (lista de `AttachmentRead`: `id`, `original_filename`,
  `content_type`, `size_bytes`, `uploaded_by`, `created_at`) · `404`.

### `POST /api/v1/tasks/{task_id}/attachments`

- **Auth**: `require_task_participant` (colaboração).
- **Body**: `multipart/form-data` com o arquivo.
- **Regras**: validar `content_type` contra lista permitida e `size_bytes` contra o
  máximo configurado (`core/config.py`) **antes** de gravar em disco; gerar nome de
  armazenamento via UUID (nunca usar `original_filename` como caminho — prevenção de
  path traversal, `research.md` #12).
- **Respostas**: `201` (`AttachmentRead`) · `400` (tipo/tamanho não permitido) · `403` ·
  `404`.

### `GET /api/v1/tasks/{task_id}/attachments/{attachment_id}/download`

- **Auth**: `require_workspace_member` (visibilidade — baixar é uma forma de leitura).
- **Respostas**: `200` (stream do arquivo, com `Content-Disposition` usando
  `original_filename`) · `404`.

### `DELETE /api/v1/tasks/{task_id}/attachments/{attachment_id}`

- **Auth (refinamento #7 — duas vias, não apenas `require_task_participant`)**: quem
  enviou o anexo (`uploaded_by_id == current_user.id`), **ou** Owner/Admin do workspace
  da tarefa (permissão administrativa — não precisam ser participantes para isso, ver
  `research.md` #8).
- **Regras (fluxo de exclusão controlada, `research.md` #12)**: (1) localizar o arquivo
  físico correspondente; (2) validar autorização (uploader ou Owner/Admin); (3) excluir
  o registro em transação e `commit()`; (4) remover o arquivo físico do disco; (5) se a
  remoção do arquivo falhar, registrar log `ERROR` (caminho, `attachment_id`, `task_id`)
  para reconciliação manual — a resposta ao cliente permanece `204` (o registro já foi
  removido com sucesso, que é o estado autoritativo).
- **Respostas**: `204` · `403` (nem uploader nem Owner/Admin) · `404`.

## Task History

**Somente leitura** — sem `POST`/`PATCH`/`DELETE` nesta API; entradas são criadas
exclusivamente pelo `TaskService` como efeito colateral de `PATCH /tasks/{task_id}` (ver
`contracts/projects-and-tasks.md`).

### `GET /api/v1/tasks/{task_id}/history`

- **Auth**: `require_workspace_member` (visibilidade — qualquer membro do workspace vê
  o histórico, mesmo sem ser participante).
- Paginação padrão, ordenado por `changed_at` descendente.
- **Respostas**: `200` (lista paginada de `TaskHistoryEntryRead`: `id`, `field_changed`,
  `old_value`, `new_value`, `changed_by`, `changed_at`) · `404`.
