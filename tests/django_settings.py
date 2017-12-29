import os

DEBUG = True

SECRET_KEY = 'lol'

STATIC_URL = '/static/'
STATIC_ROOT = './static/'

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'tests.test_app',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'tests/test.sqlite',
    }
}

MEMCACHED_HOST = os.getenv('MEMCACHED_HOST', '127.0.0.1')
MEMCACHED_PORT = os.getenv('MEMCACHED_HOST', '11211')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '{0}:{1}'.format(MEMCACHED_HOST, MEMCACHED_PORT),
    }
}

CONFIG = {
    'superuser': {
        'username': 'admin',
        'email': 'admin@example.com',
        'password': 'r00t',
    }
}
