import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextResponse } from 'next/server';

vi.mock('@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard', () => ({
  requireOrgAdmin: vi.fn(),
}));
vi.mock('@/lib/gamification/sync-run', () => ({ syncOrg: vi.fn() }));

import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { syncOrg } from '@/lib/gamification/sync-run';

const m = (fn: unknown) => fn as unknown as { mockResolvedValue: (v: unknown) => void };
const params = Promise.resolve({ orgId: 'org-1' });

describe('POST ops/sync', () => {
  beforeEach(() => vi.clearAllMocks());

  it('403s when the guard rejects', async () => {
    m(requireOrgAdmin).mockResolvedValue({
      ok: false,
      response: NextResponse.json({ error: 'Forbidden' }, { status: 403 }),
    });
    const { POST } = await import('../route');
    const res = await POST(new Request('http://x', { method: 'POST' }), { params });
    expect(res.status).toBe(403);
    expect(syncOrg).not.toHaveBeenCalled();
  });

  it('runs syncOrg for the org and returns the summary', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(syncOrg).mockResolvedValue({ organization_id: 'org-1', status: 'ok', awarded: 2 });
    const { POST } = await import('../route');
    const res = await POST(new Request('http://x', { method: 'POST' }), { params });
    expect(res.status).toBe(200);
    expect((await res.json()).summary.awarded).toBe(2);
    expect(syncOrg).toHaveBeenCalledWith('org-1');
  });

  it('500s when the sync pass errored', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(syncOrg).mockResolvedValue({ organization_id: 'org-1', status: 'error', error: 'boom' });
    const { POST } = await import('../route');
    const res = await POST(new Request('http://x', { method: 'POST' }), { params });
    expect(res.status).toBe(500);
  });
});
