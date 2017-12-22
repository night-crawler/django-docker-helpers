import os
import sys
import typing as t

from functools import wraps


def dotkey(obj, dot_path: str, default=None):
    val = obj
    sentinel = object()
    if '.' not in dot_path:
        return obj.get(dot_path, default)

    for path_item in dot_path.split('.'):
        if not hasattr(val, 'get'):
            return default
        val = val.get(path_item, sentinel)
        if val is sentinel:
            return default
    return val


def get_env_var_name(project_name: str, dotpath: str) -> str:
    return '__'.join(filter(None, [project_name] + dotpath.upper().split('.')))


load_yaml_config_return_type = t.Tuple[
    dict,
    t.Callable[
        [
            str,
            t.Optional[t.Any],
            t.Optional[t.Type],
        ],
        t.Any
    ]
]


def load_yaml_config(project_name: str, filename: str) -> load_yaml_config_return_type:
    from yaml import load
    
    config_dict = load(open(filename))
    sentinel = object()

    def configure(key_name: str, default=None, coerce_type: t.Type=None) -> t.Any:
        val = os.environ.get(get_env_var_name(project_name, key_name), sentinel)
        if val is sentinel:
            val = dotkey(config_dict, key_name, sentinel)
        if val is sentinel:
            val = default

        if coerce_type is not None:
            if coerce_type == bool and not isinstance(val, bool):
                if val in ['0', '1', 0, 1]:
                    val = bool(int(val))
                elif val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
            else:
                val = coerce_type(val)

        return val

    return config_dict, configure


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


def env_bool_flag(flag_name: str, strict: bool = False) -> bool:
    """
    Environment boolean checker. Empty string (presence in env) is treat as True.

    :param flag_name: 'dockerized'
    :param strict: raise Exception if got anything except ['', 0, 1, true, false]
    :return: True | False
    """
    sentinel = object()
    val = os.environ.get(flag_name, sentinel)

    if val is sentinel:
        return False

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
        raise ValueError('Unsupported value for boolean ENV flag: `%s`' % val)

    return bool(val)


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

