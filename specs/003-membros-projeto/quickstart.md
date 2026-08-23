# Quickstart: Membros de Projeto (Visibilidade Restrita por Convite)

**Feature**: `003-membros-projeto` | **Spec**: [spec.md](./spec.md)

Ambiente já preparado conforme [`001-taskflow-mvp/quickstart.md`](../001-taskflow-mvp/quickstart.md)
(backend em `http://localhost:8000/api/v1`, migrações aplicadas incl. a nova `project_members`,
frontend em `http://localhost:5173`). Este guia cobre só os roteiros de validação **desta** feature.

## Pré-requisito

Um workspace com 3 pessoas: **Owner** (dono do workspace), **Admin**, **Member** — mesmo cenário
usado nos testes de `WorkspaceMembersPage` do MVP — e um projeto criado pelo Owner dentro dele.

## Roteiro 1 — Gerenciar membros de um projeto (US1)

1. Como **Owner**, `POST /api/v1/workspaces/{workspace_id}/projects` → o Owner já é `ProjectMember`
   automaticamente (FR-003) — confirmar via `GET /api/v1/projects/{project_id}/members`.
2. Como **Owner**, `POST /api/v1/projects/{project_id}/members` com `{"user_id": "<Member>"}` →
   espera `201`; `GET .../members` agora lista 2 pessoas.
3. Como **Member** (não Owner/Admin), tentar `POST /api/v1/projects/{project_id}/members` com outro
   `user_id` → espera `403`.
4. Como **Owner**, `DELETE /api/v1/projects/{project_id}/members/{member_user_id}` (sem tarefas
   ativas) → espera `204`.

## Roteiro 2 — Visibilidade restrita para Member comum (US2)

1. Criar Projeto A (Owner cria, Member NÃO é adicionado) e Projeto B (Owner cria, Member É
   adicionado como membro), no mesmo workspace.
2. Como **Member**, `GET /api/v1/workspaces/{workspace_id}/projects` → resposta contém só o Projeto
   B; Projeto A não aparece em nenhuma posição da lista.
3. Como **Member**, `GET /api/v1/projects/{projeto_a_id}` (id obtido de outra sessão, ex. Owner) →
   espera `404`.
4. Adicionar o Member ao Projeto A (`POST .../members` como Owner) → repetir o passo 2: agora os
   dois projetos aparecem.

## Roteiro 3 — Visibilidade ampliada para Owner e Admin (US3)

1. Criar um Projeto C (Owner cria, ninguém mais é adicionado).
2. Como **Owner**, `GET /api/v1/projects/{projeto_c_id}` → espera `200`, mesmo nunca tendo sido
   adicionado explicitamente como membro além da criação automática.
3. Como **Admin** (não membro do Projeto C), `GET /api/v1/workspaces/{workspace_id}/projects` →
   Projeto C aparece na lista, com `is_member: false`.
4. Como o mesmo **Admin**, `GET /api/v1/projects/{projeto_c_id}` → espera `404` (vê na lista, não
   abre o conteúdo).

## Roteiro 4 — Atribuição de tarefa restrita a membros do projeto (US4)

1. No Projeto B (Member já é membro, do Roteiro 2), como Owner: `POST /api/v1/tasks` com
   `{"project_id": "<projeto_b>", "assignee_id": "<member_user_id>"}` → espera `201` (Member é
   membro do projeto).
2. No Projeto A (Member não é membro), como Owner: `POST /api/v1/tasks` com
   `{"project_id": "<projeto_a>", "assignee_id": "<member_user_id>"}` → espera
   `400 BUSINESS_RULE_VIOLATION`.

## Roteiro 5 — Remoção bloqueada por tarefas ativas (US5)

1. Com uma tarefa não concluída atribuída ao Member dentro do Projeto B, como Owner:
   `DELETE /api/v1/projects/{projeto_b}/members/{member_user_id}` → espera `409 CONFLICT`, `details`
   listando a tarefa.
2. Reatribuir ou concluir essa tarefa, repetir o `DELETE` → espera `204`.

## Roteiro 6 — Migração de projetos existentes (FR-012)

1. Antes de aplicar a migração `003`, ter ao menos um projeto já existente com 2+ membros de
   workspace associados a ele.
2. Aplicar `alembic upgrade head`.
3. `GET /api/v1/projects/{projeto_existente}/members` → todas as pessoas que já eram membros do
   workspace no momento da migração aparecem como `ProjectMember`, sem nenhuma ação manual.
