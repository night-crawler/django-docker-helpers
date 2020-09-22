# noinspection PyPackageRequirements
import pytest

import os
from unittest import mock

from django_docker_helpers import utils

pytestmark = pytest.mark.utils


# noinspection PyMethodMayBeStatic
class UtilsTest:
    def test__utils__dotkey(self):
        obj = {
            'debug': True,
            'first': 1,
            'second': {
                'nested': True,
                'next': [1, 2, 3]
            }
        }
        assert utils.dotkey(obj, 'debug') is True
        assert utils.dotkey(obj, 'first') == 1
        assert utils.dotkey(obj, 'second') == {'nested': True, 'next': [1, 2, 3]}
        assert utils.dotkey(obj, 'second.next.1') == 2
        assert utils.dotkey(obj, 'second.lol', 'DEFAULT') == 'DEFAULT'

    def test__coerce_str_to_bool(self):
        assert utils.coerce_str_to_bool('0') is False
        assert utils.coerce_str_to_bool('1') is True

        assert utils.coerce_str_to_bool('FALSE') is False
        assert utils.coerce_str_to_bool('true') is True

        assert utils.coerce_str_to_bool('off') is False
        assert utils.coerce_str_to_bool('on') is True

        assert utils.coerce_str_to_bool(False) is False
        assert utils.coerce_str_to_bool(True) is True

        assert utils.coerce_str_to_bool(0) is False
        assert utils.coerce_str_to_bool(1) is True

        assert utils.coerce_str_to_bool('qwe') is True

        with pytest.raises(ValueError):
            utils.coerce_str_to_bool('lol', strict=True)

    def test__utils__env_bool_flag(self):
        _env = {
            'test_int_0': 0,
            'test_int_1': 1,
            'test_int_2': 2,
            'test_str_0': '0',
            'test_str_1': '1',
            'test_str_2': '2',
            'test_str_true': 'true',
            'test_str_false': 'false',
            'test_bool_true': True,
            'test_bool_false': False,
        }
        assert utils.env_bool_flag('test_int_0', env=_env) is False
        assert utils.env_bool_flag('test_int_1', env=_env) is True
        assert utils.env_bool_flag('test_int_2', env=_env) is True
        with pytest.raises(ValueError):
            assert utils.env_bool_flag('test_int_2', strict=True, env=_env)

        assert utils.env_bool_flag('test_str_0', env=_env) is False
        assert utils.env_bool_flag('test_str_1', env=_env) is True
        assert utils.env_bool_flag('test_str_2', env=_env) is True
        with pytest.raises(ValueError):
            assert utils.env_bool_flag('test_str_2', strict=True, env=_env)

        assert utils.env_bool_flag('test_str_true', env=_env) is True
        assert utils.env_bool_flag('test_str_false', env=_env) is False

        assert utils.env_bool_flag('test_bool_true', env=_env) is True
        assert utils.env_bool_flag('test_bool_false', env=_env) is False

        assert utils.env_bool_flag('doesnotexist', env=_env) is False

    def test__utils__env_tristate_flag(self):
        _env = {
            'test_int_0': 0,
            'test_int_1': 1,
            'test_int_2': 2,
            'test_str_0': '0',
            'test_str_1': '1',
            'test_str_2': '2',
            'test_str_true': 'true',
            'test_str_false': 'false',
            'test_bool_true': True,
            'test_bool_false': False,
        }
        assert utils.env_tristate_flag('test_int_0', env=_env) is False
        assert utils.env_tristate_flag('test_int_1', env=_env) is True
        assert utils.env_tristate_flag('test_int_2', env=_env) is True
        with pytest.raises(ValueError):
            assert utils.env_tristate_flag('test_int_2', strict=True, env=_env)

        assert utils.env_tristate_flag('test_str_0', env=_env) is False
        assert utils.env_tristate_flag('test_str_1', env=_env) is True
        assert utils.env_tristate_flag('test_str_2', env=_env) is True
        with pytest.raises(ValueError):
            assert utils.env_tristate_flag('test_str_2', strict=True, env=_env)

        assert utils.env_tristate_flag('test_str_true', env=_env) is True
        assert utils.env_tristate_flag('test_str_false', env=_env) is False

        assert utils.env_tristate_flag('test_bool_true', env=_env) is True
        assert utils.env_tristate_flag('test_bool_false', env=_env) is False

        assert utils.env_tristate_flag('doesnotexist', env=_env) is None

    def test__utils__materialize_dict(self):
        # check yield
        sample = {
            'plain': 1,
            'a_some': {
                'path': 1
            },
            'and': {
                1: 2,
                'more': [1, 2, 3],
                'much': {
                    'a': 1,
                    'more': 2,
                    'really': {
                        'longer': {
                            'path': 666
                        }
                    }
                },
                'bad': [1, {'no': 'please'}]
            }
        }
        results = [
            ('and/much/really/longer/path', 666),
            ('and/much/a', 1),
            ('and/much/more', 2),
            ('a_some/path', 1),
            ('and/1', 2),
            ('and/bad', [1, {'no': 'please'}]),
            ('and/more', [1, 2, 3]),
            ('plain', 1)
        ]

        for gen_val in utils._materialize_dict(sample, separator='/'):
            assert gen_val in results, 'Ensure transformed path is present in results'

        for gen_val, reference_val in zip(utils.materialize_dict(sample, separator='/'), results):
            assert gen_val == reference_val, 'Ensure ordering is correct'

    def test__utils__mp_serialize_dict(self):
        sample = {
            'bool_flag': '',  # flag
            'unicode': 'вася',
            'none_value': None,
            'debug': True,
            'mixed': ['ascii', 'юникод', 1, {'d': 1}, {'b': 2}],
            'nested': {
                'a': {
                    'b': 2,
                    'c': b'bytes',
                }
            }
        }

        md = utils.mp_serialize_dict(sample, separator='/')

        # convert tuples to a plain dict
        md = dict(md)

        assert md['nested/a/b'] == b'2'
        assert md['nested/a/c'] == b'bytes'
        assert md['bool_flag'] == b"::YAML::\n''\n"
        assert md['debug'] == b'true'

        # they've changed some serialization options in pyaml, so the idea to compare our output against
        # the output of pyaml doesn't seem to be great.
        assert md['mixed'].startswith(b'::YAML::')
        assert md['none_value'] is None
        assert md['unicode'] == b'\xd0\xb2\xd0\xb0\xd1\x81\xd1\x8f'

    def test__run_env_once(self):
        res = []

        @utils.run_env_once
        def only_once():
            res.append(1)

        only_once()
        only_once()

        assert len(res) == 1
        assert os.getenv('only_once') == '1'

    def test__dot_path(self):
        class O1:
            my_dict = {'a': {'b': 1}}

        class O2:
            def __init__(self):
                self.nested = O1()

        class O3:
            final = O2()

        o = O3()

        assert utils.dot_path(o, 'final.nested.my_dict.a.b') == 1
        assert utils.dot_path(o, 'final.lol.qwe', 'my_default') == 'my_default'
        assert utils.dot_path(o, 'final.nested.my_dict.a.qwe', 'my_default') == 'my_default'

    def test__shred(self):
        assert utils.shred('password', '1234') == '****'
        assert utils.shred('qwerty', '1234') == '1234'

    def test__shred_deep(self):
        shredded = utils.shred_deep({
            'password': 1,
            'password_2': {
                'password': 4444,
            },
            'list': [
                {'password': 222},
                'normal',
                {'normal': 1}
            ],
            'set': {1, 2, 3},
            'frozenset': frozenset([1, 2, 3, 'password'])
        })

        assert shredded == {
            'password': '*',
            'password_2': {'password': '****'},
            'list': [
                {'password': '***'},
                'normal',
                {'normal': 1}],
            'set': {1, 2, 3},
            'frozenset': frozenset({1, 2, 3, 'password'})
        }

        utils.shred_deep(None)

    def test__is_dockerized(self):
        with mock.patch('os.environ', new={'DOCKERIZED': '1'}):
            assert utils.is_dockerized()

        with mock.patch('os.environ', new={'DOCKERIZED': '0'}):
            assert not utils.is_dockerized()

        with mock.patch('os.environ', new={}):
            with mock.patch('docker_check.checker.is_inside_container', return_value=True):
                assert utils.is_dockerized()

            with mock.patch('docker_check.checker.is_inside_container', return_value=False):
                assert not utils.is_dockerized()

            with mock.patch('docker_check.checker.is_inside_container', return_value=None):
                assert not utils.is_dockerized()
