---

description: "Task list for Membros de Projeto (Visibilidade Restrita por Convite)"
---

# Tasks: Membros de Projeto (Visibilidade Restrita por Convite)

**Input**: Design documents from `/specs/003-membros-projeto/` (plan.md, spec.md, research.md,
data-model.md, contracts/, quickstart.md — todos presentes)

**Tests**: incluídos e **obrigatórios** (Constitution VIII exige cobertura de testes automatizados
para toda regra de negócio crítica) — mesma exigência já aplicada em `001-taskflow-mvp` e
`002-tarefas-fixas`.

**Fluxo de trabalho**: mesmo ritmo já estabelecido em `CLAUDE.md` — um bloco por vez, validar,
testar, sugerir commit (nunca automático), só então avançar. Backend primeiro (Fases 1-8), frontend
depois (Fases 9-13), validação final por último (Fase 14).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tasks incompletas)
- **[Story]**: US1-US5, mapeadas 1:1 às User Stories de `spec.md`
- Caminhos de arquivo exatos em cada descrição

## Path Conventions (de `plan.md`)

- Backend: `backend/app/{models,schemas,repositories,services,routes,dependencies}/`
- Backend tests: `backend/tests/{unit,integration}/`
- Frontend: `frontend/src/{pages,services,hooks,types}/`
- Frontend tests: `frontend/tests/`
- Migração: `backend/alembic/versions/`

---

## Phase 1: Setup

- [x] T001 [P] Criar model `ProjectMember` em `backend/app/models/project_member.py` (`id`,
  `project_id` FK `projects.id` `ON DELETE CASCADE`, `user_id` FK `users.id` `ON DELETE CASCADE`,
  `created_at`, `UniqueConstraint(project_id, user_id)`, `Index(user_id)` — data-model.md, sem
  coluna `role`)

**Commit sugerido**: `chore(backend): adiciona model ProjectMember`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema, acesso a dados e migração completos — bloqueia todas as User Stories.

**⚠️ CRITICAL**: nenhuma User Story pode começar antes desta fase estar completa.

- [x] T002 [P] Criar `backend/app/schemas/project_member.py` (`ProjectMemberCreate`: `user_id`;
  `ProjectMemberRead`: `user_id`, `name`, `email`, `joined_at` — mesmo padrão de
  `WorkspaceMemberRead`, sem `role`) (depende de T001)
- [x] T003 [P] Criar `backend/app/repositories/project_member_repository.py` (`create`,
  `list_by_project` — join com `User` para `name`/`email`, mesmo padrão de
  `WorkspaceMemberRepository.list_by_workspace`, `get_by_project_and_user`, `is_member`,
  `list_project_ids_for_user`, `delete`) (depende de T001)
