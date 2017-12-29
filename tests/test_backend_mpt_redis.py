import os

import pytest

from django_docker_helpers.config.backends.mpt_redis_parser import MPTRedisParser
from django_docker_helpers.utils import mp_serialize_dict

REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)


@pytest.fixture
def store_redis_config():
    import redis
    sample = {
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
    c = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    for path, value in mp_serialize_dict(sample, separator='.'):
        c.set(path, value)
        c.set('my-prefix:%s' % path, value)


# noinspection PyShadowingNames,PyMethodMayBeStatic,PyUnusedLocal
class MPTRedisBackendTest:
    def test__mpt_redis__init(self):
        MPTRedisParser(host=REDIS_HOST, port=REDIS_PORT)

    def test__mpt_redis__read(self, store_redis_config):
        p = MPTRedisParser(host=REDIS_HOST, port=REDIS_PORT)
        assert p.get('nested.a.b') == '2', 'Ensure value is a valid string if no coercers present'
        assert p.get('debug') == 'true', 'Ensure value is a valid string if no coercers present'

        # consul-python treats b'' as None, so we need to armor it in serializer
        assert p.get('bool_flag') == '', 'Ensure value is a valid string if no coercers present'
        assert p.get('bool_flag', coerce_type=bool) is True, 'Ensure value treated as True since it is a flag'

        assert p.get('nested.a.b', coerce_type=int) == 2, 'Ensure coercing works for simple types'
        assert p.get('debug', coerce_type=bool) is True, 'Ensure boolean works'

        assert p.get('unicode') == 'вася', 'Ensure unicode works fine'
        assert p.get('nested') is None, 'Ensure nested values are not returned'
        assert p.get('mixed') == ['ascii', 'юникод', 1, {'d': 1}, {'b': 2}]

    def test__mpt_redis__scope(self, store_redis_config):
        p = MPTRedisParser(host=REDIS_HOST, port=REDIS_PORT, scope='nested', path_separator='.')
        assert p.get('a.b') == '2'
        assert p.get('a.b', coerce_type=int) == 2

    def test__mpt_redis__key_prefix(self):
        p = MPTRedisParser(host=REDIS_HOST, port=REDIS_PORT, scope='nested', path_separator='.', key_prefix='my-prefix')
        assert p.get('a.b') == '2'
        assert p.get('a.b', coerce_type=int) == 2

