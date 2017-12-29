## Installation
```bash
pip install -e git+https://github.com/night-crawler/django-docker-helpers.git#egg=django-docker-helpers
    # OR
pip install django-docker-helpers
```

### Utils
- `load_yaml_config(project_name: str, filename: str)` - loads config from specified YAML file. Returns dict bundle from YAML and `configure(key, default, coerce)` function to get config vars from YAML or ENV
- `env_bool_flag(flag_name, strict)` - check if ENV option specified, is it set to true, 1, 0, etc.
- `run_env_once` ensure django management don't call `twice <https://stackoverflow.com/questions/16546652/why-does-django-run-everything-twice>`_
- `is_dockerized` - reads `DOCKERIZED` flag from env
- `is_production` - reads `PRODUCTION` flag from env


### Helper functions
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
from django_docker_helpers.utils import load_yaml_config

CONFIG, configure = load_yaml_config(
    '',  # prefix
    os.path.join(
        BASE_DIR, 'project', 'config',
        os.environ.get('DJANGO_CONFIG_FILE_NAME', 'without-docker.yml')
    )
)

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
```python
#!/usr/bin/env python
import os
import sys

from django.core.management import execute_from_command_line

from django_docker_helpers.db import ensure_databases_alive, ensure_caches_alive, migrate, \
    modeltranslation_sync_translation_fields
from django_docker_helpers.files import collect_static
from django_docker_helpers.management import create_admin, run_gunicorn
from msa_mailer.wsgi import application

PRODUCTION = bool(int(os.environ.get('MSA_MAILER_PRODUCTION', 0) or 0))

SERVER = bool(int(os.environ.get('MSA_MAILER_SERVER', 0) or 0))


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'msa_mailer.settings')

    if PRODUCTION or os.environ.get('MSA_MAILER_FORCE_PRODUCTION'):
        ensure_databases_alive(100)
        ensure_caches_alive(100)
        # skip collectstatic & migrations for worker
        if SERVER:
            collect_static()
            migrate()
            modeltranslation_sync_translation_fields()
            create_admin()

    if len(sys.argv) == 2 and sys.argv[1] == 'gunicorn':
        gunicorn_module_name = 'gunicorn_dev'
        if PRODUCTION:
            gunicorn_module_name = 'gunicorn_prod'

        run_gunicorn(application, gunicorn_module_name=gunicorn_module_name)
    else:
        execute_from_command_line(sys.argv)

```