"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth, UserButton } from "@clerk/nextjs"

export default function NavBar() {
  const [mounted, setMounted] = useState(false)
  const { isSignedIn } = useAuth()
  const router = useRouter()

  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <nav className="bg-gray-900 text-white" suppressHydrationWarning>
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="text-xl font-bold">Chess Learning Platform</div>
            <div className="h-8 w-24"></div>
          </div>
        </div>
      </nav>
    )
  }

  return (
    <nav className="bg-gray-900 text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="text-xl font-bold hover:text-purple-400 transition-colors"
          >
            ♟️ Chess Learning Platform
          </button>

          <div className="flex items-center gap-6">
            {isSignedIn ? (
              <>
                <button
                  onClick={() => router.push("/dashboard")}
                  className="hover:text-purple-400 transition-colors"
                >
                  Dashboard
                </button>
                <UserButton
                  appearance={{
                    elements: {
                      avatarBox: "w-10 h-10"
                    }
                  }}
                />
              </>
            ) : (
              <>
                <button
                  onClick={() => router.push("/sign-in")}
                  className="hover:text-purple-400 transition-colors"
                >
                  Sign In
                </button>
                <button
                  onClick={() => router.push("/sign-up")}
                  className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition-colors"
                >
                  Get Started
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
