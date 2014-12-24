"""
Django settings for caobserver project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os, os.path
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

def genkey():
    alpha = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    import random
    G = random.SystemRandom()
    return ''.join([G.choice(alpha) for i in range(50)])

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = None
try:
    with open(os.path.join(BASE_DIR, 'secret.txt'), 'r') as F:
        SECRET_KEY = F.read().strip()
except:
    print 'Failed to load secret key, generating a new one'
    SECRET_KEY = genkey()
    with open(os.path.join(BASE_DIR, 'secret.txt'), 'w') as F:
        F.write(SECRET_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    #'django.contrib.admin',
    #'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.messages',
    'django.contrib.staticfiles',
    'careport',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'careport.middle.MongoMiddle',
)

ROOT_URLCONF = 'caobserver.urls'

WSGI_APPLICATION = 'caobserver.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

MONGODB = 'caspy'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Eastern'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DNS_CACHE_EXPIRE = 5*60

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'topstatic')

STATICFILES_DIRS = (
    ('jquery', '/usr/share/javascript/jquery'),
)
