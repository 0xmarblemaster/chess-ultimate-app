/**
 * GET /api/gamification/items
 *
 * Shop catalog for the calling student: every purchasable item grouped by slot
 * with owned/equipped/affordable flags (§7.4). Verified-link required (§7.1);
 * unlinked callers are hidden (D-8).
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getCoinBalance, getInventory, getItems } from '@/lib/gamification/store';
import { buildShopView } from '@/lib/gamification/items';

export const dynamic = 'force-dynamic';

export async function GET() {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const [items, inventory, balance] = await Promise.all([
    getItems(r.orgId),
    getInventory(r.orgId, r.studentId),
    getCoinBalance(r.orgId, r.studentId),
  ]);

  const groups = buildShopView(items, inventory.ownedItemIds, inventory.loadout, balance);
  return NextResponse.json({ balance, slots: groups, loadout: inventory.loadout });
}
