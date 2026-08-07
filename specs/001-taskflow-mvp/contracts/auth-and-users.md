# Contracts: Auth, Users/Profile, System Administration

Ver convenções gerais em [`_conventions.md`](./_conventions.md).
Cobre módulos: **Authentication**, **Users / Profile**, **System Administration**.
Requisitos relacionados: FR-001 a FR-004 (Auth), FR-043 a FR-046 (System
Administration), FR-051 a FR-054 (Users/Profile).

## Auth

### `POST /api/v1/auth/register`

- **Auth**: nenhuma.
- **Body** (`UserCreate`): `name`, `email`, `password`.
- **Regras**: `email` único (case-insensitive); senha com requisitos mínimos definidos no
  Schema (ex.: tamanho mínimo) — validado em `schemas`, nunca apenas no frontend.
- **Respostas**: `201` (`UserRead`, sem `password_hash`) · `409` e-mail já cadastrado ·
  `422` dados inválidos.

### `POST /api/v1/auth/login`

- **Auth**: nenhuma.
- **Body** (`LoginRequest`): `email`, `password`.
- **Respostas** (ver `research.md` #1 para o comportamento de conta desativada):
  - `200` (`TokenResponse`: `access_token`, `token_type=bearer`, `expires_in`).
  - `401` — e-mail não cadastrado ou senha incorreta. Código `INVALID_CREDENTIALS`,
    mensagem genérica (não distingue as duas causas entre si).
  - `403` — e-mail e senha corretos, mas `is_active = false`. Código
    `ACCOUNT_DISABLED`, mensagem explícita ("Esta conta está desativada."). **Nunca**
    reaproveitar a mensagem/código de `401` neste caso.
  - `422` dados inválidos.

## Users / Profile (FR-051 a FR-054)

### `GET /api/v1/users/lookup`

> **Adicionado na fase de implementação do frontend de Workspaces (Fase 20)** — o
> contrato de `POST /workspaces/{id}/members` (`contracts/workspaces.md`) já previa que
> a escolha entre `user_id` e e-mail ficaria "a definir na fase de implementação"; o
> backend implementado (Fase 5) fixou `user_id` como obrigatório, mas nenhuma rota
> permitia a um usuário comum resolver um e-mail em `user_id` — sem isso, o fluxo real de
> "adicionar membro por e-mail" era impossível de implementar no frontend. Este endpoint
> fecha essa lacuna.

- **Auth**: usuário autenticado (qualquer conta ativa — não é uma operação
  administrativa; ver `_conventions.md`).
- **Query**: `email` (obrigatório).
- **Regras**: comparação case-insensitive (mesmo índice `lower(email)` de `get_by_email`/
  `email_taken`, `research.md` #10). Retorna apenas dados mínimos e não sensíveis (`id`,
  `name`, `email`) — nunca `is_active`/`is_system_admin`, para não vazar status de conta
  de terceiros. Único propósito é viabilizar a resolução de `user_id` para
  `POST /workspaces/{id}/members`; não é uma busca/listagem geral de usuários (essa
  continua restrita ao System Admin via `GET /admin/users`).
- **Respostas**: `200` (`UserLookupRead`: `id`, `name`, `email`) · `404` nenhum usuário
  com este e-mail · `401` não autenticado.

### `GET /api/v1/users/me`

- **Auth**: usuário autenticado.
- **Respostas**: `200` (`UserRead`: `id`, `name`, `email`, `is_active`, `created_at`).

### `PATCH /api/v1/users/me`

- **Auth**: usuário autenticado.
- **Body** (`UserUpdate`): `name?`, `email?` (ambos opcionais, ao menos um obrigatório).
- **Regras**: novo `email` MUST ser único (FR-053); alteração de senha/foto/exclusão de
  conta MUST NOT ser aceitas por este endpoint (fora do MVP — FR-054; campos não
  reconhecidos são rejeitados com `422`, não silenciosamente ignorados).
- **Respostas**: `200` (`UserRead`) · `409` e-mail já em uso · `422`.

## System Administration (FR-043 a FR-046) — somente System Admin

### `GET /api/v1/admin/users`

- **Auth**: usuário autenticado **e** `is_system_admin = true` (dependency dedicada,
  distinta da dependency de membro de workspace).
- **Query**: paginação padrão; filtro opcional `is_active`.
- **Respostas**: `200` (lista paginada de `UserRead`) · `403` se autenticado mas não é
  System Admin.

### `PATCH /api/v1/admin/users/{user_id}/status`

- **Auth**: System Admin.
- **Body**: `{ "is_active": bool }`.
- **Regras**: **não** altera nome/e-mail (fora do escopo do System Admin — FR-045);
  **não** concede nem requer nenhuma associação de workspace (FR-044/FR-046).
- **Respostas**: `200` (`UserRead`) · `404` usuário não encontrado · `403` se não é
  System Admin.

**Nota explícita de design**: nenhum endpoint sob `/admin` aceita `workspace_id`,
`project_id` ou `task_id` — o System Admin não possui rota de acesso a esses recursos por
meio desta API (reforça FR-042/FR-046 também na superfície da API, não só na
autorização).
