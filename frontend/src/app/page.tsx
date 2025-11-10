'use client'

import { useAuth } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import LoadingScreen from '@/components/LoadingScreen'

export default function HomePage() {
  const { isSignedIn, isLoaded } = useAuth()
  const router = useRouter()

  // Redirect to dashboard if already signed in
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.push('/dashboard')
    }
  }, [isLoaded, isSignedIn, router])

  // Show loading animation if not loaded
  if (!isLoaded) {
    return <LoadingScreen isVisible={true} />
  }

  // Show loading animation while redirecting
  if (isSignedIn) {
    return <LoadingScreen isVisible={true} />
  }

  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-purple-600 to-indigo-900 text-white">
        <div className="container mx-auto px-4 py-20">
          <div className="max-w-4xl mx-auto text-center space-y-8">
            {/* Logo/Icon */}
            <div className="flex justify-center">
              <div className="w-24 h-24 bg-white/10 backdrop-blur-lg rounded-full flex items-center justify-center border-4 border-white/20">
                <span className="text-6xl">♟️</span>
              </div>
            </div>

            {/* Heading */}
            <h1 className="text-5xl md:text-6xl font-bold">
              Chess Learning Platform
            </h1>

            <p className="text-xl md:text-2xl text-purple-100 max-w-2xl mx-auto">
              Master chess with AI-powered lessons, personalized tutoring, and interactive exercises
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-8">
              <button
                onClick={() => router.push('/sign-up')}
                className="bg-white text-purple-600 px-8 py-4 rounded-lg font-semibold text-lg hover:bg-purple-50 transition-all transform hover:scale-105 shadow-xl"
              >
                Get Started Free
              </button>
              <button
                onClick={() => router.push('/sign-in')}
                className="bg-purple-500/20 backdrop-blur-sm text-white px-8 py-4 rounded-lg font-semibold text-lg hover:bg-purple-500/30 transition-all border-2 border-white/30"
              >
                Sign In
              </button>
            </div>

            <p className="text-purple-200 text-sm">
              No credit card required • Start learning immediately
            </p>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-gray-50 dark:bg-gray-900 py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 dark:text-white">
            Why Learn With Us?
          </h2>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Feature 1 */}
            <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow">
              <div className="text-4xl mb-4">🤖</div>
              <h3 className="text-xl font-bold mb-3 dark:text-white">AI-Powered Tutoring</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Get instant answers to your chess questions with our intelligent AI tutor that adapts to your skill level
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow">
              <div className="text-4xl mb-4">📚</div>
              <h3 className="text-xl font-bold mb-3 dark:text-white">Structured Lessons</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Progress through carefully designed courses covering everything from basic tactics to advanced strategy
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow">
              <div className="text-4xl mb-4">📈</div>
              <h3 className="text-xl font-bold mb-3 dark:text-white">Track Your Progress</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Monitor your improvement with detailed progress tracking and unlock new lessons as you advance
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="bg-white dark:bg-gray-800 py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12 dark:text-white">
            How It Works
          </h2>

          <div className="max-w-3xl mx-auto space-y-8">
            {/* Step 1 */}
            <div className="flex gap-6 items-start">
              <div className="flex-shrink-0 w-12 h-12 bg-purple-600 text-white rounded-full flex items-center justify-center font-bold text-xl">
                1
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2 dark:text-white">Sign Up & Choose Your Course</h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Create your free account and browse our carefully structured chess courses designed for all skill levels
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex gap-6 items-start">
              <div className="flex-shrink-0 w-12 h-12 bg-purple-600 text-white rounded-full flex items-center justify-center font-bold text-xl">
                2
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2 dark:text-white">Learn at Your Own Pace</h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Study lessons with rich content, practice exercises, and get help from your personal AI chess tutor
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex gap-6 items-start">
              <div className="flex-shrink-0 w-12 h-12 bg-purple-600 text-white rounded-full flex items-center justify-center font-bold text-xl">
                3
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2 dark:text-white">Track Your Improvement</h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Complete lessons to unlock new content and watch your chess skills grow with our progress tracking system
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Final CTA Section */}
      <div className="bg-gradient-to-br from-indigo-900 to-purple-600 text-white py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to Improve Your Chess?
          </h2>
          <p className="text-xl text-purple-100 mb-8 max-w-2xl mx-auto">
            Join thousands of players learning chess the smart way with AI-powered instruction
          </p>
          <button
            onClick={() => router.push('/sign-up')}
            className="bg-white text-purple-600 px-10 py-4 rounded-lg font-semibold text-xl hover:bg-purple-50 transition-all transform hover:scale-105 shadow-xl"
          >
            Start Learning Now
          </button>
        </div>
      </div>
    </main>
  )
}
