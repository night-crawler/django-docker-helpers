from distutils.core import setup

from django_docker_helpers import __version__

setup(
    name='django-docker-helpers',
    version=__version__,
    packages=['django_docker_helpers'],
    url='https://github.com/night-crawler/django-docker-helpers',
    license='MIT',
    author='night-crawler',
    author_email='lilo.panic@gmail.com',
    description='Django Docker helpers',

    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: MIT License',
    ],
    requires=['pyaml', 'gunicorn']
)
