import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/gamification/resolve-student', () => ({ resolveStudent: vi.fn() }));
vi.mock('@/lib/gamification/store', () => ({
  getItems: vi.fn(),
  getInventory: vi.fn(),
  getCoinBalance: vi.fn(),
}));

import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getItems, getInventory, getCoinBalance } from '@/lib/gamification/store';

const mock = (fn: unknown) => fn as unknown as { mockResolvedValue: (v: unknown) => void };

const ITEMS = [
  { id: 'a', sku: 'shield_iron', slot: 'shield', rarity: 'common', kind: 'purchasable', price_coins: 10, name_ru: '', name_kk: '', name_en: 'Iron', sort_order: 1 },
  { id: 'b', sku: 'pet_dragon', slot: 'pet', rarity: 'legendary', kind: 'purchasable', price_coins: 150, name_ru: '', name_kk: '', name_en: 'Dragon', sort_order: 2 },
  { id: 't', sku: 'trophy', slot: 'frame', rarity: 'legendary', kind: 'trophy', price_coins: null, name_ru: '', name_kk: '', name_en: 'Trophy', sort_order: 3 },
];

describe('GET /api/gamification/items', () => {
  beforeEach(() => vi.clearAllMocks());

  it('403 for an unlinked student', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: false, status: 403, error: 'not_linked' });
    const { GET } = await import('../route');
    const res = await GET();
    expect(res.status).toBe(403);
  });

  it('returns shop groups with owned/affordable flags and hides trophies', async () => {
    mock(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    mock(getItems).mockResolvedValue(ITEMS);
    mock(getInventory).mockResolvedValue({ ownedItemIds: ['a'], loadout: { shield: 'a' } });
    mock(getCoinBalance).mockResolvedValue(20);
    const { GET } = await import('../route');
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.balance).toBe(20);
    expect(Object.keys(body.slots).sort()).toEqual(['pet', 'shield']); // trophy 'frame' excluded
    expect(body.slots.shield[0]).toMatchObject({ id: 'a', owned: true, equipped: true, affordable: true });
    expect(body.slots.pet[0]).toMatchObject({ id: 'b', owned: false, affordable: false });
  });
});
