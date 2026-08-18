import { describe, expect, it } from 'vitest';
import {
  type ItemRow,
  buildShopView,
  evaluatePurchase,
  isAvailable,
  itemName,
  validateEquip,
} from '../items';

function item(over: Partial<ItemRow> = {}): ItemRow {
  return {
    id: 'i1',
    sku: 'shield_iron',
    slot: 'shield',
    rarity: 'common',
    kind: 'purchasable',
    price_coins: 10,
    name_ru: 'Железный щит',
    name_kk: 'Темір қалқан',
    name_en: 'Iron Shield',
    sort_order: 1,
    ...over,
  };
}

describe('itemName', () => {
  it('picks the column for the active locale (kz → name_kk)', () => {
    expect(itemName(item(), 'ru')).toBe('Железный щит');
    expect(itemName(item(), 'kz')).toBe('Темір қалқан');
    expect(itemName(item(), 'en')).toBe('Iron Shield');
  });
});

describe('isAvailable', () => {
  const now = new Date('2026-08-18T00:00:00Z');
  it('true by default', () => {
    expect(isAvailable(item(), now)).toBe(true);
  });
  it('false when explicitly unavailable', () => {
    expect(isAvailable(item({ available: false }), now)).toBe(false);
  });
  it('respects the availability window', () => {
    expect(isAvailable(item({ available_from: '2026-09-01T00:00:00Z' }), now)).toBe(false);
    expect(isAvailable(item({ available_until: '2026-08-01T00:00:00Z' }), now)).toBe(false);
    expect(isAvailable(item({ available_until: '2026-12-01T00:00:00Z' }), now)).toBe(true);
  });
});

describe('evaluatePurchase (mirrors spend_coins)', () => {
  const now = new Date('2026-08-18T00:00:00Z');

  it('ok when affordable, available, unowned', () => {
    expect(evaluatePurchase(item({ price_coins: 10 }), 15, false, now)).toBe('ok');
  });

  it('rejects insufficient balance rather than partial-charging', () => {
    expect(evaluatePurchase(item({ price_coins: 30 }), 15, false, now)).toBe('insufficient_balance');
  });

  it('exact balance is affordable (>= price)', () => {
    expect(evaluatePurchase(item({ price_coins: 15 }), 15, false, now)).toBe('ok');
  });

  it('already-owned is an idempotent no-op', () => {
    expect(evaluatePurchase(item(), 999, true, now)).toBe('already_owned');
  });

  it('trophies and free defaults are not purchasable', () => {
    expect(evaluatePurchase(item({ kind: 'trophy', price_coins: null }), 999, false, now)).toBe('not_purchasable');
    expect(evaluatePurchase(item({ kind: 'default', price_coins: null }), 999, false, now)).toBe('not_purchasable');
  });

  it('unavailable items cannot be bought even with balance', () => {
    expect(evaluatePurchase(item({ available: false }), 999, false, now)).toBe('unavailable');
  });
});

describe('validateEquip', () => {
  it('accepts an owned item into its own slot', () => {
    expect(validateEquip(item(), 'shield', ['i1'])).toEqual({ ok: true });
  });
  it('rejects an unowned item', () => {
    expect(validateEquip(item(), 'shield', ['other'])).toEqual({ ok: false, reason: 'not_owned' });
  });
  it('rejects a slot mismatch', () => {
    expect(validateEquip(item({ slot: 'helmet' }), 'shield', ['i1'])).toEqual({
      ok: false,
      reason: 'slot_mismatch',
    });
  });
  it('rejects a missing item', () => {
    expect(validateEquip(undefined, 'shield', ['i1'])).toEqual({ ok: false, reason: 'not_owned' });
  });
});

describe('buildShopView', () => {
  const items: ItemRow[] = [
    item({ id: 'a', slot: 'shield', sort_order: 2, price_coins: 10 }),
    item({ id: 'b', slot: 'shield', sort_order: 1, price_coins: 30 }),
    item({ id: 'c', slot: 'pet', sort_order: 1, price_coins: 150 }),
    item({ id: 't', slot: 'frame', kind: 'trophy', price_coins: null }),
  ];

  it('groups by slot, sorts by sort_order, and excludes trophies', () => {
    const view = buildShopView(items, ['a'], { shield: 'a' }, 20);
    expect(Object.keys(view).sort()).toEqual(['pet', 'shield']); // no trophy 'frame'
    expect(view.shield.map((i) => i.id)).toEqual(['b', 'a']); // sorted
  });

  it('flags owned/equipped/affordable per item', () => {
    const view = buildShopView(items, ['a'], { shield: 'a' }, 20);
    const a = view.shield.find((i) => i.id === 'a')!;
    const b = view.shield.find((i) => i.id === 'b')!;
    const c = view.pet[0];
    expect(a).toMatchObject({ owned: true, equipped: true, affordable: true });
    expect(b).toMatchObject({ owned: false, equipped: false, affordable: false }); // price 30 > 20
    expect(c).toMatchObject({ owned: false, affordable: false }); // price 150 > 20
  });
});
