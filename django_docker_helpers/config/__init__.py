import inspect
import logging
import os
import typing as t

from django_docker_helpers.utils import import_from
from .backends import *

DEFAULT_PARSER_MODULE_PATH = 'django_docker_helpers.config.backends'

DEFAULT_PARSER_MODULES = (
    '{0}.EnvironmentParser'.format(DEFAULT_PARSER_MODULE_PATH),
    '{0}.MPTRedisParser'.format(DEFAULT_PARSER_MODULE_PATH),
    '{0}.MPTConsulParser'.format(DEFAULT_PARSER_MODULE_PATH),
    '{0}.RedisParser'.format(DEFAULT_PARSER_MODULE_PATH),
    '{0}.ConsulParser'.format(DEFAULT_PARSER_MODULE_PATH),
    '{0}.YamlParser'.format(DEFAULT_PARSER_MODULE_PATH),
)


def comma_str_to_list(raw_val: str) -> t.List[str]:
    return list(filter(None, raw_val.split(',')))


class ConfigLoader:
    def __init__(self, parsers: t.List[BaseParser], silent: bool = False, suppress_logs: bool = False):
        self.parsers = parsers
        self.silent = silent
        self.suppress_logs = suppress_logs
        self.sentinel = object()
        self.logger = logging.getLogger(self.__class__.__name__)

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            **kwargs):

        for p in self.parsers:
            try:
                val = p.get(
                    variable_path, default=self.sentinel,
                    coerce_type=coerce_type, coercer=coercer,
                    **kwargs
                )
                if val != self.sentinel:
                    return val
            except Exception as e:
                if not self.silent:
                    raise
                if self.suppress_logs:
                    continue
                self.logger.error('Parser {0} cannot get key `{1}`: {2}'.format(
                    p.__class__.__name__,
                    variable_path,
                    str(e)
                ))

        return default

    @staticmethod
    def import_parsers(parser_modules: t.Iterable[str]):
        for import_path in parser_modules:
            path_parts = import_path.rsplit('.', 1)
            if len(path_parts) == 2:
                mod_path, parser_class_name = path_parts
            else:
                mod_path = DEFAULT_PARSER_MODULE_PATH
                parser_class_name = import_path

            yield import_from(mod_path, parser_class_name)

    @staticmethod
    def load_parser_options_from_env(parser_class: t.Type[BaseParser],
                                     env: t.Dict[str, str] = os.environ):
        sentinel = object()
        spec: inspect.FullArgSpec = inspect.getfullargspec(parser_class.__init__)
        e = EnvironmentParser(scope=parser_class.__name__.upper(), env=env)

        stop_args = ['self']
        safe_types = [int, bool, str]

        init_args = {}

        for arg_name in spec.args:
            if arg_name in stop_args:
                continue

            type_hint = spec.annotations.get(arg_name)
            coerce_type = None

            if type_hint in safe_types:
                coerce_type = type_hint
            elif hasattr(type_hint, '__args__'):
                if len(type_hint.__args__) == 1:  # one type
                    if type_hint.__args__[0] in safe_types:
                        coerce_type = type_hint.__args__[0]
                elif len(type_hint.__args__) == 2:  # t.Optional
                    try:
                        _args = list(type_hint.__args__)
                        _args.remove(type(None))
                        if _args[0] in safe_types:
                            coerce_type = _args[0]
                    except ValueError:
                        pass

            val = e.get(arg_name, sentinel, coerce_type=coerce_type)
            if val is sentinel:
                continue

            init_args[arg_name] = val

        return init_args

    @staticmethod
    def from_env(parser_modules: t.Optional[t.Union[t.List[str], t.Tuple[str]]] = DEFAULT_PARSER_MODULES,
                 env: t.Dict[str, str] = os.environ,
                 silent: bool = False,
                 suppress_logs: bool = False,
                 extra: t.Optional[dict] = None):
        extra = extra or {}
        e = EnvironmentParser(env=env)

        env_parsers = e.get('CONFIG_PARSERS', None, coercer=comma_str_to_list)
        if not env_parsers and not parser_modules:
            raise ValueError('Must specify `CONFIG_PARSERS` env var or `parser_modules`')

        if env_parsers:
            parser_classes = ConfigLoader.import_parsers(env_parsers)
        else:
            parser_classes = ConfigLoader.import_parsers(parser_modules)

        parsers = []

        for parser_class in parser_classes:
            parser_options = ConfigLoader.load_parser_options_from_env(parser_class, env=env)

            _init_args = inspect.getfullargspec(parser_class.__init__).args
            # add extra args if parser's __init__ can take it it
            if 'env' in _init_args:
                parser_options['env'] = env

            for k, v in extra.items():
                if k in _init_args:
                    parser_options[k] = v

            parser_instance = parser_class(**parser_options)
            parsers.append(parser_instance)

        return ConfigLoader(parsers=parsers, silent=silent, suppress_logs=suppress_logs)
