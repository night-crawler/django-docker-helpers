import os
import typing as t

from django.core.management.base import BaseCommand

from django_docker_helpers.config import RedisParser


def write_uwsgi_ini_cfg(fp: t.IO, cfg: dict):
    """
    Writes into IO stream the uwsgi.ini file content (actually it does smth strange, just look below).

    uWSGI configs are likely to break INI (YAML, etc) specification (double key definition)
    so it writes config AS IS even without trying to fix it.

    ::
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
    help = 'Runs uWSGI with an INI config fetched from Redis'

    def add_arguments(self, parser):
        parser.add_argument(
            'key',
            help='The Redis String (data type) key, used for getting the String\'s value (YAML config)'
        )
        parser.add_argument(
            '--yml-key', default='uwsgi', dest='yml_key',
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

        # Redis's
        parser.add_argument('--host', default='localhost', dest='host', help='Redis host (default: localhost)')
        parser.add_argument('--port', default=6379, dest='port', help='Redis port (default: 6379)')
        parser.add_argument('--db', default=0, dest='db', help='Redis db (default: 0)')

    def handle(self, key, **options):
        yml_key = options['yml_key']
        cfg_file = options['file']

        parser = RedisParser(endpoint=key, host=options['host'], port=options['port'], db=options['db'])
        cfg = parser.get(yml_key)

        if options['print']:
            self.stdout.write('*' * 80 + '\n')
            self.stdout.write('uWSGI CONFIG'.center(80))
            self.stdout.write('*' * 80 + '\n')

            write_uwsgi_ini_cfg(self.stdout, cfg)

            self.stdout.write('*' * 80 + '\n')
            self.stdout.flush()

        with open(cfg_file, 'w') as file:
            write_uwsgi_ini_cfg(file, cfg)

        os.execvp('uwsgi', ('--ini', cfg_file))
