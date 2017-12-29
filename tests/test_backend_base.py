import pytest

from django_docker_helpers.config.backends import BaseParser


# noinspection PyMethodMayBeStatic
class BaseParserTest:
    def test__base_parser__raises__not_implemented(self):
        p = BaseParser()
        with pytest.raises(NotImplementedError):
            p.get('qwe')

        with pytest.raises(NotImplementedError):
            p.get_client()
