import { describe, it, expect } from 'vitest'
import { computeLockStates, type GatingCourse } from '../learn-gating'

// Helper: build N courses with order_index 1..N and ids "c1".."cN".
function makeCourses(n: number): GatingCourse[] {
  return Array.from({ length: n }, (_, i) => ({ id: `c${i + 1}`, order_index: i + 1 }))
}

// Helper: progress map from a partial { id: progress } record.
function makeProgress(entries: Record<string, number>): Record<string, { progress: number }> {
  const map: Record<string, { progress: number }> = {}
  for (const [id, progress] of Object.entries(entries)) {
    map[id] = { progress }
  }
  return map
}

describe('computeLockStates', () => {
  it('returns {} for empty courses', () => {
    expect(computeLockStates([], {})).toEqual({})
  })

  it('single course is always unlocked', () => {
    const result = computeLockStates(makeCourses(1), {})
    expect(result).toEqual({ c1: false })
  })

  it('8 courses none complete: only first unlocked', () => {
    const result = computeLockStates(makeCourses(8), {})
    expect(result.c1).toBe(false)
    for (let i = 2; i <= 8; i++) {
      expect(result[`c${i}`]).toBe(true)
    }
  })

  it('course 1 at 100: courses 1 & 2 unlocked, 3-8 locked (cascade)', () => {
    const result = computeLockStates(makeCourses(8), makeProgress({ c1: 100 }))
    expect(result.c1).toBe(false)
    expect(result.c2).toBe(false)
    for (let i = 3; i <= 8; i++) {
      expect(result[`c${i}`]).toBe(true)
    }
  })

  it('courses 1-3 at 100: courses 1-4 unlocked, 5-8 locked', () => {
    const result = computeLockStates(
      makeCourses(8),
      makeProgress({ c1: 100, c2: 100, c3: 100 })
    )
    for (let i = 1; i <= 4; i++) {
      expect(result[`c${i}`]).toBe(false)
    }
    for (let i = 5; i <= 8; i++) {
      expect(result[`c${i}`]).toBe(true)
    }
  })

  it('scrambled input order_index is still gated correctly and input is not mutated', () => {
    const courses: GatingCourse[] = [
      { id: 'c3', order_index: 3 },
      { id: 'c1', order_index: 1 },
      { id: 'c2', order_index: 2 },
    ]
    const snapshot = courses.map((c) => ({ ...c }))
    const result = computeLockStates(courses, makeProgress({ c1: 100 }))
    expect(result).toEqual({ c1: false, c2: false, c3: true })
    // input array not mutated (same order, same contents)
    expect(courses).toEqual(snapshot)
  })

  it('missing progress entry is treated as 0 (locked unless first)', () => {
    const result = computeLockStates(makeCourses(3), {})
    expect(result).toEqual({ c1: false, c2: true, c3: true })
  })

  it('ceLevelFloor=3 with no progress: order_index 1,2,3 unlocked, 4-8 locked', () => {
    const result = computeLockStates(makeCourses(8), {}, 3)
    for (let i = 1; i <= 3; i++) {
      expect(result[`c${i}`]).toBe(false)
    }
    for (let i = 4; i <= 8; i++) {
      expect(result[`c${i}`]).toBe(true)
    }
  })

  it('ceLevelFloor gates by 1-based position, not raw order_index (prod order_index runs 3..10)', () => {
    // Production courses are ordered but NOT 1-based: order_index 3,4,5,...,10.
    // A CE student at level 3 must get the first 3 courses (positions 1-3),
    // regardless of the raw order_index values.
    const courses: GatingCourse[] = Array.from({ length: 8 }, (_, i) => ({
      id: `c${i + 1}`,
      order_index: i + 3, // 3,4,5,6,7,8,9,10
    }))
    const result = computeLockStates(courses, {}, 3)
    // positions 1,2,3 unlocked
    expect(result.c1).toBe(false)
    expect(result.c2).toBe(false)
    expect(result.c3).toBe(false)
    // positions 4-8 locked
    for (let i = 4; i <= 8; i++) {
      expect(result[`c${i}`]).toBe(true)
    }
  })

  it('CE student at level 3 who also completed course 4 unlocks course 5 via prevComplete', () => {
    // Floor unlocks 1-3; completing course 4 in-app (progress 100) makes course
    // 5 unlocked via prevComplete even though the floor alone would not reach it.
    const result = computeLockStates(makeCourses(8), makeProgress({ c4: 100 }), 3)
    expect(result.c1).toBe(false)
    expect(result.c2).toBe(false)
    expect(result.c3).toBe(false)
    expect(result.c5).toBe(false) // unlocked because previous course (4) is complete
    for (const i of [6, 7, 8]) {
      expect(result[`c${i}`]).toBe(true)
    }
  })
})
