"""
===============================================================================
ARQUIVO: app/busca.py
CAMADA: Backend / Motor de Busca Avançada no Conteúdo dos PDFs
PAPEL NO SISTEMA:
  - Mecanismo de busca textual avançada em documentos PDF de vestibulares.
  - Otimizado para a língua portuguesa (sensibilidade configurável a acentuação
    e maiúsculas/minúsculas; equivalência fonética/ortográfica ex: 'quimica' <-> 'química').
  - Extrai texto por página e indexa em banco SQLite local (app/.search_cache.db)
    para buscas ultrarrápidas em milissegundos.
  - Retorna links diretos para cada prova posicionando o visualizador PDF
    na página exata onde o termo foi encontrado (âncora #page=N).
  - Inclui trecho contextual (snippet) com marcação do termo (<mark>).
  - Compatível com PyMuPDF (fitz) para máxima performance, com fallback para PyPDF2.
===============================================================================
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("BuscaVestibulares")

# Detecção de bibliotecas de leitura de PDF
PDF_ENGINE = None
try:
    import fitz  # PyMuPDF
    PDF_ENGINE = "fitz"
except ImportError:
    try:
        import PyPDF2
        PDF_ENGINE = "pypdf2"
    except ImportError:
        try:
            import pypdf
            PDF_ENGINE = "pypdf"
        except ImportError:
            PDF_ENGINE = None

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DB_PATH = APP_DIR / ".search_cache.db"

IGNORED_DIRS = {".git", ".vscode", ".venv", "__pycache__", "app", "build", "dist"}

FILE_PATTERN = re.compile(
    r"^(?P<prefixo>[A-Za-z]+)_(?P<ano>\d{4})"
    r"(?:_(?P<semestre>\d))?"
    r"(?:_(?P<fase>\d)Fase)?"
    r"(?:_(?P<tipo>gab|resol))?$",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")
DOC_TYPES = {"": "prova", "gab": "gabarito", "resol": "resolucao"}

# Mapeamento para construção de regex insensível a acentuação do português
PORTUGUESE_CHAR_MAP = {
    "a": "[aáàãâäAÁÀÃÂÄ]",
    "e": "[eéèêëEÉÈÊË]",
    "i": "[iíìîïIÍÌÎÏ]",
    "o": "[oóòõôöOÓÒÕÔÖ]",
    "u": "[uúùûüUÚÙÛÜ]",
    "c": "[cçCÇ]",
    "n": "[nñNÑ]",
}


# =============================================================================
# Normalização e Expressões Regulares em Português
# =============================================================================
def strip_accents(text: str) -> str:
    """Remove marcas diacríticas (acentos, til, cedilha) mantendo letras base."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_pt(text: str) -> str:
    """Normaliza texto em português para minúsculas e sem acentos."""
    return strip_accents(text).lower()


def build_pt_regex(
    query: str,
    modo: str = "exata",
    sensivel_acentos: bool = False,
    sensivel_maiusculas: bool = False,
) -> re.Pattern:
    """
    Constrói expressão regular para casamento de termos em português,
    com suporte a:
      - sensibilidade ou insensibilidade a acentuação (padrão: flexível)
      - sensibilidade ou insensibilidade a maiúsculas (padrão: insensível)
      - modos: 'exata' (frase completa), 'todas' (todas as palavras), 'qualquer' (qualquer palavra)
    """
    flags = 0 if sensivel_maiusculas else re.IGNORECASE

    def term_to_pattern(term: str) -> str:
        if sensivel_acentos:
            return re.escape(term)

        # Transforma o termo decomposto em classes com variações acentuadas
        base = strip_accents(term)
        parts = []
        for char in base:
            low = char.lower()
            if low in PORTUGUESE_CHAR_MAP:
                parts.append(PORTUGUESE_CHAR_MAP[low])
            elif char.isalnum():
                parts.append(re.escape(char))
            elif char.isspace():
                parts.append(r"\s+")
            else:
                parts.append(re.escape(char))
        return "".join(parts)

    query_clean = query.strip()
    if not query_clean:
        return re.compile(r"$^")  # Não casa nada

    if modo == "exata":
        pattern_str = term_to_pattern(query_clean)
        return re.compile(pattern_str, flags)

    # Divide por palavras mantendo pontuações razoáveis
    words = [w for w in re.split(r"\s+", query_clean) if w]
    if not words:
        return re.compile(r"$^")

    patterns = [term_to_pattern(w) for w in words]
    if modo == "qualquer":
        combined = "|".join(f"(?:{p})" for p in patterns)
        return re.compile(combined, flags)

    # Para 'todas', criamos um padrão que casa qualquer uma para extração de snippets,
    # mas a verificação se todas estão presentes é feita antes da extração.
    combined = "|".join(f"(?:{p})" for p in patterns)
    return re.compile(combined, flags)


