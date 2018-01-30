import os

# noinspection PyPackageRequirements
import pytest
# noinspection PyPackageRequirements
from yaml import dump as yaml_dump

from django_docker_helpers.config import exceptions
from django_docker_helpers.config.backends.consul_parser import ConsulParser

pytestmark = [pytest.mark.backend, pytest.mark.consul]

CONSUL_HOST = os.getenv('CONSUL_HOST', '127.0.0.1')
CONSUL_PORT = os.getenv('CONSUL_PORT', 8500)

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
def consul_parser():
    return ConsulParser('my/server/config.yml', host=CONSUL_HOST, port=CONSUL_PORT)


@pytest.fixture
def store_consul_config():
    import consul

    c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)
    data = yaml_dump(SAMPLE, allow_unicode=True).encode()
    c.kv.put('my/server/config.yml', data)

    c.kv.put('my/server/empty.yml', None)
    return c


# noinspection PyMethodMayBeStatic,PyUnusedLocal,PyShadowingNames
class ConsulBackendTest:
    def test__consul_parser__client(self, consul_parser):
        assert consul_parser.client

    def test__consul_parser__inner_parser(self, store_consul_config, consul_parser):
        assert consul_parser.client
        assert consul_parser.inner_parser

    def test__consul_parser__configs_equal(self, store_consul_config, consul_parser):
        assert consul_parser.inner_parser.data == SAMPLE

    def test__consul_parser__inner_parser__exceptions(self, store_consul_config):
        with pytest.raises(exceptions.KVStorageKeyDoestNotExist):
            c = ConsulParser('nothing/here', host=CONSUL_HOST, port=CONSUL_PORT)
            assert c.inner_parser

        with pytest.raises(exceptions.KVStorageValueDoestNotExist):
            c = ConsulParser('my/server/empty.yml', host=CONSUL_HOST, port=CONSUL_PORT)
            assert c.inner_parser

    def test__consul_parser__get(self, store_consul_config, consul_parser: ConsulParser):
        assert consul_parser.get('nested.a.b', coerce_type=int) == 2
        assert consul_parser.get('nested.a') == {'b': 2}
        assert consul_parser.get('nested.nothing', default='qwe') == 'qwe'

