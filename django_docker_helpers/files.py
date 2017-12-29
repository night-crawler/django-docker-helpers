from django_docker_helpers.utils import wf, run_env_once


@run_env_once
def collect_static() -> bool:
    from django.core.management import execute_from_command_line
    # from django.conf import settings
    # if not os.listdir(settings.STATIC_ROOT):
    wf('Collecting static files... ', False)
    execute_from_command_line(['./manage.py', 'collectstatic', '-c', '--noinput', '-v0'])
    wf('[+]\n')
    return True
