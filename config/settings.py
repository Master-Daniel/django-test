"""
Django settings for route fuel API project.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Max vehicle range (miles)
VEHICLE_RANGE_MILES = 500
# Refuel before hitting empty (miles before range limit)
REFUEL_AT_MILES = 400
# MPG
MILES_PER_GALLON = 10
# OSRM base URL (public demo server)
OSRM_BASE_URL = 'https://router.project-osrm.org'
# Fuel prices CSV path (relative to BASE_DIR)
FUEL_PRICES_CSV = BASE_DIR / 'data' / 'fuel-prices-for-be-assessment.csv'
