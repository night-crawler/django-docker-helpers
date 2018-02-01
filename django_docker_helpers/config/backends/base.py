import logging
import os
import typing as t

from django_docker_helpers.utils import coerce_str_to_bool


class BaseParser:
    """
    Base class to inherit from in custom parsers.
    """
    def __init__(self,
                 scope: t.Optional[str] = None,
                 config: t.Optional[str] = None,
                 nested_delimiter: str = '__',
                 path_separator: str = '.',
                 env: t.Optional[t.Dict[str, str]] = None):
        """
        All ``__init__`` arguments **MUST** be optional if you need
        :meth:`~django_docker_helpers.config.ConfigLoader.from_env`
        automatic parser initializer (it initializes parsers like ``parser_class(**parser_options)``).

        Since :class:`~django_docker_helpers.config.ConfigLoader` can initialize parsers from environment variables
        it's **recommended** to annotate argument types to provide a correct auto typecast.

        ``BaseParser`` creates a ``logger`` with name ``__class__.__name__``.

        ``BaseParser`` implements generic copying of following arguments without any backend-specific logic inside.

        :param scope: a global prefix to all underlying values
        :param config: optional config
        :param nested_delimiter: optional delimiter for environment backend
        :param path_separator: specifies which character separates nested variables, default is ``'.'``
        :param env: a dict with environment variables, default is ``os.environ``
        """

        self.config = config
        self.scope = scope
        self.nested_delimiter = nested_delimiter
        self.path_separator = path_separator
        self.env = env or os.environ
        self.sentinel = object()
        self._client = None

        self.logger = logging.getLogger(self.__class__.__name__)

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):
        """
        Inherited method should take all specified arguments.

        :param variable_path: a delimiter-separated path to a nested value
        :param default: default value if there's no object by specified path
        :param coerce_type: cast a type of a value to a specified one
        :param coercer: perform a type casting with specified callback
        :param kwargs: additional arguments inherited parser may need
        :return: value or default
        """
        raise NotImplementedError

    @staticmethod
    def coerce(val: t.Any,
               coerce_type: t.Optional[t.Type] = None,
               coercer: t.Optional[t.Callable] = None) -> t.Any:
        """
        Casts a type of ``val`` to ``coerce_type`` with ``coercer``.

        If ``coerce_type`` is bool and no ``coercer`` specified it uses
        :func:`~django_docker_helpers.utils.coerce_str_to_bool` by default.

        :param val: a value of any type
        :param coerce_type: any type
        :param coercer: provide a callback that takes ``val`` and returns a value with desired type
        :return: type casted value
        """
        if not coerce_type and not coercer:
            return val

        if coerce_type and type(val) is coerce_type:
            return val

        if coerce_type and coerce_type is bool and not coercer:
            coercer = coerce_str_to_bool

        if coercer is None:
            coercer = coerce_type

        return coercer(val)

    @property
    def client(self):
        """
        Helper property to lazy initialize and cache client. Runs
        :meth:`~django_docker_helpers.config.backends.base.BaseParser.get_client`.

        :return: an instance of backend-specific client
        """
        if self._client is not None:
            return self._client

        self._client = self.get_client()
        return self._client

    def get_client(self):
        """
        If your backend needs a client, inherit this method and use
        :meth:`~django_docker_helpers.config.backends.base.BaseParser.client` shortcut.

        :return: an instance of backend-specific client
        """
        raise NotImplementedError
