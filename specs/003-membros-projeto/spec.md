# Feature Specification: Membros de Projeto (Visibilidade Restrita por Convite)

**Feature Branch**: `003-membros-projeto`

**Created**: 2026-08-23

**Status**: Draft

**Input**: User description: "Membros de Projeto (visibilidade restrita por convite): hoje, dentro de um
Workspace do TaskFlow, TODO membro do workspace (qualquer role) enxerga e acessa TODOS os projetos desse
workspace. Esta feature muda essa regra: um projeto passa a ter sua própria lista de membros, e só quem
foi explicitamente adicionado a um projeto específico consegue vê-lo e acessá-lo — com uma exceção para o
Owner do workspace, que sempre enxerga tudo. Admin vê a lista de todos os projetos mas só abre os que
participa. Gestão de membros de projeto é feita por Owner/Admin do workspace. Atribuição de tarefas fica
restrita a membros do projeto. Projetos existentes são migrados automaticamente (todos os membros atuais
do workspace viram membros explícitos), sem perda de acesso para ninguém."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adicionar e remover membros de um projeto (Priority: P1)

Como Owner ou Admin de um workspace, quero escolher quais pessoas do workspace têm acesso a um projeto
específico, para controlar quem vê informações sensíveis de um projeto sem precisar isolar essas pessoas
em outro workspace.

**Why this priority**: é o mecanismo básico sem o qual nenhuma restrição de visibilidade é possível de
configurar — toda a proposta de valor da feature depende de existir uma forma de definir "quem está
dentro".

**Independent Test**: pode ser testado sozinho — como Owner/Admin, adicionar um membro do workspace à
lista de membros de um projeto e depois removê-lo, confirmando que a lista reflete a mudança
imediatamente.

**Acceptance Scenarios**:

1. **Given** um projeto existente e uma pessoa que já é membro do workspace mas não do projeto, **When**
   um Owner ou Admin do workspace a adiciona à lista de membros do projeto, **Then** essa pessoa passa a
   constar como membro do projeto.
2. **Given** um projeto com um membro que não tem tarefas ativas atribuídas nele, **When** um Owner ou
   Admin do workspace remove essa pessoa da lista de membros do projeto, **Then** ela deixa de constar
   como membro do projeto.
3. **Given** um Member comum do workspace (não Owner nem Admin), **When** tenta adicionar ou remover um
   membro de um projeto, **Then** o sistema recusa a ação.

---

### User Story 2 - Um projeto só é visível para quem foi convidado (Priority: P1)

Como membro comum de um workspace, quero ver na minha lista de projetos apenas aqueles dos quais faço
parte, para não ter acesso a informações de projetos que não dizem respeito a mim.

**Why this priority**: é a proposta de valor central da feature — sem esta restrição de fato acontecendo,
a US1 (gestão de membros) não teria efeito nenhum sobre o comportamento real do sistema.

**Independent Test**: pode ser testado sozinho — como um Member comum que participa de um projeto A mas
não de um projeto B (ambos no mesmo workspace), confirmar que a listagem de projetos mostra A e não
mostra B, e que tentar acessar B diretamente é bloqueado.

**Acceptance Scenarios**:

1. **Given** um Member comum que é membro do Projeto A e não é membro do Projeto B, ambos no mesmo
   workspace, **When** ele abre a listagem de projetos do workspace, **Then** vê o Projeto A e não vê
   nenhum indício da existência do Projeto B.
2. **Given** a mesma pessoa, **When** tenta acessar diretamente a URL/tela do Projeto B, **Then** o
   sistema trata como se o projeto não existisse para ela (mesmo comportamento usado hoje para recursos
   fora do seu acesso).
3. **Given** um Member que acabou de ser adicionado como membro de um projeto, **When** ele abre a
   listagem de projetos novamente, **Then** o projeto passa a aparecer para ele, sem precisar de nenhuma
   outra ação.

---

### User Story 3 - Visibilidade ampliada para Owner e Admin (Priority: P2)

Como Owner do workspace, quero continuar enxergando e acessando todos os projetos automaticamente,
mesmo os que não me adicionaram explicitamente, para manter minha capacidade de supervisionar tudo que
acontece no workspace. Como Admin, quero pelo menos saber quais projetos existem, mesmo sem poder abrir
os que não participo, para poder me organizar e pedir acesso quando necessário.

**Why this priority**: refina a regra da US2 para os dois papéis de gestão do workspace — importante
para não quebrar o fluxo de administração existente, mas depende da restrição básica (US2) já estar
funcionando.

**Independent Test**: pode ser testado sozinho — como Owner, confirmar acesso total a um projeto sem
nunca ter sido adicionado à sua lista de membros; como Admin, confirmar que um projeto do qual não
participa aparece na listagem mas seu conteúdo (quadro/tarefas) não pode ser aberto.

**Acceptance Scenarios**:

1. **Given** um projeto qualquer do workspace, **When** o Owner do workspace abre a listagem de
   projetos, **Then** todos os projetos aparecem para ele, mesmo os que ele nunca foi adicionado
   explicitamente como membro.
