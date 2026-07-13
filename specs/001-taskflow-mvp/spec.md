# Feature Specification: TaskFlow MVP

**Feature Branch**: `001-taskflow-mvp`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "Construir o MVP do TaskFlow — aplicação de gerenciamento de tarefas, projetos e workspaces, com usuários comuns, membros/admins/donos de workspace e um administrador da plataforma (System Admin); suporte a tarefas pessoais e colaborativas, workspaces, projetos, participantes de tarefa, comentários, checklists, anexos, notificações, histórico de alterações, dashboard inicial, perfil de usuário e busca/filtros/ordenação de tarefas. O System Admin administra apenas a plataforma (usuários), nunca workspaces."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conta e Tarefas Pessoais (Priority: P1)

Um usuário cria uma conta, faz login e passa a gerenciar suas próprias tarefas pessoais
(criar, listar, editar, concluir), definindo status, prioridade, prazo e descrição para
acompanhar sua rotina.

**Why this priority**: É a base de valor do produto e pré-requisito para todo o resto —
sem conta e sem tarefa pessoal funcional não há MVP demonstrável.

**Independent Test**: Pode ser testado sozinho: cadastrar um usuário, fazer login, criar
uma tarefa pessoal (sem workspace/projeto), editar seu status/prioridade/prazo e marcá-la
como concluída — entregando valor completo de gestão pessoal de tarefas.

**Acceptance Scenarios**:

1. **Given** um visitante sem conta, **When** ele se cadastra com dados válidos, **Then**
   uma conta é criada e ele consegue fazer login com sucesso.
2. **Given** um visitante não autenticado, **When** ele tenta acessar suas tarefas sem
   estar logado, **Then** o acesso é negado e ele é direcionado ao login.
3. **Given** um usuário logado, **When** ele cria uma tarefa pessoal informando título,
   status, prioridade, prazo e descrição, **Then** a tarefa é salva e listada com o próprio
   usuário como responsável.
4. **Given** uma tarefa pessoal existente, **When** o usuário edita seu status para
   "Concluída", **Then** a tarefa passa a ser exibida como concluída na listagem.
5. **Given** uma conta desativada pelo System Admin, **When** o usuário tenta fazer login,
   **Then** o acesso é negado e ele é informado de que a conta está desativada.

---

### User Story 2 - Dashboard Inicial (Priority: P1)

Ao acessar o sistema, o usuário visualiza rapidamente um resumo de suas tarefas —
pessoais e dos workspaces dos quais participa — agrupadas por status, com destaque para
tarefas atrasadas e tarefas com vencimento hoje.

**Why this priority**: Entrega percepção imediata de valor e visão geral do trabalho logo
no primeiro acesso, reforçando a utilidade do produto desde o início.

**Independent Test**: Com tarefas pessoais e/ou de workspace já existentes em diferentes
status e prazos, acessar o dashboard e confirmar que as contagens exibidas refletem
corretamente o estado real das tarefas visíveis ao usuário.

**Acceptance Scenarios**:

1. **Given** um usuário com tarefas pessoais e de workspace em diferentes status, **When**
   ele acessa o dashboard, **Then** ele visualiza a quantidade de tarefas pendentes, em
   andamento, concluídas, atrasadas e com vencimento hoje.
2. **Given** uma tarefa (pessoal ou de workspace) com prazo já vencido e não concluída,
   **When** o usuário acessa o dashboard, **Then** essa tarefa é contabilizada como
   atrasada.
3. **Given** uma tarefa visível ao usuário com prazo igual à data atual, **When** ele
   acessa o dashboard, **Then** essa tarefa é contabilizada como vencendo hoje.
4. **Given** um usuário sem nenhuma tarefa, **When** ele acessa o dashboard, **Then**
   todos os contadores são exibidos como zero, sem erro.
5. **Given** tarefas pessoais pertencentes a outro usuário, **When** o usuário acessa seu
   próprio dashboard, **Then** essas tarefas não são contabilizadas nele.
6. **Given** um usuário membro de múltiplos workspaces, **When** ele acessa o dashboard,
   **Then** as tarefas de todos esses workspaces são combinadas com suas tarefas pessoais
   no mesmo resumo.

---

### User Story 3 - Workspaces, Membros e Roles (Priority: P2)

Um usuário cria um workspace para separar contextos (pessoal, trabalho, faculdade etc.) e,
conforme sua role (Owner, Admin ou Member), administra membros e recursos do workspace.
Todo membro visualiza os projetos e tarefas do workspace do qual participa.

**Why this priority**: Habilita a colaboração, o segundo maior diferencial do produto após
a gestão pessoal de tarefas, com uma hierarquia de permissões clara.

**Independent Test**: Pode ser testado de forma independente após a US1: criar um
workspace (o criador se torna Owner), promover um segundo membro a Admin, adicionar um
terceiro usuário como Member, e confirmar que cada role consegue apenas as ações
permitidas para si.

