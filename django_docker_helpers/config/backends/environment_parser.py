import os
import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.utils import coerce_str_to_bool


class EnvironmentParser(BaseParser):
    """
    Provides a simple interface to read config options from environment variables.

    Example:
    ::

        from json import loads as json_load
        from yaml import load as yaml_load

        env = {
            'MY__VARIABLE': '33',
            'MY__NESTED__YAML__LIST__VARIABLE': '[33, 42]',
            'MY__NESTED__JSON__DICT__VARIABLE': '{"obj": true}',
        }

        parser = EnvironmentParser(env=env)
        assert p.get('my.variable') == '33'

        assert p.get('my.nested.yaml.list.variable',
                     coerce_type=list, coercer=yaml_load) == [33, 42]
        assert p.get('my.nested.json.dict.variable',
                     coerce_type=dict, coercer=json_load) == {'obj': True}

        parser = EnvironmentParser(env=env, scope='my.nested')
        assert parser.get('yaml.list.variable',
                          coerce_type=list, coercer=yaml_load) == [33, 42]
    """
    def __init__(self,
                 scope: t.Optional[str] = None,
                 config: t.Optional[str] = None,
                 nested_delimiter: str = '__',
                 path_separator: str = '.',
                 env: t.Optional[t.Dict[str, str]] = None):
        """
        :param scope: a global namespace-like variable prefix
        :param config: not used
        :param nested_delimiter: replace ``path_separator`` with an appropriate environment variable delimiter,
         default is ``__``
        :param path_separator: specifies which character separates nested variables, default is ``'.'``
        :param env: a dict with environment variables, default is ``os.environ``
        """
        env = env or os.environ
        super().__init__(
            scope=scope, config=config,
            path_separator=path_separator, nested_delimiter=nested_delimiter,
            env=env,
        )
        # config is not used in EnvironmentParser
        self.config = None
        self.scope = (scope or '').upper()

    def __str__(self):
        return '<{0} scope={1}>'.format(
            self.__class__.__name__,
            self.scope
        )

    def get_client(self):
        raise NotImplementedError

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):
        """
        Reads a value of ``variable_path`` from environment.

        If ``coerce_type`` is ``bool`` and no ``coercer`` specified, ``coerces`` forced to be
        :func:`~django_docker_helpers.utils.coerce_str_to_bool`

        :param variable_path: a delimiter-separated path to a nested value
        :param default: default value if there's no object by specified path
        :param coerce_type: cast a type of a value to a specified one
        :param coercer: perform a type casting with specified callback
        :param kwargs: additional arguments inherited parser may need
        :return: value or default
        """

        var_name = self.get_env_var_name(variable_path)
        val = self.env.get(var_name, self.sentinel)
        if val is self.sentinel:
            return default

        # coerce to bool with default env coercer if no coercer specified
        if coerce_type and coerce_type is bool and not coercer:
            coercer = coerce_str_to_bool

        return self.coerce(val, coerce_type=coerce_type, coercer=coercer)

    def get_env_var_name(self, variable_path: str) -> str:
        return self.nested_delimiter.join(
            filter(
                None,
                (self.scope or '').split(self.path_separator) +
                variable_path.upper().split(self.path_separator)
            )
        )
