"""
===============================================================================
ARQUIVO: core/urls.py
CAMADA: Roteamento Principal
PAPEL NO SISTEMA:
  - URLs globais do projeto.
  - Painel administrativo (/admin/).
  - Rotas da aplicação (app.urls).
  - Em desenvolvimento (DEBUG=True), serve arquivos estáticos e de mídia.
===============================================================================
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.svg", permanent=True)),
    path("admin/", admin.site.urls),
    path("", include("app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

