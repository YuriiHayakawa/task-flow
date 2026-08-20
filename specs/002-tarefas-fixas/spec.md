# Feature Specification: Tarefas Fixas (Rotinas Pessoais Recorrentes)

**Feature Branch**: `002-tarefas-fixas`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Tarefas Fixas (rotinas pessoais recorrentes): uma nova funcionalidade dentro da
tela \"Minhas Tarefas\" do TaskFlow, apresentada como uma segunda aba ao lado do quadro kanban atual
(reaproveitando visualmente o mesmo padrão de abas já usado na tela de login/cadastro). Tarefas que a
pessoa precisa repetir regularmente (diária, semanal em dias específicos, ou mensal num dia específico),
enxutas (sem prioridade/prazo/comentários/checklist/anexos/histórico), escopo só pessoal, sem
streak nesta versão, cada ocorrência com estado independente de concluída/pendente, resetando sozinha a
cada novo ciclo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar e cumprir uma tarefa fixa diária (Priority: P1)

Como usuário, quero cadastrar uma tarefa que se repete todo dia (ex.: "Beber água", "Ir à academia") e
marcá-la como concluída no dia, para não precisar recriá-la manualmente toda manhã.

**Why this priority**: é o núcleo da proposta de valor da funcionalidade — resolve diretamente a dor que
motivou o pedido ("hoje ela teria que recriar manualmente a tarefa a cada dia"). Sem isso, não há
funcionalidade nenhuma.

**Independent Test**: pode ser testado sozinho — cadastrar uma tarefa fixa diária, marcar como concluída
hoje, e confirmar (simulando a virada do dia na timezone da aplicação) que ela volta a aparecer pendente
no dia seguinte, sem qualquer ação do usuário.

**Acceptance Scenarios**:

1. **Given** o usuário está na aba "Tarefas Fixas" dentro de "Minhas Tarefas", **When** cria uma tarefa
   fixa com título "Beber água" e recorrência diária, **Then** ela passa a aparecer na lista, pendente
   para hoje.
2. **Given** uma tarefa fixa diária pendente para hoje, **When** o usuário marca como concluída,
   **Then** ela passa a aparecer como concluída para hoje.
3. **Given** uma tarefa fixa diária já concluída hoje, **When** um novo dia começa (calculado na
   timezone da aplicação), **Then** ela volta a aparecer como pendente para o novo dia, automaticamente.

---

### User Story 2 - Tarefa fixa semanal em dias específicos (Priority: P2)

Como usuário, quero cadastrar uma tarefa que se repete só em dias específicos da semana (ex.:
"Revisar e-mails" às segundas, quartas e sextas), para acompanhar uma rotina que não é diária sem
poluir os outros dias.

**Why this priority**: cobre rotinas que não são diárias (a maioria das rotinas reais de trabalho/
estudo), ampliando o valor da US1 sem a qual a funcionalidade ficaria limitada a hábitos diários.

**Independent Test**: pode ser testado sozinho — cadastrar uma tarefa fixa semanal em dias específicos e
confirmar que ela só apresenta um estado de conclusão ativo (pendente/concluída) nos dias selecionados.

**Acceptance Scenarios**:

1. **Given** o usuário está criando uma tarefa fixa, **When** escolhe recorrência semanal e seleciona
   segunda, quarta e sexta, **Then** o sistema aceita a criação e associa esses três dias à tarefa.
2. **Given** uma tarefa fixa semanal configurada para segunda/quarta/sexta, **When** hoje é um desses
   dias, **Then** ela aparece na lista com um estado de conclusão ativo (pendente ou concluída) para
   hoje, igual a uma tarefa diária.
3. **Given** a mesma tarefa fixa, **When** hoje NÃO é um dos dias selecionados, **Then** ela continua
   visível na lista (para consulta/edição), mas sem um estado de conclusão ativo para hoje.

---

### User Story 3 - Tarefa fixa mensal num dia do mês (Priority: P3)

Como usuário, quero cadastrar uma tarefa que se repete uma vez por mês, num dia específico (ex.:
"Pagar boleto" todo dia 10), para lembrar de compromissos mensais.

**Why this priority**: completa a cobertura de padrões de recorrência pedida, mas atende a uma fração
menor de casos de uso do que diária/semanal — por isso prioridade mais baixa.

**Independent Test**: pode ser testado sozinho — cadastrar uma tarefa fixa mensal num dia específico e
confirmar que a ocorrência cai no dia certo, inclusive em meses mais curtos que não têm esse dia.

**Acceptance Scenarios**:

