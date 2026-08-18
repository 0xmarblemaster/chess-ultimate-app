'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import LoadingScreen from '@/components/LoadingScreen';

type ProviderId = 'kaspi' | 'bank_transfer';

interface CoinPackage {
  id: string;
  coins: number;
  price_kzt: number;
}
interface Purchase {
  id: string;
  coins: number;
  amount_kzt: number;
  provider: string;
  status: 'pending' | 'paid' | 'failed' | 'refunded';
  created_at: string;
}
interface PaymentField {
  label: string;
  value: string;
}
interface PaymentInstructions {
  provider: ProviderId;
  available: boolean;
  amountKzt: number;
  reference: string;
  payUrl: string | null;
  qrValue: string | null;
  fields: PaymentField[];
}
interface CoinsData {
  student_name: string | null;
  packages: CoinPackage[];
  purchases: Purchase[];
  providers: ProviderId[];
}

const STATUS_STYLE: Record<Purchase['status'], string> = {
  pending: 'bg-amber-100 text-amber-700',
  paid: 'bg-green-100 text-green-700',
  failed: 'bg-gray-200 text-gray-600',
  refunded: 'bg-blue-100 text-blue-700',
};

/** Client-side QR of the Kaspi link (no server round-trip; `qrcode` renders to a data URL). */
function Qr({ value }: { value: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    import('qrcode')
      .then((m) => m.toDataURL(value, { margin: 1, width: 200 }))
      .then((url) => {
        if (alive) setSrc(url);
      })
      .catch(() => setSrc(null));
    return () => {
      alive = false;
    };
  }, [value]);
  if (!src) return null;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="QR" className="w-40 h-40 rounded-lg border border-gray-200" />;
}

