export interface GatingCourse {
  id: string
  order_index: number
}

/**
 * Compute lock state per course for the learn path.
 *
 * Regular Chesster users (ceLevelFloor undefined): progressive unlock.
 *   - The first course (lowest order_index) is always unlocked.
 *   - Every later course is unlocked ONLY if the immediately-previous
 *     course (by order_index) has progress === 100.
 *
 * `ceLevelFloor` (Chess Empire students): when provided, a course is unlocked
 * if its 1-based position in the order_index-sorted list is <= ceLevelFloor,
 * OR the previous course is complete. Position (not raw order_index) is used
 * because the DB order_index values are not 1-based (they run 3..10), whereas
 * the CE current_level is 1..8. Level N ↔ the Nth course on the path.
 *
 * A course whose OWN progress is 100 is always unlocked — you can never lock a
 * course the user has already fully completed, regardless of earlier courses'
 * state (a user may finish a later course before an earlier one is at 100%).
 *
 * @param courses     courses to gate (any order; sorted internally by order_index asc)
 * @param progressMap map of courseId -> { progress } (0..100)
 * @param ceLevelFloor optional CE current_level (1..8); undefined for regular users
 * @returns map of courseId -> isLocked (boolean)
 */
export function computeLockStates(
  courses: GatingCourse[],
  progressMap: Record<string, { progress: number }>,
  ceLevelFloor?: number
): Record<string, boolean> {
  const sorted = [...courses].sort((a, b) => a.order_index - b.order_index)

  const lockStates: Record<string, boolean> = {}

  sorted.forEach((course, i) => {
    const prevComplete =
      i === 0
        ? true
        : (progressMap[sorted[i - 1].id]?.progress ?? 0) === 100

    const ownComplete = (progressMap[course.id]?.progress ?? 0) === 100

    const unlocked =
      i === 0 ||
      prevComplete ||
      ownComplete ||
      (ceLevelFloor !== undefined && i + 1 <= ceLevelFloor)

    lockStates[course.id] = !unlocked
  })

  return lockStates
}
