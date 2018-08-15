import collections
import importlib
import os
import sys
import typing as t
from decimal import Decimal
from functools import wraps

from dpath.util import get
from yaml import dump as dump_yaml

ENV_STR_BOOL_COERCE_MAP = {
    '': True,  # Flag is set

    0: False,
    '0': False,
    'false': False,
    'off': False,

    1: True,
    '1': True,
    'true': True,
    'on': True,
}

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


def shred(key_name: str,
          value: t.Any,
          field_names: t.Iterable[str] = SHRED_DATA_FIELD_NAMES) -> t.Union[t.Any, str]:
    """
    Replaces sensitive data in ``value`` with ``*`` if ``key_name`` contains something that looks like a secret.

    :param field_names: a list of key names that can possibly contain sensitive data
    :param key_name: a key name to check
    :param value: a value to mask
    :return: an unchanged value if nothing to hide, ``'*' * len(str(value))`` otherwise
    """
    key_name = key_name.lower()
    need_shred = False
    for data_field_name in field_names:
        if data_field_name in key_name:
            need_shred = True
            break

    if not need_shred:
        return value

    return '*' * len(str(value))


def shred_deep(value, field_names: t.Iterable[str] = SHRED_DATA_FIELD_NAMES):
    if not value:
        return value

    if not isinstance(value, collections.Iterable) or isinstance(value, str):
        return value

    if isinstance(value, dict):
        _value = {}
        for k, v in value.items():
            if isinstance(v, collections.Iterable) and not isinstance(v, str):
                _value[k] = shred_deep(v, field_names=field_names)
            else:
                _value[k] = shred(k, v, field_names=field_names)
        return _value

    _value = [shred_deep(v, field_names=field_names) for v in value]
    return type(value)(_value)


def import_from(module: str, name: str):
    return getattr(
        importlib.import_module(module, [name]),
        name
    )


