# Implementation Plan: Membros de Projeto (Visibilidade Restrita por Convite)

**Branch**: `001-taskflow-mvp` (decisão do usuário: sem branch dedicada para esta feature — ver
nota abaixo) | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-membros-projeto/spec.md`

> **Nota de branch**: o diretório da spec (`003-membros-projeto`) é numerado independentemente do
> nome da branch git — mesma decisão já registrada em `002-tarefas-fixas/plan.md`. O usuário optou
> explicitamente por continuar todo o trabalho na branch `001-taskflow-mvp` já em uso.

## Summary

Um Projeto deixa de ser visível/acessível a todo membro do workspace e passa a ter sua própria lista
de membros (`ProjectMember`, sem role própria). Owner do workspace continua vendo e acessando tudo
automaticamente; Admin vê a listagem completa mas só abre o conteúdo (quadro/tarefas) dos projetos
dos quais participa; Member comum só vê os projetos dos quais é membro explícito. A mesma barreira
vale para atribuição de responsável em tarefas de projeto. Projetos já existentes são migrados
automaticamente (todo membro atual do workspace vira membro explícito do projeto) — ninguém perde
acesso com a mudança.

Abordagem técnica: reaproveita 100% da stack e arquitetura de `001-taskflow-mvp`. Uma tabela nova
(`project_members`, uma migração Alembic com backfill de dados), uma dependency de autorização nova
(`require_project_visible`/`require_project_manage`), e uma correção importante identificada durante
o levantamento técnico (research.md #3): a cláusula de visibilidade de `TaskRepository.search`/
`count_by_status` — hoje só considera membership de *workspace* — precisa passar a considerar
também membership de *projeto*, senão a restrição pode ser contornada listando tarefas diretamente.

Decisões técnicas detalhadas: [research.md](./research.md).
Modelo de dados completo: [data-model.md](./data-model.md).
Contrato de API: [contracts/project-members.md](./contracts/project-members.md).
Roteiro de validação: [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: inalterado de `001-taskflow-mvp` — Python 3.13 (backend); TypeScript 5.x +
React 19 (frontend).

**Primary Dependencies**: inalterado — nenhuma dependência nova.

**Storage**: mesmo PostgreSQL 15+ já em uso. 1 tabela nova (`project_members`) — ver
[data-model.md](./data-model.md).

**Testing**: inalterado — pytest + pytest-cov + httpx (backend); Vitest + React Testing Library
(frontend).

**Target Platform**: inalterado.

**Project Type**: web (mesmo monorepo `backend/` + `frontend/`).

**Performance Goals**: sem requisito especial — mesmo perfil qualitativo do restante do MVP; a nova
cláusula `visible` de `TaskRepository` adiciona no máximo duas subconsultas de IDs pré-calculadas
(mesmo padrão que `workspace_ids` já usa hoje), sem N+1.

**Constraints**: nenhuma regra de negócio nova sobre quem pode CRIAR um projeto (spec.md,
Assumptions) — só sobre quem o vê/acessa depois de criado.

**Scale/Scope**: 5 User Stories, 12 Functional Requirements, 1 entidade nova, 1 grupo de rotas novo,
6 pontos de enforcement alterados em código já existente (research.md #3).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliação contra os 14 princípios de `.specify/memory/constitution.md` (v1.1.0):

| Princípio | Status | Nota |
|---|---|---|
| I. Stack Tecnológico Exclusivo | ✅ PASS | Mesma stack do MVP, sem exceção. |
| II. Clean Code, Tipagem e Responsabilidade Única | ✅ PASS | `ProjectMemberService` concentra a regra de gestão de membros; a fórmula de acesso (data-model.md) vive num único lugar conceitual, reaproveitada por todos os 6 pontos de enforcement — nenhuma regra de negócio em rota ou componente. |
| III. Separação de Camadas | ✅ PASS | Mesma árvore de camadas — nenhuma categoria nova (`ProjectMember` entra em `models/schemas/repositories/services/routes` já existentes). |
| IV. Backend como Autoridade de Validação | ✅ PASS | Toda decisão de acesso (quem vê/abre/atribui) é calculada no backend; frontend só reflete `is_member`/listas já filtradas (research.md #6/#7) — nunca decide sozinho o que esconder. |
| V. Reuso e Evolução Consistente | ✅ PASS | `ProjectMember` espelha `WorkspaceMember` (mesmo padrão de tabela de associação); `require_project_manage` reaproveita `require_project_visible` em vez de duplicar a checagem de acesso (research.md #5); a fórmula de acesso é definida uma vez (data-model.md) e citada, não reimplementada, em cada um dos 6 pontos. |
| VI. Migrações via Alembic | ✅ PASS | 1 migração nova (`0006_project_members.py`), incl. backfill via `op.execute` — mesmo mecanismo já usado em `0002` (research.md #4), não um padrão novo. |
| VII. Documentação Automática (OpenAPI) | ✅ PASS | Rotas novas com `response_model` explícito (`ProjectMemberRead`), mesmo padrão do restante da API. |
| VIII. Cobertura de Testes para Regras Críticas | ✅ PASS | Ver seção "Testes" abaixo — a fórmula de acesso e os 6 pontos de enforcement são as regras críticas desta feature. |
| IX. Nomenclatura Padronizada por Camada | ✅ PASS | `ProjectMember` (Model), `ProjectMemberService`/`Repository`, rotas em `/projects/{id}/members` (substantivo plural, mesmo padrão de `/workspaces/{id}/members`), `require_project_visible`/`require_project_manage` (dependencies, mesmo padrão `require_<recurso>_<regra>`). |
| X. Tratamento Padronizado de Erros | ✅ PASS | Mesmo envelope de erro; `404` para acesso negado (nunca `403`, mesma convenção de segurança já estabelecida), `400 BUSINESS_RULE_VIOLATION` para assignee fora do projeto, `409 CONFLICT` para remoção com tarefas ativas (mesmo formato de `WorkspaceMemberService.remove_member`). |
| XI. Logging de Operações Importantes | ✅ PASS | Adicionar/remover membro de projeto logados, mesmo padrão do restante do backend. |
| XII. Configuração Centralizada | ✅ PASS | Nenhuma variável de configuração nova. |
| XIII. Fluxo Spec Kit Obrigatório | ✅ PASS | Esta feature está seguindo o fluxo completo (`specify` → `plan` → `tasks` → `implement`) desde o início. |
| XIV. Compatibilidade Arquitetural | ✅ PASS | Nenhuma mudança estrutural — todo arquivo novo entra em categoria já existente (`models/`, `schemas/`, `services/`, `repositories/`, `routes/`, `dependencies/` no backend; `pages/`, `services/`, `hooks/`, `types/` no frontend). |

**Resultado**: nenhuma violação. `Complexity Tracking` vazio.

## Project Structure

### Documentation (this feature)

```text
specs/003-membros-projeto/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   └── project-members.md
└── tasks.md              # Fase 2 — gerado por /speckit-tasks (não criado aqui)
```

### Source Code (repository root)

```text
TaskFlow/
├── backend/
│   └── app/
│       ├── models/
│       │   └── project_member.py                 # NOVO
│       ├── schemas/
│       │   └── project_member.py                 # NOVO — Create/Read
│       │   └── project.py                         # ESTENDIDO — ProjectRead.is_member
│       ├── repositories/
│       │   ├── project_member_repository.py       # NOVO
│       │   ├── workspace_member_repository.py      # ESTENDIDO — list_owned_workspace_ids_for_user
│       │   └── task_repository.py                  # ESTENDIDO — visible com project_id, list_active_by_assignee_in_project
│       ├── services/
│       │   ├── project_member_service.py           # NOVO
│       │   ├── project_service.py                  # ESTENDIDO — create/list_by_workspace/get_by_id_or_404
│       │   └── task_service.py                     # ESTENDIDO — validação de assignee por projeto
│       ├── routes/
│       │   ├── project_members.py                  # NOVO
│       │   └── projects.py                          # ESTENDIDO — create_project recebe current_user
│       └── dependencies/
│           ├── project_authorization.py            # NOVO — require_project_visible/require_project_manage
│           └── task_authorization.py                # ESTENDIDO — require_task_visible considera projeto
│   └── alembic/versions/
│       └── 0006_project_members.py                 # NOVO — 1 tabela + backfill de dados (FR-012)
│
├── frontend/
│   └── src/
│       ├── types/
│       │   └── projectMember.ts                     # NOVO
│       │   └── project.ts                            # ESTENDIDO — Project.is_member
│       ├── services/
│       │   └── projectMemberService.ts               # NOVO
│       ├── hooks/
│       │   └── useProjectMembers.ts                  # NOVO
│       ├── pages/
│       │   ├── ProjectsPage.tsx                       # ESTENDIDA — cartão bloqueado quando !is_member
│       │   ├── ProjectDetailPage.tsx                  # ESTENDIDA — Sheet de gestão de membros no herói
│       │   └── TaskFormPage.tsx                       # ESTENDIDA — seletor de responsável usa useProjectMembers quando há projeto
```

**Structure Decision**: nenhuma categoria de diretório nova em nenhum dos dois projetos —
`ProjectMember` entra em categorias já existentes (Constitution XIV).

## Frontend

- `ProjectsPage.tsx`: cartão de um projeto com `is_member: false` (só ocorre para Admin, FR-006)
  renderiza com tratamento visual bloqueado (ícone de cadeado, sem navegação ao clicar) em vez de
  deixar o usuário abrir e esbarrar num `404` (research.md #6).
- `ProjectDetailPage.tsx`: novo botão "Membros" no herói (visível só para quem pode gerenciar — mesma
  condição `canManage` já usada por Editar/Excluir), abrindo um `Sheet` com lista de membros + adicionar
  por e-mail (mesmo padrão de `AddMemberByEmailForm`) + remover (mesmo padrão de
  `RemoveMemberDialog`, incl. o bloqueio com tarefas ativas retornando `details`) — decisão de não
  criar uma página dedicada em research.md #8.
- `TaskFormPage.tsx`: quando um projeto está selecionado, o `<Select>` de responsável passa a listar
  `useProjectMembers(projectId)` em vez de `useWorkspaceMembers(workspaceId)` (research.md #7).

## Testes

**Backend** — casos cobrindo as regras críticas (Constitution VIII):

- Criar projeto → criador vira `ProjectMember` automaticamente.
- Adicionar/remover membro de projeto: sucesso, `403` para Member, `400` se o alvo não é membro do
  workspace, `409` se já é membro do projeto (adicionar) ou tem tarefas ativas no projeto (remover).
- Listagem de projetos: Member vê só os seus; Admin/Owner veem todos; `is_member` correto em cada
  caso.
- Acesso a um projeto isolado (`GET /projects/{id}`): `200` para Owner (mesmo sem membership
  explícita) e para membro explícito; `404` para Member não-membro e para Admin não-membro.
- Atribuição de tarefa: `201`/`200` para assignee membro do projeto; `400` para assignee que é
  membro do workspace mas não do projeto.
- `GET /tasks?project_id=` e `GET /tasks/{id}`: tarefas de projeto restrito somem para quem não tem
  acesso, aparecem para quem tem (incl. Owner sem membership explícita).
- `GET /dashboard`: contagens não incluem tarefas de projetos restritos aos quais o usuário não tem
  acesso (regressão sobre a cláusula `visible` compartilhada).
- Migração `0006`: aplicar sobre um banco com projetos/membros pré-existentes e confirmar que todo
  `WorkspaceMember` vira `ProjectMember` de todo projeto do seu workspace.

**Frontend**: `ProjectsPage`/`ProjectDetailPage`/`TaskFormPage` — mesmo padrão de testes já usado
para as páginas equivalentes de Workspace (`WorkspaceMembersPage.test.tsx`).

## Ordem de Implementação

1. **Backend — Fundação**: model `ProjectMember`, migração Alembic (incl. backfill).
2. **Backend — Domínio**: `ProjectMemberRepository`/`Service`, extensões em
   `WorkspaceMemberRepository`/`TaskRepository` (novos métodos de IDs/filtros), `ProjectService`
   (create/list/get), `require_project_visible`/`require_project_manage`, rotas
   `project_members.py`.
3. **Backend — Correção de superfície** (research.md #3): `TaskService` (assignee), `TaskRepository`
   (`visible`), `require_task_visible` — os 3 pontos que hoje ignoram membership de projeto.
4. **Backend — Testes**: cobertura completa das regras críticas antes de avançar para o frontend.
5. **Frontend**: tipos, service, hook, extensão de `ProjectsPage`/`ProjectDetailPage`/
   `TaskFormPage`.
6. **Frontend — Testes**: componentes afetados.
7. **Validação final**: roteiro completo de `quickstart.md`.

## Complexity Tracking

> Nenhuma violação da Constitution foi identificada (ver "Constitution Check" acima). Tabela
> intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| _(nenhuma)_ | — | — |
