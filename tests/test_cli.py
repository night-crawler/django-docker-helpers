# noinspection PyPackageRequirements
import pytest

import os
from io import StringIO
from unittest import mock

from django.core.management import call_command

pytestmark = [pytest.mark.cli, pytest.mark.django]

ENDPOINT = '__DJANGO_DOCKER_HELPERS__:uwsgi-config.yml'

EXPECTED_FILE_CONTENT = """[uwsgi]
socket = 0.0.0.0:80
static-map = /test/=/application/test
static-map = /another-test/=/application/another-test
"""


@pytest.fixture
def store_redis_config():
    from redis import Redis
    from yaml import dump

    cfg = dump({
        'uwsgi': {
            'socket': '0.0.0.0:80',
            'static-map': [
                '/test/=/application/test',
                '/another-test/=/application/another-test'
            ]
        }
    }).encode()

    client = Redis(
        host=os.getenv('REDIS_HOST', '127.0.0.1'),
        port=os.getenv('REDIS_PORT', 6379)
    )
    client.set(ENDPOINT, cfg)
    yield
    client.delete(ENDPOINT)


# noinspection PyMethodMayBeStatic
@pytest.mark.django_db
class DjangoCliTest:
    def test_command_output(self, store_redis_config):
        with mock.patch(
                'django_docker_helpers.cli.django.management.commands.run_configured_uwsgi.os.execvp'
        ) as mocked__os_execvp:
            os.environ.setdefault('CONFIG__PARSERS', 'EnvironmentParser,RedisParser')
            os.environ.setdefault('REDISPARSER__ENDPOINT', ENDPOINT)

            out = StringIO()
            call_command('run_configured_uwsgi', '--print', '-f', '/tmp/__uwsgi.ini', stdout=out)

            # check output (lazy checking =)
            assert EXPECTED_FILE_CONTENT in out.getvalue()

            # check config file
            assert os.path.exists('/tmp/__uwsgi.ini')
            assert os.path.isfile('/tmp/__uwsgi.ini')
            with open('/tmp/__uwsgi.ini', 'r') as f:
                assert EXPECTED_FILE_CONTENT == f.read()

            # check os.execvp arguments
            mocked__os_execvp.assert_called_once()
            mocked__os_execvp.assert_called_once_with('uwsgi', ('--ini', '/tmp/__uwsgi.ini'))

            # NOTE: it's necessary to make environ clean
            os.environ.clear()
