/**
 * GET /api/gamification/inventory
 *
 * The student's owned items (full rows) plus their equipped-per-slot loadout —
 * feeds the avatar customization screen (§7.3). Verified-link required.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getInventory, getItems } from '@/lib/gamification/store';

export const dynamic = 'force-dynamic';

export async function GET() {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const [items, inventory] = await Promise.all([
    getItems(r.orgId),
    getInventory(r.orgId, r.studentId),
  ]);

  const owned = new Set(inventory.ownedItemIds);
  const ownedItems = items.filter((it) => owned.has(it.id));
  return NextResponse.json({ items: ownedItems, loadout: inventory.loadout });
}
