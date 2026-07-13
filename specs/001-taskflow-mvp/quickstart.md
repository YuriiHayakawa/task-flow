# Quickstart: TaskFlow MVP

**Feature**: `001-taskflow-mvp` | **Date**: 2026-07-10

Este guia descreve como preparar e executar o backend e o frontend localmente **uma vez
que os artefatos desta fase de planejamento tenham sido implementados** (Fases 1-9 do
plano, em `plan.md`). Nenhum destes arquivos/comandos existe ainda no repositório — este
documento é o roteiro de validação a ser seguido durante e após a implementação.

## Pré-requisitos

- Python 3.13 (versão fixada em `backend/Dockerfile`; o `.venv` local em `backend/.venv`
  usa a versão disponível na máquina de desenvolvimento — ver nota de ambiente no
  resumo da Fase 1 caso divirja de 3.13).
- Node.js 24+ (versão padronizada em `frontend/.nvmrc`) e npm, para o frontend Vite/React.
- PostgreSQL 15+ acessível localmente (nativo ou via Docker).
- Docker + Docker Compose (opcional, mas recomendado — ver seção "Via Docker Compose").

## Opção A — Backend e frontend nativos (sem Docker)

### 1. Banco de dados

Criar um banco PostgreSQL vazio (ex.: `taskflow`) e anotar a connection string.

### 2. Backend

```bash
cd backend
python -m venv .venv        # ou reutilizar o .venv já existente na raiz, se preferido
.venv\Scripts\activate       # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# Editar .env: DATABASE_URL, JWT_SECRET_KEY, JWT_EXPIRE_MINUTES, ATTACHMENTS_DIR,
# APP_TIMEZONE (default America/Sao_Paulo), DUE_SOON_CHECK_INTERVAL_SECONDS (default 60),
# DUE_SOON_WINDOW_HOURS (default 24), etc.

alembic upgrade head          # aplica as 4 migrações agrupadas (Constitution VI, ver data-model.md)
uvicorn app.main:app --reload --port 8000
```

Ao subir, o backend inicia automaticamente (via `lifespan`) a tarefa periódica que
gera notificações `DUE_SOON` — nenhum processo/worker separado é necessário (ver
`research.md` #2).

- API disponível em `http://localhost:8000/api/v1`.
- Documentação OpenAPI/Swagger automática em `http://localhost:8000/docs` (Constitution
  VII) e Redoc em `http://localhost:8000/redoc`.

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env
# Editar .env: VITE_API_BASE_URL=http://localhost:8000/api/v1

npm run dev
```

- Aplicação disponível em `http://localhost:5173` (padrão do Vite).

## Opção B — Via Docker Compose

```bash
docker compose up --build
```

Sobe três serviços (ver `research.md` #13):

| Serviço | Porta local | Descrição |
|---|---|---|
| `db` | `5432` | PostgreSQL |
| `backend` | `8000` | FastAPI (roda `alembic upgrade head` automaticamente na inicialização) |
| `frontend` | `5173` | Servidor de desenvolvimento Vite |

Variáveis de ambiente injetadas via `docker-compose.yml` + arquivos `.env` (não
versionados) na raiz de `backend/` e `frontend/`.

## Validação end-to-end do MVP (roteiro manual)

Após backend e frontend estarem no ar, validar o fluxo mínimo cobrindo as User Stories
P1/P2 da spec:

1. **Cadastro/login** (US1): registrar um usuário via tela de cadastro, fazer login.
2. **Tarefa pessoal** (US1): criar uma tarefa pessoal com prazo para hoje; verificar que
   ela aparece no **Dashboard** (US2) em "vencendo hoje".
3. **Workspace** (US3): criar um workspace (o usuário vira Owner); em outra conta,
   confirmar que ela não consegue acessá-lo (`404`) até ser adicionada como membro.
4. **Promoção de role** (US3): promover o segundo usuário a Admin; confirmar que ele
   consegue criar um projeto (US4) e que um terceiro usuário (Member) não consegue.
5. **Tarefa de workspace + participante** (US4/US5): criar uma tarefa dentro do projeto,
   adicionar o Member como participante adicional.
6. **Comentário/checklist/anexo** (US6/US9/US10): adicionar um de cada na tarefa criada.
7. **Histórico** (US12): alterar o status da tarefa e confirmar uma nova entrada em
   `GET /tasks/{id}/history`.
8. **Notificação** (US11): confirmar que o participante recebe uma notificação
   `TASK_CHANGED` referente à alteração acima.
9. **Reatribuição obrigatória** (US3, FR-024/025): tentar remover do workspace um membro
   responsável por uma tarefa ativa e confirmar o bloqueio (`409`); reatribuir a tarefa e
   repetir a remoção com sucesso.
10. **Busca/filtros** (US8): na listagem de tarefas, combinar busca por título com filtro
    de status e ordenação por prazo, confirmando os resultados.
11. **Perfil** (US7): editar o próprio nome/e-mail.
12. **System Admin** (US13): logar com uma conta marcada como `is_system_admin`, listar
    usuários, desativar uma conta, e confirmar que:
    a. essa conta recebe especificamente o erro `ACCOUNT_DISABLED` (não a mensagem
       genérica de credenciais inválidas) ao tentar logar novamente;
    b. se essa conta já tinha um token válido em uso, a próxima requisição autenticada
       com esse token também retorna `ACCOUNT_DISABLED`;
    c. o System Admin continua sem acesso a nenhum workspace do qual não é membro
       comum.
13. **Transferência de titularidade** (US3, refinamento #4): transferir o Owner do
    workspace para outro membro; confirmar que o Owner anterior vira Admin e que uma
    segunda tentativa concorrente de transferência (ou de promoção a Owner por outra
    via) é rejeitada — nunca dois Owners simultâneos.
14. **Exclusão de projeto preserva tarefas** (refinamento #6): excluir um projeto que
    possui tarefas; confirmar que as tarefas continuam existindo no workspace (agora
    sem projeto), com comentários/checklist/anexos/histórico intactos.
15. **Anexos e exclusão controlada** (refinamento #5): anexar um arquivo a uma tarefa,
    excluir a tarefa (ou o workspace), e confirmar no disco (`ATTACHMENTS_DIR`) que o
    arquivo físico foi removido junto com o registro.
16. **Colaboração restrita a participantes** (refinamento #8): com um Member do
    workspace que **não** é responsável nem participante de uma tarefa específica,
    confirmar que ele consegue **ver** a tarefa mas recebe `403` ao tentar comentar,
    anexar ou criar item de checklist nela.

Cada um destes passos corresponde a um Acceptance Scenario em `spec.md` ou a uma regra
de refinamento técnico registrada em `plan.md`/`research.md`/`data-model.md` — usar como
checklist de aceitação manual antes de considerar o MVP pronto para revisão.

## Testes automatizados

```bash
# Backend
cd backend
pytest                       # unit + integration (tests/unit, tests/integration)
pytest --cov=app             # com cobertura

# Frontend
cd frontend
npm run test                 # Vitest + React Testing Library
```

Ver `research.md` (#9) para a justificativa das ferramentas de teste escolhidas.
