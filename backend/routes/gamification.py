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
import uuid

from flask import Blueprint, jsonify, request

from utils.supabase_client import get_supabase as _get_supabase

logger = logging.getLogger(__name__)

gamification_bp = Blueprint('gamification', __name__, url_prefix='/api/admin')

ADMIN_ROLES = ('owner', 'admin', 'teacher')

# Asset upload (Items art, Legion crests, Rank icons — §7.2, §8.1, §9.4). Reuses
# the org-branding bucket + public-URL contract of the branding upload so art can
# be swapped without touching schema (D-9).
_ASSET_BUCKET = 'org-branding'
_ASSET_ALLOWED_MIME = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
    'image/svg+xml': 'svg',
}
_ASSET_MAX_BYTES = 1 * 1024 * 1024  # 1 MiB
_ASSET_KINDS = {'item_art', 'legion_crest', 'rank_icon'}

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

# Whitelisted columns for a legion row (Legions tab).
ALLOWED_LEGION_FIELDS = {
    'name',
    'ce_branch_id',
    'totem',
    'crest_url',
    'color_primary',
    'color_secondary',
    'sort_order',
}

LEGION_SELECT = (
    'id,name,ce_branch_id,totem,crest_url,color_primary,color_secondary,sort_order'
)

# Whitelisted columns for a season row (Seasons tab). status transitions to
# 'closed' go through the Next.js close job (freeze + trophy grant), not here.
ALLOWED_SEASON_FIELDS = {
    'name',
    'starts_at',
    'ends_at',
    'status',
    'top_n',
    'trophy_item_id',
}

SEASON_SELECT = (
    'id,name,starts_at,ends_at,status,top_n,trophy_item_id,winner_legion_id,closed_at'
)

# Whitelisted columns for an item row (Items tab).
ALLOWED_ITEM_FIELDS = {
    'sku',
    'slot',
    'rarity',
    'kind',
    'price_coins',
    'name_ru',
    'name_kk',
    'name_en',
    'description_ru',
    'description_kk',
    'description_en',
    'art_url',
    'anim_url',
    'is_placeholder_art',
    'available',
    'available_from',
    'available_until',
    'acquisition_note',
    'sort_order',
}

ITEM_SELECT = (
    'id,sku,slot,rarity,kind,price_coins,'
    'name_ru,name_kk,name_en,description_ru,description_kk,description_en,'
    'art_url,anim_url,is_placeholder_art,available,available_from,available_until,'
    'acquisition_note,sort_order'
)

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


# --- Items tab: cosmetic catalog (per-row CRUD) --------------------------

def _clean_item(payload: dict) -> dict:
    """Whitelist item fields; normalize empty strings on optional cols to NULL."""
    row = {k: v for k, v in payload.items() if k in ALLOWED_ITEM_FIELDS}
    for col in ('available_from', 'available_until'):
        if row.get(col) == '':
            row[col] = None
    return row


