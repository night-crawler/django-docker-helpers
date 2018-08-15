import io
import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.config.exceptions import KVStorageValueIsEmpty

from .yaml_parser import YamlParser


class RedisParser(BaseParser):
    """
    Reads a whole config bundle from a redis key and provides the unified interface to access config options.

    It assumes that config in your storage can be parsed with any simple parser, like
    :class:`~django_docker_helpers.config.backends.YamlParser`.

    Compared to, e.g. :class:`~django_docker_helpers.config.backends.environment_parser.EnvironmentParser`
    it does not have scope support by design, since ``endpoint`` is a good enough scope by itself.

    Example:
    ::

        parser = RedisParser('my/server/config.yml', host=REDIS_HOST, port=REDIS_PORT)
        parser.get('nested.a.b', coerce_type=int)

    """
    def __init__(self,
                 endpoint: str = 'service',
                 host: str = '127.0.0.1',
                 port: int = 6379,
                 db: int = 0,
                 path_separator: str = '.',
                 inner_parser_class: t.Optional[t.Type[BaseParser]] = YamlParser,
                 **redis_options):
        """

        :param endpoint: specifies a redis key with serialized config, e.g. ``'services/mailer/config.yml'``
        :param host: redis host, default is ``'127.0.0.1'``
        :param port: redis port, default id ``6379``
        :param db: redis database, default is ``0``
        :param path_separator: specifies which character separates nested variables, default is ``'.'``
        :param inner_parser_class: use the specified parser to read config from ``endpoint`` key
        :param redis_options: additional options for ``redis.Redis`` client
        """

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
        """
        Prepares inner config parser for config stored at ``endpoint``.

        :return: an instance of :class:`~django_docker_helpers.config.backends.base.BaseParser`

        :raises config.exceptions.KVStorageValueIsEmpty: if specified ``endpoint`` does not contain a config
        """
        if self._inner_parser is not None:
            return self._inner_parser

        config = self.client.get(self.endpoint)
        if not config:
            raise KVStorageValueIsEmpty('Key `{0}` does not exist or value is empty'.format(self.endpoint))

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
        Reads a value of ``variable_path`` from redis storage.

        :param variable_path: a delimiter-separated path to a nested value
        :param default: default value if there's no object by specified path
        :param coerce_type: cast a type of a value to a specified one
        :param coercer: perform a type casting with specified callback
        :param kwargs: additional arguments inherited parser may need
        :return: value or default

        :raises config.exceptions.KVStorageValueIsEmpty: if specified ``endpoint`` does not contain a config
        """

        return self.inner_parser.get(
            variable_path,
            default=default,
            coerce_type=coerce_type,
            coercer=coercer,
            **kwargs,
        )
