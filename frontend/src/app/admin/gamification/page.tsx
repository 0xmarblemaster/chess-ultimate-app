'use client';

import { useEffect, useState } from 'react';
import { useOrganization } from '@/contexts/OrganizationContext';

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

const WIN_KINDS = ['league_c', 'league_b', 'razryad_4', 'razryad_3', 'rated', 'pro'];
const ITEM_SLOTS = ['shield', 'armor', 'cloak', 'helmet', 'weapon', 'pet', 'background', 'frame', 'effect'];
const ITEM_RARITIES = ['common', 'rare', 'epic', 'legendary'];
const ITEM_KINDS = ['purchasable', 'trophy', 'default'];

export default function AdminGamificationPage() {
  const { org } = useOrganization();
  const [tab, setTab] = useState<'rules' | 'ranks' | 'items'>('rules');
  const [config, setConfig] = useState<Config | null>(null);
  const [ranks, setRanks] = useState<Rank[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadItems = () => {
    if (!org?.id) return;
    fetch(`/api/admin/organizations/${org.id}/gamification/items`)
      .then((r) => r.json())
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError('Failed to load items'));
  };

  useEffect(() => {
    if (!org?.id) return;
    fetch(`/api/admin/organizations/${org.id}/gamification/settings`)
      .then((r) => r.json())
      .then((d) => setConfig(d.config))
      .catch(() => setError('Failed to load settings'));
    fetch(`/api/admin/organizations/${org.id}/gamification/ranks`)
      .then((r) => r.json())
      .then((d) => setRanks(d.ranks ?? []))
      .catch(() => setError('Failed to load ranks'));
    loadItems();
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
      setError('Save failed');
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
      setError('Save failed');
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
      setError('Save failed');
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
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Gamification</h1>
      <p className="text-sm text-gray-500 mb-6">
        Configure XP rates, coins, streaks and the rank ladder. Nothing is hardcoded — these values
        drive the sync engine and profiles.
      </p>

      <div className="flex gap-2 mb-6">
        {(['rules', 'ranks', 'items'] as const).map((tabKey) => (
          <button
            key={tabKey}
            onClick={() => setTab(tabKey)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${
              tab === tabKey ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            {tabKey}
          </button>
        ))}
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 text-red-600 px-4 py-2 text-sm">{error}</div>}
      {saved && <div className="mb-4 rounded-lg bg-green-50 text-green-600 px-4 py-2 text-sm">Saved ✓</div>}

      {tab === 'rules' && config && (
        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <h2 className="font-semibold text-gray-900">XP & coins</h2>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Participation XP</span>
              {numInput(config.participation_xp, (n) => setConfig({ ...config, participation_xp: n }))}
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Coins per XP</span>
              {numInput(config.coin_per_xp, (n) => setConfig({ ...config, coin_per_xp: n }))}
            </label>
            <div className="pt-2">
              <div className="text-sm font-medium text-gray-700 mb-2">Win XP by tournament kind</div>
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
            <h2 className="font-semibold text-gray-900">Streaks</h2>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Min streak for bonus (weeks)</span>
              {numInput(config.streak.bonus_min, (n) =>
                setConfig({ ...config, streak: { ...config.streak, bonus_min: n } }),
              )}
            </label>
            <label className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Per-week bonus XP</span>
              {numInput(config.streak.bonus_xp, (n) =>
                setConfig({ ...config, streak: { ...config.streak, bonus_xp: n } }),
              )}
            </label>
            <div className="pt-2">
              <div className="text-sm font-medium text-gray-700 mb-2">Milestones (weeks → XP)</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(config.streak.milestones).map(([weeks, reward]) => (
                  <label key={weeks} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">{weeks} wk</span>
                    {numInput(reward, (n) =>
                      setConfig({
                        ...config,
                        streak: {
                          ...config.streak,
                          milestones: { ...config.streak.milestones, [weeks]: n },
                        },
                      }),
                    )}
                  </label>
                ))}
              </div>
            </div>
          </section>

          <button
            onClick={saveRules}
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-purple-600 text-white font-medium disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save rules'}
          </button>
        </div>
      )}

      {tab === 'ranks' && (
        <div className="space-y-4">
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="grid grid-cols-[1fr_1fr_1fr_1fr_100px] gap-2 text-xs font-semibold text-gray-500 mb-2">
              <span>Code</span>
              <span>RU</span>
              <span>KK</span>
              <span>EN</span>
              <span>Min XP</span>
            </div>
            {ranks.map((rank, i) => (
              <div key={rank.code} className="grid grid-cols-[1fr_1fr_1fr_1fr_100px] gap-2 mb-2">
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
                  { code: `rank_${ranks.length + 1}`, name_ru: '', name_kk: '', name_en: '', min_xp: 0, sort_order: ranks.length + 1 },
                ])
              }
              className="mt-2 text-sm text-purple-600"
            >
              + Add rank
            </button>
          </section>

          <button
            onClick={saveRanks}
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-purple-600 text-white font-medium disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save ranks'}
          </button>
        </div>
      )}

      {tab === 'items' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            Cosmetic catalog. Prices are in coins; leave price empty for trophy/default items.
            Art can be swapped later without touching the shop.
          </p>
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
                      placeholder="sku"
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
                      placeholder="Name EN"
                      onChange={(e) => set({ name_en: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      value={item.name_ru}
                      placeholder="Name RU"
                      onChange={(e) => set({ name_ru: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      value={item.name_kk}
                      placeholder="Name KK"
                      onChange={(e) => set({ name_kk: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      type="number"
                      value={item.price_coins ?? ''}
                      placeholder="price"
                      onChange={(e) =>
                        set({ price_coins: e.target.value === '' ? null : parseInt(e.target.value, 10) })
                      }
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                    <input
                      value={item.art_url}
                      placeholder="/gamification/items/....svg"
                      onChange={(e) => set({ art_url: e.target.value })}
                      className="col-span-2 md:col-span-4 rounded-lg border border-gray-300 px-2 py-1 text-sm"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2 mt-3">
                  <button
                    onClick={() => deleteItem(item)}
                    className="text-sm text-red-500 px-3 py-1"
                  >
                    Delete
                  </button>
                  <button
                    onClick={() => saveItem(item)}
                    disabled={saving}
                    className="rounded-lg bg-purple-600 text-white px-4 py-1 text-sm font-medium disabled:opacity-50"
                  >
                    Save
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
            + Add item
          </button>
        </div>
      )}
    </div>
  );
}
