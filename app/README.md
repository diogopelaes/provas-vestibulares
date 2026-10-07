# Aplicação de Upload e Padronização de Provas (`app`)

Esta aplicação consiste em um servidor local leve e uma interface web moderna (em tema escuro) desenvolvida para salvar e padronizar automaticamente os arquivos de provas e gabaritos dos vestibulares nas respectivas pastas do projeto.

---

## 🏛️ Arquitetura e Camadas

A pasta `app/` é organizada seguindo a separação de responsabilidades em camadas:

```text
app/
├── server.py             # Camada de Backend / Servidor HTTP e API REST
├── start_app.ps1         # Script PowerShell (detecta porta livre, abre navegador e roda servidor)
├── start_app.bat         # Launcher Batch para Windows Explorer (executa o ps1)
├── templates/            # Camada de Apresentação (HTML)
│   └── index.html        # Interface do usuário com Pico CSS v2 (Dark Theme)
├── static/               # Camada de Recursos Estáticos
│   ├── css/
│   │   └── style.css     # Estilos complementares (Glassmorphism, Drag & Drop, Layout)
│   └── js/
│       └── app.js        # Lógica de cliente (preview em tempo real, encoding Base64)
└── README.md             # Esta documentação
```

---

## 🚀 Como Executar

A aplicação pode ser iniciada de três formas simples:

### Opção 1: Via Duplo Clique (Mais Rápido no Windows)
Basta dar um duplo clique no arquivo [`app/start_app.bat`](./start_app.bat). Ele executará o PowerShell, verificará portas ocupadas, abrirá o navegador e iniciará o servidor automaticamente.

### Opção 2: Via Script PowerShell
No terminal PowerShell:
```powershell
.\app\start_app.ps1
```
*(O script verifica se a porta 8000 está em uso. Se estiver, busca automaticamente 8001, 8002, etc., e abre o navegador na porta encontrada).*

### Opção 3: Execução Manual com Python do `.venv`
```powershell
.\.venv\Scripts\python.exe app\server.py
```

---

## 📋 Como Funciona a Interface

1. **Seleção do Vestibular**: Carrega dinamicamente as pastas existentes no projeto (`AFA`, `IME`, `ITA`, `UNESP`, `UNICAMP`, `USP`).
2. **Ano do Vestibular**: Campo numérico para informar o ano da prova.
3. **Fase do Vestibular**:
   - `1ª Fase`: Prova e gabarito da 1ª fase.
   - `2ª Fase`: Prova e gabarito da 2ª fase.
   - *Nota*: Para a **AFA**, o sistema detecta automaticamente que se trata de fase única, salvando diretamente na raiz de `AFA/`.
   - *Nota*: Para a **USP**, é possível alternar entre o prefixo `FEVEST` (padrão histórico existente na pasta `1ª Fase`) ou `FUVEST`.
4. **Uploads Drag & Drop**: Áreas para arrastar ou clicar e selecionar os arquivos PDF da Prova e do Gabarito.
5. **Preview em Tempo Real**: Antes de salvar, exibe exatamente qual pasta de destino e quais nomes de arquivo serão gerados.

---

## 🏷️ Regras de Nomenclatura Aplicadas

| Vestibular | Fase | Pasta de Destino | Nome da Prova | Nome do Gabarito |
|---|---|---|---|---|
| **AFA** | Única | `AFA/` | `AFA_{ANO}.pdf` | `AFA_{ANO}_gab.pdf` |
| **IME** | 1ª | `IME/1ª Fase/` | `IME_{ANO}_1Fase.pdf` | `IME_{ANO}_1Fase_gab.pdf` |
| **IME** | 2ª | `IME/2ª Fase/` | `IME_{ANO}_2Fase.pdf` | `IME_{ANO}_2Fase_gab.pdf` |
| **ITA** | 1ª | `ITA/1ª Fase/` | `ITA_{ANO}_1Fase.pdf` | `ITA_{ANO}_1Fase_gab.pdf` |
| **ITA** | 2ª | `ITA/2ª Fase/` | `ITA_{ANO}_2Fase.pdf` | `ITA_{ANO}_2Fase_gab.pdf` |
| **UNESP** | 1ª | `UNESP/1ª Fase/` | `UNESP_{ANO}_1Fase.pdf` | `UNESP_{ANO}_1Fase_gab.pdf` |
| **UNESP** | 2ª | `UNESP/2ª Fase/` | `UNESP_{ANO}_2Fase.pdf` | `UNESP_{ANO}_2Fase_gab.pdf` |
| **UNICAMP** | 1ª | `UNICAMP/1ª Fase/` | `UNICAMP_{ANO}_1Fase.pdf` | `UNICAMP_{ANO}_1Fase_gab.pdf` |
| **UNICAMP** | 2ª | `UNICAMP/2ª Fase/` | `UNICAMP_{ANO}_2Fase.pdf` | `UNICAMP_{ANO}_2Fase_gab.pdf` |
| **USP** | 1ª | `USP/1ª Fase/` | `FEVEST_{ANO}_1Fase.pdf` | `FEVEST_{ANO}_1Fase_gab.pdf` |
| **USP** | 2ª | `USP/2ª Fase/` | `FUVEST_{ANO}_2Fase.pdf` | `FUVEST_{ANO}_2Fase_gab.pdf` |

---

## 🔌 Endpoints da API

- **`GET /api/vestibulares`**: Retorna a lista de pastas de vestibulares disponíveis na raiz.
- **`POST /api/preview`**: Recebe `{ vestibular, ano, fase, prefixo_usp }` e retorna os caminhos e nomes esperados.
- **`POST /api/upload`**: Recebe o payload com dados em Base64 e grava os arquivos em disco no caminho apropriado.
