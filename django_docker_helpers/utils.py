import importlib
import os
import sys
import typing as t
from decimal import Decimal
from functools import wraps

from dpath.util import get
from yaml import dump as dump_yaml

SHRED_DATA_FIELD_NAMES = (
    'password',
    'secret',
    'pass',
    'pwd',
    'key',
    'token',
    'auth',
    'cred',
)


def shred(key_name: str, value):
    key_name = key_name.lower()
    need_shred = False
    for data_field_name in SHRED_DATA_FIELD_NAMES:
        if data_field_name in key_name:
            need_shred = True
            break

    if not need_shred:
        return value

    return '*' * len(str(value))


def import_from(module: str, name: str):
    return getattr(
        importlib.import_module(module, [name]),
        name
    )


def dot_path(obj, path: str, default=None):
    """
    Access elements of mixed dict/object by path.
    :param obj: object or dict
    :param path: path to value
    :param default: default value if chain resolve failed
    :return: value
    """
    path_items = path.split('.')
    val = obj
    sentinel = object()
    for item in path_items:
        if isinstance(val, dict):
            val = val.get(item, sentinel)
            if val is sentinel:
                return default
        else:
            val = getattr(val, item, sentinel)
            if val is sentinel:
                return default
    return val


def dotkey(obj: dict, path: str, default=None, separator='.'):
    """
    :param obj: dict like {'some': {'value': 3}}
    :param path: 'some.value'
    :param separator: '.' | '/'
    :param default: default for KeyError
    :return: value or default value
    """
    try:
        return get(obj, path, separator=separator)
    except KeyError:
        return default


def _materialize_dict(d: t.Dict, separator: str = '.'):
    """
    Traverses and transforms a given dict into a tuples of key paths and values.
    :param d: a dict to traverse
    :param separator: build paths with given separator
    :return: yields tuple(materialized_path, value)

    >>> list(_materialize_dict({'test': {'path': 1}, 'key': 'val'}, '.'))
    >>> [('key', 'val'), ('test.path', 1)]
    """
    if not hasattr(d, 'items'):
        raise ValueError('Cannot materialize an object with no `items()`: %s' % repr(d))

    for path_prefix, v in d.items():
        if not isinstance(v, dict):
            yield str(path_prefix), v
            continue

        for nested_path, nested_val in _materialize_dict(v, separator=separator):
            yield '{0}{1}{2}'.format(path_prefix, separator, nested_path), nested_val


def materialize_dict(d: dict, separator: str = '.') -> t.List[t.Tuple[str, t.Any]]:
    """
    Transforms a given dict into a sorted list of tuples of key paths and values.
    :param d: a dict to materialize
    :param separator: build paths with given separator
    :return: a depth descending and alphabetically ascending sorted list (-deep, asc), longest first

    >>> sample = {
    >>>     'a': 1,
    >>>     'aa': 1,
    >>>     'b': {
    >>>         'c': 1,
    >>>         'b': 1,
    >>>         'a': 1,
    >>>         'aa': 1,
    >>>         'aaa': {
    >>>             'a': 1
    >>>         }
    >>>     }
    >>> }
    >>> materialize_dict(sample, '/')
    >>> [
    >>>     ('b/aaa/a', 1),
    >>>     ('b/a', 1),
    >>>     ('b/aa', 1),
    >>>     ('b/b', 1),
    >>>     ('b/c', 1),
    >>>     ('a', 1),
    >>>     ('aa', 1)
    >>> ]
    """

    def _matkeysort(tup: t.Tuple[str, t.Any]):
        return len(tup[0].split(separator))

    s1 = sorted(_materialize_dict(d, separator=separator), key=lambda x: x[0])
    return sorted(s1, key=_matkeysort, reverse=True)


def mp_serialize_dict(
        d: dict,
        separator: str = '.',
        serialize: t.Optional[t.Callable] = dump_yaml,
        value_prefix: str = '::YAML::\n') -> t.List[t.Tuple[str, bytes]]:
    """
    :param d: dict to materialize
    :param separator: build paths with given separator
    :param serialize: method to serialize non-basic types, default is yaml.dump
    :param value_prefix: prefix for non-basic serialized types
    :return: list of tuples (mat_path, b'value')
    """

    md = materialize_dict(d, separator=separator)
    res = []
    for path, value in md:
        # have to serialize values (value should be None or a string / binary data)
        if value is None:
            pass
        elif isinstance(value, str) and value != '':
            # check for value != '' used to armor empty string with forced serialization
            # since it can be not recognized by a storage backend
            pass
        elif isinstance(value, bytes):
            pass
        elif isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, (int, float, Decimal)):
            value = str(value)
        else:
            value = (value_prefix + serialize(value))

        if isinstance(value, str):
            value = value.encode()

        res.append((path, value))

    return res


def wf(raw_str, flush=True, prevent_completion_polluting=True):
    """
    :param raw_str: Raw string to print.
    :param flush: execute sys.stdout.flush
    :param prevent_completion_polluting: don't print anything
    :return:
    """
    if prevent_completion_polluting and len(sys.argv) <= 1:
        return

    sys.stdout.write(raw_str)
    flush and sys.stdout.flush()


def coerce_str_to_bool(val: t.Union[str, int, bool, None], strict: bool = False) -> bool:
    """
    :param val: ['', 0, 1, true, false, True, False]
    :param strict: raise Exception if got anything except ['', 0, 1, true, false, True, False]
    :return: True | False
    """
    if isinstance(val, bool):
        return val

    # flag is set
    if val == '':
        return True

    val = str(val).lower()

    if val in ['0', '1']:
        return bool(int(val))

    if val == 'true':
        return True

    if val == 'false':
        return False

    if strict:
        raise ValueError('Unsupported value for boolean flag: `%s`' % val)

    return bool(val)


def env_bool_flag(flag_name: str, strict: bool = False, env: t.Dict = os.environ) -> bool:
    """
    Environment boolean checker. Empty string (presence in env) is treat as True.

    :param flag_name: 'dockerized'
    :param strict: raise Exception if got anything except ['', 0, 1, true, false]
    :param env: dict-alike object, ``os.environ`` by default
    :return: True | False
    """
    sentinel = object()
    val = env.get(flag_name, sentinel)

    if val is sentinel:
        return False

    return coerce_str_to_bool(val, strict=strict)


def run_env_once(f):
    """
    ENV variables used to prevent running init code twice for manage.py command
    (https://stackoverflow.com/questions/16546652/why-does-django-run-everything-twice)
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        has_run = os.environ.get(wrapper.__name__)
        if has_run == '1':
            return
        result = f(*args, **kwargs)
        os.environ[wrapper.__name__] = '1'
        return result

    return wrapper


def is_dockerized(flag_name: str = 'DOCKERIZED', strict: bool = False):
    return env_bool_flag(flag_name, strict=strict)


def is_production(flag_name: str = 'PRODUCTION', strict: bool = False):
    return env_bool_flag(flag_name, strict=strict)
