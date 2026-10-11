# Diretrizes de Operação do Assistente (Gemini / Antigravity)

## 🚫 RESTRIÇÃO CRÍTICA: NUNCA USAR O NAVEGADOR
- **É ESTRITAMENTE PROIBIDO** invocar ferramentas de automação de navegador (`browser_subagent`, abertura de browser, gravação de sessão web, etc.).
- Não abra nem tente controlar o navegador do usuário ou subagentes de navegador sob nenhuma hipótese.
- Para validar alterações no frontend (HTML/CSS/JS):
  - Analise o código estático com cuidado.
  - Teste requisições via curl/Invoke-RestMethod ou rotas HTTP via scripts caso necessário.
  - Nunca acione a ferramenta de navegador.

## ⚡ CACHE BUSTING: SEMPRE ATUALIZAR VERSÃO DE CSS E JS
- **Obrigatoriedade nos Templates HTML**:
  - Toda referência a arquivos CSS (`<link rel="stylesheet">`) e JS (`<script src="...">`) nos templates (`index.html`, `busca.html`, etc.) deve **obrigatoriamente** incluir o parâmetro de versão dinâmica:
    - CSS: `href="/static/css/arquivo.css?v={{v:css/arquivo.css}}"`
    - JS: `src="/static/js/arquivo.js?v={{v:js/arquivo.js}}"`
  - O servidor Python substitui automaticamente `{{v:relpath}}` pelo timestamp (`st_mtime`) da última modificação do arquivo em disco, forçando o navegador a carregar o novo arquivo imediatamente após qualquer edição.
- **Serviço de Arquivos Estáticos (`app/server.py`)**:
  - Requisições sem a query string `?v=` devem ser servidas com `Cache-Control: no-cache, must-revalidate` para garantir que ambientes de desenvolvimento e acessos diretos nunca fiquem travados em caches antigos do navegador.
