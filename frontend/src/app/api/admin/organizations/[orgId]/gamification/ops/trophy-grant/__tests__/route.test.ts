import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest, NextResponse } from 'next/server';

vi.mock('@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard', () => ({
  requireOrgAdmin: vi.fn(),
}));
vi.mock('@/lib/gamification/ops', () => ({ grantTrophy: vi.fn() }));

import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { grantTrophy } from '@/lib/gamification/ops';

const m = (fn: unknown) => fn as unknown as {
  mockResolvedValue: (v: unknown) => void;
  mock: { calls: unknown[][] };
};
const params = Promise.resolve({ orgId: 'org-1' });

function post(body: unknown) {
  return new NextRequest('http://x/trophy-grant', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'content-type': 'application/json' },
  });
}

describe('POST ops/trophy-grant', () => {
  beforeEach(() => vi.clearAllMocks());

  it('403s when the guard rejects', async () => {
    m(requireOrgAdmin).mockResolvedValue({
      ok: false,
      response: NextResponse.json({ error: 'Forbidden' }, { status: 403 }),
    });
    const { POST } = await import('../route');
    const res = await POST(post({ student_id: 's1', item_id: 'i1' }), { params });
    expect(res.status).toBe(403);
  });

  it('400s when student_id or item_id is missing', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    const { POST } = await import('../route');
    const res = await POST(post({ student_id: 's1' }), { params });
    expect(res.status).toBe(400);
    expect(grantTrophy).not.toHaveBeenCalled();
  });

  it('grants the trophy', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(grantTrophy).mockResolvedValue({ status: 'ok', granted: 1 });
    const { POST } = await import('../route');
    const res = await POST(post({ student_id: 's1', item_id: 'i1', season_id: 'se1' }), { params });
    expect(res.status).toBe(200);
    expect((await res.json()).granted).toBe(1);
    expect(m(grantTrophy).mock.calls[0]).toEqual([
      'org-1',
      { studentId: 's1', itemId: 'i1', seasonId: 'se1' },
    ]);
  });

  it('404s when the item does not exist', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(grantTrophy).mockResolvedValue({ status: 'item_not_found' });
    const { POST } = await import('../route');
    const res = await POST(post({ student_id: 's1', item_id: 'nope' }), { params });
    expect(res.status).toBe(404);
  });
});
