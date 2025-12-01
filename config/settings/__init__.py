"""
Django settings module.

By default, imports from base settings.
For production, set DJANGO_SETTINGS_MODULE=config.settings.production
"""
import os

# Determine which settings to import
env = os.getenv('DJANGO_SETTINGS_MODULE', '')

if 'production' in env.lower():
    from .production import *
else:
    from .base import *

