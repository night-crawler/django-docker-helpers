import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.utils import dotkey


class YamlParser(BaseParser):
    def __init__(self,
                 config: t.Optional[t.Union[str, t.TextIO]] = None,
                 path_separator: str = '.',
                 scope: t.Optional[str] = None):
        super().__init__(scope=scope, config=config, path_separator=path_separator)

        self._data = None

        if not config:
            raise ValueError('Config should not be empty')

    def __str__(self):
        return '<{0} config="{1}" scope={2}>'.format(
            self.__class__.__name__,
            self.config if isinstance(self.config, str) else 'TextIO',
            self.scope,
        )

    @property
    def data(self):
        if self._data is not None:
            return self._data

        from yaml import load

        if isinstance(self.config, str):
            config = open(self.config)
        else:
            config = self.config

        self._data = load(config)
        return self._data

    def get_client(self):
        raise NotImplementedError

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):

        if self.scope:
            variable_path = '{0.scope}{0.path_separator}{1}'.format(self, variable_path)

        val = dotkey(self.data, variable_path, default=default, separator=self.path_separator)

        if default and val is default:
            return val

        return self.coerce(val, coerce_type=coerce_type, coercer=coercer)
