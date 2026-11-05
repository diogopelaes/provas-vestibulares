from django.contrib import admin
from app.models import RegistroUpload


@admin.register(RegistroUpload)
class RegistroUploadAdmin(admin.ModelAdmin):
    list_display = (
        "nome_arquivo",
        "vestibular",
        "ano",
        "fase",
        "usuario",
        "tamanho_bytes",
        "criado_em",
    )
    list_filter = ("vestibular", "ano", "criado_em")
    search_fields = ("nome_arquivo", "caminho_relativo")
    readonly_fields = ("criado_em",)

