# Implementation Plan: Tarefas Fixas (Rotinas Pessoais Recorrentes)

**Branch**: `001-taskflow-mvp` (decisão do usuário: sem branch dedicada para esta feature — ver
nota abaixo) | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-tarefas-fixas/spec.md`

> **Nota de branch**: o Spec Kit deste projeto numera o diretório da spec (`002-tarefas-fixas`)
> independentemente do nome da branch git — são decisões independentes (ver
> `specs/002-tarefas-fixas/spec.md` e a conversa que originou esta feature). O usuário optou
> explicitamente por continuar todo o trabalho na branch `001-taskflow-mvp` já em uso, em vez de
> criar uma branch `002-tarefas-fixas` dedicada.

## Summary

Uma nova funcionalidade dentro da tela "Minhas Tarefas": uma segunda aba, "Tarefas Fixas", para
rotinas pessoais recorrentes (diária, semanal em dias específicos, ou mensal num dia específico) —
deliberadamente enxutas (só título + recorrência + estado concluído/pendente do dia), sem
prioridade, prazo, comentários, checklist, anexos ou histórico. Cada ocorrência (cada data em que a
tarefa se aplica) reseta sozinha, sem ação do usuário, porque "concluída hoje" é derivado da
presença de um registro de conclusão para a data de hoje — nunca um único campo sobrescrito
(`research.md` #2), o que também deixa a porta aberta para um streak futuro sem migração destrutiva
(FR-014).

Abordagem técnica: reaproveita 100% da stack e da arquitetura já estabelecidas em
`001-taskflow-mvp` (mesmo monorepo, mesma stack, mesmas camadas) — sem dependência nova, sem
categoria de diretório nova. Três tabelas novas (uma migração Alembic), uma dependency de
autorização nova, um conjunto de rotas novo (`/api/v1/recurring-tasks`), e uma segunda aba de rota
no frontend (`/tasks/recurring`, irmã de `/tasks`).

Decisões técnicas detalhadas: [research.md](./research.md).
Modelo de dados completo: [data-model.md](./data-model.md).
Contrato de API: [contracts/recurring-tasks.md](./contracts/recurring-tasks.md).
Roteiro de validação: [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: inalterado de `001-taskflow-mvp` — Python 3.13 (backend); TypeScript 5.x +
React 19 (frontend).

**Primary Dependencies**: inalterado — nenhuma dependência nova. Cálculo de "último dia do mês"
usa `calendar.monthrange` (biblioteca padrão do Python, `research.md` #3).

**Storage**: mesmo PostgreSQL 15+ já em uso. 3 tabelas novas (`recurring_tasks`,
`recurring_task_weekdays`, `recurring_task_completions`) — ver [data-model.md](./data-model.md).

**Testing**: inalterado — pytest + pytest-cov + httpx (backend); Vitest + React Testing Library
(frontend).

**Target Platform**: inalterado.

**Project Type**: web (mesmo monorepo `backend/` + `frontend/`).

**Performance Goals**: sem requisito especial — volume por usuário é pequeno (dezenas de tarefas
fixas, no máximo), mesmo perfil qualitativo do restante do MVP.

**Constraints**: reaproveita `today_in_app_timezone()` já existente (`app/utils/timezone.py`) —
nenhuma timezone nova, nenhuma lógica de data duplicada (`research.md` #4). Sem notificação/lembrete
associado a Tarefas Fixas nesta versão (fora de escopo, spec.md "Assumptions").

**Scale/Scope**: 4 User Stories, 14 Functional Requirements, 3 entidades novas, 1 grupo de rotas
novo, 1 aba nova no frontend.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliação contra os 14 princípios de `.specify/memory/constitution.md` (v1.1.0):

| Princípio | Status | Nota |
|---|---|---|
| I. Stack Tecnológico Exclusivo | ✅ PASS | Mesma stack do MVP, sem exceção. |
| II. Clean Code, Tipagem e Responsabilidade Única | ✅ PASS | `RecurringTaskService` concentra toda a regra de recorrência/ocorrência; nenhuma lógica de negócio em rota ou componente. |
| III. Separação de Camadas | ✅ PASS | Mesma árvore de camadas (`models/schemas/repositories/services/routes/enums/dependencies`) — nenhuma categoria nova. |
| IV. Backend como Autoridade de Validação | ✅ PASS | Cálculo de ocorrência, validação de padrão de recorrência e a data usada em cada conclusão são 100% do backend (`research.md` #4) — frontend só reflete `is_due_today`/`completed_today` já calculados. |
| V. Reuso e Evolução Consistente | ✅ PASS | Nenhuma dependência nova; tabela filha para dias da semana (não bitmask/array — `research.md` #1) e reaproveitamento de `today_in_app_timezone()` são escolhas deliberadas de reuso de padrão existente. |
| VI. Migrações via Alembic | ✅ PASS | 1 migração nova, agrupando as 3 tabelas — mesmo fluxo das 4 migrações do MVP. |
| VII. Documentação Automática (OpenAPI) | ✅ PASS | Rotas novas com `response_model` explícito (`RecurringTaskRead`), mesmo padrão do restante da API. |
| VIII. Cobertura de Testes para Regras Críticas | ✅ PASS | Ver seção "Testes" abaixo — cálculo de ocorrência (incl. mês curto) e o modelo de conclusão por data são as regras críticas desta feature. |
| IX. Nomenclatura Padronizada por Camada | ✅ PASS | `RecurringTask`/`RecurringTaskWeekday`/`RecurringTaskCompletion` (Models), `RecurringTaskService`/`Repository`, rotas em `/recurring-tasks` (substantivo plural), `require_recurring_task_owner` (dependency, mesmo padrão `require_<recurso>_<regra>`). |
| X. Tratamento Padronizado de Erros | ✅ PASS | Mesmo envelope de erro; `400 BUSINESS_RULE_VIOLATION` para conclusão fora de ocorrência, `404` para acesso indevido. |
| XI. Logging de Operações Importantes | ✅ PASS | Criação/edição/exclusão de Tarefa Fixa logadas, mesmo padrão do restante do backend. |
| XII. Configuração Centralizada | ✅ PASS | Nenhuma variável de configuração nova — reaproveita `APP_TIMEZONE` já existente. |
| XIII. Fluxo Spec Kit Obrigatório | ✅ PASS | Esta feature está seguindo o fluxo completo (`specify` → `clarify` opcional → `plan` → `tasks` → `implement`) desde o início. |
| XIV. Compatibilidade Arquitetural | ✅ PASS | Nenhuma mudança estrutural — todos os arquivos novos entram em categorias já existentes (`models/`, `schemas/`, `services/`, `repositories/`, `routes/`, `enums/`, `dependencies/` no backend; `pages/`, `services/`, `hooks/`, `types/`, `components/layout/` no frontend). |

**Resultado**: nenhuma violação. `Complexity Tracking` vazio.

## Project Structure

### Documentation (this feature)

```text
specs/002-tarefas-fixas/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md         # Fase 1
├── contracts/
│   └── recurring-tasks.md
└── tasks.md              # Fase 2 — gerado por /speckit-tasks (não criado aqui)
```

### Source Code (repository root)

```text
TaskFlow/
├── backend/
│   └── app/
│       ├── enums/
│       │   └── recurrence_type.py         # NOVO
│       ├── models/
│       │   ├── recurring_task.py          # NOVO
│       │   ├── recurring_task_weekday.py  # NOVO
│       │   └── recurring_task_completion.py  # NOVO
│       ├── schemas/
│       │   └── recurring_task.py          # NOVO — Create/Update/Read
│       ├── repositories/
│       │   └── recurring_task_repository.py  # NOVO
│       ├── services/
│       │   └── recurring_task_service.py  # NOVO — cálculo de ocorrência, validação, conclusão
│       ├── routes/
│       │   └── recurring_tasks.py         # NOVO
│       └── dependencies/
│           └── task_authorization.py      # ESTENDIDO — require_recurring_task_owner
│   └── alembic/versions/
│       └── 000X_recurring_tasks.py        # NOVO — 1 migração, 3 tabelas
│
├── frontend/
│   └── src/
│       ├── types/
│       │   └── recurringTask.ts           # NOVO
│       ├── services/
│       │   └── recurringTaskService.ts    # NOVO
│       ├── hooks/
│       │   └── useRecurringTasks.ts       # NOVO
│       ├── components/layout/
│       │   └── TasksTabs.tsx              # NOVO — mesmo padrão visual de AuthTabs (research.md #5)
│       ├── pages/
│       │   ├── PersonalTasksPage.tsx      # INALTERADA em conteúdo — só ganha a TasksTabs acima do quadro
│       │   └── RecurringTasksPage.tsx     # NOVO
│       └── routes/index.tsx               # ESTENDIDO — nova rota /tasks/recurring
```

**Structure Decision**: nenhuma categoria de diretório nova em nenhum dos dois projetos — todo
arquivo novo entra numa categoria já existente (Constitution XIV). Único ajuste de estrutura:
`PersonalTasksPage.tsx` passa a renderizar `TasksTabs` acima do quadro kanban (sem alterar o
conteúdo do próprio quadro).

## Modelo de Dados

Ver [data-model.md](./data-model.md) — 3 tabelas (`RecurringTask`, `RecurringTaskWeekday`,
`RecurringTaskCompletion`), 1 enum novo (`RecurrenceType`), cálculo de ocorrência 100% em memória
no Service (nunca persistido).

## Regras de Domínio — onde cada uma é validada

| Regra (spec) | Banco | Schema | Service | Dependency/Auth |
|---|---|---|---|---|
| Tarefa fixa pertence a exatamente um usuário, sem workspace/compartilhamento (FR-011) | `owner_id NOT NULL`, sem `workspace_id` na tabela | — | — | `require_recurring_task_owner` — 404 para qualquer outro usuário |
| Recorrência semanal exige ao menos 1 dia selecionado (FR-002) | — | `RecurringTaskCreate`/`Update` validam presença de `weekdays` quando `recurrence_type=WEEKLY` | `RecurringTaskService` reforça a mesma regra (Constitution IV — nunca só no schema) | — |
| Recorrência mensal exige `month_day` 1-31 (FR-003) | `CHECK (month_day BETWEEN 1 AND 31)` | Pydantic `Field(ge=1, le=31)` | `RecurringTaskService` | — |
| Cálculo de ocorrência, incl. mês curto → último dia do mês (FR-004) | — | — | `RecurringTaskService._is_occurrence(task, date)` — única função, reaproveitada por listagem e por marcar conclusão | — |
| Conclusão só é aceita se hoje for ocorrência (FR-005) | `UNIQUE(recurring_task_id, occurrence_date)` impede duplicata | — | `RecurringTaskService.complete_today` — `400 BUSINESS_RULE_VIOLATION` se hoje não for ocorrência | — |
| Cada ocorrência com estado independente; reset automático (FR-006/FR-007) | Presença/ausência de linha em `recurring_task_completions` (research.md #2) | — | — | — |
| Editar não afeta conclusões passadas (FR-008) | `RecurringTaskCompletion` nunca é tocada por um `PATCH` em `RecurringTask` | — | `RecurringTaskService.update` só altera a linha de `recurring_tasks` (+ `recurring_task_weekdays` se `WEEKLY`) | — |
| Excluir remove as conclusões associadas (FR-009) | `ON DELETE CASCADE` em `recurring_task_completions`/`recurring_task_weekdays` | — | — | `require_recurring_task_owner` |
| Tarefas Fixas nunca entram no Dashboard (FR-013) | Tabelas totalmente separadas de `tasks` — `DashboardService`/`TaskRepository` nunca as consultam | — | — | — |

## API REST

Ver [contracts/recurring-tasks.md](./contracts/recurring-tasks.md) — `POST`/`GET
/recurring-tasks`, `PATCH`/`DELETE /recurring-tasks/{id}`, `POST`/`DELETE
/recurring-tasks/{id}/completions`.

## Frontend

- `TasksTabs.tsx`: alterna entre `/tasks` (quadro, já existente, inalterado) e `/tasks/recurring`
  (novo), mesmo tratamento visual de `AuthTabs` (research.md #5) — componente novo porque
  `AuthTabs` está fixado nas rotas de autenticação.
- `RecurringTasksPage.tsx`: lista de Tarefas Fixas do usuário, cada uma com um toggle
  concluída/pendente (visível apenas quando `is_due_today`, mudo/desabilitado quando não), ação de
  editar (Sheet + formulário, mesmo padrão de `TaskForm`) e excluir (`AlertDialog`, mesmo padrão já
  usado em toda a aplicação).
- Sem prioridade/prazo/comentários/etc. no formulário (FR-012) — só título e o seletor de
  recorrência (tipo + dias da semana OU dia do mês, condicional ao tipo escolhido).

## Testes

**Backend** — casos cobrindo as regras críticas (Constitution VIII):

- Criar tarefa fixa diária/semanal/mensal com dados válidos.
- Rejeitar semanal sem nenhum dia selecionado; rejeitar mensal sem `month_day`/com `month_day` fora
  de 1-31.
- Cálculo de ocorrência: diária sempre ocorrência; semanal só nos dias selecionados; mensal no dia
  configurado E no último dia do mês quando o mês não tiver esse dia (casos: dia 31 em mês de 30
  dias, dia 29/30/31 em fevereiro não bissexto e bissexto).
- Marcar ocorrência de hoje como concluída; chamar de novo no mesmo dia não duplica
  (`UNIQUE(recurring_task_id, occurrence_date)`); desmarcar volta a pendente.
- Marcar conclusão num dia que não é ocorrência → `400 BUSINESS_RULE_VIOLATION`.
- Editar título/recorrência não altera conclusões já registradas.
- Excluir remove a tarefa fixa e todas as suas conclusões/dias associados (nenhuma linha órfã).
- Usuário B não acessa (`404`) tarefa fixa do usuário A, em nenhuma das 5 rotas.
- `GET /dashboard` antes/depois de criar e concluir Tarefas Fixas → contagens idênticas (FR-013).

**Frontend**: componente de página (estado vazio, listagem, criação, toggle de conclusão
condicionado a `is_due_today`, edição, exclusão) — mesmo padrão de testes já usado em
`PersonalTasksPage.test.tsx`.

## Ordem de Implementação

Segue o mesmo formato de fases do MVP (`001-taskflow-mvp/tasks.md`), adaptado ao tamanho desta
feature:

1. **Backend — Fundação**: enum `RecurrenceType`, os 3 models, a migração Alembic.
2. **Backend — Domínio**: schemas, repository, `RecurringTaskService` (criar/editar/excluir +
   cálculo de ocorrência + conclusão/desconclusão), `require_recurring_task_owner`, rotas.
3. **Backend — Testes**: cobertura completa das regras críticas (ver "Testes" acima) antes de
   avançar para o frontend (mesma ordem incremental já usada no MVP: back-end validado antes do
   front consumir).
4. **Frontend**: tipos, service, hook, `TasksTabs`, `RecurringTasksPage`, formulário de
   criação/edição, ligação da rota `/tasks/recurring`.
5. **Frontend — Testes**: componente de página.
6. **Validação final**: roteiro completo de `quickstart.md`.

## Complexity Tracking

> Nenhuma violação da Constitution foi identificada (ver "Constitution Check" acima). Tabela
> intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| _(nenhuma)_ | — | — |