**Acceptance Scenarios**:

1. **Given** um usuário logado, **When** ele cria um workspace informando um nome,
   **Then** o workspace é criado e o usuário se torna seu Owner.
2. **Given** um Owner ou Admin de workspace, **When** ele adiciona outro usuário como
   Member, **Then** esse usuário passa a ter acesso de visualização e colaboração no
   workspace com a role Member.
3. **Given** um membro de workspace (qualquer role), **When** ele acessa o workspace do
   qual participa, **Then** ele visualiza todos os projetos e tarefas existentes nesse
   workspace.
4. **Given** um usuário que não é membro de um workspace, **When** ele tenta acessar esse
   workspace, **Then** o acesso é negado.
5. **Given** um Owner de workspace, **When** ele promove um Member a Admin, **Then** esse
   membro passa a poder criar projetos e gerenciar Members do workspace.
6. **Given** um Admin de workspace, **When** ele tenta promover, rebaixar ou remover outro
   Admin, **Then** a ação é negada — apenas o Owner pode gerenciar Admins.
7. **Given** um Owner de workspace, **When** ele altera as configurações do workspace
   (nome, descrição) ou o exclui, **Then** a alteração/exclusão é aplicada.
8. **Given** um Admin ou Member de workspace, **When** ele tenta alterar configurações do
   workspace ou excluí-lo, **Then** a ação é negada.
9. **Given** um Admin de workspace, **When** ele tenta alterar a role do Owner ou removê-lo
   do workspace, **Then** a ação é negada — nenhum membro, incluindo Admins, pode alterar
   ou remover o Owner.
10. **Given** um workspace com um único Owner, **When** esse Owner tenta sair do workspace
    sem antes transferir a titularidade a outro membro, **Then** a ação é bloqueada.
11. **Given** um membro do workspace responsável por tarefas ativas, **When** um Owner ou
    Admin tenta removê-lo do workspace, **Then** a remoção é bloqueada até que todas as
    tarefas ativas sob sua responsabilidade sejam reatribuídas a outro membro válido do
    workspace.

---

### User Story 4 - Projetos e Tarefas de Equipe (Priority: P2)

Dentro de um workspace, apenas Owners e Admins criam projetos para agrupar tarefas
relacionadas; qualquer membro (Owner, Admin ou Member) cria tarefas dentro desses
projetos para organizar entregas maiores, sempre com um responsável definido.

**Why this priority**: Estende a colaboração do workspace para o nível de organização de
trabalho em equipe, essencial para o caso de uso colaborativo do produto.

**Independent Test**: Pode ser testado após a US3: dentro de um workspace existente, um
Admin cria um projeto e qualquer membro cria uma tarefa vinculada a esse projeto,
confirmando que ela aparece para os demais membros do workspace.

**Acceptance Scenarios**:

1. **Given** um workspace existente, **When** um Owner ou Admin cria um projeto informando
   nome e descrição, **Then** o projeto é criado vinculado a esse workspace.
2. **Given** um Member (sem privilégio de Admin/Owner), **When** ele tenta criar um
   projeto, **Then** a ação é negada.
3. **Given** um projeto existente, **When** qualquer membro do workspace (Owner, Admin ou
   Member) cria uma tarefa dentro desse projeto com um responsável definido, **Then** a
   tarefa é criada vinculada ao projeto e ao workspace do projeto.
4. **Given** uma tarefa vinculada a um projeto, **When** qualquer membro do workspace
   consulta o projeto, **Then** a tarefa aparece na listagem de tarefas do projeto.

---

### User Story 5 - Participantes de Tarefa (Priority: P2)

Em tarefas pertencentes a um workspace, o sistema permite adicionar outros membros do
mesmo workspace como participantes da tarefa, deixando explícito quem está envolvido além
do responsável.

**Why this priority**: Aumenta a clareza de colaboração em tarefas compartilhadas,
complementando comentários e anexos com um registro explícito de quem participa.

**Independent Test**: Sobre uma tarefa de workspace já existente, adicionar um participante
que seja membro do mesmo workspace e confirmar que ele passa a ser listado como
participante da tarefa.

**Acceptance Scenarios**:

1. **Given** uma tarefa pertencente a um workspace, **When** um membro do mesmo workspace
   é adicionado como participante, **Then** ele passa a constar na lista de participantes
   da tarefa.
2. **Given** uma tarefa pessoal (sem workspace), **When** alguém tenta adicionar um
   participante a ela, **Then** a ação é rejeitada.
3. **Given** um usuário que não é membro do workspace da tarefa, **When** alguém tenta
   adicioná-lo como participante dessa tarefa, **Then** a ação é rejeitada.
4. **Given** uma tarefa com um responsável definido, **When** a tarefa é consultada,
   **Then** o responsável aparece automaticamente na lista de participantes, mesmo sem
   ter sido adicionado manualmente.
