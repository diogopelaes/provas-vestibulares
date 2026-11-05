"""
===============================================================================
ARQUIVO: app/services.py
CAMADA: Regras de Negócio e Serviços de Domínio
PAPEL NO SISTEMA:
  - Mantém a lógica de negócio isolada das views:
      * Varredura e catálogo do acervo na pasta media/.
      * Padronização de nomes de arquivos e pastas de destino.
      * Gravação e auditoria de uploads.
      * Suporte a cache busting via timestamp mtime (GEMINI.md).
===============================================================================
"""

import logging
import re
import urllib.parse
from pathlib import Path
from typing import Any

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import format_html

from app.models import RegistroUpload

logger = logging.getLogger("VestibularesServices")

MEDIA_ROOT: Path = Path(settings.MEDIA_ROOT)
STATIC_DIR: Path = Path(settings.BASE_DIR) / "app" / "static"
IGNORED_DIRS = {".git", ".vscode", ".venv", "__pycache__", "build", "dist"}

FILE_PATTERN = re.compile(
    r"^(?P<prefixo>[a-zA-ZÀ-ÿ]+)_(?P<ano>\d{4})"
    r"(?:_(?P<semestre>\d))?"
    r"(?:_(?P<etapa>\d)(?P<tipo_etapa>Fase|Serie))?"
    r"(?:_(?P<tipo>gab|resol))?$",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")
ASSET_VERSION_PATTERN = re.compile(r"\{\{\s*v:([\w./-]+)\s*\}\}")
DOC_TYPES = {"": "prova", "gab": "gabarito", "resol": "resolucao"}


# =============================================================================
# Cache Busting e Renderização
# =============================================================================
def get_asset_version(relative_path: str | Path) -> str:
    """Retorna o timestamp (st_mtime) da última modificação do arquivo estático."""
    try:
        file_path = STATIC_DIR / relative_path
        if file_path.is_file():
            return str(int(file_path.stat().st_mtime))
    except OSError as exc:
        logger.warning("Falha ao obter mtime para %s: %s", relative_path, exc)
    return "1"


def render_with_asset_versions(template_name: str, request: Any, context: dict[str, Any] | None = None) -> str:
    """
    Renderiza um template Django substituindo os marcadores {{v:caminho}}
    pelo timestamp do arquivo estático ANTES da compilação do Django,
    garantindo compatibilidade com cache busting e tags dinâmicas do Django.
    """
    from django.template import RequestContext, Template

    template_path = Path(settings.BASE_DIR) / "app" / "templates" / template_name
    template_raw = template_path.read_text(encoding="utf-8")

    # Substituição imediata dos marcadores de asset versioning
    template_preprocessed = ASSET_VERSION_PATTERN.sub(
        lambda match: get_asset_version(match.group(1)), template_raw
    )

    django_template = Template(template_preprocessed)
    ctx = RequestContext(request, context or {})
    return django_template.render(ctx)


# =============================================================================
# Descoberta de Vestibulares
# =============================================================================
def get_vestibulares() -> list[str]:
    """Retorna as pastas dos vestibulares presentes em media/."""
    if not MEDIA_ROOT.is_dir():
        return []
    return sorted(
        d.name
        for d in MEDIA_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in IGNORED_DIRS
    )


# =============================================================================
# Catálogo do Acervo
# =============================================================================
def build_file_url(path: Path) -> str:
    """Monta a URL pública de um PDF do acervo dentro de media/."""
    rel = path.relative_to(MEDIA_ROOT).as_posix()
    return "/media/" + urllib.parse.quote(rel)


def file_info(path: Path) -> dict[str, Any]:
    """Metadados de um arquivo PDF para o frontend."""
    return {
        "nome": path.name,
        "caminho": path.relative_to(MEDIA_ROOT).as_posix(),
        "url": build_file_url(path),
        "tamanho": path.stat().st_size,
    }


def describe_group(pasta: str) -> dict[str, Any]:
    """Descreve um grupo (subpasta do vestibular): título, fase e ordem de exibição."""
    parts = [part for part in pasta.split("/") if part]
    if not parts:
        return {"titulo": "Fase única", "fase": "unica", "rotulo": "Fase Única", "ordem": 90}

    match = re.match(r"(\d+)[ªaºo]?\s*(S[eé]rie|Fase)?", parts[0], re.IGNORECASE)
    if not match:
        return {"titulo": " · ".join(parts), "fase": "outros", "rotulo": " · ".join(parts), "ordem": 80}

    num = match.group(1)
    tipo = (match.group(2) or "").lower()
    if tipo.startswith("s"):
        fase_id = f"{num}_serie"
        rotulo = f"{num}ª Série"
    else:
        fase_id = num
        rotulo = f"{num}ª Fase"

    return {
        "titulo": " · ".join(parts),
        "fase": fase_id,
        "rotulo": rotulo,
        "ordem": int(num) * 10 + len(parts),
    }


def classify_file(path: Path) -> tuple[str, int, str | None, str]:
    """
    Interpreta o nome do arquivo.
    Retorna (chave_da_edicao, ano, semestre, tipo_documento).
    """
    match = FILE_PATTERN.match(path.stem)
    if match:
        ano = int(match["ano"])
        semestre = match["semestre"]
        tipo = DOC_TYPES[(match["tipo"] or "").lower()]
        return f"{ano}-{semestre or ''}", ano, semestre, tipo

    year = YEAR_PATTERN.search(path.stem)
    ano = int(year.group(0)) if year else 0
    stem_lower = path.stem.lower()
    tipo = "gabarito" if "_gab" in stem_lower else ("resolucao" if "_resol" in stem_lower else "prova")
    return f"x-{path.stem}", ano, None, tipo


def build_vestibular_catalog(nome: str) -> dict[str, Any]:
    """Monta o catálogo de um vestibular agrupando os PDFs por pasta e edição."""
    vest_dir = MEDIA_ROOT / nome
    grupos: dict[str, dict[str, Any]] = {}

    if vest_dir.is_dir():
        for pdf in sorted(vest_dir.rglob("*.pdf")):
            if not pdf.is_file():
                continue
            pasta = pdf.parent.relative_to(vest_dir).as_posix()
            pasta = "" if pasta == "." else pasta
            grupo = grupos.setdefault(
                pasta, {"pasta": pasta, **describe_group(pasta), "edicoes": {}}
            )

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
                "rotulo": grupo.get("rotulo", grupo["titulo"]),
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
# Regras de Nomenclatura e Salvamento
# =============================================================================
def resolve_file_destinations(
    vestibular: str,
    ano: str,
    fase: str = "1",
    serie: str = "1",
) -> dict[str, Any]:
    """Calcula a pasta de destino e os nomes padronizados de prova e gabarito."""
    vestibular_clean = vestibular.strip()
    ano_clean = str(ano).strip()
    fase_clean = str(fase).strip()
    serie_clean = str(serie).strip()

    if vestibular_clean in ("AFA", "ENEM"):
        dest_folder = MEDIA_ROOT / vestibular_clean
        prova_name = f"{vestibular_clean}_{ano_clean}.pdf"
        gabarito_name = f"{vestibular_clean}_{ano_clean}_gab.pdf"
    elif vestibular_clean in ("PROVÃO", "PROVAO"):
        dest_folder = MEDIA_ROOT / vestibular_clean / f"{serie_clean}ª Série"
        prova_name = f"PROVAO_{ano_clean}_{serie_clean}Serie.pdf"
        gabarito_name = f"PROVAO_{ano_clean}_{serie_clean}Serie_gab.pdf"
    else:
        phase_folder_name = "1ª Fase" if fase_clean == "1" else "2ª Fase"
        dest_folder = MEDIA_ROOT / vestibular_clean / phase_folder_name
        suffix = "1Fase" if fase_clean == "1" else "2Fase"

        if vestibular_clean == "USP":
            prefix = "FEVEST" if fase_clean == "1" else "FUVEST"
        else:
            prefix = vestibular_clean

        prova_name = f"{prefix}_{ano_clean}_{suffix}.pdf"
        gabarito_name = f"{prefix}_{ano_clean}_{suffix}_gab.pdf"

    return {
        "dest_folder": dest_folder.relative_to(MEDIA_ROOT).as_posix(),
        "dest_path": dest_folder,
        "prova_name": prova_name,
        "gabarito_name": gabarito_name,
    }


def save_uploaded_files(
    data: dict[str, Any], user: Any = None
) -> tuple[list[str], str]:
    """
    Grava os arquivos PDF recebidos na pasta media/ com a nomenclatura oficial,
    registra a auditoria no banco de dados e aciona indexação no motor de busca.
    """
    vestibular = data["vestibular"]
    ano = data["ano"]
    fase = data.get("fase", "1")
    serie = data.get("serie", "1")

    destinos = resolve_file_destinations(vestibular, ano, fase, serie)
    dest_path: Path = destinos["dest_path"]
    dest_path.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []

    # Prova
    prova_data = data.get("prova")
    if prova_data and isinstance(prova_data, dict) and prova_data.get("data"):
        raw_bytes = prova_data["data"]  # já decodificado pelo serializer
        target = dest_path / destinos["prova_name"]
        target.write_bytes(raw_bytes)
        caminho_rel = f"{destinos['dest_folder']}/{destinos['prova_name']}"
        saved_files.append(caminho_rel)

        RegistroUpload.objects.update_or_create(
            caminho_relativo=caminho_rel,
            defaults={
                "usuario": user if user and user.is_authenticated else None,
                "vestibular": vestibular,
                "ano": int(ano),
                "fase": fase if vestibular not in ("PROVÃO", "PROVAO") else f"{serie}ª Série",
                "nome_arquivo": destinos["prova_name"],
                "tamanho_bytes": len(raw_bytes),
            },
        )

        _index_file_safe(target)

    # Gabarito
    gab_data = data.get("gabarito")
    if gab_data and isinstance(gab_data, dict) and gab_data.get("data"):
        raw_bytes = gab_data["data"]  # já decodificado pelo serializer
        target = dest_path / destinos["gabarito_name"]
        target.write_bytes(raw_bytes)
        caminho_rel = f"{destinos['dest_folder']}/{destinos['gabarito_name']}"
        saved_files.append(caminho_rel)

        RegistroUpload.objects.update_or_create(
            caminho_relativo=caminho_rel,
            defaults={
                "usuario": user if user and user.is_authenticated else None,
                "vestibular": vestibular,
                "ano": int(ano),
                "fase": fase if vestibular not in ("PROVÃO", "PROVAO") else f"{serie}ª Série",
                "nome_arquivo": destinos["gabarito_name"],
                "tamanho_bytes": len(raw_bytes),
            },
        )

        _index_file_safe(target)

    return saved_files, destinos["dest_folder"]


def _index_file_safe(target_pdf: Path) -> None:
    """Aciona a indexação do PDF no banco de busca de forma segura."""
    try:
        from app.busca import index_single_file
        index_single_file(target_pdf, MEDIA_ROOT)
    except Exception as exc:
        logger.warning("Falha ao indexar arquivo salvo %s: %s", target_pdf.name, exc)
