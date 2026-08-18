import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextResponse } from 'next/server';

vi.mock('@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard', () => ({
  requireOrgAdmin: vi.fn(),
}));
vi.mock('@/lib/gamification/ops', () => ({ getSyncStatus: vi.fn() }));

import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { getSyncStatus } from '@/lib/gamification/ops';

const m = (fn: unknown) => fn as unknown as { mockResolvedValue: (v: unknown) => void };
const params = Promise.resolve({ orgId: 'org-1' });

describe('GET ops/sync-status', () => {
  beforeEach(() => vi.clearAllMocks());

  it('403s when the guard rejects', async () => {
    m(requireOrgAdmin).mockResolvedValue({
      ok: false,
      response: NextResponse.json({ error: 'Forbidden' }, { status: 403 }),
    });
    const { GET } = await import('../route');
    const res = await GET(new Request('http://x'), { params });
    expect(res.status).toBe(403);
  });

  it('returns the sync status for an admin', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(getSyncStatus).mockResolvedValue({
      last_result_created_at: '2026-03-01T00:00:00Z',
      cursor_initialized_at: '2026-01-01T00:00:00Z',
      last_run_at: '2026-03-01T00:10:00Z',
      last_status: 'ok',
      last_error: null,
    });
    const { GET } = await import('../route');
    const res = await GET(new Request('http://x'), { params });
    expect(res.status).toBe(200);
    expect((await res.json()).status.last_status).toBe('ok');
  });
});
