from setuptools import setup, find_packages

from django_docker_helpers import __version__

try:
    import pypandoc

    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = ''

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
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=['dpath', 'pyaml', 'gunicorn', 'django', 'terminaltables']
)
