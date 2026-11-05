"""
===============================================================================
ARQUIVO: app/models.py
CAMADA: Modelos de Dados (ORM)
PAPEL NO SISTEMA:
  - Registro de auditoria dos uploads realizados pelo usuário autenticado.
  - O catálogo de PDFs é lido dinamicamente da pasta media/, mas o histórico
    fica registrado para consulta administrativa.
===============================================================================
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class RegistroUpload(models.Model):
    """Histórico de arquivos enviados para o acervo."""

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploads",
        verbose_name="Usuário",
    )
    vestibular = models.CharField(max_length=50, verbose_name="Vestibular")
    ano = models.IntegerField(verbose_name="Ano")
    fase = models.CharField(max_length=50, blank=True, verbose_name="Fase / Série")
    nome_arquivo = models.CharField(max_length=255, verbose_name="Nome do Arquivo")
    caminho_relativo = models.CharField(
        max_length=500, unique=True, verbose_name="Caminho no Acervo"
    )
    tamanho_bytes = models.BigIntegerField(default=0, verbose_name="Tamanho (bytes)")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Data de Upload")

    class Meta:
        verbose_name = "Registro de Upload"
        verbose_name_plural = "Registros de Upload"
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"{self.nome_arquivo} ({self.vestibular} {self.ano})"

