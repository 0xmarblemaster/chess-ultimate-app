'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useOrganization } from '@/contexts/OrganizationContext';
import { AssetUpload } from './AssetUpload';

// Config shape (subset edited in the Rules tab — mirrors gamification_settings.config).
interface StreakConfig {
  bonus_min: number;
  bonus_xp: number;
  milestones: Record<string, number>;
  freeze_windows: Array<{ from: string; until: string; label?: string }>;
}
interface Config {
  participation_xp: number;
  win_xp: Record<string, number>;
  coin_per_xp: number;
  top_n: number;
  min_tournaments_for_trophy: number;
  count_unlinked_in_standings: boolean;
  streak: StreakConfig;
  league_thresholds: { a_min: number; b_min: number };
}
interface Rank {
  code: string;
  name_ru: string;
  name_kk: string;
  name_en: string;
  min_xp: number;
  icon_url?: string | null;
  sort_order: number;
}
interface Item {
  id?: string;
  sku: string;
  slot: string;
  rarity: string;
  kind: string;
  price_coins: number | null;
  name_ru: string;
  name_kk: string;
  name_en: string;
  art_url: string;
  is_placeholder_art?: boolean;
  available?: boolean;
  sort_order: number;
}
interface Legion {
  id?: string;
  name: string;
  ce_branch_id: string | null;
  totem: string;
  crest_url: string;
  color_primary: string;
  color_secondary: string;
  sort_order: number;
}
interface Season {
  id?: string;
  name: string;
  starts_at: string;
  ends_at: string;
  status: string;
  top_n: number;
  trophy_item_id: string | null;
  winner_legion_id?: string | null;
}

interface CoinPackage {
  id?: string;
  coins: number;
  price_kzt: number;
  active: boolean;
  sort_order: number;
}
interface Purchase {
  id: string;
  student_id: string;
  package_id: string | null;
  coins: number;
  amount_kzt: number;
  provider: string;
  provider_ref: string | null;
  status: 'pending' | 'paid' | 'failed' | 'refunded';
  created_at: string;
  paid_at: string | null;
}

interface StandingsPreviewLegion {
  legion: { id: string; name: string; crest_url?: string | null };
  points: number;
  place: number;
  gap_to_first: number;
  member_count: number;
}
interface StandingsPreview {
  top_n: number;
  frozen?: boolean;
  legions: StandingsPreviewLegion[];
}

interface SyncStatus {
  last_result_created_at: string | null;
  cursor_initialized_at: string | null;
  last_run_at: string | null;
  last_status: string | null;
  last_error: string | null;
}
interface LedgerEntry {
  ledger: 'xp' | 'coin';
  id: string;
  student_id: string;
  amount: number;
  reason?: string | null;
  source?: string | null;
  occurred_at: string;
  created_at: string;
}

const WIN_KINDS = ['league_c', 'league_b', 'razryad_4', 'razryad_3', 'rated', 'pro'];
const ITEM_SLOTS = ['shield', 'armor', 'cloak', 'helmet', 'weapon', 'pet', 'background', 'frame', 'effect'];
const ITEM_RARITIES = ['common', 'rare', 'epic', 'legendary'];
const ITEM_KINDS = ['purchasable', 'trophy', 'default'];

/** Trim an ISO/tz timestamp to the `datetime-local` input's `YYYY-MM-DDTHH:mm`. */
function toLocalInput(v: string): string {
  return v ? v.slice(0, 16) : '';
}

