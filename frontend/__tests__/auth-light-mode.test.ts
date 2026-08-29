import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

const read = (rel: string) => readFileSync(join(__dirname, '..', rel), 'utf8')

const signIn = read('src/app/sign-in/[[...sign-in]]/page.tsx')
const signUp = read('src/app/sign-up/[[...sign-up]]/page.tsx')
const css = read('src/app/globals.css')

describe('auth pages force light mode under app dark theme', () => {
  it('marks the sign-in page root with the auth-light class', () => {
    expect(signIn).toMatch(/className="auth-light /)
  })

  it('marks the sign-up page root with the auth-light class', () => {
    expect(signUp).toMatch(/className="auth-light /)
  })

  it('keeps the blanket html.dark overrides intact (other pages depend on them)', () => {
    expect(css).toMatch(/html\.dark \.bg-white \{ background-color: #1a1a1a !important; \}/)
    expect(css).toMatch(/html\.dark input, html\.dark textarea, html\.dark select \{/)
  })

  it('restores the semantic CSS variables the Clerk inline styles depend on', () => {
    const varBlock = css.match(/html\.dark \.auth-light \{[\s\S]*?\}/)?.[0] ?? ''
    expect(varBlock).toMatch(/--surface-card: #FFFFFF;/)
    expect(varBlock).toMatch(/--surface-input: #FFFFFF;/)
    expect(varBlock).toMatch(/--text-primary: #18181B;/)
    expect(varBlock).toMatch(/--border-default: #e5e7eb;/)
  })

  // Every blanket-overridden utility class used on the auth pages (JSX or the
  // Clerk appearance `elements`) must have a matching html.dark .auth-light
  // counter-override restoring its original light value.
  const counters: Record<string, RegExp> = {
    'bg-white': /html\.dark \.auth-light \.bg-white \{ background-color: #ffffff !important; \}/,
    'bg-gray-200': /html\.dark \.auth-light \.bg-gray-200 \{ background-color: #e5e7eb !important; \}/,
    'bg-purple-50': /html\.dark \.auth-light \.bg-purple-50 \{ background-color: #faf5ff !important; \}/,
    'text-gray-800': /html\.dark \.auth-light \.text-gray-800 \{ color: #1f2937 !important; \}/,
    'text-gray-700': /html\.dark \.auth-light \.text-gray-700 \{ color: #374151 !important; \}/,
    'text-gray-500': /html\.dark \.auth-light \.text-gray-500 \{ color: #6b7280 !important; \}/,
    'text-gray-400': /html\.dark \.auth-light \.text-gray-400 \{ color: #9ca3af !important; \}/,
    'text-purple-700': /html\.dark \.auth-light \.text-purple-700 \{ color: #7e22ce !important; \}/,
    'text-purple-600': /html\.dark \.auth-light \.text-purple-600 \{ color: #9333ea !important; \}/,
    'border-gray-200': /html\.dark \.auth-light \.border-gray-200 \{ border-color: #e5e7eb !important; \}/,
  }

  for (const [cls, re] of Object.entries(counters)) {
    it(`adds a scoped counter-override for .${cls}`, () => {
      expect(css).toMatch(re)
    })
  }

  it('restores the logo circle: html.dark .bg-white cannot blacken it under .auth-light', () => {
    // The scoped override must exist AND out-specify the blanket rule.
    expect(css).toMatch(/html\.dark \.auth-light \.bg-white \{ background-color: #ffffff !important; \}/)
  })

  it('restores Clerk <input> elements to white background with dark text', () => {
    const inputBlock = css.match(
      /html\.dark \.auth-light input,\s*\n\s*html\.dark \.auth-light textarea,\s*\n\s*html\.dark \.auth-light select \{[\s\S]*?\}/
    )?.[0] ?? ''
    expect(inputBlock).toMatch(/background-color: #ffffff !important;/)
    expect(inputBlock).toMatch(/color: #18181B !important;/)
  })

  it('scopes every auth counter-override under .auth-light (never weakens blanket rules)', () => {
    const authRules = css
      .split('\n')
      .filter((l) => l.includes('.auth-light') && l.includes('!important'))
    expect(authRules.length).toBeGreaterThanOrEqual(Object.keys(counters).length)
    for (const line of authRules) {
      expect(line).toMatch(/^html\.dark \.auth-light /)
    }
  })
})
