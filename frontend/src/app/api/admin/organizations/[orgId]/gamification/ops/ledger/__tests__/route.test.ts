import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

vi.mock('@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard', () => ({
  requireOrgAdmin: vi.fn(),
}));
vi.mock('@/lib/gamification/ops', () => ({ browseLedger: vi.fn() }));

import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { browseLedger } from '@/lib/gamification/ops';

const m = (fn: unknown) => fn as unknown as {
  mockResolvedValue: (v: unknown) => void;
  mock: { calls: unknown[][] };
};
const params = Promise.resolve({ orgId: 'org-1' });

describe('GET ops/ledger', () => {
  beforeEach(() => vi.clearAllMocks());

  it('403s when the guard rejects', async () => {
    m(requireOrgAdmin).mockResolvedValue({
      ok: false,
      response: NextResponse.json({ error: 'Forbidden' }, { status: 403 }),
    });
    const { GET } = await import('../route');
    const res = await GET(new NextRequest('http://x/ledger'), { params });
    expect(res.status).toBe(403);
  });

  it('forwards student_id, ledger and limit filters', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(browseLedger).mockResolvedValue([{ ledger: 'xp', id: 'x1' }]);
    const { GET } = await import('../route');
    const req = new NextRequest('http://x/ledger?student_id=stu-9&ledger=xp&limit=25');
    const res = await GET(req, { params });
    expect(res.status).toBe(200);
    expect((await res.json()).entries).toHaveLength(1);
    expect(m(browseLedger).mock.calls[0]).toEqual([
      'org-1',
      { studentId: 'stu-9', ledger: 'xp', limit: 25 },
    ]);
  });

  it('defaults ledger to "all" for an unknown kind', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(browseLedger).mockResolvedValue([]);
    const { GET } = await import('../route');
    await GET(new NextRequest('http://x/ledger?ledger=bogus'), { params });
    expect((m(browseLedger).mock.calls[0][1] as { ledger: string }).ledger).toBe('all');
  });
});
