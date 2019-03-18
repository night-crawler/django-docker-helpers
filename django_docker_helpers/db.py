from time import sleep

from django.conf import settings
from django.core.cache import caches
from django.core.management import execute_from_command_line
from django.db import OperationalError, connections

from django_docker_helpers.utils import run_env_once, wf


@run_env_once
def ensure_caches_alive(max_retries: int = 100,
                        retry_timeout: int = 5,
                        exit_on_failure: bool = True) -> bool:
    """
    Checks every cache backend alias in ``settings.CACHES`` until it becomes available. After ``max_retries``
    attempts to reach any backend are failed it returns ``False``. If ``exit_on_failure`` is set it shuts down with
    ``exit(1)``.

    It sets the ``django-docker-helpers:available-check`` key for every cache backend to ensure
    it's receiving connections. If check is passed the key is deleted.

    :param exit_on_failure: set to ``True`` if there's no sense to continue
    :param int max_retries: a number of attempts to reach cache backend, default is ``100``
    :param int retry_timeout: a timeout in seconds between attempts, default is ``5``
    :return: ``True`` if all backends are available ``False`` if any backend check failed
    """
    for cache_alias in settings.CACHES.keys():
        cache = caches[cache_alias]
        wf('Checking if the cache backed is accessible for the alias `%s`... ' % cache_alias, False)
        for i in range(max_retries):
            try:
                cache.set('django-docker-helpers:available-check', '1')
                assert cache.get('django-docker-helpers:available-check') == '1'
                cache.delete('django-docker-helpers:available-check')
                wf('[+]\n')
                break
            except Exception as e:
                wf(str(e) + '\n')
                sleep(retry_timeout)
        else:
            wf('Tried %s time(s). Shutting down.\n' % max_retries)
            exit_on_failure and exit(1)
            return False
    return True


@run_env_once
def ensure_databases_alive(max_retries: int = 100,
                           retry_timeout: int = 5,
                           exit_on_failure: bool = True) -> bool:
    """
    Checks every database alias in ``settings.DATABASES`` until it becomes available. After ``max_retries``
    attempts to reach any backend are failed it returns ``False``. If ``exit_on_failure`` is set it shuts down with
    ``exit(1)``.

    For every database alias it tries to ``SELECT 1``. If no errors raised it checks the next alias.

    :param exit_on_failure: set to ``True`` if there's no sense to continue
    :param int max_retries: number of attempts to reach every database; default is ``100``
    :param int retry_timeout: timeout in seconds between attempts
    :return: ``True`` if all backends are available, ``False`` if any backend check failed
    """
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
                sleep(retry_timeout)
        else:
            wf('Tried %s time(s). Shutting down.\n' % max_retries)
            exit_on_failure and exit(1)
            return False
    return True


@run_env_once
def migrate(*argv) -> bool:
    """
    Runs Django migrate command.

    :return: always ``True``
    """
    wf('Applying migrations... ', False)
    execute_from_command_line(['./manage.py', 'migrate'] + list(argv))
    wf('[+]\n')
    return True


@run_env_once
def modeltranslation_sync_translation_fields() -> bool:
    """
    Runs ``modeltranslation``'s ``sync_translation_fields`` manage.py command:
    ``execute_from_command_line(['./manage.py', 'sync_translation_fields', '--noinput'])``

    :return: ``None`` if modeltranslation is not specified is ``INSTALLED_APPS``, ``True`` if all synced.
    """
    # if modeltranslation present ensure it's migrations applied too

    if 'modeltranslation' in settings.INSTALLED_APPS:
        wf('Applying translations for models... ', False)
        execute_from_command_line(['./manage.py', 'sync_translation_fields', '--noinput'])
        wf('[+]\n')
        return True
