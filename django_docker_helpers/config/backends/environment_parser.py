import os
import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.utils import coerce_str_to_bool


class EnvironmentParser(BaseParser):
    def __init__(self,
                 scope: t.Optional[str] = None,
                 config: t.Optional[str] = None,
                 nested_delimiter: str = '__',
                 path_separator: str = '.',
                 env: t.Dict[str, str] = os.environ):
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
                [self.scope] + variable_path.upper().split(self.path_separator)
            )
        )
