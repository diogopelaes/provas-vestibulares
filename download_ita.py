"""Script para download e organização das provas do vestibular do ITA.

- Vestibulares a partir de 2019:
    - 1ª Fase (Prova): ITA_{ano}_1Fase.pdf em ITA/1ª Fase/
    - 1ª Fase (Gabarito): ITA_{ano}_1Fase_gab.pdf em ITA/1ª Fase/
    - 2ª Fase (Matemática): ITA_{ano}_2Fase.pdf em ITA/2ª Fase/
- Vestibulares de 2008 a 2018 (fase única):
    - Matemática: ITA_{ano}.pdf diretamente em ITA/
    - Gabarito: ITA_{ano}_gab.pdf diretamente em ITA/
"""

from dataclasses import dataclass
import html
import logging
from pathlib import Path
import re
from typing import Final
import urllib.error
import urllib.parse
import urllib.request

PAGE_URL: Final[str] = "https://www.vestibular.ita.br/provas.htm"
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
BUFFER_SIZE: Final[int] = 64 * 1024


@dataclass(frozen=True, slots=True)
class ExamItem:
    """Representa uma prova a ser baixada."""

    year: str
    phase_name: str
    target_dir: Path
    url: str
    filename: str

    @property
    def destination_path(self) -> Path:
        """Retorna o caminho completo de destino do arquivo."""
        return self.target_dir / self.filename


def configure_logging() -> None:
    """Configura o sistema de logging da aplicação."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def fetch_page_html(url: str) -> str:
    """Obtém o conteúdo HTML da página do vestibular do ITA.

    Args:
        url: URL da página a ser requisitada.

    Returns:
        O texto HTML decodificado.
    """
    logging.info("Requisitando página oficial: %s", url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=30) as response:
        content_bytes = response.read()
        # O site do ITA declara charset iso-8859-1 no cabeçalho HTML
        return content_bytes.decode("iso-8859-1", errors="replace")


def parse_exam_items(html_content: str, base_url: str, ita_base_dir: Path) -> list[ExamItem]:
    """Analisa o HTML e extrai os itens de 1ª Fase e Matemática de 2ª Fase.

    Args:
        html_content: Conteúdo HTML da página de provas.
        base_url: URL base para resolução de links relativos.
        ita_base_dir: Diretório base do ITA (onde ficam 1ª Fase e 2ª Fase).

    Returns:
        Lista de ExamItem contendo os arquivos a serem baixados.
    """
    items: list[ExamItem] = []
    dir_phase_1 = ita_base_dir / "1ª Fase"
    dir_phase_2 = ita_base_dir / "2ª Fase"

    table_rows = re.findall(r"<tr[^>]*>.*?</tr>", html_content, re.DOTALL | re.IGNORECASE)

    for row in table_rows:
        year_match = re.search(r">\s*(19\d\d|20\d\d)\s*<", row)
        if not year_match:
            continue

        year = year_match.group(1)

        # Extrai todas as tags <a> da linha
        links = re.findall(
            r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            row,
            re.DOTALL | re.IGNORECASE,
        )

        for href, text_content in links:
            clean_text = html.unescape(re.sub(r"<[^<]+?>", "", text_content)).strip().lower()
            normalized_href = href.lower()
            absolute_url = urllib.parse.urljoin(base_url, href)

            # Vestibulares a partir de 2019 (modelo em 1ª e 2ª fases)
            if int(year) >= 2019:
                # 1ª Fase: link com 'fase1' ou texto 'prova' (excluindo gabarito)
                is_phase_1 = "fase1" in normalized_href or clean_text == "prova"
                if is_phase_1 and "gabarito" not in normalized_href:
                    items.append(
                        ExamItem(
                            year=year,
                            phase_name="1ª Fase",
                            target_dir=dir_phase_1,
                            url=absolute_url,
                            filename=f"ITA_{year}_1Fase.pdf",
                        )
                    )

                # 1ª Fase (Gabarito): gabarito oficial da 1ª fase com sufixo _gab
                is_phase_1_gab = "gabarito" in normalized_href and "2f" not in normalized_href
                if is_phase_1_gab:
                    items.append(
                        ExamItem(
                            year=year,
                            phase_name="1ª Fase (Gabarito)",
                            target_dir=dir_phase_1,
                            url=absolute_url,
                            filename=f"ITA_{year}_1Fase_gab.pdf",
                        )
                    )

                # 2ª Fase de Matemática: prova discursiva de matemática na 2ª fase
                is_math_phase_2 = "matematica" in normalized_href and "2f" in normalized_href
                if is_math_phase_2:
                    items.append(
                        ExamItem(
                            year=year,
                            phase_name="2ª Fase",
                            target_dir=dir_phase_2,
                            url=absolute_url,
                            filename=f"ITA_{year}_2Fase.pdf",
                        )
                    )

            # Vestibulares de 2008 a 2018 (fase única: direto em ITA/)
            elif 2008 <= int(year) <= 2018:
                if "matematica" in normalized_href:
                    items.append(
                        ExamItem(
                            year=year,
                            phase_name="Fase Única (Matemática)",
                            target_dir=ita_base_dir,
                            url=absolute_url,
                            filename=f"ITA_{year}.pdf",
                        )
                    )
                elif "gabarito" in normalized_href:
                    items.append(
                        ExamItem(
                            year=year,
                            phase_name="Fase Única (Gabarito)",
                            target_dir=ita_base_dir,
                            url=absolute_url,
                            filename=f"ITA_{year}_gab.pdf",
                        )
                    )

    return items


def download_exam_file(item: ExamItem) -> bool:
    """Faz o download de um PDF de prova e salva no caminho de destino.

    Args:
        item: Objeto ExamItem com detalhes da prova e caminhos.

    Returns:
        True se o download ou arquivo já existente foi confirmado, False em erro.
    """
    dest_path = item.destination_path
    item.target_dir.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and dest_path.stat().st_size > 0:
        logging.info("Arquivo já existente ignorado: %s", dest_path)
        return True

    temp_path = dest_path.with_suffix(".tmp")
    logging.info("Baixando %s (%s) -> %s", item.year, item.phase_name, dest_path.name)

    try:
        request = urllib.request.Request(item.url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response, temp_path.open("wb") as out_file:
            while chunk := response.read(BUFFER_SIZE):
                out_file.write(chunk)

        temp_path.replace(dest_path)
        logging.info("Concluído: %s (tamanho: %d bytes)", dest_path.name, dest_path.stat().st_size)
        return True
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        logging.error("Falha ao baixar %s (%s): %s", item.url, item.filename, error)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        return False


def run() -> None:
    """Função principal de orquestração do download de provas do ITA."""
    configure_logging()
    logging.info("Iniciando processo de download das provas do ITA...")

    project_root = Path(__file__).resolve().parent
    ita_dir = project_root / "ITA"

    try:
        html_content = fetch_page_html(PAGE_URL)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        logging.critical("Não foi possível acessar a página %s: %s", PAGE_URL, error)
        return

    exam_items = parse_exam_items(html_content, PAGE_URL, ita_dir)
    logging.info("Total de provas identificadas: %d", len(exam_items))

    success_count = 0
    failure_count = 0

    for item in exam_items:
        if download_exam_file(item):
            success_count += 1
        else:
            failure_count += 1

    logging.info(
        "Processamento concluído. Sucesso: %d, Falhas: %d, Total: %d",
        success_count,
        failure_count,
        len(exam_items),
    )


if __name__ == "__main__":
    run()
