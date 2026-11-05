"""
===============================================================================
ARQUIVO: core/settings.py
CAMADA: Configuração Geral do Projeto Django
PAPEL NO SISTEMA:
  - Configurações do Django 5/6 para o Acervo de Provas de Vestibulares.
  - Compatível com VPS (Caddy + Gunicorn) e ambiente de desenvolvimento local.
  - Carrega variáveis de ambiente de .env se existir.
===============================================================================
"""

import os
from pathlib import Path

# Caminhos base
BASE_DIR = Path(__file__).resolve().parent.parent

# Carregamento simplificado de variáveis de ambiente do .env
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.is_file():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))

# Segurança
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-provas-vestibulares-dev-key-change-in-prod"
)
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "t", "yes")

allowed_hosts_str = os.environ.get(
    "ALLOWED_HOSTS", "acervo.diogo.mat.br,localhost,127.0.0.1,testserver"
)
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]

csrf_origins_str = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "https://acervo.diogo.mat.br,http://localhost:8000,http://127.0.0.1:8000",
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins_str.split(",") if o.strip()]

# Aplicações instaladas
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceiros
    "rest_framework",
    # Módulo do acervo
    "app.apps.AppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "app" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Banco de dados (SQLite local por padrão, compatível com zero complexidade)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Validação de senhas
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internacionalização
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Arquivos estáticos (CSS, JavaScript, Imagens)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "app" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Arquivos de mídia (PDFs do acervo organizados dentro de media/)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# Autenticação e Redirecionamentos
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
