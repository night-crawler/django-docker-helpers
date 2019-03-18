import typing as t

from django_docker_helpers.config.backends.base import BaseParser
from django_docker_helpers.utils import default_yaml_object_deserialize


class MPTConsulParser(BaseParser):
    """
    Materialized Path Tree Consul Parser.

    Compared to, e.g. :class:`~django_docker_helpers.config.backends.consul_parser.ConsulParser`
    it does not load a whole config file from a single key, but reads every config option
    from a corresponding variable path.

    Example:
    ::

        parser = MPTConsulParser(host=CONSUL_HOST, port=CONSUL_PORT, path_separator='.')
        parser.get('nested.a.b')

    If you want to store your config with separated key paths take
    :func:`~django_docker_helpers.utils.mp_serialize_dict` helper to materialize your dict.
    """
    def __init__(self,
                 scope: t.Optional[str] = None,
                 host: str = '127.0.0.1',
                 port: int = 8500,
                 scheme: str = 'http',
                 verify: bool = True,
                 cert=None,
                 path_separator: str = '.',
                 consul_path_separator: str = '/',
                 object_deserialize_prefix: str = '::YAML::\n',
                 object_deserialize: t.Optional[t.Callable] = default_yaml_object_deserialize):
        """
        :param scope: a global namespace-like variable prefix
        :param host: consul host, default is ``'127.0.0.1'``
        :param port: consul port, default is ``8500``
        :param scheme: consul scheme, default is ``'http'``
        :param verify: verify certs, default is ``True``
        :param cert: path to certificate bundle
        :param path_separator: specifies which character separates nested variables,
         default is ``'.'``
        :param consul_path_separator: specifies which character separates nested variables in consul kv storage,
         default is ``'/'``
        :param object_deserialize_prefix: if object has a specified prefix, it's deserialized with
         ``object_deserialize``
        :param object_deserialize: deserializer for complex variables
        """
        super().__init__(scope=scope, path_separator=path_separator)
        self.object_serialize_prefix = object_deserialize_prefix.encode()
        self.object_deserialize = object_deserialize
        self.consul_path_separator = consul_path_separator

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
        """
        :param variable_path: a delimiter-separated path to a nested value
        :param default: default value if there's no object by specified path
        :param coerce_type: cast a type of a value to a specified one
        :param coercer: perform a type casting with specified callback
        :param kwargs: additional arguments inherited parser may need
        :return: value or default
        """

        if self.path_separator != self.consul_path_separator:
            variable_path = variable_path.replace(self.path_separator, self.consul_path_separator)

        if self.scope:
            _scope = self.consul_path_separator.join(self.scope.split(self.path_separator))
            variable_path = '{0}/{1}'.format(_scope, variable_path)

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
