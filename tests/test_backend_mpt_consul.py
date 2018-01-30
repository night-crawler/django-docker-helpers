import os

# noinspection PyPackageRequirements
import pytest

from django_docker_helpers.config.backends.mpt_consul_parser import MPTConsulParser
from django_docker_helpers.utils import mp_serialize_dict

pytestmark = [pytest.mark.backend, pytest.mark.consul]

CONSUL_HOST = os.getenv('CONSUL_HOST', '127.0.0.1')
CONSUL_PORT = os.getenv('CONSUL_PORT', 8500)


@pytest.fixture
def store_consul_config():
    import consul
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
    c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)
    for path, value in mp_serialize_dict(sample, separator='/'):
        c.kv.put(path, value)


# noinspection PyMethodMayBeStatic,PyUnusedLocal,PyShadowingNames
class MPTConsulBackendTest:
    def test__mpt_consul_parser__get(self, store_consul_config):
        p = MPTConsulParser(host=CONSUL_HOST, port=CONSUL_PORT, path_separator='.')
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

    def test__mpt_consul_parser__scope(self, store_consul_config):
        p = MPTConsulParser(host=CONSUL_HOST, port=CONSUL_PORT, scope='nested', path_separator='.')
        assert p.get('a.b') == '2'
