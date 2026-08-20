# Data Model: Tarefas Fixas (Rotinas Pessoais Recorrentes)

**Feature**: `002-tarefas-fixas` | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

Três tabelas novas, todas dentro de uma única migração Alembic (Constitution VI). Nenhuma tabela
existente do MVP (`001-taskflow-mvp`) é alterada.

## Enum: `RecurrenceType`

`backend/app/enums/recurrence_type.py` (mesmo padrão de `TaskStatus`/`TaskPriority`):

```python
class RecurrenceType(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
```

## Entidade: `RecurringTask` (Tarefa Fixa)

Tabela `recurring_tasks`.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | gerado pelo banco |
| `owner_id` | UUID (FK → `users.id`, `ON DELETE RESTRICT`) | mesma convenção de `Task.creator_id`; NOT NULL |
| `title` | VARCHAR(255) | NOT NULL, `CHECK` não vazio (mesmo espírito de `Comment.content`) |
| `recurrence_type` | `RecurrenceType` | NOT NULL |
| `month_day` | SMALLINT | NULL exceto quando `recurrence_type = MONTHLY`; `CHECK (month_day BETWEEN 1 AND 31)` quando não nulo |
| `created_at` | TIMESTAMPTZ | default `now()` |
| `updated_at` | TIMESTAMPTZ | default `now()`, atualizado a cada `UPDATE` |

**Invariantes** (reforçadas em `RecurringTaskService`, nunca só no schema — Constitution IV):

- `recurrence_type = WEEKLY` MUST ter pelo menos uma linha em `recurring_task_weekdays`.
- `recurrence_type = MONTHLY` MUST ter `month_day` preenchido (1-31).
- `recurrence_type IN (DAILY, WEEKLY)` MUST ter `month_day IS NULL`.
- `recurrence_type IN (DAILY, MONTHLY)` MUST NOT ter nenhuma linha em `recurring_task_weekdays`.

**Relacionamentos**: `owner_id` → `User` (N:1, sem relação inversa exposta em `UserRead` — mesmo
padrão de `Task`). `RecurringTaskWeekday` e `RecurringTaskCompletion` pertencem a `RecurringTask`
(1:N cada), ambas `ON DELETE CASCADE` (FR-009: excluir a Tarefa Fixa remove seus dias e conclusões).

## Entidade: `RecurringTaskWeekday`

Tabela `recurring_task_weekdays` — só usada quando `recurrence_type = WEEKLY` (research.md #1).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | gerado pelo banco |
| `recurring_task_id` | UUID (FK → `recurring_tasks.id`, `ON DELETE CASCADE`) | NOT NULL |
| `weekday` | SMALLINT | NOT NULL, `CHECK (weekday BETWEEN 0 AND 6)` — `0 = segunda`, `6 = domingo` (`date.weekday()` do Python) |

`UNIQUE(recurring_task_id, weekday)` — o mesmo dia não pode ser selecionado duas vezes para a mesma
tarefa fixa.

## Entidade: `RecurringTaskCompletion` (Conclusão de Ocorrência)

Tabela `recurring_task_completions` — é a presença/ausência de uma linha aqui, para a data de hoje,
que decide se uma Tarefa Fixa está concluída ou pendente hoje (research.md #2, FR-006/FR-014).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | gerado pelo banco |
| `recurring_task_id` | UUID (FK → `recurring_tasks.id`, `ON DELETE CASCADE`) | NOT NULL |
| `occurrence_date` | DATE | NOT NULL — a data da ocorrência concluída, sempre `today_in_app_timezone()` no momento da criação (nunca uma data arbitrária vinda do cliente, research.md #4) |
| `completed_at` | TIMESTAMPTZ | default `now()` — quando o registro foi de fato criado (auditoria; distinto de `occurrence_date`) |

`UNIQUE(recurring_task_id, occurrence_date)` — uma ocorrência só pode ter uma conclusão.

## Cálculo de "ocorrência" (não persistido — computado em `RecurringTaskService`)

Dada uma `RecurringTask` e uma data `d` (sempre `today_in_app_timezone()` nos fluxos desta feição):

- `DAILY` → `d` é sempre ocorrência.
- `WEEKLY` → `d` é ocorrência **se e somente se** `d.weekday()` estiver entre os `weekday` cadastrados
  em `recurring_task_weekdays`.
- `MONTHLY` → seja `last_day = calendar.monthrange(d.year, d.month)[1]` (research.md #3); `d` é
  ocorrência **se e somente se** `d.day == min(month_day, last_day)`.

`is_due_today` e `completed_today` (ambos derivados, nunca persistidos) compõem a resposta de
`RecurringTaskRead`:

- `is_due_today = <regra acima aplicada a hoje>`
- `completed_today = existe RecurringTaskCompletion(recurring_task_id, occurrence_date=hoje)`

## Migração Alembic

Uma migração nova (`000X_recurring_tasks`), depois da última migração de `001-taskflow-mvp`, criando
as 3 tabelas acima nesta ordem (`recurring_tasks` → `recurring_task_weekdays` →
`recurring_task_completions`, respeitando as FKs) mais os 2 índices únicos parciais/compostos
(`recurring_task_weekdays`, `recurring_task_completions`) e os `CHECK`s listados. `downgrade()`
remove as 3 tabelas na ordem inversa — mesmo padrão das 4 migrações do MVP (Constitution VI).