5. **Given** uma tarefa com participantes, comentários, anexos e histórico, **When** um
   participante é removido da tarefa, **Then** os comentários, anexos e histórico já
   existentes permanecem inalterados.

---

### User Story 6 - Comentários em Tarefas (Priority: P2)

Participantes de uma tarefa comentam nela para registrar dúvidas, atualizações e decisões.

**Why this priority**: Comunicação assíncrona em torno da tarefa é essencial para
colaboração real, com custo de implementação relativamente baixo em relação ao valor.

**Independent Test**: Pode ser testado isoladamente sobre uma tarefa já existente
(pessoal ou de projeto): adicionar um comentário e confirmar que ele aparece no histórico
de comentários da tarefa, associado ao autor e à tarefa.

**Acceptance Scenarios**:

1. **Given** uma tarefa existente da qual o usuário participa, **When** ele adiciona um
   comentário com conteúdo, **Then** o comentário é salvo, associado à tarefa e ao autor.
2. **Given** uma tarefa existente, **When** um usuário tenta adicionar um comentário com
   conteúdo vazio, **Then** o sistema rejeita a ação e nenhum comentário é criado.
3. **Given** uma tarefa com comentários existentes, **When** um participante consulta a
   tarefa, **Then** todos os comentários são listados em ordem cronológica.
4. **Given** um membro do workspace da tarefa que não é responsável nem participante
   explícito dela, **When** ele tenta adicionar um comentário, **Then** a ação é
   rejeitada, ainda que ele continue conseguindo visualizar a tarefa e seus comentários
   existentes.

---

### User Story 7 - Perfil do Usuário (Priority: P2)

O usuário consulta seus próprios dados de conta e atualiza nome e e-mail, além de
consultar o status (ativa/desativada) da própria conta.

**Why this priority**: Funcionalidade básica de autoatendimento esperada em qualquer
produto com contas de usuário, mas não bloqueia o valor central de gestão de tarefas.

**Independent Test**: Logado, acessar a própria página de perfil, alterar o nome e
confirmar que a alteração é refletida; consultar o e-mail e o status da conta exibidos.

**Acceptance Scenarios**:

1. **Given** um usuário logado, **When** ele acessa seu perfil, **Then** vê seu nome,
   e-mail e status atual da conta (ativa/desativada).
2. **Given** um usuário logado, **When** ele atualiza seu nome para um valor válido,
   **Then** o novo nome é salvo e refletido no perfil.
3. **Given** um usuário logado, **When** ele atualiza seu e-mail para um endereço válido e
   não utilizado por nenhuma outra conta, **Then** o novo e-mail é salvo.
4. **Given** um usuário logado, **When** ele tenta atualizar seu e-mail para um endereço já
   usado por outra conta, **Then** a ação é rejeitada.

---

### User Story 8 - Busca, Filtros e Ordenação de Tarefas (Priority: P2)

O usuário pesquisa tarefas por título, filtra por status, prioridade, workspace, projeto e
responsável — de forma combinável — e ordena os resultados por prazo, prioridade ou data de
criação.

**Why this priority**: Essencial para o uso do produto à medida que o volume de tarefas
cresce, mas não bloqueia o fluxo básico de criar e gerenciar tarefas.

**Independent Test**: Com um conjunto de tarefas variadas já existentes, aplicar uma busca
por título combinada com filtros de status e prioridade, e ordenar o resultado por prazo,
confirmando que a lista retornada respeita todos os critérios aplicados simultaneamente.

**Acceptance Scenarios**:

1. **Given** uma lista de tarefas visíveis ao usuário, **When** ele pesquisa por um termo
   presente no título, **Then** apenas tarefas cujo título contém o termo são exibidas.
2. **Given** uma lista de tarefas, **When** o usuário aplica um filtro de status, **Then**
   apenas tarefas com o status selecionado são exibidas.
3. **Given** uma lista de tarefas, **When** o usuário aplica filtros de status e
   prioridade simultaneamente, **Then** apenas tarefas que atendem a ambos os critérios
   são exibidas.
4. **Given** tarefas de múltiplos workspaces e projetos visíveis ao usuário, **When** ele
   filtra por um workspace e um projeto específicos, **Then** apenas tarefas desse
   workspace/projeto são exibidas.
5. **Given** uma lista de tarefas, **When** o usuário ordena por prazo, prioridade ou data
   de criação, **Then** a lista é reordenada de acordo com o critério escolhido.
6. **Given** filtros aplicados que não correspondem a nenhuma tarefa, **When** o usuário
   consulta o resultado, **Then** uma lista vazia é exibida sem erro.

---

### User Story 9 - Checklists em Tarefas (Priority: P3)

Participantes de uma tarefa adicionam itens de checklist para quebrar a tarefa em passos
menores e acompanhar o progresso.

**Why this priority**: Melhora o acompanhamento de tarefas maiores, mas não é bloqueante
para o valor central de criar e colaborar em tarefas.

