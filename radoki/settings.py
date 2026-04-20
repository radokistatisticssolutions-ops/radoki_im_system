"""
Django settings for radoki project.
"""

import environ
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='change-me-in-production-please')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

# Production security settings
if not DEBUG:
    # Security settings for production
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1', 'radoki-im-system.onrender.com']
)

# CSRF trusted origins for development and production
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        'https://localhost:8000',
        'https://radoki-im-system.onrender.com',
        'https://*.ngrok-free.dev',
        'https://*.ngrok.app',
    ]
)

# Keep CSRF cookie alive for 1 year (default) and session for 2 weeks (default).
CSRF_COOKIE_AGE = 31449600  # 1 year in seconds
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',
    'cloudinary_storage',
    # Local apps
    'accounts',
    'courses',
    'payments',
    'dashboard',
    'core',
    'assignments',
    'notifications',
    'referrals',
    'mathfilters',
    'quizzes',
    'attendance',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'radoki.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'radoki.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'builtins': [
                'core.templatetags.admin_pagination_tags',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'radoki.wsgi.application'

# Database Configuration
# Production: Use Neon PostgreSQL or other production database
# Development: Use SQLite or local PostgreSQL
if 'DATABASE_URL' in os.environ and os.environ.get('DATABASE_URL'):
    # Production database (Neon, RDS, etc.)
    DATABASES = {
        'default': env.db('DATABASE_URL')
    }
else:
    # Development fallback - SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Cloudinary Configuration for Media Files
# Only configure if Cloudinary credentials are provided
CLOUDINARY_CLOUD_NAME = env('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = env('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = env('CLOUDINARY_API_SECRET', default='')

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    # Production: Use Cloudinary for media files
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
        import cloudinary_storage  # Ensure cloudinary_storage is imported

        # Set CLOUDINARY_URL environment variable for cloudinary_storage
        os.environ.setdefault(
            'CLOUDINARY_URL',
            f'cloudinary://{CLOUDINARY_API_KEY}:{CLOUDINARY_API_SECRET}@{CLOUDINARY_CLOUD_NAME}'
        )

        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET
        )

        # Use Cloudinary for media storage
        DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
        CLOUDINARY_STORAGE = {
            'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
            'API_KEY': CLOUDINARY_API_KEY,
            'API_SECRET': CLOUDINARY_API_SECRET,
        }
        # Cloudinary media URL - use 'upload' delivery for all file types
        MEDIA_URL = f'https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/'
    except ImportError:
        # Fallback if cloudinary is not installed
        print("Warning: Cloudinary packages not installed. Using local media storage.")
        MEDIA_URL = '/media/'
        MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
else:
    # Development: Use local media storage
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Dar_es_Salaam'
USE_I18N = True
USE_TZ = True

STATIC_URL = env('STATIC_URL', default='/static/')
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Static files storage - WhiteNoise for production
# Use explicit safe defaults so collectstatic succeeds in Render build.
STATICFILES_STORAGE = env(
    'STATICFILES_STORAGE',
    default='whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
)

LOGIN_REDIRECT_URL = '/redirect-after-login/'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Configuration
# Force console backend for local development (when not in production)
# Check if we're in production by looking for RENDER env var or specific production indicators
IS_PRODUCTION = bool(
    os.environ.get('RENDER') or  # Render deployment
    os.environ.get('PRODUCTION') or  # Explicit production flag
    (os.environ.get('DATABASE_URL') and not os.environ.get('LOCAL_DEV'))  # Has DB URL but not local dev flag
)

if not IS_PRODUCTION:
    # Local development - emails go to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    DEFAULT_FROM_EMAIL = 'test@localhost'
    print("📧 Using CONSOLE email backend for local development")
else:
    # Production - use SMTP with environment variables
    EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = env('EMAIL_PORT', default=587)
    EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
    EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@localhost')
    print("📧 Using SMTP email backend for production")
# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
