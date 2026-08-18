import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest, NextResponse } from 'next/server';

vi.mock('@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard', () => ({
  requireOrgAdmin: vi.fn(),
}));
vi.mock('@/lib/gamification/ops', () => ({ reverseLedgerEntry: vi.fn() }));

import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { reverseLedgerEntry } from '@/lib/gamification/ops';

const m = (fn: unknown) => fn as unknown as { mockResolvedValue: (v: unknown) => void };
const params = Promise.resolve({ orgId: 'org-1' });

function post(body: unknown) {
  return new NextRequest('http://x/reverse', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'content-type': 'application/json' },
  });
}

describe('POST ops/ledger/reverse', () => {
  beforeEach(() => vi.clearAllMocks());

  it('403s when the guard rejects', async () => {
    m(requireOrgAdmin).mockResolvedValue({
      ok: false,
      response: NextResponse.json({ error: 'Forbidden' }, { status: 403 }),
    });
    const { POST } = await import('../route');
    const res = await POST(post({ ledger: 'xp', entry_id: 'x1' }), { params });
    expect(res.status).toBe(403);
  });

  it('400s on a bad body', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    const { POST } = await import('../route');
    const res = await POST(post({ ledger: 'nope' }), { params });
    expect(res.status).toBe(400);
    expect(reverseLedgerEntry).not.toHaveBeenCalled();
  });

  it('reverses an existing entry', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(reverseLedgerEntry).mockResolvedValue({ status: 'ok', student_id: 's1', amount: -3, ledger: 'xp' });
    const { POST } = await import('../route');
    const res = await POST(post({ ledger: 'xp', entry_id: 'x1' }), { params });
    expect(res.status).toBe(200);
    expect((await res.json()).amount).toBe(-3);
  });

  it('404s when the entry is missing', async () => {
    m(requireOrgAdmin).mockResolvedValue({ ok: true, userId: 'u1' });
    m(reverseLedgerEntry).mockResolvedValue({ status: 'not_found' });
    const { POST } = await import('../route');
    const res = await POST(post({ ledger: 'coin', entry_id: 'nope' }), { params });
    expect(res.status).toBe(404);
  });
});