1. **Given** o usuário está criando uma tarefa fixa, **When** escolhe recorrência mensal e seleciona o
   dia 10, **Then** o sistema aceita a criação e a tarefa passa a ter ocorrência todo dia 10.
2. **Given** uma tarefa fixa mensal configurada para o dia 31, **When** o mês corrente tem menos de 31
   dias (ex.: abril, fevereiro), **Then** a ocorrência desse mês cai no último dia do mês.

---

### User Story 4 - Editar e excluir uma tarefa fixa (Priority: P2)

Como usuário, quero editar o título/recorrência de uma tarefa fixa ou excluí-la quando ela deixar de
fazer sentido, para manter minha lista de rotinas atualizada.

**Why this priority**: gestão básica do que foi criado nas US1-US3 — sem isso, um erro de cadastro ou
uma rotina abandonada fica permanente.

**Independent Test**: pode ser testado sozinho — criar uma tarefa fixa, editar seu título/recorrência,
depois excluí-la, e confirmar que ela some da lista e nenhuma conclusão associada a ela permanece.

**Acceptance Scenarios**:

1. **Given** uma tarefa fixa existente, **When** o usuário edita o título ou o padrão de recorrência,
   **Then** as mudanças são salvas e passam a valer a partir de agora (conclusões já registradas no
   passado não são alteradas).
2. **Given** uma tarefa fixa existente, **When** o usuário a exclui, **Then** ela some da lista e todo o
   registro de conclusões associado a ela é removido junto.

---

### Edge Cases

- Numa tarefa fixa semanal, num dia que não é um dos selecionados, ela aparece na lista sem estado de
  conclusão ativo para hoje (ver User Story 2, cenário 3) — nunca com um toggle "quebrado" ou um erro.
- Numa tarefa fixa mensal cujo dia configurado não existe no mês corrente (ex.: dia 31 em abril, dia 30
  em fevereiro), a ocorrência do mês cai no último dia do mês (ver User Story 3, cenário 2) — nunca pula
  o mês inteiro nem estoura pro mês seguinte.
- Editar o padrão de recorrência de uma tarefa fixa não apaga nem altera conclusões já registradas para
  ocorrências passadas — só afeta o cálculo das ocorrências futuras.
- Excluir uma tarefa fixa remove também todas as conclusões associadas a ela (sem deixar registros
  órfãos).
- Uma tarefa fixa recém-criada nunca aparece "concluída" para uma ocorrência que ainda não existia no
  momento da criação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Usuários MUST poder criar uma Tarefa Fixa fornecendo um título e um padrão de recorrência:
  diária, semanal (com um ou mais dias da semana selecionados) ou mensal (com um dia do mês
  selecionado).
- **FR-002**: Sistema MUST rejeitar a criação/edição de uma Tarefa Fixa semanal sem nenhum dia da semana
  selecionado.
- **FR-003**: Sistema MUST rejeitar a criação/edição de uma Tarefa Fixa mensal sem um dia do mês válido
  selecionado (1 a 31).
- **FR-004**: Sistema MUST determinar, para qualquer data, se ela é uma "ocorrência" de uma Tarefa Fixa:
  toda data, para recorrência diária; datas cujo dia da semana esteja entre os selecionados, para
  recorrência semanal; a data cujo dia do mês corresponda ao selecionado, para recorrência mensal — e
  quando o mês corrente não tiver esse dia (ex.: dia 31 em abril, dia 29/30/31 em fevereiro), a
  ocorrência desse mês MUST cair no último dia do mês.
- **FR-005**: Usuários MUST poder marcar como concluída ou pendente a ocorrência de hoje de uma Tarefa
  Fixa, quando hoje for uma ocorrência dela, através de uma única ação (alternância direta, sem telas
  extras).
- **FR-006**: Sistema MUST tratar cada ocorrência (cada data em que a tarefa se aplica) como um estado de
  conclusão independente — concluir a ocorrência de hoje MUST NOT alterar o estado de ocorrências
  passadas ou futuras.
- **FR-007**: Sistema MUST calcular "hoje" (para determinar ocorrências e resetar o estado
  pendente/concluída a cada novo ciclo) na mesma timezone de aplicação já usada no restante do TaskFlow
  (`APP_TIMEZONE`).
- **FR-008**: Usuários MUST poder editar o título e o padrão de recorrência de uma Tarefa Fixa
  existente; a alteração MUST valer somente a partir do momento em que é salva, sem afetar conclusões já
  registradas para ocorrências passadas.
- **FR-009**: Usuários MUST poder excluir uma Tarefa Fixa; a exclusão MUST remover também todo o
  registro de conclusões associado a ela.
