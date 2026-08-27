/**
 * Public branch-picker registration page (`/register`).
 *
 * White-label onboarding entry point. On a tenant host the sign-in footer's
 * РЕГИСТРАЦИЯ link and the sign-up guard both land here. This server component
 * reads the resolved org from the request headers (`x-org-id`, set by
 * middleware), queries `branch_invite_tokens` for that org via the service-role
 * client (active — non-revoked, non-expired — only), dedupes to the newest
 * token per branch, and hands the options to the client `RegisterPicker`.
 *
 * Each branch card links to its existing `/welcome/<token>` flow; the online
 * card links to the online-kind token's `/welcome/<token>`. An empty state
 * (contact info) renders when no active tokens exist.
 */
import type { Metadata } from 'next';
import { headers } from 'next/headers';
import { getTranslations } from 'next-intl/server';
import { supabaseAdmin } from '@/lib/supabase-admin';
import RegisterPicker, { type RegisterOption } from './RegisterPicker';

export const dynamic = 'force-dynamic';

interface TokenRow {
  token: string;
  external_branch_id: string;
  branch_name: string;
  kind: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string | null;
}

interface RegisterOptions {
  branches: RegisterOption[];
  online: RegisterOption | null;
}

/**
 * Resolve the org's active branch-invite tokens into picker options.
 * Filters out revoked/expired tokens, then dedupes to the newest token per
 * branch (and the newest online-kind token overall).
 */
async function loadRegisterOptions(orgId: string): Promise<RegisterOptions> {
  const { data, error } = await supabaseAdmin
    .from('branch_invite_tokens')
    .select('token, external_branch_id, branch_name, kind, expires_at, revoked_at, created_at')
    .eq('organization_id', orgId);

  if (error || !data) return { branches: [], online: null };

  const now = Date.now();
  const active = (data as TokenRow[]).filter((row) => {
    if (row.revoked_at) return false;
    if (row.expires_at && new Date(row.expires_at).getTime() < now) return false;
    return true;
  });

  // Newest first so the first row seen per branch is the freshest token.
  active.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

  const seen = new Set<string>();
  const branches: RegisterOption[] = [];
  let online: RegisterOption | null = null;

  for (const row of active) {
    if (row.kind === 'online') {
      if (!online) online = { token: row.token, branchName: row.branch_name };
      continue;
    }
    if (seen.has(row.external_branch_id)) continue;
    seen.add(row.external_branch_id);
    branches.push({ token: row.token, branchName: row.branch_name });
  }

  return { branches, online };
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('register');
  return { title: t('title') };
}

export default async function RegisterPage() {
  const headersList = await headers();
  const orgId = headersList.get('x-org-id');

  const { branches, online } = orgId
    ? await loadRegisterOptions(orgId)
    : { branches: [], online: null };

  return <RegisterPicker branches={branches} online={online} />;
}
