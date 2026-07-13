# Contracts: Workspaces & Workspace Members

Ver convenções gerais em [`_conventions.md`](./_conventions.md).
Cobre módulos: **Workspaces**, **Workspace Members**.
Requisitos relacionados: FR-012 a FR-025.

Autorização por role neste grupo é resolvida por dependencies reutilizáveis (ex.:
`require_workspace_member`, `require_workspace_admin_or_owner`, `require_workspace_owner`)
que recebem `workspace_id` do path e o usuário autenticado, consultando
`WorkspaceMember`.

## `POST /api/v1/workspaces`

- **Auth**: usuário autenticado.
- **Body** (`WorkspaceCreate`): `name`, `description?`.
- **Regras**: criador vira `WorkspaceMember` com `role=OWNER` na mesma transação
  (FR-012).
- **Respostas**: `201` (`WorkspaceRead`) · `422`.

## `GET /api/v1/workspaces`

- **Auth**: usuário autenticado.
- **Regras**: lista apenas workspaces dos quais o usuário é membro (qualquer role).
- **Respostas**: `200` (lista paginada de `WorkspaceRead`, incluindo `my_role`).

## `GET /api/v1/workspaces/{workspace_id}`

- **Auth**: membro do workspace (qualquer role) — `require_workspace_member`.
- **Respostas**: `200` (`WorkspaceRead`) · `404` (não é membro, ou workspace não existe —
  ver nota de segurança em `_conventions.md`).

## `PATCH /api/v1/workspaces/{workspace_id}`

- **Auth**: `require_workspace_owner` (FR-017).
- **Body** (`WorkspaceUpdate`): `name?`, `description?`.
- **Respostas**: `200` (`WorkspaceRead`) · `403` (membro não-Owner) · `404`.

## `DELETE /api/v1/workspaces/{workspace_id}`

- **Auth**: `require_workspace_owner` (FR-017).
- **Regras (fluxo de exclusão controlada — `research.md` #12, detalhado em
  `data-model.md`)**: a exclusão MUST passar por `WorkspaceService.delete`, nunca por um
  cascade de banco disparado sem preparação: (1) `AttachmentService` localiza todos os
  anexos físicos de todas as tarefas do workspace; (2) autorização já validada pela
  dependency; (3) exclusão em transação única — cascade remove projetos, tarefas (e
  transitivamente comentários, checklists, anexos, histórico, participantes,
  notificações) e membros do workspace; (4) após o `commit()`, os arquivos físicos
  coletados no passo 1 são removidos do disco; (5) falha ao remover um arquivo físico é
  logada (`ERROR`, com caminho/`attachment_id`/`task_id`) para reconciliação manual, sem
  fazer a resposta da API falhar.
- **Respostas**: `204` · `403` · `404`.

## Workspace Members

### `GET /api/v1/workspaces/{workspace_id}/members`

- **Auth**: `require_workspace_member` (FR-020 — qualquer role visualiza).
- **Respostas**: `200` (lista paginada de `WorkspaceMemberRead`: `user_id`, `name`,
  `email`, `role`, `joined_at`).

### `POST /api/v1/workspaces/{workspace_id}/members`

- **Auth**: `require_workspace_admin_or_owner` (FR-016 — Owner e Admin adicionam
  Members).
- **Body** (`WorkspaceMemberCreate`): `user_id` (ou `email`, a definir na fase de
  implementação conforme fluxo de convite adotado), `role` (restrito a `MEMBER` neste
  endpoint — promoção a `ADMIN` é uma operação separada, ver abaixo).
- **Respostas**: `201` (`WorkspaceMemberRead`) · `403` (Member tentando adicionar) ·
  `409` (usuário já é membro).

### `PATCH /api/v1/workspaces/{workspace_id}/members/{user_id}/role`

- **Auth**: `require_workspace_owner` **exclusivamente** (FR-014, FR-019 — só o Owner
  promove/rebaixa Admin, e ninguém altera o Owner por esta rota).
- **Body**: `{ "role": "ADMIN" | "MEMBER" }` (`OWNER` não é um valor aceito aqui —
  transferência de titularidade é uma operação dedicada, ver abaixo).
- **Respostas**: `200` (`WorkspaceMemberRead`) · `403` (quem não é Owner tentando
  promover/rebaixar, ou tentando alterar o próprio Owner) · `404`.

### `POST /api/v1/workspaces/{workspace_id}/transfer-ownership`

- **Auth**: `require_workspace_owner` (somente o próprio Owner transfere — FR-019).
- **Body**: `{ "new_owner_user_id": "..." }` (deve já ser membro do workspace).
- **Regras (refinamento #4 — Owner único fortalecido, `research.md` #20)**: operação
  atômica em uma única transação, com bloqueio pessimista explícito: (1) `SELECT ... FOR
  UPDATE` trava a linha `WorkspaceMember` do Owner atual e a do membro-alvo; (2)
  reconfirma sob o lock que quem chamou o endpoint ainda é o Owner; (3) Owner atual
  passa a `ADMIN`, `new_owner_user_id` passa a `OWNER`; (4) `commit()`. Isso serializa
  chamadas concorrentes a este endpoint no mesmo workspace — a segunda chamada aguarda a
  primeira liberar o lock e, ao ser liberada, recebe zero linhas para o predicado
  `role = OWNER` se a primeira já tiver concluído, retornando `409` em vez de agir sobre
  dado desatualizado. Como garantia final (não apenas a primeira linha de defesa), o
  índice único parcial `ux_workspace_members_one_owner` (`data-model.md`) impede, a
  nível de banco, que qualquer caminho de código resulte em dois `OWNER` simultâneos. Se
  a transação falhar em qualquer ponto, `rollback()` completo é aplicado — o Owner
  original permanece `OWNER` e nenhum estado parcial (zero ou dois Owners) é persistido.
- **Respostas**: `200` (`WorkspaceRead`) · `400` (novo Owner não é membro) · `403` ·
  `409` (conflito de concorrência — outra transferência já em andamento, ou o Owner
  mudou entre a autorização e o lock; cliente deve tentar novamente com o estado
  atual).

### `DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}`

- **Auth**: `require_workspace_admin_or_owner` para remover um `MEMBER` (FR-016);
  `require_workspace_owner` para remover um `ADMIN` (FR-015); remover o próprio `OWNER`
  **nunca** é permitido por esta rota (FR-019 — usar `transfer-ownership` antes de sair).
- **Regras**: se o membro a remover é responsável por tarefas ativas nesse workspace,
  **bloquear com `409`** e retornar a lista dessas tarefas no `details` do erro — o
  cliente MUST reatribuí-las (via `PATCH /tasks/{task_id}`) antes de repetir a remoção
  (FR-024, FR-025).
- **Respostas**: `204` · `403` · `404` · `409` (tarefas ativas pendentes de reatribuição).
