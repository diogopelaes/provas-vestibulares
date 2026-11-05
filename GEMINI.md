# Diretrizes de Operação do Assistente (Gemini / Antigravity)

## 🚫 RESTRIÇÃO CRÍTICA: NUNCA USAR O NAVEGADOR
- **É ESTRITAMENTE PROIBIDO** invocar ferramentas de automação de navegador (`browser_subagent`, abertura de browser, gravação de sessão web, etc.).
- Não abra nem tente controlar o navegador do usuário ou subagentes de navegador sob nenhuma hipótese.

---

## ⚡ Controle de Cache e Cache Busting (CSS e JavaScript)

Para evitar que navegadores fiquem presos em versões obsoletas de arquivos estáticos em cache após modificações, as seguintes regras devem ser rigorosamente seguidas:

### 1. Parâmetro Dinâmico de Versão (`?v={{v:...}}`)
- **Obrigatoriedade nos Templates:** Toda referência a arquivos estáticos próprios do projeto (`.css` e `.js`) dentro dos templates HTML (`app/templates/`) deve obrigatoriamente incluir a query string com o marcador de versão:
  - **CSS:** `<link rel="stylesheet" href="/static/css/arquivo.css?v={{v:css/arquivo.css}}">`
  - **JS:** `<script src="/static/js/arquivo.js?v={{v:js/arquivo.js}}"></script>`
- **Mecanismo de Substituição:** O backend (`app.services.render_with_asset_versions`) substitui dinamicamente qualquer ocorrência de `{{v:relpath}}` pelo timestamp de última modificação do arquivo (`st_mtime`).
- Sempre que um novo arquivo CSS ou JS for criado ou referenciado, certifique-se de adicionar a tag `?v={{v:...}}`.

### 2. Cabeçalhos HTTP de Não Cacheamento para Páginas HTML
- As views que renderizam páginas HTML (`index_view`, `busca_view`, `login_view`, etc.) devem sempre enviar:
  ```http
  Cache-Control: no-cache, no-store, must-revalidate
  Pragma: no-cache
  Expires: 0
  ```
- Isso força o navegador a validar e baixar o HTML atualizado a cada requisição, recebendo os novos hashes de versão dos arquivos estáticos imediatamente.

### 3. Coleta de Estáticos em Produção
- Em ambiente de produção e deploy (`dev/deploy.sh`), deve ser sempre executado `python manage.py collectstatic --noinput` para sincronizar os estáticos com o diretório servido pelo Caddy (`staticfiles/`).