def dot_path(obj: t.Union[t.Dict, object],
             path: str,
             default: t.Any = None,
             separator: str = '.'):
    """
    Provides an access to elements of a mixed dict/object type by a delimiter-separated path.
    ::

        class O1:
            my_dict = {'a': {'b': 1}}

        class O2:
            def __init__(self):
                self.nested = O1()

        class O3:
            final = O2()

        o = O3()
        assert utils.dot_path(o, 'final.nested.my_dict.a.b') == 1

    .. testoutput::

        True

    :param obj: object or dict
    :param path: path to value
    :param default: default value if chain resolve failed
    :param separator: ``.`` by default
    :return: value or default
    """
    path_items = path.split(separator)
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
    Provides an interface to traverse nested dict values by dot-separated paths. Wrapper for ``dpath.util.get``.

    :param obj: dict like ``{'some': {'value': 3}}``
    :param path: ``'some.value'``
    :param separator: ``'.'`` or ``'/'`` or whatever
    :param default: default for KeyError
    :return: dict value or default value
    """
    try:
        return get(obj, path, separator=separator)
    except KeyError:
        return default


def _materialize_dict(bundle: dict, separator: str = '.') -> t.Generator[t.Tuple[str, t.Any], None, None]:
    """
    Traverses and transforms a given dict ``bundle`` into tuples of ``(key_path, value)``.

    :param bundle: a dict to traverse
    :param separator: build paths with a given separator
    :return: a generator of tuples ``(materialized_path, value)``

    Example:
    >>> list(_materialize_dict({'test': {'path': 1}, 'key': 'val'}, '.'))
    >>> [('key', 'val'), ('test.path', 1)]
    """
    for path_prefix, v in bundle.items():
        if not isinstance(v, dict):
            yield str(path_prefix), v
            continue

        for nested_path, nested_val in _materialize_dict(v, separator=separator):
            yield '{0}{1}{2}'.format(path_prefix, separator, nested_path), nested_val


def materialize_dict(bundle: dict, separator: str = '.') -> t.List[t.Tuple[str, t.Any]]:
    """
    Transforms a given ``bundle`` into a *sorted* list of tuples with materialized value paths and values:
    ``('path.to.value', <value>)``. Output is ordered by depth: the deepest element first.

    :param bundle: a dict to materialize
    :param separator: build paths with a given separator
    :return: a depth descending and alphabetically ascending sorted list (-deep, asc), the longest first

    ::

        sample = {
            'a': 1,
            'aa': 1,
            'b': {
                'c': 1,
                'b': 1,
                'a': 1,
                'aa': 1,
                'aaa': {
                    'a': 1
                }
            }
        }
        materialize_dict(sample, '/')
        [
            ('b/aaa/a', 1),
            ('b/a', 1),
            ('b/aa', 1),
            ('b/b', 1),
            ('b/c', 1),
            ('a', 1),
            ('aa', 1)
        ]
    """

    def _matkeysort(tup: t.Tuple[str, t.Any]):
        return len(tup[0].split(separator))

    s1 = sorted(_materialize_dict(bundle, separator=separator), key=lambda x: x[0])
    return sorted(s1, key=_matkeysort, reverse=True)


def mp_serialize_dict(
        bundle: dict,
        separator: str = '.',
        serialize: t.Optional[t.Callable] = dump_yaml,
        value_prefix: str = '::YAML::\n') -> t.List[t.Tuple[str, bytes]]:
    """
    Transforms a given ``bundle`` into a *sorted* list of tuples with materialized value paths and values:
    ``('path.to.value', b'<some>')``. If the ``<some>`` value is not an instance of a basic type, it's serialized
    with ``serialize`` callback. If this value is an empty string, it's serialized anyway to enforce correct
    type if storage backend does not support saving empty strings.

    :param bundle: a dict to materialize
    :param separator: build paths with a given separator
    :param serialize: a method to serialize non-basic types, default is ``yaml.dump``
    :param value_prefix: a prefix for non-basic serialized types
    :return: a list of tuples ``(mat_path, b'value')``

    ::

        sample = {
            'bool_flag': '',  # flag
            'unicode': 'вася',
            'none_value': None,
            'debug': True,
            'mixed': ['ascii', 'юникод', 1, {'d': 1}, {'b': 2}],
            'nested': {
                'a': {
                    'b': 2,
                    'c': b'bytes',
                }
            }
        }

        result = mp_serialize_dict(sample, separator='/')
        assert result == [
            ('nested/a/b', b'2'),
            ('nested/a/c', b'bytes'),
            ('bool_flag', b"::YAML::\\n''\\n"),
            ('debug', b'true'),
            ('mixed', b'::YAML::\\n- ascii\\n- '
                      b'"\\\\u044E\\\\u043D\\\\u0438\\\\u043A\\\\u043E\\\\u0434"\\n- 1\\n- '
                      b'{d: 1}\\n- {b: 2}\\n'),
            ('none_value', None),
            ('unicode', b'\\xd0\\xb2\\xd0\\xb0\\xd1\\x81\\xd1\\x8f')
        ]
    """

    md = materialize_dict(bundle, separator=separator)
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


def wf(raw_str: str,
       flush: bool = True,
       prevent_completion_polluting: bool = True,
       stream: t.TextIO = sys.stdout):
    """
    Writes a given ``raw_str`` into a ``stream``. Ignores output if ``prevent_completion_polluting`` is set and there's
    no extra ``sys.argv`` arguments present (a bash completion issue).

    :param raw_str: a raw string to print
    :param flush: execute ``flush()``
    :param prevent_completion_polluting: don't write anything if ``len(sys.argv) <= 1``
    :param stream: ``sys.stdout`` by default
    :return: None
    """
    if prevent_completion_polluting and len(sys.argv) <= 1:
        return

    stream.write(raw_str)
    flush and hasattr(stream, 'flush') and stream.flush()


def coerce_str_to_bool(val: t.Union[str, int, bool, None], strict: bool = False) -> bool:
    """
    Converts a given string ``val`` into a boolean.

    :param val: any string representation of boolean
    :param strict: raise ``ValueError`` if ``val`` does not look like a boolean-like object
    :return: ``True`` if ``val`` is thruthy, ``False`` otherwise.

    :raises ValueError: if ``strict`` specified and ``val`` got anything except
     ``['', 0, 1, true, false, on, off, True, False]``
    """
    if isinstance(val, str):
        val = val.lower()

    flag = ENV_STR_BOOL_COERCE_MAP.get(val, None)

    if flag is not None:
        return flag

    if strict:
        raise ValueError('Unsupported value for boolean flag: `%s`' % val)

    return bool(val)


def env_bool_flag(flag_name: str, strict: bool = False, env: t.Optional[t.Dict[str, str]] = None) -> bool:
    """
    Converts an environment variable into a boolean. Empty string (presence in env) is treated as ``True``.

    :param flag_name: an environment variable name
    :param strict: raise ``ValueError`` if a ``flag_name`` value connot be coerced into a boolean in obvious way
    :param env: a dict with environment variables, default is ``os.environ``
    :return: ``True`` if ``flag_name`` is thruthy, ``False`` otherwise.

    :raises ValueError: if ``strict`` specified and ``val`` got anything except ``['', 0, 1, true, false, True, False]``
    """
    env = env or os.environ
    sentinel = object()
    val = env.get(flag_name, sentinel)

    if val is sentinel:
        return False

    return coerce_str_to_bool(val, strict=strict)


def run_env_once(f: t.Callable) -> t.Callable:
    """
    A decorator to prevent ``manage.py`` from running code twice for everything.
    (https://stackoverflow.com/questions/16546652/why-does-django-run-everything-twice)

    :param f: function or method to decorate
    :return: callable
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
    """
    Reads env ``DOCKERIZED`` variable as a boolean.

    :param flag_name: environment variable name
    :param strict: raise a ``ValueError`` if variable does not look like a normal boolean
    :return: ``True`` if has truthy ``DOCKERIZED`` env, ``False`` otherwise
    """
    return env_bool_flag(flag_name, strict=strict)


def is_production(flag_name: str = 'PRODUCTION', strict: bool = False):
    """
    Reads env ``PRODUCTION`` variable as a boolean.

    :param flag_name: environment variable name
    :param strict: raise a ``ValueError`` if variable does not look like a normal boolean
    :return: ``True`` if has truthy ``PRODUCTION`` env, ``False`` otherwise
    """
    return env_bool_flag(flag_name, strict=strict)
