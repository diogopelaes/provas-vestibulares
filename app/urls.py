"""
===============================================================================
ARQUIVO: app/urls.py
CAMADA: Roteamento da Aplicação
PAPEL NO SISTEMA:
  - Mapeia páginas HTML (index, busca, login, logout).
  - Mapeia rota de visualização inline de PDFs (/arquivos/<path>).
  - Mapeia endpoints da API REST (/api/...).
===============================================================================
"""

from django.urls import path, re_path
from app import views

urlpatterns = [
    # Páginas HTML
    path("", views.index_view, name="index"),
    path("index.html", views.index_view, name="index_html"),
    path("busca", views.busca_view, name="busca"),
    path("busca.html", views.busca_view, name="busca_html"),
    path("login/", views.login_view, name="login"),
    path("login", views.login_view, name="login_no_slash"),
    path("logout/", views.logout_view, name="logout"),
    path("logout", views.logout_view, name="logout_no_slash"),

    # Servidor de PDFs com inline streaming
    re_path(r"^arquivos/(?P<relative_path>.+)$", views.serve_pdf_view, name="serve_pdf"),

    # API Pública
    path("api/catalogo", views.CatalogoAPIView.as_view(), name="api_catalogo"),
    path("api/vestibulares", views.VestibularesAPIView.as_view(), name="api_vestibulares"),
    path("api/busca/opcoes", views.BuscaOpcoesAPIView.as_view(), name="api_busca_opcoes"),
    path("api/busca", views.BuscaAPIView.as_view(), name="api_busca"),
    path("api/auth/status", views.AuthStatusAPIView.as_view(), name="api_auth_status"),

    # API Restrita ao Usuário Autenticado
    path("api/preview", views.PreviewAPIView.as_view(), name="api_preview"),
    path("api/upload", views.UploadAPIView.as_view(), name="api_upload"),
    path("api/busca/sync", views.BuscaSyncAPIView.as_view(), name="api_busca_sync"),
]