def extract_snippets(
    text: str,
    pattern: re.Pattern,
    max_snippets: int = 3,
    context_chars: int = 90,
) -> tuple[list[str], int]:
    """
    Extrai trechos contextuais do texto onde o padrão foi encontrado,
    destacando o termo com tags <mark> e limpando quebras de linha excessivas.
    Retorna (lista_de_trechos, total_de_ocorrencias_no_texto).
    """
    if not text:
        return [], 0

    matches = list(pattern.finditer(text))
    total_matches = len(matches)
    if total_matches == 0:
        return [], 0

    snippets: list[str] = []
    # Agrupa matches muito próximos para não gerar snippets repetidos
    used_ranges: list[tuple[int, int]] = []

    for match in matches:
        if len(snippets) >= max_snippets:
            break

        start_m, end_m = match.start(), match.end()
        # Define janela de contexto
        c_start = max(0, start_m - context_chars)
        c_end = min(len(text), end_m + context_chars)

        # Evita sobreposição excessiva
        overlaps = False
        for u_start, u_end in used_ranges:
            if not (c_end < u_start or c_start > u_end):
                overlaps = True
                break
        if overlaps:
            continue

        used_ranges.append((c_start, c_end))

        # Ajusta para não cortar palavras no meio
        while c_start > 0 and not text[c_start].isspace():
            c_start -= 1
        while c_end < len(text) and not text[c_end].isspace():
            c_end += 1

        prefix = "…" if c_start > 0 else ""
        suffix = "…" if c_end < len(text) else ""

        # Monta trecho com tag <mark>
        before = text[c_start:start_m]
        matched_str = text[start_m:end_m]
        after = text[end_m:c_end]

        # Normaliza espaços em branco internos
        before_clean = re.sub(r"\s+", " ", before)
        after_clean = re.sub(r"\s+", " ", after)
        matched_clean = re.sub(r"\s+", " ", matched_str)

        snippet = f"{prefix}{before_clean}<mark>{matched_clean}</mark>{after_clean}{suffix}"
        snippets.append(snippet.strip())

    return snippets, total_matches


# =============================================================================
# Classificação de Arquivos e Metadados
# =============================================================================
def get_vestibulares(root_dir: Path = ROOT_DIR) -> list[str]:
    """Retorna os nomes das pastas de vestibulares na raiz."""
    return sorted(
        d.name
        for d in root_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in IGNORED_DIRS
    )


def classify_file(path: Path) -> tuple[int, str | None, str, str]:
    """
    Interpreta o nome do arquivo e pasta.
    Retorna (ano, semestre, fase, tipo).
    """
    match = FILE_PATTERN.match(path.stem)
    if match:
        ano = int(match["ano"])
        semestre = match["semestre"]
        fase = match["fase"] or ("1" if "1Fase" in path.stem else ("2" if "2Fase" in path.stem else "unica"))
        tipo = DOC_TYPES.get((match["tipo"] or "").lower(), "prova")
        return ano, semestre, fase, tipo

    year_match = YEAR_PATTERN.search(path.stem)
    ano = int(year_match.group(0)) if year_match else 0
    fase = "1" if "1" in path.parent.name else ("2" if "2" in path.parent.name else "unica")
    tipo = "gabarito" if "_gab" in path.stem.lower() else ("resolucao" if "_resol" in path.stem.lower() else "prova")
    return ano, None, fase, tipo


