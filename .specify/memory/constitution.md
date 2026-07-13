<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Modified principles:
  - IV. "Backend como Fonte Única de Validação e Regras de Negócio" → "Backend como
    Autoridade de Validação de Negócio e Integridade de Dados" (clarified: frontend MAY
    perform UX-oriented validation; only backend has authority over business rules and
    data integrity)
  - V. "Evolução Consistente do Projeto" — strengthened wording on reuse-before-creation
  - II. "Clean Code e Responsabilidade Única" → "Clean Code, Tipagem e Responsabilidade
    Única" — strengthened explicit typing requirement
Added principles (new, numbered VI-XIV):
  - VI. Persistência e Migrações Controladas via Alembic
  - VII. Documentação Automática da API (OpenAPI/Swagger)
  - VIII. Cobertura de Testes para Regras de Negócio Críticas
  - IX. Nomenclatura Padronizada por Camada
  - X. Tratamento Padronizado de Erros da API
  - XI. Logging de Operações Importantes
  - XII. Configuração Centralizada
  - XIII. Fluxo Spec Kit Obrigatório (specify → clarify → plan → tasks → implement)
  - XIV. Compatibilidade Arquitetural em Alterações Estruturais
Added sections: none (existing four top-level sections preserved: Core Principles,
  Estrutura do Projeto, Responsabilidades por Camada, Governance)
Removed sections/principles: none — no existing principle removed or narrowed
Expanded sections:
  - Estrutura do Projeto: frontend layout expanded with `layouts/`, `contexts/`, `assets/`
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ reviewed, no change needed (Constitution Check
    fills dynamically from this file; Complexity Tracking table already supports the new
    exception-justification requirement in Principle XIV)
  - .specify/templates/spec-template.md ✅ reviewed, no change needed
  - .specify/templates/tasks-template.md ✅ reviewed, no change needed
  - .specify/templates/checklist-template.md ✅ reviewed, no change needed
Follow-up TODOs: none
-->

# TaskFlow Constitution

## Core Principles

### I. Stack Tecnológico Exclusivo

O backend MUST ser desenvolvido exclusivamente em Python utilizando FastAPI. O frontend
MUST ser desenvolvido exclusivamente em React + TypeScript, com Vite como ferramenta de
build. Nenhuma outra linguagem, framework web ou meta-framework substitui esta stack sem
uma emenda formal a esta constituição.

**Rationale**: Uma stack única elimina fragmentação tecnológica, simplifica onboarding e
mantém previsibilidade sobre como qualquer parte do sistema é construída e mantida.

### II. Clean Code, Tipagem e Responsabilidade Única

O código MUST seguir os princípios de Clean Code, priorizando legibilidade, simplicidade,
baixo acoplamento e alta coesão. Funções, classes, componentes, schemas e services MUST
possuir responsabilidade única. Arquivos excessivamente grandes ou altamente acoplados
MUST ser evitados. Código morto, duplicado ou comentado sem necessidade MUST NOT
permanecer no repositório. Tipagem explícita MUST ser utilizada de forma consistente em
todo o projeto — type hints em 100% das assinaturas públicas de função/método no backend
(Python) e `strict` mode / ausência de `any` implícito no frontend (TypeScript). Toda
nova implementação MUST seguir o padrão já existente no projeto para a mesma
responsabilidade.

**Rationale**: Consistência de estilo, responsabilidade única e tipagem forte reduzem o
custo de leitura, manutenção e detecção precoce de erros, especialmente à medida que
múltiplos colaboradores (humanos ou agentes) tocam o mesmo código ao longo do tempo.

### III. Separação de Camadas (Layered Architecture)

O projeto MUST manter uma separação clara entre responsabilidades de camada, tanto no
backend quanto no frontend. A composição de diretórios está definida em "Estrutura do
Projeto" e o contrato de cada camada está definido em "Responsabilidades por Camada".
Nenhuma camada MUST assumir responsabilidades de outra (por exemplo, uma rota não pode
conter regra de negócio, e um componente de UI não pode acessar o banco de dados
diretamente).

**Rationale**: Camadas bem definidas tornam o sistema testável isoladamente e evitam que
regras de negócio se espalhem por lugares inesperados.

### IV. Backend como Autoridade de Validação de Negócio e Integridade de Dados

O frontend MAY realizar validações voltadas exclusivamente para experiência do usuário
(UX) — como feedback imediato de formulário, máscaras de campo ou mensagens de conveniência
— desde que essas validações nunca sejam tratadas como garantia de integridade. Apenas o
backend possui autoridade sobre validações de regra de negócio e integridade de dados; toda
validação importante MUST estar implementada no backend, independentemente de qualquer
validação equivalente no frontend. Regras de negócio MUST NEVER ser duplicadas entre
frontend e backend — o backend é a única fonte de verdade.

**Rationale**: O frontend não é confiável como única barreira de validação; duplicar
regras de negócio cria divergência e abre brechas de segurança e inconsistência de dados.
Permitir validação de UX no frontend melhora a experiência sem comprometer essa autoridade.

