# Data Model: Membros de Projeto (Visibilidade Restrita por Convite)

## Entidade nova

### `ProjectMember`

Associação entre uma pessoa e um Projeto — sem role própria (spec.md, Assumptions). Mesma estrutura
de `WorkspaceMember`, sem a coluna `role` e sem o índice único parcial de Owner (não se aplica aqui).

| Coluna | Tipo | Constraints | Nota |
|---|---|---|---|
| `id` | UUID | PK, `server_default=gen_random_uuid()` | |
| `project_id` | UUID | FK `projects.id`, `ON DELETE CASCADE`, `NOT NULL` | FR-011 — excluir o projeto remove seus membros |
| `user_id` | UUID | FK `users.id`, `ON DELETE CASCADE`, `NOT NULL` | |
| `created_at` | timestamptz | `server_default=now()`, `NOT NULL` | exposto como `joined_at` nas respostas, mesma convenção de `WorkspaceMemberRead` |

**Constraints**:

- `UniqueConstraint(project_id, user_id)` — mesma pessoa não pode ser adicionada duas vezes ao mesmo
  projeto (`name="uq_project_members_project_user"`).
- `Index(user_id)` — mesmo propósito de `ix_workspace_members_user_id`: consultas "todos os projetos
  de que este usuário participa" (research.md #2, `list_project_ids_for_user`).

**Invariante de negócio** (FR-002, garantida no Service, não no banco — evita uma segunda fonte de
verdade sobre quem é membro de workspace): todo `ProjectMember.user_id` MUST já ter um
`WorkspaceMember` correspondente no workspace do projeto no momento em que é adicionado. Não é
imposta por FK composta (não há necessidade — a rota de adicionar membro já resolve o workspace do
projeto e valida membership antes de inserir).

## Entidade alterada

### `ProjectRead` (schema, não a tabela)

Ganha um campo novo, calculado pelo Service a cada resposta (mesmo padrão de `WorkspaceRead.my_role`,
nunca via `from_attributes` direto):

| Campo novo | Tipo | Significado |
|---|---|---|
| `is_member` | bool | `true` se o usuário autenticado é membro explícito deste projeto, **ou** é o Owner do workspace (que sempre tem acesso — research.md #6). `false` só ocorre para Admin vendo um projeto do qual não participa (FR-006) — Member nunca recebe um `ProjectRead` com `is_member=false`, porque nesse caso o projeto nem aparece na listagem dele. |

Nenhuma coluna nova na tabela `projects` — `is_member` é inteiramente derivado, nunca persistido.

## Fórmula de acesso (reaproveitada em todo ponto de enforcement — research.md #3)

Dados: `role` = role do usuário no workspace do projeto (`None` se não for nem membro do workspace);
`is_project_member` = existe `ProjectMember(project_id, user_id)`.

```text
tem_acesso_ao_projeto(role, is_project_member) =
    role == OWNER
    OR is_project_member
```

`role == ADMIN` sozinho **não** concede acesso ao conteúdo — só à listagem (tratado separadamente em
`ProjectService.list_by_workspace`, que para `ADMIN`/`OWNER` retorna todos os projetos do workspace
independente desta fórmula).

## Nova cláusula `visible` de `TaskRepository.search` / `count_by_status`

Cláusula atual (`001-taskflow-mvp`):

```text
visible = (creator_id == user AND workspace_id IS NULL)   -- tarefa pessoal
       OR (workspace_id IN workspace_ids)                  -- qualquer tarefa de qualquer workspace do usuário
```

Cláusula nova — o segundo termo passa a excluir tarefas de projetos restritos aos quais o usuário não
tem acesso:

```text
visible = (creator_id == user AND workspace_id IS NULL)                          -- inalterado
       OR (workspace_id IN workspace_ids AND project_id IS NULL)                 -- tarefa de workspace sem projeto: inalterado
       OR (workspace_id IN owner_workspace_ids AND project_id IS NOT NULL)       -- Owner vê tudo (research.md #2)
       OR (project_id IN member_project_ids)                                     -- membro explícito do projeto
```

`owner_workspace_ids` e `member_project_ids` (research.md #2) são calculados uma vez por
`TaskService.search`/`TaskService.count_by_status` (mesmo lugar onde `workspace_ids` já é calculado
hoje) e passados como parâmetros novos para `TaskRepository`, nunca recalculados dentro da query.

`require_task_visible` (`task_authorization.py`, usada por `GET /tasks/{id}` e demais rotas de tarefa
única) aplica a MESMA fórmula de acesso do projeto (seção anterior) quando `task.project_id is not
None`, em vez de reimplementar a lógica de `TaskRepository`.

## Regras de Domínio — onde cada uma é validada

| Regra (spec) | Banco | Schema | Service | Dependency/Auth |
|---|---|---|---|---|
| Todo membro de projeto já é membro do workspace (FR-002) | — | — | `ProjectMemberService.add_member` confere `WorkspaceMemberRepository.get_role` antes de inserir | — |
| Criador vira primeiro membro do projeto (FR-003) | — | — | `ProjectService.create` cria `Project` + `ProjectMember` na mesma transação (mesmo padrão de `WorkspaceService.create`) | — |
| Só Owner/Admin gerenciam membros; Admin só se já é membro do projeto (FR-004/FR-005) | — | — | — | `require_project_manage` (research.md #5) |
| Listagem: Member só vê os seus; Owner/Admin veem todos (FR-006) | — | — | `ProjectService.list_by_workspace` ramifica por role | `require_workspace_member` (autorização de entrar na rota, já existente) |
| Abertura de conteúdo bloqueada para quem não tem acesso (FR-007/FR-008) | — | — | `ProjectService.get_by_id_or_404` aplica a fórmula de acesso | `require_project_visible` — `404`, nunca `403` |
| Atribuição de tarefa restrita a membro do projeto (FR-009) | — | — | `TaskService._require_project_member` (nova), chamada em `create` e `update` quando `project_id is not None` | — |
| Remoção bloqueada com tarefas ativas no projeto (FR-010) | — | — | `ProjectMemberService.remove_member` — mesmo padrão de `WorkspaceMemberService.remove_member`, usando `TaskRepository.list_active_by_assignee_in_project` (nova, mesma forma de `list_active_by_assignee_in_workspace`) | — |
| Excluir projeto remove seus membros (FR-011) | `ON DELETE CASCADE` em `project_members.project_id` | — | — | — |
| Migração dos projetos existentes (FR-012) | `op.execute` INSERT...SELECT na migração (research.md #4) | — | — | — |
