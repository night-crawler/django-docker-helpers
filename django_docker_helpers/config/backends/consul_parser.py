import io
import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.config.exceptions import KVStorageKeyDoestNotExist, KVStorageValueIsEmpty

from .yaml_parser import YamlParser


class ConsulParser(BaseParser):
    """
    Reads a whole config bundle from a consul kv key and provides the unified interface to access config options.

    It assumes that config in your storage can be parsed with any simple parser, like
    :class:`~django_docker_helpers.config.backends.YamlParser`.

    Compared to, e.g. :class:`~django_docker_helpers.config.backends.environment_parser.EnvironmentParser`
    it does not have scope support by design, since ``endpoint`` is a good enough scope by itself.

    Example:
    ::

        parser = ConsulParser('my/server/config.yml', host=CONSUL_HOST, port=CONSUL_PORT)
        parser.get('nested.a.b', coerce_type=int)
    """
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
        """

        :param endpoint: specifies a key in consul kv storage, e.g. ``'services/mailer/config.yml'``
        :param host: consul host, default is ``'127.0.0.1'``
        :param port: consul port, default is ``8500``
        :param scheme: consul scheme, default is ``'http'``
        :param verify: verify certs, default is ``True``
        :param cert: path to certificate bundle
        :param kv_get_opts: read config bundle with optional arguments to ``client.kv.get()``
        :param path_separator: specifies which character separates nested variables, default is ``'.'``
        :param inner_parser_class: use the specified parser to read config from ``endpoint`` key
        """
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
        """
        Prepares inner config parser for config stored at ``endpoint``.

        :return: an instance of :class:`~django_docker_helpers.config.backends.base.BaseParser`

        :raises config.exceptions.KVStorageKeyDoestNotExist: if specified ``endpoint`` does not exists

        :raises config.exceptions.KVStorageValueIsEmpty: if specified ``endpoint`` does not contain a config
        """
        if self._inner_parser is not None:
            return self._inner_parser

        __index, response_config = self.client.kv.get(self.endpoint, **self.kv_get_opts)
        if not response_config:
            raise KVStorageKeyDoestNotExist('Key does not exist: `{0}`'.format(self.endpoint))

        config = response_config['Value']
        if not config or config is self.sentinel:
            raise KVStorageValueIsEmpty('Read empty config by key `{0}`'.format(self.endpoint))

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
        """
        Reads a value of ``variable_path`` from consul kv storage.

        :param variable_path: a delimiter-separated path to a nested value
        :param default: default value if there's no object by specified path
        :param coerce_type: cast a type of a value to a specified one
        :param coercer: perform a type casting with specified callback
        :param kwargs: additional arguments inherited parser may need
        :return: value or default

        :raises config.exceptions.KVStorageKeyDoestNotExist: if specified ``endpoint`` does not exists

        :raises config.exceptions.KVStorageValueIsEmpty: if specified ``endpoint`` does not contain a config
        """

        return self.inner_parser.get(
            variable_path,
            default=default,
            coerce_type=coerce_type,
            coercer=coercer,
            **kwargs,
        )
