'use client'

import { useEffect, useState } from 'react'
import { useAuth, SignInButton } from '@clerk/nextjs'
import { useParams, useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import { AnimatedChessBoard } from '@/components/chess'
import LoadingScreen from '@/components/LoadingScreen'
import Link from 'next/link'

interface ArrowData {
  from: string
  path: string[]
}

interface ExerciseSolution {
  arrow?: ArrowData
  targets?: string[]
  requireAll?: boolean
  [key: string]: unknown
}

interface Lesson {
  id: string
  title: string
  content: string
  lesson_type: string
  slug: string
  course_slug: string
  course_title: string
  exercise_fen: string | null
  solution_move: string | null
  exercise_type: string | null
  hint_text: string | null
  success_message: string | null
  exercise_solution: ExerciseSolution | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function LessonPage() {
  const { courseSlug, lessonSlug } = useParams() as { courseSlug: string; lessonSlug: string }
  const router = useRouter()
  const { getToken, isLoaded, isSignedIn } = useAuth()
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  const [completingLesson, setCompletingLesson] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchLesson() {
      try {
        // Wait for auth to be loaded
        if (!isLoaded) return

        if (!isSignedIn) {
          setError('Please sign in to access this lesson')
          setLoading(false)
          return
        }

        const token = await getToken()

        if (!token) {
          setError('Unable to authenticate. Please try signing in again.')
          setLoading(false)
          return
        }

        const apiUrl = process.env.NEXT_PUBLIC_API_URL
        const headers = { 'Authorization': `Bearer ${token}` }

        // Fetch lesson and chat history in parallel for faster loading
        const [lessonRes, chatRes] = await Promise.all([
          fetch(`${apiUrl}/api/learn/${courseSlug}/${lessonSlug}`, { headers }),
          fetch(`${apiUrl}/api/learn/${courseSlug}/${lessonSlug}/chat`, { headers })
        ])

        if (lessonRes.status === 401) {
          setError('Session expired. Please sign in again.')
          setLoading(false)
          return
        }

        if (!lessonRes.ok) {
          throw new Error('Failed to fetch lesson')
        }

        const lessonData = await lessonRes.json()
        setLesson(lessonData)
        setError(null)

        if (chatRes.ok) {
          const chatData = await chatRes.json()
          setMessages(chatData.messages || [])
        }

        // Mark lesson as in progress (fire-and-forget, don't block rendering)
        fetch(`${apiUrl}/api/learn/${courseSlug}/${lessonSlug}/progress`, {
          method: 'POST',
          headers: { ...headers, 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'in_progress' })
        }).catch(err => console.warn('Failed to update progress:', err))

      } catch (err) {
        console.error('Failed to fetch lesson:', err)
        setError('Failed to load lesson. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    if (courseSlug && lessonSlug && isLoaded) {
      fetchLesson()
    }
  }, [courseSlug, lessonSlug, getToken, isLoaded, isSignedIn])

  const sendMessage = async () => {
    if (!inputMessage.trim() || sendingMessage) return

    setSendingMessage(true)
    const userMessage = inputMessage
    setInputMessage('')

    // Optimistically add user message
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      const token = await getToken()
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/learn/${courseSlug}/${lessonSlug}/chat`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message: userMessage })
        }
      )

      const data = await res.json()
      setMessages(data.messages || [])
    } catch (err) {
      console.error('Failed to send message:', err)
      // Revert optimistic update on error
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setSendingMessage(false)
    }
  }

  const markLessonComplete = async () => {
    try {
      const token = await getToken()
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/learn/${courseSlug}/${lessonSlug}/progress`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ status: 'completed' })
        }
      )
    } catch (err) {
      console.error('Failed to mark lesson complete:', err)
    }
  }

  const completeLessonAndRedirect = async () => {
    if (completingLesson) return

    setCompletingLesson(true)
    try {
      await markLessonComplete()
      router.push(`/learn/${courseSlug}`)
    } catch (err) {
      console.error('Failed to complete lesson:', err)
    } finally {
      setCompletingLesson(false)
    }
  }

  if (loading || !isLoaded) {
    return <LoadingScreen isVisible={true} />
  }

  if (error || !isSignedIn) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-xl text-red-500 mb-4">
            {error || 'Please sign in to access this lesson'}
          </div>
          <SignInButton mode="modal">
            <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded transition-colors">
              Sign In
            </button>
          </SignInButton>
          <div className="mt-4">
            <Link href={`/learn/${courseSlug}`} className="text-blue-600 hover:underline">
              ← Back to Course
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (!lesson) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-xl text-red-500 mb-4">Lesson not found</div>
          <Link href={`/learn/${courseSlug}`} className="text-blue-600 hover:underline">
            ← Back to Course
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <button
        onClick={() => router.push(`/learn/${courseSlug}`)}
        className="text-blue-600 hover:underline mb-4"
      >
        ← Back to {lesson.course_title || 'Course'}
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lesson Content */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h1 className="text-3xl font-bold mb-4">{lesson.title}</h1>

          <span className={`inline-block px-3 py-1 rounded-full text-sm mb-6 ${
            lesson.lesson_type === 'theory'
              ? 'bg-blue-100 text-blue-800'
              : lesson.lesson_type === 'exercise'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-purple-100 text-purple-800'
          }`}>
            {lesson.lesson_type}
          </span>

          <div className="prose dark:prose-invert max-w-none mb-6">
            <ReactMarkdown>{lesson.content}</ReactMarkdown>
          </div>

          {lesson.exercise_fen && (lesson.solution_move || lesson.exercise_solution?.targets) && (
            <div className="mb-6">
              <h3 className="font-semibold mb-4">Interactive Exercise:</h3>
              <AnimatedChessBoard
                fen={lesson.exercise_fen}
                solutionMove={lesson.solution_move || undefined}
                targetSquares={lesson.exercise_solution?.targets}
                onCorrectMove={markLessonComplete}
                onIncorrectMove={(move) => {
                  console.log('Incorrect move attempted:', move)
                }}
                showHints={true}
                enableAnimations={true}
                arrowFromSquare={lesson.exercise_solution?.arrow?.from}
                arrowPath={lesson.exercise_solution?.arrow?.path}
                showArrowsOverlay={!lesson.exercise_solution?.targets}
              />
              {lesson.hint_text && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-4">
                  💡 Hint: {lesson.hint_text}
                </p>
              )}
            </div>
          )}

          <button
            onClick={completeLessonAndRedirect}
            disabled={completingLesson}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded transition-colors disabled:opacity-50"
          >
            {completingLesson ? 'Completing...' : 'Complete Lesson'}
          </button>
        </div>

        {/* AI Chat */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 flex flex-col h-[600px]">
          <h2 className="text-xl font-bold mb-4">AI Tutor</h2>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.length === 0 && (
              <p className="text-gray-500 text-center mt-8">
                Ask your AI tutor any questions about this lesson!
              </p>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-100 dark:bg-blue-900 ml-8'
                    : 'bg-gray-100 dark:bg-gray-700 mr-8'
                }`}
              >
                <div className="font-semibold text-sm mb-1">
                  {msg.role === 'user' ? 'You' : 'AI Tutor'}
                </div>
                <div className="text-sm">{msg.content}</div>
              </div>
            ))}

            {sendingMessage && (
              <div className="bg-gray-100 dark:bg-gray-700 mr-8 p-3 rounded-lg">
                <div className="font-semibold text-sm mb-1">AI Tutor</div>
                <div className="text-sm">Thinking...</div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex space-x-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Ask a question..."
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
              disabled={sendingMessage}
            />
            <button
              onClick={sendMessage}
              disabled={sendingMessage || !inputMessage.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