- [x] T004 [P] Estender `backend/app/repositories/workspace_member_repository.py` com
  `list_owned_workspace_ids_for_user` (variante de `list_workspace_ids_for_user` filtrada por
  `role == OWNER` — research.md #2)
- [x] T005 Gerar migração Alembic `0006_project_members` em `backend/alembic/versions/`: cria a
  tabela `project_members` (FKs, `UniqueConstraint`, `Index` — data-model.md) e, na mesma migração,
  faz o backfill via `op.execute("INSERT INTO project_members (...) SELECT ... FROM projects p JOIN
  workspace_members wm ON wm.workspace_id = p.workspace_id")` (FR-012, research.md #4) (depende de
  T001)
- [x] T006 [P] Estender `backend/tests/conftest.py` com factory `make_project_member` (depende de
  T005)

**Checkpoint**: schema e infraestrutura de dados prontos — User Stories podem começar.

**Commit sugerido**: `chore(backend): schema e infraestrutura de Membros de Projeto`

---

## Phase 3: Backend — User Story 1: Adicionar e Remover Membros de um Projeto (Priority: P1) 🎯 MVP

**Goal**: Owner/Admin conseguem adicionar e remover pessoas da lista de membros de um projeto;
criador de um projeto novo já entra como seu primeiro membro.

**Independent Test**: como Owner/Admin, adicionar um membro do workspace a um projeto e depois
removê-lo, confirmando que a lista reflete a mudança; confirmar que um Member comum recebe `403` ao
tentar.

### Testes

- [x] T007 [P] [US1] Testes de integração: adicionar membro (sucesso, `403` para Member, `400` para
  usuário que não é membro do workspace, `409` para duplicado), remover membro (sucesso), listar
  membros — em `backend/tests/integration/test_project_members.py` (novo)
- [x] T008 [P] [US1] Teste de integração: criar projeto → criador vira `ProjectMember`
  automaticamente — em `backend/tests/integration/test_projects.py` (já existente, estendido)

### Implementação

- [x] T009 [US1] Criar `backend/app/dependencies/project_authorization.py` com
  `require_project_visible` (fórmula de acesso completa desde já — Owner do workspace OU membro
  explícito do projeto, `404` para quem não tem acesso — data-model.md) e `require_project_manage`
  (adiciona a exigência de role `OWNER`/`ADMIN` no workspace — research.md #5) (depende de T003)
- [x] T010 [US1] Criar `backend/app/services/project_member_service.py`: `list_members`,
  `add_member` (valida que `user_id` já é membro do workspace do projeto — FR-002 — senão `400`;
  `409` se já é membro do projeto), `remove_member` (versão inicial, sem checagem de tarefas ativas
  — endurecida na US5) (depende de T003, T004)
- [x] T011 [US1] Estender `ProjectService.create` (`backend/app/services/project_service.py`) para
  receber `creator_id: uuid.UUID` e criar o `ProjectMember` do criador na mesma transação (FR-003,
  research.md #3.6 — mesmo padrão de `WorkspaceService.create` com o `WorkspaceMember(OWNER)`)
  (depende de T003)
- [x] T012 [US1] Criar `backend/app/routes/project_members.py` (`GET/POST
  /api/v1/projects/{project_id}/members`, `DELETE .../members/{user_id}`) e registrar o router em
  `backend/app/main.py`; estender `create_project` em `backend/app/routes/projects.py` para receber
  `current_user: User = Depends(get_current_user)` e repassar `current_user.id` (depende de T009,
  T010, T011)

**Checkpoint**: US1 completa e testável de forma independente — gestão de membros funcionando ponta
a ponta via API.

**Commit sugerido**: `feat(backend): implementa gestao de membros de projeto (US1)`

---

## Phase 4: Backend — User Story 2: Projeto Só é Visível para Quem Foi Convidado (Priority: P1) 🎯 MVP

**Goal**: um Member comum só vê/acessa (listagem, projeto isolado, tarefas do projeto) os projetos
dos quais é membro explícito.

**Independent Test**: como Member membro do Projeto A mas não do Projeto B (mesmo workspace),
confirmar que a listagem mostra só A, que abrir B diretamente retorna `404`, e que as tarefas de B
não aparecem em nenhuma consulta de tarefas.

### Testes

- [x] T013 [P] [US2] Testes de integração: Member vê só os projetos dos quais é membro na listagem;
  Member recebe `404` ao tentar abrir (`GET`/`PATCH`/`DELETE`) um projeto do qual não é membro — em
  `backend/tests/integration/test_projects.py`
- [x] T014 [P] [US2] Testes de integração: tarefas de um projeto restrito não aparecem para um
  Member sem acesso em `GET /tasks?project_id=` nem em `GET /tasks/{id}` (mas aparecem normalmente
  para quem tem acesso) — em `backend/tests/integration/test_tasks.py`

### Implementação

- [x] T015 [US2] Estender `ProjectService.list_by_workspace` (ramifica por role: `OWNER`/`ADMIN` →
  todos os projetos; `MEMBER` → filtrado por `ProjectMemberRepository.list_project_ids_for_user`) e
  `get_by_id_or_404` (aplica a fórmula de acesso completa — data-model.md) em
  `backend/app/services/project_service.py` (depende de T003, T004, T009)
- [x] T016 [US2] Adicionar `is_member: bool` a `ProjectRead` (`backend/app/schemas/project.py`),
  calculado explicitamente pelo Service — mesmo padrão de `WorkspaceRead.my_role`, nunca via
  `from_attributes` direto (depende de T015)
- [x] T017 [US2] Estender `TaskRepository.search`/`count_by_status`
  (`backend/app/repositories/task_repository.py`) com a nova cláusula `visible` (data-model.md),
  recebendo `owner_workspace_ids`/`member_project_ids` como parâmetros novos; estender
  `TaskService.search` (`task_service.py`) **e** `DashboardService.get_summary`
  (`dashboard_service.py` — chama `count_by_status` independentemente de `TaskService`, precisa da
  mesma correção) para calcular os dois conjuntos e repassá-los (depende de T003, T004)
- [x] T018 [US2] Estender `require_task_visible` em `backend/app/dependencies/task_authorization.py`
  para aplicar a mesma fórmula de acesso quando `task.project_id is not None` (depende de T003, T004)

**Checkpoint**: US1 e US2 funcionam de forma independente — Member já não vê projetos/tarefas fora
do seu acesso, em nenhum endpoint.

**Commit sugerido**: `feat(backend): restringe visibilidade de projetos e tarefas a membros (US2)`

---

## Phase 5: Backend — User Story 3: Visibilidade Ampliada para Owner e Admin (Priority: P2)

**Goal**: Owner continua acessando tudo automaticamente; Admin vê a listagem completa mas só abre o
conteúdo dos projetos dos quais participa.

**Independent Test**: como Owner, acessar um projeto do qual nunca foi adicionado explicitamente
como membro; como Admin, confirmar que um projeto do qual não participa aparece na listagem
(`is_member: false`) mas retorna `404` ao tentar abrir.

### Testes

- [x] T019 [P] [US3] Testes de integração: Owner acessa qualquer projeto/tarefa mesmo sem
  `ProjectMember` explícito; Admin vê todos os projetos na listagem com `is_member` correto (`true`/
  `false`) mas recebe `404` ao abrir um do qual não é membro — em
  `backend/tests/integration/test_projects.py`

> Nenhuma implementação nova nesta fase — a fórmula de acesso (data-model.md) já cobre Owner/Admin
> desde a US2 (T015-T018 já a implementam por completo); esta fase só adiciona testes dedicados,
> mesmo padrão já usado em `002-tarefas-fixas` (US2/US3 do cálculo de ocorrência, escrito de uma vez
> e testado incrementalmente).

**Checkpoint**: US1, US2 e US3 funcionam de forma independente.

**Commit sugerido**: `test(backend): valida visibilidade ampliada de Owner e Admin (US3)`

---

## Phase 6: Backend — User Story 4: Atribuição de Tarefas Restrita a Membros do Projeto (Priority: P2)

**Goal**: só uma pessoa que é membro de um projeto pode ser responsável por uma tarefa desse
projeto.

**Independent Test**: tentar atribuir (na criação ou reatribuição) uma tarefa de um projeto a
alguém que é membro do workspace mas não do projeto e confirmar que o sistema recusa.

### Testes

- [x] T020 [P] [US4] Testes de integração: criar tarefa de projeto com `assignee_id` que não é
  membro do projeto → `400 BUSINESS_RULE_VIOLATION`; reatribuir uma tarefa existente para alguém
  fora do projeto → mesmo erro; atribuir/reatribuir para um membro do projeto → sucesso — em
  `backend/tests/integration/test_tasks.py`

### Implementação

- [x] T021 [US4] Criar `TaskService._require_project_member` em
  `backend/app/services/task_service.py` e usá-lo em `_resolve_workspace_assignee` (criação) e na
  validação inline de reatribuição em `update`, sempre que a tarefa tiver `project_id` (FR-009)
  (depende de T003)

**Checkpoint**: as 4 primeiras User Stories funcionam de forma independente.

**Commit sugerido**: `feat(backend): restringe atribuicao de tarefa a membros do projeto (US4)`

---

## Phase 7: Backend — User Story 5: Remoção Bloqueada por Tarefas Ativas (Priority: P3)

**Goal**: remover alguém de um projeto é recusado enquanto essa pessoa tiver tarefas ativas
atribuídas a ela dentro desse projeto.

**Independent Test**: com uma tarefa não concluída atribuída a um membro dentro de um projeto,
tentar removê-lo e confirmar a recusa; reatribuir/concluir a tarefa e confirmar que a remoção passa
a funcionar.

### Testes

- [x] T022 [P] [US5] Teste de integração: remover um membro com tarefa ativa no projeto → `409` com
  `details` (lista de `{task_id, title}`); reatribuir ou concluir a tarefa e repetir a remoção →
  sucesso — em `backend/tests/integration/test_project_members.py`

### Implementação

- [x] T023 [US5] Criar `TaskRepository.list_active_by_assignee_in_project` em
  `backend/app/repositories/task_repository.py` (mesmo padrão de
  `list_active_by_assignee_in_workspace`)
- [x] T024 [US5] Estender `ProjectMemberService.remove_member` (`project_member_service.py`) com o
  bloqueio de tarefas ativas (FR-010, mesmo padrão de `WorkspaceMemberService.remove_member`)
  (depende de T023)

**Checkpoint**: as 5 User Stories completas no backend.

🎯 **Marco: Backend de Membros de Projeto concluído**

**Commit sugerido**: `feat(backend): bloqueia remocao de membro de projeto com tarefas ativas (US5)`

---

## Phase 8: Backend — Migração de Dados e Regressão do Dashboard (cross-cutting)

**Purpose**: fecha FR-012 (migração de projetos existentes) e confirma que o Dashboard permanece
correto com a nova cláusula de visibilidade.

- [x] T025 [P] Teste de integração dedicado aplicando a migração `0006` sobre um banco com
  projetos/membros pré-existentes e confirmando que todo `WorkspaceMember` vira `ProjectMember` de
  todo projeto do seu workspace (FR-012, Roteiro 6 do `quickstart.md`) — em
  `backend/tests/integration/test_project_members.py`
- [x] T026 [P] Teste de integração confirmando que `GET /api/v1/dashboard` não conta tarefas de
  projetos restritos aos quais o usuário não tem acesso (regressão sobre a cláusula `visible`
  compartilhada, T017) — em `backend/tests/integration/test_dashboard.py`

**Checkpoint**: backend completo, testado e migrado — pronto para o frontend.

**Commit sugerido**: `test(backend): valida migracao de dados e regressao do Dashboard`

---

## Phase 9: Frontend Foundation

**Purpose**: estrutura base — bloqueia todas as User Stories no frontend.

- [x] T027 [P] Criar `frontend/src/types/projectMember.ts` (`ProjectMember`, `ProjectMemberCreate` —
  espelhando `contracts/project-members.md`) e estender `frontend/src/types/project.ts` com
  `is_member: boolean` em `Project`
- [x] T028 [P] Criar `frontend/src/services/projectMemberService.ts` (`list`, `add`, `remove`)
  (depende de T027)
- [x] T029 [P] Criar `frontend/src/hooks/useProjectMembers.ts` (mesmo padrão de
  `useWorkspaceMembers`) (depende de T028)

**Checkpoint**: estrutura de dados do frontend pronta.

**Commit sugerido**: `chore(frontend): estrutura base de Membros de Projeto`

---

## Phase 10: Frontend — User Story 1: Gerenciar Membros de um Projeto (Priority: P1) 🎯 MVP

- [x] T030 [US1] Adicionar botão "Membros" no herói de `frontend/src/pages/ProjectDetailPage.tsx`
  (visível só quando `canManage` — mesma condição já usada por Editar/Excluir), abrindo um `Sheet`
  com lista de membros (avatar + nome + e-mail), adicionar por e-mail (mesmo padrão de
  `AddMemberByEmailForm`) e remover (`AlertDialog`, mesmo padrão de `RemoveMemberDialog` de
  `WorkspaceMembersPage.tsx`, incl. erro genérico via `getApiErrorMessage`) (depende de T029)
- [x] T031 [P] [US1] Teste de componente cobrindo listar/adicionar/remover membro no Sheet, em
  `frontend/tests/ProjectDetailPage.test.tsx` (depende de T030)

**Checkpoint**: US1 completa no frontend.

🎯 **Marco: MVP de Membros de Projeto concluído** (US1 backend + frontend)

**Commit sugerido**: `feat(frontend): implementa gestao de membros de projeto (US1)`

---

## Phase 11: Frontend — User Story 2/3: Visibilidade Restrita e Ampliada (Priority: P1/P2)

- [x] T032 [US2] Estender `frontend/src/pages/ProjectsPage.tsx`: um cartão com `is_member: false`
  (só ocorre para Admin, FR-006) renderiza bloqueado — ícone de cadeado, cartão esmaecido, sem
  navegação ao clicar (research.md #6) (depende de T027)
- [x] T033 [P] [US2] Teste de componente cobrindo o cartão bloqueado (`is_member: false`) vs. normal
  (`is_member: true`) em `frontend/tests/ProjectsPage.test.tsx` (depende de T032)

**Checkpoint**: US1, US2 e US3 completas no frontend.

**Commit sugerido**: `feat(frontend): sinaliza projetos sem acesso na listagem (US2/US3)`

---

## Phase 12: Frontend — User Story 4: Atribuição de Tarefas Restrita a Membros do Projeto (Priority: P2)

- [x] T034 [US4] Estender `frontend/src/pages/TaskFormPage.tsx`: quando há um projeto selecionado, o
  `<Select>` de responsável passa a usar `useProjectMembers(projectId)` em vez de
  `useWorkspaceMembers(workspaceId)` (research.md #7) (depende de T029)
- [x] T035 [P] [US4] Teste de componente cobrindo o seletor de responsável restrito a membros do
  projeto em `frontend/tests/TaskFormPage.test.tsx` (depende de T034)

**Checkpoint**: as 4 primeiras User Stories completas em backend e frontend.

**Commit sugerido**: `feat(frontend): restringe seletor de responsavel a membros do projeto (US4)`

---

## Phase 13: Frontend — User Story 5: Remoção Bloqueada por Tarefas Ativas (Priority: P3)

- [x] T036 [US5] Estender o diálogo de remoção do Sheet de membros de `ProjectDetailPage.tsx` para
  exibir a lista de tarefas pendentes retornada pelo backend (`409`, `details`) — mesmo padrão de
  `RemoveMemberDialog` em `WorkspaceMembersPage.tsx` (depende de T030)
- [x] T037 [P] [US5] Teste de componente cobrindo o bloqueio de remoção com tarefas ativas em
  `frontend/tests/ProjectDetailPage.test.tsx` (depende de T036)

**Checkpoint**: as 5 User Stories completas em backend e frontend.

🎯 **Marco: Membros de Projeto concluída**

**Commit sugerido**: `feat(frontend): exibe tarefas pendentes ao bloquear remocao de membro (US5)`

---

## Phase 14: Validação Final (cross-cutting)

- [x] T038 Executar o roteiro completo de `quickstart.md` (6 roteiros) e registrar o resultado —
  os 6 roteiros são cobertos integralmente pela suíte automatizada (não repetidos manualmente à
  parte): Roteiro 1 (gestão de membros) → `test_project_members.py`; Roteiro 2 (visibilidade
  restrita) → `test_projects.py`/`test_tasks.py` (US2); Roteiro 3 (Owner/Admin ampliada) →
  `test_projects.py` (US3); Roteiro 4 (atribuição restrita) → `test_workspace_tasks.py`/
  `test_task_changed_notifications.py`; Roteiro 5 (remoção bloqueada) → `test_project_members.py`
  (US5); Roteiro 6 (migração) → `test_project_members.py::test_migration_backfill_...` +
  verificação manual contra o banco de desenvolvimento (9 projetos → 14 `project_members`
  criados). Suíte completa do backend: **686/686 passed** (660 anteriores + 26 novos/ajustados).
  Suíte completa do frontend: **80/80 passed** (76 anteriores + 4 novos). `tsc -b --noEmit` e
  `npm run build` sem erros. Migração `0006_project_members` aplicada com sucesso no banco de
  desenvolvimento local (`alembic upgrade head`)
- [x] T039 Avaliar se `README.md` precisa mencionar Membros de Projeto (Constitution — seção 16 do
  `CLAUDE.md`) — **não necessário agora**, mesma justificativa de `002-tarefas-fixas/tasks.md`
  (T039): o `README.md` da raiz ainda está no estado genérico/aspiracional de antes do Spec Kit,
  sem refletir nenhuma das features já implementadas — atualizá-lo é T175 de
  `001-taskflow-mvp/tasks.md`, ainda pendente e fora do escopo desta feature

**Checkpoint**: feature completa, integrada e validada.

🎯 **Marco: Membros de Projeto concluída e validada**

**Commit sugerido**: `docs: finaliza validacao de Membros de Projeto`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências.
- **Foundational (Fase 2)**: depende da Fase 1 — bloqueia todas as User Stories.
- **Backend User Stories (Fases 3-7)**: todas dependem da Fase 2. US1 é a base (a
  `ProjectMemberService`/rotas/dependencies nascem nela); US2/US3 estendem `ProjectService` e a
  cláusula `visible` de `TaskRepository` (não dependem de US1 ter sido testada, só do schema da
  Fase 2); US4 depende só da Fase 2 (assignee); US5 estende o `remove_member` já criado em US1.
- **Migração/Dashboard (Fase 8)**: depende das Fases 3-7 (a cláusula `visible` já precisa existir —
  T017/T018 — para os testes de regressão do Dashboard).
- **Frontend Foundation (Fase 9)**: depende da Fase 8 (backend completo e testado).
- **Frontend User Stories (Fases 10-13)**: cada uma depende da Fase 9 e da fase de backend
  correspondente à mesma story.
- **Validação Final (Fase 14)**: depende de todas as fases anteriores.

### User Story Dependencies

- **US1 (P1)**: depende só da Fase 2 (Foundational) — MVP mínimo de gestão.
- **US2 (P1)**: depende só da Fase 2 — pode ser implementada em paralelo a US1 (arquivos
  praticamente disjuntos: US1 mexe em rotas/service de membros, US2 em `ProjectService`/
  `TaskRepository`/`task_authorization.py`).
- **US3 (P2)**: depende de US2 (reaproveita a mesma implementação, só adiciona testes).
- **US4 (P2)**: depende só da Fase 2 — independente de US1/US2/US3.
- **US5 (P3)**: depende de US1 (estende o `remove_member` criado nela).

### Parallel Opportunities

- Todas as tasks `[P]` de uma mesma fase podem rodar em paralelo (arquivos diferentes, sem
  dependência entre si).
- US1 e US2 são mutuamente independentes (ambas só dependem da Fase 2) — podem ser feitas em
  paralelo por desenvolvedores diferentes; US4 também é independente das duas.
- Testes de uma mesma story marcados `[P]` sempre podem rodar em paralelo entre si.

---

## Parallel Example: Foundational (Fase 2)

```bash
Task: "Criar schemas em backend/app/schemas/project_member.py"
Task: "Criar repository em backend/app/repositories/project_member_repository.py"
Task: "Estender workspace_member_repository.py com list_owned_workspace_ids_for_user"
```

---

## Implementation Strategy

### MVP First (User Stories 1 e 2 apenas)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (bloqueia tudo)
3. Completar Fase 3: US1 backend (gestão de membros) — validar independentemente (quickstart.md,
   Roteiro 1)
4. Completar Fase 4: US2 backend (visibilidade restrita) — validar independentemente (Roteiro 2)
5. Completar Fases 9-11: US1/US2 frontend
6. **PARAR e VALIDAR**: gestão de membros + restrição de visibilidade funcionando ponta a ponta
   antes de prosseguir

### Entrega Incremental

1. Setup + Foundational → base pronta
2. US1 + US2 (backend + frontend) → 🎯 MVP de Membros de Projeto
3. US3 → US4 → US5, cada uma validada antes de avançar (US3/US4 podem ser paralelizadas entre si)
4. Fase 14 → validação final

---

## Notes

- `[P]` = arquivos diferentes, sem dependência entre si
- `[Story]` mapeia a task à User Story correspondente para rastreabilidade
- Toda task de teste MUST ser escrita e falhar antes da implementação correspondente
  (Constitution VIII)
- Commitar após cada bloco ou fase (ver sugestões de commit acima), seguindo Conventional Commits
  (CLAUDE.md) — nunca automaticamente, sempre aguardando autorização
- Parar em qualquer marco/checkpoint para validar antes de avançar
- Atenção especial à Fase 4 (T017/T018): são os pontos onde a restrição pode ser contornada se
  esquecidos (research.md #3) — não pular para a Fase 5 sem confirmar os testes de T014 passando
