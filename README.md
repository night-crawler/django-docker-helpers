# django-docker-helpers
[![Docs](https://readthedocs.org/projects/django-docker-helpers/badge/?style=flat)](https://readthedocs.org/projects/django-docker-helpers/)
[![Coverage](https://codecov.io/gh/night-crawler/django-docker-helpers/branch/master/graph/badge.svg)](https://codecov.io/gh/night-crawler/django-docker-helpers)
[![Build status](https://travis-ci.org/night-crawler/django-docker-helpers.svg?branch=master)](https://travis-ci.org/night-crawler/django-docker-helpers)
[![PyPI version](https://img.shields.io/pypi/v/django-docker-helpers.svg)](https://pypi.python.org/pypi/django-docker-helpers)
[![PyPI Wheel](https://img.shields.io/pypi/wheel/django-docker-helpers.svg)](https://pypi.python.org/pypi/django-docker-helpers)
[![Requirements Status](https://requires.io/github/night-crawler/django-docker-helpers/requirements.svg?branch=master)](https://requires.io/github/night-crawler/django-docker-helpers/requirements/?branch=master)
[![Supported versions](https://img.shields.io/pypi/pyversions/django-docker-helpers.svg)](https://pypi.python.org/pypi/django-docker-helpers)
[![Supported implementations](https://img.shields.io/pypi/implementation/django-docker-helpers.svg)](https://pypi.python.org/pypi/django-docker-helpers)

This package provides some useful tools you can use with your `manage.py`, 
so you have no need to use bash entry points and non-python scripting. 
As well it:
 - reads configs with typing support from env, yaml, redis, consul;
 - provides some helper functions

## Installation
```bash
pip install -e git+https://github.com/night-crawler/django-docker-helpers.git#egg=django-docker-helpers
    # OR
pip install django-docker-helpers
```

### Utils
- `env_bool_flag(flag_name, strict)` - check if ENV option specified, is it set to true, 1, 0, etc.
- `run_env_once` ensure django management don't call `twice <https://stackoverflow.com/questions/16546652/why-does-django-run-everything-twice>`_
- `is_dockerized` - reads `DOCKERIZED` flag from env
- `is_production` - reads `PRODUCTION` flag from env


### Management Helper functions
- `ensure_databases_alive(max_retries=100)` - tries to execute `SELECT 1` for every specified database alias in `DATABASES` until success or max_retries reached
- `ensure_caches_alive(max_retries=100)` - tries to execute `SELECT 1` for every specified cache alias in `CACHES` until success or max_retries reached
- `migrate` - executes `./manage.py migrate`
- `modeltranslation_sync_translation_fields` - run `sync_translation_fields` if `modeltranslation` is present
- `collect_static` - alias for `./manage.py collectstatic -c --noinput -v0`
- `create_admin` - create superuser from `settings.CONFIG['superuser']` if user does not exists and user has no usable password
- `run_gunicorn(application: WSGIHandler, gunicorn_module_name: str='gunicorn_prod')` - runs gunicorn


### Sample config
```yaml
debug: true
    db:
        engine: django.db.backends.postgresql
        host: postgres
        port: 5432
        database: mydb
        user: mydb_user
        password: mydb_password
        conn_max_age: 60
```

### Read config
```python
import os
from django_docker_helpers.config import ConfigLoader, EnvironmentParser, RedisParser, YamlParser

yml_conf = '/tmp/my/config/without-docker.yml'
redis_conf = os.environ.get('DJANGO_CONFIG_REDIS_KEY', 'msa_cas/conf.yml')

parsers = [
    EnvironmentParser(),
    RedisParser(endpoint=redis_conf),
    YamlParser(config=yml_conf),
]
configure = ConfigLoader(parsers=parsers, silent=True)



DATABASES = {
    'default': {
        'ENGINE': configure('db.name', 'django.db.backends.postgresql'),
        'HOST': configure('db.host', 'localhost'),
        'PORT': configure('db.port', 5432),
        'NAME': configure('db.database', 'project_default'),
        'USER': configure('db.user', 'project_default'),
        'PASSWORD': configure('db.password', 'project_default'),
        'CONN_MAX_AGE': configure('db.conn_max_age', 60, coerce_type=int),
    }
}
```    

### Usage

In the most cases your manage.py may look like:

```python
#!/usr/bin/env python
#!/usr/bin/env python
import os
import sys

from django_docker_helpers.db import (
    ensure_caches_alive, ensure_databases_alive, migrate
)
from django_docker_helpers.files import collect_static
from django_docker_helpers.management import create_admin, run_gunicorn
from django_docker_helpers.utils import env_bool_flag, run_env_once, wf

from setproctitle import setproctitle


@run_env_once
def invalidate_static_rev():
    from django.core.management import call_command
    call_command('invalidate_static_rev')


@run_env_once
def load_lang_fixtures():
    from django.core.management import call_command
    call_command('populate_languages')


@run_env_once
def load_dev_fixtures():
    from django.core.management import call_command

    wf('Loading DEVELOPMENT fixtures... ', False)
    call_command(
        'loaddata',
        'fixtures/dev/service_api__api_key.json'
    )
    wf('[DONE]\n')


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_project.settings')

    setproctitle('MyProject')

    if env_bool_flag('CHECK_CONNECTIONS'):
        ensure_databases_alive(100)
        ensure_caches_alive(100)

    if env_bool_flag('RUN_PREPARE'):
        collect_static()
        migrate()
        invalidate_static_rev()
        load_lang_fixtures()
        create_admin('SUPERUSER')

    if env_bool_flag('LOAD_DEV_FIXTURES'):
        load_dev_fixtures()

    if len(sys.argv) == 2:
        if sys.argv[1] == 'rungunicorn':
            from my_project.wsgi import application

            gunicorn_module_name = os.getenv('GUNICORN_MODULE_NAME', 'gunicorn_dev')
            run_gunicorn(application, gunicorn_module_name=gunicorn_module_name)
            exit()

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


```

### Testing
1. `$ pip install -r requirements/dev.txt`
2. [Download Consul](https://www.consul.io/downloads.html) and unzip it into the project's directory.
    - `CONSUL_VERSION=1.4.0 bash -c 'curl -sLo consul.zip https://releases.hashicorp.com/consul/"$CONSUL_VERSION"/consul_"$CONSUL_VERSION"_linux_amd64.zip' && unzip consul.zip`
3. `$ ./consul agent -server -ui -dev`
4. `$ pytest`
