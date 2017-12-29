import logging
import os
import typing as t

from django_docker_helpers.utils import coerce_str_to_bool


class BaseParser:
    def __init__(self,
                 scope: t.Optional[str] = None,
                 config: t.Optional[str] = None,
                 nested_delimiter: str = '__',
                 path_separator: str = '.',
                 env: t.Dict[str, str] = os.environ):
        self.config = config
        self.scope = scope
        self.nested_delimiter = nested_delimiter
        self.path_separator = path_separator
        self.env = env
        self.sentinel = object()
        self._client = None

        self.logger = logging.getLogger(self.__class__.__name__)

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):
        raise NotImplementedError

    @staticmethod
    def coerce(val: t.Any,
               coerce_type: t.Optional[t.Type] = None,
               coercer: t.Optional[t.Callable] = None):
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
        if self._client is not None:
            return self._client

        self._client = self.get_client()
        return self._client

    def get_client(self):
        raise NotImplementedError
