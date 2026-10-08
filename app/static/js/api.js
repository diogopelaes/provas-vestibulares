/**
 * ===============================================================================
 * ARQUIVO: app/static/js/api.js
 * CAMADA: Frontend / Acesso à API
 * PAPEL NO SISTEMA:
 *   - Expõe window.App.api, centralizando as chamadas HTTP ao backend (server.py):
 *       * getCatalogo(): GET /api/catalogo — acervo completo agrupado.
 *       * upload(payload): POST /api/upload — envia PDFs em Base64.
 *   - Converte respostas de erro em exceções com a mensagem vinda do servidor.
 * ===============================================================================
 */
(function () {
  'use strict';

  const App = (window.App = window.App || {});

  async function request(url, options = {}) {
    let response;
    try {
      response = await fetch(url, { cache: 'no-store', ...options });
    } catch {
      throw new Error('Não foi possível falar com o servidor local. Ele está em execução?');
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Erro ${response.status} ao acessar ${url}`);
    return data;
  }

  App.api = {
    getCatalogo: () => request('/api/catalogo'),
    upload: (payload) =>
      request('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
  };
})();
