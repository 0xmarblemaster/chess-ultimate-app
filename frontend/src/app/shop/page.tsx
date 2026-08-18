'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { SLOTS, itemName, type ItemRow } from '@/lib/gamification/items';
import LoadingScreen from '@/components/LoadingScreen';
import { AchievementCelebration } from '@/components/gamification/CelebrationOverlay';

interface ShopItem extends ItemRow {
  owned: boolean;
  equipped: boolean;
  affordable: boolean;
}
interface ShopData {
  balance: number;
  slots: Record<string, ShopItem[]>;
  loadout: Record<string, string>;
}

const RARITY_RING: Record<string, string> = {
  common: 'ring-slate-300',
  rare: 'ring-blue-400',
  epic: 'ring-purple-400',
  legendary: 'ring-amber-400',
};

export default function ShopPage() {
  const t = useTranslations('gamification');
  const locale = useLocale();
  const [data, setData] = useState<ShopData | null>(null);
  const [loading, setLoading] = useState(true);
  const [linked, setLinked] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [flash, setFlash] = useState<{ id: string; kind: 'ok' | 'err' } | null>(null);
  const [unlocked, setUnlocked] = useState<ShopItem | null>(null);

  const load = useCallback(async () => {
    const res = await fetch('/api/gamification/items');
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

  const buy = async (item: ShopItem) => {
    setBusy(item.id);
    try {
      const res = await fetch('/api/gamification/shop/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: item.id }),
      });
      const ok = res.status === 200;
      setFlash({ id: item.id, kind: ok ? 'ok' : 'err' });
      setTimeout(() => setFlash(null), 2000);
      if (ok) {
        setUnlocked(item); // item-unlock celebration (§6)
        await load();
      }
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

  const slots = data?.slots ?? {};
  const orderedSlots = SLOTS.filter((s) => slots[s]?.length);

  return (
    <div className="max-w-4xl mx-auto p-6">
      {unlocked && (
        <AchievementCelebration
          name={itemName(unlocked, locale)}
          description={t(`shop.slots.${unlocked.slot}`)}
          icon="🎁"
          xpReward={0}
          onClose={() => setUnlocked(null)}
        />
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('shop.title')}</h1>
          <p className="text-sm text-gray-500">{t('shop.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-amber-50 text-amber-700 px-4 py-2 font-semibold">
            🪙 {data?.balance ?? 0}
          </div>
          <Link href="/avatar" className="rounded-lg bg-purple-600 text-white px-4 py-2 text-sm font-medium">
            {t('shop.customize')}
          </Link>
        </div>
      </div>

      {orderedSlots.map((slot) => (
        <section key={slot} className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            {t(`shop.slots.${slot}`)}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {slots[slot].map((item) => (
              <div
                key={item.id}
                className={`rounded-xl border border-gray-200 bg-white p-3 flex flex-col items-center ring-2 ${RARITY_RING[item.rarity] ?? 'ring-slate-200'}`}
              >
                {item.art_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={item.art_url} alt="" className="w-20 h-20 mb-2" />
                )}
                <div className="text-sm font-medium text-gray-900 text-center">
                  {itemName(item, locale)}
                </div>
                <div className="text-xs text-gray-400 mb-2 capitalize">
                  {t(`shop.rarity.${item.rarity}`)}
                </div>

                {item.owned ? (
                  item.equipped ? (
                    <span className="rounded-full bg-purple-100 text-purple-700 px-2 py-0.5 text-xs font-semibold">
                      ✓ {t('shop.equipped')}
                    </span>
                  ) : (
                    <span className="text-xs font-semibold text-green-600">✓ {t('shop.owned')}</span>
                  )
                ) : (
                  <button
                    onClick={() => buy(item)}
                    disabled={!item.affordable || busy === item.id}
                    className={`w-full rounded-lg px-3 py-1.5 text-sm font-medium ${
                      item.affordable
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    {busy === item.id
                      ? '…'
                      : item.affordable
                        ? `🪙 ${item.price_coins} · ${t('shop.buy')}`
                        : t('shop.notEnough')}
                  </button>
                )}
                {flash?.id === item.id && (
                  <span
                    className={`mt-1 text-xs ${flash.kind === 'ok' ? 'text-green-600' : 'text-red-500'}`}
                  >
                    {flash.kind === 'ok' ? t('shop.purchased') : t('shop.buyFailed')}
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