2. **Given** o mesmo Owner, **When** ele abre o quadro/tarefas de qualquer projeto do workspace,
   **Then** o acesso é concedido normalmente.
3. **Given** um projeto do qual um Admin do workspace não é membro, **When** esse Admin abre a listagem
   de projetos, **Then** o projeto aparece na lista (nome e descrição), mas ao tentar abrir seu
   quadro/tarefas, **Then** o sistema recusa o acesso.

---

### User Story 4 - Atribuição de tarefas restrita a membros do projeto (Priority: P2)

Como pessoa que gerencia tarefas de um projeto, quero que só seja possível atribuir uma tarefa desse
projeto a alguém que também tem acesso a ele, para não vazar visibilidade de uma tarefa (e do contexto do
projeto) para alguém de fora.

**Why this priority**: fecha uma brecha da restrição de visibilidade (US2/US3) — sem isto, seria possível
contornar a restrição atribuindo uma tarefa a alguém sem acesso ao projeto.

**Independent Test**: pode ser testado sozinho — tentar atribuir uma tarefa de um projeto restrito a uma
pessoa que não é membro desse projeto e confirmar que o sistema recusa, mostrando somente membros do
projeto como opções válidas de responsável.

**Acceptance Scenarios**:

1. **Given** uma tarefa pertencente a um projeto, **When** alguém tenta definir como responsável uma
   pessoa que não é membro desse projeto, **Then** o sistema recusa a atribuição.
2. **Given** a mesma tarefa, **When** o responsável é escolhido entre as pessoas que são membros do
   projeto, **Then** a atribuição é aceita normalmente.

---

### User Story 5 - Remover um membro de um projeto com tarefas ativas (Priority: P3)

Como Owner ou Admin, quero ser impedido de remover alguém de um projeto enquanto essa pessoa ainda tem
tarefas ativas atribuídas nele, para não perder o rastro de quem é responsável por um trabalho em
andamento.

**Why this priority**: é uma proteção de borda sobre a US1 — importante para consistência de dados, mas
o sistema já é utilizável e majoritariamente correto sem ela (o caso comum é remover alguém sem tarefas
pendentes).

**Independent Test**: pode ser testado sozinho — tentar remover do projeto uma pessoa com uma tarefa não
concluída atribuída a ela dentro desse projeto e confirmar que o sistema recusa, indicando quais tarefas
precisam ser reatribuídas primeiro.

**Acceptance Scenarios**:

1. **Given** um membro de projeto com ao menos uma tarefa não concluída atribuída a ele dentro desse
   projeto, **When** um Owner ou Admin tenta removê-lo da lista de membros do projeto, **Then** o sistema
   recusa e indica quais tarefas precisam ser reatribuídas antes.
2. **Given** o mesmo membro, **When** todas as suas tarefas ativas nesse projeto são reatribuídas ou
   concluídas e a remoção é tentada novamente, **Then** a remoção é aceita.

---

### Edge Cases

- Uma pessoa removida do workspace inteiro (não só de um projeto) deixa de ter acesso a todos os
  projetos do workspace automaticamente — nenhuma lista de membros de projeto retém acesso órfão.
- Uma tarefa de um projeto restrito cujo responsável foi removido do projeto (via alguma exceção
  administrativa futura) não é impedida de continuar existindo com esse responsável já atribuído — a
  restrição de FR de atribuição vale para a AÇÃO de atribuir, não reavalia atribuições já feitas
  retroativamente.
- Um projeto sem nenhum membro além do seu criador continua funcionando normalmente para esse criador
  (não existe estado de "projeto travado" por falta de membros).
- Owner do workspace transfere a titularidade para outra pessoa (fluxo já existente): a visibilidade
  automática de "todos os projetos" passa a valer para o novo Owner e deixa de valer automaticamente para
  quem deixou de ser Owner (que passa a Admin, com a visibilidade de Admin da US3).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistema MUST manter, para cada Projeto, uma lista própria de membros — pessoas que têm
  acesso explícito a esse projeto específico.
- **FR-002**: Sistema MUST garantir que todo membro de um Projeto seja também, obrigatoriamente, membro
  do Workspace ao qual esse projeto pertence.
- **FR-003**: Ao criar um novo Projeto, sistema MUST adicionar automaticamente quem o criou como primeiro
  membro desse projeto.
- **FR-004**: Owner e Admin do Workspace MUST poder adicionar e remover membros da lista de membros de um
  Projeto; um Admin só MUST conseguir gerenciar a lista de membros de um Projeto do qual ele mesmo é
  membro (ou seja, ao qual já tem acesso).
- **FR-005**: Members comuns do Workspace MUST NOT poder adicionar ou remover membros de um Projeto.
- **FR-006**: Sistema MUST exibir, na listagem de projetos de um Workspace, apenas os projetos dos quais
  a pessoa autenticada é membro — EXCETO para o Owner do Workspace, que MUST ver todos os projetos do
  Workspace independentemente de ser membro explícito, e para o Admin do Workspace, que MUST ver a
  listagem de todos os projetos do Workspace (mesmo os que não participa).
