/**
 * ===============================================================================
 * ARQUIVO: app/static/js/app.js
 * CAMADA: Comportamento do Cliente / Frontend (JavaScript)
 * PAPEL NO SISTEMA:
 *   - Gerencia a interação do usuário na página de upload:
 *       1. Requisição inicial para GET /api/vestibulares para popular o <select>.
 *       2. Atualização reativa em tempo real do box de preview de nomenclatura
 *          sempre que o vestibular, o ano, a fase ou o prefixo USP forem alterados.
 *       3. Tratamento de exceção de regras de negócio:
 *          - AFA: Vestibular de fase única na raiz do diretório.
 *          - USP: Opção de seleção de prefixo (FEVEST padrão histórico vs FUVEST).
 *       4. Gerenciamento de Drag & Drop para seleção de arquivos PDF (Prova e Gabarito).
 *       5. Codificação dos arquivos em Base64 para envio JSON seguro via POST /api/upload.
 *       6. Exibição de alertas dinâmicos de sucesso/erro e feedback ao usuário.
 * ===============================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  const selectVestibular = document.getElementById('select-vestibular');
  const inputAno = document.getElementById('input-ano');
  const radiosFase = document.querySelectorAll('input[name="fase"]');
  const afaNotice = document.getElementById('afa-notice');
  const uspOptions = document.getElementById('usp-options');
  const selectPrefixoUsp = document.getElementById('prefixo-usp');

  // Elementos do painel de preview
  const previewFolder = document.getElementById('preview-folder');
  const previewProva = document.getElementById('preview-prova');
  const previewGabarito = document.getElementById('preview-gabarito');

  // Elementos de Upload
  const fileInputProva = document.getElementById('file-prova');
  const fileInputGabarito = document.getElementById('file-gabarito');
  const dropZoneProva = document.getElementById('drop-zone-prova');
  const dropZoneGabarito = document.getElementById('drop-zone-gabarito');
  const detailsProva = document.getElementById('details-prova');
  const detailsGabarito = document.getElementById('details-gabarito');
  const nameProva = document.getElementById('name-prova');
  const nameGabarito = document.getElementById('name-gabarito');
  const sizeProva = document.getElementById('size-prova');
  const sizeGabarito = document.getElementById('size-gabarito');
  const btnClearProva = document.getElementById('btn-clear-prova');
  const btnClearGabarito = document.getElementById('btn-clear-gabarito');

  // Formulário e status
  const form = document.getElementById('upload-form');
  const btnSubmit = document.getElementById('btn-submit');
  const btnText = btnSubmit.querySelector('.btn-text');
  const btnSpinner = btnSubmit.querySelector('.btn-spinner');
  const feedbackAlert = document.getElementById('feedback-alert');

  let selectedFileProva = null;
  let selectedFileGabarito = null;

  // 1. Carrega as pastas de vestibulares disponíveis do backend
  async function carregarVestibulares() {
    try {
      const res = await fetch('/api/vestibulares');
      if (!res.ok) throw new Error('Falha ao obter lista');
      const data = await res.json();
      selectVestibular.innerHTML = '';

      data.vestibulares.forEach((vest) => {
        const opt = document.createElement('option');
        opt.value = vest;
        opt.textContent = vest;
        selectVestibular.appendChild(opt);
      });

      if (data.vestibulares.includes('UNICAMP')) {
        selectVestibular.value = 'UNICAMP';
      } else if (data.vestibulares.length > 0) {
        selectVestibular.value = data.vestibulares[0];
      }
    } catch (err) {
      console.warn('Usando lista de contingência:', err);
      const fallback = ['AFA', 'IME', 'ITA', 'UNESP', 'UNICAMP', 'USP'];
      selectVestibular.innerHTML = '';
      fallback.forEach((v) => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        selectVestibular.appendChild(opt);
      });
      selectVestibular.value = 'UNICAMP';
    }
    atualizarPreview();
  }

  // 2. Atualiza a nomenclatura em tempo real no card de preview
  function atualizarPreview() {
    const vestibular = selectVestibular.value || 'VESTIBULAR';
    const ano = inputAno.value.trim() || 'ANO';
    const faseInput = document.querySelector('input[name="fase"]:checked');
    const fase = faseInput ? faseInput.value : '1';
    const prefixoUsp = selectPrefixoUsp.value;

    // Regra específica para AFA (sem divisão de fases em subpastas)
    if (vestibular === 'AFA') {
      afaNotice.style.display = 'block';
      uspOptions.style.display = 'none';
      previewFolder.textContent = 'AFA/';
      previewProva.textContent = `AFA_${ano}.pdf`;
      previewGabarito.textContent = `AFA_${ano}_gab.pdf`;
      return;
    }

    afaNotice.style.display = 'none';

    // Regra específica para USP
    if (vestibular === 'USP') {
      uspOptions.style.display = fase === '1' ? 'block' : 'none';
      const folder = fase === '1' ? 'USP/1ª Fase/' : 'USP/2ª Fase/';
      const prefix = fase === '1' ? prefixoUsp : 'FUVEST';
      const suffix = fase === '1' ? '1Fase' : '2Fase';

      previewFolder.textContent = folder;
      previewProva.textContent = `${prefix}_${ano}_${suffix}.pdf`;
      previewGabarito.textContent = `${prefix}_${ano}_${suffix}_gab.pdf`;
      return;
    }

    uspOptions.style.display = 'none';
    const phaseFolder = fase === '1' ? '1ª Fase/' : '2ª Fase/';
    const suffix = fase === '1' ? '1Fase' : '2Fase';

    previewFolder.textContent = `${vestibular}/${phaseFolder}`;
    previewProva.textContent = `${vestibular}_${ano}_${suffix}.pdf`;
    previewGabarito.textContent = `${vestibular}_${ano}_${suffix}_gab.pdf`;
  }

  // Eventos para atualização em tempo real
  selectVestibular.addEventListener('change', atualizarPreview);
  inputAno.addEventListener('input', atualizarPreview);
  radiosFase.forEach((r) => r.addEventListener('change', atualizarPreview));
  selectPrefixoUsp.addEventListener('change', atualizarPreview);

  // 3. Utilitários para exibição de tamanho de arquivos
  function formatarBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // Configuração das áreas de Drag & Drop
  function configurarZona(dropZone, fileInput, detailsEl, nameEl, sizeEl, setFileCallback) {
    ['dragenter', 'dragover'].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
      });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0 && files[0].type === 'application/pdf') {
        aplicarArquivo(files[0]);
      } else {
        mostrarFeedback('Selecione apenas arquivos no formato PDF.', 'error');
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        aplicarArquivo(fileInput.files[0]);
      }
    });

    function aplicarArquivo(file) {
      setFileCallback(file);
      nameEl.textContent = file.name;
      sizeEl.textContent = `(${formatarBytes(file.size)})`;
      detailsEl.style.display = 'flex';
      dropZone.querySelector('.drop-zone-prompt').style.display = 'none';
    }
  }

  configurarZona(
    dropZoneProva,
    fileInputProva,
    detailsProva,
    nameProva,
    sizeProva,
    (f) => { selectedFileProva = f; }
  );

  configurarZona(
    dropZoneGabarito,
    fileInputGabarito,
    detailsGabarito,
    nameGabarito,
    sizeGabarito,
    (f) => { selectedFileGabarito = f; }
  );

  btnClearProva.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFileProva = null;
    fileInputProva.value = '';
    detailsProva.style.display = 'none';
    dropZoneProva.querySelector('.drop-zone-prompt').style.display = 'block';
  });

  btnClearGabarito.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFileGabarito = null;
    fileInputGabarito.value = '';
    detailsGabarito.style.display = 'none';
    dropZoneGabarito.querySelector('.drop-zone-prompt').style.display = 'block';
  });

  // 4. Conversão assíncrona de arquivo para Base64
  function lerArquivoBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
    });
  }

  // 5. Exibição de alertas
  function mostrarFeedback(mensagem, tipo = 'success', lista = []) {
    feedbackAlert.className = `feedback-alert ${tipo}`;
    let html = `<strong>${tipo === 'success' ? '✓ Sucesso!' : '⚠️ Atenção:'}</strong> ${mensagem}`;
    if (lista && lista.length > 0) {
      html += '<ul>' + lista.map((item) => `<li><code>${item}</code></li>`).join('') + '</ul>';
    }
    feedbackAlert.innerHTML = html;
    feedbackAlert.style.display = 'block';
    feedbackAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // 6. Envio do formulário
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!selectedFileProva && !selectedFileGabarito) {
      mostrarFeedback('Selecione ao menos um arquivo (PDF da prova ou do gabarito) para salvar.', 'error');
      return;
    }

    const vestibular = selectVestibular.value;
    const ano = inputAno.value.trim();
    const faseInput = document.querySelector('input[name="fase"]:checked');
    const fase = faseInput ? faseInput.value : '1';
    const prefixoUsp = selectPrefixoUsp.value;

    if (!ano) {
      mostrarFeedback('Informe o ano do vestibular.', 'error');
      return;
    }

    btnSubmit.disabled = true;
    btnText.textContent = 'Salvando arquivos...';
    btnSpinner.style.display = 'inline-block';
    feedbackAlert.style.display = 'none';

    try {
      const payload = {
        vestibular,
        ano,
        fase,
        prefixo_usp: prefixoUsp,
      };

      if (selectedFileProva) {
        payload.prova = {
          filename: selectedFileProva.name,
          data: await lerArquivoBase64(selectedFileProva),
        };
      }

      if (selectedFileGabarito) {
        payload.gabarito = {
          filename: selectedFileGabarito.name,
          data: await lerArquivoBase64(selectedFileGabarito),
        };
      }

      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Erro desconhecido ao salvar.');
      }

      mostrarFeedback(result.message, 'success', result.saved_files);

      // Limpar uploads após sucesso
      btnClearProva.click();
      btnClearGabarito.click();
    } catch (err) {
      mostrarFeedback(err.message, 'error');
    } finally {
      btnSubmit.disabled = false;
      btnText.textContent = 'Salvar Arquivos no Repositório';
      btnSpinner.style.display = 'none';
    }
  });

  // Inicialização
  carregarVestibulares();
});
