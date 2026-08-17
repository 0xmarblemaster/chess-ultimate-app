"""
Admin gamification configuration API (org-scoped).

Rules tab (XP rates, coin coupling, streak config, holiday freeze windows) and
Ranks tab (the rank ladder). Follows the existing admin proxy pattern: the
Next.js route Clerk-gates the request and forwards it here with an `X-User-Id`
header; every handler re-checks admin role for the org and scopes all queries by
`organization_id`. Writes bypass RLS via the service key, so scoping is manual.

Nothing here is hardcoded economy — the frontend/sync read these rows (D-6).
"""
import logging

from flask import Blueprint, jsonify, request

from utils.supabase_client import get_supabase as _get_supabase

logger = logging.getLogger(__name__)

gamification_bp = Blueprint('gamification', __name__, url_prefix='/api/admin')

ADMIN_ROLES = ('owner', 'admin', 'teacher')

# Whitelisted top-level keys in gamification_settings.config (Rules tab).
ALLOWED_CONFIG_KEYS = {
    'participation_xp',
    'win_xp',
    'coin_per_xp',
    'top_n',
    'min_tournaments_for_trophy',
    'count_unlinked_in_standings',
    'streak',
    'league_thresholds',
}

# Whitelisted columns for a rank row (Ranks tab).
ALLOWED_RANK_FIELDS = {
    'code',
    'name_ru',
    'name_kk',
    'name_en',
    'min_xp',
    'icon_url',
    'sort_order',
}

DEFAULT_CONFIG = {
    'participation_xp': 1,
    'win_xp': {
        'league_c': 1, 'league_b': 2, 'razryad_4': 3,
        'razryad_3': 3, 'rated': 3, 'pro': 5,
    },
    'coin_per_xp': 1,
    'top_n': 5,
    'min_tournaments_for_trophy': 3,
    'count_unlinked_in_standings': False,
    'streak': {
        'bonus_min': 2, 'bonus_xp': 1,
        'milestones': {'3': 3, '5': 5, '10': 10, '20': 25},
        'freeze_windows': [],
    },
    'league_thresholds': {'a_min': 801, 'b_min': 450},
}


def _require_admin(org_id: str):
    """Check X-User-Id has admin-level access to org. Returns error tuple or None."""
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'Missing X-User-Id header'}), 401
    supabase = _get_supabase()
    result = (
        supabase.table('organization_members').select('role')
        .eq('organization_id', org_id).eq('user_id', user_id).single().execute()
    )
    role = result.data.get('role') if result.data else None
    if not role or role not in ADMIN_ROLES:
        return jsonify({'error': 'Forbidden'}), 403
    return None


# --- Rules tab: settings config ------------------------------------------

@gamification_bp.route('/organizations/<org_id>/gamification/settings', methods=['GET'])
def get_settings(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    row = (
        supabase.table('gamification_settings').select('config')
        .eq('organization_id', org_id).execute()
    )
    config = row.data[0]['config'] if row.data else DEFAULT_CONFIG
    return jsonify({'config': config})


@gamification_bp.route('/organizations/<org_id>/gamification/settings', methods=['PUT'])
def update_settings(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    data = request.get_json() or {}
    incoming = data.get('config', data)
    update = {k: v for k, v in incoming.items() if k in ALLOWED_CONFIG_KEYS}
    if not update:
        return jsonify({'error': 'No valid config fields'}), 400

    supabase = _get_supabase()
    existing = (
        supabase.table('gamification_settings').select('config')
        .eq('organization_id', org_id).execute()
    )
    if existing.data:
        merged = {**(existing.data[0]['config'] or {}), **update}
        supabase.table('gamification_settings').update(
            {'config': merged}
        ).eq('organization_id', org_id).execute()
    else:
        merged = {**DEFAULT_CONFIG, **update}
        supabase.table('gamification_settings').insert(
            {'organization_id': org_id, 'config': merged}
        ).execute()

    logger.info('Gamification settings updated: org=%s keys=%s', org_id, list(update.keys()))
    return jsonify({'config': merged})


# --- Ranks tab: rank ladder ----------------------------------------------

@gamification_bp.route('/organizations/<org_id>/gamification/ranks', methods=['GET'])
def get_ranks(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    rows = (
        supabase.table('gamification_ranks')
        .select('id,code,name_ru,name_kk,name_en,min_xp,icon_url,sort_order')
        .eq('organization_id', org_id).order('sort_order').execute()
    )
    return jsonify({'ranks': rows.data or []})


@gamification_bp.route('/organizations/<org_id>/gamification/ranks', methods=['PUT'])
def replace_ranks(org_id: str):
    """Replace the ladder with the supplied set (upsert by code, delete the rest)."""
    error = _require_admin(org_id)
    if error:
        return error
    data = request.get_json() or {}
    ranks = data.get('ranks')
    if not isinstance(ranks, list) or not ranks:
        return jsonify({'error': 'ranks must be a non-empty array'}), 400

    cleaned = []
    for r in ranks:
        row = {k: v for k, v in r.items() if k in ALLOWED_RANK_FIELDS}
        if not row.get('code') or 'min_xp' not in row:
            return jsonify({'error': 'each rank needs code and min_xp'}), 400
        row['organization_id'] = org_id
        cleaned.append(row)

    supabase = _get_supabase()
    keep_codes = [r['code'] for r in cleaned]
    # Remove ranks no longer present.
    supabase.table('gamification_ranks').delete().eq(
        'organization_id', org_id
    ).not_.in_('code', keep_codes).execute()
    # Upsert the supplied ladder.
    supabase.table('gamification_ranks').upsert(
        cleaned, on_conflict='organization_id,code'
    ).execute()

    logger.info('Gamification ranks replaced: org=%s count=%d', org_id, len(cleaned))
    return jsonify({'status': 'updated', 'count': len(cleaned)})
