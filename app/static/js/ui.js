/**
 * ===============================================================================
 * ARQUIVO: app/static/js/ui.js
 * CAMADA: Frontend / Utilitários de interface (sem dependências)
 * PAPEL NO SISTEMA:
 *   - Expõe window.App.ui com helpers usados pelos demais scripts:
 *       * h(tag, props, ...children): cria elementos DOM com segurança (texto via
 *         textContent; "html" só para SVGs estáticos e confiáveis).
 *       * iconNode(nome): ícones SVG inline (traço fino, estilo consistente).
 *       * colorFor(nome): cor estável e dessaturada por vestibular (hash do nome),
 *         assim novas pastas ganham cor automaticamente.
 *       * normalize(texto): minúsculas e sem acentos (para busca).
 *       * formatBytes, plural, debounce.
 *       * toast(mensagem, opções): notificações não intrusivas no canto da tela.
 * ===============================================================================
 */
(function () {
  'use strict';

  const App = (window.App = window.App || {});

  const ICON_PATHS = {
    file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    checkSquare: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    book: '<path d="M4 19.5V6a2 2 0 0 1 2-2h12v15H6.5A2.5 2.5 0 0 0 4 21.5"/><path d="M18 19v3H6.5"/>',
    paperclip: '<path d="m21 11-8.6 8.6a5 5 0 0 1-7-7l8.6-8.6a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l7.9-7.9"/>',
    external: '<path d="M14 4h6v6"/><path d="M20 4 10 14"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    alert: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><path d="M12 16h.01"/>',
    inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    arrowRight: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  };

  function iconMarkup(name) {
    return (
      '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (ICON_PATHS[name] || '') +
      '</svg>'
    );
  }

  function iconNode(name) {
    const template = document.createElement('template');
    template.innerHTML = iconMarkup(name);
    return template.content.firstElementChild;
  }

  /** Cria um elemento DOM. Filhos string viram nós de texto (sem injeção de HTML). */
  function h(tag, props, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === 'class') el.className = value;
      else if (key === 'html') el.innerHTML = value;
      else if (key === 'dataset') Object.assign(el.dataset, value);
      else if (key === 'style' && typeof value === 'object') {
        for (const [prop, val] of Object.entries(value)) el.style.setProperty(prop, val);
      } else if (key.startsWith('on') && typeof value === 'function') {
        el.addEventListener(key.slice(2).toLowerCase(), value);
      } else el.setAttribute(key, value === true ? '' : value);
    }
    for (const child of children.flat(Infinity)) {
      if (child === null || child === undefined || child === false) continue;
      el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
  }

  /** Cor estável e de baixa saturação derivada do nome. */
  function colorFor(name) {
    let hash = 0;
    for (const char of String(name)) hash = (hash * 31 + char.codePointAt(0)) >>> 0;
    const hue = (hash * 137.508) % 360;
    return `hsl(${hue.toFixed(0)} 22% 68%)`;
  }

  function normalize(text) {
    return String(text || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
  }

  function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / 1024 ** index;
    return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
  }

  function plural(count, singular, pluralForm) {
    return `${count} ${count === 1 ? singular : pluralForm || singular + 's'}`;
  }

  function debounce(fn, wait) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), wait);
    };
  }

  function toast(message, { type = 'success', detail = '', timeout = 4200 } = {}) {
    const container = document.getElementById('toasts');
    if (!container) return;
    const el = h(
      'div',
      { class: `toast toast--${type}`, role: type === 'error' ? 'alert' : 'status' },
      iconNode(type === 'error' ? 'alert' : 'check'),
      h('div', { class: 'toast-body' }, h('strong', null, message), detail ? h('span', null, detail) : null)
    );
    container.append(el);
    setTimeout(() => {
      el.classList.add('is-leaving');
      setTimeout(() => el.remove(), 260);
    }, timeout);
  }

  App.ui = { h, iconNode, colorFor, normalize, formatBytes, plural, debounce, toast };
})();
