import os
import sys
import typing as t

from yaml import load


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


def get_env_var(project_name: str, dotpath: str) -> str:
    return '__'.join([project_name] + dotpath.upper().split('.'))


def load_yaml_config(project_name: str, filename: str) -> t.Tuple[dict, t.Callable]:
    config_dict = load(open(filename))
    sentinel = object()

    def configure(key_name: str, default=None):
        val = os.environ.get(get_env_var(project_name, key_name), sentinel)
        if val is sentinel:
            val = dotkey(config_dict, key_name, sentinel)
        if val is sentinel:
            val = default
        return val

    return config_dict, configure


def wf(s, flush=True):
    sys.stdout.write(s)
    flush and sys.stdout.flush()
