import typing as t

from yaml import load as yaml_load

from django_docker_helpers.config.backends.base import BaseParser


class MPTRedisParser(BaseParser):
    def __init__(self,
                 scope: t.Optional[str] = None,
                 host: str = '127.0.0.1',
                 port: int = 6379,
                 db: int = 0,
                 path_separator: str = '.',
                 key_prefix: str = '',
                 object_deserialize_prefix: str = '::YAML::\n',
                 object_deserialize: t.Optional[t.Callable] = yaml_load,
                 **redis_options):

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
