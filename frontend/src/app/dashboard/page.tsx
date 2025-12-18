'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import LoadingScreen from '@/components/LoadingScreen'

interface Course {
  id: string
  title: string
  description: string
  level: string
  order_index: number
  slug?: string
}

// Generate slug from title if not available
function generateSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

export default function DashboardPage() {
  const { getToken } = useAuth()
  const router = useRouter()
  const t = useTranslations()
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchCourses() {
      try {
        const token = await getToken()
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/courses`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          throw new Error('Failed to fetch courses')
        }

        const data = await response.json()
        setCourses(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchCourses()
  }, [getToken])

  const analysisTools = [
    {
      id: 'position',
      title: t('dashboard.positionAnalysis'),
      description: t('dashboard.positionAnalysisDesc'),
      icon: '♟️',
      href: '/position',
      color: 'from-blue-500 to-blue-700'
    },
    {
      id: 'game',
      title: t('dashboard.gameAnalysis'),
      description: t('dashboard.gameAnalysisDesc'),
      icon: '📊',
      href: '/game',
      color: 'from-green-500 to-green-700'
    },
    {
      id: 'puzzle',
      title: t('dashboard.chessPuzzles'),
      description: t('dashboard.chessPuzzlesDesc'),
      icon: '🧩',
      href: '/puzzle',
      color: 'from-purple-500 to-purple-700'
    }
  ]

  const getLevelTranslation = (level: string) => {
    const levels: Record<string, string> = {
      'beginner': t('dashboard.levels.beginner'),
      'intermediate': t('dashboard.levels.intermediate'),
      'advanced': t('dashboard.levels.advanced')
    }
    return levels[level] || level
  }

  if (loading) {
    return <LoadingScreen isVisible={true} />
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Analysis Tools Section */}
      <div className="mb-16">
        <h1 className="text-4xl font-bold mb-4">{t('dashboard.analysisToolsTitle')}</h1>
        <p className="text-gray-600 dark:text-gray-300 mb-8">
          {t('dashboard.analysisToolsSubtitle')}
        </p>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {analysisTools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => router.push(tool.href)}
              className={`bg-gradient-to-br ${tool.color} text-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-all transform hover:scale-105 text-left`}
            >
              <div className="text-5xl mb-4">{tool.icon}</div>
              <h2 className="text-2xl font-bold mb-3">{tool.title}</h2>
              <p className="text-blue-100">{tool.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Learning Courses Section */}
      <div>
        <h2 className="text-3xl font-bold mb-4">{t('dashboard.learningJourney')}</h2>
        <p className="text-gray-600 dark:text-gray-300 mb-8">
          {t('dashboard.learningJourneySubtitle')}
        </p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {t('dashboard.errorLoading')}: {error}
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => (
            <div
              key={course.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-2xl font-bold">{course.title}</h3>
                <span className={`px-3 py-1 rounded-full text-sm ${
                  course.level === 'beginner' ? 'bg-green-100 text-green-800' :
                  course.level === 'intermediate' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {getLevelTranslation(course.level)}
                </span>
              </div>

              <p className="text-gray-600 dark:text-gray-300 mb-6">
                {course.description}
              </p>

              <Link
                href={`/learn/${course.slug || generateSlug(course.title)}`}
                className="block w-full text-center bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded transition-colors"
              >
                {t('dashboard.startLearning')}
              </Link>
            </div>
          ))}
        </div>

        {courses.length === 0 && !error && (
          <div className="text-center text-gray-500 mt-12 bg-gray-50 dark:bg-gray-800 rounded-lg p-8">
            <p className="text-xl">{t('dashboard.noCourses')}</p>
            <p className="mt-2">{t('dashboard.checkBack')}</p>
          </div>
        )}
      </div>
    </div>
  )
}
