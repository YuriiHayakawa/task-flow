---

description: "Task list for TaskFlow MVP implementation"
---

# Tasks: TaskFlow MVP

**Input**: Design documents from `/specs/001-taskflow-mvp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Incluídas e **obrigatórias**, não opcionais — a TaskFlow Constitution (Princípio VIII) exige
cobertura de testes automatizados para toda regra de negócio crítica, e o CLAUDE.md do projeto reforça
que nenhuma feature é considerada concluída sem validação de funcionamento.

**Organização**: Tarefas agrupadas por User Story (spec.md), em duas passagens sequenciais por story —
**Backend** primeiro (Fases 3-15), depois **Frontend** (Fases 18-30) — conforme a ordem incremental
explicitamente definida em `plan.md` ("1. Backend 2. Testes e validação do backend 3. Frontend
4. Integração 5. Validação final"). Dentro de cada User Story, as tarefas são organizadas em blocos
lógicos (Testes, Schemas, Repositories, Services, Dependencies, Routes, Integração) para facilitar a
leitura durante a implementação. Cada task carrega o rótulo `[US#]` da história a que pertence.

> **Nota de revisão de organização**: esta é uma reorganização puramente estrutural do `tasks.md`
> (agrupamento de microtarefas, blocos por User Story, marcos de progresso, sugestões de commit).
> Nenhuma User Story, prioridade, requisito, dependência, ordem arquitetural, contrato, entidade de
> dados ou decisão de `plan.md`/`research.md`/`data-model.md`/Constitution foi alterada — apenas a
> forma como as mesmas tarefas estão apresentadas e numeradas.

---

## Fluxo recomendado de desenvolvimento

A implementação **não** deve avançar dezenas de tarefas de uma vez. O ciclo esperado, repetido a cada
bloco de trabalho, é:

```
Fase (ou bloco dentro da fase)
        ↓
   Validação
        ↓
    Testes
        ↓
    Commit
        ↓
 Próxima fase
```

Ou seja: implemente um bloco coeso (ex.: os testes de uma story, depois seus schemas, depois seus
repositories...), **valide manualmente** o que foi feito (rodar a aplicação, checar o Swagger, revisar
o diff), **execute os testes automatizados** relacionados, **proponha um commit** (nunca execute
automaticamente — ver CLAUDE.md), e só então avance para o próximo bloco ou fase. Implementar muitas
tarefas sem parar para validar aumenta o risco de erros compostos e dificulta o diagnóstico de falhas.

## Sessões de desenvolvimento

Cada sessão de implementação (uma conversa, um período de trabalho) deve seguir esta sequência:

1. **Identificar a próxima fase** ainda não concluída (ver marcos de progresso ao longo do documento).
2. **Identificar o próximo bloco de tarefas** dentro dessa fase (ex.: "Testes", depois "Schemas",
   depois "Repositories" — não pule blocos).
3. **Implementar apenas aquele bloco** — resistir à tentação de adiantar blocos futuros.
4. **Executar os testes relacionados** àquele bloco/story (e a suíte completa, se o bloco concluir
   uma fase inteira).
5. **Revisar as alterações** (diff, arquivos tocados, aderência à Constitution e ao `plan.md`).
6. **Sugerir um commit** em Conventional Commits, apresentando resumo, arquivos e testes executados —
   e aguardar autorização, conforme o CLAUDE.md.
7. **Somente então avançar** para o próximo bloco ou fase.

Isso mantém cada sessão pequena, revisável e alinhada ao fluxo de commits pequenos e coesos exigido
pelo CLAUDE.md (seção 8 — Commits).

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tasks incompletas)
- **[Story]**: US1–US13, mapeadas 1:1 às User Stories de `spec.md`
- Caminhos de arquivo exatos em cada descrição, conforme a estrutura definida em `plan.md`

## Path Conventions (de `plan.md`)

- Backend: `backend/app/{core,database,models,schemas,repositories,services,routes,enums,dependencies,utils}/`
- Backend tests: `backend/tests/{unit,integration}/`
- Frontend: `frontend/src/{routes,pages,components,layouts,services,hooks,contexts,types,utils,assets,styles}/`
- Frontend tests: `frontend/tests/`
- Migrações: `backend/alembic/versions/`

---

## Phase 1: Setup

**Purpose**: Inicialização do monorepo, sem lógica de negócio ainda.

### Backend

- [ ] T001 Criar a árvore de diretórios completa de `backend/app/` (`core/`, `database/`, `models/`,
  `schemas/`, `repositories/`, `services/`, `routes/`, `enums/`, `dependencies/`, `utils/`) e
  `backend/tests/` (`unit/`, `integration/`), com `__init__.py` em cada pacote, conforme a estrutura de
  `plan.md`
