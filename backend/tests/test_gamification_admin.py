"""
Tests for the gamification admin API (/api/admin/organizations/<org>/gamification).

Rules (settings) + Ranks endpoints with mocked Supabase, mirroring
test_admin_api.py's FakeQueryBuilder pattern (extended with not_/in_/upsert).
"""
import pytest
from unittest.mock import patch

ORG_ID = 'org-11111111-1111-1111-1111-111111111111'
ADMIN_USER_ID = 'user_admin_123'

SAMPLE_SETTINGS = [{
    'config': {
        'participation_xp': 1,
        'win_xp': {'league_c': 1, 'league_b': 2},
        'coin_per_xp': 1,
    }
}]

SAMPLE_RANKS = [
    {'id': 'r1', 'code': 'pawn', 'name_ru': 'Пешка', 'name_kk': 'Сарбаз', 'name_en': 'Pawn', 'min_xp': 0, 'icon_url': None, 'sort_order': 1},
    {'id': 'r2', 'code': 'knight', 'name_ru': 'Конь', 'name_kk': 'Ат', 'name_en': 'Knight', 'min_xp': 10, 'icon_url': None, 'sort_order': 2},
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
        self.not_ = self  # supports `.not_.in_(...)`

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


class TestSettings:
    def test_401_without_user_header(self, client):
        r = client.get(f'/api/admin/organizations/{ORG_ID}/gamification/settings')
        assert r.status_code == 401

    def test_403_for_non_admin(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': STUDENT_MEMBER})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/settings',
                headers={'X-User-Id': 'someone'},
            )
        assert r.status_code == 403

    def test_get_returns_config(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'gamification_settings': SAMPLE_SETTINGS})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/settings',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert r.get_json()['config']['participation_xp'] == 1

    def test_put_whitelists_and_merges(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'gamification_settings': SAMPLE_SETTINGS})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/settings',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'config': {'participation_xp': 2, 'coin_per_xp': 3, 'evil_key': 'nope'}},
            )
        assert r.status_code == 200
        merged = r.get_json()['config']
        assert merged['participation_xp'] == 2
        assert merged['coin_per_xp'] == 3
        assert 'evil_key' not in merged  # dropped by whitelist
        assert merged['win_xp'] == {'league_c': 1, 'league_b': 2}  # preserved from existing

    def test_put_rejects_empty(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'gamification_settings': SAMPLE_SETTINGS})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/settings',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'config': {'not_allowed': 1}},
            )
        assert r.status_code == 400

    def test_put_persists_standings_and_streak_keys(self, client):
        """Rules tab wires top_n, trophy threshold, unlinked toggle, league
        thresholds and streak (milestones + freeze windows) — all must survive
        the whitelist merge so the UI inputs actually persist."""
        streak = {
            'bonus_min': 3,
            'bonus_xp': 2,
            'milestones': {'3': 3, '5': 5, '10': 10, '20': 25},
            'freeze_windows': [{'from': '2026-12-25', 'until': '2027-01-08', 'label': 'Winter'}],
        }
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'gamification_settings': SAMPLE_SETTINGS})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/settings',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'config': {
                    'top_n': 7,
                    'min_tournaments_for_trophy': 4,
                    'count_unlinked_in_standings': True,
                    'league_thresholds': {'a_min': 900, 'b_min': 500},
                    'streak': streak,
                }},
            )
        assert r.status_code == 200
        merged = r.get_json()['config']
        assert merged['top_n'] == 7
        assert merged['min_tournaments_for_trophy'] == 4
        assert merged['count_unlinked_in_standings'] is True
        assert merged['league_thresholds'] == {'a_min': 900, 'b_min': 500}
        assert merged['streak']['freeze_windows'][0]['label'] == 'Winter'
        assert merged['streak']['milestones']['20'] == 25


class TestRanks:
    def test_get_returns_ladder(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'gamification_ranks': SAMPLE_RANKS})
            r = client.get(
                f'/api/admin/organizations/{ORG_ID}/gamification/ranks',
                headers={'X-User-Id': ADMIN_USER_ID},
            )
        assert r.status_code == 200
        assert len(r.get_json()['ranks']) == 2

    def test_put_replaces_ladder(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER, 'gamification_ranks': SAMPLE_RANKS})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/ranks',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'ranks': [
                    {'code': 'pawn', 'name_ru': 'Пешка', 'name_kk': 'Сарбаз', 'name_en': 'Pawn', 'min_xp': 0, 'sort_order': 1},
                    {'code': 'king', 'name_ru': 'Король', 'name_kk': 'Патша', 'name_en': 'King', 'min_xp': 500, 'sort_order': 2},
                ]},
            )
        assert r.status_code == 200
        assert r.get_json()['count'] == 2

    def test_put_rejects_empty(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/ranks',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'ranks': []},
            )
        assert r.status_code == 400

    def test_put_rejects_rank_without_code(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _sb(mock, {'organization_members': ADMIN_MEMBER})
            r = client.put(
                f'/api/admin/organizations/{ORG_ID}/gamification/ranks',
                headers={'X-User-Id': ADMIN_USER_ID},
                json={'ranks': [{'name_en': 'Nameless', 'min_xp': 5}]},
            )
        assert r.status_code == 400
