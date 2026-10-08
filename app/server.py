"""
===============================================================================
ARQUIVO: app/server.py
CAMADA: Backend / Servidor HTTP & API
PAPEL NO SISTEMA:
  - Servidor HTTP leve (biblioteca padrão do Python, ThreadingHTTPServer) que:
      * Serve a interface (templates/index.html) e os estáticos (static/css, static/js).
      * Monta um CATÁLOGO do acervo varrendo as pastas de vestibulares na raiz.
      * Serve os PDFs do acervo para visualização no navegador (nova aba).
      * Recebe uploads de provas/gabaritos e salva com a nomenclatura padrão.
  - CACHE BUSTING:
      * No template, marcadores {{v:caminho/relativo.ext}} são substituídos pelo
        timestamp de modificação do arquivo em static/ (ex.: {{v:css/base.css}}).
      * O HTML é servido sem cache; os estáticos com cache longo (a URL muda a cada edição).
ENDPOINTS:
  - GET  /                    : Interface (biblioteca + modal de upload).
  - GET  /static/<arquivo>    : CSS/JS (parâmetros ?v=... são ignorados na busca).
  - GET  /arquivos/<caminho>  : PDF do acervo, exibido inline (ex.: /arquivos/USP/1%C2%AA%20Fase/...).
  - GET  /api/vestibulares    : Lista de pastas de vestibulares.
  - GET  /api/catalogo        : Catálogo completo (vestibulares > grupos/fases > edições > arquivos).
  - POST /api/preview         : Calcula pasta e nomes de destino de um upload.
  - POST /api/upload          : Recebe PDFs em Base64 (JSON) e grava no acervo.
REGRAS DE NOMENCLATURA (arquivos no acervo):
  - {PREFIXO}_{ANO}[_{SEMESTRE}][_{N}Fase][_gab|_resol].pdf
      * sem sufixo -> prova | _gab -> gabarito | _resol -> resolução
  - AFA: raiz de AFA/ (AFA_{ano}.pdf / AFA_{ano}_gab.pdf).
  - IME, ITA, UNESP, UNICAMP: {VEST}/1ª Fase/ ou 2ª Fase/.
  - USP: 1ª Fase com prefixo FEVEST (padrão histórico) e 2ª Fase com FUVEST.
SEGURANÇA:
  - Caminhos de arquivos são resolvidos e validados para nunca sair da raiz do projeto.
  - Upload aceita apenas vestibulares existentes, ano com 4 dígitos e conteúdo PDF.
COMPATIBILIDADE: Python 3.14+ (sem dependências externas).
===============================================================================
"""

import base64
import binascii
import http.server
import json
import logging
import mimetypes
import re
import shutil
import sys
import urllib.parse
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("VestibularesServer")

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
PORT = 8000

