'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { useParams, useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'

interface Lesson {
  id: string
  title: string
  content: string
  lesson_type: string
  exercise_fen: string | null
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function LessonPage() {
  const { id } = useParams()
  const router = useRouter()
  const { getToken } = useAuth()
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  const [completingLesson, setCompletingLesson] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchLesson() {
      try {
        const token = await getToken()

        // Fetch lesson
        const lessonRes = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/lessons/${id}`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )

        if (!lessonRes.ok) {
          throw new Error('Failed to fetch lesson')
        }

        const lessonData = await lessonRes.json()
        setLesson(lessonData)

        // Fetch chat history
        const chatRes = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/lessons/${id}/chat`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )

        if (chatRes.ok) {
          const chatData = await chatRes.json()
          setMessages(chatData.messages || [])
        }

        // Mark lesson as in progress
        await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/lessons/${id}/progress`,
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: 'in_progress' })
          }
        )
      } catch (err) {
        console.error('Failed to fetch lesson:', err)
      } finally {
        setLoading(false)
      }
    }

    if (id) {
      fetchLesson()
    }
  }, [id, getToken])

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
        `${process.env.NEXT_PUBLIC_API_URL}/api/lessons/${id}/chat`,
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

  const completeLesson = async () => {
    if (completingLesson) return

    setCompletingLesson(true)
    try {
      const token = await getToken()
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/lessons/${id}/progress`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ status: 'completed' })
        }
      )

      // Redirect back to course
      router.back()
    } catch (err) {
      console.error('Failed to complete lesson:', err)
    } finally {
      setCompletingLesson(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading lesson...</div>
      </div>
    )
  }

  if (!lesson) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-red-500">Lesson not found</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <button
        onClick={() => router.back()}
        className="text-blue-600 hover:underline mb-4"
      >
        ← Back to Course
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

          {lesson.exercise_fen && (
            <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg mb-6">
              <h3 className="font-semibold mb-2">Exercise Position (FEN):</h3>
              <code className="text-sm break-all">{lesson.exercise_fen}</code>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                Chess board visualization will be added in a future update.
              </p>
            </div>
          )}

          <button
            onClick={completeLesson}
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
