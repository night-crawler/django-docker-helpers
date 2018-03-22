===================
Config loader usage
===================

To initialize config loader use this::

    yml_conf = os.path.join(
        BASE_DIR, 'my_project', 'config',
        os.environ.get('DJANGO_CONFIG_FILE_NAME', 'without-docker.yml')
        )
    os.environ.setdefault('YAMLPARSER__CONFIG', yml_conf)

    configure = ConfigLoader.from_env(suppress_logs=True, silent=True)


.. note::

    You can specify parsers with env variable ``CONFIG__PARSERS``. It can be set to, i.e.
    ``EnvironmentParser,RedisParser,YamlParser``. Also you can define config parsers this way::

        loader = ConfigLoader.from_env(parser_modules=['EnvironmentParser'])

    Read more about config loader: :meth:`~django_docker_helpers.config.ConfigLoader.from_env`

Then use ``configure`` to read a setting from configs::

    DEBUG = configure('debug', False)

All settings are case insensitive::

    DEBUG = configure('DEBUG', False)


You can use nested variable paths (path parts delimiter is comma by default)::

    SECRET_KEY = configure('common.secret_key', 'secret')


Strict typing may be added with ``coerce_type``::

    DATABASES = {
        'default': {
            'ENGINE': configure('db.engine', 'django.db.backends.postgresql'),
            'HOST': configure('db.host', 'localhost'),
            'PORT': configure('db.port', 5432, coerce_type=int),

            'NAME': configure('db.name', 'marfa'),
            'USER': configure('db.user', 'marfa'),
            'PASSWORD': configure('db.password', 'marfa'),

            'CONN_MAX_AGE': configure('db.conn_max_age', 60, coerce_type=int)
        }
    }

.. note::

    You can create your own ``coercer``. By default it's equal to ``coerce_type``.
    Example: :func:`django_docker_helpers.utils.coerce_str_to_bool`
