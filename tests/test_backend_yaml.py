# noinspection PyPackageRequirements
import pytest

from django_docker_helpers.config.backends.yaml_parser import YamlParser

pytestmark = [pytest.mark.backend, pytest.mark.yaml]


# noinspection PyMethodMayBeStatic
class YamlBackendTest:
    def test__yaml_parser__init(self):
        # no config
        with pytest.raises(ValueError):
            YamlParser()

        p = YamlParser('./tests/data/config.yml')
        assert isinstance(p.data, dict)

    def test__yaml_parser__get(self):
        p = YamlParser('./tests/data/config.yml')
        assert p.get('debug') is True
        assert p.get('my.deep.nested.variable') == 1
        assert p.get('my.deep.nested.variable', coerce_type=str) == '1'

        assert p.get('my.deep.nested', coerce_type=dict) == {'variable': 1}

        assert p.get('hosts', coerce_type=list) == ['localhost', '127.0.0.1']

    def test__yaml_parser__scope(self):
        p = YamlParser('./tests/data/config.yml', scope='development')
        assert p.get('up.down.above') == [1, 2, 3]

    def test__yaml_parser__do_not_coerce_default_values(self):
        p = YamlParser('./tests/data/config.yml')
        o = object()
        assert p.get('does.not.exist', default=o, coerce_type=int) == o

    def test__yaml_parser__path_separator(self):
        p = YamlParser('./tests/data/config.yml', scope='development', path_separator='/')
        assert p.get('up/down/above') == [1, 2, 3]

    def test__get_client__raises(self):
        p = YamlParser('./tests/data/config.yml', scope='development', path_separator='/')
        with pytest.raises(NotImplementedError):
            p.get_client()