- [ ] T002 [P] Inicializar o projeto Python do backend em `backend/pyproject.toml` (ou
  `backend/requirements.txt`) com FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Pydantic Settings,
  PyJWT, bcrypt, `psycopg[binary]`, pytest, pytest-cov, httpx (`research.md` #3, #4, #5)
- [ ] T003 [P] Criar `backend/.env.example` com `DATABASE_URL`, `JWT_SECRET_KEY`,
  `JWT_EXPIRE_MINUTES`, `APP_TIMEZONE` (default `America/Sao_Paulo`), `ATTACHMENTS_DIR`,
  `ATTACHMENTS_MAX_SIZE_BYTES`, `ATTACHMENTS_ALLOWED_CONTENT_TYPES`,
  `DUE_SOON_CHECK_INTERVAL_SECONDS` (default `60`), `DUE_SOON_WINDOW_HOURS` (default `24`),
  `DUE_SOON_LOCK_KEY`
- [ ] T004 Inicializar `backend/alembic.ini` e o ambiente `backend/alembic/env.py`, conectado à
  `Base.metadata` do SQLAlchemy e a `DATABASE_URL` de `core/config.py` (depende de T001, T002)

### Frontend

- [ ] T005 [P] Criar a árvore de diretórios completa de `frontend/src/` (`routes/`, `pages/`,
  `components/{common,forms,layout,feedback}/`, `layouts/`, `services/`, `hooks/`, `contexts/`,
  `types/`, `utils/`, `assets/`, `styles/`) e `frontend/tests/`, conforme a estrutura de `plan.md`
- [ ] T006 [P] Inicializar o projeto Vite + React 19 + TypeScript em `frontend/package.json`,
  `frontend/vite.config.ts`, `frontend/tsconfig.json`, com `react-router-dom`, `axios`, `vitest`,
  `@testing-library/react` (`research.md` #13, #16)
- [ ] T007 [P] Criar `frontend/.env.example` com `VITE_API_BASE_URL`

### Infraestrutura

- [ ] T008 [P] Criar `backend/Dockerfile`, `frontend/Dockerfile` e `docker-compose.yml` (serviços
  `backend`, `frontend`, `db`) na raiz do repositório (`research.md` #18)

**Checkpoint**: estrutura de diretórios e ferramentas de build prontas; nenhuma linha de lógica de
negócio ainda.

**Commit sugerido**: `chore: configura estrutura inicial do monorepo (backend, frontend, docker)`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura central e schema completo de banco — bloqueia toda User Story.

**⚠️ CRITICAL**: Nenhuma User Story pode começar antes desta fase estar completa. O schema de `Task`
depende de `Workspace`/`Project` já existirem (FKs), por isso **todas** as migrações (não só a de
`users`) são pré-requisito, mesmo para a US1 (tarefas pessoais).

### Core

- [ ] T009 [P] Criar `backend/app/core/config.py` (Pydantic Settings — todas as variáveis de T003)
  (Constitution XII)
- [ ] T010 [P] Criar `backend/app/core/logging.py` (logging estruturado, sem dados sensíveis —
  Constitution XI)
- [ ] T011 [P] Criar `backend/app/core/exceptions.py` (envelope de erro padrão, exceções de domínio,
  exception handlers do FastAPI — incl. `ACCOUNT_DISABLED`, `INVALID_CREDENTIALS`,
  `VALIDATION_ERROR`, `NOT_AUTHENTICATED` — `contracts/_conventions.md`, Constitution X)
- [ ] T012 [P] Criar `backend/app/core/security.py` (hash/verificação de senha com `bcrypt`,
  encode/decode de JWT com `PyJWT` — `research.md` #3, #4)

### Database

- [ ] T013 Criar `backend/app/database/base.py` (Base declarativa do SQLAlchemy)
- [ ] T014 Criar `backend/app/database/connection.py` (engine SQLAlchemy a partir de
  `config.DATABASE_URL`) (depende de T009, T013)
- [ ] T015 Criar `backend/app/database/session.py` (`sessionmaker`, dependency `get_db`) (depende de
  T014)

### Enums

- [ ] T016 [P] Criar os enums controlados em `backend/app/enums/`: `workspace_role.py` (`OWNER`,
  `ADMIN`, `MEMBER`), `task_status.py` (`PENDING`, `IN_PROGRESS`, `DONE`), `task_priority.py` (`LOW`,
  `MEDIUM`, `HIGH`, `URGENT`), `notification_type.py` (`DUE_SOON`, `NEW_COMMENT`, `TASK_CHANGED`)

### Models

- [ ] T017 [P] Criar model `User` em `backend/app/models/user.py` (`id`, `name`, `email`,
  `password_hash`, `is_active`, `is_system_admin`, timestamps `TIMESTAMPTZ`) (depende de T013)
- [ ] T018 [P] Criar model `Workspace` em `backend/app/models/workspace.py` (depende de T013)
- [ ] T019 [P] Criar model `WorkspaceMember` em `backend/app/models/workspace_member.py`
  (`UNIQUE(workspace_id, user_id)`) (depende de T016, T017, T018)
- [ ] T020 [P] Criar model `Project` em `backend/app/models/project.py` (depende de T018)
- [ ] T021 [P] Criar model `Task` em `backend/app/models/task.py` (incl. `due_soon_notified_for`,
  `completed_at`, FKs `ON DELETE RESTRICT`/`CASCADE`/`SET NULL` per `data-model.md`) (depende de
  T016, T017, T018, T020)
- [ ] T022 [P] Criar model `TaskMember` em `backend/app/models/task_member.py`
  (`UNIQUE(task_id, user_id)`) (depende de T017, T021)
- [ ] T023 [P] Criar model `Comment` em `backend/app/models/comment.py` (`CHECK` conteúdo não vazio)
  (depende de T017, T021)
- [ ] T024 [P] Criar model `ChecklistItem` em `backend/app/models/checklist_item.py` (depende de
  T021)
- [ ] T025 [P] Criar model `Attachment` em `backend/app/models/attachment.py` (depende de T017,
  T021)
- [ ] T026 [P] Criar model `TaskHistoryEntry` em `backend/app/models/task_history_entry.py`
  (depende de T017, T021)
- [ ] T027 [P] Criar model `Notification` em `backend/app/models/notification.py` (depende de T016,
  T017, T021)

### Migrações

- [ ] T028 Gerar migração Alembic `0001_foundation_users` em `backend/alembic/versions/` (tabela
  `users` + índice único funcional `ux_users_email_lower` sobre `lower(email)` — `research.md` #10)
  (depende de T004, T017)
- [ ] T029 Gerar migração Alembic `0002_workspaces_and_projects` em `backend/alembic/versions/`
  (`workspaces`, `workspace_members` incl. índice único parcial `ux_workspace_members_one_owner`,
  `projects`) (depende de T028, T018, T019, T020)
- [ ] T030 Gerar migração Alembic `0003_tasks_and_collaboration` em `backend/alembic/versions/`
  (`tasks`, `task_members`, `comments`, `checklist_items`, `attachments`) (depende de T029, T021-T025)
- [ ] T031 Gerar migração Alembic `0004_history_and_notifications` em `backend/alembic/versions/`
  (`task_history_entries`, `notifications`) (depende de T030, T026, T027)
- [ ] T032 Aplicar todas as migrações no banco local (`alembic upgrade head`) e validar o schema
  resultante contra `data-model.md` (depende de T028-T031)

### Dependencies & Entrypoint

- [ ] T033 Criar `backend/app/dependencies/db.py` (dependency `get_db` reexportada para uso nas
  rotas) (depende de T015)
- [ ] T034 Criar `backend/app/dependencies/auth.py` (`get_current_user`: decodifica JWT, carrega
  `User`, valida `is_active` a cada requisição, levanta `ACCOUNT_DISABLED` se desativado —
  `research.md` #1) e `backend/app/dependencies/admin.py` (`require_system_admin`) (depende de T012,
  T017, T033)
- [ ] T035 Criar esqueleto de `backend/app/core/scheduler.py` (loop `asyncio`, início/cancelamento
  via `lifespan`, função de execução placeholder — lógica real de `DUE_SOON` só na Fase 13/US11 —
  `plan.md` "Ordem de Implementação") e `backend/app/main.py` (app FastAPI, prefixo `/api/v1`,
  `lifespan` iniciando/encerrando o scheduler, registro dos exception handlers de T011) (depende de
  T009, T011, T014)

### Test Fixtures

- [ ] T036 [P] Criar `backend/tests/conftest.py` (fixtures: banco de teste migrado via Alembic,
  `TestClient`, factories de `User`/`Workspace`/`Task`, helper para obter token JWT de teste)
  (depende de T032, T035)

**Checkpoint**: schema completo, infraestrutura central pronta — User Stories podem começar.

🎯 **Marco: Fundação concluída**

**Commit sugerido**: `chore: configura infraestrutura central, models e migrações do backend`

---

## Phase 3: Backend — User Story 1: Conta e Tarefas Pessoais (Priority: P1) 🎯 MVP

**Goal**: cadastro, login, e CRUD de tarefas pessoais com status/prioridade/prazo/descrição.

**Independent Test**: cadastrar usuário, logar, criar tarefa pessoal, editar status/prioridade/prazo,
concluir — sem depender de nenhuma outra story.

### Testes

- [ ] T037 [P] [US1] Testes de integração de cadastro/login/rotas protegidas/conta desativada
  (`403 ACCOUNT_DISABLED` distinto de `401 INVALID_CREDENTIALS`) em
  `backend/tests/integration/test_auth.py`
- [ ] T038 [P] [US1] Testes de integração de CRUD de tarefas pessoais (criar/listar/editar/concluir/
  reabrir) em `backend/tests/integration/test_personal_tasks.py`
- [ ] T039 [P] [US1] Testes unitários das invariantes de tarefa pessoal em `TaskService`
  (`assignee_id == creator_id` forçado e imutável enquanto `workspace_id IS NULL`,
  `completed_at` setado/limpo) em `backend/tests/unit/test_task_service.py`

### Schemas

- [ ] T040 [P] [US1] Criar `backend/app/schemas/user.py` (`UserCreate`, `UserRead` — nunca expõe
  `password_hash`) (depende de T017)
- [ ] T041 [P] [US1] Criar `backend/app/schemas/task.py` (`TaskCreate`, `TaskUpdate`, `TaskRead` —
  regras de tarefa pessoal: `project_id` requer `workspace_id`; enums de status/prioridade) (depende
  de T016, T021)

### Repositories

- [ ] T042 [P] [US1] Criar `backend/app/repositories/user_repository.py` (`create`, `get_by_email`,
  `get_by_id`) (depende de T017)
- [ ] T043 [P] [US1] Criar `backend/app/repositories/task_repository.py` (`create`, `get_by_id`,
  `list_personal_by_creator`, `update`, expressão reutilizável de "tarefa ativa") (depende de T021)

### Services

- [ ] T044 [US1] Criar `backend/app/services/auth_service.py` (`register`: e-mail único
  case-insensitive + hash `bcrypt`; `login`: verifica senha, distingue `ACCOUNT_DISABLED` de
  `INVALID_CREDENTIALS`, emite JWT) (depende de T012, T040, T042)
- [ ] T045 [US1] Criar `backend/app/services/task_service.py` — regras de tarefa pessoal (força
  `assignee_id = creator_id`; rejeita `assignee_id` diferente e `project_id` sem `workspace_id`;
  `status = DONE` seta `completed_at`, reabrir limpa) (depende de T041, T043)

### Routes

- [ ] T046 [US1] Criar `backend/app/routes/auth.py` (`POST /api/v1/auth/register`,
  `POST /api/v1/auth/login`) e registrar o router em `backend/app/main.py` (depende de T044)
- [ ] T047 [US1] Criar `backend/app/routes/tasks.py` (`POST /api/v1/tasks`,
  `GET /api/v1/tasks/{task_id}`, `PATCH /api/v1/tasks/{task_id}` — caminho de tarefa pessoal;
  autorização de workspace chega na US4/US5) e registrar o router em `backend/app/main.py` (depende
  de T045, T034)

**Checkpoint**: US1 completa e testável de forma independente.

**Commit sugerido**: `feat(auth): implementa cadastro, login e CRUD de tarefas pessoais (US1)`

---

## Phase 4: Backend — User Story 2: Dashboard Inicial (Priority: P1) 🎯 MVP

**Goal**: contagem de tarefas pendentes/em andamento/concluídas/atrasadas/vencendo hoje.

**Independent Test**: com tarefas pessoais existentes em diferentes status/prazos, `GET /dashboard`
retorna contagens corretas; usuário sem tarefas recebe zeros; tarefas de terceiros não aparecem.

### Testes

- [ ] T048 [P] [US2] Testes de integração do dashboard (contagens por status, atrasada/vencendo hoje
  usando `APP_TIMEZONE`, estado vazio, exclusão de tarefas pessoais de terceiros) em
  `backend/tests/integration/test_dashboard.py`

### Repositories

- [ ] T049 [US2] Adicionar consultas agregadas de contagem (por status; atrasada/vencendo hoje via
  `APP_TIMEZONE`) em `backend/app/repositories/task_repository.py` (depende de T043, T009)

### Schemas & Services

- [ ] T050 [US2] Criar `backend/app/schemas/dashboard.py` (`DashboardSummary`) e
  `backend/app/services/dashboard_service.py` (combina tarefas pessoais do usuário; a união com
  tarefas de workspace fica pronta para uso quando a US3/US4 introduzirem
  `Workspace`/`WorkspaceMember`, sem exigir alteração futura desta função) (depende de T049)

### Routes

- [ ] T051 [US2] Criar `backend/app/routes/dashboard.py` (`GET /api/v1/dashboard`) e registrar o
  router em `backend/app/main.py` (depende de T050, T034)

**Checkpoint**: US1 e US2 funcionam de forma independente (MVP mínimo completo).

🎯 **Marco: Backend MVP concluído** (US1 + US2 — as duas User Stories P1)

**Commit sugerido**: `feat(dashboard): implementa contagens do dashboard inicial (US2)`

---

## Phase 5: Backend — User Story 3: Workspaces, Membros e Roles (Priority: P2)

**Goal**: criar workspace (criador vira Owner), gerenciar membros e roles (Owner/Admin/Member),
com Owner único garantido mesmo sob concorrência.

**Independent Test**: criar workspace, promover um membro a Admin, adicionar um Member, confirmar que
cada role só executa as ações permitidas para si; transferir titularidade com segurança.

### Testes

- [ ] T052 [P] [US3] Testes de integração de CRUD de workspace e matriz de permissões Owner/Admin/
  Member em `backend/tests/integration/test_workspaces.py`
- [ ] T053 [P] [US3] Testes de integração de concorrência na transferência de Owner (`SELECT ... FOR
  UPDATE`, serialização, `409` em conflito — `research.md` #20) em
  `backend/tests/integration/test_workspace_ownership.py`
- [ ] T054 [P] [US3] Teste de integração que força a violação do índice único parcial de Owner
  (dois `OWNER` no mesmo workspace) em `backend/tests/integration/test_workspace_ownership.py`
- [ ] T055 [P] [US3] Testes de integração de bloqueio de remoção de membro com tarefas ativas até
  reatribuição em `backend/tests/integration/test_workspace_members.py`
- [ ] T056 [P] [US3] Testes unitários de `WorkspaceMemberService` (só Owner promove/rebaixa/remove
  Admin; ninguém altera/remove o Owner por outra via) em
  `backend/tests/unit/test_workspace_member_service.py`

### Schemas

- [ ] T057 [US3] Criar `backend/app/schemas/workspace.py` (`WorkspaceCreate`, `WorkspaceUpdate`,
  `WorkspaceRead`) e `backend/app/schemas/workspace_member.py` (`WorkspaceMemberCreate`,
  `WorkspaceMemberRoleUpdate`, `WorkspaceMemberRead`, `TransferOwnershipRequest`) (depende de T016,
  T018, T019)

### Repositories

- [ ] T058 [P] [US3] Criar `backend/app/repositories/workspace_repository.py` (`create`,
  `get_by_id`, `list_for_user`, `update`, `delete`) (depende de T018)
- [ ] T059 [P] [US3] Criar `backend/app/repositories/workspace_member_repository.py` (`create`,
  `get_owner_for_update` e `get_member_for_update` com `SELECT ... FOR UPDATE`, `list_by_workspace`,
  `delete`, `get_role`) (depende de T019)

### Services

- [ ] T060 [US3] Criar `backend/app/services/workspace_service.py` (criar workspace → Owner
  automático na mesma transação; atualizar/excluir restrito ao Owner) (depende de T057, T058, T059)
- [ ] T061 [US3] Criar `backend/app/services/workspace_member_service.py` (adicionar Member
  Owner/Admin; promover/rebaixar Admin exclusivo do Owner; remover membro bloqueado se responsável
  por tarefas ativas — consulta `task_repository`; `transfer_ownership` com duplo `SELECT ... FOR
  UPDATE`, reconfirmação sob lock e rollback integral — `research.md` #20) (depende de T059, T043)

### Dependencies

- [ ] T062 [US3] Criar `backend/app/dependencies/authorization.py` (`require_workspace_member`,
  `require_workspace_admin_or_owner`, `require_workspace_owner` — `404` para não-membros, `403` para
  role insuficiente) (depende de T059, T034)

### Routes

- [ ] T063 [US3] Criar `backend/app/routes/workspaces.py` (`POST/GET/PATCH/DELETE
  /api/v1/workspaces`, `POST /api/v1/workspaces/{id}/transfer-ownership`) e registrar o router em
  `backend/app/main.py` (depende de T060, T062)
- [ ] T064 [US3] Criar `backend/app/routes/workspace_members.py` (`GET/POST
  /api/v1/workspaces/{id}/members`, `PATCH .../members/{user_id}/role`,
  `DELETE .../members/{user_id}`) e registrar o router em `backend/app/main.py` (depende de T061,
  T062)

### Integração

- [ ] T065 [US3] Ativar a união com tarefas de workspace em
  `backend/app/services/dashboard_service.py` e nas consultas de `task_repository.py` agora que
  `Workspace`/`WorkspaceMember` existem (depende de T050, T060)

**Checkpoint**: US1, US2 e US3 funcionam de forma independente.

**Commit sugerido**: `feat(workspaces): implementa workspaces, membros e roles com Owner único garantido (US3)`

---

## Phase 6: Backend — User Story 4: Projetos e Tarefas de Equipe (Priority: P2)

**Goal**: Owner/Admin criam projetos; qualquer membro cria tarefas dentro de projetos/workspace.

**Independent Test**: dentro de um workspace existente, um Admin cria um projeto e qualquer membro
cria uma tarefa vinculada a ele, visível aos demais membros.

### Testes

- [ ] T066 [P] [US4] Testes de integração de CRUD de projeto e permissões (Owner/Admin criam/editam/
  excluem; Member só visualiza) em `backend/tests/integration/test_projects.py`
- [ ] T067 [P] [US4] Testes de integração de exclusão de projeto preservando tarefas (`project_id`
  vira `null`, workspace mantido, comentários/checklists/anexos/histórico/participantes intactos) em
  `backend/tests/integration/test_project_deletion.py`
- [ ] T068 [P] [US4] Testes de integração de criação de tarefa em workspace/projeto (workspace
  derivado do projeto; incompatibilidade workspace/projeto rejeitada; responsável deve ser membro do
  workspace) em `backend/tests/integration/test_workspace_tasks.py`

### Schemas & Repositories

- [ ] T069 [P] [US4] Criar `backend/app/schemas/project.py` (`ProjectCreate`, `ProjectUpdate`,
  `ProjectRead`) e `backend/app/repositories/project_repository.py` (`create`, `get_by_id`,
  `list_by_workspace`, `update`, `delete`) (depende de T020)

### Services

- [ ] T070 [US4] Criar `backend/app/services/project_service.py` (criar/editar restrito a Owner/
  Admin; excluir via service — `ON DELETE SET NULL` desvincula tarefas, log estruturado com
  contagem de tarefas afetadas, nenhuma `TaskHistoryEntry` gerada — `data-model.md`) (depende de
  T069, T062)

### Routes

- [ ] T071 [US4] Criar `backend/app/routes/projects.py` (`POST/GET /api/v1/workspaces/{id}/projects`,
  `GET/PATCH/DELETE /api/v1/projects/{id}`) e registrar o router em `backend/app/main.py` (depende
  de T070)

### Integração

- [ ] T072 [US4] Estender `backend/app/services/task_service.py` para tarefas de workspace/projeto
  (derivar workspace a partir do projeto; validar consistência workspace/projeto — FR-008; validar
  que responsável é membro do workspace) (depende de T045, T069, T059)
- [ ] T073 [US4] Estender `backend/app/routes/tasks.py` com a criação de tarefas de workspace/projeto
  (depende de T072, T071)

**Checkpoint**: US1–US4 funcionam de forma independente.

**Commit sugerido**: `feat(projects): implementa projetos e tarefas de equipe (US4)`

---

## Phase 7: Backend — User Story 5: Participantes de Tarefa (Priority: P2)

**Goal**: adicionar/remover participantes explícitos em tarefas de workspace, além do responsável.

**Independent Test**: sobre uma tarefa de workspace existente, adicionar um participante membro do
mesmo workspace e confirmar que ele passa a constar na lista.

### Testes

- [ ] T074 [P] [US5] Testes de integração de `TaskMember` — permissões (criador/responsável/Owner/
  Admin apenas), invariantes (tarefa pessoal rejeita participante; não-membro do workspace rejeitado;
  responsável é participante implícito; remoção de participante não apaga dados relacionados;
  responsável não removível sem reatribuição prévia) em
  `backend/tests/integration/test_task_members.py`

### Schemas & Repositories

- [ ] T075 [P] [US5] Criar `backend/app/schemas/task_member.py` (`TaskMemberCreate`,
  `TaskMemberRead`) e `backend/app/repositories/task_member_repository.py` (`create`, `delete`,
  `list_by_task` unindo responsável implícito + registros de `TaskMember`, `exists`) (depende de
  T022)

### Services & Dependencies

- [ ] T076 [US5] Criar `backend/app/services/task_member_service.py` (rejeita tarefa pessoal; valida
  que o usuário é membro do workspace da tarefa; rejeita duplicidade; bloqueia remoção do
  responsável) (depende de T075, T059)
- [ ] T077 [US5] Criar `backend/app/dependencies/task_authorization.py`
  (`require_task_participant`, `require_task_editor`, `require_task_delete` — matriz de
  "Visibilidade versus Participação" de `plan.md`/`research.md` #8) (depende de T075, T062, T045)

### Routes & Integração

- [ ] T078 [US5] Criar `backend/app/routes/task_members.py` (`GET/POST
  /api/v1/tasks/{id}/members`, `DELETE /api/v1/tasks/{id}/members/{user_id}`) e registrar o router
  em `backend/app/main.py` (depende de T076, T077)
- [ ] T079 [US5] Substituir a checagem de autorização simplificada de `PATCH/DELETE
  /api/v1/tasks/{id}` (US1) por `require_task_editor`/`require_task_delete` em
  `backend/app/routes/tasks.py` (depende de T077, T078)

**Checkpoint**: US1–US5 funcionam de forma independente.

**Commit sugerido**: `feat(task-members): implementa participantes de tarefa e autorização por participação (US5)`

---

## Phase 8: Backend — User Story 6: Comentários em Tarefas (Priority: P2)

**Goal**: participantes comentam em tarefas; conteúdo vazio é rejeitado.

**Independent Test**: sobre uma tarefa existente, adicionar um comentário e confirmar associação a
tarefa/autor; conteúdo vazio é rejeitado.

### Testes

- [ ] T080 [P] [US6] Testes de integração de comentários (criação, conteúdo vazio rejeitado, criação
  restrita a participantes, listagem visível a todo membro do workspace) em
  `backend/tests/integration/test_comments.py`

### Schemas & Repositories

- [ ] T081 [P] [US6] Criar `backend/app/schemas/comment.py` (`CommentCreate`, `CommentRead`) e
  `backend/app/repositories/comment_repository.py` (`create`, `list_by_task`) (depende de T023)
- [ ] T082 [P] [US6] Criar `backend/app/repositories/notification_repository.py` (`create`,
  `list_by_recipient`, `mark_read` — primeiro consumidor é `NEW_COMMENT`, estendido na US11) (depende
  de T027)

### Services

- [ ] T083 [US6] Criar `backend/app/services/comment_service.py` (rejeita conteúdo vazio; cria
  comentário + notificação `NEW_COMMENT` para os demais participantes na mesma transação —
  `research.md` #19) (depende de T081, T082, T076)

### Routes

- [ ] T084 [US6] Criar `backend/app/routes/comments.py` (`GET/POST /api/v1/tasks/{id}/comments` —
  leitura via `require_workspace_member`, escrita via `require_task_participant`) e registrar o
  router em `backend/app/main.py` (depende de T083, T077)

**Checkpoint**: US1–US6 funcionam de forma independente.

**Commit sugerido**: `feat(comments): implementa comentários em tarefas (US6)`

---

## Phase 9: Backend — User Story 7: Perfil do Usuário (Priority: P2)

**Goal**: visualizar/editar nome e e-mail próprios; consultar status da conta.

**Independent Test**: logado, acessar perfil, alterar nome, confirmar reflexo; e-mail duplicado
(inclusive variando maiúsculas/minúsculas) é rejeitado.

### Testes

- [ ] T085 [P] [US7] Testes de integração de perfil (visualizar, editar nome, editar e-mail,
  unicidade case-insensitive no cadastro e na atualização) em
  `backend/tests/integration/test_profile.py`

### Schemas & Repositories

- [ ] T086 [US7] Estender `backend/app/schemas/user.py` com `UserUpdate` (`name?`, `email?` — rejeita
  campos fora do MVP como senha/foto) e `backend/app/repositories/user_repository.py` com `update` e
  `email_taken(email, exclude_user_id)` (case-insensitive via índice `lower(email)`) (depende de
  T040, T042)

### Services & Routes

- [ ] T087 [US7] Criar `backend/app/services/user_service.py` (`get_me`, `update_me` — normaliza
  e-mail para lowercase, valida unicidade antes de persistir) (depende de T086)
- [ ] T088 [US7] Criar `backend/app/routes/users.py` (`GET/PATCH /api/v1/users/me`) e registrar o
  router em `backend/app/main.py` (depende de T087, T034)

**Checkpoint**: US1–US7 funcionam de forma independente.

**Commit sugerido**: `feat(profile): implementa visualização e edição de perfil do usuário (US7)`

---

## Phase 10: Backend — User Story 8: Busca, Filtros e Ordenação de Tarefas (Priority: P2)

**Goal**: pesquisar por título, filtrar por status/prioridade/workspace/projeto/responsável
(combináveis), ordenar por prazo/prioridade/data de criação.

**Independent Test**: com tarefas variadas existentes, combinar busca + filtros + ordenação em uma
única consulta e validar o resultado.

### Testes

- [ ] T089 [P] [US8] Testes de integração de busca/filtros/ordenação combinados, incl. resultado
  vazio sem erro, em `backend/tests/integration/test_task_search.py`

### Repositories & Schemas

- [ ] T090 [US8] Estender `backend/app/repositories/task_repository.py` com busca por título
  (`ILIKE`), filtros combináveis (status, prioridade, workspace, projeto, responsável), ordenação
  (`due_date`, `priority`, `created_at`) e paginação — consulta única parametrizada evitando N+1 — e
  estender `backend/app/schemas/task.py` com os parâmetros de consulta e o envelope de resposta
  paginado (`items`, `page`, `page_size`, `total`) (depende de T043, T072, T041)

### Routes

- [ ] T091 [US8] Estender `GET /api/v1/tasks` em `backend/app/routes/tasks.py` com os novos
  parâmetros de query (depende de T090)

**Checkpoint**: US1–US8 funcionam de forma independente.

**Commit sugerido**: `feat(tasks): implementa busca, filtros e ordenação de tarefas (US8)`

---

## Phase 11: Backend — User Story 9: Checklists em Tarefas (Priority: P3)

**Goal**: participantes adicionam itens de checklist e marcam concluído/pendente.

**Independent Test**: sobre uma tarefa existente, adicionar itens, marcar um como concluído, remover.

### Testes

- [ ] T092 [P] [US9] Testes de integração de checklist (criar, marcar concluído/pendente, remover,
  restrito a participantes) em `backend/tests/integration/test_checklist.py`

### Schemas & Repositories

- [ ] T093 [P] [US9] Criar `backend/app/schemas/checklist_item.py` (`ChecklistItemCreate`,
  `ChecklistItemUpdate` — só `is_done`, `ChecklistItemRead`) e
  `backend/app/repositories/checklist_item_repository.py` (`create`, `list_by_task`, `update`,
  `delete`) (depende de T024)

### Services & Routes

- [ ] T094 [US9] Criar `backend/app/services/checklist_service.py` (`is_done: true` seta
  `completed_at`; `false` limpa) (depende de T093)
- [ ] T095 [US9] Criar `backend/app/routes/checklist.py` (`GET/POST /api/v1/tasks/{id}/checklist`,
  `PATCH/DELETE .../checklist/{item_id}` — leitura via `require_workspace_member`, escrita via
  `require_task_participant`) e registrar o router em `backend/app/main.py` (depende de T094, T077)

**Checkpoint**: US1–US9 funcionam de forma independente.

**Commit sugerido**: `feat(checklist): implementa checklists em tarefas (US9)`

---

## Phase 12: Backend — User Story 10: Anexos em Tarefas (Priority: P3)

**Goal**: participantes anexam arquivos; upload/listagem/download/remoção controlados.

**Independent Test**: enviar um anexo a uma tarefa existente e confirmar vínculo a tarefa/usuário;
excluir e confirmar remoção do arquivo físico.

### Testes

- [ ] T096 [P] [US10] Testes de integração de anexos (upload com validação de tipo/tamanho,
  listagem, download, remoção por uploader ou Owner/Admin, prevenção de path traversal) em
  `backend/tests/integration/test_attachments.py`

### Utils, Schemas & Repositories

- [ ] T097 [US10] Criar `backend/app/utils/file_storage.py` (geração de nome de arquivo seguro via
  UUID, validação de extensão/tipo/tamanho, gravação/remoção em `ATTACHMENTS_DIR` — prevenção de
  path traversal, `research.md` #12), `backend/app/schemas/attachment.py` (`AttachmentRead`) e
  `backend/app/repositories/attachment_repository.py` (`create`, `list_by_task`, `get_by_id`,
  `delete`) (depende de T025)

### Services & Routes

- [ ] T098 [US10] Criar `backend/app/services/attachment_service.py` (upload validando tipo/tamanho
  antes de gravar; exclusão controlada — localizar arquivo, autorizar, excluir registro em
  transação, remover arquivo físico após commit, logar falha sem falhar a resposta — `research.md`
  #12) (depende de T097)
- [ ] T099 [US10] Criar `backend/app/routes/attachments.py` (`GET/POST
  /api/v1/tasks/{id}/attachments`, `GET .../attachments/{id}/download`,
  `DELETE .../attachments/{id}` — remoção por uploader ou `require_workspace_admin_or_owner`) e
  registrar o router em `backend/app/main.py` (depende de T098, T077, T062)

**Checkpoint**: US1–US10 funcionam de forma independente.

🎯 **Marco: Colaboração concluída** (Comentários — US6, Checklists — US9, Anexos — US10)

**Commit sugerido**: `feat(attachments): implementa anexos em tarefas com exclusão controlada (US10)`

---

## Phase 13: Backend — User Story 11: Notificações (Priority: P3)

**Goal**: notificações in-app de prazo próximo (via tarefa periódica), novo comentário e alterações
relevantes.

**Independent Test**: gerar um evento relevante (comentário em tarefa da qual o usuário participa) e
confirmar notificação criada; job periódico gera `DUE_SOON` sem duplicar.

### Testes

- [ ] T100 [P] [US11] Testes de integração de listagem/marcação de notificações
  (`GET /notifications`, marcar lida/todas lidas, isolamento por destinatário) em
  `backend/tests/integration/test_notifications.py`
- [ ] T101 [P] [US11] Testes de integração das regras completas de `due_soon_notified_for`
  (`NULL` quando `due_date` nulo; reset ao alterar prazo; `DONE` nunca gera `DUE_SOON`; Notification +
  campo na mesma transação; execução repetida não duplica; reabrir sem alterar prazo não notifica;
  reabrir com novo prazo notifica — `research.md` #2) em
  `backend/tests/integration/test_due_soon_notifications.py`
- [ ] T102 [P] [US11] Teste de integração que impede execução simultânea do job (advisory lock
  obtido manualmente por uma "segunda instância" simulada; `run_due_soon_job()` não processa nada
  até o lock ser liberado) em `backend/tests/integration/test_due_soon_scheduler.py`

### Schemas & Repositories

- [ ] T103 [US11] Criar `backend/app/schemas/notification.py` (`NotificationRead`) e estender
  `backend/app/repositories/notification_repository.py` com consultas de tarefas elegíveis a
  `DUE_SOON` (`status != DONE`, `due_date` não nulo, dentro de `DUE_SOON_WINDOW_HOURS`,
  `due_soon_notified_for IS DISTINCT FROM due_date`) (depende de T082, T027)

### Services & Scheduler

- [ ] T104 [US11] Criar `backend/app/services/notification_service.py` —
  `generate_due_soon_notifications(session, now)`: cria `Notification` + atualiza
  `due_soon_notified_for` na mesma transação, por tarefa elegível (depende de T103)
- [ ] T105 [US11] Implementar `run_due_soon_job()` em `backend/app/core/scheduler.py` (conexão
  dedicada + `pg_try_advisory_lock`, `Session` própria por execução, chama
  `generate_due_soon_notifications`, libera lock em `finally`, fecha Session/conexão em `finally` —
  `research.md` #2) e conectar o loop `asyncio` a ela via `asyncio.to_thread` a cada
  `DUE_SOON_CHECK_INTERVAL_SECONDS` (depende de T035, T104)

### Integração

- [ ] T106 [US11] Estender `backend/app/services/task_service.py` (`update`) para criar
  `Notification` tipo `TASK_CHANGED` para os participantes afetados (exceto quem alterou) na mesma
  transação de qualquer mudança de status/prioridade/prazo/responsável (depende de T072, T082, T076)

### Routes

- [ ] T107 [US11] Criar `backend/app/routes/notifications.py` (`GET /api/v1/notifications`,
  `PATCH .../{id}/read`, `PATCH /read-all`) e registrar o router em `backend/app/main.py` (depende
  de T103, T034)

**Checkpoint**: US1–US11 funcionam de forma independente.

**Commit sugerido**: `feat(notifications): implementa notificações in-app e tarefa periódica de prazo (US11)`

---

## Phase 14: Backend — User Story 12: Histórico de Alterações da Tarefa (Priority: P3)

**Goal**: histórico automático de mudanças de status/prioridade/prazo/responsável.

**Independent Test**: alterar status/prioridade/prazo/responsável de uma tarefa e confirmar entrada
de histórico com campo/valor anterior/novo valor/autor/data.

### Testes

- [ ] T108 [P] [US12] Testes de integração de histórico (entrada criada para cada campo rastreado,
  ordem cronológica, reatribuição por remoção de membro aparece como alteração de responsável) em
  `backend/tests/integration/test_task_history.py`

### Schemas & Repositories

- [ ] T109 [US12] Criar `backend/app/schemas/task_history.py` (`TaskHistoryEntryRead`) e
  `backend/app/repositories/task_history_repository.py` (`create`, `list_by_task` ordenado por
  `changed_at`) (depende de T026)

### Integração & Routes

- [ ] T110 [US12] Estender `backend/app/services/task_service.py` (`update`) para criar
  `TaskHistoryEntry` (campo alterado, valor anterior, novo valor, autor) na mesma transação da
  notificação `TASK_CHANGED` (US11) (depende de T106, T109)
- [ ] T111 [US12] Criar `backend/app/routes/history.py` (`GET /api/v1/tasks/{id}/history` via
  `require_workspace_member`) e registrar o router em `backend/app/main.py` (depende de T109, T077)

**Checkpoint**: US1–US12 funcionam de forma independente.

**Commit sugerido**: `feat(task-history): implementa histórico automático de alterações da tarefa (US12)`

---

## Phase 15: Backend — User Story 13: Administração de Usuários da Plataforma (System Admin) (Priority: P3)

**Goal**: System Admin lista usuários e ativa/desativa contas, sem ganhar acesso a workspaces.

**Independent Test**: autenticado como System Admin, listar usuários, desativar uma conta, confirmar
que ela não consegue mais logar; confirmar que o System Admin continua sem acesso a workspaces dos
quais não é membro.

### Testes

- [ ] T112 [P] [US13] Testes de integração de administração de usuários (listar, ativar/desativar,
  ausência de acesso a workspace, incapacidade de editar tarefas/projetos/config de workspace) em
  `backend/tests/integration/test_admin.py`

### Schemas & Services

- [ ] T113 [US13] Criar `backend/app/schemas/admin.py` (`UserStatusUpdate`, reaproveita `UserRead`
  paginado) e `backend/app/services/admin_service.py` (`list_users`, `set_user_active` — sem
  qualquer acesso a `Workspace`/`Project`/`Task`) (depende de T040, T042)

### Routes

- [ ] T114 [US13] Criar `backend/app/routes/admin.py` (`GET /api/v1/admin/users`,
  `PATCH /api/v1/admin/users/{id}/status` via `require_system_admin`) e registrar o router em
  `backend/app/main.py` (depende de T113, T034)

**Checkpoint**: todas as 13 User Stories funcionam de forma independente no backend.

**Commit sugerido**: `feat(admin): implementa administração de usuários da plataforma (US13)`

---

## Phase 16: Backend Testing & Hardening (cross-cutting)

**Purpose**: fechar a Fase 7 de `plan.md` — revisão completa antes do frontend.

### Cobertura

- [ ] T115 Executar toda a suíte `pytest` do backend e revisar cobertura (`pytest --cov=app`),
  fechando qualquer lacuna nas regras críticas listadas em `plan.md` (seção Testes)
- [ ] T116 [P] Teste de integração dedicado do cálculo de "hoje"/"atrasada"/"vencendo hoje" usando
  `APP_TIMEZONE` próximo à virada de dia UTC vs. `America/Sao_Paulo` em
  `backend/tests/integration/test_timezone_calculations.py`

### Revisões

- [ ] T117 [P] Revisão de segurança: nenhuma rota protegida sem dependency de autorização correta;
  nenhum dado sensível (senha, token) em logs ou respostas (Constitution X/XI)
- [ ] T118 [P] Revisão do Swagger/OpenAPI gerado (`/docs`): todo endpoint com `response_model`
  explícito e schemas sem `password_hash` (Constitution VII)
- [ ] T119 [P] Revisão das 4 migrações Alembic (`0001`-`0004`): `downgrade()` completo e reversível
  para cada uma, sem alteração manual de schema fora do fluxo de migração (Constitution VI)

**Checkpoint**: backend completo, testado e revisado — pronto para o frontend.

🎯 **Marco: Backend completo**

**Commit sugerido**: `test(backend): fecha cobertura de testes e revisão de segurança/OpenAPI/migrações`

---

## Phase 17: Frontend Foundation

**Purpose**: estrutura base do frontend — bloqueia todas as User Stories no frontend.

- [ ] T120 [P] Criar `frontend/src/services/httpClient.ts` (instância Axios única, interceptor de
  `Authorization: Bearer`, tratamento centralizado de erro incl. `ACCOUNT_DISABLED` → logout
  automático — `research.md` #15)
- [ ] T121 [P] Criar `frontend/src/contexts/AuthContext.tsx` (estado de sessão: usuário atual, token,
  login/logout, `is_system_admin`) (depende de T120)
- [ ] T122 [P] Criar `frontend/src/routes/index.tsx` (definição de rotas + guarda de rota
  protegida, incl. rota exclusiva de System Admin) e os layouts
  `frontend/src/layouts/AuthenticatedLayout.tsx`/`frontend/src/layouts/PublicLayout.tsx` (depende de
  T121)
- [ ] T123 [P] Criar `frontend/src/types/` espelhando os schemas de `contracts/` (`user.ts`,
  `workspace.ts`, `project.ts`, `task.ts`, `taskMember.ts`, `comment.ts`, `checklistItem.ts`,
  `attachment.ts`, `taskHistory.ts`, `notification.ts`, `dashboard.ts`, `apiError.ts`)
- [ ] T124 Criar `frontend/src/App.tsx` e `frontend/src/main.tsx` (composição do `AuthContext`,
  rotas e layout raiz) (depende de T122)

**Checkpoint**: estrutura de navegação e autenticação do frontend prontas.

**Commit sugerido**: `chore(frontend): estrutura base, autenticação e tipos do frontend`

---

## Phase 18: Frontend — User Story 1: Conta e Tarefas Pessoais (Priority: P1) 🎯 MVP

### Services & Hooks

- [ ] T125 [P] [US1] Criar `frontend/src/services/authService.ts` e
  `frontend/src/services/taskService.ts` (depende de T120, T123)
- [ ] T126 [P] [US1] Criar `frontend/src/hooks/useAuth.ts` e
  `frontend/src/hooks/usePersonalTasks.ts` (depende de T125, T121)

### Pages

- [ ] T127 [US1] Criar `frontend/src/pages/LoginPage.tsx` e `frontend/src/pages/RegisterPage.tsx`
  (validação de UX apenas — backend é a autoridade) (depende de T126)
- [ ] T128 [US1] Criar `frontend/src/pages/PersonalTasksPage.tsx` e componentes de formulário de
  tarefa em `frontend/src/components/forms/TaskForm.tsx` (depende de T126)

### Testes

- [ ] T129 [P] [US1] Testes de componente (Vitest + RTL) do formulário de login/cadastro e da lista
  de tarefas pessoais em `frontend/tests/LoginForm.test.tsx` e
  `frontend/tests/PersonalTasksPage.test.tsx` (depende de T127, T128)

---

## Phase 19: Frontend — User Story 2: Dashboard Inicial (Priority: P1) 🎯 MVP

- [ ] T130 [P] [US2] Criar `frontend/src/services/dashboardService.ts` (depende de T120, T123)
- [ ] T131 [P] [US2] Criar `frontend/src/hooks/useDashboard.ts` (depende de T130)
- [ ] T132 [US2] Criar `frontend/src/pages/DashboardPage.tsx` (contadores por status, destaque de
  atrasadas/vencendo hoje) (depende de T131)
- [ ] T133 [P] [US2] Teste de componente do dashboard (estado vazio, contagens) em
  `frontend/tests/DashboardPage.test.tsx` (depende de T132)

🎯 **Marco: Frontend MVP concluído** (US1 + US2 no frontend)

**Commit sugerido**: `feat(frontend): implementa autenticação, tarefas pessoais e dashboard (US1+US2)`

---

## Phase 20: Frontend — User Story 3: Workspaces, Membros e Roles (Priority: P2)

- [ ] T134 [P] [US3] Criar `frontend/src/services/workspaceService.ts` (depende de T120, T123)
- [ ] T135 [P] [US3] Criar `frontend/src/hooks/useWorkspaces.ts` e
  `frontend/src/hooks/useWorkspaceMembers.ts` (depende de T134)
- [ ] T136 [US3] Criar `frontend/src/pages/WorkspacesPage.tsx`,
  `frontend/src/pages/WorkspaceDetailPage.tsx` e `frontend/src/pages/WorkspaceMembersPage.tsx`
  (ações condicionadas à role do usuário: promover/rebaixar/remover/transferir titularidade)
  (depende de T135)
- [ ] T137 [P] [US3] Teste de componente da página de membros (visibilidade de ações por role) em
  `frontend/tests/WorkspaceMembersPage.test.tsx` (depende de T136)

**Commit sugerido**: `feat(frontend): implementa workspaces, membros e roles (US3)`

---

## Phase 21: Frontend — User Story 4: Projetos e Tarefas de Equipe (Priority: P2)

- [ ] T138 [P] [US4] Criar `frontend/src/services/projectService.ts`; estender
  `frontend/src/services/taskService.ts` para tarefas de workspace/projeto (depende de T134, T125)
- [ ] T139 [P] [US4] Criar `frontend/src/hooks/useProjects.ts`; estender
  `frontend/src/hooks/useTasks.ts` (depende de T138)
- [ ] T140 [US4] Criar `frontend/src/pages/ProjectsPage.tsx` e
  `frontend/src/pages/ProjectDetailPage.tsx` (criação de projeto restrita a Owner/Admin na UI,
  refletindo a autoridade do backend) (depende de T139)
- [ ] T141 [US4] Criar `frontend/src/pages/TaskDetailPage.tsx` e
  `frontend/src/pages/TaskFormPage.tsx` (criação/edição de tarefa de workspace/projeto) (depende de
  T139)

**Commit sugerido**: `feat(frontend): implementa projetos e tarefas de equipe (US4)`

---

## Phase 22: Frontend — User Story 5: Participantes de Tarefa (Priority: P2)

- [ ] T142 [P] [US5] Criar `frontend/src/services/taskMemberService.ts` (depende de T120, T123)
- [ ] T143 [P] [US5] Criar `frontend/src/hooks/useTaskMembers.ts` (depende de T142)
- [ ] T144 [US5] Adicionar seção de participantes em `frontend/src/pages/TaskDetailPage.tsx`
  (listar, adicionar, remover — ações visíveis apenas para criador/responsável/Owner/Admin) (depende
  de T143, T141)

**Commit sugerido**: `feat(frontend): implementa participantes de tarefa (US5)`

---

## Phase 23: Frontend — User Story 6: Comentários em Tarefas (Priority: P2)

- [ ] T145 [P] [US6] Criar `frontend/src/services/commentService.ts` (depende de T120, T123)
- [ ] T146 [P] [US6] Criar `frontend/src/hooks/useComments.ts` (depende de T145)
- [ ] T147 [US6] Adicionar seção de comentários em `frontend/src/pages/TaskDetailPage.tsx`
  (formulário de novo comentário desabilitado para quem não é participante, listagem visível a
  todos) (depende de T146, T141)

**Commit sugerido**: `feat(frontend): implementa comentários em tarefas (US6)`

---

## Phase 24: Frontend — User Story 7: Perfil do Usuário (Priority: P2)

- [ ] T148 [P] [US7] Estender `frontend/src/services/authService.ts` (ou criar `userService.ts`) com
  `getMe`/`updateMe` (depende de T120, T123)
- [ ] T149 [P] [US7] Criar `frontend/src/hooks/useProfile.ts` (depende de T148)
- [ ] T150 [US7] Criar `frontend/src/pages/ProfilePage.tsx` (visualizar/editar nome e e-mail,
  exibir status da conta) (depende de T149)
- [ ] T151 [P] [US7] Teste de componente do formulário de perfil em
  `frontend/tests/ProfilePage.test.tsx` (depende de T150)

**Commit sugerido**: `feat(frontend): implementa perfil do usuário (US7)`

---

## Phase 25: Frontend — User Story 8: Busca, Filtros e Ordenação de Tarefas (Priority: P2)

- [ ] T152 [US8] Estender `frontend/src/services/taskService.ts` e `frontend/src/hooks/useTasks.ts`
  com parâmetros de busca/filtro/ordenação (depende de T139)
- [ ] T153 [US8] Criar `frontend/src/pages/TasksListPage.tsx` (busca por título, filtros combináveis,
  ordenação) e componentes de filtro em `frontend/src/components/forms/TaskFilters.tsx` (depende de
  T152)
- [ ] T154 [P] [US8] Teste de componente dos filtros combinados (incl. resultado vazio) em
  `frontend/tests/TaskFilters.test.tsx` (depende de T153)

**Commit sugerido**: `feat(frontend): implementa busca, filtros e ordenação de tarefas (US8)`

---

## Phase 26: Frontend — User Story 9: Checklists em Tarefas (Priority: P3)

- [ ] T155 [P] [US9] Criar `frontend/src/services/checklistService.ts` (depende de T120, T123)
- [ ] T156 [P] [US9] Criar `frontend/src/hooks/useChecklist.ts` (depende de T155)
- [ ] T157 [US9] Adicionar seção de checklist em `frontend/src/pages/TaskDetailPage.tsx` (adicionar
  item, marcar concluído/pendente, remover — restrito a participantes) (depende de T156, T141)

**Commit sugerido**: `feat(frontend): implementa checklists em tarefas (US9)`

---

## Phase 27: Frontend — User Story 10: Anexos em Tarefas (Priority: P3)

- [ ] T158 [P] [US10] Criar `frontend/src/services/attachmentService.ts` (depende de T120, T123)
- [ ] T159 [P] [US10] Criar `frontend/src/hooks/useAttachments.ts` (depende de T158)
- [ ] T160 [US10] Adicionar seção de anexos em `frontend/src/pages/TaskDetailPage.tsx` (upload,
  listagem, download, remoção condicionada a uploader/Owner/Admin) (depende de T159, T141)

🎯 **Marco: Colaboração concluída (frontend)** (Comentários, Checklists e Anexos — US6/US9/US10)

**Commit sugerido**: `feat(frontend): implementa anexos em tarefas (US10)`

---

## Phase 28: Frontend — User Story 11: Notificações (Priority: P3)

- [ ] T161 [P] [US11] Criar `frontend/src/services/notificationService.ts` (depende de T120, T123)
- [ ] T162 [P] [US11] Criar `frontend/src/hooks/useNotifications.ts` (depende de T161)
- [ ] T163 [US11] Criar `frontend/src/pages/NotificationsPage.tsx` e indicador de não lidas em
  `frontend/src/components/layout/NotificationBadge.tsx` (depende de T162)

**Commit sugerido**: `feat(frontend): implementa notificações in-app (US11)`

---

## Phase 29: Frontend — User Story 12: Histórico de Alterações da Tarefa (Priority: P3)

- [ ] T164 [P] [US12] Criar `frontend/src/services/taskHistoryService.ts` (depende de T120, T123)
- [ ] T165 [P] [US12] Criar `frontend/src/hooks/useTaskHistory.ts` (depende de T164)
- [ ] T166 [US12] Adicionar seção de histórico (ordem cronológica) em
  `frontend/src/pages/TaskDetailPage.tsx` (depende de T165, T141)

**Commit sugerido**: `feat(frontend): implementa histórico de alterações da tarefa (US12)`

---

## Phase 30: Frontend — User Story 13: Administração de Usuários da Plataforma (System Admin) (Priority: P3)

- [ ] T167 [P] [US13] Criar `frontend/src/services/adminService.ts` (depende de T120, T123)
- [ ] T168 [P] [US13] Criar `frontend/src/hooks/useAdminUsers.ts` (depende de T167)
- [ ] T169 [US13] Criar `frontend/src/pages/AdminUsersPage.tsx` (listar usuários, ativar/desativar —
  rota protegida exclusiva de `is_system_admin`) (depende de T168, T122)
- [ ] T170 [P] [US13] Teste de rota protegida confirmando bloqueio de `AdminUsersPage` para usuários
  que não são System Admin em `frontend/tests/AdminUsersPage.test.tsx` (depende de T169)

**Checkpoint**: todas as 13 User Stories completas em backend e frontend.

🎯 **Marco: Frontend completo**

**Commit sugerido**: `feat(frontend): implementa administração de usuários da plataforma (US13)`

---

## Phase 31: Integração e Validação Final (cross-cutting)

**Purpose**: fechar a Fase 9 de `plan.md`.

- [ ] T171 Substituir quaisquer mocks de desenvolvimento por integração real frontend/backend em
  todas as páginas (revisão end-to-end)
- [ ] T172 [P] Revisar estados de erro/loading/vazio em todas as páginas listadas nas Fases 18–30
- [ ] T173 [P] Validar a matriz completa de permissões (criador, responsável, participante, Owner,
  Admin, Member, System Admin) ponta a ponta via UI

🎯 **Marco: Integração concluída**

- [ ] T174 Executar o roteiro de validação manual completo de `quickstart.md` (16 passos) e registrar
  o resultado
- [ ] T175 Atualizar o `README.md` da raiz do repositório com instruções de uso alinhadas a
  `quickstart.md`

**Checkpoint**: TaskFlow MVP completo, integrado e validado.

🎯 **Marco: TaskFlow MVP concluído**

**Commit sugerido**: `docs: atualiza README e finaliza validação do TaskFlow MVP`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Fase 2)**: depende da Fase 1 — bloqueia todas as User Stories (backend)
- **Backend User Stories (Fases 3–15)**: todas dependem da Fase 2; seguem a ordem de prioridade da
  spec (P1 → P2 → P3) e têm dependências pontuais entre si documentadas em cada task (ex.: US4
  depende de modelos criados na US1/US3; US11/US12 estendem o mesmo método de `TaskService.update`)
- **Backend Testing & Hardening (Fase 16)**: depende de todas as Fases 3–15
- **Frontend Foundation (Fase 17)**: depende da Fase 16 (backend completo e testado, conforme a
  ordem incremental de `plan.md`)
- **Frontend User Stories (Fases 18–30)**: cada uma depende da Fase 17 e da fase de **backend**
  correspondente à mesma story (ex.: Fase 18 depende da Fase 3)
- **Integração e Validação Final (Fase 31)**: depende de todas as fases anteriores

### User Story Dependencies (dentro do backend)

- **US1 (P1)**: sem dependência de outra story — MVP mínimo
- **US2 (P1)**: depende apenas de `Task` (US1); união com tarefas de workspace ativada na US3
- **US3 (P2)**: depende de US1 (usuário autenticado)
- **US4 (P2)**: depende de US3 (Workspace/WorkspaceMember)
- **US5 (P2)**: depende de US3 e US4 (Task de workspace)
- **US6 (P2)**: depende de US5 (autorização de participante)
- **US7 (P2)**: depende de US1 (User)
- **US8 (P2)**: depende de US4 (Task de workspace/projeto)
- **US9, US10 (P3)**: dependem de US5 (autorização de participante)
- **US11 (P3)**: depende de US6 (notificação de comentário) e estende `TaskService.update`
- **US12 (P3)**: depende de US11 (mesma transação de `TaskService.update`)
- **US13 (P3)**: depende apenas de US1 (User) — deliberadamente isolada de Workspace

### Parallel Opportunities

- Todas as tasks `[P]` de uma mesma fase podem rodar em paralelo (arquivos diferentes, sem
  dependência entre si)
- Dentro do backend, US9 e US10 são mutuamente independentes e podem ser feitas em paralelo por
  desenvolvedores diferentes após US5
- No frontend, Fases 26–30 (US9–US13) são mutuamente independentes entre si e podem ser paralelizadas
- Testes de uma mesma story marcados `[P]` sempre podem rodar em paralelo entre si

---

## Parallel Example: User Story 1 (Backend)

```bash
# Testes da US1 em paralelo:
Task: "Testes de integração de cadastro/login/rotas protegidas/conta desativada em backend/tests/integration/test_auth.py"
Task: "Testes de integração de CRUD de tarefas pessoais em backend/tests/integration/test_personal_tasks.py"
Task: "Testes unitários das invariantes de tarefa pessoal em backend/tests/unit/test_task_service.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 e 2 — ambas P1)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (bloqueia tudo) → 🎯 Marco: Fundação concluída
3. Completar Fase 3: US1 (backend) — validar independentemente
4. Completar Fase 4: US2 (backend) — validar independentemente → 🎯 Marco: Backend MVP concluído
5. **PARAR e VALIDAR**: cadastro/login + tarefas pessoais + dashboard funcionando de ponta a ponta
   via API (Swagger/`TestClient`), antes de prosseguir

### Entrega Incremental (conforme `plan.md`)

1. Setup + Foundational → base pronta
2. US1 → US2 → US3 → ... → US13, cada uma no backend, validada via testes de integração antes de
   avançar (Fases 3–15), com marcos intermediários (Backend MVP, Colaboração)
3. Fase 16 (Backend Testing & Hardening) → 🎯 Marco: Backend completo
4. Fase 17 (Frontend Foundation) → US1 → US2 → ... → US13 no frontend (Fases 18–30), cada uma
   consumindo a API já validada, com marcos intermediários (Frontend MVP, Frontend completo)
5. Fase 31 (Integração e Validação Final) → 🎯 Marco: TaskFlow MVP concluído

### Estratégia de Equipe Paralela

Com mais de um desenvolvedor, após a Fase 2 (Foundational): as User Stories do backend têm
dependências sequenciais reais entre si (US3→US4→US5→US6, etc. — ver "User Story Dependencies"
acima), então a paralelização mais segura é por **camada** dentro de uma mesma story já em
andamento (ex.: um desenvolvedor em `services/`, outro em `routes/` da mesma story) ou nas
User Stories P3 mutuamente independentes (US9/US10, e US9–US13 no frontend).

---

## Notes

- `[P]` = arquivos diferentes, sem dependência entre si
- `[Story]` mapeia a task à User Story correspondente para rastreabilidade
- Toda task de teste MUST ser escrita e falhar antes da implementação correspondente
  (Constitution VIII)
- Cada User Story deve ficar completa e testável de forma independente antes de avançar para a
  próxima
- Commitar após cada bloco ou fase (ver sugestões de commit acima), seguindo Conventional Commits
  (CLAUDE.md) — nunca automaticamente, sempre aguardando autorização
- Parar em qualquer marco/checkpoint para validar antes de avançar (ver "Fluxo recomendado de
  desenvolvimento")
- Evitar: tasks vagas, conflito de arquivo dentro da mesma fase, dependências entre stories que
  quebrem a independência de teste
