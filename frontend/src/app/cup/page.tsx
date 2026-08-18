'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import LoadingScreen from '@/components/LoadingScreen';

interface LegionRow {
  legion: { id: string; name: string; crest_url?: string | null; color_primary?: string | null };
  points: number;
  place: number;
  gap_to_first: number;
  member_count: number;
}
interface Proximity {
  legion_id: string | null;
  place: number | null;
  in_top_n: boolean;
  points_to_top_n: number;
  season_points: number;
}
interface CupData {
  season: { id: string; name: string; ends_at: string; status: string; frozen: boolean } | null;
  top_n: number;
  legions: LegionRow[];
  my: Proximity | null;
}
interface ArchiveSeason {
  id: string;
  name: string;
  status: string;
  winner: { id: string; name: string; crest_url?: string | null } | null;
}

function daysLeft(endsAt: string): number {
  return Math.max(0, Math.ceil((new Date(endsAt).getTime() - Date.now()) / 86400000));
}

export default function CupPage() {
  const t = useTranslations('gamification');
  const [data, setData] = useState<CupData | null>(null);
  const [archive, setArchive] = useState<ArchiveSeason[]>([]);
  const [loading, setLoading] = useState(true);
  const [linked, setLinked] = useState(true);

  useEffect(() => {
    (async () => {
      const res = await fetch('/api/gamification/cup');
      if (res.status === 403) {
        setLinked(false);
        setLoading(false);
        return;
      }
      if (res.ok) setData(await res.json());
      const arc = await fetch('/api/gamification/seasons');
      if (arc.ok) {
        const d = await arc.json();
        setArchive((d.seasons ?? []).filter((s: ArchiveSeason) => s.status === 'closed'));
      }
      setLoading(false);
    })();
  }, []);

  if (loading) return <LoadingScreen isVisible={true} />;

  if (!linked) {
    return (
      <div className="max-w-md mx-auto p-8 text-center">
        <h1 className="text-xl font-bold text-gray-900 mb-2">{t('notLinkedTitle')}</h1>
        <p className="text-gray-500">{t('notLinkedBody')}</p>
      </div>
    );
  }

  const season = data?.season ?? null;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🏆 {t('cup.title')}</h1>
        <Link href="/legion" className="text-sm text-purple-600 font-medium">
          {t('legion.title')} →
        </Link>
      </div>

      {!season ? (
        <div className="bg-white rounded-2xl shadow-md p-8 text-center text-gray-500">
          {t('cup.comingSoon')}
        </div>
      ) : (
        <>
          <div className="bg-gradient-to-br from-purple-600 to-purple-800 text-white rounded-2xl p-5 mb-6">
            <div className="text-lg font-bold">{season.name}</div>
            {season.frozen ? (
              <div className="text-sm text-amber-200 mt-1">❄️ {t('cup.frozen')}</div>
            ) : (
              <div className="text-sm text-purple-100 mt-1">
                {t('legion.season')}: {daysLeft(season.ends_at)}d
              </div>
            )}
            {data?.my && data.my.legion_id && (
              <div className="mt-2 text-sm bg-white/15 rounded-lg px-3 py-1.5 inline-block">
                {data.my.in_top_n
                  ? t('legion.inTopN', { n: data.top_n })
                  : t('legion.toTopN', { n: data.top_n, points: data.my.points_to_top_n })}
              </div>
            )}
          </div>

          <div className="space-y-2">
            {(data?.legions ?? []).map((row) => (
              <div
                key={row.legion.id}
                className={`flex items-center gap-3 bg-white rounded-xl border p-3 ${
                  row.place === 1 ? 'border-amber-300 ring-1 ring-amber-200' : 'border-gray-200'
                }`}
              >
                <div className="w-7 text-center font-bold text-gray-400">{row.place}</div>
                {row.legion.crest_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={row.legion.crest_url} alt="" className="w-10 h-10" />
                )}
                <div className="flex-1">
                  <div className="font-semibold text-gray-900">{row.legion.name}</div>
                  {row.place > 1 && (
                    <div className="text-xs text-gray-400">
                      {t('cup.gapToFirst', { points: row.gap_to_first })}
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <div className="font-bold text-purple-600">{row.points}</div>
                  <div className="text-xs text-gray-400">{t('legion.points')}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {archive.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            {t('cup.archive')}
          </h2>
          <div className="space-y-2">
            {archive.map((s) => (
              <div key={s.id} className="flex items-center gap-3 bg-white rounded-xl border border-gray-200 p-3">
                <div className="flex-1 text-sm font-medium text-gray-800">{s.name}</div>
                {s.winner ? (
                  <div className="flex items-center gap-2 text-sm text-amber-700">
                    {s.winner.crest_url && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={s.winner.crest_url} alt="" className="w-6 h-6" />
                    )}
                    🏆 {s.winner.name}
                  </div>
                ) : (
                  <span className="text-xs text-gray-400">—</span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
