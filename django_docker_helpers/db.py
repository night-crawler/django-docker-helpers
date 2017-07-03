import os
from time import sleep

from django.conf import settings
from django.core.cache import caches
from django.core.management import execute_from_command_line
from django.db import OperationalError, connections

from django_docker_helpers.utils import wf


# ENV variables used to prevent running init code twice for runserver command
# (https://stackoverflow.com/questions/16546652/why-does-django-run-everything-twice)

def ensure_caches_alive(max_retries=100):
    if os.environ.get('ensure_caches_alive'):
        return
    os.environ['ensure_caches_alive'] = '1'

    for cache_alias in settings.CACHES.keys():
        cache = caches[cache_alias]
        wf('Checking redis connection alive for cache `%s`... ' % cache_alias, False)
        for i in range(max_retries):
            try:
                cache.set('loaded', 1)
                wf('[+]\n')
                break
            except Exception as e:
                wf(str(e) + '\n')
                sleep(5)
        else:
            wf('Tried %s time(s). Shutting down.\n' % max_retries)
            exit()


def ensure_databases_alive(max_retries=100):
    if os.environ.get('ensure_databases_alive'):
        return
    os.environ['ensure_databases_alive'] = '1'

    template = """
    =============================
    Checking database connection `{CONNECTION}`:
        Engine: {ENGINE}
        Host: {HOST}
        Database: {NAME}
        User: {USER}
        Password: {PASSWORD}
    =============================\n"""
    for connection_name in connections:
        _db_settings = dict.fromkeys(['ENGINE', 'HOST', 'NAME', 'USER', 'PASSWORD'])
        _db_settings.update(settings.DATABASES[connection_name])
        _db_settings['CONNECTION'] = connection_name
        if _db_settings.get('PASSWORD'):
            _db_settings['PASSWORD'] = 'set'

        wf(template.format(**_db_settings))
        wf('Checking db connection alive... ', False)

        for i in range(max_retries):
            try:
                cursor = connections[connection_name].cursor()
                cursor.execute('SELECT 1')
                cursor.fetchone()

                wf('[+]\n')
                break
            except OperationalError as e:
                wf(str(e))
                sleep(5)
        else:
            wf('Tried %s time(s). Shutting down.\n' % max_retries)
            exit()


def migrate():
    if os.environ.get('migrate'):
        return
    os.environ['migrate'] = '1'

    wf('Applying migrations... ', False)
    execute_from_command_line(['./manage.py', 'migrate'])
    wf('[DONE]\n')


def modeltranslation_sync_translation_fields():
    # if modeltranslation present ensure it's migrations applied too

    if 'modeltranslation' in settings.INSTALLED_APPS:
        wf('Applying translations for models... ', False)
        execute_from_command_line(['./manage.py', 'sync_translation_fields', '--noinput'])
        wf('[DONE]\n')
