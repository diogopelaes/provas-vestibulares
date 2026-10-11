# Provas de Vestibulares

Este repositório tem como único objetivo **concentrar todas as provas e seus respectivos gabaritos dos principais vestibulares em um só lugar**, de forma organizada e padronizada. Nada mais.

---

## 📁 Estrutura de Pastas do Projeto

O repositório reúne arquivos em formato PDF organizados por instituição e etapas:

- **`AFA/`**: Provas e gabaritos da Academia da Força Aérea (etapa única).
- **`IME/`**: Provas e gabaritos do Instituto Militar de Engenharia (`1ª Fase` e `2ª Fase`).
- **`ITA/`**: Provas e gabaritos do Instituto Tecnológico de Aeronáutica (`1ª Fase` e `2ª Fase`).
- **`UNESP/`**: Provas e gabaritos da Universidade Estadual Paulista (`1ª Fase`, `2ª Fase` e exames de Meio de Ano).
- **`UNICAMP/`**: Provas e gabaritos da Universidade Estadual de Campinas (`1ª Fase` e `2ª Fase`).
- **`USP/`**: Provas e gabaritos da Fuvest / Universidade de São Paulo (`1ª Fase` e `2ª Fase`).

---

## 🛠️ Aplicação de Suporte (`app/`)

Na pasta [`app/`](./app/) encontra-se um servidor local leve em Python com interface web, cujo propósito é agilizar o salvamento de novos arquivos mantendo automaticamente o padrão de nomenclatura de cada pasta.

---

## 🔄 Sincronização com o Repositório Remoto (`sync.bat`)

Para sincronizar facilmente todas as adições de provas e atualizações da aplicação com o repositório remoto no GitHub:

- **Via Duplo-Clique**: Execute [`sync.bat`](./sync.bat) na raiz do projeto (ou [`app/sync.bat`](./app/sync.bat)).
- **Via PowerShell**:
  ```powershell
  .\sync.ps1
  ```
  Ou especificando uma mensagem de commit personalizada:
  ```powershell
  .\sync.ps1 -Mensagem "feat: adiciona provas UNESP 2026"
  ```

O script detecta arquivos modificados/novos, gera o commit, busca novidades com `git fetch`, integra alterações remotas com `git pull --rebase` e envia tudo com `git push`.

