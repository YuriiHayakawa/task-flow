# Research: Membros de Projeto (Visibilidade Restrita por Convite)

Decisões técnicas tomadas a partir da leitura do código real de `001-taskflow-mvp` (não do zero) —
cada uma resolve um ponto que o `spec.md` deixa como requisito de negócio, mas não como implementação.

## #1 — Modelo de dados de `ProjectMember`

**Decisão**: tabela própria `project_members` (`id`, `project_id`, `user_id`, `created_at`), com
`UniqueConstraint(project_id, user_id)` e `Index` em `user_id` — mesma estrutura de
`workspace_members` (`app/models/workspace_member.py`), **sem** a coluna `role` e **sem** o índice
único parcial de "um Owner só" (não existe Owner de projeto).

**Alternativas consideradas**: reaproveitar `TaskMember` (já existe, para participantes de tarefa) —
rejeitado porque representa uma relação diferente (pessoa ↔ tarefa, não pessoa ↔ projeto) e misturaria
dois conceitos de "participação" com regras de negócio distintas (research.md #6 de
`001-taskflow-mvp`, "Colaboração" vs. Autorização).

## #2 — Onde a decisão de "quem acessa qual projeto" é calculada

**Decisão**: em memória, no Service, nunca delegada ao schema/frontend (Constitution IV). Dois
conjuntos de IDs resolvem qualquer checagem desta feature:

- `owner_workspace_ids`: workspaces onde o usuário atual é `OWNER` (novo método
  `WorkspaceMemberRepository.list_owned_workspace_ids_for_user`, variante filtrada do já existente
  `list_workspace_ids_for_user`).
- `member_project_ids`: projetos onde existe um `ProjectMember` explícito para o usuário atual (novo
  método `ProjectMemberRepository.list_project_ids_for_user`).

