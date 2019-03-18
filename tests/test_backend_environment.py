# noinspection PyPackageRequirements
import pytest

from json import loads as json_load

from django_docker_helpers.config.backends.environment_parser import EnvironmentParser

pytestmark = [pytest.mark.backend, pytest.mark.env]


def yaml_load_safe(stream):
    from yaml import load, SafeLoader
    return load(stream, SafeLoader)


# noinspection PyMethodMayBeStatic
class EnvironmentBackendTest:
    def test__get_env_var_name(self):
        parser = EnvironmentParser('project')
        assert parser.get_env_var_name('my.nested.variable') == 'PROJECT__MY__NESTED__VARIABLE'
        parser = EnvironmentParser()
        assert parser.get_env_var_name('my.nested.variable') == 'MY__NESTED__VARIABLE'
        parser = EnvironmentParser(nested_delimiter='_NOPLEASE_')
        assert parser.get_env_var_name('my.nested.variable') == 'MY_NOPLEASE_NESTED_NOPLEASE_VARIABLE'

        parser = EnvironmentParser('my.long.project')
        assert parser.get_env_var_name('variable') == 'MY__LONG__PROJECT__VARIABLE'

    def test__get(self):
        env = {
            'MY__VARIABLE': '33',
            'MY__NESTED__YAML__LIST__VARIABLE': '[33, 42]',
            'MY__NESTED__JSON__LIST__VARIABLE': '["33", 42]',
            'MY__NESTED__JSON__DICT__VARIABLE': '{"obj": true}',
            'MY_STR_BOOL_TRUE': 'true',
            'MY_STR_BOOL_FALSE': 'false',
            'MY_INT_BOOL_TRUE': '1',
            'MY_INT_BOOL_False': '0',
        }
        parser = EnvironmentParser(env=env)
        assert parser.get('my.variable') == '33', 'Ensure return the same value if no coercing'
        assert parser.get('my.variable', coerce_type=str) == '33', 'Ensure str coercing'
        assert parser.get('my.variable', coerce_type=int) == 33, 'Ensure int coercing'

        # test complex types
        parser = EnvironmentParser(env=env)
        assert parser.get('my.nested.yaml.list.variable', coerce_type=list, coercer=yaml_load_safe) == [33, 42]
        assert parser.get('my.nested.json.list.variable', coerce_type=list, coercer=json_load) == ['33', 42]

        assert parser.get('my.nested.json.dict.variable', coerce_type=dict, coercer=json_load) == {'obj': True}
        assert parser.get('my.nested.json.dict.variable', coercer=json_load) == {'obj': True}
        assert parser.get('my.nested.json.dict.variable', coercer=json_load, coerce_type=dict) == {'obj': True}

        # test dot-separated scope
        parser = EnvironmentParser(env=env, scope='my.nested')
        assert parser.get('yaml.list.variable', coerce_type=list, coercer=yaml_load_safe) == [33, 42]

    def test__path_separator(self):
        _env = {
            'MY__VARIABLE': '33',
        }
        p = EnvironmentParser(env=_env, path_separator='/')
        assert p.get('my/variable', coerce_type=int) == 33

    def test__get__bool_coercing(self):
        _env = {
            'MY_STR_BOOL_TRUE': 'true',
            'MY_STR_BOOL_FALSE': 'false',
            'MY_INT_BOOL_TRUE': '1',
            'MY_INT_BOOL_FALSE': '0',
        }
        p = EnvironmentParser(env=_env)

        assert p.get('my_str_bool_true', coerce_type=bool) is True
        assert p.get('my_str_bool_false', coerce_type=bool) is False

        assert p.get('my_int_bool_true', coerce_type=bool) is True
        assert p.get('my_int_bool_false', coerce_type=bool) is False

    def test__get_client__raises(self):
        p = EnvironmentParser(env={}, path_separator='/')
        with pytest.raises(NotImplementedError):
            p.get_client()
