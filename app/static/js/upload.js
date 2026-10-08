/**
 * ===============================================================================
 * ARQUIVO: app/static/js/upload.js
 * CAMADA: Frontend / Modal de Upload e Nomenclatura Padronizada
 * PAPEL NO SISTEMA:
 *   - Controla o modal de adição de novas provas (<dialog id="upload-dialog">):
 *       1. Abre e fecha o diálogo com acessibilidade e atalhos de teclado (tecla N e Esc).
 *       2. Popula o <select> com os vestibulares do acervo e pré-seleciona o atual.
 *       3. Adapta os campos dinamicamente:
 *          - AFA: Oculta a escolha de fase (etapa única).
 *          - USP: Exibe seletor de prefixo (FEVEST padrão histórico vs FUVEST).
 *       4. Atualiza o painel de pré-visualização (Live Preview) em tempo real,
 *          mostrando a pasta e os nomes com os quais os arquivos serão salvos.
 *       5. Zonas de Drag & Drop para PDF da Prova e do Gabarito.
 *       6. Converte os PDFs para Base64 e envia ao endpoint POST /api/upload.
 *       7. Ao concluir, atualiza automaticamente o catálogo no navegador sem recarregar.
 * ===============================================================================
 */

(function () {
  'use strict';

  const App = (window.App = window.App || {});
  const { formatBytes, toast } = App.ui;

  const dialog = document.getElementById('upload-dialog');
  const form = document.getElementById('upload-form');
  const selVest = document.getElementById('up-vestibular');
  const inpAno = document.getElementById('up-ano');
  const faseField = document.getElementById('up-fase-field');
  const afaHint = document.getElementById('up-afa-hint');
  const uspField = document.getElementById('up-usp-field');
  const selPrefixo = document.getElementById('up-prefixo');
  const pvPasta = document.getElementById('pv-pasta');
  const pvProva = document.getElementById('pv-prova');
  const pvGabarito = document.getElementById('pv-gabarito');
  const pvWarn = document.getElementById('pv-warn');
  const btnSubmit = document.getElementById('up-submit');
  const btnAdd = document.getElementById('btn-add');

  const arquivos = {
    prova: null,
    gabarito: null,
  };

  // ---------------------------------------------------------------------------
  // Dropzones
  // ---------------------------------------------------------------------------
  function setupDropzones() {
    const dropzones = document.querySelectorAll('.dropzone[data-kind]');
    dropzones.forEach((dz) => {
      const kind = dz.dataset.kind;
      const input = dz.querySelector('input[type="file"]');
      const nameEl = dz.querySelector('.dz-name');
      const sizeEl = dz.querySelector('.dz-size');
      const btnClear = dz.querySelector('.dz-clear');

      function definirArquivo(file) {
        if (!file) {
          arquivos[kind] = null;
          dz.classList.remove('has-file');
          if (input) input.value = '';
          return;
        }

        if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
          toast('Selecione apenas arquivos no formato PDF', { type: 'error' });
          return;
        }

        arquivos[kind] = file;
        nameEl.textContent = file.name;
        sizeEl.textContent = formatBytes(file.size);
        dz.classList.add('has-file');
      }

      ['dragenter', 'dragover'].forEach((evt) => {
        dz.addEventListener(evt, (e) => {
          e.preventDefault();
          dz.classList.add('is-dragover');
        });
      });

      ['dragleave', 'drop'].forEach((evt) => {
        dz.addEventListener(evt, (e) => {
          e.preventDefault();
          dz.classList.remove('is-dragover');
        });
      });

      dz.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) definirArquivo(files[0]);
      });

      if (input) {
        input.addEventListener('change', () => {
          if (input.files && input.files.length > 0) definirArquivo(input.files[0]);
        });
      }

      if (btnClear) {
        btnClear.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          definirArquivo(null);
        });
      }
    });
  }

  function limparArquivos() {
    arquivos.prova = null;
    arquivos.gabarito = null;
    document.querySelectorAll('.dropzone[data-kind]').forEach((dz) => {
      dz.classList.remove('has-file');
      const input = dz.querySelector('input[type="file"]');
      if (input) input.value = '';
    });
  }

  // ---------------------------------------------------------------------------
  // Preview da Nomenclatura
  // ---------------------------------------------------------------------------
  function atualizarPreview() {
    if (!selVest || !inpAno) return;

    const vest = selVest.value || 'VESTIBULAR';
    const ano = inpAno.value.trim() || 'ANO';
    const faseRadio = document.querySelector('input[name="fase"]:checked');
    const fase = faseRadio ? faseRadio.value : '1';
    const prefixoUsp = selPrefixo ? selPrefixo.value : 'FEVEST';

    // Regra AFA
    if (vest === 'AFA') {
      if (faseField) faseField.querySelector('.segmented')?.classList.add('is-disabled');
      if (afaHint) afaHint.hidden = false;
      if (uspField) uspField.hidden = true;

      pvPasta.textContent = 'AFA/';
      pvProva.textContent = `AFA_${ano}.pdf`;
      pvGabarito.textContent = `AFA_${ano}_gab.pdf`;
      pvWarn.hidden = true;
      return;
    }

    if (faseField) faseField.querySelector('.segmented')?.classList.remove('is-disabled');
    if (afaHint) afaHint.hidden = true;

    // Regra USP
    if (vest === 'USP') {
      if (uspField) uspField.hidden = fase !== '1';
      const prefix = fase === '1' ? prefixoUsp : 'FUVEST';
      const folder = fase === '1' ? 'USP/1ª Fase/' : 'USP/2ª Fase/';

      pvPasta.textContent = folder;
      pvProva.textContent = `${prefix}_${ano}_${fase}Fase.pdf`;
      pvGabarito.textContent = `${prefix}_${ano}_${fase}Fase_gab.pdf`;
      pvWarn.hidden = true;
      return;
    }

    if (uspField) uspField.hidden = true;

    // Demais Vestibulares (IME, ITA, UNESP, UNICAMP)
    const folder = `${vest}/${fase}ª Fase/`;
    pvPasta.textContent = folder;
    pvProva.textContent = `${vest}_${ano}_${fase}Fase.pdf`;
    pvGabarito.textContent = `${vest}_${ano}_${fase}Fase_gab.pdf`;
    pvWarn.hidden = true;
  }

  // ---------------------------------------------------------------------------
  // Leitura Base64
  // ---------------------------------------------------------------------------
  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
    });
  }

  // ---------------------------------------------------------------------------
  // Abertura e Fechamento do Modal
  // ---------------------------------------------------------------------------
  function open(vestibularSugerido = null) {
    if (!dialog) return;

    if (vestibularSugerido && selVest) {
      selVest.value = vestibularSugerido;
    }

    if (inpAno && !inpAno.value) {
      inpAno.value = String(new Date().getFullYear());
    }

    atualizarPreview();
    dialog.showModal();
  }

  function close() {
    if (!dialog) return;
    dialog.close();
    limparArquivos();
  }

  // ---------------------------------------------------------------------------
  // Envio do Formulário
  // ---------------------------------------------------------------------------
  async function handleSubmit(e) {
    e.preventDefault();

    if (!arquivos.prova && !arquivos.gabarito) {
      toast('Selecione pelo menos um arquivo PDF (prova ou gabarito).', { type: 'error' });
      return;
    }

    const vest = selVest.value;
    const ano = inpAno.value.trim();
    const faseRadio = document.querySelector('input[name="fase"]:checked');
    const fase = faseRadio ? faseRadio.value : '1';
    const prefixoUsp = selPrefixo ? selPrefixo.value : 'FEVEST';

    if (!ano || ano.length !== 4) {
      toast('Informe um ano válido com 4 dígitos.', { type: 'error' });
      inpAno.focus();
      return;
    }

    btnSubmit.disabled = true;
    btnSubmit.setAttribute('aria-busy', 'true');

    try {
      const payload = {
        vestibular: vest,
        ano,
        fase,
        prefixo_usp: prefixoUsp,
      };

      if (arquivos.prova) {
        payload.prova = {
          filename: arquivos.prova.name,
          data: await fileToBase64(arquivos.prova),
        };
      }

      if (arquivos.gabarito) {
        payload.gabarito = {
          filename: arquivos.gabarito.name,
          data: await fileToBase64(arquivos.gabarito),
        };
      }

      const res = await App.api.upload(payload);

      toast('Prova adicionada com sucesso!', {
        detail: res.saved_files.join(' · '),
      });

      close();

      // Recarrega o catálogo exibindo o vestibular do upload
      if (App.library) {
        await App.library.reload(vest);
      }
    } catch (err) {
      toast('Falha ao salvar no acervo', { type: 'error', detail: err.message });
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.removeAttribute('aria-busy');
    }
  }

  // ---------------------------------------------------------------------------
  // Inicialização
  // ---------------------------------------------------------------------------
  App.upload = {
    init(catalogo) {
      if (!dialog) return;

      // Popula o select com as pastas disponíveis
      if (selVest && catalogo && catalogo.vestibulares) {
        selVest.innerHTML = '';
        catalogo.vestibulares.forEach((v) => {
          const opt = document.createElement('option');
          opt.value = v.nome;
          opt.textContent = v.nome;
          selVest.appendChild(opt);
        });
      }

      setupDropzones();

      // Listeners de mudança para atualizar o preview
      selVest?.addEventListener('change', atualizarPreview);
      inpAno?.addEventListener('input', atualizarPreview);
      document.querySelectorAll('input[name="fase"]').forEach((r) => {
        r.addEventListener('change', atualizarPreview);
      });
      selPrefixo?.addEventListener('change', atualizarPreview);

      // Botão fechar (data-close)
      dialog.querySelectorAll('[data-close]').forEach((btn) => {
        btn.addEventListener('click', close);
      });

      // Fechar clicando no backdrop
      dialog.addEventListener('click', (e) => {
        if (e.target === dialog) close();
      });

      // Botão Adicionar Prova na toolbar
      if (btnAdd) {
        btnAdd.addEventListener('click', () => open());
      }

      // Submit
      if (form) {
        form.addEventListener('submit', handleSubmit);
      }

      atualizarPreview();
    },

    open,
    close,
  };
})();