**Independent Test**: Pode ser testado isoladamente sobre uma tarefa existente: adicionar
itens de checklist, marcar um como concluído e confirmar que o progresso é refletido.

**Acceptance Scenarios**:

1. **Given** uma tarefa existente, **When** um participante adiciona um item de checklist,
   **Then** o item é salvo vinculado a essa tarefa.
2. **Given** um item de checklist existente, **When** o participante o marca como
   concluído, **Then** o item passa a ser exibido como concluído.
3. **Given** um membro do workspace da tarefa que não é responsável nem participante
   explícito dela, **When** ele tenta adicionar ou marcar um item de checklist, **Then**
   a ação é rejeitada, ainda que ele continue conseguindo visualizar o checklist da
   tarefa.

---

### User Story 10 - Anexos em Tarefas (Priority: P3)

Participantes de uma tarefa anexam arquivos para centralizar documentos relacionados.

**Why this priority**: Valor incremental de conveniência; não bloqueia o fluxo central de
criação e acompanhamento de tarefas.

**Independent Test**: Pode ser testado isoladamente sobre uma tarefa existente: enviar um
anexo e confirmar que ele aparece vinculado à tarefa e ao usuário que o enviou.

**Acceptance Scenarios**:

1. **Given** uma tarefa existente, **When** um participante anexa um arquivo, **Then** o
   anexo é salvo vinculado à tarefa e ao usuário que o enviou.
2. **Given** uma tarefa com anexos, **When** um participante consulta a tarefa, **Then**
   todos os anexos vinculados são listados.
3. **Given** um membro do workspace da tarefa que não é responsável nem participante
   explícito dela, **When** ele tenta anexar um arquivo, **Then** a ação é rejeitada,
   ainda que ele continue conseguindo visualizar e baixar os anexos já existentes.

---

### User Story 11 - Notificações (Priority: P3)

Usuários recebem notificações sobre vencimentos de tarefas, novos comentários e alterações
importantes que os afetam.

**Why this priority**: Aumenta o engajamento e evita que usuários percam prazos, mas o
produto é utilizável sem notificações automatizadas no primeiro corte.

**Independent Test**: Pode ser testado isoladamente: gerar um evento relevante (ex.: um
comentário em uma tarefa da qual o usuário participa) e confirmar que uma notificação é
criada para o usuário afetado.

**Acceptance Scenarios**:

1. **Given** uma tarefa com prazo próximo do vencimento, **When** o vencimento se
   aproxima, **Then** o responsável pela tarefa recebe uma notificação.
2. **Given** uma tarefa da qual o usuário participa, **When** outro participante adiciona
   um comentário, **Then** o usuário recebe uma notificação sobre o novo comentário.
3. **Given** uma tarefa da qual o usuário participa, **When** uma alteração importante é
   feita (status, prioridade, prazo ou responsável), **Then** o usuário recebe uma
   notificação sobre a alteração.

---

### User Story 12 - Histórico de Alterações da Tarefa (Priority: P3)

O sistema registra automaticamente um histórico das alterações relevantes feitas em uma
tarefa, permitindo auditoria básica do que mudou, quando e por quem.

**Why this priority**: Suporta confiança e rastreabilidade, mas não é necessário para o
primeiro uso funcional do produto.

**Independent Test**: Pode ser testado isoladamente: alterar o status, a prioridade, o
prazo ou o responsável de uma tarefa existente e confirmar que uma entrada de histórico é
criada refletindo a mudança.

**Acceptance Scenarios**:

1. **Given** uma tarefa existente, **When** seu status, prioridade, prazo ou responsável é
   alterado, **Then** uma entrada de histórico é registrada com o campo alterado, o valor
   anterior, o novo valor, o autor e o momento da alteração.
2. **Given** uma tarefa com histórico de alterações, **When** um participante consulta a
   tarefa, **Then** o histórico é exibido em ordem cronológica.
3. **Given** uma tarefa que foi reatribuída a um novo responsável por remoção de membro
   (ver User Story 3), **When** o histórico é consultado, **Then** essa reatribuição
   aparece registrada como uma alteração de responsável.

---

### User Story 13 - Administração de Usuários da Plataforma (System Admin) (Priority: P3)

Um System Admin lista as contas de usuário da plataforma e ativa/desativa contas, sem que
essa condição lhe conceda qualquer acesso a workspaces, projetos ou tarefas específicas.

**Why this priority**: Necessário para a operação básica da plataforma (ex.: suspender uma
conta problemática), mas não faz parte do fluxo de valor do usuário final e não bloqueia o
uso do produto.

**Independent Test**: Autenticado como System Admin, listar usuários, desativar uma conta
e confirmar que o usuário afetado não consegue mais fazer login; confirmar em seguida que
o System Admin continua sem acesso a workspaces dos quais não é membro comum.

**Acceptance Scenarios**:

1. **Given** um System Admin autenticado, **When** ele lista os usuários da plataforma,
   **Then** ele vê todas as contas com seus respectivos status (ativa/desativada).
