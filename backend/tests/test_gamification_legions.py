"""
Tests for the gamification Legions + Seasons admin API (Phase 3, §9.4).

Same mocked-Supabase FakeQueryBuilder pattern as test_gamification_admin.py.
Closing a season is the Next.js freeze+trophy job, not covered here.
"""
import pytest
from unittest.mock import patch

ORG_ID = 'org-11111111-1111-1111-1111-111111111111'
ADMIN_USER_ID = 'user_admin_123'

SAMPLE_LEGIONS = [
    {'id': 'l1', 'name': 'Снежные Барсы', 'ce_branch_id': None, 'totem': 'leopard',
     'crest_url': '/x.svg', 'color_primary': '#38bdf8', 'color_secondary': '#0369a1', 'sort_order': 1},
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


class TestLegions:
    def test_401_without_user_header(self, client):
        r = client.get(f'/api/admin/organizations/{ORG_ID}/gamification/legions')
        assert r.status_code == 401

    def test_403_for_non_admin(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': STUDENT_MEMBER})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/legions',
                headers={'X-User-Id': 'x'},
            )
        assert r.status_code == 403

    def test_get_returns_legions(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'legions': SAMPLE_LEGIONS})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/legions',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert len(r.get_json()['legions']) == 1

    def test_create_requires_name(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/legions',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'totem': 'wolf'},
            )
        assert r.status_code == 400

    def test_create_whitelists_fields(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'legions': SAMPLE_LEGIONS})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/legions',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'name': 'New Legion', 'ce_branch_id': '', 'evil': 'x'},
            )
        assert r.status_code == 201

    def test_update_legion(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'legions': SAMPLE_LEGIONS})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/legions/l1',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'name': 'Renamed', 'ce_branch_id': 'branch-uuid'},
            )
        assert r.status_code == 200

    def test_delete_legion(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'legions': SAMPLE_LEGIONS})
            r = client.delete(
                f'/api/admin/organizations/{ORG_ID}/gamification/legions/l1',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200


class TestSeasons:
    def test_get_returns_seasons(self, client):
        seasons = [{'id': 's1', 'name': 'Сезон 1', 'status': 'draft', 'starts_at': 'x', 'ends_at': 'y'}]
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'seasons': seasons})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert len(r.get_json()['seasons']) == 1

    def test_create_requires_dates(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'name': 'No dates'},
            )
        assert r.status_code == 400

    def test_create_defaults_to_draft(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'seasons': [{'id': 's2', 'status': 'draft'}]})
            r = client.post(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'name': 'Сезон 2', 'starts_at': '2026-09-01', 'ends_at': '2026-11-30'},
            )
        assert r.status_code == 201

    def test_put_rejects_close_via_status(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'seasons': [{'id': 's1'}]})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons/s1',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'status': 'closed'},
            )
        assert r.status_code == 400

    def test_put_active_conflict_returns_409(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {
                'organization_members': ADMIN_MEMBER,
                'seasons': [{'id': 'other-active'}],  # another active season
            })
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons/s-new',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'status': 'active'},
            )
        assert r.status_code == 409

    def test_put_activate_ok_when_no_clash(self, client):
        # The only active row is the one being updated → no clash.
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {
                'organization_members': ADMIN_MEMBER,
                'seasons': [{'id': 's1'}],
            })
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons/s1',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'status': 'active'},
            )
        assert r.status_code == 200

    def test_delete_closed_season_rejected(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'seasons': [{'status': 'closed'}]})
            r = client.delete(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons/s1',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 400

    def test_delete_draft_season_ok(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'seasons': [{'status': 'draft'}]})
            r = client.delete(
                f'/api/admin/organizations/{ORG_ID}/gamification/seasons/s1',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
