# Data Model: TaskFlow MVP

**Feature**: `001-taskflow-mvp` | **Date**: 2026-07-10 (revisado)

Convenções de nomenclatura seguem a Constitution (Princípio IX): Models em PascalCase
singular; toda alteração de Model listada aqui exige uma migração Alembic correspondente
(Princípio VI). Nenhum SQL completo é escrito nesta fase — apenas o modelo conceitual.

> **Revisão 2**: adiciona `Task.due_soon_notified_for` (job periódico de notificação,
> `research.md` #2), índice único parcial de Owner em `WorkspaceMember` (#4 do
> refinamento), índice único funcional sobre `lower(email)` em `User` (`research.md`
> #10), tipo `TIMESTAMPTZ` explícito para todos os timestamps + `APP_TIMEZONE`
> (`research.md` #9), invariantes explícitas de tarefa pessoal, e a nova estratégia de
> migrações agrupadas (substitui a lista de 11 migrações 1-por-entidade da revisão 1).

## Enums controlados

| Enum | Valores | Usado em |
|---|---|---|
| `WorkspaceRole` | `OWNER`, `ADMIN`, `MEMBER` | `WorkspaceMember.role` |
| `TaskStatus` | `PENDING`, `IN_PROGRESS`, `DONE` | `Task.status` — conjunto fechado; não existem `CANCELLED`/`ARCHIVED` neste MVP |
| `TaskPriority` | `LOW`, `MEDIUM`, `HIGH`, `URGENT` | `Task.priority` |
| `NotificationType` | `DUE_SOON`, `NEW_COMMENT`, `TASK_CHANGED` | `Notification.type` |

Identificadores de enum em inglês (convenção de código, valor persistido e transmitido
pela API); rótulos exibidos ao usuário são localizados em português no frontend — ver
`research.md` #21 para a decisão formalizada.

## Convenção de timestamps e timezone (research.md #9)

Toda coluna de timestamp é `TIMESTAMPTZ` (armazenada em UTC pelo PostgreSQL). A
aplicação lê `APP_TIMEZONE` (default `America/Sao_Paulo`) de `core/config.py` para
qualquer cálculo de "hoje"/"atrasada"/"vencendo hoje" (dashboard, job de notificação de
prazo). `Task.due_date` permanece um campo `DATE` puro (sem componente de horário).

## Entidades

### User

Representa uma conta de acesso ao sistema (FR-001 a FR-004 — cadastro/login/rotas
protegidas/conta desativada; FR-051 a FR-054 — perfil).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | gerado pelo servidor |
| `name` | string | obrigatório |
| `email` | string | obrigatório; normalizado para lowercase no `UserService` antes de gravar |
| `password_hash` | string | obrigatório; **nunca** exposto em nenhum Schema de saída |
| `is_active` | bool | default `true`; `false` = conta desativada (FR-004, FR-043). Reconsultado a cada requisição autenticada (`research.md` #1), não apenas no login |
| `is_system_admin` | bool | default `false`; não implica nenhuma role de workspace |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | automáticos |

- **Unicidade case-insensitive (research.md #10)**: índice único funcional sobre
  `lower(email)` (não `CITEXT`) — `CREATE UNIQUE INDEX ux_users_email_lower ON users
  (lower(email))`. Aplica-se tanto a `INSERT` (cadastro) quanto a `UPDATE` (edição de
  perfil, FR-053): a constraint de banco rejeita qualquer tentativa que resulte em
  colisão de e-mail em minúsculas, independentemente de o código já normalizar antes.
- **Exclusão**: sem exclusão de conta no MVP (FR-054). Apenas `is_active` alterna.

### Workspace

Contexto que agrupa projetos, tarefas e membros (FR-012, FR-013, FR-017).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `name` | string | obrigatório |
| `description` | string (nullable) | opcional |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | automáticos |

- O Owner **não** é uma coluna direta em `Workspace` — é derivado de
  `WorkspaceMember.role == OWNER`, com exatamente um garantido pelo índice único parcial
  descrito em `WorkspaceMember` abaixo.
- **Exclusão (research.md #12, fluxo de exclusão controlada)**: hard delete, restrito ao
  Owner (FR-017), **sempre via `WorkspaceService.delete`, nunca cascade disparado sem
  preparação**. Fluxo: (1) `AttachmentService` localiza todos os anexos físicos de todas
  as tarefas do workspace; (2) autorização validada (`require_workspace_owner`); (3)
  exclusão em transação única no banco — cascade remove `Project`, `Task` (com
  `workspace_id` correspondente), `WorkspaceMember`, e transitivamente `TaskMember`/
  `Comment`/`ChecklistItem`/`Attachment`/`TaskHistoryEntry`/`Notification` ligadas a
  essas tarefas; (4) após o `commit()` bem-sucedido, os arquivos físicos coletados no
  passo 1 são removidos do disco; (5) falha ao remover um arquivo físico é registrada
  via log `ERROR` (caminho, `attachment_id`, `task_id`) para reconciliação manual, sem
  falhar a resposta da API (o banco já está correto).

### WorkspaceMember

Associação usuário-workspace com role (FR-013 a FR-025).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `workspace_id` | UUID (FK → Workspace, `ON DELETE CASCADE`) | obrigatório |
| `user_id` | UUID (FK → User, `ON DELETE CASCADE`) | obrigatório |
| `role` | `WorkspaceRole` | obrigatório |
| `created_at` | `TIMESTAMPTZ` | automático |

- **Unicidade**: constraint `UNIQUE(workspace_id, user_id)` — impede associação
  duplicada.
- **Owner único, garantido em dois níveis (refinamento #4)**:
  1. **Índice único parcial no PostgreSQL** (garantia de banco, à prova de condição de
     corrida): `CREATE UNIQUE INDEX ux_workspace_members_one_owner ON
     workspace_members (workspace_id) WHERE role = 'OWNER'`. Isso torna
     **estruturalmente impossível** existir duas linhas com `role = OWNER` para o mesmo
     `workspace_id`, mesmo sob concorrência — qualquer segunda tentativa de `INSERT`/
     `UPDATE` que violasse isso falha no banco com `IntegrityError`, capturada pelo
     Service e traduzida para o erro padronizado (`409`).
  2. **Operação transacional com bloqueio pessimista no Service**
     (`WorkspaceMemberService.transfer_ownership`, detalhado em `research.md` #20):
     dentro da transação, trava a linha do Owner atual e a do membro-alvo via
     `SELECT ... FOR UPDATE`, reconfirma que `current_user` ainda é o Owner sob o lock,
     e só então rebaixa o Owner atual para `ADMIN` e promove o novo Owner, com
     `commit()` único. O `SELECT ... FOR UPDATE` serializa transferências concorrentes
     no mesmo workspace (uma segunda transação bloqueia até a primeira concluir, e ao
     ser liberada recebe zero linhas se o Owner já mudou, respondendo `409`). Se
     qualquer etapa falhar (incluindo a violação do índice único acima), a transação
     inteira sofre `rollback()` — nenhum estado parcial (dois Owners, ou zero Owners) é
     persistido.
  3. Remover o Owner atual (`DELETE /workspaces/{id}/members/{user_id}` sobre o próprio
     Owner) é bloqueado na camada de Service **antes** de chegar ao banco (FR-019) —
     a única forma de o Owner deixar de sê-lo é `transfer_ownership`.
- **Índice**: `(workspace_id)` e `(user_id)` para consultas de listagem/autorização
  frequentes (além do índice parcial de Owner acima).

### Project

Agrupamento de tarefas dentro de um workspace (FR-020, FR-026).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `workspace_id` | UUID (FK → Workspace, `ON DELETE CASCADE`) | obrigatório |
| `name` | string | obrigatório |
| `description` | string (nullable) | opcional |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | automáticos |

- Criação, edição e exclusão restritas a Owner/Admin do workspace (FR-020; refinamento
  #7 — Member apenas visualiza).
- **Exclusão (refinamento #6)**: **não** é um simples `ON DELETE CASCADE` sobre `Task`.
  A FK `Task.project_id` usa `ON DELETE SET NULL` (constraint de banco, mantida), mas a
  exclusão de um projeto MUST sempre passar por `ProjectService.delete`, que: (1)
  valida autorização (Owner/Admin); (2) executa o `DELETE` do projeto em transação —
  o `ON DELETE SET NULL` do banco cuida de desvincular as tarefas automaticamente na
  mesma transação; (3) registra um log estruturado (`INFO`) com o projeto excluído, o
  workspace, o autor da ação e a quantidade de tarefas desvinculadas. As tarefas
  **permanecem** no workspace (com `project_id = NULL`, tornando-se tarefas
  colaborativas diretamente no workspace) — comentários, checklists, anexos, histórico
  e participantes dessas tarefas permanecem intactos, pois nenhuma `Task` é removida.
  Esta exclusão **não** gera uma `TaskHistoryEntry` por tarefa afetada — o histórico de
  tarefa (FR-041) cobre apenas status/prioridade/prazo/responsável (spec Assumptions);
  desvinculação de projeto é registrada apenas no log de aplicação, não como entrada de
  histórico de tarefa (evita expandir o escopo de FR-041 sem uma decisão de produto
  explícita — sinalizado no resumo final).
- **Índice**: `(workspace_id)`.

### Task

Unidade de trabalho, pessoal ou de projeto (FR-005 a FR-011, FR-021, FR-024, FR-025).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `title` | string | obrigatório |
| `description` | string (nullable) | opcional |
| `status` | `TaskStatus` | obrigatório, default `PENDING` |
| `priority` | `TaskPriority` | obrigatório, default `MEDIUM` |
| `due_date` | `DATE` (nullable) | opcional — sem componente de horário (research.md #9) |
| `assignee_id` | UUID (FK → User, `ON DELETE RESTRICT`) | obrigatório — toda tarefa tem exatamente um responsável (FR-006) |
| `creator_id` | UUID (FK → User, `ON DELETE RESTRICT`) | obrigatório |
| `workspace_id` | UUID (FK → Workspace, `ON DELETE CASCADE`, nullable) | opcional (FR-007) |
| `project_id` | UUID (FK → Project, `ON DELETE SET NULL`, nullable) | opcional (FR-008) |
| `completed_at` | `TIMESTAMPTZ` (nullable) | preenchido quando `status` muda para `DONE`; limpo se reaberta |
| `due_soon_notified_for` | `DATE` (nullable) | **novo** — valor de `due_date` para o qual a notificação `DUE_SOON` já foi gerada (idempotência do job periódico, `research.md` #2). `NULL` enquanto `due_date IS NULL`; resetado para `NULL` sempre que `due_date` é alterado; tarefas `DONE` nunca são selecionadas pelo job, independentemente deste campo. Ver tabela completa de regras em `research.md` #2 |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | automáticos |

#### Invariantes de tarefa pessoal (refinamento #3)

Uma tarefa é **pessoal** se e somente se `workspace_id IS NULL`. Nesse caso, MUST valer:

| Invariante | Onde é aplicada |
|---|---|
| `project_id IS NULL` (consequência de FR-008 — projeto sempre implica workspace) | Schema (`TaskCreate`/`TaskUpdate`: rejeita `project_id` sem `workspace_id`) + Service |
| `assignee_id == creator_id` | Service (`TaskService.create` força o default e rejeita valor diferente); não expressável como `CHECK` simples porque depende de `workspace_id IS NULL`, então validado em código, não em constraint de banco |
| Nenhum `TaskMember` associado | Service (`TaskMemberService` rejeita criação se `Task.workspace_id IS NULL` — FR-031) + Repository (query de participantes de tarefa pessoal sempre retorna apenas o criador) |
| Visível apenas ao criador | Repository — toda consulta de listagem/detalhe filtra `Task.creator_id == current_user.id` quando `workspace_id IS NULL` |
| Editável apenas pelo criador (inclui concluir/excluir) | Service — `require_task_editor`/`require_task_delete` (ver `plan.md`) tratam tarefa pessoal como caso especial: somente `creator_id == current_user.id` |
| `assignee_id` MUST NOT ser alterado para outro usuário enquanto `workspace_id IS NULL` | Service (`TaskService.update` rejeita `assignee_id != creator_id` se a tarefa continua pessoal) |
| Sem comentários/checklist/anexos de terceiros | Consequência direta de "visível apenas ao criador" — se ninguém além do criador enxerga a tarefa, ninguém além dele pode colaborar nela. Reforçado explicitamente em `require_task_participant` (trata tarefa pessoal como participante único = criador) |
| Pode virar colaborativa ao receber `workspace_id` (e opcionalmente `project_id`) | Service — `TaskService.update` permite a transição, validando as mesmas regras de criação de tarefa de workspace (assignee deve ser membro do workspace de destino) nesse momento |

Testes de integração dedicados MUST cobrir cada linha da tabela acima (ver seção de
Testes em `plan.md`).

- **`ON DELETE RESTRICT` em `assignee_id`/`creator_id`**: reforça em nível de banco que
  um `User` não pode ser removido enquanto referenciado — a remoção de conta não existe
  no MVP, mas a constraint documenta a invariante.
- **Constraint de consistência workspace/projeto (FR-008)**: se `project_id` não é
  nulo, `workspace_id` MUST ser igual ao `workspace_id` do projeto referenciado.
  Validado no `TaskService` antes de persistir; coberto por teste de integração
  dedicado.
- **"Tarefa ativa"** (FR-024): `status != DONE`. Expressão reutilizada no
  `TaskRepository`.
- **"Atrasada"/"vencendo hoje"** (FR-011, FR-047): calculados por comparação de
  `due_date` com a data atual **na timezone `APP_TIMEZONE`** (research.md #9), nunca
  armazenados.
- **Índices**: `(assignee_id)`, `(workspace_id)`, `(project_id)`, `(status)`,
  `(due_date)` — suportam os filtros/ordenação de FR-055 a FR-058, o dashboard, e a
  consulta do job periódico de `DUE_SOON` (filtro adicional por `due_soon_notified_for`,
  também indexado).

### TaskMember

Participante de uma tarefa de workspace, além do responsável (FR-030 a FR-034).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `task_id` | UUID (FK → Task, `ON DELETE CASCADE`) | obrigatório |
| `user_id` | UUID (FK → User, `ON DELETE CASCADE`) | obrigatório |
| `created_at` | `TIMESTAMPTZ` | automático |

- **Unicidade**: constraint `UNIQUE(task_id, user_id)`.
- **Regra de negócio (Service)**: só pode existir se `Task.workspace_id` não for nulo
  (FR-030/FR-031, invariante de tarefa pessoal); `user_id` MUST ser membro do mesmo
  workspace da tarefa (FR-032).
- **Quem pode adicionar/remover (refinamento #7)**: criador da tarefa, responsável
  (`assignee`), ou Owner/Admin do workspace — **não** qualquer membro com visibilidade
  da tarefa (ver "Visibilidade versus participação", `research.md` #8).
- **Remoção do responsável**: `assignee_id` MUST NOT ser removido da lista de
  participantes por esta via — remover o responsável como participante só é possível
  reatribuindo a responsabilidade da tarefa primeiro (`PATCH /tasks/{id}` com novo
  `assignee_id`); tentar via `DELETE /tasks/{id}/members/{assignee_id}` diretamente
  retorna `400`.
- O responsável (`assignee`) é tratado como participante implícito nas consultas de
  listagem (união `assignee` + registros de `TaskMember`), sem precisar de um registro
  próprio.

### Comment

Comunicação em torno de uma tarefa (FR-027 a FR-029). **Fora do MVP**: edição e
exclusão de comentários (refinamento #7) — apenas criação e listagem.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `task_id` | UUID (FK → Task, `ON DELETE CASCADE`) | obrigatório |
| `author_id` | UUID (FK → User, `ON DELETE RESTRICT`) | obrigatório |
| `content` | text | obrigatório, `CHECK (length(trim(content)) > 0)` a nível de banco **e** validação no Schema (FR-029) |
| `created_at` | `TIMESTAMPTZ` | automático |

- **Quem pode criar (refinamento #8 — colaboração, não apenas visibilidade)**: apenas
  responsável e participantes explícitos da tarefa (ou o criador, no caso de tarefa
  pessoal) — não qualquer membro do workspace com visibilidade da tarefa.
- **Índice**: `(task_id, created_at)`.

### ChecklistItem

Passo menor dentro de uma tarefa (FR-035, FR-036). **Fora do MVP**: edição textual
separada do fluxo de criação/marcação (refinamento #7 — apenas criar, marcar concluído/
pendente, remover).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `task_id` | UUID (FK → Task, `ON DELETE CASCADE`) | obrigatório |
| `description` | string | obrigatório |
| `is_done` | bool | default `false` |
| `completed_at` | `TIMESTAMPTZ` (nullable) | preenchido quando `is_done` vira `true` |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | automáticos |

- **Quem pode criar/marcar/remover**: mesma regra de colaboração de `Comment` acima —
  responsável e participantes explícitos (ou criador, se pessoal).
- **Índice**: `(task_id)`.

### Attachment

Arquivo vinculado a uma tarefa (FR-037, FR-038). **Fora do MVP**: substituição de
arquivo (refinamento #7).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `task_id` | UUID (FK → Task, `ON DELETE CASCADE`) | obrigatório |
| `uploaded_by_id` | UUID (FK → User, `ON DELETE RESTRICT`) | obrigatório |
| `original_filename` | string | nome informado pelo usuário (exibição apenas) |
| `storage_path` | string | caminho/identificador interno gerado pelo servidor (UUID-based) |
| `content_type` | string | validado contra lista de tipos permitidos (config) |
| `size_bytes` | integer | validado contra tamanho máximo (config) |
| `created_at` | `TIMESTAMPTZ` | automático |

- **Quem pode enviar**: responsável e participantes explícitos (ou criador, se
  pessoal) — mesma regra de colaboração.
- **Quem pode remover (refinamento #7)**: quem enviou o anexo (`uploaded_by_id`), **ou**
  Owner/Admin do workspace da tarefa (permissão administrativa, independente de ser
  participante — ver `research.md` #8).
- **Exclusão controlada (research.md #12)**: seguir o fluxo de "localizar → autorizar →
  excluir registro (transação) → remover arquivo físico após commit → logar falha sem
  falhar a resposta", descrito em `Workspace` acima e detalhado em `plan.md`.
- **Índice**: `(task_id)`.

### TaskHistoryEntry

Registro de alteração relevante em uma tarefa (FR-041).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `task_id` | UUID (FK → Task, `ON DELETE CASCADE`) | obrigatório |
| `changed_by_id` | UUID (FK → User, `ON DELETE RESTRICT`) | obrigatório |
| `field_changed` | string | um de: `status`, `priority`, `due_date`, `assignee_id` |
| `old_value` | string (nullable) | representação textual do valor anterior |
| `new_value` | string (nullable) | representação textual do novo valor |
| `changed_at` | `TIMESTAMPTZ` | automático |

- Somente os quatro campos listados geram histórico. Desvinculação de projeto (ver
  `Project`, acima) **não** gera entrada aqui — apenas log de aplicação.
- **Índice**: `(task_id, changed_at)`.
- Escrita sempre dentro da mesma transação da alteração principal.

### Notification

Aviso a um usuário sobre um evento relevante (FR-039, FR-040).

| Campo | Tipo | Regras |
|---|---|---|
| `id` | UUID (PK) | |
| `recipient_id` | UUID (FK → User, `ON DELETE CASCADE`) | obrigatório |
| `task_id` | UUID (FK → Task, `ON DELETE CASCADE`, nullable) | opcional |
| `type` | `NotificationType` | obrigatório |
| `title` | string | obrigatório |
| `message` | string | obrigatório |
| `is_read` | bool | default `false` |
| `created_at` | `TIMESTAMPTZ` | automático |

- **Deduplicação de `DUE_SOON` (revisão 2)**: garantida pela chave lógica
  `Task.due_soon_notified_for` (ver campo em `Task`, acima), não por uma constraint na
  própria tabela `Notification` — o job periódico só cria uma nova `Notification` do
  tipo `DUE_SOON` quando `due_soon_notified_for` ainda não reflete o `due_date` atual da
  tarefa, e atualiza esse campo na mesma transação da criação da notificação.
- **Índice**: `(recipient_id, is_read, created_at)`.

## Diagrama de relacionamentos (conceitual)

```text
User ──< WorkspaceMember >── Workspace ──< Project ──< Task
User ──(assignee/creator)──< Task
Workspace ──< Task (opcional, direto — tarefa sem projeto)
Task ──< TaskMember >── User
Task ──< Comment >── User (author)
Task ──< ChecklistItem
Task ──< Attachment >── User (uploaded_by)
Task ──< TaskHistoryEntry >── User (changed_by)
User ──< Notification (recipient) >── Task (opcional)
```

## Estratégia de Migrações Alembic (revisão 2 — agrupada por domínio)

A revisão 1 deste documento propunha uma migração por entidade (11 migrações). Não há
exigência de uma migração por tabela — o refinamento adota o agrupamento abaixo,
preservando ordem de dependência de FK, clareza e reversibilidade (cada migração
agrupada continua com `downgrade()` completo e independente):

1. **`0001_foundation_users`**
   - Tabela `users` (incluindo `is_active`, `is_system_admin`).
   - Índice único funcional `ux_users_email_lower` sobre `lower(email)` (research.md
     #10).

2. **`0002_workspaces_and_projects`**
   - Tabelas `workspaces`, `workspace_members` (incluindo o índice único parcial
     `ux_workspace_members_one_owner` — refinamento #4), `projects`.

3. **`0003_tasks_and_collaboration`**
   - Tabela `tasks` (incluindo `due_soon_notified_for`), `task_members`, `comments`,
     `checklist_items`, `attachments`. Agrupadas juntas por dependerem todas
     diretamente de `tasks` e serem introduzidas como uma unidade coesa de domínio
     ("colaboração em torno de uma tarefa").

4. **`0004_history_and_notifications`**
   - Tabelas `task_history_entries`, `notifications`.

**Justificativa do agrupamento**: cada migração corresponde a um marco coeso e
testável do domínio (fundação de usuários → estrutura organizacional → núcleo
operacional de tarefas e colaboração → rastreabilidade/engajamento), reduzindo o número
de arquivos de migração a manter sem perder clareza sobre o que cada uma introduz — e
mantendo rastreabilidade (cada migração é revertível isoladamente, na ordem inversa).
Caso um refinamento futuro precise adicionar uma tabela nova a um domínio já migrado
(ex.: uma tabela adicional de colaboração), a prática é uma nova migração incremental
(ex.: `0005_...`), nunca editar uma migração já aplicada.
