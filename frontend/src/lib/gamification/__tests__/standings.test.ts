import { describe, expect, it } from 'vitest';
import {
  type StandingsLegion,
  type StandingsStudent,
  computeStandings,
  planSeasonClose,
  studentProximity,
} from '../standings';

const LEGIONS: StandingsLegion[] = [
  { id: 'L1', name: 'Alpha' },
  { id: 'L2', name: 'Bravo' },
];

/** Terse student factory — linked by default. */
function stu(p: Partial<StandingsStudent> & Pick<StandingsStudent, 'student_id' | 'legion_id' | 'season_points'>): StandingsStudent {
  return {
    season_wins: 0,
    tournaments: 3,
    linked: true,
    first_reached_at: null,
    ...p,
  };
}

const OPTS = { top_n: 2, count_unlinked: false };

describe('computeStandings — Top-N legion scoring (§8.3)', () => {
  it('sums only the Top-N members per legion', () => {
    const students = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 10 }),
      stu({ student_id: 'b', legion_id: 'L1', season_points: 8 }),
      stu({ student_id: 'c', legion_id: 'L1', season_points: 5 }), // outside top-2, ignored
      stu({ student_id: 'd', legion_id: 'L2', season_points: 9 }),
    ];
    const s = computeStandings(LEGIONS, students, OPTS);
    const alpha = s.legions.find((l) => l.legion.id === 'L1')!;
    expect(alpha.points).toBe(18); // 10 + 8, not 23
    expect(alpha.member_count).toBe(3);
    expect(alpha.place).toBe(1);
    expect(alpha.gap_to_first).toBe(0);
    const bravo = s.legions.find((l) => l.legion.id === 'L2')!;
    expect(bravo.points).toBe(9);
    expect(bravo.place).toBe(2);
    expect(bravo.gap_to_first).toBe(9);
    expect(bravo.gap_to_above).toBe(9);
  });

  it('includes every legion even with zero members', () => {
    const s = computeStandings(LEGIONS, [], OPTS);
    expect(s.legions).toHaveLength(2);
    expect(s.legions.every((l) => l.points === 0)).toBe(true);
  });

  it('marks in_top_n and ranks members within a legion', () => {
    const students = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 10 }),
      stu({ student_id: 'b', legion_id: 'L1', season_points: 8 }),
      stu({ student_id: 'c', legion_id: 'L1', season_points: 5 }),
    ];
    const alpha = computeStandings(LEGIONS, students, OPTS).legions.find((l) => l.legion.id === 'L1')!;
    expect(alpha.members.map((m) => [m.student_id, m.place, m.in_top_n])).toEqual([
      ['a', 1, true],
      ['b', 2, true],
      ['c', 3, false],
    ]);
  });
});

describe('computeStandings — unlinked hidden (D-8)', () => {
  it('excludes unlinked students from totals and lists by default', () => {
    const students = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 10 }),
      stu({ student_id: 'x', legion_id: 'L1', season_points: 100, linked: false }),
    ];
    const alpha = computeStandings(LEGIONS, students, OPTS).legions.find((l) => l.legion.id === 'L1')!;
    expect(alpha.points).toBe(10); // the strong unlinked kid does not count
    expect(alpha.member_count).toBe(1);
  });

  it('linking a strong player instantly boosts the legion (recompute)', () => {
    const before = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 10 }),
      stu({ student_id: 'x', legion_id: 'L1', season_points: 100, linked: false }),
    ];
    const after = before.map((s) => (s.student_id === 'x' ? { ...s, linked: true } : s));
    const pBefore = computeStandings(LEGIONS, before, OPTS).legions.find((l) => l.legion.id === 'L1')!.points;
    const pAfter = computeStandings(LEGIONS, after, OPTS).legions.find((l) => l.legion.id === 'L1')!.points;
    expect(pBefore).toBe(10);
    expect(pAfter).toBe(110);
  });

  it('count_unlinked flag includes unlinked when set', () => {
    const students = [stu({ student_id: 'x', legion_id: 'L1', season_points: 50, linked: false })];
    const p = computeStandings(LEGIONS, students, { top_n: 2, count_unlinked: true }).legions.find(
      (l) => l.legion.id === 'L1',
    )!.points;
    expect(p).toBe(50);
  });
});

