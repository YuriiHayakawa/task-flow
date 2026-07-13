# API Contract Conventions

**Feature**: `001-taskflow-mvp`

Convenções aplicadas a todos os contratos em `contracts/*.md`. A documentação
interativa final (Swagger/OpenAPI) é gerada automaticamente pelo FastAPI a partir do
código (Constitution VII) — estes arquivos descrevem a intenção do contrato para a fase
de planejamento, não o schema OpenAPI completo.

## Base path

Todas as rotas de negócio ficam sob `/api/v1`. Exemplo completo: `/api/v1/workspaces`.

## Autenticação

- Todas as rotas, exceto `POST /api/v1/auth/register` e `POST /api/v1/auth/login`, exigem
  header `Authorization: Bearer <jwt>`.
- Token ausente/inválido/expirado → `401 UNAUTHORIZED`, código `NOT_AUTHENTICATED`.
- **Conta desativada** (`is_active = false`) — comportamento distinto e explícito
  (`research.md` #1), reconsultado a **cada** requisição autenticada, não só no login:
  - `POST /auth/login` contra uma conta desativada → `403 FORBIDDEN`, código
    `ACCOUNT_DISABLED`, mensagem "Esta conta está desativada." — **nunca** a mensagem
    genérica de credenciais inválidas usada para e-mail/senha incorretos.
  - Qualquer rota protegida, quando o token é válido mas `is_active = false` no momento
    da requisição → `403 FORBIDDEN`, código `ACCOUNT_DISABLED` (mesmo corpo de erro do
    login). Isso cobre o caso de uma conta ser desativada **enquanto** o usuário ainda
    possui um JWT não expirado — a checagem de `is_active` a cada requisição é o que
    torna a desativação efetiva de imediato.
  - Credenciais incorretas (e-mail não cadastrado ou senha errada) continuam retornando
    `401 UNAUTHORIZED`, código `INVALID_CREDENTIALS`, mensagem genérica — distinto de
    `ACCOUNT_DISABLED` tanto no código HTTP quanto no `code` do envelope de erro.

## Formato padrão de erro (Constitution X)

Todas as respostas de erro (incluindo erros de validação do FastAPI/Pydantic) usam o
mesmo envelope, via exception handlers centralizados em `core/exceptions.py`:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Descrição legível do erro.",
    "details": [
      {"field": "email", "issue": "already registered"}
    ]
  }
}
```

`details` é omitido quando não aplicável. Nenhuma resposta de erro MUST expor stack
trace, nome de classe interna ou detalhes de implementação (Constitution X).

## Códigos HTTP padrão

| Código | Uso |
|---|---|
| `200` | Sucesso em GET/PUT/PATCH |
| `201` | Sucesso em POST que cria recurso |
| `204` | Sucesso em DELETE (sem corpo) |
| `400` | Erro de regra de negócio (ex.: e-mail já em uso) |
| `401` | Não autenticado / token ausente ou inválido / credenciais de login incorretas (`INVALID_CREDENTIALS`) |
| `403` | Autenticado, mas sem permissão (role insuficiente) **ou** conta desativada (`ACCOUNT_DISABLED`, ver "Autenticação" acima) |
| `404` | Recurso não encontrado (ou não visível ao usuário — ver nota de segurança) |
| `409` | Conflito (ex.: membro já existe, e-mail duplicado em cadastro) |
| `422` | Erro de validação de schema (corpo/query mal formado) |

**Nota de segurança (proteção contra acesso horizontal indevido)**: para recursos
aninhados em um workspace/tarefa ao qual o usuário não tem acesso, a API responde `404`
(não `403`), evitando confirmar a existência do recurso a quem não tem permissão sobre
ele. `403` é reservado para quando o recurso é visível (o usuário tem acesso de leitura),
mas a ação específica é proibida pela role (ex.: Member tentando criar projeto) —
**exceto** o caso de `ACCOUNT_DISABLED` acima, que é deliberadamente explícito por
instrução direta de produto (ver `research.md` #1).

## Visibilidade versus participação (research.md #8)

Aplica-se a toda tarefa pertencente a um workspace (não se aplica a tarefas pessoais,
onde só o criador tem qualquer acesso). Três níveis distintos de acesso, usados de forma
consistente em todos os contratos deste diretório:

| Nível | Quem | Dependency | Cobre |
|---|---|---|---|
| **Visibilidade** | Qualquer membro do workspace (Owner, Admin ou Member) | `require_workspace_member` | `GET` da tarefa, comentários, checklist, anexos, histórico, participantes |
| **Colaboração** | Responsável (`assignee`) + participantes explícitos (`TaskMember`) | `require_task_participant` | Criar comentário; criar/alterar/remover item de checklist; enviar anexo |
| **Administração** | Criador e/ou responsável (conforme a ação) + Owner/Admin do workspace, **mesmo sem serem participantes** | `require_task_editor` (editar) / `require_task_delete` (excluir) | Editar campos operacionais da tarefa; excluir a tarefa; gerenciar participantes; remover anexos de terceiros (Owner/Admin) |

Owner/Admin MUST NOT ser tratados como participantes automáticos só por deterem essas
roles — se quiserem comentar/anexar/criar checklist em uma tarefa da qual não são
participantes, precisam ser adicionados como qualquer outro membro (`POST
/tasks/{task_id}/members`). Ver detalhamento completo de quem pode editar/excluir cada
tipo de recurso em `plan.md` (seção "Regras de Domínio" e "Permissões de Edição e
Exclusão").

## Paginação (listagens)

Query params: `page` (default `1`), `page_size` (default `20`, máximo `100`).

Resposta de listagem:

```json
{
  "items": [ ... ],
  "page": 1,
  "page_size": 20,
  "total": 137
}
```

## Schemas por operação (Constitution: Schemas)

Cada recurso possui, no mínimo: `<Entity>Create`, `<Entity>Update` (campos opcionais),
`<Entity>Read` (resposta). `password_hash` MUST NEVER aparecer em nenhum `Read`/`List`.

## Timestamps

Todos os campos de data/hora em UTC, formato ISO 8601 (`2026-07-10T14:30:00Z`).
