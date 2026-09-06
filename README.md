# 🚀 TaskFlow

**Gerenciamento de tarefas, projetos e workspaces — com hierarquia de permissões, colaboração em tempo real de contexto e uma trilha de documentação completa por trás de cada decisão.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tests](https://img.shields.io/badge/tests-779%20passing-2ea44f)](#qualidade-e-testes)
[![Spec Kit](https://img.shields.io/badge/workflow-Spec%20Kit-6f42c1)](#engenharia-orientada-a-especificação)

---

## 📑 Sumário

* [Sobre o projeto](#sobre-o-projeto)
* [Funcionalidades](#funcionalidades)
* [Arquitetura e princípios](#arquitetura-e-princípios)
* [Modelo de dados](#modelo-de-dados)
* [Stack tecnológica](#stack-tecnológica)
* [Estrutura do projeto](#estrutura-do-projeto)
* [Como executar](#como-executar)
* [Autenticação e segurança](#autenticação-e-segurança)
* [Engenharia orientada a especificação](#engenharia-orientada-a-especificação)
* [Qualidade e testes](#qualidade-e-testes)
* [Documentação de cada feature](#documentação-de-cada-feature)
* [Status do projeto](#status-do-projeto)
* [Autor](#autor)

---

<a id="sobre-o-projeto"></a>
## 📌 Sobre o projeto

O **TaskFlow** é uma aplicação full stack de gerenciamento de tarefas — pense num ponto de encontro entre um board pessoal de produtividade e uma ferramenta de colaboração em equipe, com uma hierarquia de permissões real por trás.

Um usuário comum gerencia suas próprias tarefas e rotinas pessoais, mas também pode criar **workspaces** para organizar o trabalho em equipe: dentro de um workspace, **projetos** agrupam tarefas, **membros** têm papéis (Owner/Admin/Member) com regras de governança bem definidas, e cada tarefa carrega participantes, comentários, checklists, anexos, histórico de alterações e notificações — tudo isolado por regras de visibilidade explícitas, validadas no backend, nunca só na interface.

Além do produto em si, o projeto foi construído como um estudo aplicado de **engenharia de software orientada a especificação**: nenhuma linha de código foi escrita sem antes passar por uma especificação, um plano técnico e uma lista de tarefas rastreável — o processo completo, com todas as decisões e trade-offs registrados, está documentado em [`specs/`](specs/).

---

<a id="funcionalidades"></a>
## ⚙️ Funcionalidades

### `001-taskflow-mvp` — o núcleo do produto

| Área                                 | O que faz                                                                                                                                                                               |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Contas**                           | Cadastro e login com e-mail/senha (JWT), contas ativas/desativadas                                                                                                                      |
| **Tarefas pessoais**                 | CRUD completo — título, descrição, status, prioridade, prazo                                                                                                                            |
| **Dashboard**                        | Contagem de pendentes/em andamento/concluídas/atrasadas/vencendo hoje, combinando tarefas pessoais e de todos os workspaces, com alternador de escopo (Geral/Pessoal/Workspace/Projeto) |
| **Workspaces**                       | Owner (titularidade única, transferível com segurança sob concorrência), Admin e Member, cada um com um conjunto de permissões bem delimitado                                           |
| **Projetos**                         | Criados por Owner/Admin; agrupam tarefas de equipe dentro de um workspace                                                                                                               |
| **Participantes de tarefa**          | Além do responsável, outros membros do workspace podem colaborar explicitamente numa tarefa                                                                                             |
| **Comentários, checklists e anexos** | Restritos ao responsável e aos participantes explícitos; visualização aberta a qualquer membro do workspace                                                                             |
| **Notificações in-app**              | Prazo próximo, novos comentários e alterações relevantes (status, prioridade, prazo, responsável)                                                                                       |
| **Histórico de alterações**          | Registro automático de quem mudou o quê, quando e de onde para onde                                                                                                                     |
| **Perfil**                           | Visualizar e editar nome/e-mail, consultar status da conta                                                                                                                              |
| **Administração da plataforma**      | Um System Admin lista e ativa/desativa contas — sem ganhar, por isso, nenhum acesso a workspaces específicos                                                                            |

> 💡 **Observação:** Busca, filtros e ordenação de tarefas (`GET /tasks?search=...`) existem e são testados na API; a tela dedicada de busca no frontend foi conscientemente adiada por decisão de produto (ver `specs/001-taskflow-mvp/tasks.md`, Fase 25).

---

### `002-tarefas-fixas` — rotinas pessoais recorrentes

Uma segunda aba em "Minhas tarefas" para hábitos e rotinas que se repetem: diária, semanal (em dias específicos da semana) ou mensal (num dia do mês, com a regra correta para meses mais curtos). Cada ocorrência tem um estado de conclusão independente, que reseta sozinho a cada novo ciclo — sem qualquer ação manual do usuário.

---

### `003-membros-projeto` — visibilidade restrita por convite

Cada projeto passa a ter sua própria lista de membros: só quem foi explicitamente convidado o vê e acessa. O Owner do workspace continua enxergando tudo automaticamente; o Admin vê a existência de todos os projetos mas só abre o conteúdo dos que participa. Atribuir uma tarefa de projeto passa a exigir que a pessoa seja membro daquele projeto específico — fechando uma brecha que permitiria vazar visibilidade por fora da regra.

---

<a id="arquitetura-e-princípios"></a>
## 🏗️ Arquitetura e princípios

O projeto segue uma **arquitetura em camadas estrita**, regida pela [TaskFlow Constitution](.specify/memory/constitution.md) — o documento que qualquer mudança no projeto precisa respeitar. Alguns dos princípios mais relevantes:

* **Backend como única autoridade de negócio.** O frontend pode validar campos por UX, mas toda regra que importa é validada (de novo) no backend — nunca confiado só ao cliente.

* **Camadas com responsabilidade única**, sem exceção:

```text
Route          → recebe a requisição, valida formato, delega ao service
Service        → concentra toda a regra de negócio
Repository     → único ponto de acesso ao banco de dados
Model / Schema → persistência / contrato de entrada-saída da API
```

* **Migrações versionadas.** Toda mudança de schema passa por uma migração Alembic — nunca uma alteração manual direto no banco.

* **Erros padronizados.** Uma única forma de payload de erro em toda a API, exceções de domínio traduzidas por exception handlers centralizados — nunca tratamento ad-hoc por rota.

* **Documentação automática.** Toda rota tem `response_model` explícito; o contrato real da API é sempre o gerado pelo FastAPI (Swagger/Redoc), nunca um documento paralelo que pode divergir.

* **Fluxo Spec Kit obrigatório.** Nenhuma funcionalidade é implementada sem antes passar por `specify → clarify → plan → tasks → implement` — ver [Documentação de cada feature](#documentação-de-cada-feature).

---

<a id="modelo-de-dados"></a>
## 🗄️ Modelo de dados

```text
User ──< WorkspaceMember >── Workspace ──< Project ──< ProjectMember >── User
User ──(assignee/creator)──< Task
Workspace ──< Task (opcional — tarefa de workspace sem projeto)
Project ──< Task
Task ──< TaskMember >── User               (participantes)
Task ──< Comment >── User                  (autor)
Task ──< ChecklistItem
Task ──< Attachment >── User               (quem enviou)
Task ──< TaskHistoryEntry >── User         (quem alterou)
User ──< Notification (destinatário) >── Task (opcional)

User ──< RecurringTask ──< RecurringTaskWeekday
                       └─< RecurringTaskCompletion   (rotinas pessoais, sem workspace)
```

> 📌 Todos os status, prioridades e papéis usam **enumerações controladas** — nunca strings ou inteiros livres.

Modelo completo, com colunas, constraints e índices de cada entidade, em `specs/*/data-model.md`.

---

<a id="stack-tecnológica"></a>
## 🧰 Stack tecnológica

### 🔹 Backend

| Tecnologia                          | Papel                                            |
| ----------------------------------- | ------------------------------------------------ |
| **Python 3.13**                     | Linguagem                                        |
| **FastAPI**                         | Framework web + documentação OpenAPI automática  |
| **SQLAlchemy 2.0**                  | ORM                                              |
| **Alembic**                         | Migrações de banco versionadas                   |
| **PostgreSQL 15+**                  | Banco de dados relacional                        |
| **Pydantic v2 / Pydantic Settings** | Validação de schemas e configuração centralizada |
| **PyJWT + bcrypt**                  | Autenticação (JWT) e hashing de senha            |
| **Pytest + pytest-cov**             | Testes unitários e de integração, com cobertura  |

### 🔹 Frontend

| Tecnologia                           | Papel                                                                  |
| ------------------------------------ | ---------------------------------------------------------------------- |
| **React 19 + TypeScript**            | UI, com tipagem estrita em toda a base                                 |
| **Vite**                             | Build e dev server                                                     |
| **React Router**                     | Roteamento e guardas de rota protegida                                 |
| **Axios**                            | Cliente HTTP com interceptors (token, tratamento de erro centralizado) |
| **shadcn/ui (Radix + Tailwind CSS)** | Componentes acessíveis e sistema de design                             |
| **Vitest + React Testing Library**   | Testes de componente                                                   |

### 🔹 Infraestrutura

Docker + Docker Compose (`db`, `backend`, `frontend`) para subir o ambiente completo com um único comando — ver [Como executar](#como-executar).

---

<a id="estrutura-do-projeto"></a>
## 📂 Estrutura do projeto

```text
TaskFlow/
├── backend/
│   ├── alembic/            # migrações versionadas
│   ├── app/
│   │   ├── core/           # config, logging, exceptions, security, scheduler
│   │   ├── database/       # engine, session
│   │   ├── models/         # entidades SQLAlchemy
│   │   ├── schemas/        # contratos Pydantic (entrada/saída da API)
│   │   ├── repositories/   # único ponto de acesso ao banco
│   │   ├── services/       # regras de negócio
│   │   ├── routes/         # 17 módulos, 54 endpoints — sem regra de negócio
│   │   ├── dependencies/   # autenticação e autorização (por camada de acesso)
│   │   ├── enums/          # valores controlados (status, roles, prioridade...)
│   │   └── utils/
│   └── tests/
│       ├── unit/
│       └── integration/
├── frontend/
│   └── src/
│       ├── pages/, components/, layouts/
│       ├── hooks/, services/, contexts/
│       └── types/, utils/
├── specs/                     # spec, plan, research, data-model, contracts e tasks de cada feature
└── .specify/                  # Constitution e templates do Spec Kit
```

Camadas e convenções de nomenclatura por camada estão detalhadas na [TaskFlow Constitution](.specify/memory/constitution.md).

---

<a id="como-executar"></a>
## 🚀 Como executar

### 📋 Pré-requisitos

* Python 3.13
* Node.js 24+ e npm
* PostgreSQL 15+ (nativo ou via Docker)

---

### Opção A — Backend e frontend nativos

```bash
# Banco de dados: criar um banco PostgreSQL vazio (ex.: taskflow)

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # editar DATABASE_URL, JWT_SECRET_KEY etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (em outro terminal)
cd frontend
npm install
copy .env.example .env        # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

### 🔗 Endpoints

* **Frontend:** http://localhost:5173
* **API:** http://localhost:8000/api/v1
* **Documentação interativa:** http://localhost:8000/docs (Swagger) e `/redoc`

Ao subir, o backend já inicia automaticamente a tarefa periódica que gera notificações de prazo próximo (`DUE_SOON`) — nenhum worker separado é necessário.

---

### Opção B — Docker Compose

```bash
docker compose up --build
```

Sobe três serviços:

| Serviço    | Tecnologia |  Porta |
| ---------- | ---------- | -----: |
| `db`       | PostgreSQL | `5432` |
| `backend`  | FastAPI    | `8000` |
| `frontend` | Vite       | `5173` |

O `backend` roda `alembic upgrade head` automaticamente.

Roteiro de validação manual completo (16 passos, cobrindo as principais User Stories) em [`specs/001-taskflow-mvp/quickstart.md`](specs/001-taskflow-mvp/quickstart.md).

---

<a id="autenticação-e-segurança"></a>
## 🔐 Autenticação e segurança

* Sessão via **JWT** (`Authorization: Bearer`), validada a cada requisição — inclusive revalidando se a conta segue ativa, mesmo com um token ainda não expirado.
* Senhas com hash **bcrypt**; nunca expostas em nenhum schema de resposta.
* Autorização em camadas, aplicada via `dependencies` do FastAPI (nunca checada ad-hoc dentro de uma rota): pertencimento a workspace, papel dentro do workspace, participação numa tarefa, pertencimento a projeto.
* Recurso sem acesso responde **`404`**, não `403` — quem não tem permissão não descobre que o recurso existe.
* O **System Admin** é uma role de plataforma isolada por design: não concede nenhum acesso a workspace, projeto ou tarefa por si só.

---

<a id="engenharia-orientada-a-especificação"></a>
## 📐 Engenharia orientada a especificação

O desenvolvimento do TaskFlow segue um fluxo baseado no **Spec Kit**:

```text
specify
   ↓
clarify
   ↓
plan
   ↓
tasks
   ↓
implement
```

Cada funcionalidade possui seu próprio conjunto de documentos:

```text
spec.md
    ↓
plan.md
    ↓
research.md
    ↓
data-model.md
    ↓
contracts/
    ↓
tasks.md
    ↓
quickstart.md
```

Isso mantém rastreável a relação entre:

**requisito → decisão técnica → implementação → validação.**

### 📋 Features documentadas

| Feature               | Descrição                      |
| ---------------------- | ------------------------------- |
| `001-taskflow-mvp`    | MVP principal do sistema       |
| `002-tarefas-fixas`   | Rotinas pessoais recorrentes   |
| `003-membros-projeto` | Controle de acesso por projeto |

---

<a id="qualidade-e-testes"></a>
## 🧪 Qualidade e testes

```bash
# Backend — IMPORTANTE: DATABASE_URL deve apontar para um banco de teste
# descartável cujo nome contenha "test" (ex.: taskflow_test) — a suíte roda
# migrações destrutivas e se recusa a rodar contra um banco sem esse padrão.

cd backend
pytest                       # unit + integration
pytest --cov=app             # com cobertura

# Frontend
cd frontend
npm run test                 # Vitest + React Testing Library
npm run build                # build de produção (tsc -b && vite build)
```

### 📊 Testes

| Suíte                       |  Testes |
| ---------------------------- | ------: |
| Backend (unit + integração) | **686** |
| Frontend (componente)       |  **93** |
| **Total**                   | **779** |

> ✅ Toda regra de negócio crítica tem cobertura automatizada — regra do projeto, não exceção: nenhuma feature é considerada concluída sem testes que a validem (`TaskFlow Constitution`, Princípio VIII).

---

<a id="documentação-de-cada-feature"></a>
## 📚 Documentação de cada feature

Cada funcionalidade em `specs/<feature>/` documenta, na ordem em que foi produzida — o rastro completo entre a intenção e o código:

```text
spec.md          → especificação: user stories, critérios de aceite, requisitos
plan.md          → plano técnico e checagem de aderência à Constitution
research.md      → decisões técnicas e alternativas consideradas
data-model.md    → entidades, colunas, constraints, índices
contracts/       → contrato da API (rotas, request/response, códigos de erro)
tasks.md         → tarefas de implementação, rastreáveis e com progresso registrado
quickstart.md    → roteiro de validação manual ponta a ponta
```

### Features

| Feature                                            | Descrição                                                                             |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [`001-taskflow-mvp`](specs/001-taskflow-mvp)       | MVP completo: contas, tarefas, workspaces, projetos, colaboração, notificações, admin |
| [`002-tarefas-fixas`](specs/002-tarefas-fixas)     | Rotinas pessoais recorrentes                                                          |
| [`003-membros-projeto`](specs/003-membros-projeto) | Visibilidade de projeto restrita por convite                                          |

---

<a id="status-do-projeto"></a>
## 📈 Status do projeto

* ✅ **`001-taskflow-mvp`** — implementado, testado e validado de ponta a ponta (13 User Stories; busca/filtros dedicados no frontend conscientemente adiados).
* ✅ **`002-tarefas-fixas`** — implementado, testado e validado.
* ✅ **`003-membros-projeto`** — implementado, testado e validado.

Todas as três features têm o roteiro de validação de `quickstart.md` executado contra o backend e o frontend reais (não simulados), com o resultado registrado no `tasks.md` correspondente.

---

<a id="autor"></a>
## 👨‍💻 Autor

Desenvolvido por [**Yuri**](https://github.com/YuriiHayakawa).

---
