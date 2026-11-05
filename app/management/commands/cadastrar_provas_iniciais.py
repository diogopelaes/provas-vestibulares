"""
===============================================================================
ARQUIVO: app/management/commands/cadastrar_provas_iniciais.py
CAMADA: Django Management Command
PAPEL NO SISTEMA:
  - Varre todos os PDFs existentes na pasta media/ e cadastra no modelo
    RegistroUpload, associando ao superusuário administrador.
  - Totalmente idempotente: utiliza get_or_create para garantir que NENHUMA
    duplicata seja inserida no banco de dados.
===============================================================================
"""

from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from app.models import RegistroUpload
from app.services import classify_file, describe_group


class Command(BaseCommand):
    help = "Cadastra no banco de dados todos os PDFs já existentes em media/ sem gerar duplicatas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default="diogo",
            help="Nome de usuário a ser associado aos registros (padrão: diogo).",
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        username = options.get("username", "diogo")

        User = get_user_model()
        user = User.objects.filter(username=username).first()

        self.stdout.write(
            self.style.NOTICE(f"Iniciando cadastro do acervo de '{media_root}' para o usuário '{username}'...")
        )

        all_pdfs = sorted(media_root.rglob("*.pdf"))
        if not all_pdfs:
            self.stdout.write(self.style.WARNING("Nenhum arquivo PDF encontrado em media/."))
            return

        criados = 0
        ja_existentes = 0

        for pdf in all_pdfs:
            if not pdf.is_file():
                continue

            rel_path = pdf.relative_to(media_root).as_posix()
            parts = rel_path.split("/")
            vestibular = parts[0]

            # Pasta intermediária (ex: 1ª Fase, 2ª Série)
            pasta_grupo = "/".join(parts[1:-1]) if len(parts) > 2 else ""
            info_grupo = describe_group(pasta_grupo)
            fase_str = info_grupo.get("rotulo", "")

            _, ano, _, _ = classify_file(pdf)
            tamanho_bytes = pdf.stat().st_size

            _, created = RegistroUpload.objects.get_or_create(
                caminho_relativo=rel_path,
                defaults={
                    "usuario": user,
                    "vestibular": vestibular,
                    "ano": ano,
                    "fase": fase_str,
                    "nome_arquivo": pdf.name,
                    "tamanho_bytes": tamanho_bytes,
                },
            )

            if created:
                criados += 1
            else:
                ja_existentes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Cadastro concluído! Total de PDFs analisados: {len(all_pdfs)}. "
                f"Novos cadastros: {criados}. Já existentes (sem duplicatas): {ja_existentes}."
            )
        )