# =============================================================================
# Extração de Texto de PDFs
# =============================================================================
def extract_pdf_pages(pdf_path: Path) -> list[str]:
    """
    Extrai o texto página por página de um PDF.
    Retorna lista de textos (índice 0 = página 1).
    """
    pages_text: list[str] = []
    if not pdf_path.is_file():
        return pages_text

    if PDF_ENGINE == "fitz":
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                pages_text.append(page.get_text() or "")
            doc.close()
            return pages_text
        except Exception as exc:
            logger.warning("Erro ao ler com PyMuPDF %s: %s", pdf_path.name, exc)

    # Fallback para PyPDF2
    if PDF_ENGINE in ("pypdf2", "pypdf"):
        try:
            pdf_module = PyPDF2 if PDF_ENGINE == "pypdf2" else pypdf
            with pdf_path.open("rb") as f:
                reader = pdf_module.PdfReader(f)
                for page in reader.pages:
                    pages_text.append(page.extract_text() or "")
            return pages_text
        except Exception as exc:
            logger.warning("Erro ao ler com PyPDF %s: %s", pdf_path.name, exc)

    return pages_text


# =============================================================================
# Banco de Dados e Cache SQLite
# =============================================================================
def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Inicializa tabelas do cache SQLite e configura modo WAL para concorrência."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indexed_files (
            caminho TEXT PRIMARY KEY,
            mtime REAL,
            vestibular TEXT,
            ano INT,
            semestre TEXT,
            fase TEXT,
            tipo TEXT,
            num_paginas INT
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_pages (
            caminho TEXT,
            pagina INT,
            texto TEXT,
            PRIMARY KEY (caminho, pagina),
            FOREIGN KEY (caminho) REFERENCES indexed_files(caminho) ON DELETE CASCADE
        );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_filter ON indexed_files (vestibular, ano, tipo);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_ano ON indexed_files (ano);")
    conn.commit()
    return conn


def sync_index(
    root_dir: Path = ROOT_DIR,
    db_path: Path = DB_PATH,
    force: bool = False,
    max_workers: int = 4,
) -> dict[str, Any]:
    """
    Sincroniza o índice SQLite com os arquivos PDF existentes no disco.
    Apenas arquivos novos ou com mtime alterado são reprocessados.
    """
    start_time = time.perf_counter()
    vestibulares = get_vestibulares(root_dir)

    all_pdfs: list[Path] = []
    for vest in vestibulares:
        vest_dir = root_dir / vest
        if vest_dir.is_dir():
            all_pdfs.extend(p for p in vest_dir.rglob("*.pdf") if p.is_file())

    conn = init_db(db_path)
    cur = conn.cursor()

    # Mapeia estado atual do cache
    cur.execute("SELECT caminho, mtime FROM indexed_files")
    cached_files = {row[0]: row[1] for row in cur.fetchall()}

    to_process: list[Path] = []
    disk_rel_paths = set()

    for pdf in all_pdfs:
        rel_posix = pdf.relative_to(root_dir).as_posix()
        disk_rel_paths.add(rel_posix)
        mtime = pdf.stat().st_mtime
        if force or rel_posix not in cached_files or abs(cached_files[rel_posix] - mtime) > 0.01:
            to_process.append(pdf)

    # Remove arquivos deletados do disco
    deleted = set(cached_files.keys()) - disk_rel_paths
    if deleted:
        conn.executemany("DELETE FROM indexed_files WHERE caminho = ?", [(c,) for c in deleted])
        conn.executemany("DELETE FROM file_pages WHERE caminho = ?", [(c,) for c in deleted])
        conn.commit()
        logger.info("Removidos %d arquivos inexistentes do cache.", len(deleted))

    indexed_count = 0
    if to_process:
        logger.info("Indexando %d arquivos PDF novos/modificados...", len(to_process))

        def process_one(pdf_path: Path):
            rel = pdf_path.relative_to(root_dir).as_posix()
            vest = rel.split("/")[0]
            ano, sem, fase, tipo = classify_file(pdf_path)
            mtime = pdf_path.stat().st_mtime
            pages = extract_pdf_pages(pdf_path)
            return rel, mtime, vest, ano, sem, fase, tipo, len(pages), pages

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pdf = {executor.submit(process_one, pdf): pdf for pdf in to_process}
            for future in as_completed(future_to_pdf):
                try:
                    rel, mtime, vest, ano, sem, fase, tipo, num_pages, pages = future.result()
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO indexed_files
                        (caminho, mtime, vestibular, ano, semestre, fase, tipo, num_paginas)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (rel, mtime, vest, ano, sem, fase, tipo, num_pages),
                    )
                    conn.execute("DELETE FROM file_pages WHERE caminho = ?", (rel,))
                    pages_rows = [
                        (rel, idx + 1, page_text)
                        for idx, page_text in enumerate(pages)
                        if page_text.strip()
                    ]
                    if pages_rows:
                        conn.executemany(
                            "INSERT INTO file_pages (caminho, pagina, texto) VALUES (?, ?, ?)",
                            pages_rows,
                        )
                    indexed_count += 1
                except Exception as exc:
                    logger.error("Falha ao indexar %s: %s", future_to_pdf[future], exc)

        conn.commit()

    conn.close()
    elapsed = time.perf_counter() - start_time
    logger.info(
        "Sincronização do índice concluída em %.2fs (%d indexados, %d totais).",
        elapsed,
        indexed_count,
        len(disk_rel_paths),
    )
    return {
        "novos_ou_atualizados": indexed_count,
        "total_arquivos": len(disk_rel_paths),
        "removidos": len(deleted),
        "tempo_s": round(elapsed, 2),
    }


