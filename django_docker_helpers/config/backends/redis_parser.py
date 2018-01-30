import io
import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.config.exceptions import KVStorageValueDoestNotExist
from .yaml_parser import YamlParser


class RedisParser(BaseParser):
    def __init__(self,
                 endpoint: str = 'service',
                 host: str = '127.0.0.1',
                 port: int = 6379,
                 db: int = 0,
                 path_separator: str = '.',
                 inner_parser_class: t.Optional[t.Type[BaseParser]] = YamlParser,
                 **redis_options):

        super().__init__(path_separator=path_separator)
        self.inner_parser_class = inner_parser_class
        self.endpoint = endpoint

        self.client_options = {
            'host': host,
            'port': port,
            'db': db,
        }
        self.client_options.update(**redis_options)
        self._inner_parser = None

    def __str__(self):
        return '<{0} {1[host]}:{1[port]} db={1[db]} scope={2}>'.format(
            self.__class__.__name__,
            self.client_options,
            self.scope,
        )

    def get_client(self):
        # type: () -> redis.Redis
        import redis
        self._client = redis.Redis(**self.client_options)
        return self._client

    @property
    def inner_parser(self) -> BaseParser:
        if self._inner_parser is not None:
            return self._inner_parser

        config = self.client.get(self.endpoint)
        if not config:
            raise KVStorageValueDoestNotExist('Key `{0}` does not exist or value is empty'.format(self.endpoint))

        config = config.decode()

        self._inner_parser = self.inner_parser_class(
            config=io.StringIO(config),
            path_separator=self.path_separator,
            scope=None
        )
        return self._inner_parser

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):

        return self.inner_parser.get(
            variable_path,
            default=default,
            coerce_type=coerce_type,
            coercer=coercer,
            **kwargs,
        )
