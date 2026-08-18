/**
 * Cosmetics — pure, framework-free logic (PRD-gamification.md §7).
 *
 * Item catalog types plus the deterministic purchase/loadout rules the shop and
 * API layers enforce. The purchase rules here MIRROR the atomic `spend_coins`
 * Postgres RPC (the race-safe source of truth); this pure copy exists so the
 * decision logic is unit-testable without a database, and so routes can reject
 * obviously-invalid requests before hitting the RPC.
 */

export const SLOTS = [
  'shield',
  'armor',
  'cloak',
  'helmet',
  'weapon',
  'pet',
  'background',
  'frame',
  'effect',
] as const;
export type Slot = (typeof SLOTS)[number];

export const RARITIES = ['common', 'rare', 'epic', 'legendary'] as const;
export type Rarity = (typeof RARITIES)[number];

export type ItemKind = 'purchasable' | 'trophy' | 'default';

export interface ItemRow {
  id: string;
  sku: string;
  slot: string;
  rarity: string;
  kind: ItemKind;
  price_coins: number | null;
  name_ru: string;
  name_kk: string;
  name_en: string;
  description_ru?: string | null;
  description_kk?: string | null;
  description_en?: string | null;
  art_url?: string | null;
  anim_url?: string | null;
  available?: boolean;
  available_from?: string | null;
  available_until?: string | null;
  sort_order?: number;
}

/** Localized item name for the active locale (kz → Kazakh column). */
export function itemName(item: ItemRow, locale: string): string {
  if (locale === 'ru') return item.name_ru;
  if (locale === 'kz') return item.name_kk;
  return item.name_en;
}

/** True while the item is on-sale for `now` (available flag + window). */
export function isAvailable(item: ItemRow, now: Date = new Date()): boolean {
  if (item.available === false) return false;
  if (item.available_from && now < new Date(item.available_from)) return false;
  if (item.available_until && now > new Date(item.available_until)) return false;
  return true;
}

export type PurchaseStatus =
  | 'ok'
  | 'already_owned'
  | 'not_purchasable'
  | 'unavailable'
  | 'insufficient_balance';

/**
 * Decide the outcome of a purchase — pure mirror of `spend_coins`. `alreadyOwned`
 * short-circuits to an idempotent no-op (own-once, §7.3); an unaffordable price
 * is rejected, never partially charged.
 */
export function evaluatePurchase(
  item: ItemRow,
  balance: number,
  alreadyOwned: boolean,
  now: Date = new Date(),
): PurchaseStatus {
  if (item.kind !== 'purchasable' || item.price_coins == null) return 'not_purchasable';
  if (!isAvailable(item, now)) return 'unavailable';
  if (alreadyOwned) return 'already_owned';
  if (balance < item.price_coins) return 'insufficient_balance';
  return 'ok';
}

export type EquipDecision = { ok: true } | { ok: false; reason: 'not_owned' | 'slot_mismatch' };

/**
 * Validate an equip request: you can only equip an item you own, and only into
 * its own slot. Loadout holds one item per slot (§7.3).
 */
export function validateEquip(
  item: ItemRow | undefined,
  slot: string,
  ownedItemIds: Iterable<string>,
): EquipDecision {
  if (!item || !new Set(ownedItemIds).has(item.id)) return { ok: false, reason: 'not_owned' };
  if (item.slot !== slot) return { ok: false, reason: 'slot_mismatch' };
  return { ok: true };
}

export interface ShopItemView extends ItemRow {
  owned: boolean;
  equipped: boolean;
  affordable: boolean;
}

/**
 * Project the catalog into the shop view: owned/equipped/affordable flags per
 * item. Only purchasable items belong in the shop; trophies are shown elsewhere
 * (§7.4). Groups are keyed by slot in canonical SLOTS order.
 */
export function buildShopView(
  items: ItemRow[],
  ownedItemIds: Iterable<string>,
  loadout: Record<string, string>,
  balance: number,
  now: Date = new Date(),
): Record<string, ShopItemView[]> {
  const owned = new Set(ownedItemIds);
  const equipped = new Set(Object.values(loadout));
  const groups: Record<string, ShopItemView[]> = {};

  for (const item of items) {
    if (item.kind === 'trophy') continue; // trophy case, never the shop
    const view: ShopItemView = {
      ...item,
      owned: owned.has(item.id),
      equipped: equipped.has(item.id),
      affordable: item.price_coins != null && balance >= item.price_coins,
    };
    (groups[item.slot] ??= []).push(view);
  }

  for (const slot of Object.keys(groups)) {
    groups[slot].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  }
  return groups;
}
