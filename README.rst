## Sample

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
