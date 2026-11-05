/**
 * ===============================================================================
 * ARQUIVO: app/static/js/api.js
 * CAMADA: Frontend / Acesso à API
 * PAPEL NO SISTEMA:
 *   - Expõe window.App.api, centralizando as chamadas HTTP ao backend Django:
 *       * getCatalogo(): GET /api/catalogo — acervo completo agrupado.
 *       * upload(payload): POST /api/upload — envia PDFs em Base64.
 *       * getAuthStatus(): GET /api/auth/status — status de login do usuário.
 *   - Converte respostas de erro em exceções com a mensagem vinda do servidor.
 *   - Inclui cabeçalho X-CSRFToken automaticamente em requisições POST/PUT/DELETE.
 * ===============================================================================
 */
(function () {
  'use strict';

  const App = (window.App = window.App || {});

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  async function request(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = { ...(options.headers || {}) };

    if (method !== 'GET' && method !== 'HEAD') {
      const csrf = getCookie('csrftoken');
      if (csrf) {
        headers['X-CSRFToken'] = csrf;
      }
    }

    let response;
    try {
      response = await fetch(url, { cache: 'no-store', ...options, headers });
    } catch {
      throw new Error('Não foi possível conectar ao servidor. Verifique se ele está ativo.');
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const errorMsg = data.error || (typeof data === 'object' && Object.values(data)[0]) || `Erro ${response.status} ao acessar ${url}`;
      throw new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    }
    return data;
  }

  App.api = {
    getCatalogo: () => request('/api/catalogo'),
    getAuthStatus: () => request('/api/auth/status'),
    upload: (payload) =>
      request('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
  };

  App.getCookie = getCookie;
})();
