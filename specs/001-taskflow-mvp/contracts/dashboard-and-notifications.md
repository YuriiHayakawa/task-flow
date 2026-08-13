# Contracts: Dashboard & Notifications

Ver convenções gerais em [`_conventions.md`](./_conventions.md).
Cobre módulos: **Dashboard**, **Notifications**.
Requisitos relacionados: FR-011, FR-039, FR-040, FR-047 a FR-050.

## Dashboard

### `GET /api/v1/dashboard`

- **Auth**: usuário autenticado.
- **Regras**: agrega, sob demanda (`research.md` #7), as tarefas visíveis ao usuário —
  tarefas pessoais do próprio usuário + tarefas de todos os workspaces dos quais é
  membro (FR-048) — nunca tarefas pessoais de terceiros (FR-049).
- **Sem efeito colateral de notificação**: diferentemente da revisão 1 deste plano, este
  endpoint **não** dispara mais a geração de notificações `DUE_SOON` — isso agora é
  responsabilidade exclusiva da tarefa periódica (ver seção abaixo e `research.md` #2).
  `GET /dashboard` é uma operação de leitura pura.
- **Resposta** (`DashboardSummary`, `200`):

```json
{
  "counts": {
    "pending": 4,
    "in_progress": 2,
    "done": 10,
    "overdue": 1,
    "due_today": 2
  }
}
```

- `pending`/`in_progress`/`done` somam todas as tarefas visíveis, independentemente do
  prazo. `overdue` e `due_today` são subconjuntos derivados de `due_date` (FR-011) sobre
  as tarefas não concluídas, calculados com "hoje" na timezone `APP_TIMEZONE`
  (`research.md` #9) — uma tarefa aparece em no máximo um dos dois (nunca ambos).
- Sem tarefas → todos os contadores `0` (nunca erro — US2, cenário 4).

### Escopo opcional do resumo (`workspace_id` / `project_id` / `personal_only`)

> **Adicionado após a US2/T065** — não previsto pela spec original (FR-047 a FR-050
> descrevem apenas o resumo combinado). Motivado pelo pedido de um alternador de
> contexto no Dashboard do frontend (pessoal / um workspace / um projeto específico).

- **Query** (todos opcionais, no máximo um por requisição): `workspace_id` (UUID),
  `project_id` (UUID), `personal_only` (bool).
- Sem nenhum filtro → comportamento padrão inalterado (resumo combinado, FR-048).
- `workspace_id` → contadores restritos às tarefas desse workspace (qualquer projeto ou
  diretamente no workspace).
- `project_id` → contadores restritos às tarefas desse projeto.
- `personal_only=true` → contadores restritos às tarefas pessoais do próprio usuário
  (`workspace_id IS NULL`).
- **Autorização**: não há checagem dedicada — o filtro de escopo é aplicado **sobre** a
  mesma visibilidade (`visible`) que já restringe o resumo aos workspaces dos quais o
  usuário é membro (mesmo padrão de `GET /tasks` com filtros, US8). Um `workspace_id`/
  `project_id` fora do alcance do usuário simplesmente devolve contadores zerados, sem
  distinguir "não existe" de "existe mas não sou membro" (mesma convenção de
  `_conventions.md`).
- **Respostas**: `200` (`DashboardSummary`, mesmo formato, agora com contagem restrita) ·
  `400` (`BUSINESS_RULE_VIOLATION`) se mais de um filtro de escopo for informado
  simultaneamente · `422` se `workspace_id`/`project_id` não forem UUIDs válidos.

## Notifications

### `GET /api/v1/notifications`

- **Auth**: usuário autenticado; retorna somente notificações do próprio usuário
  (`recipient_id = current_user.id`).
- **Query**: `is_read` (opcional, filtra lidas/não lidas); paginação padrão, ordenado por
  `created_at` descendente.
- **Respostas**: `200` (lista paginada de `NotificationRead`: `id`, `type`, `title`,
  `message`, `task_id`, `is_read`, `created_at`).

### `PATCH /api/v1/notifications/{notification_id}/read`

- **Auth**: dono da notificação.
- **Regras**: marca `is_read = true` (idempotente).
- **Respostas**: `200` (`NotificationRead`) · `403` (notificação de outro usuário —
  tratado como `404` por padrão de segurança, ver `_conventions.md`) · `404`.

### `PATCH /api/v1/notifications/read-all`

- **Auth**: usuário autenticado.
- **Regras**: marca todas as notificações não lidas do usuário como lidas.
- **Respostas**: `200` (`{ "updated": <int> }`).

## Eventos que geram notificação (disparados por outros services, não por este módulo)

| Evento | Disparado por | Tipo | Destinatários |
|---|---|---|---|
| Prazo próximo/vencendo hoje | **Tarefa periódica** (`app/core/scheduler.py`, a cada `DUE_SOON_CHECK_INTERVAL_SECONDS`, default 60s — ver `research.md` #2, substitui a estratégia lazy da revisão 1) chamando `NotificationService.generate_due_soon_notifications()` | `DUE_SOON` | responsável da tarefa |
| Novo comentário | `CommentService.create` | `NEW_COMMENT` | participantes da tarefa (responsável + `TaskMember`, exceto o autor do comentário) |
| Alteração relevante (status/prioridade/prazo/responsável) | `TaskService.update` | `TASK_CHANGED` | participantes da tarefa (responsável + `TaskMember`, exceto quem fez a alteração) |

Nenhum destes envia e-mail (FR-040) — apenas grava `Notification` para consulta via
`GET /api/v1/notifications` e para as contagens não lidas exibidas na UI.

### Tarefa periódica `DUE_SOON` — resumo operacional (detalhes em `research.md` #2)

- **Mecanismo**: loop `asyncio` iniciado no `lifespan` do FastAPI (`app/main.py`),
  encerrado de forma limpa (`task.cancel()` + await) no shutdown — nenhuma dependência
  nova (Celery/APScheduler) introduzida.
- **Concorrência**: cada execução adquire um advisory lock do PostgreSQL antes de
  processar; se não obtiver o lock (outra instância já está processando), pula a
  execução silenciosamente (log `DEBUG`).
- **Idempotência**: usa `Task.due_soon_notified_for` (ver `data-model.md`) como chave
  lógica de deduplicação — uma tarefa só recebe uma nova notificação `DUE_SOON` quando
  esse campo ainda não reflete o `due_date` atual; resetado a `NULL` sempre que
  `due_date` muda (via `PATCH /tasks/{task_id}`).
- **Janela de detecção**: `due_date` dentro de `DUE_SOON_WINDOW_HOURS` (default 24h) à
  frente, calculado na timezone `APP_TIMEZONE` (`research.md` #9) — cobre tanto
  "vencendo hoje" quanto tarefas já atrasadas e ainda não notificadas.
- **Falhas**: cada execução é isolada em `try/except`; uma exceção não interrompe as
  próximas execuções (log `ERROR` com contexto, sem dados sensíveis).
- **Teste**: cobertura via chamada direta a
  `NotificationService.generate_due_soon_notifications()` em testes de integração com
  tempo de referência controlado — não é necessário aguardar o intervalo real do loop
  em nenhum teste.