@gamification_bp.route('/organizations/<org_id>/gamification/items', methods=['GET'])
def get_items(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    rows = (
        supabase.table('items').select(ITEM_SELECT)
        .eq('organization_id', org_id).order('sort_order').execute()
    )
    return jsonify({'items': rows.data or []})


@gamification_bp.route('/organizations/<org_id>/gamification/items', methods=['POST'])
def create_item(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    row = _clean_item(request.get_json() or {})
    if not row.get('sku') or not row.get('slot'):
        return jsonify({'error': 'sku and slot are required'}), 400
    row['organization_id'] = org_id
    supabase = _get_supabase()
    res = supabase.table('items').insert(row).execute()
    created = res.data[0] if res.data else row
    logger.info('Gamification item created: org=%s sku=%s', org_id, row['sku'])
    return jsonify({'item': created}), 201


@gamification_bp.route('/organizations/<org_id>/gamification/items/<item_id>', methods=['PUT'])
def update_item(org_id: str, item_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    row = _clean_item(request.get_json() or {})
    if not row:
        return jsonify({'error': 'No valid item fields'}), 400
    supabase = _get_supabase()
    res = (
        supabase.table('items').update(row)
        .eq('organization_id', org_id).eq('id', item_id).execute()
    )
    if not res.data:
        return jsonify({'error': 'Item not found'}), 404
    logger.info('Gamification item updated: org=%s id=%s', org_id, item_id)
    return jsonify({'item': res.data[0]})


@gamification_bp.route('/organizations/<org_id>/gamification/items/<item_id>', methods=['DELETE'])
def delete_item(org_id: str, item_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    supabase.table('items').delete().eq(
        'organization_id', org_id
    ).eq('id', item_id).execute()
    logger.info('Gamification item deleted: org=%s id=%s', org_id, item_id)
    return jsonify({'status': 'deleted'})


# --- Legions tab: legion CRUD + CE-branch mapping -----------------------------

def _clean_legion(payload: dict) -> dict:
    """Whitelist legion fields; blank optional strings become NULL."""
    row = {k: v for k, v in payload.items() if k in ALLOWED_LEGION_FIELDS}
    if row.get('ce_branch_id') == '':
        row['ce_branch_id'] = None
    return row


@gamification_bp.route('/organizations/<org_id>/gamification/legions', methods=['GET'])
def get_legions(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    rows = (
        supabase.table('legions').select(LEGION_SELECT)
        .eq('organization_id', org_id).order('sort_order').execute()
    )
    return jsonify({'legions': rows.data or []})


@gamification_bp.route('/organizations/<org_id>/gamification/legions', methods=['POST'])
def create_legion(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    row = _clean_legion(request.get_json() or {})
    if not row.get('name'):
        return jsonify({'error': 'name is required'}), 400
    row['organization_id'] = org_id
    supabase = _get_supabase()
    res = supabase.table('legions').insert(row).execute()
    created = res.data[0] if res.data else row
    logger.info('Gamification legion created: org=%s name=%s', org_id, row['name'])
    return jsonify({'legion': created}), 201


@gamification_bp.route('/organizations/<org_id>/gamification/legions/<legion_id>', methods=['PUT'])
def update_legion(org_id: str, legion_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    row = _clean_legion(request.get_json() or {})
    if not row:
        return jsonify({'error': 'No valid legion fields'}), 400
    supabase = _get_supabase()
    res = (
        supabase.table('legions').update(row)
        .eq('organization_id', org_id).eq('id', legion_id).execute()
    )
    if not res.data:
        return jsonify({'error': 'Legion not found'}), 404
    logger.info('Gamification legion updated: org=%s id=%s', org_id, legion_id)
    return jsonify({'legion': res.data[0]})


@gamification_bp.route('/organizations/<org_id>/gamification/legions/<legion_id>', methods=['DELETE'])
def delete_legion(org_id: str, legion_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    supabase.table('legions').delete().eq(
        'organization_id', org_id
    ).eq('id', legion_id).execute()
    logger.info('Gamification legion deleted: org=%s id=%s', org_id, legion_id)
    return jsonify({'status': 'deleted'})


# --- Seasons tab: season CRUD (close is the Next.js job, §8.4) -----------------

def _clean_season(payload: dict) -> dict:
    """Whitelist season fields; blank optional refs become NULL."""
    row = {k: v for k, v in payload.items() if k in ALLOWED_SEASON_FIELDS}
    if row.get('trophy_item_id') == '':
        row['trophy_item_id'] = None
    return row


@gamification_bp.route('/organizations/<org_id>/gamification/seasons', methods=['GET'])
def get_seasons(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    rows = (
        supabase.table('seasons').select(SEASON_SELECT)
        .eq('organization_id', org_id).order('starts_at', desc=True).execute()
    )
    return jsonify({'seasons': rows.data or []})


@gamification_bp.route('/organizations/<org_id>/gamification/seasons', methods=['POST'])
def create_season(org_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    row = _clean_season(request.get_json() or {})
    if not row.get('name') or not row.get('starts_at') or not row.get('ends_at'):
        return jsonify({'error': 'name, starts_at and ends_at are required'}), 400
    # New seasons default to draft; activation is a separate explicit action.
    row.setdefault('status', 'draft')
    row['organization_id'] = org_id
    supabase = _get_supabase()
    res = supabase.table('seasons').insert(row).execute()
    created = res.data[0] if res.data else row
    logger.info('Gamification season created: org=%s name=%s', org_id, row['name'])
    return jsonify({'season': created}), 201


@gamification_bp.route('/organizations/<org_id>/gamification/seasons/<season_id>', methods=['PUT'])
def update_season(org_id: str, season_id: str):
    error = _require_admin(org_id)
    if error:
        return error
    row = _clean_season(request.get_json() or {})
    if not row:
        return jsonify({'error': 'No valid season fields'}), 400
    # Closing is the freeze+trophy job (Next.js), never a bare status flip.
    if row.get('status') == 'closed':
        return jsonify({'error': 'Use the close endpoint to close a season'}), 400

    supabase = _get_supabase()
    # Enforce "one active season per org" before flipping to active.
    if row.get('status') == 'active':
        existing = (
            supabase.table('seasons').select('id')
            .eq('organization_id', org_id).eq('status', 'active').execute()
        )
        clash = [r for r in (existing.data or []) if r.get('id') != season_id]
        if clash:
            return jsonify({'error': 'Another season is already active'}), 409

    res = (
        supabase.table('seasons').update(row)
        .eq('organization_id', org_id).eq('id', season_id).execute()
    )
    if not res.data:
        return jsonify({'error': 'Season not found'}), 404
    logger.info('Gamification season updated: org=%s id=%s', org_id, season_id)
    return jsonify({'season': res.data[0]})


@gamification_bp.route('/organizations/<org_id>/gamification/seasons/<season_id>', methods=['DELETE'])
def delete_season(org_id: str, season_id: str):
    """Delete a season. Closed seasons are history — only draft/active removable."""
    error = _require_admin(org_id)
    if error:
        return error
    supabase = _get_supabase()
    existing = (
        supabase.table('seasons').select('status')
        .eq('organization_id', org_id).eq('id', season_id).single().execute()
    )
    status = existing.data.get('status') if existing.data else None
    if status == 'closed':
        return jsonify({'error': 'Closed seasons cannot be deleted'}), 400
    supabase.table('seasons').delete().eq(
        'organization_id', org_id
    ).eq('id', season_id).execute()
    logger.info('Gamification season deleted: org=%s id=%s', org_id, season_id)
    return jsonify({'status': 'deleted'})


# --- Asset upload: item art / legion crest / rank icon -------------------

@gamification_bp.route('/organizations/<org_id>/gamification/upload', methods=['POST'])
def upload_asset(org_id: str):
    """Upload a cosmetic asset (item art, legion crest, or rank icon).

    Body: multipart/form-data with:
      * file — the image bytes (PNG/JPEG/WebP/SVG, ≤1 MiB)
      * kind — 'item_art', 'legion_crest', or 'rank_icon'

    Each upload gets a unique object key so many assets coexist; the returned
    `{ url }` is written into the catalog row's art_url/crest_url/icon_url. Art is
    swappable without schema impact (D-9), mirroring the branding upload contract.
    """
    error = _require_admin(org_id)
    if error:
        return error

    kind = (request.form.get('kind') or '').strip().lower()
    if kind not in _ASSET_KINDS:
        return jsonify({'error': 'kind must be item_art, legion_crest, or rank_icon'}), 400

    upload = request.files.get('file')
    if upload is None or upload.filename == '':
        return jsonify({'error': 'file is required'}), 400

    mime = (upload.mimetype or '').lower()
    if mime not in _ASSET_ALLOWED_MIME:
        return jsonify({'error': f'Unsupported MIME type: {mime or "unknown"}'}), 415

    payload = upload.read()
    if len(payload) > _ASSET_MAX_BYTES:
        return jsonify({'error': 'File exceeds 1 MiB limit'}), 413
    if not payload:
        return jsonify({'error': 'Empty file'}), 400

    ext = _ASSET_ALLOWED_MIME[mime]
    object_key = f'{org_id}/gamification/{kind}/{uuid.uuid4().hex}.{ext}'

    supabase = _get_supabase()
    bucket = supabase.storage.from_(_ASSET_BUCKET)
    try:
        bucket.upload(
            path=object_key,
            file=payload,
            file_options={'content-type': mime, 'upsert': 'true', 'cache-control': '3600'},
        )
    except Exception as e:  # noqa: BLE001 — surface storage errors as 502
        logger.exception('Gamification asset upload failed: org=%s kind=%s: %s', org_id, kind, e)
        return jsonify({'error': 'Upload failed', 'detail': str(e)}), 502

    public_url = bucket.get_public_url(object_key)
    if isinstance(public_url, str):
        public_url = public_url.rstrip('?')

    logger.info('Gamification asset uploaded: org=%s kind=%s key=%s', org_id, kind, object_key)
    return jsonify({'url': public_url, 'key': object_key, 'kind': kind}), 201
