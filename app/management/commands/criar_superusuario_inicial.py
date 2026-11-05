"""
===============================================================================
ARQUIVO: app/management/commands/criar_superusuario_inicial.py
CAMADA: Django Management Command
PAPEL NO SISTEMA:
  - Cria ou atualiza o superusuário administrador inicial de forma automatizada
    e segura, garantindo idempotência.
===============================================================================
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria ou atualiza o superusuário administrador inicial."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default="diogo")
        parser.add_argument("--email", type=str, default="diogopelaes@gmail.com")
        parser.add_argument("--password", type=str, default="123")
        parser.add_argument("--first-name", type=str, default="Diogo")
        parser.add_argument("--last-name", type=str, default="Pelaes")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        email = options["email"]
        password = options["password"]
        first_name = options["first_name"]
        last_name = options["last_name"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Superusuário '{username}' criado com sucesso!")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Superusuário '{username}' atualizado com sucesso!")
            )

