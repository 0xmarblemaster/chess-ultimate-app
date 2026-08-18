"""
Tests for the gamification asset upload admin API (§7.2, §8.1, §9.4).

Covers auth, kind/MIME/size validation, and the { url } success contract used
by the Items art / Legion crest / Rank icon upload widgets. Same mocked-Supabase
pattern as the sibling gamification admin tests; storage is stubbed so no real
bucket is touched.
"""
import io
from unittest.mock import MagicMock, patch

import pytest

ORG_ID = 'org-11111111-1111-1111-1111-111111111111'
ADMIN_USER_ID = 'user_admin_123'

ADMIN_MEMBER = [{'role': 'admin'}]
STUDENT_MEMBER = [{'role': 'student'}]

URL = f'/api/admin/organizations/{ORG_ID}/gamification/upload'


class FakeQueryResult:
    def __init__(self, data=None):
        self.data = data


class FakeQueryBuilder:
    def __init__(self, data=None):
        self._data = data

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
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


def _admin_supabase(mock, *, public_url='https://cdn.example/x.png'):
    """Wire the mock: admin role check + a stubbed storage bucket."""
    mock.return_value.table = _dispatcher({'organization_members': ADMIN_MEMBER})
    bucket = MagicMock()
    bucket.get_public_url.return_value = public_url
    mock.return_value.storage.from_.return_value = bucket
    return bucket


def _file(content=b'\x89PNG\r\n', mime='image/png', name='art.png'):
    return {'file': (io.BytesIO(content), name, mime)}


class TestUpload:
    def test_401_without_user_header(self, client):
        r = client.post(URL, data={'kind': 'item_art', **_file()},
                        content_type='multipart/form-data')
        assert r.status_code == 401

    def test_403_for_non_admin(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            mock.return_value.table = _dispatcher({'organization_members': STUDENT_MEMBER})
            r = client.post(URL, headers={'X-User-Id': 'x'},
                            data={'kind': 'item_art', **_file()},
                            content_type='multipart/form-data')
        assert r.status_code == 403

    def test_rejects_unknown_kind(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _admin_supabase(mock)
            r = client.post(URL, headers={'X-User-Id': ADMIN_USER_ID},
                            data={'kind': 'logo', **_file()},
                            content_type='multipart/form-data')
        assert r.status_code == 400

    def test_requires_file(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _admin_supabase(mock)
            r = client.post(URL, headers={'X-User-Id': ADMIN_USER_ID},
                            data={'kind': 'item_art'},
                            content_type='multipart/form-data')
        assert r.status_code == 400

    def test_rejects_bad_mime(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            _admin_supabase(mock)
            r = client.post(URL, headers={'X-User-Id': ADMIN_USER_ID},
                            data={'kind': 'item_art',
                                  **_file(content=b'oops', mime='application/pdf', name='x.pdf')},
                            content_type='multipart/form-data')
        assert r.status_code == 415

    def test_rejects_oversize_file(self, client):
        big = b'0' * (1 * 1024 * 1024 + 1)
        with patch('routes.gamification._get_supabase') as mock:
            _admin_supabase(mock)
            r = client.post(URL, headers={'X-User-Id': ADMIN_USER_ID},
                            data={'kind': 'legion_crest', **_file(content=big)},
                            content_type='multipart/form-data')
        assert r.status_code == 413

    def test_success_returns_url(self, client):
        with patch('routes.gamification._get_supabase') as mock:
            bucket = _admin_supabase(mock, public_url='https://cdn.example/crest.svg?')
            r = client.post(URL, headers={'X-User-Id': ADMIN_USER_ID},
                            data={'kind': 'rank_icon',
                                  **_file(content=b'<svg/>', mime='image/svg+xml', name='r.svg')},
                            content_type='multipart/form-data')
        assert r.status_code == 201
        body = r.get_json()
        # Trailing '?' from supabase-py is stripped.
        assert body['url'] == 'https://cdn.example/crest.svg'
        assert body['kind'] == 'rank_icon'
        assert body['key'].startswith(f'{ORG_ID}/gamification/rank_icon/')
        bucket.upload.assert_called_once()
