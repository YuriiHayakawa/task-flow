# Contracts: Projects, Tasks & Task Members

Ver convenções gerais em [`_conventions.md`](./_conventions.md), especialmente a seção
"Visibilidade versus participação" (`require_workspace_member`, `require_task_participant`,
`require_task_editor`, `require_task_delete`).
Cobre módulos: **Projects**, **Tasks**, **Task Members**, e a superfície de
**Search/Filters/Ordering** (aplicada em `GET /tasks`).
Requisitos relacionados: FR-006 a FR-011 (regras centrais de Task), FR-018 a FR-026
(Projects e permissões de workspace aplicadas a Projects/Tasks), FR-030 a FR-034 (Task
Members), FR-055 a FR-059 (Search/Filters/Ordering).

## Projects

### `POST /api/v1/workspaces/{workspace_id}/projects`

- **Auth**: `require_workspace_admin_or_owner` (FR-020 — Members MUST NOT criar
  projetos).
- **Body** (`ProjectCreate`): `name`, `description?`.
- **Respostas**: `201` (`ProjectRead`) · `403` (Member) · `404` (não é membro do
  workspace).

### `GET /api/v1/workspaces/{workspace_id}/projects`

- **Auth**: `require_workspace_member` (qualquer role — visibilidade, não colaboração).
- **Respostas**: `200` (lista paginada de `ProjectRead`).

### `GET /api/v1/projects/{project_id}`

- **Auth**: `require_workspace_member` do workspace ao qual o projeto pertence.
- **Respostas**: `200` (`ProjectRead`) · `404`.

### `PATCH /api/v1/projects/{project_id}`

- **Auth**: `require_workspace_admin_or_owner` do workspace do projeto (refinamento #7 —
  Member MUST NOT editar projeto, mesmo o que ele mesmo não criou nenhuma exceção).
- **Respostas**: `200` (`ProjectRead`) · `403` · `404`.

### `DELETE /api/v1/projects/{project_id}`

