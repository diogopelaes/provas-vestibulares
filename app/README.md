# Aplicação do Acervo de Vestibulares (`app`)

Esta aplicação consiste em um servidor local leve e uma interface web moderna em **tema escuro de baixo contraste** desenvolvida para:
1. **Navegar e Visualizar** todas as provas e gabaritos em PDF diretamente pelo navegador em novas abas (`target="_blank"`).
2. **Filtrar e Buscar** facilmente por instituição, ano, fase ou presença de gabarito.
3. **Adicionar Novas Provas** por meio de um modal rápido que valida, padroniza e salva os arquivos nas pastas corretas do projeto.

---

## 🏛️ Arquitetura e Camadas

A pasta `app/` é organizada seguindo a separação limpa de responsabilidades:

```text
app/
├── server.py             # Backend: Servidor HTTP multithread, API do catálogo e uploads seguros
├── start_app.ps1         # Script PowerShell (detecta porta livre, abre navegador e roda servidor)
├── start_app.bat         # Launcher Batch para Windows Explorer (duplo clique)
├── templates/
│   └── index.html        # Página principal da biblioteca + Modal de upload
├── static/
│   ├── css/
│   │   ├── tokens.css    # Paleta de cores escura de baixo contraste e variáveis
│   │   ├── base.css      # Ajustes globais, reset e tipografia (Inter / JetBrains Mono)
│   │   ├── layout.css    # Sidebar, toolbar, responsividade
│   │   ├── components.css# Cards de exames, links de documentos, filtros e toasts
│   │   └── upload.css    # Modal dialog, controle segmentado e dropzones
│   └── js/
│       ├── ui.js         # Utilitários DOM seguros, ícones SVG e toasts
│       ├── api.js        # Cliente HTTP centralizado (/api/catalogo, /api/upload)
│       ├── library.js    # Renderização da biblioteca, busca, filtros e rota por hash
│       ├── upload.js     # Controle do modal de envio, preview e drag & drop
│       └── main.js       # Inicialização e atalhos de teclado globais
└── README.md             # Esta documentação
```

---

## 🚀 Como Executar

A aplicação pode ser iniciada de três formas simples:

### Opção 1: Via Duplo Clique (Recomendado no Windows)
Dê um duplo clique no arquivo [`app/start_app.bat`](./start_app.bat). Ele cuida de criar o `.venv` caso não exista, atualizar o `pip`, verificar portas ocupadas e abrir a página no navegador.

### Opção 2: Pelo Terminal PowerShell
```powershell
.\app\start_app.ps1
```

### Opção 3: Execução Manual com o Python do `.venv`
```powershell
.\.venv\Scripts\python.exe app\server.py
```

Acesse no navegador: **[http://localhost:8000](http://localhost:8000)**

---

## ⌨️ Atalhos de Teclado

- `/` ou `Ctrl+K`: Foca diretamente na barra de busca.
- `N`: Abre o modal para adicionar nova prova.
- `Esc`: Fecha o modal ou limpa a busca.

---

## 🔌 Endpoints da API

- **`GET /`**: Retorna a interface do acervo com cache-busting dinâmico nos estáticos.
- **`GET /api/catalogo`**: Retorna o catálogo estruturado com contagem de edições, arquivos e anos por vestibular.
- **`GET /api/vestibulares`**: Retorna a lista de pastas de vestibulares disponíveis.
- **`GET /arquivos/<caminho>`**: Serve os arquivos PDF com cabeçalho `inline` para leitura imediata em outra aba.
- **`POST /api/preview`**: Calcula a pasta e nomes padronizados antes do envio.
- **`POST /api/upload`**: Grava os arquivos PDF enviados em Base64 no disco respeitando a nomenclatura oficial.