- **FR-007**: Sistema MUST bloquear o acesso ao conteúdo (quadro e tarefas) de um Projeto para qualquer
  pessoa que não seja: membro explícito desse Projeto, ou o Owner do Workspace. Isso MUST incluir
  Admins do Workspace que não sejam membros do Projeto — eles veem o projeto na listagem (FR-006) mas
  não MUST conseguir abrir seu conteúdo.
- **FR-008**: Sistema MUST tratar o acesso negado a um Projeto (listagem para Member comum, ou abertura
  de conteúdo para quem não tem acesso) da mesma forma que trata hoje o acesso a um recurso inexistente
  — sem revelar a um usuário sem acesso que aquele projeto existe.
- **FR-009**: Sistema MUST permitir definir como responsável (assignee) de uma tarefa pertencente a um
  Projeto apenas pessoas que sejam membros desse Projeto; MUST recusar a atribuição a qualquer outra
  pessoa, mesmo que ela seja membro do Workspace.
- **FR-010**: Ao tentar remover uma pessoa da lista de membros de um Projeto, sistema MUST recusar a
  remoção caso ela tenha tarefas ativas (não concluídas) atribuídas a ela dentro desse Projeto
  especificamente, indicando quais tarefas precisam ser reatribuídas ou concluídas primeiro — mesma regra
  já aplicada hoje à remoção de um membro de Workspace.
- **FR-011**: Sistema MUST remover a lista de membros de um Projeto junto com o restante de seus dados
  quando o Projeto é excluído.
- **FR-012**: No momento em que esta funcionalidade entra em vigor, sistema MUST adicionar
  automaticamente, como membros explícitos de cada Projeto já existente, todas as pessoas que hoje já são
  membros do Workspace ao qual esse projeto pertence — nenhuma pessoa que já tinha acesso a um projeto
  antes desta mudança MUST perder esse acesso por causa dela.

### Key Entities *(include if feature involves data)*

- **Membro de Projeto**: associação entre uma pessoa e um Projeto, concedendo a ela acesso de visualização
  e uso desse projeto específico. Não carrega uma role própria (não existe "Owner de projeto" ou "Admin
  de projeto") — quem pode gerenciar essa lista é decidido pela role da pessoa no Workspace (FR-004).
  Toda pessoa nessa lista MUST já ser membro do Workspace-pai do projeto (FR-002).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa sem acesso a um projeto não encontra nenhum vestígio dele (nem na listagem, nem
  tentando acessar diretamente) em 100% dos casos testados.
- **SC-002**: Um Owner ou Admin do workspace consegue conceder acesso de um projeto a uma nova pessoa em
  menos de 30 segundos, sem sair da tela do projeto.
- **SC-003**: 100% dos projetos já existentes no momento em que a funcionalidade entra em vigor continuam
  acessíveis, sem qualquer perda de acesso, para todas as pessoas que já os acessavam antes.
- **SC-004**: 100% das tentativas de atribuir uma tarefa de um projeto restrito a alguém fora da lista de
  membros desse projeto são recusadas pelo sistema.

## Assumptions

- O nome adotado nesta especificação para a nova associação é "Membro de Projeto" — mesmo vocabulário já
  usado para "Membro de Workspace" (`WorkspaceMember`), só que escopado ao projeto; pode ser revisado sem
  impacto funcional caso o produto prefira outro termo.
- Não existe role própria de projeto (ex.: "líder de projeto") nesta versão — a lista de membros de
  projeto é flat (a pessoa está dentro ou fora), e quem pode gerenciá-la depende exclusivamente da role
  da pessoa no Workspace (Owner/Admin), conforme FR-004.
- Um Admin do Workspace não consegue se autoadicionar a um projeto que vê na listagem mas do qual não é
  membro — precisa ser adicionado por alguém que já tem acesso a esse projeto (o próprio Owner, ou outro
  Admin que já seja membro dele). Fora de escopo nesta versão qualquer mecanismo de "solicitar acesso".
- A regra de quem pode CRIAR um novo Projeto não muda nesta feature — continua sendo Owner/Admin do
  Workspace, como hoje.
- Migração de projetos já existentes (FR-012) é tratada como um evento único no momento em que esta
  funcionalidade entra em vigor, não como um processo contínuo — projetos criados depois desse momento
  começam sem nenhum membro além de quem os criou (FR-003), sem herdar automaticamente o restante do
  Workspace.
- Autenticação, formato de erro da API e o restante das regras de autorização (ex.: quem pode ver/editar
  uma tarefa em si) seguem os mesmos padrões já estabelecidos no restante do TaskFlow, sem alteração fora
  do que está descrito nesta especificação.
- Fora de escopo nesta versão (podem virar features futuras, sem que nada aqui precise ser refeito):
  papéis/roles dentro de um projeto; um Admin solicitar/se autoadicionar acesso a um projeto; qualquer
  mudança em quem pode criar um projeto; notificar alguém quando é adicionado ou removido de um projeto.
