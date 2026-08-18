/**
 * Gamification persistence helpers (service-role Supabase IO).
 *
 * Thin wrappers over `supabaseAdmin` for reading org config / rank ladder and
 * recomputing the `player_gamification` read model from the ledgers. All balance
 * columns are SUM(ledger) — never incremented in place (§5.2).
 */
import 'server-only';
import { supabaseAdmin } from '@/lib/supabase-admin';
import {
  type GamificationConfig,
  type RankRow,
  normalizeConfig,
  rankForXp,
  roundHalf,
} from './economy';
import {
  type GamificationProfile,
  type PlayerRow,
  type StreakRow,
  buildProfile,
} from './profile';
import { type ItemRow } from './items';

const ITEM_COLS =
  'id,sku,slot,rarity,kind,price_coins,name_ru,name_kk,name_en,' +
  'description_ru,description_kk,description_en,art_url,anim_url,' +
  'available,available_from,available_until,sort_order';

function num(v: unknown): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return Number.isFinite(n) ? n : 0;
}

/** Org gamification config, merged over defaults. */
export async function getOrgConfig(orgId: string): Promise<GamificationConfig> {
  const { data } = await supabaseAdmin
    .from('gamification_settings')
    .select('config')
    .eq('organization_id', orgId)
    .maybeSingle();
  return normalizeConfig(data?.config);
}

/** Org rank ladder, ascending by sort_order. */
export async function getRanks(orgId: string): Promise<RankRow[]> {
  const { data } = await supabaseAdmin
    .from('gamification_ranks')
    .select('code,name_ru,name_kk,name_en,min_xp,icon_url,sort_order')
    .eq('organization_id', orgId)
    .order('sort_order', { ascending: true });
  return (data ?? []).map((r) => ({ ...r, min_xp: num(r.min_xp) })) as RankRow[];
}

/**
 * Load the full client-facing gamification profile for a linked student.
 * Shared by the profile API route and the Empire homepage render pipeline.
 */
export async function loadGamificationProfile(
  orgId: string,
  studentId: string,
): Promise<GamificationProfile> {
  const [{ data: player }, { data: streak }, ranks, config] = await Promise.all([
    supabaseAdmin
      .from('player_gamification')
      .select('xp_total,coin_balance,rank_code,tournaments_played,wins_total')
      .eq('organization_id', orgId)
      .eq('student_id', studentId)
      .maybeSingle(),
    supabaseAdmin
      .from('streak_state')
      .select('current_weeks,best_weeks,run_start_week,last_active_week')
      .eq('organization_id', orgId)
      .eq('student_id', studentId)
      .maybeSingle(),
    getRanks(orgId),
    getOrgConfig(orgId),
  ]);
  return buildProfile(
    studentId,
    (player as PlayerRow | null) ?? null,
    (streak as StreakRow | null) ?? null,
    ranks,
    config,
  );
}

export interface PlayerAggregate {
  xp_total: number;
  coin_balance: number;
  rank_code: string | null;
  tournaments_played: number;
  wins_total: number;
}

/**
 * Recompute the read model for a set of students from their ledger rows and
 * upsert `player_gamification`. Returns the computed aggregates by student id.
 */
export async function recomputePlayers(
  orgId: string,
  studentIds: string[],
  ranks: RankRow[],
): Promise<Record<string, PlayerAggregate>> {
  const out: Record<string, PlayerAggregate> = {};
  const nowIso = new Date().toISOString();

  for (const sid of studentIds) {
    const [{ data: xpRows }, { data: coinRows }] = await Promise.all([
      supabaseAdmin
        .from('xp_ledger')
        .select('amount,reason,wins')
        .eq('organization_id', orgId)
        .eq('student_id', sid),
      supabaseAdmin
        .from('coin_ledger')
        .select('amount')
        .eq('organization_id', orgId)
        .eq('student_id', sid),
    ]);

    let xpTotal = 0;
    let winsTotal = 0;
    let tournaments = 0;
    for (const r of xpRows ?? []) {
      xpTotal += num(r.amount);
      winsTotal += num(r.wins);
      if (r.reason === 'tournament') tournaments += 1;
      else if (r.reason === 'ce_result_reversed') tournaments -= 1;
    }
    const coinBalance = (coinRows ?? []).reduce((s, r) => s + num(r.amount), 0);

    const agg: PlayerAggregate = {
      xp_total: roundHalf(xpTotal),
      coin_balance: roundHalf(coinBalance),
      rank_code: rankForXp(ranks, roundHalf(xpTotal))?.code ?? null,
      tournaments_played: Math.max(0, tournaments),
      wins_total: roundHalf(winsTotal),
    };
    out[sid] = agg;

    await supabaseAdmin.from('player_gamification').upsert(
      { organization_id: orgId, student_id: sid, ...agg, updated_at: nowIso },
      { onConflict: 'organization_id,student_id' },
    );
  }

  return out;
}