2. **Given** uma conta de usuário ativa, **When** o System Admin a desativa, **Then** o
   usuário deixa de conseguir fazer login.
3. **Given** uma conta de usuário desativada, **When** o System Admin a reativa, **Then**
   o usuário volta a conseguir fazer login normalmente.
4. **Given** um System Admin que não é membro de nenhum workspace, **When** ele tenta
   acessar dados de um workspace, **Then** o acesso é negado, da mesma forma que para
   qualquer outro não membro.
5. **Given** um System Admin, **When** ele tenta editar uma tarefa, um projeto ou as
   configurações de qualquer workspace, **Then** a ação é negada.

---

### Edge Cases

- O que acontece quando um usuário tenta criar uma tarefa vinculada a um projeto sem
  informar o workspace? → O sistema MUST derivar o workspace automaticamente a partir do
  projeto informado (todo projeto pertence a exatamente um workspace).
- O que acontece quando um Owner/Admin tenta remover um membro que é responsável por
  tarefas ativas no workspace? → A remoção MUST ser bloqueada até que todas essas tarefas
  sejam reatribuídas a outro membro válido do workspace; nenhuma tarefa MUST permanecer
  sem responsável.
- O que acontece quando um usuário tenta comentar, anexar arquivo, criar checklist ou ser
  adicionado como participante em uma tarefa de um workspace do qual não é membro? → A
  ação MUST ser negada.
- O que acontece quando um membro do workspace (que não é responsável nem participante
  explícito da tarefa) tenta comentar, anexar arquivo ou criar/marcar item de checklist
  nessa tarefa? → A ação MUST ser negada — colaborar (comentar, anexar, criar/marcar
  checklist) exige ser o responsável ou um participante explícito da tarefa (ver FR-042,
  User Story 5); visualizar a tarefa e seus comentários/checklist/anexos/histórico
  permanece permitido a qualquer membro do workspace (FR-022, FR-042), independentemente
  de participação.
- O que acontece quando o único Owner de um workspace tenta sair ou ser removido sem
  transferir a titularidade? → A ação MUST ser bloqueada até que a titularidade seja
  transferida a outro membro.
- O que acontece quando um Admin tenta promover, rebaixar ou remover outro Admin, ou
  tentar alterar configurações/excluir o workspace? → A ação MUST ser negada; essas ações
  são exclusivas do Owner.
- O que acontece quando um Admin (ou qualquer outro membro que não o próprio Owner) tenta
  alterar a role do Owner ou removê-lo do workspace? → A ação MUST ser negada; somente o
  próprio Owner pode transferir sua titularidade a outro membro.
- O que acontece quando um usuário tenta definir um status ou prioridade fora dos valores
  controlados (por exemplo, um valor como "Cancelada" ou "Arquivada", inexistentes neste
  MVP)? → A requisição MUST ser rejeitada com erro de validação.
- O que acontece quando uma tarefa pessoal (sem workspace) é editada para ser movida para
  um projeto? → Ela MUST passar a herdar o workspace desse projeto, deixando de ser
  puramente pessoal.
- O que acontece quando o System Admin tenta acessar dados de um workspace do qual não é
  membro comum? → O acesso MUST ser negado; ser System Admin MUST NOT conceder nenhum
  privilégio dentro de workspaces.
- O que acontece quando uma conta é desativada pelo System Admin? → O usuário MUST NOT
  conseguir fazer login ou acessar qualquer funcionalidade até que a conta seja reativada.
- O que acontece quando uma busca/filtro combinado não retorna nenhuma tarefa? → O sistema
  MUST exibir uma lista vazia, sem erro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um visitante se cadastre com nome, e-mail e
  senha, impedindo e-mails duplicados.
- **FR-002**: O sistema MUST permitir que um usuário cadastrado faça login com e-mail e
  senha.
- **FR-003**: O sistema MUST proteger todas as rotas de dados (tarefas, workspaces,
  projetos, comentários, checklists, anexos, notificações, perfil) exigindo autenticação.
- **FR-004**: O sistema MUST negar login e acesso a qualquer funcionalidade para contas
  desativadas.
- **FR-005**: O sistema MUST permitir que um usuário crie, liste, edite e conclua tarefas
  pessoais (sem workspace e sem projeto).
- **FR-006**: Toda tarefa MUST possuir, em todo momento, exatamente um usuário responsável
  com conta ativa — nenhuma tarefa MUST existir sem responsável.
- **FR-007**: Uma tarefa MAY pertencer a um workspace; quando não pertencer, é tratada como
  tarefa pessoal do seu criador.
- **FR-008**: Uma tarefa MAY pertencer a um projeto; quando pertencer, a tarefa MUST
  também pertencer ao workspace desse projeto.
- **FR-009**: Toda tarefa MUST permitir definir status, prioridade, prazo (opcional) e
  descrição (opcional).
