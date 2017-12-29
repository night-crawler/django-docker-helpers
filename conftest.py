import os


def pytest_configure():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.django_settings')
    import django
    django.setup()

    from django.core.management import execute_from_command_line

    execute_from_command_line(['manage.py', 'makemigrations', 'test_app'])
    execute_from_command_line(['manage.py', 'migrate'])
