import os
import typing as t

from django.core.management.base import BaseCommand

from django_docker_helpers.config import ConfigLoader


def write_uwsgi_ini_cfg(fp: t.IO, cfg: dict):
    """
    Writes into IO stream the uwsgi.ini file content (actually it does smth strange, just look below).

    uWSGI configs are likely to break INI (YAML, etc) specification (double key definition)
    so it writes `cfg` object (dict) in "uWSGI Style".

    >>> import sys
    >>> cfg = {
    ... 'static-map': [
    ... '/static/=/application/static/',
    ... '/media/=/application/media/',
    ... '/usermedia/=/application/usermedia/']
    ... }
    >>> write_uwsgi_ini_cfg(sys.stdout, cfg)
    [uwsgi]
    static-map = /static/=/application/static/
    static-map = /media/=/application/media/
    static-map = /usermedia/=/application/usermedia/
    """
    fp.write(f'[uwsgi]\n')

    for key, val in cfg.items():
        if isinstance(val, bool):
            val = str(val).lower()

        if isinstance(val, list):
            for v in val:
                fp.write(f'{key} = {v}\n')
            continue

        fp.write(f'{key} = {val}\n')


class Command(BaseCommand):
    help = 'Runs uWSGI with an INI config fetched from ConfigLoader'

    def add_arguments(self, parser):
        parser.add_argument(
            '--key', default='uwsgi', dest='key',
            help='The YAML configuration key with which uWSGI config can be accessed (default: uwsgi)'
        )
        parser.add_argument(
            '--print', action='store_true', dest='print',
            help='If true the ini file content will be outputted'
        )
        parser.add_argument(
            '-f', '--file', default='/tmp/uwsgi.ini', dest='file',
            help='Specifies a file that will be used for config storing'
        )

    def handle(self, **options):
        key = options['key']

        configure = ConfigLoader.from_env(suppress_logs=True, silent=True)
        uwsgi_cfg = configure.get(key)

        if not uwsgi_cfg:
            self.stderr.write(f'Parsing error: uWSGI config was not found by the key "{key}"')
            return

        if options['print']:
            self.stdout.write('*' * 80 + '\n')
            self.stdout.write('uWSGI CONFIG'.center(80))
            self.stdout.write('*' * 80 + '\n')

            write_uwsgi_ini_cfg(self.stdout, uwsgi_cfg)

            self.stdout.write('*' * 80 + '\n')
            self.stdout.flush()

        cfg_file = options['file']
        with open(cfg_file, 'w') as file:
            write_uwsgi_ini_cfg(file, uwsgi_cfg)

        os.execvp('uwsgi', ('--ini', cfg_file))
