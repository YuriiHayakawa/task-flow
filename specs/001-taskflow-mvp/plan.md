# Implementation Plan: TaskFlow MVP

**Branch**: `001-taskflow-mvp` | **Date**: 2026-07-10 (revisado) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-taskflow-mvp/spec.md`

> **Revisão 2**: refina comportamento de conta desativada, substitui a estratégia de
> notificação de prazo por uma tarefa periódica, formaliza invariantes de tarefa
> pessoal, fortalece a garantia de Owner único, define um fluxo controlado de exclusão
> (evitando anexos órfãos), redefine a exclusão de projeto (preserva tarefas), detalha
> permissões de edição/exclusão por recurso, distingue visibilidade de participação,
> define timezone/datas, resolve unicidade case-insensitive de e-mail, reagrupa as
> migrações Alembic, e atualiza a versão-alvo do React. Nenhuma mudança de escopo do
> MVP. Ver `research.md` para o detalhamento de cada decisão.

> **Revisão 3 (auditoria técnica final)**: corrige referências cruzadas de Functional
> Requirements desatualizadas (Profile, TaskMember, Search/Filters/Ordering, System
> Administration) em `plan.md`/`data-model.md`/`research.md`/`contracts/`; fortalece a
> transferência de Owner com bloqueio pessimista (`SELECT ... FOR UPDATE`) além da
> transação e do índice único parcial já definidos; detalha a execução do scheduler
> `DUE_SOON` (execução fora do event loop via `asyncio.to_thread`, Session e conexão
> dedicadas por execução, liberação do advisory lock em `finally`, comportamento com
> múltiplas instâncias); completa as regras de `due_soon_notified_for` (incluindo
> `due_date` nulo, tarefas `DONE`, e reabertura com/sem alteração de prazo); confirma
> formalmente a convenção de enums (valores em inglês, rótulos em português no
> frontend). Nenhuma mudança de escopo, arquitetura ou decisão de produto — apenas
> correções e detalhamento técnico. Ver `research.md` #20 e #21, e a seção Testes
> abaixo.

## Summary

TaskFlow MVP é uma aplicação de gerenciamento de tarefas pessoais e colaborativas,
organizadas por workspaces e projetos, com três níveis de role de workspace (Owner,
Admin, Member), um System Admin de plataforma totalmente desacoplado da administração de
workspaces, dashboard inicial, busca/filtros/ordenação de tarefas, participantes de
tarefa, comentários, checklists, anexos, histórico de alterações e notificações in-app
(incluindo uma tarefa periódica dedicada a prazos próximos).

A abordagem técnica é um monorepo com **backend** Python/FastAPI em arquitetura de
camadas (routes → services → repositories → models), persistência PostgreSQL via
SQLAlchemy 2.0 síncrono com migrações Alembic agrupadas por domínio, autenticação JWT
com verificação de conta ativa a cada requisição, e **frontend** React 19/TypeScript/Vite
consumindo a API REST via Axios, sem biblioteca de estado global. O projeto é greenfield
— não há código em `backend/` nem `frontend/` ainda.

Decisões técnicas detalhadas: [research.md](./research.md).
Modelo de dados completo: [data-model.md](./data-model.md).
Contratos de API: [contracts/](./contracts/).
Roteiro de validação local: [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: Python 3.13 (backend); TypeScript 5.x + **React 19** (frontend —
ver `research.md` #16; não fixado em React 18 por falta de justificativa técnica para
uma versão mais antiga).

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (síncrono), Alembic, Pydantic v2,
Pydantic Settings, PyJWT, bcrypt, psycopg[binary] — backend, todas usando apenas a
biblioteca padrão (`asyncio`) para a tarefa periódica de notificações (`research.md`
#2), sem scheduler externo. React 19, React Router, Axios, Vite — frontend.

**Storage**: PostgreSQL 15+ (todos os timestamps em `TIMESTAMPTZ`, timezone de aplicação
configurável — `research.md` #9). Arquivos de anexo em disco local, com fluxo de
exclusão controlada (`research.md` #12).

**Testing**: pytest + pytest-cov + httpx (via `TestClient` do FastAPI) — backend. Vitest
+ React Testing Library — frontend.

**Target Platform**: backend como serviço Linux containerizável (Docker), rodável
nativamente no Windows de desenvolvimento atual; frontend como SPA em navegadores
evergreen.

**Project Type**: web (monorepo com `backend/` + `frontend/` separados).

**Performance Goals**: sem requisito de alta escala na spec; alvo qualitativo de latência
interativa padrão de aplicação web. A tarefa periódica de notificações roda a cada 60s
por padrão (configurável), com overhead desprezível sobre a carga normal da API.

**Constraints**: backend é a única autoridade de validação de negócio; notificações
somente in-app; sem e-mail; sem login social/OAuth/SSO; sem exclusão de conta, alteração/
recuperação de senha ou foto de perfil; conta desativada bloqueia login e todo acesso
autenticado subsequente com erro específico (`ACCOUNT_DISABLED`, não genérico).

**Scale/Scope**: MVP para uso pessoal e por equipes pequenas/médias dentro de um
workspace; 15 módulos funcionais, ~13 User Stories, 59 Functional Requirements. Sem meta
explícita de volume de usuários/dados.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reavaliação contra os 14 princípios de `.specify/memory/constitution.md` (v1.1.0), após
as mudanças desta revisão:

| Princípio | Status | Nota |
|---|---|---|
| I. Stack Tecnológico Exclusivo | ✅ PASS | Nenhuma stack alternativa introduzida; a tarefa periódica usa `asyncio` (biblioteca padrão do Python), não uma nova dependência de scheduler. |
| II. Clean Code, Tipagem e Responsabilidade Única | ✅ PASS | Sem alteração de avaliação — mantém-se válido com as novas regras (invariantes de tarefa pessoal, permissões granulares) encapsuladas em métodos de Service dedicados. |
| III. Separação de Camadas | ✅ PASS | `app/core/scheduler.py` fica em `core/`, ao lado de `config.py`/`security.py`/`logging.py`/`exceptions.py` — nenhuma categoria nova de diretório introduzida. |
| IV. Backend como Autoridade de Validação | ✅ PASS | Todas as novas regras (invariantes de tarefa pessoal, Owner único, permissões de edição/exclusão, deduplicação de notificação) são validadas exclusivamente no backend (Service/constraint de banco); frontend permanece limitado a UX. |
| V. Reuso e Evolução Consistente | ✅ PASS | Nenhuma dependência nova introduzida (asyncio é padrão; índice funcional em vez de CITEXT evita extensão de banco); reaproveita infraestrutura já presente (Postgres para advisory lock). |
| VI. Migrações via Alembic | ✅ PASS | Reagrupamento para 4 migrações por domínio (em vez de 11 por entidade) continua 100% dentro do fluxo Alembic — nenhuma alteração de schema fora de migração. |
| VII. Documentação Automática (OpenAPI) | ✅ PASS | Novos códigos de erro (`ACCOUNT_DISABLED`) e regras de autorização continuam expressos via `response_model`/dependencies do FastAPI, refletidos automaticamente no Swagger. |
| VIII. Cobertura de Testes para Regras Críticas | ✅ PASS | Seção "Testes" ampliada com 13 novos casos cobrindo exatamente as regras críticas desta revisão. |
| IX. Nomenclatura Padronizada por Camada | ✅ PASS | Novas dependencies (`require_task_participant`, `require_task_editor`, `require_task_delete`) seguem a convenção `require_<recurso>_<regra>` já estabelecida. |
| X. Tratamento Padronizado de Erros | ✅ PASS | `ACCOUNT_DISABLED` é mais um código dentro do mesmo envelope de erro já definido — nenhum formato novo introduzido. |
| XI. Logging de Operações Importantes | ✅ PASS | Tarefa periódica loga início/fim/erros; exclusões controladas logam falhas de remoção de arquivo; exclusão de projeto loga a operação — todos via `core/logging.py`, sem dados sensíveis. |
| XII. Configuração Centralizada | ✅ PASS | Novas variáveis (`APP_TIMEZONE`, `DUE_SOON_CHECK_INTERVAL_SECONDS`, `DUE_SOON_WINDOW_HOURS`) todas em `core/config.py` via Pydantic Settings. |
| XIII. Fluxo Spec Kit Obrigatório | ✅ PASS | Esta revisão ocorreu dentro do próprio `/speckit.plan`, antes de `/speckit.tasks` — fluxo respeitado. |
| XIV. Compatibilidade Arquitetural | ✅ PASS | Nenhuma mudança estrutural fora do já definido; `core/scheduler.py` é a única adição de arquivo à árvore de diretórios, dentro de uma categoria já existente (`core/`). |

**Resultado**: nenhuma violação. `Complexity Tracking` permanece vazio.

**Reavaliação (Revisão 3)**: o `SELECT ... FOR UPDATE` na transferência de Owner e a
execução do job via `asyncio.to_thread` com conexão/Session dedicadas usam apenas
recursos nativos do SQLAlchemy/PostgreSQL e da biblioteca padrão do Python — nenhuma
dependência nova, nenhum diretório/categoria nova na árvore do projeto. Todos os 14
princípios permanecem ✅ PASS; `Complexity Tracking` continua vazio.

## Project Structure

### Documentation (this feature)

```text
specs/001-taskflow-mvp/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── _conventions.md
│   ├── auth-and-users.md
│   ├── workspaces.md
│   ├── projects-and-tasks.md
│   ├── collaboration.md
│   └── dashboard-and-notifications.md
└── tasks.md              # Fase 2 — gerado por /speckit.tasks (não criado aqui)
```

### Source Code (repository root)

```text
TaskFlow/
├── backend/
│   ├── app/
│   │   ├── main.py                # inclui o lifespan que inicia/encerra o scheduler
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings, incl. APP_TIMEZONE, DUE_SOON_*
│   │   │   ├── security.py        # hashing (bcrypt) + JWT (PyJWT)
│   │   │   ├── logging.py         # logging estruturado
│   │   │   ├── exceptions.py      # exception handlers + envelope de erro padrão (incl. ACCOUNT_DISABLED)
│   │   │   └── scheduler.py       # NOVO — loop asyncio da tarefa periódica DUE_SOON (research.md #2)
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── routes/
│   │   ├── enums/
│   │   ├── dependencies/          # incl. require_task_participant/editor/delete (novos)
│   │   └── utils/
│   ├── alembic/
│   │   └── versions/              # 4 migrações agrupadas (ver data-model.md)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example                # incl. APP_TIMEZONE, DUE_SOON_CHECK_INTERVAL_SECONDS, DUE_SOON_WINDOW_HOURS
│
├── frontend/                       # estrutura inalterada desta revisão — ver revisão 1
│   └── ... (ver revisão anterior deste documento; sem mudança estrutural)
│
├── docker-compose.yml
├── .specify/
├── specs/
└── README.md
```

**Structure Decision**: inalterada — Opção "Web application", sem divergência a
registrar em Complexity Tracking. Único arquivo novo na árvore: `core/scheduler.py`,
dentro de uma categoria já existente.

## Domínios e Módulos

Tabela original preservada (ver revisão 1); ajuste apenas no módulo 15:

| # | Módulo | Responsabilidade principal | Depende de | Testável isoladamente? |
|---|---|---|---|---|
| 15 | **Notifications** | Notificações in-app (comentário, alteração, **e tarefa periódica de prazo** — `research.md` #2) | 7, 11, 14 | Não para o loop em si; sim para `NotificationService.generate_due_soon_notifications()` chamada diretamente |

Demais módulos (1-14) e ordem recomendada (1→2→3→4→5→6→7→{8,9,10,11,12,13}→14→15)
inalterados desta revisão.

## Modelo de Dados

Ver [data-model.md](./data-model.md) — revisado nesta iteração com: invariantes
explícitas de tarefa pessoal, índice único parcial de Owner, índice único funcional de
e-mail, `TIMESTAMPTZ`/`APP_TIMEZONE`, campo `Task.due_soon_notified_for`, e a nova
estratégia de 4 migrações agrupadas por domínio (substituindo as 11 por entidade da
revisão 1).

## Regras de Domínio — onde cada uma é validada

Tabela da revisão 1 preservada e estendida com as linhas abaixo (refinamentos #1, #3,
#4, #6, #7, #8, #9, #10):

| Regra (spec / refinamento) | Banco | Schema | Service | Dependency/Auth |
|---|---|---|---|---|
| Login com conta desativada retorna erro específico `ACCOUNT_DISABLED`, não genérico (refinamento #1) | — | — | `AuthService.login` distingue os dois casos | — |
| Toda requisição autenticada revalida `is_active` (refinamento #1) | `User.is_active` | — | — | `get_current_user` consulta o banco a cada chamada |
| Tarefa pessoal: `workspace_id`/`project_id` nulos, `assignee_id == creator_id`, sem participantes, visível/editável só pelo criador (refinamento #3) | `workspace_id`/`project_id` nullable | `TaskCreate`/`TaskUpdate` rejeitam combinações inválidas | `TaskService`/`TaskMemberService` — ver tabela de invariantes em `data-model.md` | `require_task_editor`/`require_task_delete` tratam tarefa pessoal como caso especial (só o criador) |
| Exatamente um Owner por workspace, inclusive sob concorrência (refinamento #4) | Índice único parcial `ux_workspace_members_one_owner` | — | `WorkspaceMemberService.transfer_ownership` — `SELECT ... FOR UPDATE` na linha do Owner e do membro-alvo, reconfirmação sob lock, transacional com rollback completo em falha (`research.md` #20) | `require_workspace_owner` |
| Exclusão de projeto preserva tarefas (`project_id = NULL`, permanecem no workspace) (refinamento #6) | `ON DELETE SET NULL` | — | `ProjectService.delete` (autorização + log, nunca cascade "cego") | `require_workspace_admin_or_owner` |
| Task pessoal: só o criador vê/edita/conclui/exclui; Task de workspace: criador+responsável editam campos operacionais, apenas criador+Owner/Admin excluem, Member comum não edita nem exclui (refinamento #7) | — | `TaskUpdate` restrito aos "dados operacionais" (title, description, status, priority, due_date, assignee_id, project_id) | `TaskService` | `require_task_editor` (PATCH) / `require_task_delete` (DELETE) — dependencies distintas |
| Projects: só Owner/Admin criam, editam e excluem; Member só visualiza (refinamento #7) | — | — | `ProjectService` | `require_workspace_admin_or_owner` |
| Comments: sem edição/exclusão no MVP (refinamento #7) | — | Nenhum schema de `CommentUpdate`/delete existe | — | — |
| Checklists: sem edição textual separada, só criar/marcar/remover (refinamento #7) | — | `ChecklistItemUpdate` só aceita `is_done` | `ChecklistService` | `require_task_participant` |
| Attachments: uploader ou Owner/Admin removem; sem substituição (refinamento #7) | — | — | `AttachmentService.delete` | uploader-check **ou** `require_workspace_admin_or_owner` |
| TaskMembers: adicionar/remover só por criador, responsável ou Owner/Admin; responsável não é removível sem reatribuição antes (refinamento #7) | `UNIQUE(task_id, user_id)` | — | `TaskMemberService` | `require_task_editor` |
| Visibilidade (ver tarefa/comentários/checklist/anexos/histórico) é de todo membro do workspace; colaborar (comentar/checklist/anexar) exige ser responsável ou participante explícito; Owner/Admin não são participantes automáticos (refinamento #8) | — | — | Todos os services de sub-recurso de tarefa | `require_workspace_member` (leitura) vs. `require_task_participant` (escrita colaborativa) |
| Timestamps em UTC; "hoje"/"atrasada"/"vencendo hoje" calculados na timezone `APP_TIMEZONE` (refinamento #9) | `TIMESTAMPTZ` | — | `TaskRepository`/`DashboardService`/`NotificationService` | — |
| E-mail único, case-insensitive, no cadastro e na atualização de perfil (refinamento #10) | Índice único funcional sobre `lower(email)` | `UserCreate`/`UserUpdate` normalizam para lowercase antes de enviar ao Service | `UserService` | — |

Linhas da revisão 1 (tarefa pessoal básica, projeto pertence a workspace, responsável
obrigatório, System Admin desacoplado de workspaces, bloqueio de remoção de membro com
tarefas ativas, status controlado, atrasada/vencendo hoje derivados) permanecem válidas
e não foram removidas — apenas detalhadas onde a tabela acima se sobrepõe.

## Permissões de Edição e Exclusão — matriz consolidada (refinamento #7)

| Recurso | Visualizar | Criar | Editar | Excluir |
|---|---|---|---|---|
| **Task pessoal** | Só o criador | Próprio usuário | Só o criador | Só o criador |
| **Task de workspace** | Qualquer membro do workspace | Owner, Admin ou Member | Criador, responsável, Owner ou Admin | Criador, Owner ou Admin (**não** o responsável isoladamente, salvo se também for o criador) |
| **Project** | Qualquer membro do workspace | Owner ou Admin | Owner ou Admin | Owner ou Admin |
| **Comment** | Qualquer membro do workspace (ou criador, se task pessoal) | Responsável ou participante explícito (ou criador, se pessoal) | _fora do MVP_ | _fora do MVP_ |
| **ChecklistItem** | idem Comment | idem Comment | Apenas `is_done` (idem Comment) | idem Comment |
| **Attachment** | idem Comment | idem Comment | — (sem edição/substituição) | Quem enviou, **ou** Owner/Admin do workspace |
| **TaskMember** | Qualquer membro do workspace | Criador, responsável, Owner ou Admin | — | Criador, responsável, Owner ou Admin (responsável nunca removível sem reatribuição prévia) |
| **Workspace** | Qualquer membro | Qualquer usuário autenticado (vira Owner) | Só o Owner | Só o Owner |
| **WorkspaceMember (role)** | Qualquer membro | Owner/Admin adicionam Member; só Owner promove/rebaixa Admin | — | Owner/Admin removem Member; só Owner remove Admin; ninguém remove o Owner (só `transfer-ownership`) |

**Dados operacionais de Task** (campos cobertos por "Editar" acima): `title`,
`description`, `status`, `priority`, `due_date`, `assignee_id`, `project_id`.

## Autenticação e Segurança

- **Cadastro/Login**: inalterado da revisão 1 (bcrypt + PyJWT), **exceto** o
  comportamento de login com conta desativada (ver abaixo).
- **Conta desativada (refinamento #1)**: `AuthService.login` verifica `is_active`
  **depois** de confirmar a senha (para não abrir uma via de enumeração adicional além
  da já aceita — ver `research.md` #1) e retorna `403 ACCOUNT_DISABLED` distinto de
  `401 INVALID_CREDENTIALS`. `get_current_user` (dependency usada em toda rota
  protegida) **sempre** consulta `User.is_active` no banco a cada requisição — nunca
  confia apenas na validade/expiração do JWT — e retorna o mesmo `403 ACCOUNT_DISABLED`
  se a conta tiver sido desativada após a emissão do token.
- **Dependencies de autorização de tarefa (novas, refinamento #7/#8)**:
  - `require_task_participant`: responsável ou `TaskMember` explícito (ou criador, se
    tarefa pessoal) — usada em criação de comentário/checklist/anexo.
  - `require_task_editor`: criador, responsável, ou Owner/Admin do workspace (ou
    criador, se pessoal) — usada em `PATCH /tasks/{id}` e gestão de `TaskMember`.
  - `require_task_delete`: criador, ou Owner/Admin do workspace (ou criador, se
    pessoal) — usada em `DELETE /tasks/{id}`.
  - Todas retornam `404` para quem não tem sequer visibilidade da tarefa (não-membro do
    workspace), e `403` para quem tem visibilidade mas não a permissão específica —
    consistente com a nota de segurança de `contracts/_conventions.md`.
- Demais itens (segredos via env, logging sem dados sensíveis, formato padronizado de
  erro) inalterados da revisão 1.

## API REST

Inalterado na estrutura — ver [contracts/](./contracts/), todos revisados nesta
iteração para refletir: erro `ACCOUNT_DISABLED`, permissões de edição/exclusão
granulares, exclusão de projeto preservando tarefas, exclusão controlada de anexos, e a
tarefa periódica de notificações (substitui o `GET /dashboard` com efeito colateral da
revisão 1 — o dashboard agora é leitura pura).

## Dashboard, Busca e Filtros

Inalterado — ver revisão 1. Único ajuste: cálculo de "atrasada"/"vencendo hoje" agora
usa explicitamente `APP_TIMEZONE` (refinamento #9) em vez de UTC puro.

## Histórico e Notificações (revisado — refinamento #2)

- `TaskService.update` continua sendo o único ponto de escrita de `TaskHistoryEntry` —
  alteração + histórico + notificações relevantes na mesma transação.
- `CommentService.create` continua disparando `NEW_COMMENT` para participantes na
  mesma transação da criação do comentário.
- **Notificações `DUE_SOON` não são mais geradas de forma lazy** — uma tarefa periódica
  dedicada (`app/core/scheduler.py`, iniciada/encerrada via `lifespan` do FastAPI)
  chama `NotificationService.generate_due_soon_notifications()` a cada
  `DUE_SOON_CHECK_INTERVAL_SECONDS` (default 60s), protegida por advisory lock do
  PostgreSQL (evita execução duplicada mesmo com múltiplas instâncias) e idempotente via
  `Task.due_soon_notified_for` (evita notificação repetida para o mesmo ciclo de
  prazo). Detalhes completos, incluindo tratamento de falhas e estratégia de teste, em
  `research.md` #2.
- Nenhum envio de e-mail é implementado (FR-040).

## Anexos (revisado — refinamento #5)

Armazenamento local (inalterado — `research.md` #12), **mas toda exclusão que afeta
anexos (individual, de tarefa, ou de workspace) segue obrigatoriamente o fluxo**:

1. Localizar todos os anexos físicos afetados (antes de qualquer alteração no banco).
2. Validar autorização (uploader, ou Owner/Admin — ver matriz de permissões acima).
3. Excluir os registros de banco em uma transação e efetuar `commit()`.
4. Remover os arquivos físicos do disco **somente após** o commit ter sucesso.
5. Se a remoção de um arquivo físico falhar, registrar log `ERROR` (caminho,
   `attachment_id`, `task_id`) para reconciliação manual — a resposta da API não falha
   por isso, pois o estado autoritativo (banco) já está correto.

Nenhum cascade de banco "cego" (sem essa preparação) é aceitável para exclusão de tarefa
ou workspace — o `AttachmentService` é sempre acionado pelo `TaskService`/
`WorkspaceService` antes do `commit()` de exclusão, para coletar os caminhos físicos a
remover depois. Prevenção de path traversal (nomes UUID, nunca o nome original)
inalterada.

## Frontend

Estrutura inalterada desta revisão (ver revisão 1). Único ajuste: versão-alvo **React
19** em vez de React 18 (`research.md` #16), sem impacto na estrutura de pastas ou nos
princípios já definidos (TypeScript estrito, componentes funcionais, sem estado global,
validação de UX apenas).

## Testes (ampliado — refinamento #14)

**Backend** — casos da revisão 1 preservados, mais os seguintes casos novos:

- Login com conta desativada retorna `403 ACCOUNT_DISABLED` (mensagem específica, não
  genérica).
- Token de um usuário desativado **após** a emissão é rejeitado na próxima requisição
  autenticada (`403 ACCOUNT_DISABLED`).
- Tarefa pessoal: tentativa de definir `assignee_id` diferente do criador é rejeitada.
- Tarefa pessoal: tentativa de adicionar `TaskMember` é rejeitada.
- Concorrência de transferência de Owner (`research.md` #20): duas transferências
  simultâneas para o mesmo workspace — a segunda transação bloqueia no `SELECT ... FOR
  UPDATE` até a primeira concluir; ao ser liberada, recebe zero linhas para `role =
  OWNER` e responde `409` — apenas uma transferência MUST ter sucesso, nunca dois
  Owners nem zero Owners ao final. Testado forçando duas sessões de banco concorrentes
  (ex.: duas conexões/transações abertas explicitamente no teste) para exercitar o
  bloqueio real, não apenas a lógica do Service isoladamente.
- Tentativa de criar/promover um segundo `OWNER` no mesmo workspace é rejeitada pelo
  índice único parcial (teste de integração que força a violação diretamente, inserindo
  um segundo `WorkspaceMember` com `role=OWNER` por fora do fluxo normal do Service).
- Tarefa periódica `DUE_SOON` — impedir execução simultânea (`research.md` #2): um
  teste adquire manualmente o advisory lock em uma conexão separada (simulando outra
  instância já processando aquele tick) e verifica que `run_due_soon_job()` retorna sem
  processar nenhuma tarefa nem criar notificações; ao liberar o lock manual, uma nova
  chamada processa normalmente.
- Remoção de um projeto com tarefas: tarefas permanecem no workspace, com `project_id
  = null`, dados relacionados intactos.
- Exclusão de tarefa e de workspace remove os arquivos físicos de anexos
  correspondentes (verificado no sistema de arquivos de teste).
- Member do workspace que não é responsável nem participante recebe `403` ao tentar
  comentar/anexar/criar checklist em uma tarefa (mas `200` ao apenas visualizá-la).
- Matriz completa de permissões de edição/exclusão de tarefa (criador, responsável,
  Owner, Admin, Member comum — cada combinação testada).
- Unicidade case-insensitive de e-mail: cadastro com variação de maiúsculas/minúsculas
  de um e-mail já existente é rejeitado; atualização de perfil para um e-mail
  equivalente (case-insensitive) a um já existente também é rejeitada.
- Cálculo de "hoje"/atrasada" usando `APP_TIMEZONE` (teste com data/hora controlada
  próxima à virada de dia em UTC vs. `America/Sao_Paulo`, garantindo que o resultado
  segue a timezone configurada, não UTC).
- Regras completas de `due_soon_notified_for` (`research.md` #2, tabela dedicada):
  `due_date IS NULL` → campo permanece `NULL` e a tarefa nunca é selecionada pelo job;
  alterar `due_date` reseta o campo para `NULL`; tarefas `DONE` nunca geram `DUE_SOON`
  mesmo com `due_soon_notified_for` desatualizado; `Notification` + atualização do
  campo ocorrem na mesma transação (testado inclusive simulando falha entre as duas
  operações, confirmando rollback de ambas); chamar o job duas vezes em sequência para
  o mesmo conjunto de tarefas não duplica notificações; reabrir uma tarefa (`DONE` →
  `PENDING`/`IN_PROGRESS`) **sem** alterar `due_date` não gera nova notificação; reabrir
  **e** alterar `due_date` na mesma operação permite nova notificação no próximo ciclo
  do job.

**Frontend**: casos da revisão 1 preservados (nenhuma mudança necessária — as regras
novas são inteiramente aplicadas/validadas no backend, com o frontend apenas refletindo
os erros retornados, incluindo tratamento específico de `ACCOUNT_DISABLED` no
`httpClient.ts`).

## Ordem de Implementação

Inalterada em estrutura (Fases 1-9, ver revisão 1), com dois ajustes pontuais:

- **Fase 1 — Fundação do backend**: agora inclui a criação do **esqueleto** de
  `core/scheduler.py` (loop `asyncio` + `lifespan` wiring + advisory lock), ainda sem a
  lógica de negócio de `DUE_SOON` (que só existe a partir da Fase 6, quando
  `NotificationService` existe). O esqueleto pode chamar uma função vazia/placeholder
  até lá.
- **Fase 6 — Produtividade e rastreabilidade**: implementação real de
  `NotificationService.generate_due_soon_notifications()`, conectada ao scheduler
  criado na Fase 1.

Demais fases inalteradas.

## Complexity Tracking

> Nenhuma violação da Constitution foi identificada nesta revisão (ver "Constitution
> Check" acima). Tabela intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(nenhuma)_ | — | — |
