import os

import pytest
from yaml import dump as yaml_dump

from django_docker_helpers.config import exceptions
from django_docker_helpers.config.backends.redis_parser import RedisParser

REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)

SAMPLE = {
    'bool_flag': '',  # flag
    'unicode': 'вася',
    'none_value': None,
    'debug': True,
    'mixed': ['ascii', 'юникод', 1, {'d': 1}, {'b': 2}],
    'nested': {
        'a': {
            'b': 2
        }
    }
}


@pytest.fixture
def redis_parser():
    return RedisParser('my/server/config.yml', host=REDIS_HOST, port=REDIS_PORT)


@pytest.fixture
def store_redis_config():
    import redis

    c = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    data = yaml_dump(SAMPLE, allow_unicode=True).encode()
    c.set('my/server/config.yml', data)
    c.set('my/server/empty.yml', '')
    return c


# noinspection PyMethodMayBeStatic,PyShadowingNames,PyUnusedLocal
class RedisBackendTest:
    def test__redis_parser__client(self, redis_parser: RedisParser):
        assert redis_parser.client

    def test__redis_parser__inner_parser(self, store_redis_config, redis_parser: RedisParser):
        assert redis_parser.client
        assert redis_parser.inner_parser

    def test__redis_parser__inner_parser__exceptions(self, store_redis_config):
        with pytest.raises(exceptions.KVEmptyValue):
            c = RedisParser('nothing/here', host=REDIS_HOST, port=REDIS_PORT)
            assert c.inner_parser

        with pytest.raises(exceptions.KVEmptyValue):
            c = RedisParser('my/server/empty.yml', host=REDIS_HOST, port=REDIS_PORT)
            assert c.inner_parser

    def test__redis_parser__configs_equal(self, store_redis_config, redis_parser):
        assert redis_parser.inner_parser
        assert redis_parser.inner_parser.data == SAMPLE
