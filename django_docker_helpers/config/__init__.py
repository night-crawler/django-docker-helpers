import inspect
import logging
import os
import textwrap
import typing as t
from collections import deque, namedtuple
from pprint import pformat

from django_docker_helpers.utils import import_from, shred, wf, run_env_once
from . import exceptions
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


ConfigReadItem = namedtuple('ConfigReadItem', ['variable_path', 'value', 'type', 'is_default', 'parser_name'])


class ConfigLoader:
    """
    - provides a single interface to read from specified config parsers in order they present;
    - tracks accessed from parsers options;
    - prints config options access log in pretty-print way.

    Example:
        ::

            env = {
                'PROJECT__DEBUG': 'false'
            }
            parsers = [
                EnvironmentParser(scope='project', env=env),
                RedisParser('my/conf/service/config.yml', host=REDIS_HOST, port=REDIS_PORT),
                YamlParser(config='./tests/data/config.yml', scope='project'),
            ]
            configure = ConfigLoader(parsers=parsers)

            DEBUG = configure('debug')  # 'false'
            DEBUG = configure('debug', coerce_type=bool)  # False
    """
    def __init__(self,
                 parsers: t.List[BaseParser],
                 silent: bool = False,
                 suppress_logs: bool = False,
                 keep_read_records_max: int = 1024):
        """
        Initialization:
            - takes a list of initialized parsers;
            - it's supposed to use ONLY unique parsers for ``parsers`` argument
              (or you are going to get the same initial arguments for all parsers of the same type in
              :meth:`~django_docker_helpers.config.ConfigLoader.from_env`);
            - the parsers's order does matter.

        :param parsers: a list of initialized parsers
        :param silent: don't raise exceptions if any read attempt failed
        :param suppress_logs: don't display any exception warnings on screen
        :param keep_read_records_max: max capacity queue length
        """
        self.parsers = parsers
        self.silent = silent
        self.suppress_logs = suppress_logs
        self.sentinel = object()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_read_queue = deque(maxlen=keep_read_records_max)

        self.colors_map = {
            'title': '\033[1;35m',

            'parser': '\033[0;33m',
            'path': '\033[94m',
            'type': '\033[1;33m',
            'value': '\033[32m',

            'reset': '\033[0m',
        }

    def enqueue(self,
                variable_path: str,
                parser: t.Optional[BaseParser] = None,
                value: t.Any = None):
        self.config_read_queue.append(ConfigReadItem(
            variable_path,
            shred(variable_path, value),
            type(value).__name__,
            not bool(parser),
            str(parser),
        ))

    def __call__(self,
                 variable_path: str,
                 default: t.Optional[t.Any] = None,
                 coerce_type: t.Optional[t.Type] = None,
                 coercer: t.Optional[t.Callable] = None,
                 required: bool = False,
                 **kwargs):
        """
        A useful shortcut for method :meth:`~django_docker_helpers.config.ConfigLoader.get`
        """
        return self.get(
            variable_path, default=default,
            coerce_type=coerce_type, coercer=coercer,
            required=required,
            **kwargs)

    def get(self,
            variable_path: str,
            default: t.Optional[t.Any] = None,
            coerce_type: t.Optional[t.Type] = None,
            coercer: t.Optional[t.Callable] = None,
            required: bool = False,
            **kwargs):
        """
        Tries to read a ``variable_path`` from each of the passed parsers.
        It stops if read was successful and returns a retrieved value.
        If none of the parsers contain a value for the specified path it returns ``default``.

        :param variable_path: a path to variable in config
        :param default: a default value if ``variable_path`` is not present anywhere
        :param coerce_type: cast a result to a specified type
        :param coercer: perform the type casting with specified callback
        :param required: raise ``RequiredValueIsEmpty`` if no ``default`` and no result
        :param kwargs: additional options to all parsers
        :return: **the first successfully read** value from the list of parser instances or ``default``

        :raises config.exceptions.RequiredValueIsEmpty: if nothing is read,``required``
         flag is set, and there's no ``default`` specified
        """

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

        if not default and required:
            raise exceptions.RequiredValueIsEmpty(
                'No default provided and no value read for `{0}`'.format(variable_path))

        return default

    @staticmethod
    def import_parsers(parser_modules: t.Iterable[str]) -> t.Generator[t.Type[BaseParser], None, None]:
        """
        Resolves and imports all modules specified in ``parser_modules``. Short names from the local scope
        are supported (the scope is ``django_docker_helpers.config.backends``).

        :param parser_modules: a list of dot-separated module paths
        :return: a generator of [probably] :class:`~django_docker_helpers.config.backends.base.BaseParser`

        Example:
        ::

            parsers = list(ConfigLoader.import_parsers([
                'EnvironmentParser',
                'django_docker_helpers.config.backends.YamlParser'
            ]))
            assert parsers == [EnvironmentParser, YamlParser]
        """
        for import_path in parser_modules:
            path_parts = import_path.rsplit('.', 1)
            if len(path_parts) == 2:
                mod_path, parser_class_name = path_parts
            else:
                mod_path = DEFAULT_PARSER_MODULE_PATH
                parser_class_name = import_path

            yield import_from(mod_path, parser_class_name)

    @staticmethod
    def load_parser_options_from_env(
            parser_class: t.Type[BaseParser],
            env: t.Optional[t.Dict[str, str]] = None) -> t.Dict[str, t.Any]:
        """
        Extracts arguments from ``parser_class.__init__`` and populates them from environment variables.

        Uses ``__init__`` argument type annotations for correct type casting.

        .. note::

            Environment variables should be prefixed with ``<UPPERCASEPARSERCLASSNAME>__``.

        :param parser_class: a subclass of :class:`~django_docker_helpers.config.backends.base.BaseParser`
        :param env: a dict with environment variables, default is ``os.environ``
        :return: parser's ``__init__`` arguments dict mapping

        Example:
        ::

            env = {
                'REDISPARSER__ENDPOINT': 'go.deep',
                'REDISPARSER__HOST': 'my-host',
                'REDISPARSER__PORT': '66',
            }

            res = ConfigLoader.load_parser_options_from_env(RedisParser, env)
            assert res == {'endpoint': 'go.deep', 'host': 'my-host', 'port': 66}
        """
        env = env or os.environ
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
                 env: t.Optional[t.Dict[str, str]] = None,
                 silent: bool = False,
                 suppress_logs: bool = False,
                 extra: t.Optional[dict] = None) -> 'ConfigLoader':
        """
        Creates an instance of :class:`~django_docker_helpers.config.ConfigLoader`
        with parsers initialized from environment variables.

        By default it tries to initialize all bundled parsers.
        Parsers may be customized with ``parser_modules`` argument or ``CONFIG__PARSERS`` environment variable.
        Environment variable has a priority over the method argument.

        :param parser_modules: a list of dot-separated module paths
        :param env: a dict with environment variables, default is ``os.environ``
        :param silent: passed to :class:`~django_docker_helpers.config.ConfigLoader`
        :param suppress_logs: passed to :class:`~django_docker_helpers.config.ConfigLoader`
        :param extra: pass extra arguments to *every* parser
        :return: an instance of :class:`~django_docker_helpers.config.ConfigLoader`

        Example:
        ::

            env = {
                'CONFIG__PARSERS': 'EnvironmentParser,RedisParser,YamlParser',
                'ENVIRONMENTPARSER__SCOPE': 'nested',
                'YAMLPARSER__CONFIG': './tests/data/config.yml',
                'REDISPARSER__HOST': 'wtf.test',
                'NESTED__VARIABLE': 'i_am_here',
            }

            loader = ConfigLoader.from_env(env=env)
            assert [type(p) for p in loader.parsers] == [EnvironmentParser, RedisParser, YamlParser]
            assert loader.get('variable') == 'i_am_here', 'Ensure env copied from ConfigLoader'

            loader = ConfigLoader.from_env(parser_modules=['EnvironmentParser'], env={})

        """
        env = env or os.environ
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

    def _colorize(self, name: str, value: str, use_color: bool = False) -> str:
        if not use_color:
            return value
        color = self.colors_map.get(name, '')
        if not color:
            return value
        reset = self.colors_map['reset']
        parts = [color + p + reset for p in str(value).split('\n')]
        return '\n'.join(parts)

    @staticmethod
    def _pformat(raw_obj: t.Union[str, t.Any], width: int = 50) -> str:
        raw_str = str(raw_obj)
        if len(raw_str) <= width:
            return raw_obj
        if isinstance(raw_obj, str):
            return '\n'.join(textwrap.wrap(raw_str, width=width))
        return pformat(raw_obj, width=width, compact=True)

    @run_env_once
    def print_config_read_queue(
            self,
            use_color: bool = False,
            max_col_width: int = 50):
        """
        Prints all read (in call order) options.

        :param max_col_width: limit column width, ``50`` by default
        :param use_color: use terminal colors
        :return: nothing
        """
        wf(self.format_config_read_queue(use_color=use_color, max_col_width=max_col_width))
        wf('\n')

    def format_config_read_queue(self,
                                 use_color: bool = False,
                                 max_col_width: int = 50) -> str:
        """
        Prepares a string with pretty printed config read queue.

        :param use_color: use terminal colors
        :param max_col_width: limit column width, ``50`` by default
        :return:
        """
        try:
            from terminaltables import SingleTable
        except ImportError:
            import warnings
            warnings.warn('Cannot display config read queue. Install terminaltables first.')
            return ''

        col_names_order = ['path', 'value', 'type', 'parser']
        pretty_bundles = [[self._colorize(name, name.capitalize(), use_color=use_color)
                           for name in col_names_order]]

        for config_read_item in self.config_read_queue:
            pretty_attrs = [
                config_read_item.variable_path,
                config_read_item.value,
                config_read_item.type,
                config_read_item.parser_name
            ]
            pretty_attrs = [self._pformat(pa, max_col_width) for pa in pretty_attrs]

            if config_read_item.is_default:
                pretty_attrs[0] = '*' + pretty_attrs[0]

            if use_color:
                pretty_attrs = [self._colorize(column_name, pretty_attr, use_color=use_color)
                                for column_name, pretty_attr in zip(col_names_order, pretty_attrs)]
            pretty_bundles.append(pretty_attrs)

        table = SingleTable(pretty_bundles)
        table.title = self._colorize('title', 'CONFIG READ QUEUE', use_color=use_color)
        table.justify_columns[0] = 'right'
        # table.inner_row_border = True
        return str(table.table)
