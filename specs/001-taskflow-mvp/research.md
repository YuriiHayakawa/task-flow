# Research: TaskFlow MVP

**Feature**: `001-taskflow-mvp` | **Date**: 2026-07-10 (revisado)

Este documento consolida as decisões técnicas necessárias para fechar os itens da stack
oficial que não determinam, por si só, uma escolha única de biblioteca ou padrão. O
projeto é greenfield (nenhum código de `backend/` ou `frontend/` existe ainda), então não
há padrão prévio no repositório a ser respeitado — as decisões abaixo estabelecem o
padrão a partir de agora, conforme a Constitution (Princípio V).

> **Revisão 2 (2026-07-10)**: decisões #1, #2, #8, #9, #10 e #14 são novas ou foram
> reescritas nesta revisão para refinar comportamentos que a primeira versão do plano
> deixava implícitos ou simplificados demais. As demais decisões (#3 a #7, #11 a #13, na
> numeração desta revisão) foram preservadas ou apenas reforçadas.

## 1. Comportamento de conta desativada (login e requisições autenticadas)

- **Decision**: uma tentativa de login em uma conta com `is_active = false` retorna um
  erro **distinto** do erro de credenciais inválidas: `403 FORBIDDEN`, código
  `ACCOUNT_DISABLED`, mensagem explícita ("Esta conta está desativada."). Credenciais
  incorretas (e-mail inexistente ou senha errada) continuam retornando `401
  UNAUTHORIZED`, código `INVALID_CREDENTIALS`, mensagem genérica. Para requisições
  autenticadas, a dependency `get_current_user` MUST reconsultar `User.is_active` no
  banco a cada requisição (nunca confiar apenas no fato de o JWT ainda não ter expirado)
  e, se `false`, retornar o mesmo `403 ACCOUNT_DISABLED`.
- **Rationale**: requisito explícito do produto — o usuário precisa entender que sua
  conta foi desativada, não apenas que "as credenciais estão erradas". Verificar
  `is_active` a cada requisição (não só no login) é o único jeito de garantir que uma
  desativação feita pelo System Admin **enquanto o usuário já tem um token válido**
  derrube o acesso imediatamente (o JWT em si não é revogado — é o `is_active` que age
  como uma revogação de fato).
- **Trade-off explícito assumido**: a versão anterior deste plano usava uma mensagem
  genérica também para conta desativada, para não permitir que um atacante descubra, por
  enumeração, se um e-mail existe e está desativado. Esta revisão **substitui
  deliberadamente** essa escolha por instrução direta de produto: a clareza para o
  usuário legítimo foi priorizada sobre essa mitigação específica de enumeração. Isso é
  aceitável no MVP porque (a) desativação é uma ação rara/administrativa, não um estado
  comum, e (b) a superfície de enumeração já existe de forma equivalente em
  `POST /auth/register` (que informa e-mail duplicado). Registrado aqui para
  rastreabilidade da decisão, não é necessário ação adicional.
- **Alternatives considered**: manter mensagem genérica também para conta desativada
  (rejeitado — instrução explícita do produto pede o oposto); invalidar/"queimar" o JWT
  no momento da desativação via uma blocklist de tokens (rejeitado — exigiria estado
  adicional, como Redis ou uma tabela de tokens revogados, não presente na stack e não
  justificado quando a checagem de `is_active` a cada requisição já resolve o problema
  com uma simples consulta ao `User` que o `get_current_user` já precisa fazer de
  qualquer forma).

## 2. Notificações de prazo próximo (DUE_SOON) — tarefa periódica

- **Decision**: substituir a estratégia "lazy" da primeira revisão por uma **tarefa
  periódica em processo**, usando `asyncio` da biblioteca padrão (sem nova dependência):
  um loop iniciado no `lifespan` do FastAPI (`app/main.py` → `app/core/scheduler.py`),
  que a cada `DUE_SOON_CHECK_INTERVAL_SECONDS` (config, default `60`) executa o job. O
  loop é cancelado (`task.cancel()` + `await` do cancelamento) no shutdown do
  `lifespan`, garantindo encerramento limpo sem processo órfão.
