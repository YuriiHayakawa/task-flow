# Contracts: Project Members & Endpoints Existentes Afetados

Ver convenções gerais em [`../../001-taskflow-mvp/contracts/_conventions.md`](../../001-taskflow-mvp/contracts/_conventions.md).
Cobre módulo novo: **Project Members**. Requisitos relacionados: FR-001 a FR-012.

Autorização por role/membership neste grupo é resolvida por duas dependencies novas em
`app/dependencies/project_authorization.py` (research.md #5): `require_project_visible` (resolve
`Project` do path, `404` para quem não tem acesso) e `require_project_manage` (adicionalmente exige
`OWNER`/`ADMIN` no workspace do projeto).

## Project Members (novo)

### `GET /api/v1/projects/{project_id}/members`

- **Auth**: `require_project_visible` — Owner do workspace, ou membro explícito do projeto.
- **Respostas**: `200` (lista paginada de `ProjectMemberRead`: `user_id`, `name`, `email`,
  `joined_at`) · `404` (sem acesso, ou projeto inexistente).

### `POST /api/v1/projects/{project_id}/members`

- **Auth**: `require_project_manage` (FR-004 — Owner, ou Admin que já é membro do projeto).
- **Body** (`ProjectMemberCreate`): `user_id`.
- **Regras**: `user_id` MUST já ser membro do workspace ao qual o projeto pertence (FR-002) —
  senão `400 BUSINESS_RULE_VIOLATION`.
- **Respostas**: `201` (`ProjectMemberRead`) · `400` (não é membro do workspace) · `403` (Member, ou
  Admin que não é membro do projeto — na prática vira `404` antes de chegar aqui, ver nota de
  segurança em `_conventions.md`) · `404` (sem acesso ao projeto) · `409` (usuário já é membro do
  projeto).

### `DELETE /api/v1/projects/{project_id}/members/{user_id}`

- **Auth**: `require_project_manage`.
- **Regras (FR-010)**: recusa (`409 CONFLICT`) se `user_id` tiver tarefas ativas (status ≠ `DONE`)
  atribuídas a ele **dentro deste projeto** — mesmo formato de erro já usado por
  `DELETE /workspaces/{id}/members/{user_id}` (`details`: lista de `{task_id, title}`).
- **Respostas**: `204` · `404` (sem acesso, membro inexistente) · `409` (tarefas ativas pendentes).

## Endpoints existentes afetados (comportamento MODIFICADO por esta feature)

Estes endpoints já existem (`001-taskflow-mvp/contracts/projects-and-tasks.md`,
`collaboration.md`) — aqui documentamos apenas a MUDANÇA de comportamento introduzida por
`003-membros-projeto`. Tudo que não está listado aqui permanece exatamente como antes.

### `POST /api/v1/workspaces/{workspace_id}/projects`

- **Mudança (FR-003)**: quem cria o projeto é adicionado como seu primeiro `ProjectMember`, na
  mesma transação da criação.

### `GET /api/v1/workspaces/{workspace_id}/projects`

- **Mudança (FR-006)**: `OWNER`/`ADMIN` continuam vendo todos os projetos do workspace (inalterado);
  `MEMBER` passa a ver só os projetos dos quais é membro explícito. Cada item da resposta
  (`ProjectRead`) ganha o campo `is_member` (data-model.md).

### `GET /api/v1/projects/{project_id}`

- **Mudança (FR-007/FR-008)**: além de exigir membership de workspace (já existente), agora também
  exige acesso ao projeto (`require_project_visible`) — Admin que vê o projeto na listagem mas não é
  membro dele recebe `404` aqui, igual a qualquer outra pessoa sem acesso.

### `PATCH /api/v1/projects/{project_id}` / `DELETE /api/v1/projects/{project_id}`

- **Mudança**: passam a usar `require_project_manage` em vez da checagem de role isolada — mesmo
  efeito prático de antes (Owner/Admin) mais a exigência de acesso ao projeto (research.md #5, um
  Admin sem membership nunca passa da checagem de visibilidade).

### `POST /api/v1/tasks` / `PATCH /api/v1/tasks/{task_id}`

- **Mudança (FR-009)**: quando a tarefa pertence a um projeto (`project_id` definido, na criação ou
  já existente na tarefa sendo atualizada), `assignee_id` MUST ser membro desse projeto — não basta
  ser membro do workspace. `400 BUSINESS_RULE_VIOLATION` caso contrário (mesmo código já usado para
  "responsável deve ser membro do workspace").

### `GET /api/v1/tasks` (incl. `?project_id=`) / `GET /api/v1/tasks/{task_id}`

- **Mudança (FR-007)**: tarefas de um projeto restrito deixam de aparecer para quem não tem acesso a
  esse projeto (data-model.md, nova cláusula `visible`) — vale tanto para a listagem quanto para
  abrir uma tarefa isolada por id.

### `GET /api/v1/dashboard`

- **Mudança implícita**: as contagens por status usam a mesma cláusula `visible` de
  `count_by_status` — tarefas de projetos restritos aos quais o usuário não tem acesso deixam de ser
  contadas, automaticamente, sem mudança de código no próprio `DashboardService`.
