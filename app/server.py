"""
===============================================================================
ARQUIVO: app/server.py
CAMADA: Backend / Servidor HTTP & API
PAPEL NO SISTEMA:
  - Servidor HTTP leve construído com a biblioteca padrão do Python (http.server).
  - Serve os templates HTML (camada de apresentação) e arquivos estáticos (CSS/JS).
  - CONTROLE DE VERSÕES & CACHE BUSTING:
      * Ao servir index.html, calcula dinamicamente o timestamp de modificação
        (st_mtime) de style.css e app.js e injeta nos marcadores {{CSS_VERSION}}
        e {{JS_VERSION}}.
      * Utiliza urllib.parse para ignorar query parameters (?v=...) na busca dos arquivos.
      * Configura headers HTTP de Cache-Control para que alterações em CSS e JS
        sejam refletidas imediatamente no navegador sem necessidade de limpar cache manual.
  - Endpoints de API:
      * GET  /api/vestibulares : Lista dinamicamente as pastas de vestibulares na raiz.
      * POST /api/preview      : Calcula previamente os nomes dos arquivos e caminhos.
      * POST /api/upload       : Recebe arquivos em Base64 (JSON) e salva nos diretórios
                                 corretos respeitando os padrões de nomenclatura do projeto.
REGRAS DE NOMENCLATURA & DIRETÓRIOS:
  - Raiz do projeto (ROOT_DIR): Onde ficam as pastas dos vestibulares (AFA, IME, etc.).
  - AFA: Salva diretamente em ROOT_DIR/AFA/ (AFA_{ano}.pdf e AFA_{ano}_gab.pdf).
  - IME, ITA, UNESP, UNICAMP: Salva em {VESTIBULAR}/1ª Fase/ ou 2ª Fase/
    ({VESTIBULAR}_{ano}_{fase}Fase.pdf e {VESTIBULAR}_{ano}_{fase}Fase_gab.pdf).
  - USP: Salva em USP/1ª Fase/ (FEVEST_{ano}_1Fase.pdf por padrão histórico da pasta)
    ou USP/2ª Fase/ (FUVEST_{ano}_2Fase.pdf).
COMPATIBILIDADE: Python 3.14+ (Sem dependências externas).
===============================================================================
"""

import base64
import http.server
import json
import logging
import mimetypes
from pathlib import Path
import sys
from typing import Any
import urllib.parse

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("VestibularesServer")

# Diretórios base
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
PORT = 8000


def get_vestibulares() -> list[str]:
    """Retorna as pastas dos vestibulares presentes na raiz do projeto, ignorando pastas de sistema."""
    ignored = {".git", ".vscode", ".venv", "__pycache__", "app", "build", "dist"}
    vestibulares = [
        d.name
        for d in ROOT_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in ignored
    ]
    vestibulares.sort()
    return vestibulares


def get_asset_version(file_path: Path) -> str:
    """Retorna o timestamp de modificação do arquivo em segundos para cache busting automático."""
    try:
        if file_path.is_file():
            return str(int(file_path.stat().st_mtime))
    except Exception as exc:
        logger.warning("Falha ao obter mtime para %s: %s", file_path, exc)
    return "1"


def resolve_file_destinations(
    vestibular: str, ano: str, fase: str, prefixo_usp: str = "FEVEST"
) -> dict[str, Any]:
    """
    Calcula a pasta de destino e a nomenclatura padronizada dos arquivos
    para prova e gabarito com base no vestibular, ano e fase selecionados.
    """
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
        "dest_folder": str(dest_folder.relative_to(ROOT_DIR)).replace("\\", "/"),
        "dest_path": dest_folder,
        "prova_name": prova_name,
        "gabarito_name": gabarito_name,
    }


class VestibularesHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP customizado para servir templates, estáticos e processar uploads."""

    def _send_json_response(self, status_code: int, data: dict[str, Any]) -> None:
        """Envia resposta JSON com encoding UTF-8."""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_index_html(self) -> None:
        """Serve o template index.html injetando as versões dinâmicas de CSS e JS para cache busting."""
        template_file = TEMPLATES_DIR / "index.html"
        if not template_file.is_file():
            self.send_error(404, "Template index.html não encontrado.")
            return

        css_file = STATIC_DIR / "css" / "style.css"
        js_file = STATIC_DIR / "js" / "app.js"

        css_version = get_asset_version(css_file)
        js_version = get_asset_version(js_file)

        content = template_file.read_text(encoding="utf-8")
        content = content.replace("{{CSS_VERSION}}", css_version)
        content = content.replace("{{JS_VERSION}}", js_version)
        payload = content.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        # Instrução para o navegador não armazenar o HTML em cache, garantindo URLs de assets sempre atualizadas
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_file(self, file_path: Path) -> None:
        """Serve um arquivo estático local com o Content-Type apropriado e controle de cache."""
        if not file_path.is_file():
            self.send_error(404, f"Arquivo não encontrado: {file_path.name}")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        content = file_path.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", f"{mime_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        # Como a URL inclui ?v=<timestamp>, o arquivo pode ser mantido em cache pelo navegador com segurança
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        clean_path = parsed_url.path

        # Página inicial (com injeção de versões de cache busting)
        if clean_path in ("/", "/index.html"):
            self._serve_index_html()
            return

        # Arquivos estáticos (ignorando parâmetros de query como ?v=...)
        if clean_path.startswith("/static/"):
            relative_static = clean_path[len("/static/"):]
            file_path = STATIC_DIR / relative_static
            self._serve_file(file_path)
            return

        # API de listagem de vestibulares
        if clean_path == "/api/vestibulares":
            self._send_json_response(200, {"vestibulares": get_vestibulares()})
            return

        self.send_error(404, "Página ou recurso não encontrado.")

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        clean_path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        # Endpoint de preview de nomenclatura
        if clean_path == "/api/preview":
            try:
                data = json.loads(raw_body.decode("utf-8"))
                vestibular = data.get("vestibular", "")
                ano = data.get("ano", "")
                fase = data.get("fase", "1")
                prefixo_usp = data.get("prefixo_usp", "FEVEST")

                res = resolve_file_destinations(vestibular, ano, fase, prefixo_usp)
                self._send_json_response(
                    200,
                    {
                        "dest_folder": res["dest_folder"],
                        "prova_name": res["prova_name"],
                        "gabarito_name": res["gabarito_name"],
                    },
                )
            except Exception as exc:
                logger.error("Erro ao calcular preview: %s", exc)
                self._send_json_response(400, {"error": str(exc)})
            return

        # Endpoint de upload e salvamento de arquivos
        if clean_path == "/api/upload":
            try:
                data = json.loads(raw_body.decode("utf-8"))
                vestibular = data.get("vestibular", "").strip()
                ano = str(data.get("ano", "")).strip()
                fase = str(data.get("fase", "1")).strip()
                prefixo_usp = data.get("prefixo_usp", "FEVEST")

                if not vestibular or not ano:
                    self._send_json_response(
                        400, {"error": "Vestibular e ano são obrigatórios."}
                    )
                    return

                res = resolve_file_destinations(vestibular, ano, fase, prefixo_usp)
                dest_path: Path = res["dest_path"]
                dest_path.mkdir(parents=True, exist_ok=True)

                saved_files: list[str] = []

                # Salvar Prova (PDF)
                prova_data = data.get("prova")
                if prova_data and prova_data.get("data"):
                    prova_file = dest_path / res["prova_name"]
                    b64_content = prova_data["data"]
                    if "," in b64_content:
                        b64_content = b64_content.split(",", 1)[1]
                    prova_bytes = base64.b64decode(b64_content)
                    prova_file.write_bytes(prova_bytes)
                    saved_files.append(
                        f"{res['dest_folder']}/{res['prova_name']} ({len(prova_bytes):,} bytes)"
                    )
                    logger.info("Salvo arquivo de prova: %s", prova_file)

                # Salvar Gabarito (PDF)
                gabarito_data = data.get("gabarito")
                if gabarito_data and gabarito_data.get("data"):
                    gabarito_file = dest_path / res["gabarito_name"]
                    b64_content = gabarito_data["data"]
                    if "," in b64_content:
                        b64_content = b64_content.split(",", 1)[1]
                    gabarito_bytes = base64.b64decode(b64_content)
                    gabarito_file.write_bytes(gabarito_bytes)
                    saved_files.append(
                        f"{res['dest_folder']}/{res['gabarito_name']} ({len(gabarito_bytes):,} bytes)"
                    )
                    logger.info("Salvo arquivo de gabarito: %s", gabarito_file)

                if not saved_files:
                    self._send_json_response(
                        400, {"error": "Nenhum arquivo enviado (selecione ao menos um PDF)."}
                    )
                    return

                self._send_json_response(
                    200,
                    {
                        "success": True,
                        "message": "Arquivos salvos com sucesso!",
                        "saved_files": saved_files,
                        "dest_folder": res["dest_folder"],
                    },
                )
            except Exception as exc:
                logger.error("Erro no upload: %s", exc)
                self._send_json_response(500, {"error": f"Erro interno ao salvar arquivos: {exc}"})
            return

        self._send_json_response(404, {"error": "Endpoint não encontrado."})


def run_server(port: int = PORT) -> None:
    """Inicia o servidor HTTP."""
    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, VestibularesHandler)
    logger.info("Servidor iniciado em http://localhost:%d", port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor interrompido pelo usuário.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
