from unittest.mock import patch

# noinspection PyPackageRequirements
import pytest

from django_docker_helpers.db import migrate, ensure_caches_alive, ensure_databases_alive
from django_docker_helpers.files import collect_static
from django_docker_helpers.management import create_admin

pytestmark = pytest.mark.management


# noinspection PyMethodMayBeStatic
class ManagementTest:
    @pytest.mark.django_db
    def test__migrate(self):
        with patch('django_docker_helpers.db.wf') as wf:
            assert migrate()
            assert any('[+]' in arg[0][0] for arg in wf.call_args_list)

    @pytest.mark.django_db
    def test__ensure_databases_alive(self):
        with patch('django_docker_helpers.db.wf') as wf:
            assert ensure_databases_alive(max_retries=1)
            assert any('[+]' in arg[0][0] for arg in wf.call_args_list)

    def test__ensure_caches_alive(self):
        with patch('django_docker_helpers.db.wf') as wf:
            assert ensure_caches_alive(max_retries=1)
            assert any('[+]' in arg[0][0] for arg in wf.call_args_list)

    def test__collect_static(self):
        with patch('django_docker_helpers.files.wf') as wf:
            assert collect_static()
            assert any('[+]' in arg[0][0] for arg in wf.call_args_list)

    @pytest.mark.django_db
    def test__create_admin(self):
        with patch('django_docker_helpers.management.wf') as wf:
            assert create_admin()
            assert any('[+]' in arg[0][0] for arg in wf.call_args_list)