describe('computeStandings — branch transfer moves the score (D-11)', () => {
  it('a mid-season transfer moves the whole season score to the new legion', () => {
    const before = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 30 }),
      stu({ student_id: 'b', legion_id: 'L2', season_points: 5 }),
    ];
    const s1 = computeStandings(LEGIONS, before, OPTS);
    expect(s1.legions.find((l) => l.legion.id === 'L1')!.points).toBe(30);
    expect(s1.legions.find((l) => l.legion.id === 'L2')!.points).toBe(5);

    // `a` transfers from L1 to L2 — only their current legion_id changes.
    const after = before.map((s) => (s.student_id === 'a' ? { ...s, legion_id: 'L2' } : s));
    const s2 = computeStandings(LEGIONS, after, OPTS);
    expect(s2.legions.find((l) => l.legion.id === 'L1')!.points).toBe(0); // removed
    expect(s2.legions.find((l) => l.legion.id === 'L2')!.points).toBe(35); // added
  });

  it('students with an unmapped branch (null legion) are not scored', () => {
    const students = [stu({ student_id: 'a', legion_id: null, season_points: 40 })];
    const s = computeStandings(LEGIONS, students, OPTS);
    expect(s.legions.every((l) => l.points === 0)).toBe(true);
  });
});

describe('computeStandings — ties (§8.3)', () => {
  it('shared placement, tiebreak by Top-N wins', () => {
    const students = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 10, season_wins: 5 }),
      stu({ student_id: 'b', legion_id: 'L2', season_points: 10, season_wins: 8 }),
    ];
    const s = computeStandings(LEGIONS, students, OPTS);
    // Equal points → more wins ranks first; places are 1 and 2 (wins broke the tie).
    expect(s.legions[0].legion.id).toBe('L2');
    expect(s.legions[0].place).toBe(1);
    expect(s.legions[1].place).toBe(2);
  });

  it('genuinely tied legions share a place', () => {
    const students = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 10, season_wins: 4 }),
      stu({ student_id: 'b', legion_id: 'L2', season_points: 10, season_wins: 4 }),
    ];
    const s = computeStandings(LEGIONS, students, OPTS);
    expect(s.legions[0].place).toBe(1);
    expect(s.legions[1].place).toBe(1); // shared
  });
});

describe('studentProximity — second-ladder motivation (§8.3)', () => {
  const students = [
    stu({ student_id: 'a', legion_id: 'L1', season_points: 20 }),
    stu({ student_id: 'b', legion_id: 'L1', season_points: 15 }),
    stu({ student_id: 'c', legion_id: 'L1', season_points: 8 }), // outside top-2
  ];
  const s = computeStandings(LEGIONS, students, OPTS);

  it('a Top-N member needs 0 more points', () => {
    const p = studentProximity(s, 'a');
    expect(p).toMatchObject({ in_top_n: true, points_to_top_n: 0, place: 1 });
  });

  it('an outside member needs the gap to the cut line', () => {
    const p = studentProximity(s, 'c');
    expect(p.in_top_n).toBe(false);
    expect(p.place).toBe(3);
    expect(p.points_to_top_n).toBe(7); // 15 (2nd place cut) − 8
  });

  it('an unscored student gets a null legion', () => {
    expect(studentProximity(s, 'nobody').legion_id).toBeNull();
  });
});

describe('planSeasonClose — winner + trophy eligibility (§8.4, D-4)', () => {
  const legions: StandingsLegion[] = [
    { id: 'L1', name: 'Alpha' },
    { id: 'L2', name: 'Bravo' },
  ];

  it('grants trophies only to eligible members of the winning legion', () => {
    const students = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 30, tournaments: 5 }),
      stu({ student_id: 'b', legion_id: 'L1', season_points: 20, tournaments: 2 }), // below min
      stu({ student_id: 'c', legion_id: 'L2', season_points: 10, tournaments: 9 }), // not winner
    ];
    const standings = computeStandings(legions, students, { top_n: 5, count_unlinked: false });
    const plan = planSeasonClose(standings, { min_tournaments_for_trophy: 3 });
    expect(plan.winner_legion_id).toBe('L1');
    expect(plan.grants.map((g) => g.student_id)).toEqual(['a']); // b below 3, c wrong legion
    expect(plan.per_student).toHaveLength(3); // full snapshot
  });

  it('no winner when nobody scored', () => {
    const standings = computeStandings(legions, [], { top_n: 5, count_unlinked: false });
    const plan = planSeasonClose(standings, { min_tournaments_for_trophy: 3 });
    expect(plan.winner_legion_id).toBeNull();
    expect(plan.grants).toHaveLength(0);
  });

  it('unlinked members of the winning legion never receive a trophy', () => {
    const students = [
      stu({ student_id: 'a', legion_id: 'L1', season_points: 30, tournaments: 5 }),
      stu({ student_id: 'x', legion_id: 'L1', season_points: 99, tournaments: 9, linked: false }),
    ];
    const standings = computeStandings(legions, students, { top_n: 5, count_unlinked: false });
    const plan = planSeasonClose(standings, { min_tournaments_for_trophy: 3 });
    // x was excluded from standings entirely (D-8), so cannot be granted.
    expect(plan.grants.map((g) => g.student_id)).toEqual(['a']);
  });
});