Um projeto `P` do workspace `W` é acessível ao usuário quando: `W ∈ owner_workspace_ids` **ou**
`P ∈ member_project_ids`. Essa expressão de 2 conjuntos é reaproveitada em todo ponto de enforcement
(#3), nunca recalculada de formas diferentes em lugares diferentes.

## #3 — Superfície completa de enforcement (todos os pontos que hoje ignoram membership de projeto)

Levantamento feito lendo o código atual (não presumido) — 6 pontos precisam mudar:

1. **`ProjectService.list_by_workspace`** — hoje devolve todos os projetos do workspace para
   qualquer role. Passa a ramificar: `OWNER`/`ADMIN` → todos (FR-006, Admin também vê a lista);
   `MEMBER` → só os de `member_project_ids`.
2. **`ProjectService.get_by_id_or_404`** — hoje só confere membership de *workspace*. Passa a exigir
   também acesso ao projeto (fórmula do #2) — usada por `GET/PATCH/DELETE /projects/{id}`.
3. **`TaskRepository.search` e `count_by_status`** — a cláusula `visible` compartilhada por elas
   (`GET /tasks`, incl. `?project_id=`, e as contagens do Dashboard) hoje só considera
   `workspace_id ∈ workspace_ids`, sem olhar `project_id` nenhuma vez. Uma tarefa de um projeto
   restrito continuaria aparecendo para qualquer membro do workspace via estas duas consultas —
   contorna a restrição inteira se não for corrigido. Nova cláusula (ver `data-model.md`): tarefa sem
   `project_id` continua com a regra atual; tarefa com `project_id` exige também a fórmula do #2.
4. **`require_task_visible`** (`app/dependencies/task_authorization.py`) — mesmo problema do #3, mas
   para `GET /tasks/{id}` (uma tarefa isolada, ex.: abrir `TaskDetailPage` direto por link). Mesma
   fórmula.
5. **Validação de `assignee_id`** (`TaskService._resolve_workspace_assignee` na criação,
   `TaskService.update` na reatribuição) — hoje só confirmam membership de *workspace*. Passam a
   também exigir membership de *projeto* quando a tarefa tem `project_id` (FR-009).
6. **`ProjectService.create`** — hoje não recebe `creator_id` nenhum (a rota descarta
   `current_user`); precisa passar a receber e, na mesma transação, criar o `ProjectMember` do criador
   (FR-003) — mesmo padrão de `WorkspaceService.create` criando o `WorkspaceMember(OWNER)` do criador.

## #4 — Migração de projetos já existentes (FR-012)

**Decisão**: um único `op.execute("INSERT INTO project_members (...) SELECT ... FROM projects p JOIN
workspace_members wm ON wm.workspace_id = p.workspace_id")`, dentro da própria migração Alembic que
cria a tabela `project_members` — evento único, não um script/comando separado. Mesmo mecanismo
(`op.execute` com SQL bruto) já usado em `0002_workspaces_and_projects.py` para o índice único parcial
de Owner — não é um padrão novo introduzido sem precedente no projeto.

**Alternativas consideradas**: script de backfill em Python separado, rodado manualmente — rejeitado
por criar uma etapa de deploy manual fora do fluxo padrão (`alembic upgrade head`) já usado para as 5
migrações anteriores.

## #5 — Nova dependency de autorização para rotas de projeto sem `workspace_id` no path

**Decisão**: novo arquivo `app/dependencies/project_authorization.py` (mesmo motivo de
`task_authorization.py` existir separado de `authorization.py`: rotas `/projects/{id}/...` não têm
`workspace_id` no path para reaproveitar `require_workspace_member` diretamente).

- `require_project_visible(project_id, current_user, db) -> Project`: aplica a fórmula do #2; `404`
  (nunca `403`) para quem não tem acesso — mesma convenção de segurança de `require_task_visible`
  (nunca confirma a um usuário sem acesso que o projeto existe).
- `require_project_manage(project: Project = Depends(require_project_visible), ...) -> Project`: além
  de já exigir acesso (herdado), exige role `OWNER`/`ADMIN` no workspace do projeto. Cobre, com a
  MESMA dependency, tanto editar/excluir o projeto quanto gerenciar sua lista de membros — como
  `require_project_visible` já garante "Owner OU membro explícito", um Admin que não é membro do
  projeto nunca chega a esta segunda checagem (recebe `404` antes), implementando FR-004 (Admin só
  gerencia projeto do qual já participa) sem nenhum caso especial adicional.

## #6 — Frontend: Admin vê o projeto na listagem mas pode não conseguir abri-lo

**Decisão**: `ProjectRead` ganha um campo `is_member: bool`, calculado explicitamente pelo Service
(nunca via `from_attributes` direto) — mesmo padrão já usado por `WorkspaceRead.my_role`
(`app/schemas/workspace.py`). O frontend usa esse campo para renderizar um projeto que aparece na
lista mas `is_member = false` (só acontece para Admin, por FR-006) como visualmente bloqueado
(ex.: cadeado, cartão esmaecido, sem navegação ao clicar) — em vez de deixar o usuário navegar e
esbarrar num `404` inesperado.

## #7 — Frontend: seletor de responsável precisa respeitar membership de projeto

**Decisão**: `TaskFormPage.tsx` hoje sempre popula o `<Select>` de responsável com
`useWorkspaceMembers(workspaceId)` (todos os membros do workspace), independente de projeto
selecionado. Novo hook `useProjectMembers(projectId)` (mesmo padrão de `useWorkspaceMembers`); quando
a tarefa tem um projeto selecionado, o seletor passa a listar os membros desse projeto em vez dos
membros do workspace inteiro — reflete no frontend a mesma regra já aplicada no backend (#3.5).

## #8 — Frontend: onde gerenciar membros de um projeto

**Decisão**: um `Sheet` disparado a partir do herói de `ProjectDetailPage` (botão "Membros", visível
só para quem pode gerenciar — mesma condição `canManage` que já controla Editar/Excluir do projeto
hoje) — não uma página dedicada. Justificativa: ao contrário de Workspace Members (que tem roles,
promoção, rebaixamento, transferência de titularidade — motivos reais para ser uma página cheia),
Membro de Projeto é uma lista flat (dentro ou fora) — listar, adicionar por e-mail, remover é
suficiente num painel lateral, mesmo padrão já usado para o formulário de criar/editar em outras
telas do app.
