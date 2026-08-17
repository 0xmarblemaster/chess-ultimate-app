'use client'

import { useUser, useClerk } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { useEffect, useState } from 'react'
import { StreakBanner } from '@/components/gamification/StreakBanner'
import { XPDisplay } from '@/components/gamification/XPDisplay'
import LoadingScreen from '@/components/LoadingScreen'
import type { GamificationProfile } from '@/lib/gamification/profile'

/** Pick the rank name for the active locale (kz → Kazakh column). */
function rankName(
  rank: NonNullable<GamificationProfile['rank']>,
  locale: string,
): string {
  if (locale === 'ru') return rank.name_ru
  if (locale === 'kz') return rank.name_kk
  return rank.name_en
}

export default function ProfilePage() {
  const { user, isLoaded } = useUser()
  const { signOut } = useClerk()
  const router = useRouter()
  const t = useTranslations()
  const locale = useLocale()

  const [profile, setProfile] = useState<GamificationProfile | null>(null)
  const [loadingProfile, setLoadingProfile] = useState(true)

  useEffect(() => {
    if (!isLoaded || !user) return
    let cancelled = false
    fetch('/api/gamification/profile')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled) setProfile(data)
      })
      .catch(() => {
        if (!cancelled) setProfile(null)
      })
      .finally(() => {
        if (!cancelled) setLoadingProfile(false)
      })
    return () => {
      cancelled = true
    }
  }, [isLoaded, user])

  const handleSignOut = async () => {
    await signOut()
    router.push('/')
  }

  if (!isLoaded) {
    return <LoadingScreen isVisible={true} />
  }

  if (!user) {
    router.push('/sign-in')
    return null
  }

  const linked = profile?.linked === true

  return (
    <div className="min-h-screen bg-gray-50 animate-page-enter">
      {/* Profile Header */}
      <div className="bg-gradient-to-br from-purple-600 to-purple-800 text-white">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 rounded-full bg-white/20 flex items-center justify-center overflow-hidden">
              {user.imageUrl ? (
                <img src={user.imageUrl} alt={user.firstName || 'Profile'} className="w-full h-full object-cover" />
              ) : (
                <span className="text-4xl">👤</span>
              )}
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold">{user.firstName || 'Chess Player'}</h1>
              <p className="text-purple-200">{user.emailAddresses[0]?.emailAddress}</p>
              {linked && profile && (
                <div className="flex items-center gap-3 mt-2 flex-wrap">
                  <XPDisplay xp={profile.xp} size="sm" />
                  {profile.rank && (
                    <>
                      <span className="text-purple-200">•</span>
                      <span className="text-sm text-purple-100">
                        {t('gamification.rankLabel')}: {rankName(profile.rank, locale)}
                      </span>
                    </>
                  )}
                  <span className="text-purple-200">•</span>
                  <span className="flex items-center gap-1 text-sm">
                    <span className="text-yellow-300">🪙</span>
                    <span>{profile.coins}</span>
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6 space-y-6">
        {loadingProfile ? (
          <div className="bg-white rounded-2xl shadow-md p-6 text-center text-gray-500">…</div>
        ) : linked && profile ? (
          <>
            {/* Rank + progress */}
            {profile.rank && (
              <div className="bg-white rounded-2xl shadow-md p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">♟️</span>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-400">
                        {t('gamification.rankLabel')}
                      </div>
                      <div className="text-xl font-bold text-gray-900">
                        {rankName(profile.rank, locale)}
                      </div>
                    </div>
                  </div>
                  <XPDisplay xp={profile.xp} size="lg" />
                </div>
                <div className="h-3 w-full rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-purple-500 to-amber-400 transition-all"
                    style={{ width: `${profile.rank_progress.pct}%` }}
                  />
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  {profile.rank_progress.next_code
                    ? t('gamification.toNextRank', {
                        xp: Math.max(
                          0,
                          profile.rank_progress.xp_for_next - profile.rank_progress.xp_into_rank,
                        ),
                      })
                    : t('gamification.maxRank')}
                </div>
              </div>
            )}

            {/* Tournament-week streak */}
            <StreakBanner
              streakDays={profile.streak.current_weeks}
              unit="weeks"
              nextMilestone={profile.streak.next_milestone}
            />

            {/* Stats since launch */}
            <div className="bg-white rounded-2xl shadow-md p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-1">{t('profile.yourStats')}</h2>
              <p className="text-xs text-gray-400 mb-4">{t('gamification.sinceLaunch')}</p>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-purple-50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-purple-600">{profile.stats.tournaments_played}</div>
                  <div className="text-sm text-gray-600">{t('gamification.tournaments')}</div>
                </div>
                <div className="bg-green-50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-green-600">{profile.stats.wins_total}</div>
                  <div className="text-sm text-gray-600">{t('gamification.wins')}</div>
                </div>
                <div className="bg-yellow-50 rounded-xl p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-600">{profile.coins}</div>
                  <div className="text-sm text-gray-600">{t('gamification.coins')}</div>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Unlinked (D-8): gamification hidden until the account is linked. */
          <div className="bg-white rounded-2xl shadow-md p-6 text-center">
            <div className="text-4xl mb-2">🔗</div>
            <h2 className="text-lg font-bold text-gray-900 mb-1">{t('gamification.notLinkedTitle')}</h2>
            <p className="text-sm text-gray-500">{t('gamification.notLinkedBody')}</p>
          </div>
        )}

        {/* Account Actions */}
        <div className="bg-white rounded-2xl shadow-md p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">{t('profile.account')}</h2>
          <div className="space-y-3">
            <button
              onClick={() => router.push('/settings')}
              className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">♞</span>
                <span className="font-medium text-gray-900">Board & App Settings</span>
              </div>
              <span className="text-gray-400">→</span>
            </button>

            <button
              onClick={() => router.push('/user-profile')}
              className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">⚙️</span>
                <span className="font-medium text-gray-900">{t('profile.accountSettings')}</span>
              </div>
              <span className="text-gray-400">→</span>
            </button>

            <button
              onClick={handleSignOut}
              className="w-full flex items-center justify-between p-3 bg-red-50 rounded-xl hover:bg-red-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">🚪</span>
                <span className="font-medium text-red-600">{t('profile.signOut')}</span>
              </div>
              <span className="text-red-400">→</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