- **Auth**: `require_workspace_admin_or_owner` do workspace do projeto (refinamento #7).
- **Regras (refinamento #6 — exclusão de projeto preserva tarefas)**: a exclusão MUST
  passar por `ProjectService.delete`, nunca por cascade direto sem preparação:
  1. Valida autorização (Owner/Admin).
  2. Executa a exclusão do projeto em uma transação — a constraint de banco
     `Task.project_id` com `ON DELETE SET NULL` desvincula automaticamente todas as
     tarefas desse projeto na mesma transação (elas **não** são excluídas).
  3. As tarefas desvinculadas permanecem no mesmo `workspace_id`, agora como tarefas
     colaborativas diretas do workspace (sem projeto) — comentários, checklists,
     anexos, histórico e participantes dessas tarefas permanecem intactos.
  4. Registra um log estruturado (`INFO`): projeto excluído, workspace, autor da ação,
     quantidade de tarefas desvinculadas. **Não** gera `TaskHistoryEntry` por tarefa
     (fora do conjunto de campos rastreados por FR-041 — ver `data-model.md`).
- **Acceptance técnico**: dado um projeto com 3 tarefas, ao excluí-lo, as 3 tarefas
  continuam existindo, visíveis na listagem geral do workspace (`GET /tasks` filtrando
  por `workspace_id`), agora com `project_id = null`.
- **Respostas**: `204` · `403` · `404`.

## Tasks

### `POST /api/v1/tasks`

- **Auth**: usuário autenticado.
- **Body** (`TaskCreate`): `title`, `description?`, `status?` (default `PENDING`),
  `priority?` (default `MEDIUM`), `due_date?`, `assignee_id?` (default: o próprio
  criador), `workspace_id?`, `project_id?`.
- **Regras de negócio (validadas no `TaskService`, não apenas no schema)**:
  - Se `project_id` informado e `workspace_id` ausente → `workspace_id` MUST ser
    derivado do projeto (FR-008). Se o `project_id` informado não corresponder a
    nenhum projeto existente, a resposta MUST ser `403` — **o mesmo código usado para
    "criador não é membro do workspace"**, nunca `404`: este endpoint não distingue
    "projeto inexistente" de "projeto existente mas inacessível ao chamador", pela
    mesma razão pela qual `workspace_id` inexistente já usa `403` em vez de `404`
    abaixo — o identificador foi fornecido pelo próprio chamador no corpo da
    requisição (não inferido de um path de recurso aninhado), então não há ganho de
    segurança em diferenciar as duas causas, e uma resposta uniforme evita que o
    chamador confirme a existência de um `project_id` que não pode acessar.
  - Se `project_id` informado e `workspace_id` também informado → MUST coincidir com o
    workspace do projeto, senão `400`.
  - Se `workspace_id` informado → o criador MUST ser membro desse workspace (`403`
    caso contrário — inclui tanto "workspace inexistente" quanto "workspace existe mas
    não sou membro", sem distinção, mesma justificativa do `project_id` acima);
    `assignee_id` (se informado) MUST ser membro do mesmo workspace (`400` caso
    contrário — inclui tanto "usuário inexistente" quanto "usuário existente mas não
    membro", sem distinção).
  - **Se nem `workspace_id` nem `project_id` informados → tarefa pessoal (invariantes
    completas em `data-model.md`)**: `assignee_id`, se informado, MUST ser igual ao
    `creator_id` — enviar um `assignee_id` diferente do próprio usuário para uma tarefa
    sem `workspace_id` retorna `400`. `project_id` MUST estar ausente (uma tarefa nunca
    é criada com projeto e sem workspace).
- **Respostas**: `201` (`TaskRead`) · `400` (inconsistência workspace/projeto, assignee
  fora do workspace, ou tentativa de atribuir tarefa pessoal a terceiro) · `403`
  (não-membro tentando criar no workspace, workspace inexistente, projeto inexistente,
  ou projeto inacessível) · `422`.

### `GET /api/v1/tasks`

Endpoint central de listagem — cobre tarefas pessoais e de todos os workspaces do
usuário, com busca/filtros/ordenação (US8).

- **Auth**: usuário autenticado.
- **Regras de visibilidade**: retorna união de (a) tarefas pessoais **do próprio
  usuário** (`creator_id = current_user.id AND workspace_id IS NULL` — nunca tarefas
  pessoais de terceiros, FR-059) e (b) tarefas de todos os workspaces dos quais o
  usuário é membro (qualquer role — visibilidade ampla, `research.md` #8).
- **Query params**: `search` (título, FR-055), `status`, `priority`, `workspace_id`,
  `project_id`, `assignee_id` (combináveis, FR-056/057), `sort_by` ∈ `due_date` |
  `priority` | `created_at` (default `created_at`), `sort_order` ∈ `asc` | `desc`
  (default `desc`), paginação padrão.
- **Respostas**: `200` (lista paginada de `TaskRead`) — resultado vazio é `200` com
  `items: []`.

### `GET /api/v1/tasks/{task_id}`

- **Auth**: `require_workspace_member` do workspace da tarefa, **ou** o próprio criador
  se a tarefa for pessoal (visibilidade — não exige ser participante explícito).
- **Respostas**: `200` (`TaskRead` — inclui `assignee`, `workspace_id`, `project_id`,
  contadores de comentários/checklist/anexos) · `404`.

### `PATCH /api/v1/tasks/{task_id}` — edição de "dados operacionais"

**Dados operacionais** (refinamento #7): `title`, `description`, `status`, `priority`,
`due_date`, `assignee_id`, `project_id`. Todo o corpo de `TaskUpdate` é composto
exclusivamente por esses campos (opcionais).

- **Auth — `require_task_editor`**:
  - **Tarefa pessoal**: somente o criador (`creator_id == current_user.id`).
  - **Tarefa de workspace**: o **criador**, o **responsável** (`assignee_id`), **ou**
    Owner/Admin do workspace da tarefa. Um Member do workspace que não seja criador nem
    responsável **MUST NOT** editar (nem mesmo campos considerados "menores" — não há
    edição parcial permitida a quem não tem uma das três posições acima).
- **Regras adicionais**:
  - Alterar `assignee_id` MUST validar que o novo responsável é membro do mesmo
    workspace da tarefa; para tarefa pessoal, `assignee_id` MUST permanecer igual a
    `creator_id` (não pode ser alterado para outro usuário enquanto a tarefa continuar
    sem `workspace_id` — invariante de tarefa pessoal).
  - Alterar `workspace_id`/`project_id` para **adicionar** um workspace a uma tarefa até
    então pessoal é a via oficial de conversão para tarefa colaborativa (invariante de
    tarefa pessoal, `data-model.md`) — nesse momento, as mesmas validações de criação de
    tarefa de workspace se aplicam (assignee deve ser membro do workspace de destino).
    Remover o `workspace_id` de uma tarefa já colaborativa (torná-la pessoal novamente)
    **não é suportado neste MVP** (`400` se tentado) — não há requisito da spec para
    essa conversão inversa.
  - Alterar `project_id` isoladamente (sem alterar `workspace_id`) MUST validar que o
    novo projeto pertence ao mesmo workspace já associado à tarefa (mesma regra de
    FR-008 aplicada em criação).
  - Qualquer alteração em `status`, `priority`, `due_date` ou `assignee_id` MUST
    disparar, na mesma transação: criação de `TaskHistoryEntry` (FR-041) e, quando
    aplicável, `Notification` para os participantes afetados (FR-039) — ver
    `research.md` #19 (transação única).
  - `status = DONE` → preenche `completed_at`; reabrir → limpa `completed_at`.
  - Alterar `due_date` MUST resetar `Task.due_soon_notified_for` para `NULL` na mesma
    transação (permite nova notificação `DUE_SOON` para o novo prazo — `research.md`
    #2).
- **Respostas**: `200` (`TaskRead`) · `400` (assignee fora do workspace, conversão de
  pessoal para outro responsável, remoção de workspace) · `403` (Member sem ser
  criador/responsável) · `404`.

### `DELETE /api/v1/tasks/{task_id}`

- **Auth — `require_task_delete`** (refinamento #7 — mais restrito que a edição: o
  **responsável sozinho, se não for também o criador, MUST NOT excluir**):
  - **Tarefa pessoal**: somente o criador.
  - **Tarefa de workspace**: o **criador** da tarefa, **ou** Owner/Admin do workspace.
- **Regras**: cascade remove `TaskMember`, `Comment`, `ChecklistItem`, `Attachment`
  (fluxo de exclusão controlada — localizar anexos físicos, autorizar, excluir
  registros em transação, remover arquivos físicos após commit, logar falhas — ver
  `research.md` #12 e `data-model.md`), `TaskHistoryEntry`, `Notification`
  relacionadas.
- **Respostas**: `204` · `403` (responsável não-criador, ou Member comum, tentando
  excluir) · `404`.

## Task Members (participantes — US5)

### `GET /api/v1/tasks/{task_id}/members`

- **Auth**: `require_workspace_member` (visibilidade — qualquer membro do workspace
  pode ver quem participa, mesmo sem participar).
- **Respostas**: `200` (lista de `TaskMemberRead`, **incluindo o responsável** como
  participante implícito — FR-033).

### `POST /api/v1/tasks/{task_id}/members`

- **Auth — `require_task_editor`** (refinamento #7 — criador, responsável, ou
  Owner/Admin do workspace; **não** qualquer participante existente, e **não** qualquer
  membro com mera visibilidade).
- **Body**: `{ "user_id": "..." }`.
- **Regras**: `400` se a tarefa é pessoal (FR-031); `400` se `user_id` não é membro do
  workspace da tarefa (FR-032); `409` se já é participante.
- **Respostas**: `201` (`TaskMemberRead`) · `400` · `403` · `404` · `409`.

### `DELETE /api/v1/tasks/{task_id}/members/{user_id}`

- **Auth — `require_task_editor`** (mesma regra de `POST`, acima).
- **Regras**: remover participante MUST NOT apagar `Comment`/`Attachment`/
  `TaskHistoryEntry` existentes (FR-034). Remover o `assignee_id` por esta rota **MUST
  NOT** ser permitido — o responsável só muda via `PATCH /tasks/{task_id}` com novo
  `assignee_id` (que, por sua vez, reatribui a responsabilidade antes de qualquer
  remoção — nunca deixando a tarefa sem responsável). Tentativa de
  `DELETE .../members/{assignee_id}` retorna `400`.
- **Respostas**: `204` · `400` · `403` · `404`.
