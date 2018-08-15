from django_docker_helpers.utils import run_env_once, wf


@run_env_once
def collect_static() -> bool:
    """
    Runs Django ``collectstatic`` command in silent mode.

    :return: always ``True``
    """
    from django.core.management import execute_from_command_line
    # from django.conf import settings
    # if not os.listdir(settings.STATIC_ROOT):
    wf('Collecting static files... ', False)
    execute_from_command_line(['./manage.py', 'collectstatic', '-c', '--noinput', '-v0'])
    wf('[+]\n')
    return True
