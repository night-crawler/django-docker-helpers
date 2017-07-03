import os

from django_docker_helpers.utils import wf


# ENV variables used to prevent running init code twice for runserver command
# (https://stackoverflow.com/questions/16546652/why-does-django-run-everything-twice)


def collect_static():
    if os.environ.get('collect_static'):
        return
    os.environ['collect_static'] = '1'

    from django.core.management import execute_from_command_line
    # from django.conf import settings
    # if not os.listdir(settings.STATIC_ROOT):
    wf('Collecting static files... ', False)
    execute_from_command_line(['./manage.py', 'collectstatic', '-c', '--noinput', '-v0'])
    wf('[DONE]\n')
