# 🚀 TaskFlow

O **TaskFlow** é uma aplicação full stack de gerenciamento de tarefas, projetos e
workspaces — com tarefas pessoais e colaborativas, hierarquia de permissões por
workspace, colaboração em tarefas (comentários, checklists, anexos), notificações
in-app, histórico de alterações, dashboard e administração de usuários da plataforma.

O projeto é construído seguindo o fluxo do [GitHub Spec Kit](https://github.com/github/spec-kit)
(`specify → clarify → plan → tasks → implement`) e a [TaskFlow Constitution](.specify/memory/constitution.md),
documento que rege a arquitetura, as convenções e o processo de desenvolvimento do
projeto. Toda a documentação de cada funcionalidade — especificação, plano técnico,
pesquisa, modelo de dados, contratos de API e roteiro de validação — vive em
[`specs/`](specs/).

---

## 📦 Funcionalidades

### `001-taskflow-mvp` — MVP

- **Contas e tarefas pessoais**: cadastro, login (JWT) e CRUD de tarefas pessoais com
  status, prioridade, prazo e descrição.
- **Dashboard**: contagem de tarefas pendentes/em andamento/concluídas/atrasadas/
  vencendo hoje, combinando tarefas pessoais e de todos os workspaces do usuário, com
  alternador de escopo (Geral/Pessoal/Workspace/Projeto).
- **Workspaces, membros e roles**: Owner/Admin/Member, com Owner sempre único e
  titularidade transferível com segurança sob concorrência.
- **Projetos e tarefas de equipe**: projetos criados por Owner/Admin; tarefas criadas
  por qualquer membro do workspace.
- **Participantes de tarefa**, **comentários**, **checklists** e **anexos**, restritos
  ao responsável e aos participantes explícitos da tarefa (visualização é aberta a
  qualquer membro do workspace).
- **Notificações in-app** de prazo próximo, novos comentários e alterações relevantes
  (status, prioridade, prazo, responsável).
- **Histórico automático** das alterações relevantes de uma tarefa.
- **Perfil do usuário** (nome/e-mail/status da conta).
- **Administração de usuários da plataforma** (System Admin): lista e ativa/desativa
  contas, sem qualquer acesso a workspaces específicos.
- Busca/filtros/ordenação de tarefas existem na API (`GET /tasks`); a tela dedicada de
  busca no frontend foi adiada por decisão de produto (ver `specs/001-taskflow-mvp/tasks.md`,
  Fase 25).

### `002-tarefas-fixas` — Rotinas pessoais recorrentes

Uma segunda aba em "Minhas tarefas" para rotinas pessoais que se repetem (diária,
semanal em dias específicos, ou mensal num dia do mês), com estado de conclusão
independente por ocorrência e reset automático a cada novo ciclo.

### `003-membros-projeto` — Visibilidade restrita por convite

Cada projeto passa a ter sua própria lista de membros: só quem foi explicitamente
adicionado a um projeto o vê e acessa (com o Owner do workspace sempre enxergando
tudo, e o Admin vendo a lista completa mas só abrindo os projetos dos quais participa).
Atribuição de tarefas de projeto fica restrita aos membros desse projeto.

---

## ⚙️ Stack

### Backend

- Python 3.13 + [FastAPI](https://fastapi.tiangolo.com/)
- SQLAlchemy 2.0 + Alembic (migrações versionadas)
- PostgreSQL 15+
- JWT (`PyJWT`) + `bcrypt`
- Pytest + `pytest-cov`

### Frontend

- React 19 + TypeScript + Vite
- React Router, Axios
- shadcn/ui (Radix + Tailwind CSS)
- Vitest + React Testing Library

---

## 🏗️ Estrutura do projeto

```
TaskFlow/
├── backend/
│   └── app/
│       ├── core/            # config, logging, exceptions, security, scheduler
│       ├── database/        # engine, session
│       ├── models/          # entidades SQLAlchemy
│       ├── schemas/         # contratos Pydantic (entrada/saída da API)
│       ├── repositories/    # único ponto de acesso ao banco
│       ├── services/        # regras de negócio
│       ├── routes/          # endpoints FastAPI (sem regra de negócio)
│       ├── dependencies/    # autenticação e autorização
│       ├── enums/           # valores controlados (status, roles, prioridade...)
│       └── utils/
├── frontend/
│   └── src/
│       ├── pages/, components/, layouts/
│       ├── hooks/, services/, contexts/
│       └── types/, utils/
├── specs/                   # specs, plans, contracts e tasks de cada feature
└── .specify/                # Constitution e templates do Spec Kit
```

Camadas e convenções detalhadas na [TaskFlow Constitution](.specify/memory/constitution.md).

---

## 🚀 Como rodar

### Pré-requisitos

- Python 3.13
- Node.js 24+ e npm
- PostgreSQL 15+ (nativo ou via Docker)

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

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1
- Swagger/OpenAPI: http://localhost:8000/docs (Redoc em `/redoc`)

Ao subir, o backend já inicia automaticamente a tarefa periódica que gera notificações
de prazo próximo (`DUE_SOON`) — nenhum worker separado é necessário.

### Opção B — Docker Compose

```bash
docker compose up --build
```

Sobe três serviços: `db` (PostgreSQL, `5432`), `backend` (FastAPI, `8000`, roda
`alembic upgrade head` automaticamente) e `frontend` (Vite, `5173`).

Roteiro completo de validação manual em [`specs/001-taskflow-mvp/quickstart.md`](specs/001-taskflow-mvp/quickstart.md).

---

## ✅ Testes

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

---

## 📚 Documentação de cada feature

Cada funcionalidade em `specs/<feature>/` documenta, na ordem em que foi produzida:
`spec.md` (especificação e critérios de aceite) → `plan.md` (plano técnico) →
`research.md` → `data-model.md` → `contracts/` (contrato da API) → `tasks.md`
(tarefas de implementação, com o progresso de cada uma) → `quickstart.md` (roteiro de
validação).

---

## 🚧 Status

MVP (`001-taskflow-mvp`) e as duas features subsequentes (`002-tarefas-fixas`,
`003-membros-projeto`) implementadas, testadas e validadas de ponta a ponta.
