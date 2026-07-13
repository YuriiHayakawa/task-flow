# CLAUDE.md

# Diretrizes Operacionais do Projeto TaskFlow

Este arquivo define como o Claude Code deve trabalhar durante todo o desenvolvimento do TaskFlow.

A TaskFlow Constitution continua sendo a autoridade máxima do projeto.

O CLAUDE.md complementa a Constitution definindo regras operacionais, fluxo de desenvolvimento e boas práticas de colaboração.

---

# 1. Fonte de Verdade

Antes de iniciar qualquer implementação, consulte obrigatoriamente, nesta ordem:

1. TaskFlow Constitution
2. Specification da feature
3. Clarifications (quando existirem)
4. Plan
5. Research
6. Data Model
7. Contracts
8. Tasks

Nenhuma implementação deve contrariar esses documentos.

Caso exista conflito entre documentos, interrompa a implementação e informe o problema antes de prosseguir.

Nunca invente regras de negócio.

---

# 2. Fluxo Oficial do Projeto

Toda feature deve seguir obrigatoriamente o fluxo:

Constitution

↓

Specification

↓

Clarify

↓

Plan

↓

Tasks

↓

Implementação

↓

Testes

↓

Commit

↓

Push

↓

Merge

Não pular etapas.

---

# 3. Arquitetura

Sempre seguir a arquitetura definida na Constitution.

Não criar novos padrões quando já existir um padrão equivalente.

Sempre reutilizar estruturas existentes antes de criar novas soluções.

Evitar duplicação.

Evitar código morto.

Evitar overengineering.

Priorizar simplicidade.

---

# 4. Organização do Código

Todo código novo deve seguir:

Backend

- Models
- Schemas
- Repositories
- Services
- Routes
- Dependencies
- Database
- Core
- Utils

Frontend

- Pages
- Components
- Layouts
- Hooks
- Services
- Types
- Utils

Nenhum componente deve possuir responsabilidade que pertença a outra camada.

---

# 5. Regras de Desenvolvimento

Sempre:

- escrever código limpo;
- utilizar tipagem explícita;
- utilizar nomes claros;
- remover código não utilizado;
- seguir o padrão existente do projeto;
- manter responsabilidade única.

Nunca:

- duplicar regra de negócio;
- colocar regra de negócio em rotas;
- acessar banco fora dos repositories;
- utilizar lógica de domínio em componentes React.

---

# 6. Git e Versionamento

Este projeto utiliza Git desde o início.

Antes de iniciar qualquer alteração:

executar:

git status

Verificar:

- branch atual;
- alterações pendentes;
- conflitos existentes.

Nunca trabalhar diretamente na branch main.

Sempre utilizar a branch da feature atual.

Para o MVP atual utilizar:

001-taskflow-mvp

---

# 7. Estratégia de Branches

Utilizar:

feature/<nome>

fix/<nome>

docs/<nome>

refactor/<nome>

test/<nome>

chore/<nome>

Quando a feature possuir branch criada pelo Spec Kit, utilizar essa branch.

Não criar branches paralelas sem necessidade.

---

# 8. Commits

Todos os commits devem ser:

- pequenos;
- coesos;
- relacionados a uma única responsabilidade.

Utilizar Conventional Commits.

Exemplos:

docs:

feat:

fix:

test:

refactor:

chore:

build:

ci:

Nunca utilizar mensagens genéricas.

---

# 9. Processo Antes do Commit

Antes de qualquer commit:

1. executar git status;

2. revisar git diff;

3. validar que os arquivos pertencem à mesma responsabilidade;

4. executar testes relacionados;

5. verificar se nenhum segredo será enviado;

6. verificar o .gitignore.

Antes de executar git commit apresentar obrigatoriamente:

- resumo das alterações;
- arquivos modificados;
- testes executados;
- resultado dos testes;
- mensagem sugerida.

Aguardar autorização do usuário.

Após o commit informar:

- hash;
- branch;
- mensagem utilizada.

---

# 10. Push

Nunca executar automaticamente:

git push

Aguardar autorização do usuário.

Após o push informar:

- branch enviada;
- hash enviado;
- status do repositório.

Nunca executar:

git push --force

---

# 11. Merge

Nunca executar merge automaticamente.

Nunca executar merge na main.

Aguardar autorização.

---

# 12. Segurança

Nunca versionar:

.env

credenciais

tokens

senhas

certificados

arquivos locais

uploads

logs sensíveis

Sempre verificar isso antes do commit.

---

# 13. Implementação

Antes de criar novos arquivos:

verificar se já existe implementação semelhante.

Priorizar:

reutilização

extensão

padronização

Não apagar código funcional sem justificativa.

---

# 14. Testes

Toda implementação deve prever testes.

Sempre que possível:

- testes unitários;
- testes de integração;
- testes de autorização;
- testes de regras de negócio.

Não considerar uma feature concluída sem validar seu funcionamento.

---

# 15. Comunicação

Durante qualquer implementação:

Informar:

- o que será feito;
- quais arquivos serão alterados;
- possíveis impactos.

Ao finalizar:

Apresentar:

- resumo técnico;
- arquivos modificados;
- testes executados;
- próximos passos sugeridos.

---

# 16. Documentação

Sempre que uma alteração impactar arquitetura, regras de negócio ou contratos:

avaliar automaticamente se devem ser atualizados:

- Constitution
- Specification
- Plan
- Research
- Data Model
- Contracts
- Quickstart
- README

Caso não seja necessário atualizar, informar o motivo.

---

# 17. Qualidade

Sempre priorizar:

- legibilidade;
- simplicidade;
- segurança;
- manutenibilidade;
- testabilidade;
- consistência.

O objetivo não é produzir código rapidamente.

O objetivo é produzir código que permaneça fácil de entender e evoluir durante anos.