/** Human-readable local timestamp for the Ops tab; em-dash on empty/invalid. */
function fmt(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

export default function AdminGamificationPage() {
  const { org } = useOrganization();
  const t = useTranslations('adminGamification');
  const [tab, setTab] = useState<
    'rules' | 'ranks' | 'items' | 'legions' | 'seasons' | 'coins' | 'ops'
  >('rules');
  const [config, setConfig] = useState<Config | null>(null);
  const [ranks, setRanks] = useState<Rank[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [legions, setLegions] = useState<Legion[]>([]);
  const [seasons, setSeasons] = useState<Season[]>([]);
  // Live standings preview per season id (§9.4) — 'loading' while fetching.
  const [standingsPreview, setStandingsPreview] = useState<
    Record<string, StandingsPreview | 'loading'>
  >({});
  const [packages, setPackages] = useState<CoinPackage[]>([]);
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [purchaseFilter, setPurchaseFilter] = useState<'pending' | 'all'>('pending');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newMilestoneWeeks, setNewMilestoneWeeks] = useState('');
  // Ops tab state
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [ledgerStudent, setLedgerStudent] = useState('');
  const [ledgerKind, setLedgerKind] = useState<'all' | 'xp' | 'coin'>('all');
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
  const [grant, setGrant] = useState<{ student_id: string; item_id: string; season_id: string }>({
    student_id: '',
    item_id: '',
    season_id: '',
  });

  const loadItems = () => {
    if (!org?.id) return;
    fetch(`/api/admin/organizations/${org.id}/gamification/items`)
      .then((r) => r.json())
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError(t('errors.loadItems')));
  };

  const loadLegions = () => {
    if (!org?.id) return;
    fetch(`/api/admin/organizations/${org.id}/gamification/legions`)
      .then((r) => r.json())
      .then((d) => setLegions(d.legions ?? []))
      .catch(() => setError(t('errors.loadLegions')));
  };

  const loadSeasons = () => {
    if (!org?.id) return;
    fetch(`/api/admin/organizations/${org.id}/gamification/seasons`)
      .then((r) => r.json())
      .then((d) => setSeasons(d.seasons ?? []))
      .catch(() => setError(t('errors.loadSeasons')));
  };

  useEffect(() => {
    if (!org?.id) return;
    fetch(`/api/admin/organizations/${org.id}/gamification/settings`)
      .then((r) => r.json())
      .then((d) => setConfig(d.config))
      .catch(() => setError(t('errors.loadSettings')));
    fetch(`/api/admin/organizations/${org.id}/gamification/ranks`)
      .then((r) => r.json())
      .then((d) => setRanks(d.ranks ?? []))
      .catch(() => setError(t('errors.loadRanks')));
    loadItems();
    loadLegions();
    loadSeasons();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [org?.id]);

  const flash = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const saveRules = async () => {
    if (!org?.id || !config) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/organizations/${org.id}/gamification/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config }),
      });
      if (!res.ok) throw new Error();
      flash();
    } catch {
      setError(t('errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const saveRanks = async () => {
    if (!org?.id) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin/organizations/${org.id}/gamification/ranks`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ranks }),
      });
      if (!res.ok) throw new Error();
      flash();
    } catch {
      setError(t('errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const saveItem = async (item: Item) => {
    if (!org?.id) return;
    setSaving(true);
    setError(null);
    try {
      const base = `/api/admin/organizations/${org.id}/gamification/items`;
      const res = await fetch(item.id ? `${base}/${item.id}` : base, {
        method: item.id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });
      if (!res.ok) throw new Error();
      loadItems();
      flash();
    } catch {
      setError(t('errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const deleteItem = async (item: Item) => {
    if (!org?.id || !item.id) {
      setItems((prev) => prev.filter((i) => i !== item));
      return;
    }
    setSaving(true);
    try {
      await fetch(`/api/admin/organizations/${org.id}/gamification/items/${item.id}`, {
        method: 'DELETE',
      });
      loadItems();
    } finally {
      setSaving(false);
    }
  };

  const saveLegion = async (legion: Legion) => {
    if (!org?.id) return;
    setSaving(true);
    setError(null);
    try {
      const base = `/api/admin/organizations/${org.id}/gamification/legions`;
      const res = await fetch(legion.id ? `${base}/${legion.id}` : base, {
        method: legion.id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(legion),
      });
      if (!res.ok) throw new Error();
      loadLegions();
      flash();
    } catch {
      setError(t('errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const deleteLegion = async (legion: Legion) => {
    if (!org?.id || !legion.id) {
      setLegions((prev) => prev.filter((l) => l !== legion));
      return;
    }
    setSaving(true);
    try {
      await fetch(`/api/admin/organizations/${org.id}/gamification/legions/${legion.id}`, {
        method: 'DELETE',
      });
      loadLegions();
    } finally {
      setSaving(false);
    }
  };

  const saveSeason = async (season: Season) => {
    if (!org?.id) return;
    setSaving(true);
    setError(null);
    try {
      const base = `/api/admin/organizations/${org.id}/gamification/seasons`;
      const res = await fetch(season.id ? `${base}/${season.id}` : base, {
        method: season.id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(season),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.error || t('errors.save'));
      }
      loadSeasons();
      flash();
    } catch (e) {
      setError((e as Error).message || t('errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const setSeasonStatus = async (season: Season, status: string) => {
    await saveSeason({ ...season, status });
  };

  const closeSeason = async (season: Season) => {
    if (!org?.id || !season.id) return;
    if (!confirm(t('seasons.confirmClose', { name: season.name }))) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/organizations/${org.id}/gamification/seasons/${season.id}/close`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) },
      );
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.error || d.status || t('errors.close'));
      loadSeasons();
      flash();
    } catch (e) {
      setError((e as Error).message || t('errors.close'));
    } finally {
      setSaving(false);
    }
  };

  const deleteSeason = async (season: Season) => {
    if (!org?.id || !season.id) {
      setSeasons((prev) => prev.filter((s) => s !== season));
      return;
    }
    setSaving(true);
    try {
      await fetch(`/api/admin/organizations/${org.id}/gamification/seasons/${season.id}`, {
        method: 'DELETE',
      });
      loadSeasons();
    } finally {
      setSaving(false);
    }
  };

  // Live standings preview (§9.4) — read-only, reuses the standings API/store.
  const previewStandings = async (season: Season) => {
    if (!org?.id || !season.id) return;
    const id = season.id;
    setStandingsPreview((prev) => ({ ...prev, [id]: 'loading' }));
    try {
      const res = await fetch(
        `/api/admin/organizations/${org.id}/gamification/seasons/${id}/standings`,
      );
      if (!res.ok) throw new Error();
      const d = await res.json();
      setStandingsPreview((prev) => ({
        ...prev,
        [id]: { top_n: d.top_n, frozen: d.season?.frozen, legions: d.legions ?? [] },
      }));
    } catch {
      setStandingsPreview((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setError(t('errors.loadStandings'));
    }
  };

  // --- Ops tab: sync status, ledger browser, trophy grant ------------------

  const opsBase = () => `/api/admin/organizations/${org?.id}/gamification/ops`;

  const loadSyncStatus = () => {
    if (!org?.id) return;
    fetch(`${opsBase()}/sync-status`)
      .then((r) => r.json())
      .then((d) => setSyncStatus(d.status ?? null))
      .catch(() => setError(t('errors.loadSyncStatus')));
  };

  const loadLedger = () => {
    if (!org?.id) return;
    const qs = new URLSearchParams();
    if (ledgerStudent) qs.set('student_id', ledgerStudent);
    if (ledgerKind !== 'all') qs.set('ledger', ledgerKind);
    fetch(`${opsBase()}/ledger?${qs.toString()}`)
      .then((r) => r.json())
      .then((d) => setLedgerEntries(d.entries ?? []))
      .catch(() => setError(t('errors.loadLedger')));
  };

  useEffect(() => {
    if (tab === 'ops' && org?.id) {
      loadSyncStatus();
      loadLedger();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, org?.id]);

  const runSync = async () => {
    if (!org?.id) return;
    setSyncing(true);
    setError(null);
    try {
      const res = await fetch(`${opsBase()}/sync`, { method: 'POST' });
      if (!res.ok) throw new Error();
      loadSyncStatus();
      loadLedger();
      flash();
    } catch {
      setError(t('errors.sync'));
    } finally {
      setSyncing(false);
    }
  };

  const reverseEntry = async (entry: LedgerEntry) => {
    if (!org?.id) return;
    if (
      !confirm(
        t('ops.confirmReverse', { ledger: entry.ledger.toUpperCase(), amount: entry.amount }),
      )
    )
      return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${opsBase()}/ledger/reverse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ledger: entry.ledger, entry_id: entry.id }),
      });
      if (!res.ok) throw new Error();
      loadLedger();
      flash();
    } catch {
      setError(t('errors.reversal'));
    } finally {
      setSaving(false);
    }
  };

  const grantTrophy = async () => {
    if (!org?.id || !grant.student_id || !grant.item_id) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${opsBase()}/trophy-grant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: grant.student_id,
          item_id: grant.item_id,
          season_id: grant.season_id || undefined,
        }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.error || d.status || t('errors.grant'));
      setGrant({ student_id: '', item_id: '', season_id: '' });
      flash();
    } catch (e) {
      setError((e as Error).message || t('errors.grant'));
    } finally {
      setSaving(false);
    }
  };

  // --- Coins tab: package CRUD + manual-confirm purchase queue (§10) --------

  const loadPackages = () => {
    if (!org?.id) return;
    fetch(`/api/admin/organizations/${org.id}/gamification/coin-packages`)
      .then((r) => r.json())
      .then((d) => setPackages(d.packages ?? []))
      .catch(() => setError(t('errors.loadPackages')));
  };

  const loadPurchases = () => {
    if (!org?.id) return;
    const qs = purchaseFilter === 'pending' ? '?status=pending' : '';
    fetch(`/api/admin/organizations/${org.id}/gamification/coin-purchases${qs}`)
      .then((r) => r.json())
      .then((d) => setPurchases(d.purchases ?? []))
      .catch(() => setError(t('errors.loadPurchases')));
  };

  useEffect(() => {
    if (tab === 'coins' && org?.id) {
      loadPackages();
      loadPurchases();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, org?.id, purchaseFilter]);

  const savePackage = async (pkg: CoinPackage) => {
    if (!org?.id) return;
    setSaving(true);
    setError(null);
    try {
      const base = `/api/admin/organizations/${org.id}/gamification/coin-packages`;
      const res = await fetch(pkg.id ? `${base}/${pkg.id}` : base, {
        method: pkg.id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pkg),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.error || t('errors.save'));
      }
      loadPackages();
      flash();
    } catch (e) {
      setError((e as Error).message || t('errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const deletePackage = async (pkg: CoinPackage) => {
    if (!org?.id || !pkg.id) {
      setPackages((prev) => prev.filter((p) => p !== pkg));
      return;
    }
    setSaving(true);
    try {
      await fetch(`/api/admin/organizations/${org.id}/gamification/coin-packages/${pkg.id}`, {
        method: 'DELETE',
      });
      loadPackages();
    } finally {
      setSaving(false);
    }
  };

  const purchaseAction = async (p: Purchase, action: 'confirm' | 'refund' | 'reject') => {
    if (!org?.id) return;
    const prompts: Record<typeof action, string> = {
      confirm: t('coins.confirmConfirm', { coins: p.coins }),
      refund: t('coins.confirmRefund'),
      reject: t('coins.confirmReject'),
    };
    if (!confirm(prompts[action])) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/organizations/${org.id}/gamification/coin-purchases/${p.id}/${action}`,
        { method: 'POST' },
      );
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.error || d.current || d.status || t('errors.action'));
      }
      loadPurchases();
      flash();
    } catch (e) {
      setError((e as Error).message || t('errors.action'));
    } finally {
      setSaving(false);
    }
  };

  const numInput = (value: number, onChange: (n: number) => void) => (
    <input
      type="number"
      step="0.5"
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      className="w-24 rounded-lg border border-gray-300 px-2 py-1 text-sm"
    />
  );

  return (
    <div className="p-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">{t('title')}</h1>
      <p className="text-sm text-gray-500 mb-6">{t('subtitle')}</p>

      <div className="flex gap-2 mb-6 flex-wrap">
        {(['rules', 'ranks', 'items', 'legions', 'seasons', 'coins', 'ops'] as const).map((tabKey) => (
          <button
            key={tabKey}
            onClick={() => setTab(tabKey)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              tab === tabKey ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            {t(`tabs.${tabKey}`)}
          </button>
        ))}
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 text-red-600 px-4 py-2 text-sm">{error}</div>}
      {saved && <div className="mb-4 rounded-lg bg-green-50 text-green-600 px-4 py-2 text-sm">{t('saved')}</div>}

      {tab === 'rules' && config && (
        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <h2 className="font-semibold text-gray-900">{t('rules.xpCoinsHeading')}</h2>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('rules.participationXp')}</span>
              {numInput(config.participation_xp, (n) => setConfig({ ...config, participation_xp: n }))}
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('rules.coinsPerXp')}</span>
              {numInput(config.coin_per_xp, (n) => setConfig({ ...config, coin_per_xp: n }))}
            </label>
            <div className="pt-2">
              <div className="text-sm font-medium text-gray-700 mb-2">{t('rules.winXpHeading')}</div>
              <div className="grid grid-cols-2 gap-2">
                {WIN_KINDS.map((kind) => (
                  <label key={kind} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">{kind}</span>
                    {numInput(config.win_xp[kind] ?? 0, (n) =>
                      setConfig({ ...config, win_xp: { ...config.win_xp, [kind]: n } }),
                    )}
                  </label>
                ))}
              </div>
            </div>
          </section>

          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <h2 className="font-semibold text-gray-900">{t('rules.standingsHeading')}</h2>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('rules.topN')}</span>
              {numInput(config.top_n, (n) => setConfig({ ...config, top_n: n }))}
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('rules.minTournaments')}</span>
              {numInput(config.min_tournaments_for_trophy, (n) =>
                setConfig({ ...config, min_tournaments_for_trophy: n }),
              )}
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('rules.countUnlinked')}</span>
              <input
                type="checkbox"
                checked={config.count_unlinked_in_standings}
                onChange={(e) => setConfig({ ...config, count_unlinked_in_standings: e.target.checked })}
                className="h-4 w-4 rounded border-gray-300 text-purple-600"
              />
            </label>
            <div className="pt-2">
              <div className="text-sm font-medium text-gray-700 mb-2">{t('rules.leagueThresholds')}</div>
              <div className="grid grid-cols-2 gap-2">
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{t('rules.aMin')}</span>
                  {numInput(config.league_thresholds.a_min, (n) =>
                    setConfig({
                      ...config,
                      league_thresholds: { ...config.league_thresholds, a_min: n },
                    }),
                  )}
                </label>
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{t('rules.bMin')}</span>
                  {numInput(config.league_thresholds.b_min, (n) =>
                    setConfig({
                      ...config,
                      league_thresholds: { ...config.league_thresholds, b_min: n },
                    }),
                  )}
                </label>
              </div>
            </div>
          </section>

          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <h2 className="font-semibold text-gray-900">{t('rules.streaksHeading')}</h2>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('rules.minStreak')}</span>
              {numInput(config.streak.bonus_min, (n) =>
                setConfig({ ...config, streak: { ...config.streak, bonus_min: n } }),
              )}
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{t('rules.perWeekBonus')}</span>
              {numInput(config.streak.bonus_xp, (n) =>
                setConfig({ ...config, streak: { ...config.streak, bonus_xp: n } }),
              )}
            </label>
            <div className="pt-2">
              <div className="text-sm font-medium text-gray-700 mb-2">{t('rules.milestonesHeading')}</div>
              <div className="space-y-2">
                {Object.entries(config.streak.milestones)
                  .sort((a, b) => Number(a[0]) - Number(b[0]))
                  .map(([weeks, reward]) => (
                    <div key={weeks} className="flex items-center gap-2">
                      <span className="text-sm text-gray-600 w-16">{t('rules.weeksShort', { weeks })}</span>
                      {numInput(reward, (n) =>
                        setConfig({
                          ...config,
                          streak: {
                            ...config.streak,
                            milestones: { ...config.streak.milestones, [weeks]: n },
                          },
                        }),
                      )}
                      <button
                        type="button"
                        onClick={() => {
                          const next = { ...config.streak.milestones };
                          delete next[weeks];
                          setConfig({ ...config, streak: { ...config.streak, milestones: next } });
                        }}
                        className="text-sm text-red-500"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <input
                  type="number"
                  value={newMilestoneWeeks}
                  onChange={(e) => setNewMilestoneWeeks(e.target.value)}
                  placeholder={t('rules.weeksPlaceholder')}
                  className="w-24 rounded-lg border border-gray-300 px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    const w = parseInt(newMilestoneWeeks, 10);
                    if (!w || w <= 0 || config.streak.milestones[String(w)] !== undefined) return;
                    setConfig({
                      ...config,
                      streak: {
                        ...config.streak,
                        milestones: { ...config.streak.milestones, [String(w)]: 0 },
                      },
                    });
                    setNewMilestoneWeeks('');
                  }}
                  className="text-sm text-purple-600"
                >
                  {t('rules.addMilestone')}
                </button>
              </div>
            </div>

            <div className="pt-2">
              <div className="text-sm font-medium text-gray-700 mb-2">{t('rules.freezeHeading')}</div>
              <p className="text-xs text-gray-400 mb-2">{t('rules.freezeHelp')}</p>
              <div className="space-y-2">
                {config.streak.freeze_windows.map((w, i) => {
                  const setWin = (patch: Partial<{ from: string; until: string; label: string }>) => {
                    const next = [...config.streak.freeze_windows];
                    next[i] = { ...w, ...patch };
                    setConfig({ ...config, streak: { ...config.streak, freeze_windows: next } });
                  };
                  return (
                    <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2 items-center">
                      <input
                        type="date"
                        value={w.from ?? ''}
                        onChange={(e) => setWin({ from: e.target.value })}
                        className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                      />
                      <input
                        type="date"
                        value={w.until ?? ''}
                        onChange={(e) => setWin({ until: e.target.value })}
                        className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                      />
                      <input
                        value={w.label ?? ''}
                        placeholder={t('rules.labelPlaceholder')}
                        onChange={(e) => setWin({ label: e.target.value })}
                        className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                      />
                      <button
                        type="button"
                        onClick={() =>
                          setConfig({
                            ...config,
                            streak: {
                              ...config.streak,
                              freeze_windows: config.streak.freeze_windows.filter((_, j) => j !== i),
                            },
                          })
                        }
                        className="text-sm text-red-500"
                      >
                        Remove
                      </button>
                    </div>
                  );
                })}
              </div>
              <button
                type="button"
                onClick={() =>
                  setConfig({
                    ...config,
                    streak: {
                      ...config.streak,
                      freeze_windows: [...config.streak.freeze_windows, { from: '', until: '', label: '' }],
                    },
                  })
                }
                className="mt-2 text-sm text-purple-600"
              >
                {t('rules.addWindow')}
              </button>
            </div>
          </section>

          <button
            onClick={saveRules}
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-purple-600 text-white font-medium disabled:opacity-50"
          >
            {saving ? t('common.saving') : t('rules.saveButton')}
          </button>
        </div>
      )}

      {tab === 'ranks' && (
        <div className="space-y-4">
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="grid grid-cols-[72px_1fr_1fr_1fr_1fr_100px] gap-2 text-xs font-semibold text-gray-500 mb-2">
              <span>{t('ranks.colIcon')}</span>
              <span>{t('ranks.colCode')}</span>
              <span>{t('ranks.colRu')}</span>
              <span>{t('ranks.colKk')}</span>
              <span>{t('ranks.colEn')}</span>
              <span>{t('ranks.colMinXp')}</span>
            </div>
            {ranks.map((rank, i) => (
              <div key={rank.code} className="grid grid-cols-[72px_1fr_1fr_1fr_1fr_100px] gap-2 mb-2 items-start">
                <AssetUpload
                  orgId={org?.id ?? ''}
                  kind="rank_icon"
                  compact
                  value={rank.icon_url ?? ''}
                  onChange={(url) => {
                    const next = [...ranks];
                    next[i] = { ...rank, icon_url: url };
                    setRanks(next);
                  }}
                />
                <input
                  value={rank.code}
                  onChange={(e) => {
                    const next = [...ranks];
                    next[i] = { ...rank, code: e.target.value };
                    setRanks(next);
                  }}
                  className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                />
                {(['name_ru', 'name_kk', 'name_en'] as const).map((field) => (
                  <input
                    key={field}
                    value={rank[field]}
                    onChange={(e) => {
                      const next = [...ranks];
                      next[i] = { ...rank, [field]: e.target.value };
                      setRanks(next);
                    }}
                    className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                  />
                ))}
                <input
                  type="number"
                  value={rank.min_xp}
                  onChange={(e) => {
                    const next = [...ranks];
                    next[i] = { ...rank, min_xp: parseFloat(e.target.value) || 0 };
                    setRanks(next);
                  }}
                  className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                />
              </div>
            ))}
            <button
              onClick={() =>
                setRanks([
                  ...ranks,
                  { code: `rank_${ranks.length + 1}`, name_ru: '', name_kk: '', name_en: '', min_xp: 0, icon_url: '', sort_order: ranks.length + 1 },
                ])
              }
              className="mt-2 text-sm text-purple-600"
            >
              {t('ranks.addRank')}
            </button>
          </section>

          <button
            onClick={saveRanks}
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-purple-600 text-white font-medium disabled:opacity-50"
          >
            {saving ? t('common.saving') : t('ranks.saveButton')}
          </button>
        </div>
      )}

      {tab === 'items' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">{t('items.description')}</p>
          {items.map((item, i) => {
            const set = (patch: Partial<Item>) => {
              const next = [...items];
              next[i] = { ...item, ...patch };
              setItems(next);
            };
            return (
              <section key={item.id ?? `new-${i}`} className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-start gap-3">
                  {item.art_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={item.art_url} alt="" className="w-14 h-14 rounded-lg border border-gray-100" />
                  )}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 flex-1">
                    <input
                      value={item.sku}
                      placeholder={t('items.skuPlaceholder')}
                      onChange={(e) => set({ sku: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <select
                      value={item.slot}
                      onChange={(e) => set({ slot: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    >
                      {ITEM_SLOTS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <select
                      value={item.rarity}
                      onChange={(e) => set({ rarity: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    >
                      {ITEM_RARITIES.map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                    <select
                      value={item.kind}
                      onChange={(e) => set({ kind: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    >
                      {ITEM_KINDS.map((k) => (
                        <option key={k} value={k}>{k}</option>
                      ))}
                    </select>
                    <input
                      value={item.name_en}
                      placeholder={t('items.nameEnPlaceholder')}
                      onChange={(e) => set({ name_en: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      value={item.name_ru}
                      placeholder={t('items.nameRuPlaceholder')}
                      onChange={(e) => set({ name_ru: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      value={item.name_kk}
                      placeholder={t('items.nameKkPlaceholder')}
                      onChange={(e) => set({ name_kk: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      type="number"
                      value={item.price_coins ?? ''}
                      placeholder={t('items.pricePlaceholder')}
                      onChange={(e) =>
                        set({ price_coins: e.target.value === '' ? null : parseInt(e.target.value, 10) })
                      }
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <AssetUpload
                      orgId={org?.id ?? ''}
                      kind="item_art"
                      value={item.art_url}
                      onChange={(url) => set({ art_url: url })}
                      placeholder={t('items.artPlaceholder')}
                      className="col-span-2 md:col-span-4"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2 mt-3">
                  <button
                    onClick={() => deleteItem(item)}
                    className="text-sm text-red-500 px-3 py-1"
                  >
                    {t('common.delete')}
                  </button>
                  <button
                    onClick={() => saveItem(item)}
                    disabled={saving}
                    className="rounded-lg bg-purple-600 text-white px-4 py-1 text-sm font-medium disabled:opacity-50"
                  >
                    {t('common.save')}
                  </button>
                </div>
              </section>
            );
          })}
          <button
            onClick={() =>
              setItems([
                ...items,
                {
                  sku: '',
                  slot: 'shield',
                  rarity: 'common',
                  kind: 'purchasable',
                  price_coins: 10,
                  name_ru: '',
                  name_kk: '',
                  name_en: '',
                  art_url: '',
                  sort_order: items.length + 1,
                },
              ])
            }
            className="text-sm text-purple-600"
          >
            {t('items.addItem')}
          </button>
        </div>
      )}

      {tab === 'legions' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">{t('legions.description')}</p>
          {legions.map((legion, i) => {
            const set = (patch: Partial<Legion>) => {
              const next = [...legions];
              next[i] = { ...legion, ...patch };
              setLegions(next);
            };
            return (
              <section key={legion.id ?? `new-${i}`} className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-start gap-3">
                  {legion.crest_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={legion.crest_url} alt="" className="w-14 h-14" />
                  )}
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 flex-1">
                    <input
                      value={legion.name}
                      placeholder={t('legions.namePlaceholder')}
                      onChange={(e) => set({ name: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      value={legion.totem ?? ''}
                      placeholder={t('legions.totemPlaceholder')}
                      onChange={(e) => set({ totem: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      value={legion.ce_branch_id ?? ''}
                      placeholder={t('legions.branchIdPlaceholder')}
                      onChange={(e) => set({ ce_branch_id: e.target.value || null })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <AssetUpload
                      orgId={org?.id ?? ''}
                      kind="legion_crest"
                      value={legion.crest_url ?? ''}
                      onChange={(url) => set({ crest_url: url })}
                      placeholder={t('legions.crestPlaceholder')}
                      className="col-span-2 md:col-span-3"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={legion.color_primary || '#38bdf8'}
                        onChange={(e) => set({ color_primary: e.target.value })}
                        className="h-8 w-10 rounded border border-gray-300"
                      />
                      <input
                        type="color"
                        value={legion.color_secondary || '#0369a1'}
                        onChange={(e) => set({ color_secondary: e.target.value })}
                        className="h-8 w-10 rounded border border-gray-300"
                      />
                    </div>
                  </div>
                </div>
                <div className="flex justify-end gap-2 mt-3">
                  <button onClick={() => deleteLegion(legion)} className="text-sm text-red-500 px-3 py-1">
                    {t('common.delete')}
                  </button>
                  <button
                    onClick={() => saveLegion(legion)}
                    disabled={saving}
                    className="rounded-lg bg-purple-600 text-white px-4 py-1 text-sm font-medium disabled:opacity-50"
                  >
                    {t('common.save')}
                  </button>
                </div>
              </section>
            );
          })}
          <button
            onClick={() =>
              setLegions([
                ...legions,
                {
                  name: '',
                  ce_branch_id: null,
                  totem: '',
                  crest_url: '',
                  color_primary: '#38bdf8',
                  color_secondary: '#0369a1',
                  sort_order: legions.length + 1,
                },
              ])
            }
            className="text-sm text-purple-600"
          >
            {t('legions.addLegion')}
          </button>
        </div>
      )}

      {tab === 'seasons' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">{t('seasons.description')}</p>
          {seasons.map((season, i) => {
            const set = (patch: Partial<Season>) => {
              const next = [...seasons];
              next[i] = { ...season, ...patch };
              setSeasons(next);
            };
            const frozen = season.ends_at ? new Date(season.ends_at).getTime() <= Date.now() : false;
            const preview = season.id ? standingsPreview[season.id] : undefined;
            return (
              <section key={season.id ?? `new-${i}`} className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <input
                    value={season.name}
                    placeholder={t('seasons.namePlaceholder')}
                    onChange={(e) => set({ name: e.target.value })}
                    className="rounded-lg border border-gray-300 px-2 py-1 text-sm font-medium flex-1 mr-3"
                  />
                  <span
                    className={`text-xs font-semibold px-2 py-1 rounded-full ${
                      season.status === 'active'
                        ? 'bg-green-100 text-green-700'
                        : season.status === 'closed'
                          ? 'bg-gray-200 text-gray-600'
                          : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {season.status}
                    {season.status === 'active' && frozen ? t('seasons.frozenSuffix') : ''}
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  <label className="text-xs text-gray-500">
                    {t('seasons.starts')}
                    <input
                      type="datetime-local"
                      value={toLocalInput(season.starts_at)}
                      disabled={season.status === 'closed'}
                      onChange={(e) => set({ starts_at: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                  </label>
                  <label className="text-xs text-gray-500">
                    {t('seasons.ends')}
                    <input
                      type="datetime-local"
                      value={toLocalInput(season.ends_at)}
                      disabled={season.status === 'closed'}
                      onChange={(e) => set({ ends_at: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                  </label>
                  <label className="text-xs text-gray-500">
                    {t('seasons.topN')}
                    <input
                      type="number"
                      value={season.top_n ?? 5}
                      disabled={season.status === 'closed'}
                      onChange={(e) => set({ top_n: parseInt(e.target.value, 10) || 5 })}
                      className="w-full rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                  </label>
                  <label className="text-xs text-gray-500 md:col-span-3">
                    {t('seasons.trophyItem')}
                    <select
                      value={season.trophy_item_id ?? ''}
                      disabled={season.status === 'closed'}
                      onChange={(e) => set({ trophy_item_id: e.target.value || null })}
                      className="w-full rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    >
                      <option value="">{t('seasons.trophyNone')}</option>
                      {items
                        .filter((it) => it.kind === 'trophy' && it.id)
                        .map((it) => (
                          <option key={it.id} value={it.id}>
                            {it.name_en || it.sku}
                          </option>
                        ))}
                    </select>
                  </label>
                </div>
                {season.status !== 'closed' && (
                  <div className="flex flex-wrap justify-end gap-2 mt-3">
                    <button onClick={() => deleteSeason(season)} className="text-sm text-red-500 px-3 py-1">
                      {t('common.delete')}
                    </button>
                    {season.status === 'draft' && season.id && (
                      <button
                        onClick={() => setSeasonStatus(season, 'active')}
                        disabled={saving}
                        className="rounded-lg bg-green-600 text-white px-4 py-1 text-sm font-medium disabled:opacity-50"
                      >
                        {t('seasons.activate')}
                      </button>
                    )}
                    {season.status === 'active' && season.id && (
                      <button
                        onClick={() => closeSeason(season)}
                        disabled={saving}
                        className="rounded-lg bg-amber-600 text-white px-4 py-1 text-sm font-medium disabled:opacity-50"
                      >
                        {t('seasons.closeAward')}
                      </button>
                    )}
                    <button
                      onClick={() => saveSeason(season)}
                      disabled={saving}
                      className="rounded-lg bg-purple-600 text-white px-4 py-1 text-sm font-medium disabled:opacity-50"
                    >
                      {t('common.save')}
                    </button>
                  </div>
                )}

                {season.id && (
                  <div className="mt-3 border-t border-gray-100 pt-3">
                    <button
                      type="button"
                      onClick={() => previewStandings(season)}
                      disabled={preview === 'loading'}
                      className="text-sm text-purple-600 font-medium disabled:opacity-50"
                    >
                      {preview === 'loading'
                        ? t('seasons.loadingStandings')
                        : preview
                          ? t('seasons.refreshStandings')
                          : t('seasons.previewStandings')}
                    </button>
                    {preview && preview !== 'loading' && (
                      <div className="mt-3">
                        <div className="text-xs text-gray-400 mb-2">
                          {t('seasons.standingsMeta', { topN: preview.top_n })}
                          {preview.frozen ? t('seasons.standingsFrozen') : ''}
                        </div>
                        {preview.legions.length === 0 ? (
                          <p className="text-sm text-gray-400">{t('seasons.noStandings')}</p>
                        ) : (
                          <div className="space-y-1">
                            {preview.legions.map((row) => (
                              <div
                                key={row.legion.id}
                                className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2"
                              >
                                <span className="w-6 text-center font-bold text-gray-400">
                                  {row.place}
                                </span>
                                {row.legion.crest_url && (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img src={row.legion.crest_url} alt="" className="w-7 h-7" />
                                )}
                                <span className="flex-1 text-sm font-medium text-gray-800">
                                  {row.legion.name}
                                </span>
                                <span className="text-xs text-gray-400">
                                  {t('seasons.members', { count: row.member_count })}
                                </span>
                                <span className="w-16 text-right font-bold text-purple-600">
                                  {row.points}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </section>
            );
          })}
          <button
            onClick={() =>
              setSeasons([
                {
                  name: '',
                  starts_at: '',
                  ends_at: '',
                  status: 'draft',
                  top_n: 5,
                  trophy_item_id: null,
                },
                ...seasons,
              ])
            }
            className="text-sm text-purple-600"
          >
            {t('seasons.addSeason')}
          </button>
        </div>
      )}

      {tab === 'coins' && (
        <div className="space-y-6">
          {/* Base rate + packages (all pricing is admin-created — D-6) */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">{t('coins.packagesHeading')}</h2>
              <span className="text-xs text-gray-400">
                {t('coins.baseRate', { coins: config?.coin_per_xp ?? 1 })}
              </span>
            </div>
            <p className="text-sm text-gray-500">{t('coins.packagesDescription')}</p>
            <div className="grid grid-cols-[1fr_1fr_1fr_auto_auto_auto] gap-2 text-xs font-semibold text-gray-500">
              <span>{t('coins.colCoins')}</span>
              <span>{t('coins.colPrice')}</span>
              <span>{t('coins.colPerCoin')}</span>
              <span>{t('coins.colOrder')}</span>
              <span>{t('coins.colActive')}</span>
              <span></span>
            </div>
            {packages.map((pkg, i) => {
              const set = (patch: Partial<CoinPackage>) => {
                const next = [...packages];
                next[i] = { ...pkg, ...patch };
                setPackages(next);
              };
              const perCoin = pkg.coins > 0 ? (pkg.price_kzt / pkg.coins).toFixed(1) : '—';
              return (
                <div
                  key={pkg.id ?? `new-${i}`}
                  className="grid grid-cols-[1fr_1fr_1fr_auto_auto_auto] gap-2 items-center"
                >
                  <input
                    type="number"
                    value={pkg.coins}
                    onChange={(e) => set({ coins: parseInt(e.target.value, 10) || 0 })}
                    className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                  />
                  <input
                    type="number"
                    value={pkg.price_kzt}
                    onChange={(e) => set({ price_kzt: parseInt(e.target.value, 10) || 0 })}
                    className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                  />
                  <span className="text-sm text-gray-500">{perCoin}</span>
                  <input
                    type="number"
                    value={pkg.sort_order}
                    onChange={(e) => set({ sort_order: parseInt(e.target.value, 10) || 0 })}
                    className="w-16 rounded-lg border border-gray-300 px-2 py-1 text-sm"
                  />
                  <input
                    type="checkbox"
                    checked={pkg.active}
                    onChange={(e) => set({ active: e.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-purple-600"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => savePackage(pkg)}
                      disabled={saving}
                      className="rounded-lg bg-purple-600 text-white px-3 py-1 text-sm font-medium disabled:opacity-50"
                    >
                      {t('common.save')}
                    </button>
                    <button
                      onClick={() => deletePackage(pkg)}
                      className="text-sm text-red-500 px-1"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              );
            })}
            <button
              onClick={() =>
                setPackages([
                  ...packages,
                  { coins: 100, price_kzt: 500, active: true, sort_order: packages.length + 1 },
                ])
              }
              className="text-sm text-purple-600"
            >
              {t('coins.addPackage')}
            </button>
          </section>

          {/* Manual-confirm queue */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">{t('coins.queueHeading')}</h2>
              <select
                value={purchaseFilter}
                onChange={(e) => setPurchaseFilter(e.target.value as 'pending' | 'all')}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
              >
                <option value="pending">{t('coins.filterPending')}</option>
                <option value="all">{t('coins.filterAll')}</option>
              </select>
            </div>
            <p className="text-sm text-gray-500">{t('coins.queueDescription')}</p>
            {purchases.length === 0 ? (
              <p className="text-sm text-gray-400">{t('coins.noPurchases')}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500">
                      <th className="py-1 pr-2 font-medium">{t('coins.colWhen')}</th>
                      <th className="pr-2 font-medium">{t('coins.colStudent')}</th>
                      <th className="pr-2 font-medium">{t('coins.colCoins')}</th>
                      <th className="pr-2 font-medium">{t('coins.colKzt')}</th>
                      <th className="pr-2 font-medium">{t('coins.colProvider')}</th>
                      <th className="pr-2 font-medium">{t('coins.colStatus')}</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {purchases.map((p) => (
                      <tr key={p.id} className="border-t border-gray-100">
                        <td className="py-1 pr-2 text-gray-500 whitespace-nowrap">{fmt(p.created_at)}</td>
                        <td className="pr-2 text-gray-600 font-mono text-xs break-all">{p.student_id}</td>
                        <td className="pr-2 font-medium text-gray-900">{p.coins}</td>
                        <td className="pr-2 text-gray-500">{p.amount_kzt}</td>
                        <td className="pr-2 text-gray-500">{p.provider}</td>
                        <td className="pr-2">
                          <span
                            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                              p.status === 'paid'
                                ? 'bg-green-100 text-green-700'
                                : p.status === 'pending'
                                  ? 'bg-amber-100 text-amber-700'
                                  : p.status === 'refunded'
                                    ? 'bg-blue-100 text-blue-700'
                                    : 'bg-gray-200 text-gray-600'
                            }`}
                          >
                            {p.status}
                          </span>
                        </td>
                        <td className="text-right whitespace-nowrap">
                          {p.status === 'pending' && (
                            <>
                              <button
                                onClick={() => purchaseAction(p, 'confirm')}
                                disabled={saving}
                                className="text-xs text-green-600 font-medium disabled:opacity-50 mr-2"
                              >
                                {t('coins.confirm')}
                              </button>
                              <button
                                onClick={() => purchaseAction(p, 'reject')}
                                disabled={saving}
                                className="text-xs text-gray-500 disabled:opacity-50"
                              >
                                {t('coins.reject')}
                              </button>
                            </>
                          )}
                          {p.status === 'paid' && (
                            <button
                              onClick={() => purchaseAction(p, 'refund')}
                              disabled={saving}
                              className="text-xs text-red-500 disabled:opacity-50"
                            >
                              {t('coins.refund')}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {tab === 'ops' && (
        <div className="space-y-6">
          {/* Sync status + Sync now */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">{t('ops.syncHeading')}</h2>
              <button
                onClick={runSync}
                disabled={syncing}
                className="px-4 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium disabled:opacity-50"
              >
                {syncing ? t('ops.syncing') : t('ops.syncNow')}
              </button>
            </div>
            {syncStatus ? (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                <dt className="text-gray-500">{t('ops.lastRun')}</dt>
                <dd className="text-gray-900">{fmt(syncStatus.last_run_at)}</dd>
                <dt className="text-gray-500">{t('ops.status')}</dt>
                <dd className={syncStatus.last_status === 'error' ? 'text-red-600' : 'text-gray-900'}>
                  {syncStatus.last_status ?? '—'}
                </dd>
                <dt className="text-gray-500">{t('ops.cursor')}</dt>
                <dd className="text-gray-900">{fmt(syncStatus.last_result_created_at)}</dd>
                <dt className="text-gray-500">{t('ops.initialized')}</dt>
                <dd className="text-gray-900">{fmt(syncStatus.cursor_initialized_at)}</dd>
                {syncStatus.last_error && (
                  <>
                    <dt className="text-gray-500">{t('ops.lastError')}</dt>
                    <dd className="text-red-600 break-all">{syncStatus.last_error}</dd>
                  </>
                )}
              </dl>
            ) : (
              <p className="text-sm text-gray-400">{t('ops.syncNever')}</p>
            )}
          </section>

          {/* Award audit log — ledger browser + reversal */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <h2 className="font-semibold text-gray-900">{t('ops.auditHeading')}</h2>
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={ledgerStudent}
                onChange={(e) => setLedgerStudent(e.target.value)}
                placeholder={t('ops.filterStudentPlaceholder')}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm flex-1 min-w-[160px]"
              />
              <select
                value={ledgerKind}
                onChange={(e) => setLedgerKind(e.target.value as 'all' | 'xp' | 'coin')}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
              >
                <option value="all">{t('ops.filterAll')}</option>
                <option value="xp">{t('ops.filterXp')}</option>
                <option value="coin">{t('ops.filterCoin')}</option>
              </select>
              <button
                onClick={loadLedger}
                className="px-3 py-1 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium"
              >
                {t('ops.apply')}
              </button>
            </div>
            {ledgerEntries.length === 0 ? (
              <p className="text-sm text-gray-400">{t('ops.noLedger')}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500">
                      <th className="py-1 pr-2 font-medium">{t('ops.colWhen')}</th>
                      <th className="pr-2 font-medium">{t('ops.colLedger')}</th>
                      <th className="pr-2 font-medium">{t('ops.colStudent')}</th>
                      <th className="pr-2 font-medium">{t('ops.colAmount')}</th>
                      <th className="pr-2 font-medium">{t('ops.colReason')}</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {ledgerEntries.map((e) => (
                      <tr key={`${e.ledger}-${e.id}`} className="border-t border-gray-100">
                        <td className="py-1 pr-2 text-gray-500 whitespace-nowrap">{fmt(e.occurred_at)}</td>
                        <td className="pr-2 uppercase text-gray-600">{e.ledger}</td>
                        <td className="pr-2 text-gray-600 font-mono text-xs break-all">{e.student_id}</td>
                        <td className={`pr-2 font-medium ${e.amount < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                          {e.amount}
                        </td>
                        <td className="pr-2 text-gray-500">{e.reason ?? e.source ?? '—'}</td>
                        <td className="text-right">
                          <button
                            onClick={() => reverseEntry(e)}
                            disabled={saving}
                            className="text-xs text-red-500 disabled:opacity-50"
                          >
                            {t('ops.reverse')}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Manual trophy grant */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <h2 className="font-semibold text-gray-900">{t('ops.grantHeading')}</h2>
            <p className="text-sm text-gray-500">{t('ops.grantDescription')}</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <input
                value={grant.student_id}
                onChange={(e) => setGrant({ ...grant, student_id: e.target.value })}
                placeholder={t('ops.studentIdPlaceholder')}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
              />
              <select
                value={grant.item_id}
                onChange={(e) => setGrant({ ...grant, item_id: e.target.value })}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
              >
                <option value="">{t('ops.trophyItemOption')}</option>
                {items
                  .filter((it) => it.kind === 'trophy' && it.id)
                  .map((it) => (
                    <option key={it.id} value={it.id}>
                      {it.name_en || it.sku}
                    </option>
                  ))}
              </select>
              <select
                value={grant.season_id}
                onChange={(e) => setGrant({ ...grant, season_id: e.target.value })}
                className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
              >
                <option value="">{t('ops.seasonOption')}</option>
                {seasons
                  .filter((s) => s.id)
                  .map((s) => (
                    <option key={s.id} value={s.id!}>
                      {s.name}
                    </option>
                  ))}
              </select>
            </div>
            <button
              onClick={grantTrophy}
              disabled={saving || !grant.student_id || !grant.item_id}
              className="px-5 py-2 rounded-lg bg-purple-600 text-white font-medium disabled:opacity-50"
            >
              {t('ops.grantTrophy')}
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
