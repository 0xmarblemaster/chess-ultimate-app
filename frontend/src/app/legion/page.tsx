'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import LoadingScreen from '@/components/LoadingScreen';

interface Member {
  student_id: string;
  name?: string | null;
  season_points: number;
  place: number;
  in_top_n: boolean;
}
interface LegionStanding {
  legion: {
    id: string;
    name: string;
    crest_url?: string | null;
    color_primary?: string | null;
    color_secondary?: string | null;
  };
  points: number;
  place: number;
  member_count: number;
  members: Member[];
}
interface Proximity {
  legion_id: string | null;
  place: number | null;
  in_top_n: boolean;
  points_to_top_n: number;
  season_points: number;
}
interface LegionData {
  season: { id: string; name: string; status: string; frozen: boolean } | null;
  top_n: number;
  legion: LegionStanding | null;
  my: Proximity | null;
}

export default function LegionPage() {
  const t = useTranslations('gamification');
  const [data, setData] = useState<LegionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [linked, setLinked] = useState(true);

  useEffect(() => {
    (async () => {
      const res = await fetch('/api/gamification/legion');
      if (res.status === 403) {
        setLinked(false);
        setLoading(false);
        return;
      }
      if (res.ok) setData(await res.json());
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

  const legion = data?.legion ?? null;
  const my = data?.my ?? null;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">🛡️ {t('legion.title')}</h1>
        <Link href="/cup" className="text-sm text-purple-600 font-medium">
          {t('cup.title')} →
        </Link>
      </div>

      {!data?.season ? (
        <div className="bg-white rounded-2xl shadow-md p-8 text-center text-gray-500">
          {t('legion.noSeason')}
        </div>
      ) : !legion ? (
        <div className="bg-white rounded-2xl shadow-md p-8 text-center text-gray-500">
          {t('legion.none')}
        </div>
      ) : (
        <>
          <div
            className="rounded-2xl p-5 mb-6 text-white"
            style={{
              background: `linear-gradient(135deg, ${legion.legion.color_primary ?? '#7c3aed'}, ${
                legion.legion.color_secondary ?? '#4c1d95'
              })`,
            }}
          >
            <div className="flex items-center gap-4">
              {legion.legion.crest_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={legion.legion.crest_url} alt="" className="w-16 h-16" />
              )}
              <div className="flex-1">
                <div className="text-xl font-bold">{legion.legion.name}</div>
                <div className="text-sm opacity-90">
                  {t('legion.place')} #{legion.place} · {legion.points} {t('legion.points')}
                </div>
              </div>
            </div>
            {my && (
              <div className="mt-3 text-sm bg-white/15 rounded-lg px-3 py-1.5">
                {t('legion.myPosition')}: #{my.place ?? '—'} ·{' '}
                {my.in_top_n
                  ? t('legion.inTopN', { n: data.top_n })
                  : t('legion.toTopN', { n: data.top_n, points: my.points_to_top_n })}
              </div>
            )}
          </div>

          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            {t('legion.members')} · {t('cup.standings')}
          </h2>
          <div className="space-y-2">
            {legion.members.map((m) => (
              <div
                key={m.student_id}
                className={`flex items-center gap-3 rounded-xl border p-3 ${
                  m.in_top_n ? 'border-purple-200 bg-purple-50' : 'border-gray-200 bg-white'
                } ${my && m.student_id === my.legion_id ? '' : ''}`}
              >
                <div className="w-6 text-center font-bold text-gray-400">{m.place}</div>
                <div className="flex-1 font-medium text-gray-900">
                  {m.name || `#${m.student_id.slice(0, 6)}`}
                  {m.in_top_n && (
                    <span className="ml-2 text-xs font-semibold text-purple-600">
                      {t('legion.top', { n: data.top_n })}
                    </span>
                  )}
                </div>
                <div className="font-bold text-purple-600">{m.season_points}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
