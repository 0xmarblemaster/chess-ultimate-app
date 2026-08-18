'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useUser } from '@clerk/nextjs';
import { useTranslations, useLocale } from 'next-intl';
import { SLOTS, itemName, type ItemRow } from '@/lib/gamification/items';
import { Avatar } from '@/components/gamification/Avatar';
import LoadingScreen from '@/components/LoadingScreen';

interface InventoryData {
  items: ItemRow[];
  loadout: Record<string, string>;
}

export default function AvatarPage() {
  const t = useTranslations('gamification');
  const locale = useLocale();
  const { user } = useUser();
  const [data, setData] = useState<InventoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [linked, setLinked] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch('/api/gamification/inventory');
    if (res.status === 403) {
      setLinked(false);
      setLoading(false);
      return;
    }
    if (res.ok) setData(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const setSlot = async (slot: string, itemId: string | null) => {
    setBusy(slot);
    try {
      const res = await fetch('/api/gamification/loadout', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot, item_id: itemId }),
      });
      if (res.ok) await load();
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <LoadingScreen isVisible={true} />;

  if (!linked) {
    return (
      <div className="max-w-md mx-auto p-8 text-center">
        <h1 className="text-xl font-bold text-gray-900 mb-2">{t('notLinkedTitle')}</h1>
        <p className="text-gray-500">{t('notLinkedBody')}</p>
      </div>
    );
  }

  const items = data?.items ?? [];
  const loadout = data?.loadout ?? {};
  const byId = new Map(items.map((it) => [it.id, it]));

  // Resolve the equipped item per slot for the avatar preview.
  const equipped: Record<string, ItemRow> = {};
  for (const [slot, id] of Object.entries(loadout)) {
    const it = byId.get(id);
    if (it) equipped[slot] = it;
  }

  const ownedBySlot = (slot: string) => items.filter((it) => it.slot === slot);
  const slotsWithItems = SLOTS.filter((s) => ownedBySlot(s).length);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('shop.customize')}</h1>
        <Link href="/shop" className="rounded-lg bg-purple-600 text-white px-4 py-2 text-sm font-medium">
          {t('shop.title')}
        </Link>
      </div>

      <div className="grid md:grid-cols-[200px_1fr] gap-8">
        <div className="flex flex-col items-center">
          <Avatar equipped={equipped} photoUrl={user?.imageUrl} size={200} />
        </div>

        <div>
          {slotsWithItems.length === 0 && (
            <p className="text-gray-500">
              {t('shop.empty')}{' '}
              <Link href="/shop" className="text-purple-600 underline">
                {t('shop.title')}
              </Link>
            </p>
          )}
          {slotsWithItems.map((slot) => (
            <section key={slot} className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                  {t(`shop.slots.${slot}`)}
                </h2>
                {loadout[slot] && (
                  <button
                    onClick={() => setSlot(slot, null)}
                    disabled={busy === slot}
                    className="text-xs text-gray-400 hover:text-red-500"
                  >
                    {t('shop.unequip')}
                  </button>
                )}
              </div>
              <div className="flex gap-3 flex-wrap">
                {ownedBySlot(slot).map((it) => {
                  const isEquipped = loadout[slot] === it.id;
                  return (
                    <button
                      key={it.id}
                      onClick={() => setSlot(slot, isEquipped ? null : it.id)}
                      disabled={busy === slot}
                      className={`rounded-xl border p-2 flex flex-col items-center w-24 ${
                        isEquipped ? 'border-purple-500 ring-2 ring-purple-300' : 'border-gray-200'
                      }`}
                    >
                      {it.art_url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={it.art_url} alt="" className="w-14 h-14" />
                      )}
                      <span className="text-xs text-gray-700 text-center mt-1">
                        {itemName(it, locale)}
                      </span>
                      <span className="text-[10px] mt-0.5 text-purple-600">
                        {isEquipped ? t('shop.equipped') : t('shop.equip')}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
