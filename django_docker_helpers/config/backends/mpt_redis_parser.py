import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.utils import default_yaml_object_deserialize


class MPTRedisParser(BaseParser):
    """
    Materialized Path Tree Redis Parser.

    Compared to, e.g. :class:`~django_docker_helpers.config.backends.redis_parser.RedisParser`
    it does not load a whole config file from a single key, but reads every config option
    from a corresponding variable path.

    Example:
    ::

        parser = MPTRedisParser(host=REDIS_HOST, port=REDIS_PORT)
        parser.get('nested.a.b')
        parser.get('debug')

    If you want to store your config with separated key paths take
    :func:`~django_docker_helpers.utils.mp_serialize_dict` helper to materialize your dict.
    """

    def __init__(self,
                 scope: t.Optional[str] = None,
                 host: str = '127.0.0.1',
                 port: int = 6379,
                 db: int = 0,
                 path_separator: str = '.',
                 key_prefix: str = '',
                 object_deserialize_prefix: str = '::YAML::\n',
                 object_deserialize: t.Optional[t.Callable] = default_yaml_object_deserialize,
                 **redis_options):
        """

        :param scope: a global namespace-like variable prefix
        :param host: redis host, default is ``'127.0.0.1'``
        :param port: redis port, default id ``6379``
        :param db: redis database, default is ``0``
        :param path_separator: specifies which character separates nested variables, default is ``'.'``
        :param key_prefix: prefix all keys with specified one
        :param object_deserialize_prefix: if object has a specified prefix, it's deserialized with
         ``object_deserialize``
        :param object_deserialize: deserializer for complex variables
        :param redis_options: additional options for ``redis.Redis`` client
        """

        super().__init__(scope=scope, path_separator=path_separator)
        self.object_serialize_prefix = object_deserialize_prefix.encode()
        self.object_deserialize = object_deserialize
        self.key_prefix = key_prefix

        self.client_options = {
            'host': host,
            'port': port,
            'db': db,
        }
        self.client_options.update(**redis_options)

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

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):
        """
        :param variable_path: a delimiter-separated path to a nested value
        :param default: default value if there's no object by specified path
        :param coerce_type: cast a type of a value to a specified one
        :param coercer: perform a type casting with specified callback
        :param kwargs: additional arguments inherited parser may need
        :return: value or default
        """

        if self.scope:
            variable_path = '{0.scope}{0.path_separator}{1}'.format(self, variable_path)

        if self.key_prefix:
            variable_path = '{0.key_prefix}:{1}'.format(self, variable_path)

        val = self.client.get(variable_path)

        if val is None:
            return default

        if val.startswith(self.object_serialize_prefix):
            # since complex data types are yaml-serialized there's no need to coerce anything
            _val = val[len(self.object_serialize_prefix):]
            bundle = self.object_deserialize(_val)
            if bundle == '':  # check for reinforced empty flag
                return self.coerce(bundle, coerce_type=coerce_type, coercer=coercer)
            return bundle

        if isinstance(val, bytes):
            val = val.decode()

        return self.coerce(val, coerce_type=coerce_type, coercer=coercer)
