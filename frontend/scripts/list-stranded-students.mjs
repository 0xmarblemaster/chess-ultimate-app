#!/usr/bin/env node
/**
 * Read-only audit: list students stranded after branch-link registration.
 *
 * A stranded user has a terminal link_attempts row (`stranded`, or a
 * `jwt_expired` claim that never recovered) and NO organization_members row —
 * their invite JWT expired beyond grace with no pending_registrations recovery,
 * so only a manual link (scripts/oneoff-link-stuck-students.mjs) can complete it.
 *
 * Mirrors oneoff-link-stuck-students.mjs env loading. NO writes — pure listing,
 * newest first. Optionally resolves Clerk names for easier identification.
 */
import { readFileSync } from 'node:fs';

const TERMINAL_STATUSES = ['stranded', 'jwt_expired'];

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

// 1. Terminal / stranded link attempts, newest first.
const statusFilter = TERMINAL_STATUSES.map((s) => `"${s}"`).join(',');
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
  if (!byUser.has(a.user_id)) byUser.set(a.user_id, a); // first seen = newest
}

const rows = [...byUser.values()];
console.log(`Stranded students (terminal link attempt, no organization_members row): ${rows.length}\n`);

for (const a of rows) {
  const name = await clerkName(a.user_id);
  const org = a.organization_id ? orgById.get(a.organization_id) || a.organization_id : 'unknown';
  console.log(`── ${a.user_id}`);
  console.log(
    `   email: ${a.email || '?'} | name: ${name || '?'} | status: ${a.status} | org: ${org} | at: ${a.created_at}`,
  );
}
console.log(rows.length ? '\nRe-link with scripts/oneoff-link-stuck-students.mjs --apply --only user:studentId' : '\nNone.');
