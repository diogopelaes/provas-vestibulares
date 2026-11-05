# Acervo de Provas de Vestibulares

> Repositório centralizado e padronizado com todas as provas e gabaritos dos principais exames e vestibulares do Brasil (AFA, ENEM, IME, ITA, Provão Paulista, UNESP, UNICAMP e USP/Fuvest).

**URL Oficial em Produção:** [https://acervo.diogo.mat.br](https://acervo.diogo.mat.br)

---

## 🏛️ Visão Geral da Arquitetura

O projeto foi estruturado para ser uma aplicação web robusta, rápida e de baixa manutenção, pronta para rodar em servidor VPS com **Caddy** e **Gunicorn**:

- **Backend:** Python 3.14+ com **Django** e **Django REST Framework (DRF)**.
- **Frontend:** Interface moderna com tema escuro (Pico CSS v2 customizado), sem frameworks pesados de frontend (JavaScript puro com carregamento instantâneo).
- **Busca de Alta Performance:** Mecanismo de busca textual nos PDFs com **PyMuPDF**, indexação local em SQLite (`.search_cache.db`), insensibilidade a acentuação e links diretos com posicionamento na página exata (`#page=N`).
- **Autenticação Simples & Segura:**
  - **Público:** Todo o acervo (biblioteca de edições, PDFs, gabaritos e ferramenta de busca) é **aberto a qualquer visitante**, sem necessidade de login.
  - **Restrito:** O formulário e a API de upload (`/api/upload` e `/api/preview`) exigem **autenticação** via Django Auth (usuário único para o administrador alimentar o acervo).
- **Servidor Web & Proxy Reverso:** **Caddy** com HTTPS automático, compressão Zstandard/Gzip e entrega direta dos arquivos estáticos e de mídia.

---

## 📁 Estrutura de Diretórios

```text
provas-vestibulares/
│
├── core/                           # Configuração do Projeto Django
│   ├── settings.py                 # Configurações de ambiente, hosts e apps
│   ├── urls.py                     # Rotas globais (/admin/, /, /api/)
│   ├── wsgi.py                     # Ponto de entrada WSGI para Gunicorn
│   └── asgi.py                     # Ponto de entrada ASGI
│
├── app/                            # Aplicação do Acervo (Django App)
│   ├── models.py                   # Registro de auditoria (RegistroUpload)
│   ├── serializers.py              # Validação DRF de upload, preview e busca
│   ├── services.py                 # Regras de negócio (catálogo, arquivos, mtime)
│   ├── views.py                    # Views de templates e endpoints da API
│   ├── urls.py                     # Rotas da aplicação
│   ├── busca.py                    # Motor de busca textual nos PDFs
│   ├── management/commands/        # Comandos administrativos (sync_search)
│   ├── static/                     # CSS e JS do frontend
│   │   ├── css/                    # tokens.css, base.css, layout.css, etc.
│   │   └── js/                     # api.js, library.js, upload.js, busca.js
│   └── templates/                  # Templates HTML
│       ├── index.html              # Biblioteca principal do acervo
│       ├── busca.html              # Página de busca nos textos dos PDFs
│       └── login.html              # Tela de autenticação do administrador
│
├── media/                          # Pastas dos Vestibulares e PDFs do Acervo
│   ├── AFA/                        # Academia da Força Aérea
│   ├── ENEM/                       # Exame Nacional do Ensino Médio
│   ├── IME/                        # 1ª Fase e 2ª Fase
│   ├── ITA/                        # 1ª Fase e 2ª Fase
│   ├── PROVÃO/                     # 1ª Série, 2ª Série e 3ª Série
│   ├── UNESP/                      # 1ª Fase, 2ª Fase e Meio de Ano
│   ├── UNICAMP/                    # 1ª Fase e 2ª Fase
│   └── USP/                        # 1ª Fase (FEVEST) e 2ª Fase (FUVEST)
│
├── dev/                            # Arquivos e Scripts de Desenvolvimento / VPS
│   ├── Caddyfile                   # Caddyfile completo atualizado da VPS
│   ├── caddy-acervo.Caddyfile      # Bloco isolado do Caddy para acervo.diogo.mat.br
│   ├── provas-vestibulares.service # Arquivo de serviço Systemd para Gunicorn
│   ├── start_app.ps1               # Launcher local PowerShell
│   ├── start_app.bat               # Launcher local duplo-clique no Windows
│   ├── sync.ps1                    # Script PowerShell de sincronização Git
│   ├── sync.bat                    # Atalho duplo-clique para sync.ps1
│   └── server_legacy.py            # Servidor HTTP simples de protótipo (legado)
│
├── staticfiles/                    # Arquivos estáticos coletados para produção
├── deploy.sh                       # Script de deploy e atualização forçada na VPS
├── manage.py                       # Utilitário CLI do Django
├── requirements.txt                # Dependências Python
├── .env.example                    # Exemplo de variáveis de ambiente
└── .gitignore                      # Regras de exclusão do Git
```

---

## 🚀 Como Executar em Desenvolvimento Local (Windows / PowerShell)

### Opção 1: Atalho Rápido (Duplo-clique)
Dê dois cliques no arquivo [`dev/start_app.bat`](./dev/start_app.bat). O script:
1. Detecta ou cria o ambiente virtual `.venv`.
2. Instala/atualiza as dependências de `requirements.txt`.
3. Aplica as migrações do banco de dados SQLite.
4. Inicializa o índice de busca dos PDFs caso ainda não exista.
5. Inicia o servidor de desenvolvimento Django na porta 8000.
6. Abre o navegador na interface local.

### Opção 2: Linha de Comando (PowerShell)
```powershell
# Ativar o ambiente virtual
.\.venv\Scripts\Activate.ps1

# Aplicar migrações
python manage.py migrate

# Sincronizar índice dos PDFs
python manage.py sync_search

# Iniciar servidor
python manage.py runserver 8000
```

---

## 🔒 Gerenciamento de Usuário para Upload

O acervo utiliza o sistema de autenticação nativo do Django. Para criar o seu usuário administrador capaz de enviar provas:

```powershell
# No ambiente local ou na VPS:
python manage.py createsuperuser
```

1. Acesse `http://localhost:8000/login` ou [https://acervo.diogo.mat.br/login](https://acervo.diogo.mat.br/login).
2. Informe o usuário e a senha criados.
3. Ao retornar à página inicial, o botão **"+ Adicionar prova"** estará visível e ativo.
4. Para sair, basta clicar em **"Sair"** no topo da página.

O painel administrativo completo também fica disponível em `/admin/`.

---

## 🌐 Deploy e Produção na VPS (acervo.diogo.mat.br)

### 1. Clonar o Repositório na VPS
Na sua VPS Linux (Ubuntu/Debian), clone o repositório no caminho padrão:
```bash
sudo mkdir -p /var/www/provas-vestibulares
sudo chown -R $USER:$USER /var/www/provas-vestibulares
git clone <URL_DO_REPOSITORIO> /var/www/provas-vestibulares
cd /var/www/provas-vestibulares
```

### 2. Configurar o Caddy
O bloco Caddy para o domínio `acervo.diogo.mat.br` já está pronto em [`dev/caddy-acervo.Caddyfile`](./dev/caddy-acervo.Caddyfile) e no arquivo consolidado [`dev/Caddyfile`](./dev/Caddyfile):

```caddy
acervo.diogo.mat.br {
    encode zstd gzip

    handle_path /static/* {
        root * /var/www/provas-vestibulares/staticfiles
        file_server
    }

    handle_path /media/* {
        root * /var/www/provas-vestibulares/media
        file_server
    }

    handle_path /arquivos/* {
        root * /var/www/provas-vestibulares/media
        file_server
    }

    handle {
        reverse_proxy localhost:9003 {
            header_down Cache-Control "no-cache, must-revalidate"
        }
    }

    log {
        output file /var/log/caddy/acervo.access.log
    }
}
```

Adicione o bloco ao `/etc/caddy/Caddyfile` da sua VPS e recarregue:
```bash
sudo caddy reload --config /etc/caddy/Caddyfile
```

### 3. Configurar o Serviço Systemd
Copie o arquivo de serviço para o sistema:
```bash
sudo cp dev/provas-vestibulares.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable provas-vestibulares
```

### 4. Executar o Script de Deploy
Execute o script de automação:
```bash
chmod +x deploy.sh
./deploy.sh
```

O `deploy.sh`:
- Força a sincronização com o repositório remoto (`git fetch origin main && git reset --hard origin/main`).
- Garante que nenhuma alteração local da VPS tente subir ou conflitar com o Git remoto.
- Preserva a pasta `media/`, o arquivo `.env`, o banco de dados `db.sqlite3` e o cache de busca `app/.search_cache.db`.
- Atualiza o `.venv` e dependências.
- Executa migrações (`migrate`) e coleta estáticos (`collectstatic`).
- Indexa novos PDFs adicionados.
- Reinicia o serviço Gunicorn (`provas-vestibulares.service`) e recarrega o Caddy.

### 5. Atualizações Futuras
Sempre que fizer alterações no repositório remoto, basta rodar na VPS:
```bash
./deploy.sh
```
Todo o processo de deploy e alinhamento forçado é executado em segundos sem intervenção manual.

---

## ⚡ Cache Busting Automático

Em conformidade com as diretrizes do projeto:
- Todo arquivo CSS ou JS chamado nos templates utiliza `?v={{v:caminho/arquivo.ext}}`.
- O backend Django substitui dinamicamente essa tag pelo timestamp de modificação (`st_mtime`) do arquivo estático em disco.
- Ao editar qualquer CSS ou JS, os navegadores dos usuários baixam a versão atualizada imediatamente, sem problemas de cache persistente.
