"""
===============================================================================
ARQUIVO: app/management/commands/sync_search.py
CAMADA: Django Management Command
PAPEL NO SISTEMA:
  - Comando 'python manage.py sync_search' que sincroniza os arquivos PDF
    do acervo com o banco de busca SQLite local.
===============================================================================
"""

from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from app.busca import sync_index


class Command(BaseCommand):
    help = "Sincroniza o índice de busca textual dos arquivos PDF em media/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Força reprocessamento de todos os PDFs, ignorando timestamps de cache.",
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        force = options.get("force", False)

        self.stdout.write(
            self.style.NOTICE(f"Iniciando sincronização do acervo em '{media_root}'...")
        )

        res = sync_index(root_dir=media_root, force=force)

        novos = res.get("novos_ou_atualizados", 0)
        total = res.get("total_arquivos", 0)
        tempo = res.get("tempo_s", 0)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sincronização concluída com sucesso em {tempo:.2f}s! "
                f"{novos} arquivo(s) indexado(s) de um total de {total}."
            )
        )

