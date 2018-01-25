import typing as t

from yaml import load as yaml_load

from django_docker_helpers.config.backends.base import BaseParser


class MPTConsulParser(BaseParser):
    def __init__(self,
                 scope: t.Optional[str] = None,
                 host: str = '127.0.0.1',
                 port: int = 8500,
                 scheme: str = 'http',
                 verify: bool = True,
                 cert=None,
                 path_separator: str = '.',
                 object_deserialize_prefix: str = '::YAML::\n',
                 object_deserialize: t.Optional[t.Callable] = yaml_load):
        super().__init__(scope=scope, path_separator=path_separator)
        self.object_serialize_prefix = object_deserialize_prefix.encode()
        self.object_deserialize = object_deserialize

        self.client_options = {
            'host': host,
            'port': port,
            'scheme': scheme,
            'verify': verify,
            'cert': cert,
        }

    def __str__(self):
        return '<{0} {1[scheme]}://{1[host]}:{1[port]} scope={2}>'.format(
            self.__class__.__name__,
            self.client_options,
            self.scope,
        )

    def get_client(self):
        # type: () -> consul.Consul
        import consul
        self._client = consul.Consul(**self.client_options)
        return self._client

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):
        if self.path_separator != '/':
            variable_path = variable_path.replace(self.path_separator, '/')

        if self.scope:
            variable_path = '{0}/{1}'.format(self.scope, variable_path)

        index, data = self.client.kv.get(variable_path, **kwargs)

        if data is None:
            return default

        val = data['Value']
        if val is None:
            # None is present and it is a valid value
            return val

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