- **Execução fora do event loop (SQLAlchemy síncrono dentro de um loop `asyncio`)**: o
  código de negócio (`NotificationService.generate_due_soon_notifications`) usa Sessão
  síncrona do SQLAlchemy (decisão #5) e faz I/O bloqueante (rede para o Postgres). Para
  não bloquear o event loop do `asyncio` que também serve requisições HTTP, cada tick do
  loop chama a função de execução síncrona via `await asyncio.to_thread(run_due_soon_job)`
  — `run_due_soon_job` roda em uma thread do executor padrão, nunca diretamente na
  coroutine do loop principal. Não é necessário um executor dedicado além do padrão do
  `asyncio` (o volume de trabalho — um job leve a cada 60s — não justifica um pool
  próprio).
- **Sessão e conexão dedicadas por execução**: `run_due_soon_job()` (síncrona, roda na
  thread) segue este fluxo, com a conexão que sustenta o advisory lock mantida ativa
  durante toda a seção protegida:
  1. Abre uma **conexão dedicada** do engine (`connection = engine.connect()`) — não uma
     `Session` diretamente, porque o advisory lock (`pg_try_advisory_lock`) é vinculado
     à conexão física do Postgres, e essa mesma conexão precisa permanecer aberta e sem
     ser devolvida ao pool entre o `LOCK` e o `UNLOCK`.
  2. `got_lock = connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key":
     DUE_SOON_LOCK_KEY}).scalar()`. Se `False`, loga `DEBUG` e encerra (via `finally`,
     fecha a conexão) sem processar nada.
  3. Se o lock foi obtido, cria uma **`Session` própria desta execução**, vinculada a
     essa mesma conexão (`Session(bind=connection)`) — nunca reaproveita uma Session de
     outra parte da aplicação.
  4. Chama `NotificationService.generate_due_soon_notifications(session, now=...)`
     dentro de `try/except/finally`: sucesso → `session.commit()`; exceção → captura,
     loga `ERROR` (contexto: nome do job, timestamp, mensagem — sem dados sensíveis) e
     `session.rollback()`; em ambos os casos, `finally: session.close()` — a Session é
     sempre fechada, mesmo em erro.
  5. **Sempre**, em um `finally` externo ao passo 3-4, libera o lock:
     `connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key":
     DUE_SOON_LOCK_KEY})`.
  6. Em um `finally` mais externo ainda, fecha a conexão (`connection.close()`),
     devolvendo-a ao pool.
  Essa pilha de `try/finally` aninhados garante que o lock é liberado e a conexão/Session
  fechadas mesmo se `generate_due_soon_notifications` lançar uma exceção inesperada.
- **Como evitar execução duplicada (uma ou múltiplas instâncias da API)**: com **uma
  única instância** de backend (alvo do MVP — Docker Compose local), o lock nunca
  encontra contenção — cada tick simplesmente o obtém e libera. Com **múltiplas
  instâncias** (cenário futuro, não o padrão do MVP, mas suportado sem mudança de
  código): cada instância roda seu próprio loop `asyncio` de forma independente; a cada
  tick, cada uma tenta `pg_try_advisory_lock` com a **mesma chave fixa**
  (`DUE_SOON_LOCK_KEY`, configurável) — o Postgres garante que apenas uma conexão por
  vez mantém esse lock. As demais instâncias recebem `False` naquele tick e pulam
  silenciamente (log `DEBUG`); não há coordenação além do que o próprio Postgres já
  oferece, e não há garantia de que seja sempre a mesma instância a "vencer" — apenas a
  garantia de que nunca duas processam o mesmo tick simultaneamente.
- **Dev vs. produção**: mesmo mecanismo em ambos — é apenas uma tarefa `asyncio` presa
  ao processo da aplicação. Em desenvolvimento (`uvicorn --reload`), o processo worker
  real do Uvicorn é quem roda o loop (comportamento padrão do Uvicorn/FastAPI já isola
  o processo de reload do processo de trabalho); nenhuma configuração extra é
  necessária.
- **Deduplicação lógica (idempotência por tarefa)**: adicionado o campo
  `Task.due_soon_notified_for` (data, nullable — ver `data-model.md`), que armazena o
  valor de `due_date` para o qual a notificação `DUE_SOON` já foi gerada. A query do job
  seleciona tarefas onde `status != DONE` **e** `due_date` não é nulo **e** `due_date`
  está dentro da janela configurada (`DUE_SOON_WINDOW_HOURS`, default `24`) **e**
  `due_soon_notified_for IS DISTINCT FROM due_date`. Para cada tarefa selecionada, cria a
  `Notification` (tipo `DUE_SOON`) para o responsável e, **na mesma transação**, atualiza
  `due_soon_notified_for = due_date`.

  **Regras completas de `due_soon_notified_for`** (cada uma coberta por teste de
  integração dedicado — ver `plan.md`, seção Testes):

  | Regra | Comportamento |
  |---|---|
  | `due_date IS NULL` | `due_soon_notified_for` MUST ser `NULL` (não há prazo, não há o que rastrear); o job nunca seleciona tarefas sem `due_date` |
  | `due_date` é alterado (`TaskService.update`) | `due_soon_notified_for` MUST ser resetado para `NULL` na mesma transação da alteração, independentemente do valor anterior — permite nova notificação para o novo prazo |
  | Tarefa está `DONE` | O job MUST NOT gerar `DUE_SOON` para tarefas concluídas — filtro `status != DONE` na query exclui-as, mesmo que `due_soon_notified_for IS DISTINCT FROM due_date` fosse verdadeiro |
  | Job executado repetidamente (mesmo ciclo de prazo) | Não duplica — a segunda execução encontra `due_soon_notified_for == due_date` e a tarefa não é reselecionada |
  | Notification criada + `due_soon_notified_for` atualizado | Sempre na mesma transação/`commit()` — nunca uma sem a outra (evita um registrar sem o outro em caso de falha parcial) |
  | Tarefa reaberta (`DONE` → `PENDING`/`IN_PROGRESS`) **sem** alterar `due_date` | `due_soon_notified_for` permanece com o valor já gravado (reabrir sozinho não o reseta) — se ainda igual a `due_date`, **não** gera nova notificação, mesmo que a tarefa volte a ficar ativa dentro da janela |
  | Tarefa reaberta **e** `due_date` alterado na mesma operação | A alteração de `due_date` reseta `due_soon_notified_for` para `NULL` (regra acima, incondicional) — a tarefa volta a ser elegível para uma nova notificação `DUE_SOON` no próximo ciclo do job, agora que está ativa novamente |
- **Atende ao Success Criterion de 1 minuto (SC-004)**: com intervalo padrão de 60s, o
  pior caso é a notificação aparecer até ~60s após a tarefa entrar na janela de "prazo
  próximo" — dentro do critério de aceitação.
- **Tratamento de falhas**: cada execução é envolvida em `try/except` amplo; uma
  exceção em uma execução é registrada via logging estruturado (nível `ERROR`, com
  contexto: nome do job, timestamp, mensagem) e **não** derruba o loop — a próxima
  execução ocorre normalmente no próximo intervalo. Uma falha ao processar uma tarefa
  específica dentro do lote não MUST interromper o processamento das demais (loop
  interno também isola exceções por tarefa).
- **Logging**: início e fim de cada execução (nível `INFO`, com contagem de
  notificações criadas); `DEBUG` quando o lock não é obtido; `ERROR` em exceções (ver
  acima). Nenhum dado sensível é logado.
- **Como testar**: o loop `asyncio` em si não é testado diretamente (é só um
  agendador); duas unidades são testadas separadamente:
  - `NotificationService.generate_due_soon_notifications(session, now=...)` — chamada
    diretamente em testes de integração com um "agora" controlado (parâmetro explícito
    de referência temporal, sem depender de `freezegun`/mocks de tempo do sistema),
    verificando as regras completas listadas na seção "Regras de
    `due_soon_notified_for`" abaixo.
  - `run_due_soon_job()` (a função que adquire/libera o advisory lock) — testada
    simulando uma segunda "instância": um teste de integração abre uma conexão own
    separada, adquire manualmente o mesmo advisory lock (`pg_advisory_lock`), então
    chama `run_due_soon_job()` e verifica que ele **não** processa nenhuma tarefa nem
    cria notificações (early-return por lock não obtido); em seguida libera o lock
    manual e confirma que uma nova chamada a `run_due_soon_job()` processa normalmente.
    Isso cobre diretamente o requisito de "impedir execuções simultâneas".
- **Rationale**: cumpre o requisito de intervalo ≤ 1 minuto sem introduzir Celery/Redis/
  RabbitMQ — infraestrutura desproporcional para um único job leve em um MVP de
  instância única. `asyncio` é biblioteca padrão (zero dependência nova); o advisory
  lock do Postgres reusa infraestrutura já presente na stack.
- **Alternatives considered**: **APScheduler** (rejeitado — dependência nova cuja única
  vantagem sobre um loop `asyncio` simples seria agendamento cron-like mais expressivo,
  não necessário para um intervalo fixo de 60s); **Celery + beat + broker** (rejeitado —
  infraestrutura distribuída pesada, exatamente o que a instrução pede para evitar);
  **cron do sistema operacional + script CLI** (rejeitado — não é portável entre Windows
  de desenvolvimento e o container Linux de produção sem duplicar lógica de agendamento,
  e não garante granularidade de 60s de forma simples); **`ThreadPoolExecutor` dedicado**
  em vez de `asyncio.to_thread` (rejeitado — `to_thread` já usa o executor padrão do
  loop, suficiente para um único job leve a cada 60s; um executor dedicado só se
  justificaria com múltiplos jobs concorrentes de longa duração, não é o caso aqui);
  rodar a lógica síncrona diretamente na coroutine do loop sem `to_thread` (rejeitado —
  bloquearia o processamento de requisições HTTP durante a execução do job, violando o
  requisito explícito de não executar operações bloqueantes diretamente no event loop).

## 3. Hash de senha

- **Decision**: usar a biblioteca `bcrypt` diretamente (sem `passlib`).
- **Rationale**: `passlib` está com manutenção estagnada e possui incompatibilidades
  conhecidas com versões recentes do `bcrypt` (>=4.x). Usar `bcrypt` diretamente é mais
  simples, tem uma API mínima (`hashpw`/`checkpw`) suficiente para o requisito (FR-001,
  FR-002) e evita uma dependência extra sem necessidade.
- **Alternatives considered**: `passlib[bcrypt]` (rejeitado — problemas de manutenção);
  `argon2-cffi` (rejeitado — mais forte, mas introduz dependência nativa adicional sem
  benefício claro para o escopo do MVP).

## 4. Tokens de autenticação (JWT)

- **Decision**: usar `PyJWT` para gerar/validar access tokens JWT assinados com HS256,
  segredo lido de `core/config.py` (variável de ambiente), com expiração configurável
  (padrão: 60 minutos). Conforme decisão #1, o JWT em si nunca é revogado antes de
  expirar — a checagem de `is_active` a cada requisição é o mecanismo de invalidação
  efetiva para contas desativadas.
- **Rationale**: `PyJWT` é ativamente mantido, tem API mínima e cobre integralmente o que
  a Constitution e a spec exigem (FR-002; Constitution: JWT para autenticação). Não há
  necessidade de refresh tokens ou múltiplos algoritmos no MVP.
- **Alternatives considered**: `python-jose[cryptography]` (rejeitado — superset de
  funcionalidades, como suporte a JWE, não necessário no MVP, e dependências extras de
  criptografia).
- **Out of scope**: refresh tokens, blacklist de tokens por jti, múltiplos dispositivos
  — não exigidos pela spec; se necessários no futuro, exigem nova decisão técnica.

## 5. ORM e driver de banco de dados

- **Decision**: SQLAlchemy 2.0 (estilo declarativo tipado com `Mapped`/`mapped_column`),
  modo **síncrono**, com driver `psycopg[binary]` (psycopg 3) para PostgreSQL.
- **Rationale**: SQLAlchemy 2.0 é o padrão de mercado para FastAPI e já exigido pela stack
  oficial. Modo síncrono é suficiente para a escala do MVP (sem requisito de alta
  concorrência na spec) e evita a complexidade adicional de sessões assíncronas, pools
  assíncronos e testes assíncronos — alinhado ao Princípio "evitar overengineering".
  `psycopg` 3 é o driver recomendado atualmente pela documentação do SQLAlchemy 2.0 para
  PostgreSQL.
- **Nota (revisão 2)**: o job periódico da decisão #2 roda em uma tarefa `asyncio`, mas
  chama `NotificationService` de forma síncrona (via `run_in_executor`/chamada direta a
  uma sessão síncrona do SQLAlchemy), preservando a decisão de ORM síncrono — não é
  necessário adotar SQLAlchemy assíncrono só por causa do agendador.
- **Alternatives considered**: SQLAlchemy assíncrono + `asyncpg` (rejeitado — complexidade
  adicional não justificada pela escala/requisitos atuais do MVP).

## 6. Paginação de listagens

- **Decision**: paginação por `page`/`page_size` (offset-based) em todos os endpoints de
  listagem (tarefas, projetos, membros, notificações, histórico), com `page_size` máximo
  configurável (padrão 20, máximo 100).
- **Rationale**: mais simples de implementar, testar e documentar via OpenAPI do que
  paginação por cursor; suficiente para o volume de dados esperado de um MVP.
- **Alternatives considered**: paginação por cursor/keyset (rejeitada — complexidade
  extra não justificada nesta fase).

## 7. Cálculo do Dashboard

- **Decision**: contagens do dashboard (pendentes, em andamento, concluídas, atrasadas,
  vencendo hoje) são calculadas **sob demanda**, via consultas agregadas (`COUNT`
  agrupado por status, mais filtros de `due_date` para atrasadas/vencendo hoje,
  calculados na timezone da aplicação — ver decisão #9) no `TaskRepository`, sem tabela
  materializada ou cache.
- **Rationale**: atende diretamente ao requisito de que as contagens reflitam o estado
  real no momento da consulta (FR-050, SC-009); evita a complexidade de manter uma
  estrutura de cache sincronizada.
- **Alternatives considered**: contagem pré-agregada/cache (rejeitada — risco de
  inconsistência e complexidade de invalidação sem benefício mensurável no MVP).

## 8. Visibilidade versus participação em uma tarefa

- **Decision**: distinguir explicitamente três níveis de acesso a uma tarefa de
  workspace: **(a) visibilidade** (`GET` da tarefa e de seus comentários/checklist/
  anexos/histórico) — qualquer membro do workspace; **(b) colaboração** (criar
  comentário, criar/alterar item de checklist, enviar anexo) — apenas o responsável
  (`assignee`) e participantes explícitos (`TaskMember`); **(c) administração** (editar
  campos operacionais, excluir a tarefa, gerenciar participantes) — criador, responsável
  (parcialmente, ver decisão #7 do plano) e Workspace Owner/Admin, mesmo que estes
  últimos não sejam participantes explícitos da tarefa. Owner/Admin MUST NOT ser
  adicionados automaticamente como `TaskMember` só por deterem essas roles.
- **Rationale**: evita que qualquer membro do workspace — mesmo sem envolvimento direto
  na tarefa — possa poluir uma tarefa alheia com comentários/anexos/checklist, mantendo
  a visibilidade ampla (necessária para coordenação do time) separada da autoridade de
  colaborar ativamente nela.
- **Nota de consistência com a spec (sinalizada, não corrigida aqui)**: a versão atual
  de `spec.md` (Edge Cases e FR-027/FR-035/FR-037) só exige que o usuário seja **membro
  do workspace** para comentar/anexar/criar checklist, sem mencionar a necessidade de
  ser participante explícito. Esta decisão técnica adota a leitura mais restritiva
  (participante explícito ou responsável), por instrução direta de refinamento do
  produto. Isso é uma **restrição de comportamento em relação à redação literal atual da
  spec**, não apenas um detalhe de implementação — recomienda-se uma pequena atualização
  de `spec.md` (via `/speckit.specify` ou `/speckit.clarify`) para alinhar o texto de
  FR-027/FR-035/FR-037 e os Edge Cases a esta regra antes da fase de `/speckit.tasks`,
  ou aceitar formalmente que o plano é mais restritivo que a spec redigida. Ver resumo
  final para a recomendação explícita.
- **Alternatives considered**: manter "qualquer membro do workspace pode colaborar"
  (rejeitado — é a leitura antiga, agora explicitamente substituída pela instrução de
  refinamento do produto); tornar Owner/Admin participantes implícitos automaticamente
  (rejeitado — o produto quer que a lista de participantes reflita envolvimento real,
  não hierarquia administrativa).

## 9. Timezone e datas

- **Decision**: todo timestamp persistido usa `TIMESTAMPTZ` (UTC) no PostgreSQL. A
  aplicação possui uma timezone configurável via `APP_TIMEZONE` (variável de ambiente,
  `core/config.py`), com padrão `America/Sao_Paulo` para o MVP. Todo cálculo de "hoje",
  "atrasada" e "vencendo hoje" (dashboard, job de notificação de prazo) MUST converter o
  instante atual (UTC) para `APP_TIMEZONE` antes de comparar com `Task.due_date`.
  Respostas da API usam timestamps em ISO 8601 (UTC, sufixo `Z`); o frontend pode
  converter para exibição local, sem alterar nenhuma regra de negócio (a regra é sempre
  avaliada no backend, na timezone configurada). `due_date` continua sendo um campo de
  data pura (sem horário), conforme já definido.
- **Rationale**: sem uma timezone de referência explícita, "vencendo hoje" seria
  ambíguo (o "hoje" do servidor em UTC pode ser um dia diferente do "hoje" percebido
  pelos usuários no Brasil). Fixar a timezone da aplicação (não a do usuário individual)
  é a solução mais simples adequada ao MVP, que não modela fuso horário por usuário.
- **Alternatives considered**: usar UTC puro para "hoje" (rejeitado — produziria datas
  de corte incorretas para usuários no fuso brasileiro, especialmente à noite);
  timezone por usuário (rejeitado — não solicitado pela spec, adicionaria um campo e
  lógica de preferência de usuário fora do escopo do MVP).

## 10. Unicidade case-insensitive de e-mail

- **Decision**: normalizar o e-mail para lowercase no `UserService` (cadastro e
  atualização de perfil) **e**, como garantia de banco, criar um **índice único sobre
  `lower(email)`** (índice funcional), em vez de adotar a extensão `CITEXT`.
- **Rationale**: `CITEXT` exigiria `CREATE EXTENSION citext` no banco (passo de
  provisionamento adicional, nem sempre disponível sem privilégio de superusuário em
  ambientes gerenciados) e mudaria o tipo de dado da coluna de forma menos padrão/
  portável. Um índice único funcional sobre `lower(email)` usa apenas SQL/Alembic
  padrão, é suportado nativamente pelo SQLAlchemy (`Index` com `text("lower(email)")`),
  e garante a mesma invariante (não pode haver dois `User` cujo e-mail em minúsculas
  coincida) tanto no cadastro quanto na atualização de perfil (FR-053), sem exigir
  privilégios especiais no banco.
- **Alternatives considered**: `CITEXT` (rejeitado — dependência de extensão de banco
  não estritamente necessária); apenas normalizar no código sem constraint de banco
  (rejeitado — não protege contra corrida de cadastro simultâneo com variações de case,
  nem contra qualquer futuro caminho de código que insira sem passar pelo `UserService`).

## 11. Notificações de prazo — mecanismo, ver decisão #2

## 12. Armazenamento de anexos e exclusões controladas

- **Decision**: armazenamento em disco local, em um diretório configurável
  (`ATTACHMENTS_DIR`, via `core/config.py`), com nome de arquivo gerado (UUID + extensão
  original validada) — nunca o nome original do usuário é usado como caminho no disco.
  Metadados (nome original, caminho relativo, tipo MIME, tamanho) persistidos em
  `Attachment`.
- **Exclusão sempre via Service, nunca cascade "cego"**: toda exclusão que afeta anexos
  (exclusão de um anexo individual, de uma tarefa, ou de um workspace) segue o fluxo:
  (1) localizar todos os `Attachment` físicos afetados **antes** de qualquer alteração
  no banco; (2) validar autorização; (3) executar a exclusão dos registros no banco
  dentro de uma transação e fazer `commit()`; (4) **somente após o commit ter sucesso**,
  remover os arquivos físicos correspondentes do disco; (5) se a remoção de um arquivo
  físico falhar, registrar um log `ERROR` com o caminho, `attachment_id` e `task_id`
  afetados (para reconciliação manual posterior) — a resposta da API **não** falha por
  causa disso, pois o estado autoritativo (banco) já está correto e consistente.
- **Rationale da ordem (banco primeiro, disco depois)**: garante que uma falha ao
  excluir o registro no banco (ex.: violação de constraint inesperada) nunca deixa
  arquivos órfãos sem registro correspondente — e uma falha ao excluir o arquivo físico
  (ex.: permissão de sistema de arquivos) nunca deixa o banco em estado inconsistente
  com registros "fantasmas" apontando para nada. O único artefato órfão possível é um
  arquivo físico sem registro de banco (nunca o contrário), que é o cenário mais seguro
  de se reconciliar manualmente (basta varrer `ATTACHMENTS_DIR` por arquivos sem
  `Attachment.storage_path` correspondente).
- **Prevenção de path traversal**: nomes de armazenamento sempre gerados por UUID pelo
  servidor; `original_filename` é usado apenas para exibição/`Content-Disposition`,
  nunca para compor caminho no disco; extensão validada contra lista permitida antes de
  persistir.
- **Limitation**: armazenamento local não é compartilhado entre múltiplas instâncias do
  backend; aceitável para o MVP (execução local/single-instance via Docker Compose).
- **Alternatives considered**: armazenamento em objeto externo (S3-compatible)
  (rejeitado nesta fase — dependência de infraestrutura externa fora da stack oficial);
  excluir arquivo físico antes do commit do banco (rejeitado — se o commit falhar depois,
  o arquivo já estaria perdido sem o registro ter sido de fato removido — pior cenário
  de inconsistência que o escolhido).

## 13. Testes de frontend

- **Decision**: Vitest + React Testing Library.
- **Rationale**: Vitest é a ferramenta de teste com integração nativa ao Vite (já
  presente na stack), sem configuração adicional de bundler; React Testing Library é o
  padrão de mercado para testar componentes React pelo comportamento observável pelo
  usuário.
- **Alternatives considered**: Jest (rejeitado — exigiria configuração adicional de
  transformação para funcionar com Vite/ESM, redundante com o que o Vitest já oferece).

## 14. Gestão de estado no frontend

- **Decision**: nenhuma biblioteca de estado global. Estado de autenticação/sessão via
  `AuthContext`; estado de dados de servidor mantido localmente em cada página/hook via
  `useState`/`useEffect` chamando os `services/` centralizados.
- **Rationale**: o volume de estado compartilhado do MVP (sessão do usuário) é pequeno o
  suficiente para Context puro; introduzir Redux/Zustand ou uma lib de cache de servidor
  não se justifica tecnicamente neste estágio.
- **Alternatives considered**: React Query/TanStack Query (rejeitado nesta fase — pode
  ser reavaliado se a complexidade de re-fetch manual crescer).

## 15. Cliente HTTP do frontend

- **Decision**: Axios, com uma instância única centralizada em `services/httpClient.ts`,
  usando interceptors para (a) anexar o header `Authorization: Bearer <token>`, e (b)
  tratamento centralizado de erros HTTP — incluindo o novo código `ACCOUNT_DISABLED`
  (decisão #1), que MUST disparar logout automático e uma mensagem específica ao usuário
  (distinta do tratamento genérico de `401`/`INVALID_CREDENTIALS`).
- **Rationale**: Axios foi explicitamente permitido pela stack oficial; centralizar em
  um único cliente evita duplicar lógica de autenticação/erro em cada `service`.

## 16. Versão do React

- **Decision**: **React 19** (última versão estável major disponível no início da
  implementação), não React 18.
- **Rationale**: a stack oficial define "React" sem fixar versão; React 19 é a versão
  estável atual recomendada para novos projetos no momento em que este MVP começa a ser
  implementado, com suporte já maduro nas bibliotecas planejadas (React Router 7.x e
  versões recentes de React Router 6.x suportam React 19; Vite + `@vitejs/plugin-react`
  suportam React 19 sem alteração; Vitest + React Testing Library 16.x suportam React
  19). Não há nenhuma dependência planejada que exija React 18 especificamente.
- **Ação de acompanhamento**: ao iniciar a Fase 8 (Frontend) do plano, confirmar as
  versões exatas disponíveis no momento (`package.json`) e ajustar esta decisão apenas
  se alguma biblioteca prevista ainda não suportar React 19 — nesse caso, documentar o
  motivo aqui antes de fixar React 18 como fallback.
- **Alternatives considered**: fixar React 18 "por segurança" (rejeitado — instrução
  explícita do produto para não fixar 18 sem justificativa; React 19 é a escolha correta
  por ser a versão estável vigente sem incompatibilidades conhecidas com a stack
  planejada).

## 17. Soft delete

- **Decision**: não usar um padrão genérico de soft delete. A única exceção é o campo
  `is_active` em `User`. Exclusão de Workspace (Owner-only) é uma exclusão definitiva
  (hard delete) com `ON DELETE CASCADE` para as entidades dependentes, seguindo o fluxo
  controlado por Service da decisão #12 (para anexos). Exclusão de Project **não**
  remove as tarefas associadas (ver decisão #6 do plano) — apenas desvincula
  (`project_id = NULL`), o que tecnicamente não é soft delete (o projeto em si é
  removido de verdade; são as tarefas que sobrevivem por design).
- **Rationale**: soft delete genérico adicionaria complexidade não exigida por nenhum
  requisito da spec.
- **Alternatives considered**: soft delete em todas as entidades (rejeitado).

## 18. Containerização (Docker)

- **Decision**: preparar `Dockerfile` para `backend/` e `frontend/`, mais um
  `docker-compose.yml` na raiz do monorepo com serviços `backend`, `frontend` e `db`
  (PostgreSQL), para uso em desenvolvimento local. Sem pipeline de deploy/produção nesta
  fase.
- **Rationale**: atende ao pedido explícito de preparação para execução local, sem
  introduzir infraestrutura de produção fora do escopo do MVP.

## 19. Histórico e notificações na mesma transação da alteração

- **Decision**: toda alteração relevante de uma tarefa (status, prioridade, prazo,
  responsável) é feita dentro de um único método de `TaskService`, que: (1) aplica a
  alteração via `TaskRepository`, (2) cria a entrada de `TaskHistoryEntry`
  correspondente, e (3) cria as `Notification`s pertinentes (tipo `TASK_CHANGED`) —
  tudo na mesma sessão/transação do SQLAlchemy, com um único `commit()` ao final. Se
  qualquer etapa falhar, a transação inteira é revertida (`rollback`). O mesmo padrão
  se aplica a `CommentService.create` (comentário + notificação `NEW_COMMENT` na mesma
  transação).
- **Rationale**: garante que a tarefa nunca fique com histórico ausente ou notificação
  perdida por falha parcial (FR-041, FR-039). É a abordagem mais simples possível dentro
  da stack já definida (sem fila de mensagens) — nota: isto é distinto da tarefa
  periódica `DUE_SOON` da decisão #2, que roda fora do ciclo de uma requisição HTTP e
  usa sua própria transação por execução.
- **Alternatives considered**: eventos assíncronos via fila (Celery/RabbitMQ)
  (rejeitado — dependência não presente na stack oficial); triggers de banco de dados
  (rejeitado — moveria regra de negócio para o banco, violando o Princípio III da
  Constitution).

## 20. Owner único — bloqueio pessimista na transferência de titularidade

- **Decision**: além da transação única e do índice único parcial
  `ux_workspace_members_one_owner` (`data-model.md`), `WorkspaceMemberService.
  transfer_ownership` adota bloqueio pessimista explícito via `SELECT ... FOR UPDATE`:
  1. Dentro da transação, executa `SELECT * FROM workspace_members WHERE workspace_id =
     :workspace_id AND role = 'OWNER' FOR UPDATE` — trava a linha do Owner atual (não a
     tabela inteira, nem a linha de `Workspace`, para não serializar operações não
     relacionadas ao mesmo workspace, como criação de tarefas).
  2. Reconfirma, com a linha já travada, que `current_user` ainda é o Owner (defesa
     contra corrida entre a checagem de autorização feita antes de entrar na
     transação e o momento em que o lock é obtido).
  3. Executa também `SELECT * FROM workspace_members WHERE workspace_id = :workspace_id
     AND user_id = :new_owner_user_id FOR UPDATE` — trava a linha do membro-alvo, para
     impedir que ele seja removido do workspace concorrentemente por outra transação
     enquanto a transferência está em andamento.
  4. Atualiza a linha do Owner atual para `ADMIN` e a linha do novo Owner para `OWNER`,
     ambas dentro da mesma transação, e faz `commit()`.
- **Serialização de transferências concorrentes**: se duas chamadas a
  `transfer_ownership` (ou uma chamada a `transfer_ownership` concorrente com uma
  tentativa de remoção do Owner ou do membro-alvo) ocorrerem ao mesmo tempo no mesmo
  workspace, a segunda transação **bloqueia** no `SELECT ... FOR UPDATE` até a primeira
  concluir (`commit`/`rollback`). Ao ser liberada, o PostgreSQL reavalia o predicado
  `WHERE role = 'OWNER'` contra a versão mais recente da linha: se a primeira transação
  já mudou essa linha para `ADMIN`, a segunda consulta retorna **zero linhas** — o
  Service interpreta isso como "o Owner mudou durante a operação" e responde `409`
  (conflito, cliente deve tentar novamente com o estado atual), nunca prossegue com uma
  suposição desatualizada de quem é o Owner.
- **Rollback integral**: qualquer falha em qualquer uma das etapas (incluindo violação
  do índice único parcial, timeout de lock, ou erro de integridade) causa `rollback()`
  completo da transação — as duas linhas envolvidas (Owner atual e novo Owner) retornam
  ao estado anterior; não há cenário em que a transação parcialmente aplicada persista.
- **Impossibilidade de zero ou mais de um Owner**: a combinação de (a) bloqueio
  pessimista serializando qualquer alteração concorrente à linha do Owner, (b)
  reconfirmação da identidade do Owner após obter o lock, e (c) o índice único parcial
  como garantia estrutural de última linha de defesa, torna estruturalmente impossível
  persistir um estado com zero Owners (a promoção do novo Owner ocorre na mesma
  transação que rebaixa o antigo — nunca existe um instante committed sem Owner) ou mais
  de um Owner (o índice único parcial rejeitaria o segundo `INSERT`/`UPDATE` com `role =
  'OWNER'`, mesmo que o bloqueio pessimista falhasse por algum motivo).
- **Rationale**: o índice único parcial sozinho já impede a persistência de um estado
  inválido, mas só reage **depois** de uma tentativa de escrita conflitante (via erro de
  banco). O `SELECT ... FOR UPDATE` evita a colisão *antes* dela acontecer, serializando
  as transações candidatas de forma ordenada e previsível, e permite ao Service devolver
  um erro claro (`409`) em vez de depender apenas de capturar uma exceção de
  `IntegrityError` do banco.
- **Alternatives considered**: confiar apenas no índice único parcial sem lock explícito
  (rejeitado — funciona como garantia final, mas produz uma corrida "otimista" em que a
  segunda transação só descobre o conflito ao tentar o `commit`, exigindo tratamento de
  `IntegrityError` como fluxo de controle normal — mais frágil e menos claro que a
  serialização pessimista); `SELECT ... FOR UPDATE` na tabela `Workspace` inteira em vez
  da linha específica de `WorkspaceMember` (rejeitado — serializaria também operações não
  relacionadas a Owner, como criação de tarefas/projetos no mesmo workspace, reduzindo
  concorrência sem necessidade); `SERIALIZABLE` isolation level para toda a transação
  (rejeitado — mais custoso e exigiria tratamento de retry em toda a aplicação para esse
  nível de isolamento, quando o lock pontual já resolve o problema específico).

## 21. Convenção de enums — valores internos em inglês, rótulos em português no frontend

- **Decision (confirmada, não mais pendente)**: todos os enums controlados
  (`WorkspaceRole`, `TaskStatus`, `TaskPriority`, `NotificationType`) usam identificadores
  em **inglês** como valor persistido no banco, transmitido pela API e usado em código
  (`OWNER`, `PENDING`, `HIGH`, `DUE_SOON` etc.). O **frontend** é responsável por mapear
  cada valor para o rótulo em **português** exibido ao usuário (ex.: `PENDING` →
  "Pendente", `IN_PROGRESS` → "Em andamento", `OWNER` → "Dono"), via um dicionário de
  tradução centralizado em `frontend/src/utils/` (ou equivalente), nunca duplicado
  ad-hoc em cada componente.
- **Rationale**: identificadores em inglês são a convenção universal de código
  (nomes de coluna, enum de linguagem, chaves de API) e evitam acoplar o contrato da
  API/schema do banco ao idioma de apresentação — se o produto precisar suportar outro
  idioma no futuro, apenas o dicionário de tradução do frontend muda, sem migração de
  banco nem alteração de contrato de API.
- **Alternatives considered**: persistir os valores já em português (ex.:
  `"Pendente"`, `"Concluída"`) (rejeitado — acopla o schema/API ao idioma, dificulta
  qualquer localização futura, e foge da convenção usual de enums de código); manter os
  dois formatos sincronizados manualmente em cada camada (rejeitado — duplicação
  desnecessária quando um único dicionário no frontend resolve).

## Resumo das dependências novas propostas (com justificativa)

| Dependência | Camada | Justificativa |
|---|---|---|
| `fastapi` | Backend | Definida na stack oficial |
| `sqlalchemy` (2.0) | Backend | Definida na stack oficial |
| `alembic` | Backend | Definida na stack oficial (Constitution VI) |
| `psycopg[binary]` | Backend | Driver PostgreSQL recomendado para SQLAlchemy 2.0 |
| `pydantic` / `pydantic-settings` | Backend | Definidas na stack oficial |
| `pyjwt` | Backend | Ver decisão 4 |
| `bcrypt` | Backend | Ver decisão 3 |
| `pytest` / `pytest-cov` / `httpx` | Backend (testes) | Definida na stack oficial |
| `react` (v19), `typescript`, `vite`, `react-router-dom`, `axios` | Frontend | Ver decisão 16 para a versão do React |
| `vitest`, `@testing-library/react` | Frontend (testes) | Ver decisão 13 |

Nenhuma dependência de scheduler (APScheduler/Celery), fila de mensagens, cache externo
(Redis) ou extensão de banco (CITEXT) é introduzida — decisões #2 e #10 optaram
deliberadamente por soluções dentro da stack já aprovada.
