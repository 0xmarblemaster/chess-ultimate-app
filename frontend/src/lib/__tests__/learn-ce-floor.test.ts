/**
 * Tests for resolveCeLevelFloor — the CE student level-floor resolver that
 * feeds the `/learn` gating. Mocks next/headers, Clerk auth, membership lookup,
 * and the CE profile client so we assert only the pure decision logic.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// ---- Mock stores (mutated per test) --------------------------------------
const headerStore: Record<string, string | null> = {
  'x-org-id': 'org-ce',
  'x-org-slug': 'chess-empire',
}
const authStore: { userId: string | null } = { userId: 'user-1' }
const memberStore: {
  state: string
  role: string
  source: string
  studentId: string | null
  throws: boolean
} = {
  state: 'verified',
  role: 'student',
  source: 'chess_empire',
  studentId: 'stu-1',
  throws: false,
}
const profileStore: { current_level: number | null | undefined; throws: boolean } = {
  current_level: 3,
  throws: false,
}

vi.mock('next/headers', () => ({
  headers: async () => ({
    get: (k: string) => headerStore[k] ?? null,
  }),
}))

vi.mock('@clerk/nextjs/server', () => ({
  auth: async () => ({ userId: authStore.userId }),
}))

vi.mock('@/lib/chess-empire-member', () => ({
  getMembershipState: vi.fn(async () => {
    if (memberStore.throws) throw new Error('lookup failed')
    return {
      state: memberStore.state,
      role: memberStore.role,
      source: memberStore.source,
      studentId: memberStore.studentId,
      memberId: memberStore.studentId ? 'mem-1' : null,
    }
  }),
}))

vi.mock('@/lib/chess-empire-client', () => ({
  getStudentProfile: vi.fn(async () => {
    if (profileStore.throws) throw new Error('profile failed')
    return { id: 'stu-1', current_level: profileStore.current_level }
  }),
}))

import { resolveCeLevelFloor } from '../learn-ce-floor'

beforeEach(() => {
  headerStore['x-org-id'] = 'org-ce'
  headerStore['x-org-slug'] = 'chess-empire'
  authStore.userId = 'user-1'
  memberStore.state = 'verified'
  memberStore.role = 'student'
  memberStore.source = 'chess_empire'
  memberStore.studentId = 'stu-1'
  memberStore.throws = false
  profileStore.current_level = 3
  profileStore.throws = false
})

describe('resolveCeLevelFloor', () => {
  it('returns undefined for a non-chess-empire org slug', async () => {
    headerStore['x-org-slug'] = 'some-other-org'
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined when there is no org id', async () => {
    headerStore['x-org-id'] = null
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined when there is no signed-in user', async () => {
    authStore.userId = null
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined for a no_link membership', async () => {
    memberStore.state = 'no_link'
    memberStore.studentId = null
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined for an online-source member', async () => {
    memberStore.source = 'online'
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined for a coach role', async () => {
    memberStore.role = 'coach'
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined when the membership lookup throws (no crash)', async () => {
    memberStore.throws = true
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns the current level for a verified student', async () => {
    expect(await resolveCeLevelFloor()).toBe(3)
  })

  it('accepts a pending_confirm student', async () => {
    memberStore.state = 'pending_confirm'
    expect(await resolveCeLevelFloor()).toBe(3)
  })

  it('returns undefined when getStudentProfile throws (no crash)', async () => {
    profileStore.throws = true
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined when current_level is null', async () => {
    profileStore.current_level = null
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined when current_level is 0', async () => {
    profileStore.current_level = 0
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })

  it('returns undefined when current_level is undefined', async () => {
    profileStore.current_level = undefined
    expect(await resolveCeLevelFloor()).toBeUndefined()
  })
})
