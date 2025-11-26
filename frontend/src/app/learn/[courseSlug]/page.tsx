'use client'

import { useEffect, useState } from 'react'
import { useAuth, useUser, SignInButton } from '@clerk/nextjs'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import LoadingScreen from '@/components/LoadingScreen'

interface Course {
  id: string
  title: string
  description: string
  level: string
  slug: string
}

interface Module {
  id: string
  title: string
  description: string
  order_index: number
}

interface Lesson {
  id: string
  module_id: string
  title: string
  slug: string
  lesson_type: string
  order_index: number
  requires_lesson_id: string | null
}

interface Progress {
  status: string
  completed_at: string | null
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

export default function CoursePage() {
  const { courseSlug } = useParams() as { courseSlug: string }
  const { getToken, isLoaded, isSignedIn } = useAuth()
  const { user } = useUser()
  const [course, setCourse] = useState<Course | null>(null)
  const [modules, setModules] = useState<Module[]>([])
  const [lessons, setLessons] = useState<Record<string, Lesson[]>>({})
  const [progress, setProgress] = useState<Record<string, Progress>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    async function fetchCourseData() {
      try {
        // Wait for auth to be loaded and user to be signed in
        if (!isLoaded) return

        if (!isSignedIn) {
          setError('Please sign in to access this course')
          setLoading(false)
          return
        }

        const token = await getToken()

        if (!token) {
          setError('Unable to authenticate. Please try signing in again.')
          setLoading(false)
          return
        }

        const headers = { 'Authorization': `Bearer ${token}` }

        // Fetch course data using slug-based API
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/learn/${courseSlug}`,
          { headers }
        )

        if (response.status === 401) {
          setError('Session expired. Please sign in again.')
          setLoading(false)
          return
        }

        if (!response.ok) {
          throw new Error('Failed to fetch course data')
        }

        const data = await response.json()

        if (!isMounted) return

        setCourse(data.course || null)
        setModules(data.modules || [])
        setLessons(data.lessons || {})
        setProgress(data.progress || {})
        setError(null)
      } catch (err) {
        console.error('Failed to fetch course data:', err)
        if (isMounted) {
          setError('Failed to load course. Please try again.')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    if (courseSlug && isLoaded) {
      fetchCourseData()
    }

    return () => {
      isMounted = false
    }
  }, [courseSlug, getToken, isLoaded, isSignedIn])

  const isLessonUnlocked = (lesson: Lesson): boolean => {
    if (!lesson.requires_lesson_id) return true
    const requiredProgress = progress[lesson.requires_lesson_id]
    return requiredProgress?.status === 'completed'
  }

  if (loading || !isLoaded) {
    return <LoadingScreen isVisible={true} />
  }

  if (error || !isSignedIn) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-xl text-red-500 mb-4">
            {error || 'Please sign in to access this course'}
          </div>
          <SignInButton mode="modal">
            <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded transition-colors">
              Sign In
            </button>
          </SignInButton>
          <div className="mt-4">
            <Link href="/dashboard" className="text-blue-600 hover:underline">
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (!course) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-xl text-red-500 mb-4">Course not found</div>
          <Link href="/dashboard" className="text-blue-600 hover:underline">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <Link href="/dashboard" className="text-blue-600 hover:underline mb-4 inline-block">
        ← Back to Dashboard
      </Link>

      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">{course.title}</h1>
        <p className="text-gray-600 dark:text-gray-300 mb-4">{course.description}</p>
        <span className={`px-3 py-1 rounded-full text-sm ${
          course.level === 'beginner' ? 'bg-green-100 text-green-800' :
          course.level === 'intermediate' ? 'bg-yellow-100 text-yellow-800' :
          'bg-red-100 text-red-800'
        }`}>
          {course.level}
        </span>
      </div>

      <div className="space-y-8">
        {modules.map((module) => (
          <div key={module.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-2">{module.title}</h2>
            <p className="text-gray-600 dark:text-gray-300 mb-4">{module.description}</p>

            <div className="space-y-3">
              {lessons[module.id]?.map((lesson) => {
                const unlocked = isLessonUnlocked(lesson)
                const lessonProgress = progress[lesson.id]
                const isCompleted = lessonProgress?.status === 'completed'

                return (
                  <div
                    key={lesson.id}
                    className={`flex items-center justify-between p-4 rounded-lg border-2 ${
                      !unlocked
                        ? 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 opacity-60'
                        : isCompleted
                        ? 'bg-green-50 dark:bg-green-900 border-green-300 dark:border-green-700'
                        : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center space-x-4">
                      {!unlocked && (
                        <span className="text-2xl">🔒</span>
                      )}
                      {isCompleted && (
                        <span className="text-2xl">✅</span>
                      )}
                      <div>
                        <h3 className="font-semibold">{lesson.title}</h3>
                        <span className={`text-sm px-2 py-1 rounded ${
                          lesson.lesson_type === 'theory'
                            ? 'bg-blue-100 text-blue-800'
                            : lesson.lesson_type === 'exercise'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-purple-100 text-purple-800'
                        }`}>
                          {lesson.lesson_type}
                        </span>
                      </div>
                    </div>

                    {unlocked ? (
                      <Link
                        href={`/learn/${courseSlug}/${lesson.slug || generateSlug(lesson.title)}`}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded transition-colors"
                      >
                        {isCompleted ? 'Review' : 'Start'}
                      </Link>
                    ) : (
                      <span className="text-gray-500 text-sm">
                        Complete previous lesson to unlock
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {modules.length === 0 && (
        <div className="text-center text-gray-500 mt-12">
          <p className="text-xl">No modules found for this course.</p>
        </div>
      )}
    </div>
  )
}
