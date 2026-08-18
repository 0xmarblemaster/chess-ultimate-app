"""
Tests for the gamification admin Items tab
(/api/admin/organizations/<org>/gamification/items).

Cosmetic catalog CRUD with mocked Supabase, mirroring test_gamification_admin.py's
FakeQueryBuilder pattern.
"""
import pytest
from unittest.mock import patch

ORG_ID = 'org-11111111-1111-1111-1111-111111111111'
ADMIN_USER_ID = 'user_admin_123'

SAMPLE_ITEMS = [
    {'id': 'i1', 'sku': 'shield_iron', 'slot': 'shield', 'rarity': 'common',
     'kind': 'purchasable', 'price_coins': 10, 'name_ru': 'Железный щит',
     'name_kk': 'Темір қалқан', 'name_en': 'Iron Shield', 'sort_order': 2},
    {'id': 'i2', 'sku': 'pet_dragon', 'slot': 'pet', 'rarity': 'legendary',
     'kind': 'purchasable', 'price_coins': 150, 'name_ru': 'Дракончик',
     'name_kk': 'Кішкентай айдаһар', 'name_en': 'Baby Dragon', 'sort_order': 18},
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


class TestItemsList:
    def test_401_without_user_header(self, client):
        r = client.get(f'/api/admin/organizations/{ORG_ID}/gamification/items')
        assert r.status_code == 401

    def test_403_for_non_admin(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': STUDENT_MEMBER})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/items',
                headers={'X-User-Id': 'someone'},
            )
        assert r.status_code == 403

    def test_get_returns_catalog(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'items': SAMPLE_ITEMS})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/items',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert len(r.get_json()['items']) == 2


class TestItemsCreate:
    def test_create_requires_sku_and_slot(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'items': []})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/items',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'name_en': 'No sku'},
            )
        assert r.status_code == 400

    def test_create_whitelists_and_returns_201(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'items': [SAMPLE_ITEMS[0]]})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/items',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'sku': 'shield_iron', 'slot': 'shield', 'price_coins': 10,
                      'evil_key': 'nope'},
            )
        assert r.status_code == 201
        assert r.get_json()['item']['sku'] == 'shield_iron'


class TestItemsUpdate:
    def test_update_returns_item(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'items': [SAMPLE_ITEMS[0]]})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/items/i1',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'price_coins': 20},
            )
        assert r.status_code == 200
        assert r.get_json()['item']['id'] == 'i1'

    def test_update_missing_item_404(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'items': []})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/items/nope',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'price_coins': 20},
            )
        assert r.status_code == 404

    def test_update_rejects_empty_payload(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'items': [SAMPLE_ITEMS[0]]})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/items/i1',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'not_allowed': 1},
            )
        assert r.status_code == 400


class TestItemsDelete:
    def test_delete_ok(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'items': [SAMPLE_ITEMS[0]]})
            r = client.delete(
                f'/api/admin/organizations/{ORG_ID}/gamification/items/i1',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert r.get_json()['status'] == 'deleted'
