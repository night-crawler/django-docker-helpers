from setuptools import setup, find_packages
from django_docker_helpers import __version__

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(
    name='django-docker-helpers',
    version=__version__,
    packages=find_packages(),
    url='https://github.com/night-crawler/django-docker-helpers',
    license='MIT',
    author='night-crawler',
    author_email='lilo.panic@gmail.com',
    description='Django Docker helpers',
    long_description=long_description,
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