- **FR-010**: Status e prioridade de tarefas MUST usar um conjunto fixo e controlado de
  valores (enumerações — ver Key Entities), rejeitando qualquer valor fora desse conjunto.
- **FR-011**: Os estados "atrasada" e "vencendo hoje" MUST ser derivados automaticamente
  do prazo e do status da tarefa (não são valores adicionais do conjunto controlado de
  status, e não existe status "Cancelada", "Arquivada" ou similar neste MVP).
- **FR-012**: O sistema MUST permitir que um usuário crie um workspace, tornando-se
  automaticamente seu Owner.
- **FR-013**: Um workspace MUST sempre possuir exatamente um Owner ativo.
- **FR-014**: Somente o Owner de um workspace MUST poder promover um Member a Admin ou
  rebaixar um Admin a Member.
- **FR-015**: Somente o Owner de um workspace MUST poder remover um Admin do workspace.
- **FR-016**: Owner e Admin de um workspace MUST poder adicionar ou remover Members do
  workspace.
- **FR-017**: Somente o Owner MUST poder alterar as configurações do workspace (nome,
  descrição) ou excluir o workspace.
- **FR-018**: O Workspace Owner MUST possuir controle total sobre o workspace, incluindo
  todas as ações permitidas a Admin e a Member.
- **FR-019**: Nenhum membro do workspace, incluindo Admins, MUST poder alterar a role do
  Owner ou removê-lo do workspace; somente o próprio Owner pode transferir sua titularidade
  a outro membro.
- **FR-020**: Somente Owner e Admin de um workspace MUST poder criar projetos dentro dele;
  Members MUST NOT poder criar projetos.
- **FR-021**: Qualquer membro do workspace (Owner, Admin ou Member) MUST poder criar
  tarefas dentro de projetos ou diretamente no workspace.
- **FR-022**: Qualquer membro de um workspace (independentemente da role) MUST poder
  visualizar todos os projetos e tarefas desse workspace.
- **FR-023**: Um usuário que não é membro de um workspace MUST NOT visualizar ou alterar
  dados desse workspace.
- **FR-024**: O sistema MUST impedir a remoção de um membro do workspace enquanto ele for
  responsável por uma ou mais tarefas ativas (não concluídas) nesse workspace.
- **FR-025**: Antes de uma remoção de membro ser efetivada, todas as tarefas ativas sob a
  responsabilidade desse membro MUST ser reatribuídas a outro membro válido do workspace.
- **FR-026**: Todo projeto MUST pertencer a exatamente um workspace.
- **FR-027**: O sistema MUST permitir que participantes de uma tarefa adicionem
  comentários a ela.
- **FR-028**: Todo comentário MUST pertencer a exatamente uma tarefa e a exatamente um
  usuário (autor).
- **FR-029**: O sistema MUST rejeitar comentários com conteúdo vazio.
- **FR-030**: Tarefas pertencentes a um workspace MAY ter participantes além do
  responsável.
- **FR-031**: Tarefas pessoais (sem workspace) MUST NOT ter participantes adicionais.
- **FR-032**: Somente membros do mesmo workspace da tarefa MUST poder ser adicionados como
  participantes dela.
- **FR-033**: O responsável de uma tarefa MUST ser automaticamente considerado
  participante dela, independentemente de adição manual.
- **FR-034**: Remover um participante de uma tarefa MUST NOT apagar comentários, anexos ou
  entradas de histórico já existentes.
- **FR-035**: O sistema MUST permitir que participantes de uma tarefa adicionem itens de
  checklist a ela e marquem cada item como concluído ou pendente.
- **FR-036**: Todo item de checklist MUST pertencer a exatamente uma tarefa.
- **FR-037**: O sistema MUST permitir que participantes de uma tarefa anexem arquivos a
  ela.
- **FR-038**: Todo anexo MUST pertencer a exatamente uma tarefa e a exatamente um usuário
  (quem enviou).
- **FR-039**: O sistema MUST gerar notificações para eventos relevantes: aproximação de
  prazo, novo comentário e alterações importantes (status, prioridade, prazo ou
  responsável) em tarefas das quais o usuário participa.
- **FR-040**: O sistema MUST entregar notificações exclusivamente dentro da aplicação
  (central de notificações in-app); envio por e-mail fica fora do escopo deste MVP.
- **FR-041**: O sistema MUST registrar automaticamente um histórico quando status,
  prioridade, prazo ou responsável de uma tarefa forem alterados, contendo o campo
  alterado, valor anterior, novo valor, autor e data/hora.
- **FR-042**: O sistema MUST permitir que qualquer membro do workspace da tarefa (ou, no
  caso de tarefa pessoal, o próprio criador) consulte seus comentários, checklist, anexos
  e histórico — consultar é uma forma de visualização e segue a mesma regra ampla de
  FR-022, não a de colaboração. Adicionar um novo comentário, item de checklist ou anexo,
  por sua vez, MUST ficar restrito ao responsável pela tarefa e aos participantes
  explícitos dela (ver FR-027, FR-035, FR-037 e User Story 5) — um membro do workspace que
  não seja responsável nem participante MUST conseguir visualizar esses dados, mas MUST
  NOT conseguir adicionar novos.
