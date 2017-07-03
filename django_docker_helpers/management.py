import os
from gunicorn.app.base import Application
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import execute_from_command_line

from django_docker_helpers.utils import dotkey, wf

# ENV variables used to prevent running init code twice for runserver command
# (https://stackoverflow.com/questions/16546652/why-does-django-run-everything-twice)


def create_admin():
    if os.environ.get('create_admin'):
        return
    os.environ['create_admin'] = '1'

    from django.conf import settings
    wf('Creating superuser... ', False)

    username, email, password = [dotkey(settings.CONFIG, 'superuser.%s' % v) for v in ['username', 'email', 'password']]
    if not all([username, email]):
        wf('[SKIP: username and email should not be empty]\n')
        return

    from django.db import IntegrityError
    try:
        execute_from_command_line([
            './manage.py', 'createsuperuser',
            '--username', username,
            '--email', email,
            '--noinput'
        ])
    except IntegrityError:
        pass

    if password:
        # after `execute_from_command_line` models are loaded
        from django.contrib.auth.models import User
        user = User.objects.get(username=username)

        # do not change password if it was set before
        if not user.has_usable_password():
            user.set_password(password)
            user.save()
    wf('[DONE]\n')


def run_gunicorn(application: WSGIHandler, gunicorn_module_name: str='gunicorn_prod'):
    class DjangoApplication(Application):
        def init(self, parser, opts, args):
            cfg = self.get_config_from_module_name(gunicorn_module_name)
            clean_cfg = {}
            for k, v in cfg.items():
                # Ignore unknown names
                if k not in self.cfg.settings:
                    continue
                clean_cfg[k.lower()] = v
            return clean_cfg

        def load(self) -> WSGIHandler:
            return application

    return DjangoApplication().run()
