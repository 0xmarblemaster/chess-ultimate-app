"""
Tests for the gamification admin Coins tab — coin package CRUD
(/api/admin/organizations/<org>/gamification/coin-packages).

Package pricing is admin-created (D-6). Mirrors test_gamification_items.py's
FakeQueryBuilder pattern with mocked Supabase.
"""
import pytest
from unittest.mock import patch

ORG_ID = 'org-11111111-1111-1111-1111-111111111111'
ADMIN_USER_ID = 'user_admin_123'

SAMPLE_PACKAGES = [
    {'id': 'p1', 'coins': 100, 'price_kzt': 500, 'active': True, 'sort_order': 1},
    {'id': 'p2', 'coins': 500, 'price_kzt': 2000, 'active': True, 'sort_order': 2},
]

ADMIN_MEMBER = [{'role': 'admin'}]
STUDENT_MEMBER = [{'role': 'student'}]


class FakeQueryResult:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class FakeQueryBuilder:
    def __init__(self, data=None):
        self._data = data
        self.not_ = self

    def select(self, *a, **k):
        return self

    def insert(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def delete(self, *a, **k):
        return self

    def upsert(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def single(self):
        if isinstance(self._data, list):
            self._data = self._data[0] if self._data else None
        return self

    def execute(self):
        return FakeQueryResult(data=self._data)


def _dispatcher(table_data: dict):
    def table(name):
        return FakeQueryBuilder(data=table_data.get(name, []))
    return table


@pytest.fixture
def client():
    from flask import Flask
    from routes.gamification import gamification_bp
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(gamification_bp)
    return app.test_client()


def _sb(mock, tables):
    mock.return_value.table = _dispatcher(tables)


class TestPackagesList:
    def test_401_without_user_header(self, client):
        r = client.get(f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages')
        assert r.status_code == 401

    def test_403_for_non_admin(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': STUDENT_MEMBER})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages',
                headers={'X-User-Id': 'someone'},
            )
        assert r.status_code == 403

    def test_get_returns_packages(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': SAMPLE_PACKAGES})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert len(r.get_json()['packages']) == 2


class TestPackagesCreate:
    def test_create_requires_positive_coins_and_price(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': []})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'coins': 0, 'price_kzt': 500},
            )
        assert r.status_code == 400

    def test_create_whitelists_and_returns_201(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': [SAMPLE_PACKAGES[0]]})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'coins': 100, 'price_kzt': 500, 'active': True, 'evil_key': 'nope'},
            )
        assert r.status_code == 201
        assert r.get_json()['package']['coins'] == 100

    def test_create_coerces_string_numerics(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': [SAMPLE_PACKAGES[0]]})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'coins': '100', 'price_kzt': '500'},
            )
        assert r.status_code == 201


class TestPackagesUpdate:
    def test_update_returns_package(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': [SAMPLE_PACKAGES[0]]})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages/p1',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'active': False},
            )
        assert r.status_code == 200
        assert r.get_json()['package']['id'] == 'p1'

    def test_update_missing_package_404(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': []})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages/nope',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'price_kzt': 999},
            )
        assert r.status_code == 404

    def test_update_rejects_empty_payload(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': [SAMPLE_PACKAGES[0]]})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages/p1',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'not_allowed': 1},
            )
        assert r.status_code == 400


class TestPackagesDelete:
    def test_delete_ok(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'coin_packages': [SAMPLE_PACKAGES[0]]})
            r = client.delete(
                f'/api/admin/organizations/{ORG_ID}/gamification/coin-packages/p1',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert r.get_json()['status'] == 'deleted'
