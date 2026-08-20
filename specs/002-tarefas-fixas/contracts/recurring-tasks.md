# Contract: Recurring Tasks (Tarefas Fixas)

**Feature**: `002-tarefas-fixas` | Segue as convenções gerais de
[`001-taskflow-mvp/contracts/_conventions.md`](../../001-taskflow-mvp/contracts/_conventions.md)
(base path `/api/v1`, envelope de erro, códigos HTTP, autenticação, timestamps) — não repetidas
aqui.

**Autorização** (research.md #6): toda rota abaixo exige que o usuário autenticado seja o
`owner_id` do recurso — `404` (nunca `403`) para qualquer outro usuário, incl. quem não é dono.
Sem noção de visibilidade/colaboração como em `Task` — uma Tarefa Fixa nunca é vista por ninguém
além do dono (FR-011).

## Schemas

- **`RecurringTaskCreate`**: `title` (string, 1-255), `recurrence_type`
  (`DAILY`\|`WEEKLY`\|`MONTHLY`), `weekdays` (lista de int 0-6, obrigatória e não vazia **apenas**
  quando `recurrence_type = WEEKLY`), `month_day` (int 1-31, obrigatório **apenas** quando
  `recurrence_type = MONTHLY`).
- **`RecurringTaskUpdate`**: mesmos campos de `RecurringTaskCreate`, todos opcionais (atualização
  parcial) — mudar `recurrence_type` exige fornecer os campos que o novo tipo requer na mesma
  requisição (não é permitido deixar a tarefa num estado inconsistente entre dois `PATCH`s).
- **`RecurringTaskRead`**: `id`, `title`, `recurrence_type`, `weekdays` (lista, vazia se não
  `WEEKLY`), `month_day` (`null` se não `MONTHLY`), `is_due_today` (bool, derivado — data-model.md),
  `completed_today` (bool, derivado), `created_at`, `updated_at`.

## `POST /api/v1/recurring-tasks`

Cria uma Tarefa Fixa para o usuário autenticado (dono = usuário autenticado, nunca vindo do corpo).

- **Body**: `RecurringTaskCreate`.
- **Respostas**: `201` (`RecurringTaskRead`) · `400` `VALIDATION_ERROR` (recorrência semanal sem
  dias, ou mensal sem `month_day`, ou `month_day` fora de 1-31) · `401`.

## `GET /api/v1/recurring-tasks`

Lista todas as Tarefas Fixas do usuário autenticado.

- **Respostas**: `200` (lista de `RecurringTaskRead`, sem paginação — volume esperado baixo por
  usuário, mesmo padrão de Checklist/Attachments em `001-taskflow-mvp`) · `401`.

## `PATCH /api/v1/recurring-tasks/{id}`

Edita título e/ou padrão de recorrência. Conclusões já registradas (ocorrências passadas) MUST NOT
ser alteradas (FR-008).

- **Body**: `RecurringTaskUpdate`.
- **Respostas**: `200` (`RecurringTaskRead`) · `400` `VALIDATION_ERROR` · `404`.

## `DELETE /api/v1/recurring-tasks/{id}`

Exclui a Tarefa Fixa. `ON DELETE CASCADE` remove junto `recurring_task_weekdays` e
`recurring_task_completions` (FR-009) — sem passo manual adicional no Service além do `DELETE` da
linha pai.

- **Respostas**: `204` · `404`.

## `POST /api/v1/recurring-tasks/{id}/completions`

Marca a ocorrência de **hoje** (`today_in_app_timezone()`, nunca uma data do cliente — research.md
#4) como concluída.

- **Regras**: `400` `BUSINESS_RULE_VIOLATION` se hoje não for uma ocorrência desta tarefa fixa (ex.:
  tarefa semanal configurada para segunda/quarta/sexta, hoje é terça). Chamar de novo no mesmo dia,
  já concluído, é idempotente — não cria uma segunda linha (`UNIQUE(recurring_task_id,
  occurrence_date)`) e responde `201` normalmente, sem distinguir "criou agora" de "já existia".
- **Respostas**: `201` (`RecurringTaskRead`, já refletindo `completed_today: true`) · `400` · `404`.

## `DELETE /api/v1/recurring-tasks/{id}/completions`

Desmarca a ocorrência de **hoje** (volta a pendente). Idempotente — chamar quando já está pendente
não é erro.

- **Respostas**: `200` (`RecurringTaskRead`, já refletindo `completed_today: false`) · `404`.
