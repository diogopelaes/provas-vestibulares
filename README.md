# Provas de Vestibulares

Este repositório tem como único objetivo **concentrar todas as provas e seus respectivos gabaritos dos principais vestibulares em um só lugar**, de forma organizada e padronizada. Nada mais.

---

## 📁 Estrutura de Pastas do Projeto

O repositório reúne arquivos em formato PDF organizados por instituição e etapas:

- **`AFA/`**: Provas e gabaritos da Academia da Força Aérea (etapa única).
- **`ENEM/`**: Provas e gabaritos do Exame Nacional do Ensino Médio (etapa única).
- **`IME/`**: Provas e gabaritos do Instituto Militar de Engenharia (`1ª Fase` e `2ª Fase`).
- **`ITA/`**: Provas e gabaritos do Instituto Tecnológico de Aeronáutica (`1ª Fase` e `2ª Fase`).
- **`PROVÃO/`**: Provas e gabaritos do Provão Paulista (`1ª Série`, `2ª Série` e `3ª Série`).
- **`UNESP/`**: Provas e gabaritos da Universidade Estadual Paulista (`1ª Fase`, `2ª Fase` e exames de Meio de Ano).
- **`UNICAMP/`**: Provas e gabaritos da Universidade Estadual de Campinas (`1ª Fase` e `2ª Fase`).
- **`USP/`**: Provas e gabaritos da Fuvest / Universidade de São Paulo (`1ª Fase` e `2ª Fase`).

---

## 🛠️ Aplicação de Suporte (`app/`)

Na pasta [`app/`](./app/) encontra-se um servidor local leve em Python com interface web, cujo propósito é agilizar o salvamento de novos arquivos mantendo automaticamente o padrão de nomenclatura de cada pasta.

---

## 🔄 Sincronização com o Repositório Remoto (`sync.bat`)

O projeto inclui um mecanismo de sincronização **100% automático e silencioso**:

- **Via Duplo-Clique**: Dê dois cliques em [`sync.bat`](./sync.bat) na raiz do projeto. O script executa todas as etapas e fecha automaticamente ao terminar sem exigir nenhuma confirmação manual.
- **Funcionamento em Repositório Público**:
  - **Para o Proprietário/Colaborador**: Comita alterações locais, integra novidades remotas e envia (`git push`) tudo de volta ao GitHub.
  - **Para Quem Apenas Clonou (Uso Público/Sem Permissão de Escrita)**: O script baixa todas as atualizações e novas provas do repositório remoto via `git pull --rebase` e mantém o acervo local perfeitamente atualizado, sem falhar por falta de permissão de push.