# =============================================================================
# Motor de Busca Principal
# =============================================================================
def buscar(
    query: str,
    options: dict[str, Any] | None = None,
    root_dir: Path = ROOT_DIR,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """
    Executa a busca avançada no acervo de provas.
    Parâmetros em `options`:
      - vestibulares: list[str] (ex: ["USP", "UNICAMP"])
      - anos: list[int] (ex: [2021, 2022])
      - ano_min: int | None
      - ano_max: int | None
      - tipos: list[str] (ex: ["prova", "gabarito"])
      - fases: list[str] (ex: ["1", "2"])
      - modo: "exata" | "todas" | "qualquer"
      - sensivel_acentos: bool (padrão: False)
      - sensivel_maiusculas: bool (padrão: False)
      - limite: int (máximo de páginas retornadas, padrão: 250)
    """
    t0 = time.perf_counter()
    opts = options or {}
    query_str = (query or "").strip()

    if not query_str:
        return {
            "termo": "",
            "total_ocorrencias": 0,
            "total_paginas": 0,
            "total_provas": 0,
            "tempo_ms": 0,
            "resumo_vestibulares": {},
            "resumo_anos": {},
            "resultados": [],
        }

    # Garante que o banco está pronto
    conn = init_db(db_path)

    # Extrai opções
    vestibulares = [v.strip() for v in opts.get("vestibulares", []) if v and v.strip()]
    anos = [int(a) for a in opts.get("anos", []) if str(a).isdigit()]
    ano_min = opts.get("ano_min")
    ano_max = opts.get("ano_max")
    tipos = [t.strip().lower() for t in opts.get("tipos", []) if t and t.strip()]
    fases = [f.strip() for f in opts.get("fases", []) if f and f.strip()]
    modo = opts.get("modo", "exata")
    sensivel_acentos = bool(opts.get("sensivel_acentos", False))
    sensivel_maiusculas = bool(opts.get("sensivel_maiusculas", False))
    limite = int(opts.get("limite", 300))

    # Constrói o regex principal e subpadrões para modo 'todas'
    main_pattern = build_pt_regex(
        query_str,
        modo=modo,
        sensivel_acentos=sensivel_acentos,
        sensivel_maiusculas=sensivel_maiusculas,
    )

    all_word_patterns: list[re.Pattern] = []
    if modo == "todas":
        words = [w for w in re.split(r"\s+", query_str) if w]
        all_word_patterns = [
            build_pt_regex(
                w,
                modo="exata",
                sensivel_acentos=sensivel_acentos,
                sensivel_maiusculas=sensivel_maiusculas,
            )
            for w in words
        ]

    # Monta a cláusula SQL filtrando pelos metadados
    sql_where: list[str] = []
    params: list[Any] = []

    if vestibulares:
        placeholders = ",".join("?" for _ in vestibulares)
        sql_where.append(f"f.vestibular IN ({placeholders})")
        params.extend(vestibulares)

    if anos:
        placeholders = ",".join("?" for _ in anos)
        sql_where.append(f"f.ano IN ({placeholders})")
        params.extend(anos)
    else:
        if ano_min:
            sql_where.append("f.ano >= ?")
            params.append(int(ano_min))
        if ano_max:
            sql_where.append("f.ano <= ?")
            params.append(int(ano_max))

    if tipos:
        placeholders = ",".join("?" for _ in tipos)
        sql_where.append(f"f.tipo IN ({placeholders})")
        params.extend(tipos)

    if fases:
        placeholders = ",".join("?" for _ in fases)
        sql_where.append(f"f.fase IN ({placeholders})")
        params.extend(fases)

    where_clause = f"WHERE {' AND '.join(sql_where)}" if sql_where else ""

    query_sql = f"""
        SELECT
            p.caminho,
            p.pagina,
            p.texto,
            f.vestibular,
            f.ano,
            f.semestre,
            f.fase,
            f.tipo,
            f.num_paginas
        FROM file_pages p
        JOIN indexed_files f ON p.caminho = f.caminho
        {where_clause}
        ORDER BY f.ano DESC, f.vestibular ASC, p.caminho ASC, p.pagina ASC
    """

    cur = conn.cursor()
    cur.execute(query_sql, params)

    resultados: list[dict[str, Any]] = []
    resumo_vestibulares: dict[str, int] = {}
    resumo_anos: dict[str, int] = {}
    provas_encontradas: set[str] = set()
    total_ocorrencias = 0

    for row in cur:
        caminho, pagina, texto, vestibular, ano, semestre, fase, tipo, num_paginas = row

        # Se modo é 'todas', todas as palavras devem casar no texto da página
        if modo == "todas":
            if not all(wp.search(texto) for wp in all_word_patterns):
                continue

        snippets, ocorrencias = extract_snippets(texto, main_pattern, max_snippets=2)
        if ocorrencias == 0:
            continue

        total_ocorrencias += ocorrencias
        provas_encontradas.add(caminho)
        resumo_vestibulares[vestibular] = resumo_vestibulares.get(vestibular, 0) + ocorrencias
        ano_str = str(ano) if ano else "Outros"
        resumo_anos[ano_str] = resumo_anos.get(ano_str, 0) + ocorrencias

        url_arquivo = f"/arquivos/{urllib.parse.quote(caminho)}#page={pagina}"
        nome_arquivo = Path(caminho).name

        resultados.append(
            {
                "vestibular": vestibular,
                "ano": ano,
                "semestre": semestre,
                "fase": fase,
                "tipo": tipo,
                "arquivo": nome_arquivo,
                "caminho": caminho,
                "url": url_arquivo,
                "pagina": pagina,
                "total_paginas": num_paginas,
                "ocorrencias": ocorrencias,
                "trechos": snippets,
            }
        )

        if len(resultados) >= limite:
            break

    conn.close()
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    return {
        "termo": query_str,
        "total_ocorrencias": total_ocorrencias,
        "total_paginas": len(resultados),
        "total_provas": len(provas_encontradas),
        "tempo_ms": elapsed_ms,
        "limite_atingido": len(resultados) >= limite,
        "resumo_vestibulares": dict(
            sorted(resumo_vestibulares.items(), key=lambda item: item[1], reverse=True)
        ),
        "resumo_anos": dict(
            sorted(resumo_anos.items(), key=lambda item: item[0], reverse=True)
        ),
        "resultados": resultados,
    }


def get_opcoes_busca(root_dir: Path = ROOT_DIR, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Retorna lista de vestibulares, anos e status do índice para preencher filtros."""
    conn = init_db(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            vestibular,
            COUNT(DISTINCT caminho) as total_arquivos,
            MIN(ano) as ano_min,
            MAX(ano) as ano_max
        FROM indexed_files
        GROUP BY vestibular
        ORDER BY vestibular ASC
    """)
    rows = cur.fetchall()

    cur.execute("SELECT DISTINCT ano FROM indexed_files WHERE ano > 0 ORDER BY ano DESC")
    anos = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*), (SELECT COUNT(*) FROM file_pages) FROM indexed_files")
    count_files, count_pages = cur.fetchone()

    conn.close()

    vestibulares_info = []
    for r in rows:
        vest, total, a_min, a_max = r
        vestibulares_info.append(
            {
                "nome": vest,
                "total_arquivos": total,
                "ano_min": a_min,
                "ano_max": a_max,
            }
        )

    # Se banco ainda estiver vazio, busca pastas do disco
    if not vestibulares_info:
        for vest in get_vestibulares(root_dir):
            vestibulares_info.append(
                {
                    "nome": vest,
                    "total_arquivos": 0,
                    "ano_min": None,
                    "ano_max": None,
                }
            )

    return {
        "vestibulares": vestibulares_info,
        "anos_disponiveis": anos,
        "ano_min": min(anos, default=1990),
        "ano_max": max(anos, default=2026),
        "status_indice": {
            "total_arquivos": count_files,
            "total_paginas": count_pages,
            "engine": PDF_ENGINE,
        },
    }


