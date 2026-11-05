"""
===============================================================================
ARQUIVO: app/serializers.py
CAMADA: Serialização e Validação de Dados (Django REST Framework)
PAPEL NO SISTEMA:
  - Validações de entrada para preview de upload, upload de PDFs e parâmetros de busca.
===============================================================================
"""

import base64
import re
from typing import Any
from rest_framework import serializers
from app.models import RegistroUpload


class PreviewRequestSerializer(serializers.Serializer):
    """Valida os parâmetros para pré-visualização dos caminhos de upload."""

    vestibular = serializers.CharField(max_length=50, required=True, trim_whitespace=True)
    ano = serializers.CharField(max_length=4, required=True, trim_whitespace=True)
    fase = serializers.CharField(max_length=20, default="1", required=False, trim_whitespace=True)
    serie = serializers.CharField(max_length=10, default="1", required=False, trim_whitespace=True)

    def validate_ano(self, value: str) -> str:
        if not re.fullmatch(r"\d{4}", value):
            raise serializers.ValidationError("Informe um ano com 4 dígitos numéricos.")
        ano_int = int(value)
        if ano_int < 1950 or ano_int > 2100:
            raise serializers.ValidationError("Ano fora do intervalo permitido (1950-2100).")
        return value


class DocumentoPayloadSerializer(serializers.Serializer):
    """Valida o documento PDF codificado em Base64."""

    filename = serializers.CharField(max_length=255, required=False, allow_blank=True)
    data = serializers.CharField(required=True)

    def validate_data(self, value: str) -> bytes:
        content = value
        if "," in content:
            content = content.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(content)
        except Exception as exc:
            raise serializers.ValidationError("Conteúdo Base64 inválido.") from exc

        if not raw_bytes.startswith(b"%PDF"):
            raise serializers.ValidationError("O arquivo enviado não possui cabeçalho de PDF válido (%PDF).")

        return raw_bytes


class UploadRequestSerializer(serializers.Serializer):
    """Valida a requisição completa de upload de arquivos (prova e/ou gabarito)."""

    vestibular = serializers.CharField(max_length=50, required=True, trim_whitespace=True)
    ano = serializers.CharField(max_length=4, required=True, trim_whitespace=True)
    fase = serializers.CharField(max_length=20, default="1", required=False, trim_whitespace=True)
    serie = serializers.CharField(max_length=10, default="1", required=False, trim_whitespace=True)
    prova = DocumentoPayloadSerializer(required=False, allow_null=True)
    gabarito = DocumentoPayloadSerializer(required=False, allow_null=True)

    def validate_ano(self, value: str) -> str:
        if not re.fullmatch(r"\d{4}", value):
            raise serializers.ValidationError("Informe um ano com 4 dígitos numéricos.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        prova = attrs.get("prova")
        gabarito = attrs.get("gabarito")

        has_prova = bool(prova and prova.get("data"))
        has_gabarito = bool(gabarito and gabarito.get("data"))

        if not has_prova and not has_gabarito:
            raise serializers.ValidationError(
                "Envie ao menos um documento PDF (prova ou gabarito)."
            )

        return attrs


class BuscaQuerySerializer(serializers.Serializer):
    """Valida os parâmetros de pesquisa avançada."""

    termo = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    vestibulares = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, default=list
    )
    anos = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    tipos = serializers.ListField(child=serializers.CharField(max_length=20), required=False, default=list)
    modo = serializers.ChoiceField(
        choices=["exata", "todas", "qualquer"], default="exata", required=False
    )
    sensivel_acentos = serializers.BooleanField(default=False, required=False)
    sensivel_maiusculas = serializers.BooleanField(default=False, required=False)
    palavra_inteira = serializers.BooleanField(default=False, required=False)


class RegistroUploadSerializer(serializers.ModelSerializer):
    """Serializador para visualização dos registros de upload."""

    usuario_nome = serializers.ReadOnlyField(source="usuario.username")

    class Meta:
        model = RegistroUpload
        fields = [
            "id",
            "vestibular",
            "ano",
            "fase",
            "nome_arquivo",
            "caminho_relativo",
            "tamanho_bytes",
            "usuario_nome",
            "criado_em",
        ]