// ---------------------------------------------------------------------------
// Cosmetics IO (Phase 2, §7) — catalog, inventory, loadout, atomic purchase.
// ---------------------------------------------------------------------------

/** Full cosmetic catalog for an org, ascending by sort_order. */
export async function getItems(orgId: string): Promise<ItemRow[]> {
  const { data } = await supabaseAdmin
    .from('items')
    .select(ITEM_COLS)
    .eq('organization_id', orgId)
    .order('sort_order', { ascending: true });
  return (data ?? []).map((r) => ({
    ...r,
    price_coins: r.price_coins == null ? null : num(r.price_coins),
  })) as ItemRow[];
}

export interface Inventory {
  ownedItemIds: string[];
  loadout: Record<string, string>; // slot → item_id
}

/** A student's owned item ids and their equipped-per-slot loadout. */
export async function getInventory(orgId: string, studentId: string): Promise<Inventory> {
  const [{ data: owned }, { data: loadout }] = await Promise.all([
    supabaseAdmin
      .from('player_items')
      .select('item_id')
      .eq('organization_id', orgId)
      .eq('student_id', studentId),
    supabaseAdmin
      .from('player_loadout')
      .select('slot,item_id')
      .eq('organization_id', orgId)
      .eq('student_id', studentId),
  ]);
  const map: Record<string, string> = {};
  for (const r of loadout ?? []) map[r.slot as string] = r.item_id as string;
  return { ownedItemIds: (owned ?? []).map((r) => r.item_id as string), loadout: map };
}

/** Materialized coin balance (authoritative value is SUM(coin_ledger), §5.2). */
export async function getCoinBalance(orgId: string, studentId: string): Promise<number> {
  const { data } = await supabaseAdmin
    .from('player_gamification')
    .select('coin_balance')
    .eq('organization_id', orgId)
    .eq('student_id', studentId)
    .maybeSingle();
  return roundHalf(num(data?.coin_balance));
}

export interface SpendResult {
  status: string;
  balance?: number;
  price?: number;
  item_id?: string;
}

/** Atomic purchase via the spend_coins RPC (balance check + debit + grant). */
export async function buyItem(
  orgId: string,
  studentId: string,
  itemId: string,
): Promise<SpendResult> {
  const { data, error } = await supabaseAdmin.rpc('spend_coins', {
    p_org: orgId,
    p_student: studentId,
    p_item: itemId,
  });
  if (error) throw new Error(error.message);
  return (data ?? { status: 'error' }) as SpendResult;
}

/** Equip an owned item into its slot (one item per slot). */
export async function equipItem(
  orgId: string,
  studentId: string,
  slot: string,
  itemId: string,
): Promise<void> {
  await supabaseAdmin.from('player_loadout').upsert(
    {
      organization_id: orgId,
      student_id: studentId,
      slot,
      item_id: itemId,
      updated_at: new Date().toISOString(),
    },
    { onConflict: 'organization_id,student_id,slot' },
  );
}

/** Clear the equipped item in a slot. */
export async function unequipSlot(
  orgId: string,
  studentId: string,
  slot: string,
): Promise<void> {
  await supabaseAdmin
    .from('player_loadout')
    .delete()
    .eq('organization_id', orgId)
    .eq('student_id', studentId)
    .eq('slot', slot);
}
