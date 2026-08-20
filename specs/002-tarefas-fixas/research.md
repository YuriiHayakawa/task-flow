# Research: Tarefas Fixas (Rotinas Pessoais Recorrentes)

**Feature**: `002-tarefas-fixas` | **Spec**: [spec.md](./spec.md)

Decisões técnicas que resolvem os pontos em aberto do `Technical Context` de `plan.md`. Nenhuma
decisão aqui contraria a spec — todas resolvem *como* implementar o que a spec já definiu.

## #1 — Como armazenar os dias da semana de uma recorrência semanal

**Decision**: uma tabela filha `recurring_task_weekdays` (`recurring_task_id` FK, `weekday`
`SMALLINT` 0-6), com `UNIQUE(recurring_task_id, weekday)` — mesmo padrão relacional já usado no
projeto para "vários valores pertencentes a um pai" (ex.: `ChecklistItem` pertence a `Task`,
`TaskMember` pertence a `Task`).

**Rationale**: mantém a mesma linguagem de modelagem já estabelecida no TaskFlow (tabela filha, não
um tipo de coluna novo) — Constitution V exige reaproveitar padrão consolidado antes de introduzir
um novo. Também mantém a consulta legível (`SELECT weekday FROM recurring_task_weekdays WHERE
recurring_task_id = ...`) e a validação de "pelo menos um dia selecionado" simples (contagem de
linhas no Service, mesmo espírito de `TaskMemberService`).

**Alternatives considered**:
- **Bitmask** (`INTEGER`, um bit por dia da semana): mais compacto, mas exige lógica de bit a bit
  nunca usada em nenhum outro lugar do projeto — pior legibilidade (Constitution II) para um ganho
  de armazenamento irrelevante (volume esperado: dezenas de linhas por usuário).
  Rejeitada.
- **Coluna `ARRAY` do Postgres**: nenhuma tabela do TaskFlow usa hoje um tipo array — seria o
  primeiro precedente do tipo no projeto, contrariando Constitution V ("não criar novo padrão
  quando um padrão consolidado já resolve"). Rejeitada.

## #2 — Como representar "concluída/pendente" de cada ocorrência (e permitir reset automático)

**Decision**: uma tabela `recurring_task_completions` (`recurring_task_id` FK, `occurrence_date`
`DATE`, `completed_at` `TIMESTAMPTZ`), com `UNIQUE(recurring_task_id, occurrence_date)`. **Existir
uma linha** para a data de hoje = concluída hoje; **não existir** = pendente. Marcar como concluída
é um `INSERT`; marcar como pendente de novo é um `DELETE` da linha do dia.

**Rationale**: resolve literalmente sozinho o FR-006 (cada ocorrência com estado independente) e o
FR-007/reset automático (uma data nova nunca tem linha — "pendente" é o estado natural, não algo que
precisa ser "resetado" por nenhum job/cron) e entrega de graça o FR-014 (histórico completo de
conclusões, base para um streak futuro sem qualquer migração adicional). A alternativa mais simples
(um único campo `last_completed_date` sobrescrito na própria `recurring_tasks`) foi deliberadamente
rejeitada, mesmo sendo mais simples: ela cumpriria a spec desta versão, mas tornaria o FR-014
impossível de atender sem uma migração destrutiva depois (dados históricos já teriam sido
sobrescritos e perdidos) — e o próprio texto da spec pede explicitamente esse cuidado.

**Alternatives considered**:
- **Campo único `last_completed_date` na tabela pai**: mais simples, porém sem histórico — rejeitada
  pelo motivo acima.
- **Job periódico que "reseta" um campo `is_done` todo início de ciclo**: introduziria um scheduler
  novo (o TaskFlow já tem um, `core/scheduler.py`, para `DUE_SOON` — reaproveitável em tese), mas é
  complexidade desnecessária: o modelo de log não precisa de nenhum job para "resetar" nada.
  Rejeitada.

## #3 — Regra de recorrência mensal em meses mais curtos que o dia configurado

**Decision**: quando o mês corrente não tem o dia configurado (ex.: dia 31 em abril, dia 30/31 em
fevereiro), a ocorrência do mês cai no **último dia do mês** — calculado com
`calendar.monthrange(year, month)[1]` (biblioteca padrão do Python, nenhuma dependência nova).

**Rationale**: é a convenção mais comum e menos surpreendente para o usuário (mesmo comportamento de
sistemas de cobrança recorrente do dia a dia) — já adotada explicitamente na spec (FR-004, Edge
Cases). `calendar.monthrange` é solução de biblioteca padrão, sem dependência nova (Constitution V).

## #4 — Formato do endpoint que marca a ocorrência de hoje como concluída/pendente

**Decision**: `POST /api/v1/recurring-tasks/{id}/completions` (marca hoje como concluída) e `DELETE
/api/v1/recurring-tasks/{id}/completions` (desmarca hoje) — **sem** data no corpo/path. A data usada
é sempre `today_in_app_timezone()`, calculada no servidor.

**Rationale**: reaproveita o utilitário `app/utils/timezone.py::today_in_app_timezone()` já existente
(usado por `DashboardService`) — nenhuma lógica de tempo duplicada (mesmo motivo documentado no
próprio utilitário). Não aceitar uma data vinda do cliente é deliberado: o cliente nunca deve poder
marcar conclusão de uma data arbitrária (passada ou futura) — reforça Constitution IV (backend como
única autoridade). `POST`/`DELETE` sobre a mesma sub-rota de coleção segue o mesmo estilo REST já
usado em `tasks/{id}/members` (`POST` adiciona, `DELETE` remove).

## #5 — Onde a aba "Tarefas Fixas" vive no frontend

**Decision**: uma nova rota `/tasks/recurring`, irmã da rota existente `/tasks` (o quadro kanban
atual, inalterado). Uma nova barra de abas (`TasksTabs.tsx`) alterna entre as duas rotas, com o
mesmo tratamento visual (sublinhado azul, `Link` + `useLocation`) já usado em `AuthTabs.tsx` — mas
`AuthTabs` em si não é reaproveitado diretamente porque está fixado nas rotas `/login`/`/register`
(sem generalização de props); um componente novo, porém seguindo o **mesmo padrão visual e mecanismo
já validado** (abas = rotas reais, não um `useState` de aba ativa), evita introduzir um segundo jeito
de fazer abas no projeto.

**Rationale**: rotas reais (em vez de estado local) mantêm o comportamento de voltar/avançar do
navegador e permitem link direto para `/tasks/recurring` — mesma vantagem já obtida em `AuthTabs`.

**Alternatives considered**: alternar entre as duas visões com `useState` na mesma rota `/tasks` —
mais simples de implementar, porém diverge do único padrão de abas já validado no projeto (rotas).
Rejeitada.

## #6 — Autorização

**Decision**: uma única dependency nova, `require_recurring_task_owner` (em
`app/dependencies/task_authorization.py`, junto das demais dependencies de tarefa) — carrega a
`RecurringTask` pelo `id` do path e `404` se não existir **ou** se `owner_id != current_user.id`.
Sem níveis de visibilidade/colaboração/administração (ao contrário de `Task`) porque uma Tarefa Fixa
nunca é visível a ninguém além do dono (FR-011) — um único nível já cobre 100% dos casos.

**Rationale**: reaproveita o padrão de nomenclatura `require_<recurso>_<regra>` já estabelecido
(Constitution IX) e o padrão de "404, nunca 403, para quem não tem acesso" já estabelecido em
`contracts/_conventions.md`.
