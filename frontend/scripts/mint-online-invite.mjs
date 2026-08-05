#!/usr/bin/env node
/**
 * Mint (or reuse) the single Chess Empire "online students" invite link.
 *
 * Online tokens (`branch_invite_tokens.kind='online'`) skip the CE roster
 * search: a signup enters only a name, then gets a synthetic-student invite JWT
 * carrying `access_ttl_hours`, so the linked member is time-boxed
 * (`access_expires_at = now() + access_ttl_hours`).
 *
 * Idempotent: reuses an existing non-revoked online token for the org rather
 * than minting a second one. Writes the final URL to specs/online-invite-link.txt.
 *
 * Env: reads frontend/.env.local (NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY).
 * Usage: node frontend/scripts/mint-online-invite.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';

const ORG_SLUG = 'chess-empire';
const ACCESS_TTL_HOURS = 72;
const BASE_URL = 'https://chess-empire.chesster.io';
const LINK_FILE = '/root/chess-app/specs/online-invite-link.txt';

const env = {};
for (const line of readFileSync('/root/chess-app/frontend/.env.local', 'utf8').split('\n')) {
  const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '');
}
const SB_URL = env.NEXT_PUBLIC_SUPABASE_URL;
const SB_KEY = env.SUPABASE_SERVICE_ROLE_KEY;
for (const [k, v] of Object.entries({ SB_URL, SB_KEY })) {
  if (!v) throw new Error(`missing env for ${k}`);
}

async function sb(path, init = {}) {
  const res = await fetch(`${SB_URL}/rest/v1/${path}`, {
    ...init,
    headers: {
      apikey: SB_KEY,
      Authorization: `Bearer ${SB_KEY}`,
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${path} -> ${res.status}: ${text}`);
  return text ? JSON.parse(text) : null;
}

const uuid = () => {
  const b = randomBytes(16);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = b.toString('hex');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
};

const [org] = await sb(`organizations?slug=eq.${ORG_SLUG}&select=id&limit=1`);
if (!org) throw new Error(`org '${ORG_SLUG}' not found`);

const existing = await sb(
  `branch_invite_tokens?organization_id=eq.${org.id}&kind=eq.online&revoked_at=is.null&select=token&limit=1`,
);

let token;
if (existing.length > 0) {
  token = existing[0].token;
  console.log('reusing existing online token');
} else {
  const [row] = await sb('branch_invite_tokens', {
    method: 'POST',
    headers: { Prefer: 'return=representation' },
    body: JSON.stringify({
      organization_id: org.id,
      external_branch_id: uuid(),
      branch_name: 'Online Students',
      token: randomBytes(32).toString('hex'),
      kind: 'online',
      access_ttl_hours: ACCESS_TTL_HOURS,
      created_by: 'mint-online-invite-script',
    }),
  });
  token = row.token;
  console.log('minted new online token');
}

const url = `${BASE_URL}/welcome/${token}`;
writeFileSync(LINK_FILE, `${url}\n`);
console.log(url);
console.log(`written to ${LINK_FILE}`);
