"""
Django production settings for config project.
"""
import os
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Ensure SECRET_KEY is set in production
if SECRET_KEY == 'django-insecure-fallback-key-change-this':
    raise ValueError("SECRET_KEY must be set in production environment!")

# Parse ALLOWED_HOSTS from environment variable
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be set in production environment!")

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS Settings (uncomment when SSL is configured)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000  # 1 year
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# PostgreSQL Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', ''),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Validate database settings
if not DATABASES['default']['NAME'] or not DATABASES['default']['USER']:
    raise ValueError("DB_NAME and DB_USER must be set in production environment!")

# Static files configuration for production
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Use WhiteNoise for static files serving (if installed)
# Add 'whitenoise.middleware.WhiteNoiseMiddleware' to MIDDLEWARE if using WhiteNoise
# MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email Configuration for Production
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@timertracker.com')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'django_logs.log' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Cache Configuration (optional, for performance)
# Uncomment and configure if you want to use caching
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#     }
# }

# Session Configuration
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

