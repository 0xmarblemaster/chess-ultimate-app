#!/usr/bin/env node
/**
 * Read-only audit: list students stranded after branch-link registration.
 *
 * Two cohorts, both requiring NO organization_members row:
 *  - terminal: a `stranded` or `jwt_expired` claim — the invite JWT expired
 *    beyond grace with no pending_registrations recovery.
 *  - silent: newest attempt is a non-success status (`jwt_missing`, `no_match`,
 *    …) older than SILENT_AGE_HOURS. These users never POST /link/claim (the
 *    client skips it without a stashed JWT), so they never earn a `stranded`
 *    row — without this cohort the listing misses them entirely.
 *
 * Either way only a manual link (scripts/oneoff-link-stuck-students.mjs) — or
 * the student re-opening their branch link — can complete it.
 *
 * Mirrors oneoff-link-stuck-students.mjs env loading. NO writes — pure listing,
 * newest first. Optionally resolves Clerk names for easier identification.
 */
import { readFileSync } from 'node:fs';

const TERMINAL_STATUSES = ['stranded', 'jwt_expired'];
// Every non-success status: a user whose NEWEST attempt is one of these and who
// is still unlinked after SILENT_AGE_HOURS is stranded even without a claim row.
const SILENT_STATUSES = [
  'no_match',
  'multiple_match',
  'jwt_missing',
  'jwt_invalid',
  'jwt_replayed',
  'webhook_error',
];
const SILENT_AGE_HOURS = 24;

const env = {};
for (const line of readFileSync('/root/chess-app/frontend/.env.local', 'utf8').split('\n')) {
  const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, '');
}
const SB_URL = env.NEXT_PUBLIC_SUPABASE_URL;
const SB_KEY = env.SUPABASE_SERVICE_ROLE_KEY;
const CLERK_KEY = env.CLERK_SECRET_KEY;
for (const [k, v] of Object.entries({ SB_URL, SB_KEY })) {
  if (!v) throw new Error(`missing env for ${k}`);
}

async function sb(path) {
  const res = await fetch(`${SB_URL}/rest/v1/${path}`, {
    headers: {
      apikey: SB_KEY,
      Authorization: `Bearer ${SB_KEY}`,
      'Content-Type': 'application/json',
    },
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${path} -> ${res.status}: ${text}`);
  return text ? JSON.parse(text) : null;
}

async function clerkName(uid) {
  if (!CLERK_KEY) return '';
  try {
    const res = await fetch(`https://api.clerk.com/v1/users/${uid}`, {
      headers: { Authorization: `Bearer ${CLERK_KEY}` },
    });
    if (!res.ok) return '';
    const u = await res.json();
    return `${u.first_name || ''} ${u.last_name || ''}`.trim();
  } catch {
    return '';
  }
}

// 1. All non-success link attempts, newest first. Success statuses are excluded
//    so the newest-per-user row below reflects the user's latest FAILURE; a user
//    with any membership row is filtered out regardless.
const statusFilter = [...TERMINAL_STATUSES, ...SILENT_STATUSES].map((s) => `"${s}"`).join(',');
const attempts = await sb(
  `link_attempts?select=user_id,email,status,organization_id,created_at&status=in.(${statusFilter})&order=created_at.desc&limit=2000`,
);

// 2. Already-linked users are not stranded.
const members = await sb('organization_members?select=user_id&limit=5000');
const linked = new Set(members.map((m) => m.user_id));

const orgs = await sb('organizations?select=id,name&limit=200');
const orgById = new Map(orgs.map((o) => [o.id, o.name]));

// 3. Distinct unlinked users, keeping the newest attempt per user.
const byUser = new Map();
for (const a of attempts) {
  if (!a.user_id || linked.has(a.user_id)) continue;
  if (a.email?.endsWith('@test.chesster.io')) continue; // simulator accounts
  if (!byUser.has(a.user_id)) byUser.set(a.user_id, a); // first seen = newest
}

// 4. Terminal cohort always listed; silent cohort only after the grace period —
//    a fresh jwt_missing may still recover via the pending-row/cookie safety net.
const silentCutoff = Date.now() - SILENT_AGE_HOURS * 3600 * 1000;
const rows = [...byUser.values()].filter(
  (a) =>
    TERMINAL_STATUSES.includes(a.status) ||
    new Date(a.created_at).getTime() < silentCutoff,
);

const terminalCount = rows.filter((a) => TERMINAL_STATUSES.includes(a.status)).length;
console.log(
  `Stranded students (no organization_members row): ${rows.length}` +
    ` (${terminalCount} terminal, ${rows.length - terminalCount} silent >${SILENT_AGE_HOURS}h)\n`,
);

for (const a of rows) {
  const name = await clerkName(a.user_id);
  const org = a.organization_id ? orgById.get(a.organization_id) || a.organization_id : 'unknown';
  const cohort = TERMINAL_STATUSES.includes(a.status) ? 'terminal' : 'silent';
  console.log(`── ${a.user_id}`);
  console.log(
    `   email: ${a.email || '?'} | name: ${name || '?'} | status: ${a.status} (${cohort}) | org: ${org} | at: ${a.created_at}`,
  );
}
console.log(rows.length ? '\nRe-link with scripts/oneoff-link-stuck-students.mjs --apply --only user:studentId' : '\nNone.');
