from time import sleep

from django.conf import settings
from django.core.cache import caches
from django.core.management import execute_from_command_line
from django.db import OperationalError, connections

from django_docker_helpers.utils import wf, run_env_once


@run_env_once
def ensure_caches_alive(max_retries: int = 100) -> bool:
    for cache_alias in settings.CACHES.keys():
        cache = caches[cache_alias]
        wf('Checking redis connection alive for cache `%s`... ' % cache_alias, False)
        for i in range(max_retries):
            try:
                cache.set('loaded', 1)
                wf('[+]\n')
                return True
            except Exception as e:
                wf(str(e) + '\n')
                sleep(5)
        else:
            wf('Tried %s time(s). Shutting down.\n' % max_retries)
            exit()


@run_env_once
def ensure_databases_alive(max_retries: int = 100, retry_timeout: int = 5) -> bool:
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
                return True
            except OperationalError as e:
                wf(str(e))
                sleep(retry_timeout)
        else:
            wf('Tried %s time(s). Shutting down.\n' % max_retries)
            exit()


@run_env_once
def migrate() -> bool:
    wf('Applying migrations... ', False)
    execute_from_command_line(['./manage.py', 'migrate'])
    wf('[+]\n')
    return True


@run_env_once
def modeltranslation_sync_translation_fields():
    # if modeltranslation present ensure it's migrations applied too

    if 'modeltranslation' in settings.INSTALLED_APPS:
        wf('Applying translations for models... ', False)
        execute_from_command_line(['./manage.py', 'sync_translation_fields', '--noinput'])
        wf('[+]\n')
        return True
