"""
===============================================================================
ARQUIVO: core/middleware.py
CAMADA: Middleware HTTP
PAPEL NO SISTEMA:
  - Adiciona cabeçalhos de segurança padronizados e modernos às respostas HTTP.
  - Corrige especificamente erros de 'Unrecognized feature' no Permissions-Policy
    em navegadores modernos, garantindo apenas diretivas oficiais reconhecidas
    pelo padrão W3C (camera, microphone, geolocation, payment, usb), sem recursos
    experimentais ou depreciados como 'attribution-reporting', 'private-aggregation',
    'join-ad-interest-group', 'run-ad-auction' ou 'browsing-topics'.
===============================================================================
"""

from typing import Callable
from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware:
    """
    Middleware para garantir políticas de segurança de cabeçalho limpas,
    eliminando avisos e erros de console no navegador.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Define Permissions-Policy com recursos estritamente reconhecidos
        # evitando avisos no console sobre recursos experimentais de ad-tracking.
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )

        return response

