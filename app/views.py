"""
===============================================================================
ARQUIVO: app/views.py
CAMADA: Views e Endpoints HTTP / API (Django & Django REST Framework)
PAPEL NO SISTEMA:
  - Páginas HTML com cache-busting dinâmico (index, busca, login, logout).
  - API pública (catálogo, vestibulares, busca no conteúdo dos PDFs).
  - API restrita ao usuário autenticado (preview, upload, sincronização do acervo).
  - Servidor de PDF inline com streaming.
===============================================================================
"""

import logging
import mimetypes
import urllib.parse
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.busca import buscar, get_opcoes_busca, sync_index
from app.serializers import (
    BuscaQuerySerializer,
    PreviewRequestSerializer,
    UploadRequestSerializer,
)
from app.services import (
    build_catalog,
    get_vestibulares,
    render_with_asset_versions,
    resolve_file_destinations,
    save_uploaded_files,
)

logger = logging.getLogger("VestibularesViews")
MEDIA_ROOT: Path = Path(settings.MEDIA_ROOT)


# =============================================================================
# Views HTML (Templates)
# =============================================================================
def index_view(request: HttpRequest) -> HttpResponse:
    """Renderiza a página inicial (biblioteca de provas) com cache busting."""
    html_content = render_with_asset_versions(
        "index.html", request, {"user": request.user}
    )
    response = HttpResponse(html_content, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def busca_view(request: HttpRequest) -> HttpResponse:
    """Renderiza a página de busca avançada nos PDFs com cache busting."""
    html_content = render_with_asset_versions(
        "busca.html", request, {"user": request.user}
    )
    response = HttpResponse(html_content, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def login_view(request: HttpRequest) -> HttpResponse:
    """Página de autenticação do usuário para liberação do upload."""
    if request.user.is_authenticated:
        return redirect("/")

    error_msg = None
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next") or "/"
            return redirect(next_url)
        error_msg = "Usuário ou senha incorretos."
    else:
        form = AuthenticationForm()

    html_content = render_with_asset_versions(
        "login.html", request, {"form": form, "error_msg": error_msg}
    )
    return HttpResponse(html_content, content_type="text/html; charset=utf-8")


def logout_view(request: HttpRequest) -> HttpResponse:
    """Encerra a sessão do usuário e retorna à página principal."""
    logout(request)
    return redirect("/")


# =============================================================================
# Visualização Inline de PDFs (Compatibilidade /arquivos/<path>)
# =============================================================================
def serve_pdf_view(request: HttpRequest, relative_path: str) -> HttpResponse:
    """
    Serve PDFs do acervo para abertura inline na aba do navegador.
    Garante que o caminho permaneça estritamente contido em MEDIA_ROOT.
    """
    unquoted = urllib.parse.unquote(relative_path).lstrip("/\\")
    target_path = (MEDIA_ROOT / unquoted).resolve()

    if not target_path.is_relative_to(MEDIA_ROOT.resolve()) or not target_path.is_file():
        raise Http404("PDF não encontrado.")

    if target_path.suffix.lower() != ".pdf":
        return HttpResponse("Acesso negado: tipo de arquivo não permitido.", status=403)

    filename_quoted = urllib.parse.quote(target_path.name)
    response = FileResponse(
        target_path.open("rb"),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f"inline; filename*=UTF-8''{filename_quoted}"
    response["Cache-Control"] = "no-cache, must-revalidate"
    return response


# =============================================================================
# API Pública (Leitura de Catálogo e Busca)
# =============================================================================
class CatalogoAPIView(APIView):
    """Retorna o catálogo completo do acervo agrupado por vestibular, fase e edição."""

    permission_classes = [AllowAny]

    def get(self, request: HttpRequest) -> Response:
        data = build_catalog()
        return Response(data)


class VestibularesAPIView(APIView):
    """Retorna a lista de vestibulares disponíveis."""

    permission_classes = [AllowAny]

    def get(self, request: HttpRequest) -> Response:
        vestibulares = get_vestibulares()
        return Response({"vestibulares": vestibulares})


class BuscaOpcoesAPIView(APIView):
    """Retorna os vestibulares, anos e status do índice para preenchimento dos filtros."""

    permission_classes = [AllowAny]

    def get(self, request: HttpRequest) -> Response:
        try:
            opcoes = get_opcoes_busca(MEDIA_ROOT)
            return Response(opcoes)
        except Exception as exc:
            logger.error("Erro ao carregar opções de busca: %s", exc)
            return Response(
                {"error": f"Erro ao obter opções de busca: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BuscaAPIView(APIView):
    """
    Executa busca textual de termos nos PDFs indexados.
    Suporta GET (query string) e POST (payload JSON).
    """

    permission_classes = [AllowAny]

    def get(self, request: HttpRequest) -> Response:
        # Extrai parâmetros da query string
        data = {
            "termo": request.query_params.get("termo", ""),
            "vestibulares": request.query_params.getlist("vestibulares"),
            "anos": [
                int(a)
                for a in request.query_params.getlist("anos")
                if a.isdigit()
            ],
            "tipos": request.query_params.getlist("tipos"),
            "modo": request.query_params.get("modo", "exata"),
            "sensivel_acentos": request.query_params.get(
                "sensivel_acentos", "false"
            ).lower()
            in ("true", "1"),
            "sensivel_maiusculas": request.query_params.get(
                "sensivel_maiusculas", "false"
            ).lower()
            in ("true", "1"),
            "palavra_inteira": request.query_params.get(
                "palavra_inteira", "false"
            ).lower()
            in ("true", "1"),
        }
        return self._process_search(data)

    def post(self, request: HttpRequest) -> Response:
        return self._process_search(request.data)

    def _process_search(self, raw_data: dict[str, Any]) -> Response:
        serializer = BuscaQuerySerializer(data=raw_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        params = serializer.validated_data
        termo = params.get("termo", "")
        resultado = buscar(termo, params, root_dir=MEDIA_ROOT)
        return Response(resultado)


class AuthStatusAPIView(APIView):
    """Informa ao frontend se o usuário atual está autenticado."""

    permission_classes = [AllowAny]

    def get(self, request: HttpRequest) -> Response:
        return Response(
            {
                "authenticated": request.user.is_authenticated,
                "username": request.user.username if request.user.is_authenticated else None,
            }
        )


# =============================================================================
# API Restrita (Usuário Autenticado)
# =============================================================================
class PreviewAPIView(APIView):
    """Calcula os nomes e pasta padronizados de destino antes do envio."""

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest) -> Response:
        serializer = PreviewRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        if data["vestibular"] not in get_vestibulares():
            return Response(
                {"error": f"Vestibular '{data['vestibular']}' não encontrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        destino = resolve_file_destinations(
            data["vestibular"],
            data["ano"],
            data.get("fase", "1"),
            data.get("serie", "1"),
        )
        return Response(
            {
                "dest_folder": destino["dest_folder"],
                "prova_name": destino["prova_name"],
                "gabarito_name": destino["gabarito_name"],
            }
        )


class UploadAPIView(APIView):
    """
    Recebe os documentos PDF em Base64, salva no diretório media/ com a
    nomenclatura padrão, grava o log de auditoria e aciona a indexação.
    Acesso restrito ao usuário autenticado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest) -> Response:
        serializer = UploadRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        if data["vestibular"] not in get_vestibulares():
            return Response(
                {"error": f"Vestibular '{data['vestibular']}' não encontrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            saved_files, dest_folder = save_uploaded_files(
                data, user=request.user
            )
            return Response(
                {
                    "success": True,
                    "message": "Arquivos salvos e indexados com sucesso!",
                    "saved_files": saved_files,
                    "dest_folder": dest_folder,
                },
                status=status.HTTP_200_OK,
            )
        except OSError as exc:
            logger.error("Erro ao salvar arquivos de upload: %s", exc)
            return Response(
                {"error": f"Erro no sistema de arquivos: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BuscaSyncAPIView(APIView):
    """
    Sincroniza e reindexa os arquivos PDF do acervo no banco de busca.
    Acesso restrito ao usuário autenticado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest) -> Response:
        try:
            resultado = sync_index(root_dir=MEDIA_ROOT)
            return Response(resultado)
        except Exception as exc:
            logger.error("Erro na sincronização manual do índice: %s", exc)
            return Response(
                {"error": f"Erro ao sincronizar índice: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

