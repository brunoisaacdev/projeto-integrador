import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_env_file(path):
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    else:
        load_dotenv(path)


load_env_file(BASE_DIR / ".env")


def env_list(name, default=()):
    value = os.getenv(name)
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
<<<<<<< HEAD
    os.getenv("SECRET_KEY", "django-insecure-+-zi*qdy6vy2!1#gf^nj(&8vdfh%wfv-=zr99xe(+(8)%3zk3h"),
)

DEBUG = env_bool("DEBUG", default=not env_bool("VERCEL"))
=======
    "django-insecure-+-zi*qdy6vy2!1#gf^nj(&8vdfh%wfv-=zr99xe(+(8)%3zk3h",
)

DEBUG = os.getenv("DEBUG", "False").lower() in {"1", "true", "yes", "on"}
>>>>>>> d452c60e595773391001bcbcf7337ef93e02ac83

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "testserver",
<<<<<<< HEAD
    ".vercel.app",
    *env_list("ALLOWED_HOSTS"),
]

CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.app",
    *env_list("CSRF_TRUSTED_ORIGINS"),
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
=======
    "projeto-integrador-t5bm.vercel.app",
    ".vercel.app",
]

CSRF_TRUSTED_ORIGINS = [
    "https://projeto-integrador-t5bm.vercel.app",
    "https://*.vercel.app",
]
>>>>>>> d452c60e595773391001bcbcf7337ef93e02ac83



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.ControleAcessoMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'setup.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'setup.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        },
    },
]

AUTHENTICATION_BACKENDS = [
    'core.backends.EmailOuTelefoneBackend',
]


LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "Premium Barbearia <no-reply@premiumbarbearia.com>",
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
