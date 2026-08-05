/**
 * Chess Empire ↔ Chesster membership lookup.
 *
 * The apex CE homepage and `/dashboard` on the CE subdomain read from here to
 * decide what to render:
 *  - `no_link` → no `organization_members` row → name-less "we're getting your
 *    profile ready" copy.
 *  - `pending_confirm` → email auto-match found a single student; the user
 *    must confirm on the homepage before we treat it as verified.
 *  - `verified` → normal personalized surface.
 *
 * `getLinkedStudentId` is kept as a thin wrapper that returns the verified
 * student id or null, for callers that only care about the terminal state.
 *
 * Reads `NEXT_PUBLIC_SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` on each call
 * so tests can patch the env without needing to re-import this module — same
 * pattern as `chess-empire-client.ts`.
 *
 * Wrapped in `react cache()` so concurrent server components inside a single
 * render (homepage tree) dedupe the lookup.
 */
import 'server-only';
import { cache } from 'react';
import { createClient } from '@supabase/supabase-js';

export interface GetLinkedStudentIdArgs {
  orgId: string;
  clerkUserId: string;
}

export type MembershipState =
  | 'no_link'
  | 'pending_confirm'
  | 'verified'
  | 'expired';
export type MemberRole = 'student' | 'coach';
export type MemberSource = 'chess_empire' | 'online';

export interface MembershipStateResult {
  state: MembershipState;
  studentId: string | null;
  memberId: string | null;
  /** Member role — 'coach' rows must not be fed to the student profile API. */
  role: MemberRole;
  /** Onboarding track — 'online' members have no CE profile to render. */
  source: MemberSource;
}

interface MemberRow {
  id: string;
  external_student_id: string | null;
  link_status: string | null;
  role: string | null;
  external_source: string | null;
  /** Absolute access expiry; NULL means never expires. */
  access_expires_at: string | null;
}

const SELECT_COLUMNS =
  'id, external_student_id, link_status, role, external_source, access_expires_at';

/** Both onboarding tracks funnel through the same member lookup. */
const MEMBER_SOURCES = ['chess_empire', 'online'] as const;

function serviceClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceKey) {
    throw new Error(
      'chess-empire-member: NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set',
    );
  }
  return createClient(supabaseUrl, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

function rowToState(row: MemberRow | null): MembershipStateResult {
  const noLink: MembershipStateResult = {
    state: 'no_link',
    studentId: null,
    memberId: null,
    role: 'student',
    source: 'chess_empire',
  };
  if (!row || !row.external_student_id) return noLink;

  const role: MemberRole = row.role === 'coach' ? 'coach' : 'student';
  const source: MemberSource =
    row.external_source === 'online' ? 'online' : 'chess_empire';
  if (row.link_status === 'verified') {
    // Time-boxed access (online invites): a verified row whose window has
    // elapsed downgrades to `expired` on every read — no cron, checked live.
    // A null/absent `access_expires_at` means the access never expires.
    const expired = row.access_expires_at
      ? new Date(row.access_expires_at).getTime() < Date.now()
      : false;
    return {
      state: expired ? 'expired' : 'verified',
      studentId: row.external_student_id,
      memberId: row.id,
      role,
      source,
    };
  }
  if (row.link_status === 'pending_confirm') {
    return {
      state: 'pending_confirm',
      studentId: row.external_student_id,
      memberId: row.id,
      role,
      source,
    };
  }
  return noLink;
}

async function fetchMembershipState({
  orgId,
  clerkUserId,
}: GetLinkedStudentIdArgs): Promise<MembershipStateResult> {
  if (!orgId || !clerkUserId) return rowToState(null);

  const supabase = serviceClient();
  const { data, error } = await supabase
    .from('organization_members')
    .select(SELECT_COLUMNS)
    .eq('organization_id', orgId)
    .eq('user_id', clerkUserId)
    .in('external_source', MEMBER_SOURCES)
    .limit(1)
    .maybeSingle();
  if (error) {
    throw new Error(`chess-empire-member: ${error.message}`);
  }
  return rowToState((data ?? null) as MemberRow | null);
}

/**
 * Membership state resolved by Clerk user id alone (no org context).
 *
 * The `/api/chess-empire/link/status` polling endpoint calls this: Chess
 * Empire is a single tenant today, so a user has at most one `chess_empire`
 * member row and org scoping is unnecessary — matching the email-fallback
 * assumption in the webhook.
 */
async function fetchMembershipStateForUser(
  clerkUserId: string,
): Promise<MembershipStateResult> {
  if (!clerkUserId) return rowToState(null);

  const supabase = serviceClient();
  const { data, error } = await supabase
    .from('organization_members')
    .select(SELECT_COLUMNS)
    .eq('user_id', clerkUserId)
    .in('external_source', MEMBER_SOURCES)
    .limit(1)
    .maybeSingle();
  if (error) {
    throw new Error(`chess-empire-member: ${error.message}`);
  }
  return rowToState((data ?? null) as MemberRow | null);
}

async function fetchLinkedStudentId(
  args: GetLinkedStudentIdArgs,
): Promise<string | null> {
  const result = await fetchMembershipState(args);
  return result.state === 'verified' ? result.studentId : null;
}

export const getMembershipState = cache(fetchMembershipState);
export const getMembershipStateForUser = cache(fetchMembershipStateForUser);
export const getLinkedStudentId = cache(fetchLinkedStudentId);
