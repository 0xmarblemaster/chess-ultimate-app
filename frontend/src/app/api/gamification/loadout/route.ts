/**
 * PUT /api/gamification/loadout   body: { slot, item_id | null }
 *
 * Equip an owned item into its slot, or unequip (item_id null). One item per
 * slot (§7.3). Server-validates ownership + slot match before writing, so a
 * client can never equip an item it doesn't own or into the wrong slot.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { equipItem, getInventory, getItems, unequipSlot } from '@/lib/gamification/store';
import { SLOTS, type Slot, validateEquip } from '@/lib/gamification/items';

export const dynamic = 'force-dynamic';

export async function PUT(req: NextRequest) {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const body = await req.json().catch(() => ({}));
  const slot = body?.slot as string | undefined;
  if (!slot || !SLOTS.includes(slot as Slot)) {
    return NextResponse.json({ error: 'valid slot required' }, { status: 400 });
  }

  const itemId = body?.item_id ?? null;

  // Unequip.
  if (itemId === null) {
    await unequipSlot(r.orgId, r.studentId, slot);
    return NextResponse.json({ status: 'unequipped', slot });
  }

  if (typeof itemId !== 'string') {
    return NextResponse.json({ error: 'item_id must be a string or null' }, { status: 400 });
  }

  const [items, inventory] = await Promise.all([
    getItems(r.orgId),
    getInventory(r.orgId, r.studentId),
  ]);
  const item = items.find((it) => it.id === itemId);
  const decision = validateEquip(item, slot, inventory.ownedItemIds);
  if (!decision.ok) {
    return NextResponse.json({ error: decision.reason }, { status: 400 });
  }

  await equipItem(r.orgId, r.studentId, slot, itemId);
  return NextResponse.json({ status: 'equipped', slot, item_id: itemId });
}
