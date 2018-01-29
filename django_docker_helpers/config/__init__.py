import inspect
import logging
import os
import typing as t
from collections import deque, namedtuple

from django_docker_helpers.utils import import_from, shred, wf, run_env_once
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


ConfigReadItem = namedtuple('ConfigReadItem', ['parser_name', 'variable_path', 'value', 'is_default'])


class ConfigLoader:
    def __init__(self,
                 parsers: t.List[BaseParser],
                 silent: bool = False,
                 suppress_logs: bool = False,
                 keep_read_records_max: int = 1024):
        self.parsers = parsers
        self.silent = silent
        self.suppress_logs = suppress_logs
        self.sentinel = object()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_read_queue = deque(maxlen=keep_read_records_max)

        self.colors_map = {
            'color_parser_name': '\033[0;33m',
            'color_variable_path': '\033[94m',
            'color_value': '\033[32m',
            'uncolor': '\033[0m',
        }

    # useful shortcut
    def __call__(self, variable_path: str,
                 default: t.Optional[t.Any] = None,
                 coerce_type: t.Optional[t.Type] = None,
                 coercer: t.Optional[t.Callable] = None,
                 **kwargs):
        return self.get(variable_path, default=default,
                        coerce_type=coerce_type, coercer=coercer,
                        **kwargs)

    def enqueue(self,
                variable_path: str,
                parser: t.Optional[BaseParser] = None,
                value: t.Any = None):
        self.config_read_queue.append(ConfigReadItem(
            str(parser),
            variable_path,
            shred(variable_path, value),
            not bool(parser),
        ))

    @run_env_once
    def print_config_read_queue(self, color=False):
        wf('\n'.join(self.format_config_read_queue(color=color)))
        wf('\n')

    def format_config_read_queue(self, color=False):
        screen_options = dict.fromkeys(ConfigReadItem._fields, 0)

        # find max length for every item
        for config_read_item in self.config_read_queue:
            for k, v in config_read_item._asdict().items():
                _len = len(str(v))
                if screen_options[k] < _len:
                    screen_options[k] = _len

        # add space for default asterisk sign
        screen_options['value'] += 1
        max_length = sum(screen_options.values())

        if color:
            screen_options.update(self.colors_map)
        else:
            screen_options.update(dict.fromkeys(self.colors_map.keys(), ''))

        template_parts = [
            '%(color_variable_path)s {0[variable_path]:>%(variable_path)s} %(uncolor)s',
            '=%(color_value)s {0[value]:<%(value)s} %(uncolor)s',
            '%(color_parser_name)s {0[parser_name]:<%(parser_name)s} %(uncolor)s'
        ]

        template = ''.join(template_parts) % screen_options

        res = ['CONFIG READ QUEUE'.center(max_length + 3, '=')]
        for config_read_item in self.config_read_queue:
            _option_log_item_dict = {k: str(v) for k, v in config_read_item._asdict().items()}

            if config_read_item.is_default:
                _option_log_item_dict['value'] += '*'

            res.append(template.format(_option_log_item_dict))
        res.append('=' * (max_length + 3))

        return res

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
                    self.enqueue(variable_path, p, val)
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

        self.enqueue(variable_path, value=default)
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
        environment_parser = EnvironmentParser(scope=parser_class.__name__.upper(), env=env)

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

            val = environment_parser.get(arg_name, sentinel, coerce_type=coerce_type)
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
        environment_parser = EnvironmentParser(scope='config', env=env)
        silent = environment_parser.get('silent', silent, coerce_type=bool)
        suppress_logs = environment_parser.get('suppress_logs', suppress_logs, coerce_type=bool)

        env_parsers = environment_parser.get('parsers', None, coercer=comma_str_to_list)
        if not env_parsers and not parser_modules:
            raise ValueError('Must specify `CONFIG__PARSERS` env var or `parser_modules`')

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
