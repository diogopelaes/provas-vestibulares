/**
 * ===============================================================================
 * ARQUIVO: app/static/js/library.js
 * CAMADA: Frontend / Visualização do Acervo (Biblioteca de Provas)
 * PAPEL NO SISTEMA:
 *   - Gerencia a renderização do catálogo completo de vestibulares:
 *       1. Sidebar: Lista todos os vestibulares com contador de edições e
 *          estatísticas gerais (total de provas, gabaritos e período de anos).
 *       2. Navegação por Hash: Suporta rotas como '#/' (todas) ou '#/UNICAMP'
 *          para filtrar diretamente o vestibular selecionado.
 *       3. Barra de Filtros: Filtro rápido por fase (Todas, 1ª Fase, 2ª Fase)
 *          e switch para exibir somente exames com gabarito disponível.
 *       4. Busca Instantânea: Filtra por ano, nome do vestibular, fase ou documento.
 *       5. Cards de Edição (Ano):
 *          - O ano é um link clicável que abre a prova em nova aba (_blank).
 *          - Botões elegantes para Prova, Gabarito e Resolução.
 *          - Indicação visual discreta para itens ausentes.
 *          - Ícone de link externo e tamanho formatado do arquivo.
 * ===============================================================================
 */

(function () {
  'use strict';

  const App = (window.App = window.App || {});
  const { h, iconNode, colorFor, normalize, formatBytes, plural } = App.ui;

  let catalogo = null;
  let vestibularAtivo = null; // null = todos
  let faseAtiva = 'todas';
  let apenasComGabarito = false;
  let termoBusca = '';

  const elSideList = document.getElementById('side-list');
  const elSideStats = document.getElementById('side-stats');
  const elContent = document.getElementById('content');
  const elFilters = document.getElementById('filters');
  const elSearch = document.getElementById('search-input');
  const elPageTitle = document.getElementById('page-title');
  const elPageSub = document.getElementById('page-sub');
  const elPageEyebrow = document.getElementById('page-eyebrow');

  // ---------------------------------------------------------------------------
  // Sidebar e Estatísticas
  // ---------------------------------------------------------------------------
  function renderSidebar() {
    if (!catalogo || !elSideList) return;

    elSideList.innerHTML = '';

    // Item: Todas as Provas
    const totalGeral = catalogo.totais.edicoes;
    const itemTodos = h(
      'button',
      {
        type: 'button',
        class: `side-item ${vestibularAtivo === null ? 'is-active' : ''}`,
        onclick: () => setVestibular(null),
      },
      h('span', { class: 'side-icon' }, iconNode('book')),
      h('span', { class: 'side-name' }, 'Todas as provas'),
      h('span', { class: 'side-count' }, totalGeral)
    );
    elSideList.appendChild(itemTodos);

    // Itens: Cada Vestibular
    catalogo.vestibulares.forEach((v) => {
      const cor = colorFor(v.nome);
      const isActive = vestibularAtivo === v.nome;
      const btn = h(
        'button',
        {
          type: 'button',
          class: `side-item ${isActive ? 'is-active' : ''}`,
          style: { '--c': cor },
          onclick: () => setVestibular(v.nome),
        },
        h('span', { class: 'side-dot' }),
        h('span', { class: 'side-name' }, v.nome),
        h('span', { class: 'side-count' }, v.total_edicoes)
      );
      elSideList.appendChild(btn);
    });

    // Bloco de estatísticas no rodapé da sidebar
    if (elSideStats) {
      const { provas, gabaritos, ano_min, ano_max } = catalogo.totais;
      const taxa = provas > 0 ? Math.round((gabaritos / provas) * 100) : 0;
      elSideStats.innerHTML = '';
      elSideStats.appendChild(
        h(
          'div',
          { class: 'stat' },
          h('span', { class: 'stat-value' }, provas),
          h('span', { class: 'stat-label' }, 'Provas em PDF')
        )
      );
      elSideStats.appendChild(
        h(
          'div',
          { class: 'stat' },
          h('span', { class: 'stat-value' }, gabaritos),
          h('span', { class: 'stat-label' }, 'Gabaritos')
        )
      );
      if (ano_min && ano_max) {
        elSideStats.appendChild(
          h(
            'div',
            { class: 'stat stat--wide' },
            h('span', { class: 'stat-value' }, `${ano_min} — ${ano_max}`),
            h('span', { class: 'stat-label' }, `Período arquivado · ${taxa}% com gabarito`),
            h('div', { class: 'stat-bar' }, h('span', { style: { width: `${taxa}%` } }))
          )
        );
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Filtros (Chips de Fase + Switch de Gabarito)
  // ---------------------------------------------------------------------------
  function renderFilters(fasesDisponiveis) {
    if (!elFilters) return;
    elFilters.innerHTML = '';

    const chipsWrapper = h('div', { style: { display: 'flex', gap: '0.4rem', flexWrap: 'wrap' } });

    // Opção "Todas"
    const chipTodas = h(
      'button',
      {
        type: 'button',
        class: `chip ${faseAtiva === 'todas' ? 'is-active' : ''}`,
        onclick: () => {
          faseAtiva = 'todas';
          renderContent();
        },
      },
      'Todas as fases'
    );
    chipsWrapper.appendChild(chipTodas);

    // Chips específicos das fases presentes
    fasesDisponiveis.forEach((faseKey) => {
      let label = faseKey;
      if (faseKey === '1') label = '1ª Fase';
      else if (faseKey === '2') label = '2ª Fase';
      else if (faseKey === 'unica') label = 'Fase Única';

      const chip = h(
        'button',
        {
          type: 'button',
          class: `chip ${faseAtiva === faseKey ? 'is-active' : ''}`,
          onclick: () => {
            faseAtiva = faseKey;
            renderContent();
          },
        },
        label
      );
      chipsWrapper.appendChild(chip);
    });

    elFilters.appendChild(chipsWrapper);

    // Switch para filtrar apenas itens com gabarito
    const switchLabel = h(
      'label',
      { class: 'filter-switch' },
      h('input', {
        type: 'checkbox',
        role: 'switch',
        checked: apenasComGabarito,
        onchange: (e) => {
          apenasComGabarito = e.target.checked;
          renderContent();
        },
      }),
      'Somente com gabarito'
    );
    elFilters.appendChild(switchLabel);
  }

  // ---------------------------------------------------------------------------
  // Card de Edição (Ano + Documentos PDF)
  // ---------------------------------------------------------------------------
  function createExamCard(edicao, vestNome, index) {
    const cor = colorFor(vestNome);
    const prova = edicao.arquivos.prova;
    const gabarito = edicao.arquivos.gabarito;
    const resolucao = edicao.arquivos.resolucao;

    const topEl = h(
      'div',
      { class: 'exam-top' },
      h(
        'div',
        null,
        prova
          ? h(
              'a',
              {
                href: prova.url,
                target: '_blank',
                rel: 'noopener noreferrer',
                class: `exam-year stretched ${edicao.titulo.length > 5 ? 'exam-year--text' : ''}`,
                title: `Abrir prova em PDF (${prova.nome})`,
              },
              edicao.titulo
            )
          : h(
              'span',
              { class: `exam-year ${edicao.titulo.length > 5 ? 'exam-year--text' : ''}` },
              edicao.titulo
            ),
        edicao.semestre
          ? h('div', { class: 'exam-sub' }, `${edicao.semestre}º Semestre`)
          : null
      ),
      h('span', { class: 'exam-open' }, iconNode('external'))
    );

    const actionsEl = h('div', { class: 'exam-actions' });

    // Link Prova
    if (prova) {
      actionsEl.appendChild(
        h(
          'a',
          {
            href: prova.url,
            target: '_blank',
            rel: 'noopener noreferrer',
            class: 'doc',
            title: `${prova.nome} (${formatBytes(prova.tamanho)})`,
          },
          iconNode('file'),
          'Prova'
        )
      );
    } else {
      actionsEl.appendChild(h('span', { class: 'doc is-missing' }, 'Sem prova'));
    }

    // Link Gabarito
    if (gabarito) {
      actionsEl.appendChild(
        h(
          'a',
          {
            href: gabarito.url,
            target: '_blank',
            rel: 'noopener noreferrer',
            class: 'doc',
            title: `${gabarito.nome} (${formatBytes(gabarito.tamanho)})`,
          },
          iconNode('checkSquare'),
          'Gabarito'
        )
      );
    } else {
      actionsEl.appendChild(h('span', { class: 'doc is-missing' }, 'Sem gabarito'));
    }

    // Link Resolução (quando existir)
    if (resolucao) {
      actionsEl.appendChild(
        h(
          'a',
          {
            href: resolucao.url,
            target: '_blank',
            rel: 'noopener noreferrer',
            class: 'doc',
            title: `${resolucao.nome} (${formatBytes(resolucao.tamanho)})`,
          },
          iconNode('paperclip'),
          'Resolução'
        )
      );
    }

    return h(
      'article',
      {
        class: 'exam-card',
        style: {
          '--c': cor,
          '--i': index,
        },
      },
      topEl,
      actionsEl
    );
  }

  // ---------------------------------------------------------------------------
  // Renderização Principal do Acervo
  // ---------------------------------------------------------------------------
  function renderContent() {
    if (!catalogo || !elContent) return;

    const termNorm = normalize(termoBusca);

    // Filtrar vestibulares
    const vestibularesFiltrados = catalogo.vestibulares.filter((v) => {
      if (vestibularAtivo && v.nome !== vestibularAtivo) return false;
      return true;
    });

    // Descobrir todas as fases presentes no contexto
    const fasesSet = new Set();
    vestibularesFiltrados.forEach((v) => {
      v.grupos.forEach((g) => {
        if (g.fase) fasesSet.add(g.fase);
      });
    });
    renderFilters(Array.from(fasesSet));

    // Atualizar títulos do cabeçalho
    if (vestibularAtivo) {
      const atual = catalogo.vestibulares.find((v) => v.nome === vestibularAtivo);
      elPageEyebrow.textContent = 'Vestibular Selecionado';
      elPageTitle.textContent = vestibularAtivo;
      const count = atual ? atual.total_edicoes : 0;
      elPageSub.textContent = `${plural(count, 'edição arquivada', 'edições arquivadas')} (${atual.ano_min || '—'} a ${atual.ano_max || '—'})`;
    } else {
      elPageEyebrow.textContent = 'Acervo Completo';
      elPageTitle.textContent = 'Todas as Provas';
      const tot = catalogo.totais;
      elPageSub.textContent = `${tot.edicoes} edições em ${tot.vestibulares} instituições (${tot.ano_min || '—'} a ${tot.ano_max || '—'})`;
    }

    elContent.innerHTML = '';
    let totalExibidos = 0;

    vestibularesFiltrados.forEach((v) => {
      const cor = colorFor(v.nome);
      const gruposComEdicoes = [];

      v.grupos.forEach((grupo) => {
        // Filtro por fase
        if (faseAtiva !== 'todas' && grupo.fase !== faseAtiva) return;

        // Filtro por termo de busca e gabarito
        const edicoesFiltradas = grupo.edicoes.filter((ed) => {
          if (apenasComGabarito && !ed.arquivos.gabarito) return false;

          if (termNorm) {
            const matchesVest = normalize(v.nome).includes(termNorm);
            const matchesAno = String(ed.ano).includes(termNorm);
            const matchesTitulo = normalize(ed.titulo).includes(termNorm);
            const matchesGrupo = normalize(grupo.titulo).includes(termNorm);
            const matchesDocs = Object.values(ed.arquivos).some((doc) =>
              normalize(doc.nome).includes(termNorm)
            );
            if (!matchesVest && !matchesAno && !matchesTitulo && !matchesGrupo && !matchesDocs) {
              return false;
            }
          }
          return true;
        });

        if (edicoesFiltradas.length > 0) {
          gruposComEdicoes.push({ grupo, edicoes: edicoesFiltradas });
        }
      });

      if (gruposComEdicoes.length === 0) return;

      const vestBlock = h('section', { class: 'vest-block', style: { '--c': cor } });

      // Cabeçalho do vestibular (mostrado se estamos na visão de todos)
      if (!vestibularAtivo) {
        const vestHead = h(
          'header',
          { class: 'vest-head' },
          h('button', {
            type: 'button',
            class: 'vest-badge',
            title: `Filtrar apenas ${v.nome}`,
            onclick: () => setVestibular(v.nome),
          }, v.nome.slice(0, 4)),
          h(
            'div',
            null,
            h('h2', { class: 'vest-name' }, v.nome),
            h('p', { class: 'vest-meta' }, `${plural(v.total_edicoes, 'edição arquivada', 'edições arquivadas')} (${v.ano_min || '—'} a ${v.ano_max || '—'})`)
          ),
          h('button', {
            type: 'button',
            class: 'vest-open',
            onclick: () => setVestibular(v.nome),
          }, 'Ver apenas este vestibular →')
        );
        vestBlock.appendChild(vestHead);
      }

      // Grupos por fase / ano
      gruposComEdicoes.forEach(({ grupo, edicoes }) => {
        const groupEl = h('div', { class: 'group' });
        groupEl.appendChild(
          h(
            'h3',
            { class: 'group-head' },
            grupo.titulo,
            h('span', { class: 'group-count' }, `(${edicoes.length})`)
          )
        );

        const gridEl = h('div', { class: 'exam-grid' });
        edicoes.forEach((ed, idx) => {
          totalExibidos++;
          gridEl.appendChild(createExamCard(ed, v.nome, idx));
        });
        groupEl.appendChild(gridEl);
        vestBlock.appendChild(groupEl);
      });

      elContent.appendChild(vestBlock);
    });

    // Estado vazio caso a busca não retorne itens
    if (totalExibidos === 0) {
      elContent.appendChild(
        h(
          'div',
          { class: 'empty' },
          iconNode('inbox'),
          h('h3', null, 'Nenhuma prova encontrada'),
          h('p', null, termoBusca ? `Nenhum resultado corresponde a "${termoBusca}".` : 'Nenhum exame atende aos filtros atuais.'),
          termoBusca || faseAtiva !== 'todas' || apenasComGabarito
            ? h(
                'button',
                {
                  type: 'button',
                  class: 'btn btn-ghost',
                  onclick: () => {
                    termoBusca = '';
                    faseAtiva = 'todas';
                    apenasComGabarito = false;
                    if (elSearch) elSearch.value = '';
                    renderContent();
                  },
                },
                'Limpar filtros'
              )
            : null
        )
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Roteamento e Ações
  // ---------------------------------------------------------------------------
  function setVestibular(nome) {
    vestibularAtivo = nome;
    faseAtiva = 'todas';
    window.location.hash = nome ? `#/${encodeURIComponent(nome)}` : '#/';
    renderSidebar();
    renderContent();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function handleHash() {
    const hash = window.location.hash.replace(/^#\/?/, '').trim();
    if (!hash || !catalogo) {
      vestibularAtivo = null;
    } else {
      const decoded = decodeURIComponent(hash);
      const existe = catalogo.vestibulares.some((v) => v.nome === decoded);
      vestibularAtivo = existe ? decoded : null;
    }
    renderSidebar();
    renderContent();
  }

  // ---------------------------------------------------------------------------
  // Interface Pública
  // ---------------------------------------------------------------------------
  App.library = {
    init(dadosCatalogo) {
      catalogo = dadosCatalogo;

      if (elSearch) {
        elSearch.addEventListener(
          'input',
          App.ui.debounce((e) => {
            termoBusca = e.target.value;
            renderContent();
          }, 180)
        );
      }

      window.addEventListener('hashchange', handleHash);
      handleHash();
    },

    setVestibular,

    async reload(novoVestibular = null) {
      try {
        catalogo = await App.api.getCatalogo();
        if (novoVestibular) vestibularAtivo = novoVestibular;
        renderSidebar();
        renderContent();
      } catch (err) {
        App.ui.toast('Falha ao atualizar o acervo', { type: 'error', detail: err.message });
      }
    },
  };
})();
