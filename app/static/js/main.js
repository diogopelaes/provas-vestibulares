/**
 * ===============================================================================
 * ARQUIVO: app/static/js/main.js
 * CAMADA: Frontend / Ponto de Entrada da Aplicação
 * PAPEL NO SISTEMA:
 *   - Orquestra a inicialização da aplicação ao carregar a página:
 *       1. Busca os dados completos do catálogo via App.api.getCatalogo().
 *       2. Inicializa o módulo de visualização da biblioteca (App.library.init).
 *       3. Inicializa o módulo do modal de upload (App.upload.init).
 *       4. Configura atalhos globais de teclado ergonômicos:
 *          - '/' ou 'Ctrl+K' : Foca imediatamente no campo de busca.
 *          - 'N'             : Abre o modal para adicionar nova prova.
 *          - 'Escape'        : Fecha modais ou limpa o campo de busca ativo.
 * ===============================================================================
 */

(function () {
  'use strict';

  const App = (window.App = window.App || {});

  async function bootstrap() {
    const elContent = document.getElementById('content');
    const elSearch = document.getElementById('search-input');

    try {
      const catalogo = await App.api.getCatalogo();

      App.library.init(catalogo);
      App.upload.init(catalogo);

      // Controle do menu lateral no mobile (drawer)
      const btnMenuToggle = document.getElementById('btn-menu-toggle');
      const btnSidebarClose = document.getElementById('sidebar-close');
      const sidebarBackdrop = document.getElementById('sidebar-backdrop');

      function openSidebar() {
        document.body.classList.add('sidebar-open');
        if (btnMenuToggle) btnMenuToggle.setAttribute('aria-expanded', 'true');
      }

      function closeSidebar() {
        document.body.classList.remove('sidebar-open');
        if (btnMenuToggle) btnMenuToggle.setAttribute('aria-expanded', 'false');
      }

      if (btnMenuToggle) {
        btnMenuToggle.addEventListener('click', () => {
          if (document.body.classList.contains('sidebar-open')) {
            closeSidebar();
          } else {
            openSidebar();
          }
        });
      }

      if (btnSidebarClose) {
        btnSidebarClose.addEventListener('click', closeSidebar);
      }

      if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener('click', closeSidebar);
      }

      // Atalhos de teclado globais
      document.addEventListener('keydown', (e) => {
        const target = e.target;
        const isEditing =
          target.tagName === 'INPUT' ||
          target.tagName === 'SELECT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable;

        // Fechar menu lateral com Escape
        if (e.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
          closeSidebar();
          return;
        }

        // Focar na busca com "/" ou "Ctrl+K"
        if ((e.key === '/' && !isEditing) || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')) {
          e.preventDefault();
          if (elSearch) {
            closeSidebar();
            elSearch.focus();
            elSearch.select();
          }
          return;
        }

        // Abrir modal de upload com "N"
        if (e.key.toLowerCase() === 'n' && !isEditing && !e.ctrlKey && !e.metaKey && !e.altKey) {
          e.preventDefault();
          closeSidebar();
          App.upload.open();
          return;
        }

        // Limpar busca com Escape
        if (e.key === 'Escape' && target === elSearch && elSearch.value) {
          elSearch.value = '';
          elSearch.dispatchEvent(new Event('input', { bubbles: true }));
        }
      });
    } catch (err) {
      console.error('Falha ao inicializar a aplicação:', err);
      if (elContent) {
        elContent.innerHTML = '';
        elContent.appendChild(
          App.ui.h(
            'div',
            { class: 'state-error' },
            App.ui.iconNode('alert'),
            App.ui.h('h3', null, 'Não foi possível carregar o acervo'),
            App.ui.h('p', null, err.message || 'Verifique se o servidor Python está em execução.'),
            App.ui.h(
              'button',
              {
                type: 'button',
                class: 'btn btn-primary',
                onclick: () => window.location.reload(),
              },
              'Tentar novamente'
            )
          )
        );
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
})();
