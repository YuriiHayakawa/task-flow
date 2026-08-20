---

description: "Task list for Tarefas Fixas (Rotinas Pessoais Recorrentes)"
---

# Tasks: Tarefas Fixas (Rotinas Pessoais Recorrentes)

**Input**: Design documents from `/specs/002-tarefas-fixas/` (plan.md, spec.md, research.md,
data-model.md, contracts/, quickstart.md — todos presentes)

**Tests**: incluídos e **obrigatórios** (Constitution VIII exige cobertura de testes automatizados
para toda regra de negócio crítica) — mesma exigência já aplicada em `001-taskflow-mvp`.

**Fluxo de trabalho**: mesmo ritmo já estabelecido em `CLAUDE.md`/`001-taskflow-mvp/tasks.md` — um
bloco por vez, validar, testar, sugerir commit (nunca automático), só então avançar. Backend
primeiro (Fases 1-7), frontend depois (Fases 8-12), validação final por último (Fase 13) — mesma
ordem incremental de `plan.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tasks incompletas)
- **[Story]**: US1-US4, mapeadas 1:1 às User Stories de `spec.md`
- Caminhos de arquivo exatos em cada descrição

## Path Conventions (de `plan.md`)

- Backend: `backend/app/{models,schemas,repositories,services,routes,enums,dependencies}/`
- Backend tests: `backend/tests/{unit,integration}/`
- Frontend: `frontend/src/{pages,services,hooks,components/layout,routes}/`
- Frontend tests: `frontend/tests/`
- Migração: `backend/alembic/versions/`

---

## Phase 1: Setup

- [x] T001 [P] Criar enum `RecurrenceType` (`DAILY`, `WEEKLY`, `MONTHLY`) em
  `backend/app/enums/recurrence_type.py` (data-model.md)

**Commit sugerido**: `chore(backend): adiciona enum RecurrenceType`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema completo e infraestrutura central — bloqueia todas as User Stories.

**⚠️ CRITICAL**: nenhuma User Story pode começar antes desta fase estar completa — a migração
agrupa as 3 tabelas juntas (data-model.md), então até a US1 (só diária) depende do schema inteiro
já existir.

- [x] T002 [P] Criar model `RecurringTask` em `backend/app/models/recurring_task.py` (`id`,
  `owner_id` FK `users.id` `ON DELETE RESTRICT`, `title`, `recurrence_type`, `month_day` nullable,
  timestamps) (depende de T001)
- [x] T003 [P] Criar model `RecurringTaskWeekday` em
  `backend/app/models/recurring_task_weekday.py` (`recurring_task_id` FK `ON DELETE CASCADE`,
  `weekday` 0-6, `UNIQUE(recurring_task_id, weekday)`) (depende de T002)
- [x] T004 [P] Criar model `RecurringTaskCompletion` em
  `backend/app/models/recurring_task_completion.py` (`recurring_task_id` FK `ON DELETE CASCADE`,
  `occurrence_date`, `completed_at`, `UNIQUE(recurring_task_id, occurrence_date)`) (depende de T002)
- [x] T005 Gerar migração Alembic `000X_recurring_tasks` em `backend/alembic/versions/` criando as
  3 tabelas acima, `CHECK`s (`title` não vazio, `month_day BETWEEN 1 AND 31` quando não nulo,
  `weekday BETWEEN 0 AND 6`) e os índices únicos compostos (data-model.md) (depende de T002-T004)
- [x] T006 [P] Criar `backend/app/schemas/recurring_task.py` (`RecurringTaskCreate`,
  `RecurringTaskUpdate` — campos opcionais, `RecurringTaskRead` incl. `weekdays: list[int]`,
  `month_day: int | None`, `is_due_today: bool`, `completed_today: bool`) (depende de T001)
- [x] T007 [P] Criar `backend/app/repositories/recurring_task_repository.py` (`create`,
  `get_by_id`, `list_by_owner`, `update`, `delete`, `set_weekdays`, `create_completion`,
  `delete_completion`, `get_completion`) (depende de T002-T004)
- [x] T008 Estender `backend/app/dependencies/task_authorization.py` com
  `require_recurring_task_owner` (carrega a `RecurringTask` pelo `id` do path; `404` se não existir
  ou se `owner_id != current_user.id` — research.md #6) (depende de T007)
- [x] T009 [P] Estender `backend/tests/conftest.py` com factory de `RecurringTask` para os testes
  desta feature (depende de T005)

**Checkpoint**: schema e infraestrutura prontos — User Stories podem começar.

**Commit sugerido**: `chore(backend): schema e infraestrutura de Tarefas Fixas`

---

## Phase 3: Backend — User Story 1: Tarefa Fixa Diária (Priority: P1) 🎯 MVP

**Goal**: criar, listar, concluir e desconcluir a ocorrência de hoje de uma tarefa fixa diária, com
reset automático no dia seguinte.

**Independent Test**: cadastrar uma tarefa fixa diária, marcar concluída hoje, confirmar (com a
data controlada no teste) que ela volta pendente no dia seguinte, sem nenhuma ação manual.

### Testes

- [x] T010 [P] [US1] Testes de integração de criar/listar/concluir/desconcluir tarefa fixa diária,
  incl. idempotência de concluir duas vezes no mesmo dia, em
  `backend/tests/integration/test_recurring_tasks.py`
- [x] T011 [P] [US1] Testes unitários do cálculo de ocorrência para `DAILY` (sempre ocorrência,
  qualquer data) em `backend/tests/unit/test_recurring_task_service.py`

### Implementação

- [x] T012 [US1] Criar `backend/app/services/recurring_task_service.py`: `create`,
  `list_for_owner` (retorna `is_due_today`/`completed_today` calculados via `_is_occurrence`),
  `complete_today`, `uncomplete_today` — `_is_occurrence` já escrita para os 3 tipos de recorrência
  de uma vez (é uma função só, data-model.md "Cálculo de ocorrência"), mas testada nesta fase
  apenas para `DAILY` (depende de T007, T008)
- [x] T013 [US1] Criar `backend/app/routes/recurring_tasks.py` (`POST/GET
  /api/v1/recurring-tasks`, `POST/DELETE /api/v1/recurring-tasks/{id}/completions`) e registrar o
  router em `backend/app/main.py` (depende de T012)

**Checkpoint**: US1 completa e testável de forma independente — tarefa fixa diária funcionando
ponta a ponta via API.

**Commit sugerido**: `feat(backend): implementa tarefas fixas diárias (US1)`

---

## Phase 4: Backend — User Story 2: Tarefa Fixa Semanal em Dias Específicos (Priority: P2)

**Goal**: recorrência semanal com um ou mais dias da semana escolhidos; ocorrência só nos dias
selecionados.

**Independent Test**: cadastrar uma tarefa fixa semanal (ex.: segunda/quarta/sexta) e confirmar que
ela só tem um estado de conclusão ativo nesses dias.

### Testes

- [x] T014 [P] [US2] Testes de integração: criar semanal com dias válidos; rejeitar sem nenhum dia
  selecionado; ocorrência (`is_due_today`) só verdadeira nos dias certos; concluir num dia que não
  é ocorrência retorna `400 BUSINESS_RULE_VIOLATION` — em `test_recurring_tasks.py`
- [x] T015 [P] [US2] Testes unitários do cálculo de ocorrência para `WEEKLY` em
  `test_recurring_task_service.py`

### Implementação

- [x] T016 [US2] Estender `RecurringTaskService.create`/`update` com validação de `weekdays`
  (rejeita `WEEKLY` sem nenhum dia) e gestão de `RecurringTaskWeekday` via
  `RecurringTaskRepository.set_weekdays` (depende de T012)

**Checkpoint**: US1 e US2 funcionam de forma independente.

**Commit sugerido**: `feat(backend): implementa tarefas fixas semanais (US2)`

---

## Phase 5: Backend — User Story 3: Tarefa Fixa Mensal (Priority: P3)

**Goal**: recorrência mensal num dia específico, incl. a regra de mês mais curto que o dia
configurado.

**Independent Test**: cadastrar uma tarefa fixa mensal no dia 31 e confirmar que, num mês com menos
de 31 dias, a ocorrência cai no último dia desse mês.

### Testes

- [x] T017 [P] [US3] Testes de integração: criar mensal com dia válido; rejeitar sem `month_day`/
  com `month_day` fora de 1-31; ocorrência no dia configurado — em `test_recurring_tasks.py`
- [x] T018 [P] [US3] Testes unitários do cálculo de ocorrência para `MONTHLY`, incl. dia 31 em mês
  de 30 dias e dia 29/30/31 em fevereiro (bissexto e não bissexto), usando
  `calendar.monthrange` — em `test_recurring_task_service.py`

### Implementação

- [x] T019 [US3] Estender `RecurringTaskService.create`/`update` com validação de `month_day`
  (1-31) e a regra de último dia do mês em `_is_occurrence` (research.md #3) (depende de T012)

**Checkpoint**: US1, US2 e US3 funcionam de forma independente.

**Commit sugerido**: `feat(backend): implementa tarefas fixas mensais (US3)`

---

## Phase 6: Backend — User Story 4: Editar e Excluir uma Tarefa Fixa (Priority: P2)

**Goal**: editar título/recorrência sem afetar conclusões passadas; excluir removendo conclusões e
dias associados.

**Independent Test**: criar uma tarefa fixa, concluir uma ocorrência, editar o título, confirmar
que a conclusão anterior permanece; excluir e confirmar que nada órfão sobra no banco.

### Testes

- [x] T020 [P] [US4] Testes de integração: editar título/recorrência (incl. trocar de tipo, ex.
  `WEEKLY` → `DAILY` limpando os dias antigos) sem alterar conclusões passadas; excluir remove a
  tarefa e toda conclusão/dia associado; usuário não-dono recebe `404` em todas as rotas — em
  `test_recurring_tasks.py`

### Implementação

- [x] T021 [US4] Implementar `RecurringTaskService.update` (título e/ou recorrência — trocar o tipo
  substitui os campos específicos do tipo anterior) e `delete` (depende de T012, T016, T019)
- [x] T022 [US4] Criar rotas `PATCH`/`DELETE /api/v1/recurring-tasks/{id}` em
  `recurring_tasks.py`, usando `require_recurring_task_owner` (depende de T021, T008)

**Checkpoint**: as 4 User Stories funcionam de forma independente no backend.

**Commit sugerido**: `feat(backend): implementa edição e exclusão de tarefas fixas (US4)`

---

## Phase 7: Backend — Isolamento e Dashboard (cross-cutting)

**Purpose**: fecha FR-011 (isolamento por dono) e FR-013 (Dashboard inalterado) com testes
dedicados, cobrindo todas as rotas de uma vez.

- [x] T023 [P] Teste de integração dedicado confirmando `404` (nunca `403`) para um usuário que não
  é dono, em cada uma das 5 rotas de `/recurring-tasks`, em `test_recurring_tasks.py`
- [x] T024 [P] Teste de integração confirmando que `GET /api/v1/dashboard` retorna as mesmas
  contagens antes e depois de criar/concluir Tarefas Fixas, em
  `backend/tests/integration/test_dashboard.py`

**Checkpoint**: backend completo e testado — pronto para o frontend.

🎯 **Marco: Backend de Tarefas Fixas concluído**

**Commit sugerido**: `test(backend): fecha cobertura de isolamento e Dashboard das tarefas fixas`

---

## Phase 8: Frontend Foundation

**Purpose**: estrutura base — bloqueia todas as User Stories no frontend.

- [x] T025 [P] Criar `frontend/src/types/recurringTask.ts` (espelhando `RecurringTaskCreate`/
  `Update`/`Read` de contracts/recurring-tasks.md)
- [x] T026 [P] Criar `frontend/src/services/recurringTaskService.ts` (`list`, `create`, `update`,
  `remove`, `complete`, `uncomplete`) (depende de T025)
- [x] T027 [P] Criar `frontend/src/hooks/useRecurringTasks.ts` (depende de T026)
- [x] T028 [P] Criar `frontend/src/components/layout/TasksTabs.tsx` — mesmo padrão visual de
  `AuthTabs.tsx` (sublinhado azul, `Link` + `useLocation`), alternando entre `/tasks` (quadro,
  inalterado) e `/tasks/recurring` (novo) (research.md #5)

**Checkpoint**: estrutura de dados e navegação do frontend prontas.

**Commit sugerido**: `chore(frontend): estrutura base de Tarefas Fixas`

---

## Phase 9: Frontend — User Story 1: Tarefa Fixa Diária (Priority: P1) 🎯 MVP

- [x] T029 [US1] Criar `frontend/src/pages/RecurringTasksPage.tsx`: lista de tarefas fixas, toggle
  concluída/pendente (visível quando `is_due_today`, mudo quando não), Sheet de criação — formulário
  com título + seletor de recorrência mostrando por ora só a opção diária (depende de T027, T028)
- [x] T030 [US1] Ligar a rota `/tasks/recurring` em `frontend/src/routes/index.tsx` e renderizar
  `TasksTabs` acima do quadro em `frontend/src/pages/PersonalTasksPage.tsx` (conteúdo do quadro
  inalterado) (depende de T029)
- [x] T031 [P] [US1] Teste de componente (estado vazio, criar tarefa diária, alternar
  concluída/pendente) em `frontend/tests/RecurringTasksPage.test.tsx` (depende de T030)

**Checkpoint**: US1 completa no frontend.

🎯 **Marco: MVP de Tarefas Fixas concluído** (US1 backend + frontend)

**Commit sugerido**: `feat(frontend): implementa tarefas fixas diárias (US1)`

---

## Phase 10: Frontend — User Story 2: Tarefa Fixa Semanal (Priority: P2)

- [x] T032 [US2] Estender o formulário de `RecurringTasksPage.tsx` com seleção de dias da semana
  quando o tipo escolhido é semanal (depende de T029)
- [x] T033 [P] [US2] Teste de componente cobrindo criação semanal e a rejeição sem dia selecionado
  em `RecurringTasksPage.test.tsx` (depende de T032)

**Commit sugerido**: `feat(frontend): implementa tarefas fixas semanais (US2)`

---

## Phase 11: Frontend — User Story 3: Tarefa Fixa Mensal (Priority: P3)

- [x] T034 [US3] Estender o formulário de `RecurringTasksPage.tsx` com seleção do dia do mês quando
  o tipo escolhido é mensal (depende de T029)
- [x] T035 [P] [US3] Teste de componente cobrindo criação mensal em `RecurringTasksPage.test.tsx`
  (depende de T034)

**Commit sugerido**: `feat(frontend): implementa tarefas fixas mensais (US3)`

---

## Phase 12: Frontend — User Story 4: Editar e Excluir (Priority: P2)

- [x] T036 [US4] Adicionar edição (reabre o mesmo Sheet pré-preenchido) e exclusão (`AlertDialog`,
  mesmo padrão já usado em toda a aplicação) a cada item da lista em `RecurringTasksPage.tsx`
  (depende de T029)
- [x] T037 [P] [US4] Teste de componente cobrindo editar e excluir em
  `RecurringTasksPage.test.tsx` (depende de T036)

**Checkpoint**: as 4 User Stories completas em backend e frontend.

🎯 **Marco: Tarefas Fixas concluída**

**Commit sugerido**: `feat(frontend): implementa edição e exclusão de tarefas fixas (US4)`

---

## Phase 13: Validação Final (cross-cutting)

- [x] T038 Executar o roteiro completo de `quickstart.md` (6 roteiros) e registrar o resultado —
  os 6 roteiros são cobertos integralmente pela suíte automatizada (não repetidos manualmente à
  parte): Roteiro 1 (diária) → testes de US1; Roteiro 2 (semanal) → US2; Roteiro 3 (mensal, incl.
  mês curto) → US3; Roteiro 4 (editar/excluir) → US4; Roteiro 5 (isolamento/Dashboard) → Fase 7;
  Roteiro 6 (frontend) → `RecurringTasksPage.test.tsx`. Suíte completa do backend: 660/660 passed
  (627 do MVP + 33 novos: 25 integração + 7 unitários + 1 de isolamento do Dashboard). Suíte
  completa do frontend: 76/76 passed (68 anteriores + 8 novos). `tsc -b --noEmit` e `npm run
  build` sem erros. Migração `0005_recurring_tasks` aplicada com sucesso tanto no banco de teste
  quanto no banco de desenvolvimento local
- [x] T039 Avaliar se `README.md` precisa mencionar a nova aba "Tarefas Fixas" (Constitution —
  seção 16 do `CLAUDE.md`) — **não necessário agora**: o `README.md` da raiz ainda está no estado
  genérico/aspiracional de antes do Spec Kit (nem reflete PostgreSQL, que já está em uso há muito,
  nem nenhuma das 13 User Stories do MVP já implementadas) — atualizá-lo é T175 de
  `001-taskflow-mvp/tasks.md` (Fase 31, "Integração e Validação Final"), ainda pendente e fora do
  escopo desta feature. Adicionar só "Tarefas Fixas" isoladamente, antes dessa atualização
  completa, deixaria o documento mais inconsistente, não menos

**Checkpoint**: Tarefas Fixas completa, integrada e validada.

🎯 **Marco: Tarefas Fixas concluída e validada**

**Commit sugerido**: `docs: atualiza README e finaliza validação de Tarefas Fixas`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sem dependências.
- **Foundational (Fase 2)**: depende da Fase 1 — bloqueia todas as User Stories.
- **Backend User Stories (Fases 3-6)**: todas dependem da Fase 2. US1 é a base (schema/service/
  rotas nascem nela); US2 e US3 estendem a mesma `RecurringTaskService`/rotas já criadas em US1
  (não recriam nada); US4 depende só de US1 (editar/excluir não depende de US2/US3 existirem).
- **Isolamento/Dashboard (Fase 7)**: depende das Fases 3-6.
- **Frontend Foundation (Fase 8)**: depende da Fase 7 (backend completo e testado).
- **Frontend User Stories (Fases 9-12)**: cada uma depende da Fase 8 e da fase de backend
  correspondente à mesma story.
- **Validação Final (Fase 13)**: depende de todas as fases anteriores.

### User Story Dependencies

- **US1 (P1)**: depende só da Fase 2 (Foundational) — MVP mínimo desta feature.
- **US2 (P2)**: depende de US1 (mesma `RecurringTaskService`/rotas, estendidas).
- **US3 (P3)**: depende de US1 (idem US2); independente de US2.
- **US4 (P2)**: depende só de US1 (editar/excluir não exige semanal/mensal implementados).

### Parallel Opportunities

- Todas as tasks `[P]` de uma mesma fase podem rodar em paralelo (arquivos diferentes, sem
  dependência entre si).
- US2 e US3 são mutuamente independentes (ambas só dependem de US1) — podem ser feitas em paralelo
  por desenvolvedores diferentes.
- Testes de uma mesma story marcados `[P]` sempre podem rodar em paralelo entre si.

---

## Parallel Example: Foundational (Fase 2)

```bash
Task: "Criar model RecurringTask em backend/app/models/recurring_task.py"
Task: "Criar schemas em backend/app/schemas/recurring_task.py"
Task: "Criar repository em backend/app/repositories/recurring_task_repository.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (bloqueia tudo)
3. Completar Fase 3: US1 backend — validar independentemente (quickstart.md, Roteiro 1)
4. Completar Fases 8-9: US1 frontend
5. **PARAR e VALIDAR**: tarefa fixa diária funcionando ponta a ponta antes de prosseguir

### Entrega Incremental

1. Setup + Foundational → base pronta
2. US1 (backend + frontend) → 🎯 MVP de Tarefas Fixas
3. US2 → US3 → US4, cada uma validada antes de avançar (podem ser paralelizadas entre si após US1)
4. Fase 13 → validação final

---

## Notes

- `[P]` = arquivos diferentes, sem dependência entre si
- `[Story]` mapeia a task à User Story correspondente para rastreabilidade
- Toda task de teste MUST ser escrita e falhar antes da implementação correspondente
  (Constitution VIII)
- Commitar após cada bloco ou fase (ver sugestões de commit acima), seguindo Conventional Commits
  (CLAUDE.md) — nunca automaticamente, sempre aguardando autorização
- Parar em qualquer marco/checkpoint para validar antes de avançar