### V. Reuso e Evolução Consistente do Projeto

Antes de criar qualquer nova implementação, MUST verificar-se explicitamente se uma
implementação existente pode ser reutilizada ou estendida — criar código novo quando um
padrão consolidado já resolve o problema é uma violação deste princípio. Toda nova
funcionalidade MUST respeitar a arquitetura existente. Novos padrões MUST NOT ser criados
quando já existir um padrão consolidado para o mesmo problema. Novas dependências MUST só
ser adicionadas quando houver benefício técnico claro que não pode ser obtido com o que já
está disponível no projeto. Mudanças estruturais MUST manter a consistência e organização
já estabelecidas no projeto.

**Rationale**: Sem essa disciplina, o projeto acumula padrões concorrentes e dependências
desnecessárias, aumentando entropia e custo de manutenção a cada nova feature.

### VI. Persistência e Migrações Controladas via Alembic

Toda alteração no esquema do banco de dados (criação, alteração ou remoção de tabelas,
colunas, constraints ou índices) MUST ser realizada exclusivamente através de migrações
Alembic versionadas. MUST NOT haver alteração manual de schema diretamente no banco de
dados fora do fluxo de migração. Toda mudança em um Model MUST ser acompanhada da migração
Alembic correspondente no mesmo conjunto de alterações.

**Rationale**: Migrações versionadas garantem reprodutibilidade do schema entre ambientes
e um histórico auditável de todas as mudanças estruturais no banco de dados.

### VII. Documentação Automática da API (OpenAPI/Swagger)

A API MUST manter documentação automática precisa via OpenAPI, gerada pelo FastAPI
(Swagger UI/Redoc). Endpoints, schemas e respostas MUST estar corretamente tipados e
anotados (summary, description, response models) para que a documentação gerada
automaticamente permaneça como fonte confiável do contrato da API. Endpoints MUST NOT ser
publicados sem um schema de resposta explícito.

**Rationale**: Documentação gerada a partir do código nunca diverge da implementação real,
eliminando a necessidade de manter documentação de API em paralelo.

### VIII. Cobertura de Testes para Regras de Negócio Críticas

Toda regra de negócio crítica implementada em um service MUST possuir cobertura de testes
automatizados, utilizando o framework de testes já estabelecido no projeto. Alterações em
regras de negócio críticas MUST NOT ser mescladas sem os testes correspondentes atualizados
e passando. Correções de bugs em lógica de negócio SHOULD incluir um teste de regressão.

**Rationale**: Regras de negócio são o ativo mais valioso do sistema; testá-las
automaticamente é o que permite evoluir o projeto com confiança.

### IX. Nomenclatura Padronizada por Camada

Cada camada MUST seguir uma convenção de nomenclatura única e previsível:
- **Models**: substantivo no singular em PascalCase (ex.: `Task`, `Project`).
- **Schemas**: nome da entidade seguido do propósito (ex.: `TaskCreate`, `TaskUpdate`,
  `TaskRead`).
- **Services**: nome da entidade/domínio seguido de `Service` (ex.: `TaskService`).
- **Repositories**: nome da entidade seguido de `Repository` (ex.: `TaskRepository`).
- **Routes**: agrupadas por recurso, usando substantivos no plural para coleções (ex.:
  `/tasks`, `/projects`).
No frontend, componentes MUST usar PascalCase, hooks MUST ser prefixados com `use`, e
contexts MUST ser sufixados com `Context`.

**Rationale**: Nomenclatura previsível permite localizar qualquer artefato do sistema sem
depender de conhecimento tácito, reduzindo o tempo de onboarding e revisão.

### X. Tratamento Padronizado de Erros da API

A API MUST utilizar um formato de erro consistente em todas as respostas de falha (mesmo
formato de payload para código, mensagem e detalhes). Exceções de negócio MUST ser
representadas por exceções customizadas e traduzidas para respostas HTTP apropriadas via
exception handlers centralizados do FastAPI — rotas MUST NOT tratar exceções de negócio
individualmente de forma ad-hoc. Erros internos MUST NOT vazar stack traces ou detalhes de
implementação para o cliente.

**Rationale**: Um contrato de erro consistente simplifica o consumo da API pelo frontend e
evita exposição acidental de informações sensíveis do backend.

### XI. Logging de Operações Importantes

Operações importantes — criação/alteração/remoção de entidades relevantes, eventos de
autenticação/autorização e erros não tratados — MUST ser registradas via logging
estruturado. Dados sensíveis (senhas, tokens, segredos) MUST NEVER aparecer em logs.

**Rationale**: Logs estruturados de eventos relevantes são essenciais para depuração,
auditoria e observabilidade em produção.

### XII. Configuração Centralizada

Toda configuração da aplicação (variáveis de ambiente, segredos, parâmetros de conexão,
feature flags) MUST ser centralizada em módulos de configuração apropriados (ex.:
`core/config` no backend), carregada a partir de variáveis de ambiente/arquivos `.env`.
Valores de configuração MUST NOT ser hardcoded ou duplicados em múltiplos pontos do
código-fonte.