- **FR-010**: Sistema MUST exibir, na aba "Tarefas Fixas" dentro de "Minhas Tarefas", todas as Tarefas
  Fixas do usuário autenticado, com indicação clara de se hoje é uma ocorrência dela e, quando for, se já
  foi concluída.
- **FR-011**: Uma Tarefa Fixa MUST pertencer a exatamente um usuário (seu criador) — sem responsável,
  participantes, workspace, projeto ou qualquer forma de compartilhamento com outros usuários.
- **FR-012**: Uma Tarefa Fixa MUST NOT ter prioridade, prazo, descrição longa, comentários, checklist,
  anexos ou histórico de alterações — recursos exclusivos das tarefas normais do TaskFlow.
- **FR-013**: Tarefas Fixas MUST NOT ser contadas nas contagens do Dashboard existente (pendente/em
  andamento/concluída/atrasada/vencendo hoje) — essas contagens continuam refletindo exclusivamente
  tarefas normais, sem alteração de comportamento.
- **FR-014**: Sistema MUST persistir o registro de cada conclusão de ocorrência de forma que o
  histórico completo de cumprimento de uma Tarefa Fixa possa ser reconstituído posteriormente (base para
  uma eventual funcionalidade de sequência/streak), mesmo que essa funcionalidade não seja exposta ao
  usuário nesta versão.

### Key Entities *(include if feature involves data)*

- **Tarefa Fixa**: rotina pessoal recorrente. Pertence a um único usuário (dono). Possui título e um
  padrão de recorrência (tipo — diária/semanal/mensal — e, conforme o tipo, os dias da semana ou o dia
  do mês selecionados). Não tem prioridade, prazo, responsável, participantes, workspace, projeto,
  comentários, checklist, anexos ou histórico.
- **Conclusão de Ocorrência**: registro de que uma Tarefa Fixa foi cumprida numa data específica
  (ocorrência). Vinculada à Tarefa Fixa e à data da ocorrência. É por meio da presença/ausência desse
  registro para a data de hoje que o sistema decide se uma Tarefa Fixa está pendente ou concluída hoje —
  não existe um único campo "concluída" sobrescrito a cada ciclo, para permitir reconstituir o histórico
  completo no futuro (FR-014).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue criar uma nova Tarefa Fixa e marcá-la como concluída pela primeira vez
  em menos de 30 segundos.
- **SC-002**: Em 100% dos casos, uma Tarefa Fixa concluída numa ocorrência aparece novamente como
  pendente na ocorrência seguinte, sem qualquer ação manual do usuário.
- **SC-003**: Usuários conseguem identificar, em menos de 3 segundos de observação da lista, quais
  tarefas fixas já foram cumpridas hoje e quais ainda não.
- **SC-004**: As contagens do Dashboard existente permanecem 100% inalteradas pela introdução de Tarefas
  Fixas (nenhuma Tarefa Fixa é contada nelas).

## Assumptions

- O nome de produto adotado nesta especificação é "Tarefas Fixas" (termo de trabalho definido em
  conversa com o usuário) — pode ser revisado sem impacto funcional caso o produto prefira outro nome
  (ex.: "Rotinas") antes da implementação.
- A aba "Tarefas Fixas" é exibida dentro da tela "Minhas Tarefas" já existente, ao lado do quadro kanban
  atual, reaproveitando visualmente o mesmo padrão de abas já usado na tela de login/cadastro do
  TaskFlow.
- Numa Tarefa Fixa semanal, num dia que não é um dos selecionados, a tarefa permanece visível na lista
  (para consulta/edição), mas sem um estado de conclusão ativo para "hoje" — o toggle de
  pendente/concluída só existe nos dias em que a tarefa realmente tem ocorrência.
- Tarefas Fixas mensais cujo dia configurado não existe no mês corrente usam o último dia desse mês,
  todo mês em que isso ocorrer — sem compensar no mês seguinte.
- Autenticação, autorização (uma Tarefa Fixa só é visível/editável pelo seu próprio criador) e o formato
  de erro da API seguem os mesmos padrões já estabelecidos no restante do TaskFlow.
- Sem suporte a fuso horário por usuário: mesma referência de timezone única (`APP_TIMEZONE`) já usada
  em todo o TaskFlow, sem exceção para esta funcionalidade.
- Fora de escopo nesta versão (podem virar features futuras, sem que nada aqui precise ser refeito):
  sequência/streak visível ao usuário, tarefas fixas de workspace/equipe, notificações/lembretes,
  pausar uma tarefa fixa sem excluí-la.