- **FR-043**: Um System Admin MUST poder listar usuários e ativar/desativar contas de
  usuário, independentemente de participação em workspaces específicos.
- **FR-044**: Ser System Admin MUST NOT conceder, por si só, nenhum acesso a workspaces,
  projetos ou tarefas específicas.
- **FR-045**: O System Admin MUST NOT editar tarefas, projetos ou configurações de
  qualquer workspace.
- **FR-046**: Para acessar ou colaborar em um workspace, o System Admin MUST ser
  adicionado como membro comum (Owner, Admin ou Member) da mesma forma que qualquer outro
  usuário — sua condição de System Admin não substitui essa exigência.
- **FR-047**: O dashboard inicial MUST exibir a contagem de tarefas pendentes, em
  andamento, concluídas, atrasadas e com vencimento hoje.
- **FR-048**: O dashboard MUST considerar as tarefas pessoais do usuário autenticado e as
  tarefas de todos os workspaces dos quais ele participa.
- **FR-049**: O dashboard MUST NOT exibir tarefas pessoais pertencentes a outros usuários.
- **FR-050**: As contagens do dashboard MUST refletir o estado real das tarefas visíveis
  ao usuário no momento da consulta.
- **FR-051**: O sistema MUST permitir que um usuário visualize seus próprios dados de
  perfil: nome, e-mail e status da conta (ativa/desativada).
- **FR-052**: O sistema MUST permitir que um usuário edite seu próprio nome.
- **FR-053**: O sistema MUST permitir que um usuário edite seu próprio e-mail, desde que o
  novo endereço não esteja em uso por outra conta.
- **FR-054**: Alteração de senha, recuperação de senha, foto de perfil e exclusão da
  própria conta MUST NOT fazer parte deste MVP.
- **FR-055**: O sistema MUST permitir que um usuário pesquise tarefas por título.
- **FR-056**: O sistema MUST permitir que um usuário filtre tarefas por status,
  prioridade, workspace, projeto e responsável.
- **FR-057**: Os filtros de busca de tarefas MUST poder ser combinados simultaneamente.
- **FR-058**: O sistema MUST permitir que um usuário ordene os resultados de tarefas por
  prazo, prioridade ou data de criação.
- **FR-059**: Busca, filtros e ordenação MUST respeitar as mesmas regras de visibilidade e
  permissão já aplicadas às tarefas (ex.: uma tarefa pessoal de outro usuário nunca deve
  aparecer nos resultados).

### Key Entities

- **User**: representa uma pessoa com acesso ao sistema; atributos-chave: nome, e-mail
  (único), senha (armazenada de forma segura), status da conta (ativa/desativada),
  indicador de System Admin. O indicador de System Admin é uma propriedade da plataforma e
  MUST NOT implicar nenhuma role dentro de workspaces.
- **Workspace**: contexto que agrupa projetos, tarefas e membros; atributos-chave: nome,
  descrição, Owner (exatamente um, sempre ativo).
- **WorkspaceMember**: associação entre um usuário e um workspace; atributos-chave:
  usuário, workspace, role (Owner, Admin ou Member — não há role Viewer neste MVP).
- **Project**: agrupamento de tarefas dentro de um workspace; atributos-chave: nome,
  descrição, workspace ao qual pertence (exatamente um). Criado apenas por Owner ou Admin.
- **Task**: unidade de trabalho, pessoal ou de projeto; atributos-chave: título, descrição,
  status (conjunto controlado: Pendente, Em Andamento, Concluída — não existem status como
  Cancelada ou Arquivada nesta versão), prioridade, prazo, responsável, workspace
  (opcional), projeto (opcional), criador. "Atrasada" e "vencendo hoje" são estados
  derivados do prazo, não valores de status.
- **TaskMember**: participante de uma tarefa de workspace além do responsável;
  atributos-chave: tarefa relacionada, usuário participante. Aplicável somente a tarefas
  vinculadas a um workspace; o responsável da tarefa é implicitamente um participante.
- **Comment**: registro de comunicação sobre uma tarefa; atributos-chave: conteúdo, autor,
  tarefa relacionada, data/hora.
- **ChecklistItem**: passo menor dentro de uma tarefa; atributos-chave: descrição, estado
  (concluído/pendente), tarefa relacionada.
- **Attachment**: arquivo vinculado a uma tarefa; atributos-chave: nome do arquivo, quem
  enviou, tarefa relacionada, data/hora do envio.
- **Notification**: aviso enviado a um usuário sobre um evento relevante; atributos-chave:
  destinatário, tipo de evento, tarefa relacionada, estado (lida/não lida), data/hora.