**Rationale**: Configuração centralizada evita divergência entre ambientes e reduz o risco
de segredos expostos diretamente no código.

### XIII. Fluxo Spec Kit Obrigatório

Nenhuma funcionalidade MUST ser implementada sem passar pelo fluxo do Spec Kit, na ordem:
`specify → clarify → plan → tasks → implement`. Implementação direta de funcionalidades
sem os artefatos correspondentes (spec, plano e tarefas) é proibida.

**Rationale**: O fluxo Spec Kit garante que toda funcionalidade seja especificada,
esclarecida e planejada antes da escrita de código, mantendo rastreabilidade entre
intenção e implementação.

### XIV. Compatibilidade Arquitetural em Alterações Estruturais

Toda alteração estrutural (novo módulo de topo, reorganização de diretórios ou mudança no
contrato de uma camada definida em "Responsabilidades por Camada") MUST manter
compatibilidade com a arquitetura existente descrita nesta constituição. Qualquer exceção
MUST ser explicitamente justificada na seção "Complexity Tracking" do plano da feature
correspondente, incluindo por que as alternativas dentro da arquitetura atual foram
rejeitadas.

**Rationale**: Sem esse controle, mudanças estruturais pontuais tendem a se acumular e
corroer a arquitetura ao longo do tempo sem que ninguém tenha avaliado o trade-off.

## Estrutura do Projeto

**Backend** (Python + FastAPI): `models/`, `schemas/`, `repositories/`, `services/`,
`routes/` (ou `controllers/`), `database/`, `enums/`, `core/config/`.

**Frontend** (React + TypeScript + Vite): `pages/`, `components/`, `layouts/`,
`contexts/`, `services/`, `hooks/`, `types/`, `utils/`, `assets/`.

Qualquer novo módulo MUST ser posicionado dentro de uma dessas categorias existentes;
categorias adicionais só devem ser introduzidas quando nenhuma das existentes comportar a
nova responsabilidade, e essa decisão deve ser explicitada no plano da feature (ver
Princípio XIV).

## Responsabilidades por Camada

- **Routes/Controllers**: MUST apenas receber requisições, validar entradas (formato) e
  delegar o processamento aos services. MUST NOT conter regra de negócio.
- **Services**: MUST concentrar exclusivamente as regras de negócio da aplicação.
- **Repositories**: MUST concentrar todo o acesso ao banco de dados; nenhuma outra camada
  MUST acessar o banco diretamente.
- **Models**: representam as entidades persistidas no banco de dados; qualquer mudança
  MUST vir acompanhada de migração Alembic (ver Princípio VI).
- **Schemas**: representam os contratos de entrada e saída da API e alimentam a
  documentação OpenAPI automática (ver Princípio VII).
- **Enums**: MUST ser utilizados para todos os valores controlados, como status,
  prioridades e roles — MUST NOT usar strings/ints livres para esses valores.
- **Layouts/Contexts (frontend)**: layouts MUST concentrar a composição estrutural de
  páginas (shells, navegação); contexts MUST concentrar estado compartilhado entre
  componentes, sem conter regra de negócio de domínio.
- **Componentes de UI (frontend)**: MUST NOT conter regras de negócio; regras de negócio
  pertencem exclusivamente ao backend (ver Princípio IV). MAY conter validações de UX.

## Governance

Esta constituição prevalece sobre qualquer outra prática, convenção informal ou preferência
individual dentro do projeto TaskFlow. Em caso de conflito entre esta constituição e
qualquer outro documento (README, comentários, discussões passadas), esta constituição
prevalece até ser formalmente emendada.

**Procedimento de emenda**: Alterações a esta constituição MUST ser feitas via atualização
direta deste arquivo, incluindo o Sync Impact Report no topo do arquivo e a propagação de
quaisquer mudanças necessárias para `.specify/templates/*`. Emendas MUST ser justificadas
(o que mudou e por quê).

**Política de versionamento** (semver aplicado à constituição):
- **MAJOR**: remoção ou redefinição incompatível de um princípio existente.
- **MINOR**: adição de um novo princípio ou expansão material de uma seção existente.
- **PATCH**: esclarecimentos, correções de redação ou ajustes não semânticos.

**Revisão de conformidade**: Toda nova feature MUST seguir o fluxo Spec Kit (Princípio
XIII), e seu plano (`plan.md`) MUST verificar aderência a todos os princípios acima antes de
ser mesclada. Complexidade que viole um princípio (por exemplo, uma camada extra, uma
dependência nova ou uma exceção à arquitetura definida em "Estrutura do Projeto") MUST ser
justificada explicitamente na seção "Complexity Tracking" do plano correspondente.
Simplicidade e reuso do padrão existente têm precedência sobre soluções novas quando ambas
resolvem o mesmo problema.

**Version**: 1.1.0 | **Ratified**: 2026-07-09 | **Last Amended**: 2026-07-09