IGNORED_DIRS = {".git", ".vscode", ".venv", "__pycache__", "app", "build", "dist"}
FILE_PATTERN = re.compile(
    r"^(?P<prefixo>[A-Za-z]+)_(?P<ano>\d{4})"
    r"(?:_(?P<semestre>\d))?"
    r"(?:_(?P<fase>\d)Fase)?"
    r"(?:_(?P<tipo>gab|resol))?$",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")
ASSET_VERSION_PATTERN = re.compile(r"\{\{\s*v:([\w./-]+)\s*\}\}")
DOC_TYPES = {"": "prova", "gab": "gabarito", "resol": "resolucao"}
TEXT_MIME_PREFIXES = ("text/", "application/javascript", "application/json")
CLIENT_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


# =============================================================================
# Utilidades gerais
# =============================================================================
def get_vestibulares() -> list[str]:
    """Retorna as pastas dos vestibulares presentes na raiz do projeto."""
    return sorted(
        d.name
        for d in ROOT_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in IGNORED_DIRS
    )


def get_asset_version(file_path: Path) -> str:
    """Retorna o timestamp de modificação do arquivo (usado para cache busting)."""
    try:
        if file_path.is_file():
            return str(int(file_path.stat().st_mtime))
    except OSError as exc:
        logger.warning("Falha ao obter mtime para %s: %s", file_path, exc)
    return "1"


def render_template(name: str) -> bytes:
    """Lê um template e substitui os marcadores {{v:...}} pelas versões dos estáticos."""
    content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    rendered = ASSET_VERSION_PATTERN.sub(
        lambda match: get_asset_version(STATIC_DIR / match.group(1)), content
    )
    return rendered.encode("utf-8")


def resolve_inside(base: Path, relative: str) -> Path | None:
    """Resolve um caminho relativo garantindo que ele permaneça dentro de `base`."""
    base_resolved = base.resolve()
    target = (base_resolved / urllib.parse.unquote(relative)).resolve()
    if not target.is_relative_to(base_resolved) or not target.is_file():
        return None
    return target


# =============================================================================
# Catálogo do acervo
# =============================================================================
def build_file_url(path: Path) -> str:
    """Monta a URL pública de um PDF do acervo."""
    return "/arquivos/" + urllib.parse.quote(path.relative_to(ROOT_DIR).as_posix())


def file_info(path: Path) -> dict[str, Any]:
    """Metadados de um arquivo para o frontend."""
    return {
        "nome": path.name,
        "caminho": path.relative_to(ROOT_DIR).as_posix(),
        "url": build_file_url(path),
        "tamanho": path.stat().st_size,
    }


def describe_group(pasta: str) -> dict[str, Any]:
    """Descreve um grupo (subpasta do vestibular): título, fase e ordem de exibição."""
    parts = [part for part in pasta.split("/") if part]
    if not parts:
        return {"titulo": "Fase única", "fase": "unica", "ordem": 90}

    match = re.match(r"\d", parts[0])
    if not match:
        return {"titulo": " · ".join(parts), "fase": "outros", "ordem": 80}

    fase = match.group(0)
    return {"titulo": " · ".join(parts), "fase": fase, "ordem": int(fase) * 10 + len(parts)}


def classify_file(path: Path) -> tuple[str, int, str | None, str]:
    """
    Interpreta o nome do arquivo.
    Retorna (chave_da_edicao, ano, semestre, tipo_documento).
    Arquivos fora do padrão viram uma edição própria do tipo "prova".
    """
    match = FILE_PATTERN.match(path.stem)
    if match:
        ano = int(match["ano"])
        semestre = match["semestre"]
        tipo = DOC_TYPES[(match["tipo"] or "").lower()]
        return f"{ano}-{semestre or ''}", ano, semestre, tipo

    year = YEAR_PATTERN.search(path.stem)
    return f"x-{path.stem}", int(year.group(0)) if year else 0, None, "prova"


def build_vestibular_catalog(nome: str) -> dict[str, Any]:
    """Monta o catálogo de um vestibular agrupando os PDFs por pasta e edição."""
    vest_dir = ROOT_DIR / nome
    grupos: dict[str, dict[str, Any]] = {}

    for pdf in sorted(vest_dir.rglob("*.pdf")):
        if not pdf.is_file():
            continue
        pasta = pdf.parent.relative_to(vest_dir).as_posix()
        pasta = "" if pasta == "." else pasta
        grupo = grupos.setdefault(pasta, {"pasta": pasta, **describe_group(pasta), "edicoes": {}})

        chave, ano, semestre, tipo = classify_file(pdf)
        edicao = grupo["edicoes"].setdefault(
            chave,
            {
                "ano": ano,
                "semestre": semestre,
                "titulo": str(ano) if chave[0] != "x" else pdf.stem,
                "arquivos": {},
                "extras": [],
            },
        )
        if tipo in edicao["arquivos"]:
            edicao["extras"].append(file_info(pdf))
        else:
            edicao["arquivos"][tipo] = file_info(pdf)

    lista_grupos: list[dict[str, Any]] = []
    for grupo in sorted(grupos.values(), key=lambda g: (g["ordem"], g["pasta"])):
        edicoes = sorted(
            grupo["edicoes"].values(),
            key=lambda e: (e["ano"], e["semestre"] or ""),
            reverse=True,
        )
        lista_grupos.append(
            {
                "id": f"{nome}/{grupo['pasta']}",
                "pasta": grupo["pasta"],
                "titulo": grupo["titulo"],
                "fase": grupo["fase"],
                "edicoes": edicoes,
            }
        )

    todas = [edicao for grupo in lista_grupos for edicao in grupo["edicoes"]]
    anos = [edicao["ano"] for edicao in todas if edicao["ano"]]
    return {
        "nome": nome,
        "grupos": lista_grupos,
        "total_edicoes": len(todas),
        "total_provas": sum("prova" in e["arquivos"] for e in todas),
        "total_gabaritos": sum("gabarito" in e["arquivos"] for e in todas),
        "ano_min": min(anos, default=None),
        "ano_max": max(anos, default=None),
    }


def build_catalog() -> dict[str, Any]:
    """Catálogo completo do acervo com totais gerais."""
    vestibulares = [build_vestibular_catalog(nome) for nome in get_vestibulares()]
    anos_min = [v["ano_min"] for v in vestibulares if v["ano_min"]]
    anos_max = [v["ano_max"] for v in vestibulares if v["ano_max"]]
    return {
        "vestibulares": vestibulares,
        "totais": {
            "vestibulares": len(vestibulares),
            "edicoes": sum(v["total_edicoes"] for v in vestibulares),
            "provas": sum(v["total_provas"] for v in vestibulares),
            "gabaritos": sum(v["total_gabaritos"] for v in vestibulares),
            "ano_min": min(anos_min, default=None),
            "ano_max": max(anos_max, default=None),
        },
    }


# =============================================================================
# Regras de nomenclatura para upload
# =============================================================================
def resolve_file_destinations(
    vestibular: str, ano: str, fase: str, prefixo_usp: str = "FEVEST"
) -> dict[str, Any]:
    """Calcula a pasta de destino e os nomes padronizados de prova e gabarito."""
    vestibular_clean = vestibular.strip()
    ano_clean = str(ano).strip()
    fase_clean = str(fase).strip()

    if vestibular_clean == "AFA":
        dest_folder = ROOT_DIR / "AFA"
        prova_name = f"AFA_{ano_clean}.pdf"
        gabarito_name = f"AFA_{ano_clean}_gab.pdf"
    else:
        phase_folder_name = "1ª Fase" if fase_clean == "1" else "2ª Fase"
        dest_folder = ROOT_DIR / vestibular_clean / phase_folder_name
        suffix = "1Fase" if fase_clean == "1" else "2Fase"

        if vestibular_clean == "USP":
            prefix = prefixo_usp if fase_clean == "1" else "FUVEST"
        else:
            prefix = vestibular_clean

        prova_name = f"{prefix}_{ano_clean}_{suffix}.pdf"
        gabarito_name = f"{prefix}_{ano_clean}_{suffix}_gab.pdf"

    return {
        "dest_folder": dest_folder.relative_to(ROOT_DIR).as_posix(),
        "dest_path": dest_folder,
        "prova_name": prova_name,
        "gabarito_name": gabarito_name,
    }


def validate_upload_params(data: dict[str, Any]) -> tuple[str, str, str, str]:
    """Valida e normaliza os parâmetros do upload. Lança ValueError se inválidos."""
    vestibular = str(data.get("vestibular", "")).strip()
    ano = str(data.get("ano", "")).strip()
    fase = str(data.get("fase", "1")).strip()
    prefixo_usp = str(data.get("prefixo_usp", "FEVEST")).strip().upper()

    if vestibular not in get_vestibulares():
        raise ValueError("Vestibular inválido.")
    if not re.fullmatch(r"\d{4}", ano):
        raise ValueError("Informe um ano com 4 dígitos.")
    if fase not in {"1", "2"}:
        raise ValueError("Fase inválida.")
    if prefixo_usp not in {"FEVEST", "FUVEST"}:
        raise ValueError("Prefixo USP inválido.")
    return vestibular, ano, fase, prefixo_usp


def decode_pdf(document: dict[str, Any] | None) -> bytes | None:
    """Decodifica um documento Base64 (data URL ou puro) e confirma que é um PDF."""
    if not document or not document.get("data"):
        return None
    content = str(document["data"])
    if "," in content:
        content = content.split(",", 1)[1]
    raw = base64.b64decode(content)
    if not raw.startswith(b"%PDF"):
        raise ValueError(f"O arquivo '{document.get('filename', '')}' não parece ser um PDF válido.")
    return raw


# =============================================================================
# Handler HTTP
# =============================================================================
class VestibularesHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP: interface, estáticos, PDFs do acervo e API."""

    # ---------------------------------------------------------------- respostas
    def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_bytes(self, payload: bytes, content_type: str, cache_control: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(
        self,
        path: Path,
        content_type: str,
        cache_control: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        """Envia um arquivo em streaming (adequado para PDFs grandes)."""
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", cache_control)
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            with path.open("rb") as file_handle:
                shutil.copyfileobj(file_handle, self.wfile)
        except CLIENT_DISCONNECT_ERRORS:
            pass  # O visualizador de PDF do navegador pode cancelar a leitura.

    # ------------------------------------------------------------------- rotas
    def _serve_index(self) -> None:
        try:
            payload = render_template("index.html")
        except OSError:
            self.send_error(404, "Template index.html não encontrado.")
            return
        self._send_bytes(payload, "text/html; charset=utf-8", "no-cache, no-store, must-revalidate")

    def _serve_static(self, relative: str) -> None:
        path = resolve_inside(STATIC_DIR, relative)
        if path is None:
            self.send_error(404, "Arquivo estático não encontrado.")
            return
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime_type.startswith(TEXT_MIME_PREFIXES):
            mime_type += "; charset=utf-8"
        self._send_file(path, mime_type, "public, max-age=31536000, immutable")

    def _serve_pdf(self, relative: str) -> None:
        path = resolve_inside(ROOT_DIR, relative)
        if path is None or path.suffix.lower() != ".pdf":
            self.send_error(404, "PDF não encontrado.")
            return
        if path.relative_to(ROOT_DIR.resolve()).parts[0] not in get_vestibulares():
            self.send_error(403, "Acesso negado.")
            return
        disposition = f"inline; filename*=UTF-8''{urllib.parse.quote(path.name)}"
        self._send_file(path, "application/pdf", "no-cache", {"Content-Disposition": disposition})

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path

        if path in ("/", "/index.html"):
            self._serve_index()
        elif path.startswith("/static/"):
            self._serve_static(path.removeprefix("/static/"))
        elif path.startswith("/arquivos/"):
            self._serve_pdf(path.removeprefix("/arquivos/"))
        elif path == "/api/catalogo":
            self._send_json(200, build_catalog())
        elif path == "/api/vestibulares":
            self._send_json(200, {"vestibulares": get_vestibulares()})
        else:
            self.send_error(404, "Página ou recurso não encontrado.")

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            data = json.loads(raw_body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "JSON inválido."})
            return

        if path == "/api/preview":
            self._handle_preview(data)
        elif path == "/api/upload":
            self._handle_upload(data)
        else:
            self._send_json(404, {"error": "Endpoint não encontrado."})

    # ---------------------------------------------------------------- handlers
    def _handle_preview(self, data: dict[str, Any]) -> None:
        try:
            vestibular, ano, fase, prefixo_usp = validate_upload_params(data)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        destino = resolve_file_destinations(vestibular, ano, fase, prefixo_usp)
        self._send_json(
            200,
            {
                "dest_folder": destino["dest_folder"],
                "prova_name": destino["prova_name"],
                "gabarito_name": destino["gabarito_name"],
            },
        )

    def _handle_upload(self, data: dict[str, Any]) -> None:
        try:
            vestibular, ano, fase, prefixo_usp = validate_upload_params(data)
            documentos = {
                "prova_name": decode_pdf(data.get("prova")),
                "gabarito_name": decode_pdf(data.get("gabarito")),
            }
        except (ValueError, binascii.Error) as exc:
            self._send_json(400, {"error": str(exc)})
            return

        if not any(documentos.values()):
            self._send_json(400, {"error": "Selecione ao menos um PDF (prova ou gabarito)."})
            return

        destino = resolve_file_destinations(vestibular, ano, fase, prefixo_usp)
        dest_path: Path = destino["dest_path"]

        try:
            dest_path.mkdir(parents=True, exist_ok=True)
            saved_files: list[str] = []
            for name_key, content in documentos.items():
                if content is None:
                    continue
                target = dest_path / destino[name_key]
                target.write_bytes(content)
                saved_files.append(f"{destino['dest_folder']}/{destino[name_key]}")
                logger.info("Arquivo salvo: %s (%d bytes)", target, len(content))
        except OSError as exc:
            logger.error("Erro ao gravar arquivos: %s", exc)
            self._send_json(500, {"error": f"Erro ao gravar arquivos: {exc}"})
            return

        self._send_json(
            200,
            {
                "success": True,
                "message": "Arquivos salvos com sucesso!",
                "saved_files": saved_files,
                "dest_folder": destino["dest_folder"],
            },
        )


def run_server(port: int = PORT) -> None:
    """Inicia o servidor HTTP (multithread, para servir PDFs em paralelo)."""
    httpd = http.server.ThreadingHTTPServer(("", port), VestibularesHandler)
    logger.info("Servidor iniciado em http://localhost:%d", port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor interrompido pelo usuário.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server(int(sys.argv[1]) if len(sys.argv) > 1 else PORT)
