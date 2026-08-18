import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/gamification/resolve-student', () => ({ resolveStudent: vi.fn() }));
vi.mock('@/lib/gamification/store', () => ({
  getItems: vi.fn(),
  getInventory: vi.fn(),
  equipItem: vi.fn(),
  unequipSlot: vi.fn(),
}));

import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getItems, getInventory, equipItem, unequipSlot } from '@/lib/gamification/store';

const mock = (fn: unknown) => fn as unknown as { mockResolvedValue: (v: unknown) => void };

function req(body: unknown) {
  return { json: async () => body } as unknown as import('next/server').NextRequest;
}

const SHIELD = { id: 'i1', slot: 'shield', kind: 'purchasable' };
const HELMET = { id: 'i2', slot: 'helmet', kind: 'purchasable' };

describe('PUT /api/gamification/loadout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mock(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    mock(getItems).mockResolvedValue([SHIELD, HELMET]);
  });

  it('403 for an unlinked student', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: false, status: 403, error: 'not_linked' });
    const { PUT } = await import('../route');
    const res = await PUT(req({ slot: 'shield', item_id: 'i1' }));
    expect(res.status).toBe(403);
  });

  it('400 for an unknown slot', async () => {
    const { PUT } = await import('../route');
    const res = await PUT(req({ slot: 'nonsense', item_id: 'i1' }));
    expect(res.status).toBe(400);
  });

  it('equips an owned item into its slot', async () => {
    mock(getInventory).mockResolvedValue({ ownedItemIds: ['i1'], loadout: {} });
    const { PUT } = await import('../route');
    const res = await PUT(req({ slot: 'shield', item_id: 'i1' }));
    expect(res.status).toBe(200);
    expect((await res.json()).status).toBe('equipped');
    expect(equipItem).toHaveBeenCalledWith('org-1', 'stu-1', 'shield', 'i1');
  });

  it('rejects equipping an unowned item', async () => {
    mock(getInventory).mockResolvedValue({ ownedItemIds: [], loadout: {} });
    const { PUT } = await import('../route');
    const res = await PUT(req({ slot: 'shield', item_id: 'i1' }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe('not_owned');
    expect(equipItem).not.toHaveBeenCalled();
  });

  it('rejects a slot mismatch (helmet into shield slot)', async () => {
    mock(getInventory).mockResolvedValue({ ownedItemIds: ['i2'], loadout: {} });
    const { PUT } = await import('../route');
    const res = await PUT(req({ slot: 'shield', item_id: 'i2' }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe('slot_mismatch');
    expect(equipItem).not.toHaveBeenCalled();
  });

  it('unequips a slot when item_id is null', async () => {
    const { PUT } = await import('../route');
    const res = await PUT(req({ slot: 'shield', item_id: null }));
    expect(res.status).toBe(200);
    expect((await res.json()).status).toBe('unequipped');
    expect(unequipSlot).toHaveBeenCalledWith('org-1', 'stu-1', 'shield');
  });
});
