import io
import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.config.exceptions import KVEmptyValue, KVKeyDoesNotExist
from .yaml_parser import YamlParser


class ConsulParser(BaseParser):
    def __init__(self,
                 endpoint: str = 'service',
                 host: str = '127.0.0.1',
                 port: int = 8500,
                 scheme: str = 'http',
                 verify: bool = True,
                 cert: str = None,
                 kv_get_opts: t.Optional[t.Dict] = None,

                 path_separator: str = '.',
                 inner_parser_class: t.Optional[t.Type[BaseParser]] = YamlParser):
        super().__init__(path_separator=path_separator)

        self.endpoint = endpoint

        self.client_options = {
            'host': host,
            'port': port,
            'scheme': scheme,
            'verify': verify,
            'cert': cert,
        }

        self.inner_parser_class = inner_parser_class
        self.kv_get_opts = kv_get_opts or {}

        self._inner_parser = None

    def __str__(self):
        return '<{0} {1[scheme]}://{1[host]}:{1[port]} scope={2}>'.format(
            self.__class__.__name__,
            self.client_options,
            self.scope
        )

    def get_client(self):
        # type: () -> consul.Consul
        import consul
        self._client = consul.Consul(**self.client_options)
        return self._client

    @property
    def inner_parser(self) -> BaseParser:
        if self._inner_parser is not None:
            return self._inner_parser

        __index, response_config = self.client.kv.get(self.endpoint, **self.kv_get_opts)
        if not response_config:
            raise KVKeyDoesNotExist('Key does not exist: `{0}`'.format(self.endpoint))

        config = response_config['Value']
        if not config or config is self.sentinel:
            raise KVEmptyValue('Read empty config by key `{0}`'.format(self.endpoint))

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