# =============================================================================
# Execução via Linha de Comando (CLI)
# =============================================================================
def main(argv: list[str] | None = None) -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        description="Mecanismo de busca textual avançada em PDFs de provas de vestibulares."
    )
    parser.add_argument("termo", nargs="?", default="", help="Palavra ou termo a buscar")
    parser.add_argument("--indexar", action="store_true", help="Atualiza o índice de busca")
    parser.add_argument("--forcar", action="store_true", help="Força reindexação completa")
    parser.add_argument("--vestibular", "-v", nargs="*", default=[], help="Filtrar por vestibular(es)")
    parser.add_argument("--ano", "-a", nargs="*", type=int, default=[], help="Filtrar por ano(s)")
    parser.add_argument("--tipo", "-t", nargs="*", default=[], help="prova, gabarito, resolucao")
    parser.add_argument("--modo", choices=["exata", "todas", "qualquer"], default="exata")
    parser.add_argument("--sensivel-acentos", action="store_true", help="Exige correspondência exata de acentos")
    parser.add_argument("--sensivel-maiusculas", action="store_true", help="Diferencia maiúsculas e minúsculas")
    parser.add_argument("--limite", type=int, default=100, help="Limite de resultados")

    args = parser.parse_args(argv)

    if args.indexar or args.forcar:
        res = sync_index(force=args.forcar)
        print(f"Indexação concluída: {res['novos_ou_atualizados']} indexados em {res['tempo_s']}s.")
        if not args.termo:
            return

    if not args.termo:
        parser.print_help()
        return

    # Se banco não existe, faz sincronização inicial automática
    if not DB_PATH.exists():
        print("Banco de busca não encontrado. Criando índice inicial...")
        sync_index()

    options = {
        "vestibulares": args.vestibular,
        "anos": args.ano,
        "tipos": args.tipo,
        "modo": args.modo,
        "sensivel_acentos": args.sensivel_acentos,
        "sensivel_maiusculas": args.sensivel_maiusculas,
        "limite": args.limite,
    }

    resultado = buscar(args.termo, options)

    print("\n" + "=" * 60)
    print(f" BUSCA: '{resultado['termo']}'")
    print(
        f" Ocorrências: {resultado['total_ocorrencias']} em {resultado['total_paginas']} páginas "
        f"({resultado['total_provas']} provas) [{resultado['tempo_ms']}ms]"
    )
    print("=" * 60)

    for item in resultado["resultados"]:
        print(
            f"\n[PDF] [{item['vestibular']}] {item['arquivo']} (Pag. {item['pagina']}/{item['total_paginas']})"
        )
        print(f"   Link: {item['url']}")
        for trecho in item["trechos"]:
            # Remove marcação HTML para o terminal
            clean_trecho = trecho.replace("<mark>", "\033[1;33m").replace("</mark>", "\033[0m")
            print(f"   > {clean_trecho}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main(sys.argv[1:])