export default function CoinsPage() {
  const t = useTranslations('gamification');
  const [data, setData] = useState<CoinsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [linked, setLinked] = useState(true);

  const [selected, setSelected] = useState<CoinPackage | null>(null);
  const [provider, setProvider] = useState<ProviderId | null>(null);
  const [instructions, setInstructions] = useState<PaymentInstructions | null>(null);
  const [instrError, setInstrError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [claimed, setClaimed] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch('/api/gamification/coins');
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

  const reset = () => {
    setSelected(null);
    setProvider(null);
    setInstructions(null);
    setInstrError(null);
    setClaimed(false);
  };

  const choosePackage = (pkg: CoinPackage) => {
    reset();
    setSelected(pkg);
    // Auto-select the first available provider so the parent sees a pay option immediately.
    const first = data?.providers?.[0] ?? null;
    if (first) chooseProvider(pkg, first);
  };

  const chooseProvider = async (pkg: CoinPackage, prov: ProviderId) => {
    setProvider(prov);
    setInstructions(null);
    setInstrError(null);
    setBusy(true);
    try {
      const res = await fetch('/api/gamification/coins/instructions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ package_id: pkg.id, provider: prov }),
      });
      if (!res.ok) {
        setInstrError(t('purchase.providerUnavailable'));
        return;
      }
      const d = await res.json();
      setInstructions(d.instructions as PaymentInstructions);
    } catch {
      setInstrError(t('purchase.providerUnavailable'));
    } finally {
      setBusy(false);
    }
  };

  const claim = async () => {
    if (!selected || !provider) return;
    setBusy(true);
    try {
      const res = await fetch('/api/gamification/coins/claim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ package_id: selected.id, provider }),
      });
      if (!res.ok) {
        setInstrError(t('purchase.claimError'));
        return;
      }
      setClaimed(true);
      await load();
    } catch {
      setInstrError(t('purchase.claimError'));
    } finally {
      setBusy(false);
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

  const packages = data?.packages ?? [];
  const purchases = data?.purchases ?? [];
  const fmtKzt = (n: number) => `${n.toLocaleString('ru-RU')} ₸`;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-gray-900">{t('purchase.title')}</h1>
        <Link href="/shop" className="text-sm text-purple-600 font-medium">
          {t('shop.title')}
        </Link>
      </div>
      <p className="text-sm text-gray-500 mb-4">{t('purchase.subtitle')}</p>
      <div className="rounded-xl bg-amber-50 text-amber-800 text-sm px-4 py-3 mb-6">
        {t('purchase.parentNote')}
      </div>

      {/* Package grid → provider → instructions → claim */}
      {!selected ? (
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            {t('purchase.selectPackage')}
          </h2>
          {packages.length === 0 ? (
            <p className="text-sm text-gray-400">{t('purchase.noPackages')}</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {packages.map((pkg) => (
                <button
                  key={pkg.id}
                  onClick={() => choosePackage(pkg)}
                  className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col items-center hover:border-purple-400 transition"
                >
                  <span className="text-2xl">🪙</span>
                  <span className="text-lg font-bold text-gray-900">{pkg.coins}</span>
                  <span className="text-xs text-gray-400 mb-1">{t('purchase.coinsLabel')}</span>
                  <span className="rounded-full bg-purple-50 text-purple-700 px-3 py-1 text-sm font-semibold">
                    {fmtKzt(pkg.price_kzt)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      ) : (
        <section className="mb-8 rounded-xl border border-gray-200 bg-white p-5">
          <button onClick={reset} className="text-sm text-gray-500 mb-3">
            ← {t('purchase.back')}
          </button>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-2xl">🪙</span>
            <span className="text-lg font-bold text-gray-900">{selected.coins}</span>
            <span className="text-sm text-gray-400">{t('purchase.coinsLabel')}</span>
            <span className="ml-auto rounded-full bg-purple-50 text-purple-700 px-3 py-1 text-sm font-semibold">
              {fmtKzt(selected.price_kzt)}
            </span>
          </div>

          {(data?.providers?.length ?? 0) > 1 && (
            <div className="flex gap-2 mb-4">
              {data!.providers.map((prov) => (
                <button
                  key={prov}
                  onClick={() => chooseProvider(selected, prov)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                    provider === prov ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {t(`purchase.provider.${prov}`)}
                </button>
              ))}
            </div>
          )}

          {busy && !instructions && <p className="text-sm text-gray-400">…</p>}
          {instrError && <p className="text-sm text-red-500 mb-3">{instrError}</p>}

          {instructions && !claimed && (
            <div className="space-y-4">
              {instructions.provider === 'kaspi' && instructions.payUrl && (
                <div className="flex flex-col items-center gap-3">
                  <a
                    href={instructions.payUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full text-center rounded-lg bg-[#f14635] text-white px-4 py-3 font-semibold"
                  >
                    {t('purchase.payKaspi')}
                  </a>
                  {instructions.qrValue && (
                    <>
                      <Qr value={instructions.qrValue} />
                      <span className="text-xs text-gray-400">{t('purchase.scanQr')}</span>
                    </>
                  )}
                </div>
              )}

              <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 space-y-2">
                {instructions.fields.map((f) => (
                  <div key={f.label} className="flex items-start justify-between gap-3 text-sm">
                    <span className="text-gray-400 capitalize">
                      {f.label === 'reference' ? t('purchase.reference') : f.label}
                    </span>
                    <span className="text-gray-900 font-medium text-right break-all">{f.value}</span>
                  </div>
                ))}
                <p className="text-xs text-gray-400 pt-1">{t('purchase.referenceHint')}</p>
              </div>

              <button
                onClick={claim}
                disabled={busy}
                className="w-full rounded-lg bg-purple-600 text-white px-4 py-3 font-semibold disabled:opacity-50"
              >
                {t('purchase.iPaid')}
              </button>
            </div>
          )}

          {claimed && (
            <div className="rounded-lg bg-green-50 text-green-700 px-4 py-3 text-sm">
              {t('purchase.claimed')}
            </div>
          )}
        </section>
      )}

      {/* Purchase history */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          {t('purchase.statusTitle')}
        </h2>
        {purchases.length === 0 ? (
          <p className="text-sm text-gray-400">{t('purchase.noPurchases')}</p>
        ) : (
          <div className="space-y-2">
            {purchases.map((p) => (
              <div
                key={p.id}
                className="flex items-center gap-3 rounded-lg border border-gray-100 bg-white px-4 py-2"
              >
                <span className="text-lg">🪙</span>
                <span className="font-semibold text-gray-900">{p.coins}</span>
                <span className="text-sm text-gray-400">{fmtKzt(p.amount_kzt)}</span>
                <span
                  className={`ml-auto text-xs font-semibold px-2 py-1 rounded-full ${STATUS_STYLE[p.status]}`}
                >
                  {t(`purchase.status.${p.status}`)}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
