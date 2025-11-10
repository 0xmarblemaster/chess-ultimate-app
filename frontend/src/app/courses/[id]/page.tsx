'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { useParams } from 'next/navigation'
import Link from 'next/link'

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
  lesson_type: string
  order_index: number
  requires_lesson_id: string | null
}

interface Progress {
  status: string
  completed_at: string | null
}

export default function CoursePage() {
  const { id } = useParams()
  const { getToken } = useAuth()
  const [modules, setModules] = useState<Module[]>([])
  const [lessons, setLessons] = useState<Record<string, Lesson[]>>({})
  const [progress, setProgress] = useState<Record<string, Progress>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchCourseData() {
      try {
        const token = await getToken()

        // Fetch modules
        const modulesRes = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/courses/${id}/modules`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )
        const modulesData = await modulesRes.json()
        setModules(modulesData)

        // Fetch lessons for each module
        const lessonsMap: Record<string, Lesson[]> = {}
        for (const module of modulesData) {
          const lessonsRes = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/modules/${module.id}/lessons`,
            { headers: { 'Authorization': `Bearer ${token}` } }
          )
          const lessonsData = await lessonsRes.json()
          lessonsMap[module.id] = lessonsData

          // Fetch progress for each lesson
          for (const lesson of lessonsData) {
            try {
              const progressRes = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/lessons/${lesson.id}/progress`,
                { headers: { 'Authorization': `Bearer ${token}` } }
              )
              const progressData = await progressRes.json()
              setProgress(prev => ({ ...prev, [lesson.id]: progressData }))
            } catch (err) {
              // Progress not found, use default
              setProgress(prev => ({ ...prev, [lesson.id]: { status: 'not_started', completed_at: null } }))
            }
          }
        }
        setLessons(lessonsMap)
      } catch (err) {
        console.error('Failed to fetch course data:', err)
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchCourseData()
    }
  }, [id, getToken])

  const isLessonUnlocked = (lesson: Lesson): boolean => {
    if (!lesson.requires_lesson_id) return true
    const requiredProgress = progress[lesson.requires_lesson_id]
    return requiredProgress?.status === 'completed'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading course...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <Link href="/dashboard" className="text-blue-600 hover:underline mb-4 inline-block">
        ← Back to Dashboard
      </Link>

      <h1 className="text-4xl font-bold mb-8">Course Content</h1>

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
                        href={`/lessons/${lesson.id}`}
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
