/**
 * ===============================================================================
 * ARQUIVO: app/static/js/busca.js
 * CAMADA: Frontend / Controlador da Busca Avançada
 * PAPEL NO SISTEMA:
 *   - Gerencia a interação do usuário na página de busca textual (busca.html):
 *       * Carrega opções disponíveis de vestibulares e anos (/api/busca/opcoes).
 *       * Controla seleção dinâmica de filtros (vestibulares múltiplos, presets de anos).
 *       * Dispara requisições à API (/api/busca) e renderiza cards de resultados.
 *       * Links diretos para os PDFs na página exata (#page=N).
 *       * Cópia rápida de trechos citados e atalhos de teclado (/ e Enter).
 * ===============================================================================
 */
(function () {
  'use strict';

  const { h, colorFor, toast } = window.App.ui;

  // Estado interno dos filtros
  const state = {
    vestibularesDisponiveis: [],
    anosDisponiveis: [],
    selecionadosVest: new Set(),
    selecionadosAnos: new Set(),
    carregando: false,
    ultimoResultado: null,
  };

  // Elementos DOM
  const elements = {
    form: document.getElementById('search-form'),
    input: document.getElementById('query-input'),
    btnSubmit: document.getElementById('btn-submit-search'),
    vestChips: document.getElementById('vest-chips'),
    btnVestAll: document.getElementById('btn-vest-all'),
    btnVestNone: document.getElementById('btn-vest-none'),
    yearsGrid: document.getElementById('years-grid'),
    yearsPresets: document.getElementById('years-presets'),
    btnYearsAll: document.getElementById('btn-years-all'),
    btnYearsNone: document.getElementById('btn-years-none'),
    chkTipoProva: document.getElementById('chk-tipo-prova'),
    chkTipoGabarito: document.getElementById('chk-tipo-gabarito'),
    chkTipoResol: document.getElementById('chk-tipo-resol'),
    chkIgnoreAccents: document.getElementById('chk-ignore-accents'),
    chkCaseSensitive: document.getElementById('chk-case-sensitive'),
    statusBar: document.getElementById('status-bar'),
    statusText: document.getElementById('status-text'),
    statusTime: document.getElementById('status-time'),
    vestBreakdown: document.getElementById('vest-breakdown'),
    resultsContainer: document.getElementById('results-container'),
    initialState: document.getElementById('initial-state'),
  };

  // ===========================================================================
  // 1. Inicialização e Carga de Opções
  // ===========================================================================
  async function carregarOpcoes() {
    try {
      const response = await fetch('/api/busca/opcoes');
      if (!response.ok) throw new Error('Falha ao carregar opções de busca.');
      const data = await response.json();

      state.vestibularesDisponiveis = data.vestibulares || [];
      state.anosDisponiveis = data.anos_disponiveis || [];

      // Seleciona todos os vestibulares por padrão
      state.selecionadosVest = new Set(state.vestibularesDisponiveis.map((v) => v.nome));
      // Seleciona todos os anos por padrão
      state.selecionadosAnos = new Set(state.anosDisponiveis);

      renderizarChipsVestibulares();
      renderizarGridAnos();
    } catch (err) {
      console.error(err);
      toast('Não foi possível carregar os vestibulares disponíveis.', { tipo: 'danger' });
    }
  }

  // ===========================================================================
  // 2. Renderização dos Filtros (Vestibulares e Anos)
  // ===========================================================================
  function renderizarChipsVestibulares() {
    elements.vestChips.innerHTML = '';
    state.vestibularesDisponiveis.forEach((vest) => {
      const cor = colorFor(vest.nome);
      const isAtivo = state.selecionadosVest.has(vest.nome);

      const chip = h(
        'button',
        {
          type: 'button',
          class: `vest-chip ${isAtivo ? 'is-active' : ''}`,
          style: { '--c': cor },
          title: `Alternar vestibular ${vest.nome} (${vest.total_arquivos} arquivos)`,
          onClick: () => alternarVestibular(vest.nome),
        },
        h('span', { class: 'vest-dot' }),
        h('span', {}, vest.nome),
        h('span', { class: 'vest-count' }, `${vest.total_arquivos}`)
      );

      elements.vestChips.appendChild(chip);
    });
  }

  function alternarVestibular(nome) {
    if (state.selecionadosVest.has(nome)) {
      state.selecionadosVest.delete(nome);
    } else {
      state.selecionadosVest.add(nome);
    }
    renderizarChipsVestibulares();
  }

  function renderizarGridAnos() {
    elements.yearsGrid.innerHTML = '';
    state.anosDisponiveis.forEach((ano) => {
      const isAtivo = state.selecionadosAnos.has(ano);
      const chip = h(
        'button',
        {
          type: 'button',
          class: `year-chip ${isAtivo ? 'is-active' : ''}`,
          title: `Alternar ano ${ano}`,
          onClick: () => alternarAno(ano),
        },
        String(ano)
      );
      elements.yearsGrid.appendChild(chip);
    });
  }

  function alternarAno(ano) {
    if (state.selecionadosAnos.has(ano)) {
      state.selecionadosAnos.delete(ano);
    } else {
      state.selecionadosAnos.add(ano);
    }
    atualizarPresetsAnos();
    renderizarGridAnos();
  }

  function aplicarPresetAnos(preset) {
    const atualAno = new Date().getFullYear();
    const todosAnos = state.anosDisponiveis;

    // Remove classe ativa de outros presets
    elements.yearsPresets.querySelectorAll('.preset-chip').forEach((p) => {
      p.classList.toggle('is-active', p.dataset.preset === preset);
    });

    if (preset === 'all') {
      state.selecionadosAnos = new Set(todosAnos);
    } else if (preset === 'last3') {
      state.selecionadosAnos = new Set(todosAnos.filter((a) => a >= atualAno - 3));
    } else if (preset === 'last5') {
      state.selecionadosAnos = new Set(todosAnos.filter((a) => a >= atualAno - 5));
    } else if (preset === 'last10') {
      state.selecionadosAnos = new Set(todosAnos.filter((a) => a >= atualAno - 10));
    } else if (preset === '2020s') {
      state.selecionadosAnos = new Set(todosAnos.filter((a) => a >= 2020));
    } else if (preset === '2010s') {
      state.selecionadosAnos = new Set(todosAnos.filter((a) => a >= 2010 && a <= 2019));
    } else if (preset === 'pre2010') {
      state.selecionadosAnos = new Set(todosAnos.filter((a) => a < 2010));
    }

    renderizarGridAnos();
  }

  function atualizarPresetsAnos() {
    // Desmarca presets quando houver seleção manual fora do padrão
    elements.yearsPresets.querySelectorAll('.preset-chip').forEach((p) => {
      if (p.dataset.preset === 'all') {
        p.classList.toggle('is-active', state.selecionadosAnos.size === state.anosDisponiveis.length);
      } else {
        p.classList.remove('is-active');
      }
    });
  }

  // ===========================================================================
  // 3. Execução da Busca
  // ===========================================================================
  async function executarBusca(queryManual) {
    const termo = (queryManual !== undefined ? queryManual : elements.input.value).trim();
    if (!termo) {
      toast('Digite uma palavra ou termo para pesquisar.', { tipo: 'warn' });
      elements.input.focus();
      return;
    }

    // Tipos de arquivos
    const tipos = [];
    if (elements.chkTipoProva.checked) tipos.push('prova');
    if (elements.chkTipoGabarito.checked) tipos.push('gabarito');
    if (elements.chkTipoResol.checked) tipos.push('resolucao');

    if (tipos.length === 0) {
      toast('Selecione ao menos um tipo de arquivo (Provas ou Gabaritos).', { tipo: 'warn' });
      return;
    }

    // Modo de combinação
    const modoInput = document.querySelector('input[name="search-mode"]:checked');
    const modo = modoInput ? modoInput.value : 'exata';

    // Opções de payload
    const payload = {
      termo,
      vestibulares: Array.from(state.selecionadosVest),
      anos: Array.from(state.selecionadosAnos),
      tipos,
      modo,
      sensivel_acentos: !elements.chkIgnoreAccents.checked,
      sensivel_maiusculas: elements.chkCaseSensitive.checked,
      limite: 300,
    };

    setCarregando(true);
    elements.resultsContainer.innerHTML = '';
    renderizarSkeletons();

    try {
      const response = await fetch('/api/busca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || 'Erro na requisição de busca.');
      }

      const resultado = await response.json();
      state.ultimoResultado = resultado;
      renderizarResultados(resultado);
    } catch (err) {
      console.error(err);
      toast(err.message || 'Erro ao processar a busca.', { tipo: 'danger' });
      renderizarEstadoErro(err.message);
    } finally {
      setCarregando(false);
    }
  }

  function setCarregando(ativo) {
    state.carregando = ativo;
    elements.btnSubmit.disabled = ativo;
    elements.btnSubmit.style.opacity = ativo ? '0.7' : '1';
    if (ativo) {
      elements.statusBar.hidden = false;
      elements.statusText.innerHTML = 'Pesquisando nos PDFs das provas…';
      elements.statusTime.textContent = 'Aguarde';
      elements.vestBreakdown.hidden = true;
    }
  }

  function renderizarSkeletons() {
    elements.resultsContainer.innerHTML = '';
    for (let i = 0; i < 4; i++) {
      const skel = h(
        'div',
        { class: 'result-card', style: { opacity: '0.6' } },
        h('span', { class: 'skeleton skeleton-row', style: { width: '40%', height: '20px', marginBottom: '1rem' } }),
        h('span', { class: 'skeleton skeleton-row', style: { width: '90%', height: '16px', marginBottom: '0.5rem' } }),
        h('span', { class: 'skeleton skeleton-row', style: { width: '75%', height: '16px' } })
      );
      elements.resultsContainer.appendChild(skel);
    }
  }

  // ===========================================================================
  // 4. Renderização dos Resultados e Trechos
  // ===========================================================================
  function renderizarResultados(res) {
    elements.resultsContainer.innerHTML = '';

    // Atualiza Barra de Status
    elements.statusBar.hidden = false;
    elements.statusText.innerHTML = `
      Encontradas <strong>${res.total_ocorrencias} ocorrências</strong>
      em <strong>${res.total_paginas} páginas</strong>
      (de <strong>${res.total_provas} provas</strong>).
    `;
    elements.statusTime.textContent = `${res.tempo_ms}ms`;

    // Pílulas de Distribuição por Vestibular
    renderizarDistribuicaoVestibulares(res.resumo_vestibulares);

    if (res.resultados.length === 0) {
      renderizarVazio(res.termo);
      return;
    }

    // Renderiza cada card de resultado
    res.resultados.forEach((item) => {
      const card = criarCardResultado(item);
      elements.resultsContainer.appendChild(card);
    });
  }

  function renderizarDistribuicaoVestibulares(resumo) {
    elements.vestBreakdown.innerHTML = '';
    const entradas = Object.entries(resumo || {});
    if (entradas.length <= 1) {
      elements.vestBreakdown.hidden = true;
      return;
    }

    elements.vestBreakdown.hidden = false;
    entradas.forEach(([vest, count]) => {
      const cor = colorFor(vest);
      const pill = h(
        'div',
        { class: 'breakdown-pill', style: { '--c': cor } },
        h('span', { class: 'breakdown-dot' }),
        h('span', {}, vest),
        h('span', { class: 'breakdown-badge' }, `${count}`)
      );
      elements.vestBreakdown.appendChild(pill);
    });
  }

  function criarCardResultado(item) {
    const cor = colorFor(item.vestibular);

    // Badges de Cabeçalho
    const badgesHeader = h(
      'div',
      { class: 'result-badges' },
      h('span', { class: 'badge-vest', style: { '--c': cor, borderColor: cor, color: cor } }, item.vestibular),
      h('span', { class: 'badge-ano' }, String(item.ano || '—')),
      h('span', { class: 'badge-tipo' }, item.tipo || 'prova'),
      item.fase && item.fase !== 'unica'
        ? h('span', { class: 'badge-fase' }, `${item.fase}ª Fase`)
        : null
    );

    // Badge com Página Exata
    const badgePage = h(
      'span',
      { class: 'badge-page', title: `Posicionado na página ${item.pagina} do PDF` },
      h('svg', {
        class: 'icon',
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '2',
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        style: { width: '14px', height: '14px' },
        html: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
      }),
      `Página ${item.pagina} de ${item.total_paginas}`
    );

    const header = h('div', { class: 'result-header' }, badgesHeader, badgePage);

    // Trechos contextuais com tags <mark>
    const snippetsBox = h('div', { class: 'result-snippets' });
    (item.trechos || []).forEach((trechoHtml) => {
      const sEl = h('div', { class: 'snippet-box', html: trechoHtml });
      snippetsBox.appendChild(sEl);
    });

    // Informação de arquivo e Botão de Ação
    const fileInfo = h(
      'div',
      { class: 'result-file-info', title: item.caminho },
      h('svg', {
        class: 'icon',
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '1.6',
        style: { width: '13px', height: '13px', flexShrink: '0' },
        html: '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
      }),
      h('span', {}, item.arquivo)
    );

    // Botões de Ação
    const btnOpenPdf = h(
      'a',
      {
        href: item.url,
        target: '_blank',
        rel: 'noopener noreferrer',
        class: 'btn-open-pdf',
        title: `Abrir prova no navegador diretamente na página ${item.pagina}`,
      },
      h('svg', {
        class: 'icon',
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '2',
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        style: { width: '14px', height: '14px' },
        html: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
      }),
      `Abrir PDF na Página ${item.pagina}`
    );

    const btnCopySnippet = h(
      'button',
      {
        type: 'button',
        class: 'btn btn-ghost',
        style: { height: '32px', fontSize: '0.78rem', padding: '0 0.6rem' },
        title: 'Copiar citação para a área de transferência',
        onClick: () => {
          const textoLimpo = (item.trechos || []).map((t) => t.replace(/<[^>]+>/g, '')).join('\n---\n');
          const citacao = `[${item.vestibular} ${item.ano} - Pág. ${item.pagina}]\n${textoLimpo}`;
          navigator.clipboard.writeText(citacao).then(() => {
            toast('Trecho copiado para a área de transferência!');
          });
        },
      },
      'Copiar citação'
    );

    const actions = h('div', { class: 'result-actions' }, btnCopySnippet, btnOpenPdf);
    const footer = h('div', { class: 'result-footer' }, fileInfo, actions);

    return h('article', { class: 'result-card', style: { '--c': cor } }, header, snippetsBox, footer);
  }

  function renderizarVazio(termo) {
    const empty = h(
      'div',
      { class: 'search-empty-state' },
      h('svg', {
        class: 'empty-icon',
        viewBox: '0 0 24 24',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '1.6',
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        html: '<circle cx="12" cy="12" r="10"/><line x1="8" y1="15" x2="16" y2="15"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>',
      }),
      h('h3', { class: 'empty-title' }, `Nenhum resultado para "${termo}"`),
      h(
        'p',
        { class: 'empty-desc' },
        'Verifique se a palavra foi digitada corretamente ou tente ampliar os filtros de vestibulares e anos. Lembre-se de ativar a "Busca flexível de acentos" caso o termo contenha acentuação.'
      )
    );
    elements.resultsContainer.appendChild(empty);
  }

  function renderizarEstadoErro(msg) {
    const errBox = h(
      'div',
      { class: 'search-empty-state', style: { borderColor: 'var(--danger-line)' } },
      h('h3', { class: 'empty-title', style: { color: 'var(--danger)' } }, 'Ocorreu um erro na busca'),
      h('p', { class: 'empty-desc' }, msg || 'Não foi possível completar a consulta ao servidor local.')
    );
    elements.resultsContainer.appendChild(errBox);
  }

  // ===========================================================================
  // 5. Eventos e Atalhos
  // ===========================================================================
  function registrarEventos() {
    // Submissão do formulário
    elements.form.addEventListener('submit', (e) => {
      e.preventDefault();
      executarBusca();
    });

    // Botões de seleção de vestibulares
    elements.btnVestAll.addEventListener('click', () => {
      state.selecionadosVest = new Set(state.vestibularesDisponiveis.map((v) => v.nome));
      renderizarChipsVestibulares();
    });

    elements.btnVestNone.addEventListener('click', () => {
      state.selecionadosVest.clear();
      renderizarChipsVestibulares();
    });

    // Botões de seleção de anos
    elements.btnYearsAll.addEventListener('click', () => {
      state.selecionadosAnos = new Set(state.anosDisponiveis);
      atualizarPresetsAnos();
      renderizarGridAnos();
    });

    elements.btnYearsNone.addEventListener('click', () => {
      state.selecionadosAnos.clear();
      atualizarPresetsAnos();
      renderizarGridAnos();
    });

    // Presets de anos
    elements.yearsPresets.addEventListener('click', (e) => {
      const btn = e.target.closest('.preset-chip');
      if (!btn) return;
      aplicarPresetAnos(btn.dataset.preset);
    });

    // Cliques em chips de sugestão rápida
    document.addEventListener('click', (e) => {
      const chip = e.target.closest('.sample-chip');
      if (chip) {
        elements.input.value = chip.textContent.trim();
        executarBusca();
        window.scrollTo({ top: elements.form.offsetTop - 30, behavior: 'smooth' });
      }
    });

    // Atalhos de teclado globais
    window.addEventListener('keydown', (e) => {
      if (e.target.matches('input, textarea, select')) return;
      if (e.key === '/') {
        e.preventDefault();
        elements.input.focus();
        elements.input.select();
      }
    });

    elements.input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        elements.input.blur();
      }
    });
  }

  // Inicialização
  registrarEventos();
  carregarOpcoes();
})();