- **TaskHistoryEntry**: registro de uma alteração relevante em uma tarefa; atributos-chave:
  tarefa relacionada, campo alterado, valor anterior, novo valor, autor da alteração,
  data/hora.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um novo usuário consegue se cadastrar, fazer login e criar sua primeira
  tarefa pessoal em menos de 3 minutos.
- **SC-002**: 100% das tarefas exibidas no sistema possuem um responsável, um status e uma
  prioridade válidos (dentro dos valores controlados), em qualquer momento.
- **SC-003**: Um Owner de workspace consegue criar um workspace, adicionar um membro e ter
  esse membro visualizando os projetos e tarefas compartilhados em menos de 2 minutos.
- **SC-004**: Usuários recebem notificação de eventos relevantes (comentário, alteração
  importante, prazo próximo) em até 1 minuto após o evento ocorrer.
- **SC-005**: 100% das alterações de status, prioridade, prazo ou responsável em uma
  tarefa geram uma entrada de histórico visível para os participantes da tarefa.
- **SC-006**: Usuários conseguem adicionar um comentário, um item de checklist ou um
  anexo a uma tarefa existente em menos de 30 segundos por ação.
- **SC-007**: Tentativas de acessar workspaces, projetos ou tarefas sem permissão —
  inclusive por parte do System Admin sobre workspaces dos quais não é membro comum, e por
  parte de Admins tentando alterar/remover o Owner — são bloqueadas em 100% dos casos
  testados.
- **SC-008**: 100% das tentativas de remover um membro responsável por tarefas ativas são
  bloqueadas até que essas tarefas sejam reatribuídas a outro membro válido.
- **SC-009**: As contagens exibidas no dashboard (pendentes, em andamento, concluídas,
  atrasadas, vencendo hoje) correspondem a 100% do estado real das tarefas visíveis ao
  usuário no momento da consulta.
- **SC-010**: Usuários encontram uma tarefa específica combinando busca por título e ao
  menos dois filtros em uma única consulta, sem etapas adicionais.
- **SC-011**: Usuários conseguem atualizar nome e/ou e-mail do próprio perfil em menos de
  1 minuto.
- **SC-012**: Um System Admin consegue localizar um usuário e alternar o status de sua
  conta (ativa/desativada) em menos de 1 minuto, sem obter acesso a nenhum workspace.

## Assumptions

- Autenticação MVP utiliza cadastro e login com e-mail/senha; métodos alternativos (SSO,
  OAuth social/login social) ficam fora do escopo deste MVP.
- O System Admin é uma role exclusivamente de administração da plataforma (usuários),
  totalmente independente da administração de workspaces; ele não se torna membro de
  nenhum workspace automaticamente e não possui privilégios sobre tarefas ou projetos de
  workspaces apenas por sua condição de System Admin.
- Um workspace possui três níveis de role: Owner (controle total, incluindo gestão de
  Admins, configurações e exclusão do workspace — nenhum outro membro pode alterar ou
  remover o Owner), Admin (criação de projetos, tarefas e gestão de Members, sem poder
  alterar/remover outro Admin ou o Owner) e Member (participação em projetos e tarefas,
  criação de tarefas, comentários, checklists e anexos, sem gerenciar membros, projetos ou
  configurações). Não existe role Viewer neste MVP.
- Apenas Owner e Admin podem criar projetos; Members criam tarefas, comentários,
  checklists e anexos conforme as permissões de sua role, mas não criam projetos.
- Tarefas pessoais (sem workspace) só são visíveis e editáveis pelo próprio criador/
  responsável, e não podem ter participantes adicionais.
- "Tarefa ativa" significa qualquer tarefa cujo status seja diferente de "Concluída". O
  conjunto de status deste MVP é fechado (Pendente, Em Andamento, Concluída); não existem
  status "Cancelada", "Arquivada" ou similares nesta versão do produto.
- Não há limite de tamanho ou tipo de arquivo definido para anexos neste MVP; a validação
  de arquivos aceitos é uma decisão técnica a ser detalhada na fase de planejamento.
- O histórico de alterações cobre os campos status, prioridade, prazo e responsável;
  alterações de título/descrição/comentários não geram entradas de histórico no MVP.
- "Concluir" uma tarefa corresponde a transicioná-la para o valor de status "Concluída"
  dentro do conjunto controlado de status.
- Dentro de um workspace, a visibilidade de projetos e tarefas é aberta a todos os membros
  do workspace (sem granularidade restrita por projeto/role neste MVP).
- Notificações são entregues apenas dentro da aplicação (in-app); envio por e-mail fica
  fora do escopo deste MVP.
- Permanecem explicitamente fora do escopo deste MVP: login social, OAuth, SSO, alteração
  de senha, recuperação de senha, exclusão da própria conta, foto de perfil, notificações
  por e-mail, permissões avançadas por tarefa, visibilidade restrita por projeto, auditoria
  completa da plataforma e integrações externas.
