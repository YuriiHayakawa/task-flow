# Quickstart: Tarefas Fixas (Rotinas Pessoais Recorrentes)

**Feature**: `002-tarefas-fixas` | **Spec**: [spec.md](./spec.md)

Ambiente já preparado conforme [`001-taskflow-mvp/quickstart.md`](../001-taskflow-mvp/quickstart.md)
(backend em `http://localhost:8000/api/v1`, migrações aplicadas incl. a nova de
`recurring_tasks`/`recurring_task_weekdays`/`recurring_task_completions`, frontend em
`http://localhost:5173`). Este guia cobre só os roteiros de validação **desta** feature.

## Pré-requisito

Um usuário autenticado (token JWT via `POST /auth/login`, ver quickstart do MVP) — Tarefas Fixas não
tem fluxo de cadastro próprio.

## Roteiro 1 — Tarefa fixa diária (US1)

1. `POST /api/v1/recurring-tasks` com `{"title": "Beber água", "recurrence_type": "DAILY"}` →
   espera `201`, `is_due_today: true`, `completed_today: false`.
2. `GET /api/v1/recurring-tasks` → a tarefa aparece na lista, `is_due_today: true`.
3. `POST /api/v1/recurring-tasks/{id}/completions` → espera `201`, `completed_today: true`.
4. `POST /api/v1/recurring-tasks/{id}/completions` de novo (mesmo dia) → espera `200` (idempotente,
   não duplica).
5. `DELETE /api/v1/recurring-tasks/{id}/completions` → espera `200`, `completed_today: false`.

## Roteiro 2 — Tarefa fixa semanal em dias específicos (US2)

1. `POST /api/v1/recurring-tasks` com
   `{"title": "Revisar e-mails", "recurrence_type": "WEEKLY", "weekdays": [0, 2, 4]}` (segunda,
   quarta, sexta) → espera `201`.
2. Num dia da semana **fora** dessa lista: `GET /api/v1/recurring-tasks` → a tarefa aparece,
   `is_due_today: false`; `POST .../completions` → espera `400 BUSINESS_RULE_VIOLATION`.
3. Num dia **dentro** da lista: `is_due_today: true`; `POST .../completions` funciona normalmente
   (mesmo comportamento do Roteiro 1).

## Roteiro 3 — Tarefa fixa mensal, mês curto (US3)

1. `POST /api/v1/recurring-tasks` com
   `{"title": "Pagar boleto", "recurrence_type": "MONTHLY", "month_day": 31}` → espera `201`.
2. Num mês com menos de 31 dias (ex.: abril, fevereiro): `is_due_today: true` **no último dia do
   mês** (dia 30 em abril, dia 28/29 em fevereiro) — nunca em nenhum outro dia, nunca pulando o mês
   (data-model.md, "Cálculo de ocorrência").

## Roteiro 4 — Editar e excluir (US4)

1. Editar: `PATCH /api/v1/recurring-tasks/{id}` com `{"title": "Novo título"}` → espera `200`,
   `title` atualizado, conclusões passadas inalteradas.
2. Trocar de `WEEKLY` para `DAILY`: `PATCH` com `{"recurrence_type": "DAILY"}` → espera `200`,
   `weekdays: []`.
3. Excluir: `DELETE /api/v1/recurring-tasks/{id}` → espera `204`; `GET /api/v1/recurring-tasks` não
   lista mais a tarefa; nenhuma linha órfã em `recurring_task_completions`/`recurring_task_weekdays`
   (verificável direto no banco durante o desenvolvimento).

## Roteiro 5 — Isolamento e Dashboard (FR-011, FR-013)

1. Usuário B (outro token) tenta `GET`/`PATCH`/`DELETE` numa Tarefa Fixa do usuário A → espera `404`
   em todos os casos (nunca `403` — `_conventions.md`).
2. `GET /api/v1/dashboard` do usuário A, antes e depois de criar/concluir Tarefas Fixas → contagens
   idênticas nos dois momentos (Tarefas Fixas nunca entram no Dashboard).

## Roteiro 6 — Frontend

1. Login → "Minhas tarefas" → aba "Tarefas Fixas" (`/tasks/recurring`) ao lado da aba do quadro
   (`/tasks`) → confirma navegação entre as duas sem perder o estado de autenticação.
2. Criar uma tarefa fixa pelo formulário, marcar/desmarcar o toggle de hoje, editar, excluir — cada
   ação reflete imediatamente na lista, sem recarregar a página manualmente.
