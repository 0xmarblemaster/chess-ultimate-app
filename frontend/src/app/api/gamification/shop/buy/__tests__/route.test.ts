import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/gamification/resolve-student', () => ({ resolveStudent: vi.fn() }));
vi.mock('@/lib/gamification/store', () => ({ buyItem: vi.fn() }));

import { resolveStudent } from '@/lib/gamification/resolve-student';
import { buyItem } from '@/lib/gamification/store';

const mock = (fn: unknown) => fn as unknown as { mockResolvedValue: (v: unknown) => void };

function req(body: unknown) {
  return { json: async () => body } as unknown as import('next/server').NextRequest;
}

describe('POST /api/gamification/shop/buy', () => {
  beforeEach(() => vi.clearAllMocks());

  it('403 for an unlinked student (D-8)', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: false, status: 403, error: 'not_linked' });
    const { POST } = await import('../route');
    const res = await POST(req({ item_id: 'i1' }));
    expect(res.status).toBe(403);
  });

  it('400 when item_id is missing', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    const { POST } = await import('../route');
    const res = await POST(req({}));
    expect(res.status).toBe(400);
    expect(buyItem).not.toHaveBeenCalled();
  });

  it('200 on a successful purchase', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    mock(buyItem).mockResolvedValue({ status: 'ok', balance: 15, item_id: 'i1' });
    const { POST } = await import('../route');
    const res = await POST(req({ item_id: 'i1' }));
    expect(res.status).toBe(200);
    expect((await res.json()).balance).toBe(15);
    expect(buyItem).toHaveBeenCalledWith('org-1', 'stu-1', 'i1');
  });

  it('200 and no double-charge on an idempotent re-purchase (already_owned)', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    mock(buyItem).mockResolvedValue({ status: 'already_owned', balance: 15 });
    const { POST } = await import('../route');
    const res = await POST(req({ item_id: 'i1' }));
    expect(res.status).toBe(200);
    expect((await res.json()).status).toBe('already_owned');
  });

  it('402 on insufficient balance (rejected, not partially charged)', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    mock(buyItem).mockResolvedValue({ status: 'insufficient_balance', balance: 5, price: 30 });
    const { POST } = await import('../route');
    const res = await POST(req({ item_id: 'i1' }));
    expect(res.status).toBe(402);
    const body = await res.json();
    expect(body.status).toBe('insufficient_balance');
    expect(body.price).toBe(30);
  });

  it('400 for a non-purchasable item (trophy/default)', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    mock(buyItem).mockResolvedValue({ status: 'not_purchasable' });
    const { POST } = await import('../route');
    const res = await POST(req({ item_id: 'i1' }));
    expect(res.status).toBe(400);
  });
});
