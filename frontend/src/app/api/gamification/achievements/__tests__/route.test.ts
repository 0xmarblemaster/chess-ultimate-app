import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/gamification/resolve-student', () => ({ resolveStudent: vi.fn() }));
vi.mock('@/lib/chess-empire-client', () => ({ getStudentAchievements: vi.fn() }));

import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getStudentAchievements } from '@/lib/chess-empire-client';

const m = (fn: unknown) =>
  fn as unknown as {
    mockResolvedValue: (v: unknown) => void;
    mockRejectedValue: (v: unknown) => void;
  };

describe('GET /api/gamification/achievements', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns an empty list for an unlinked caller', async () => {
    m(resolveStudent).mockResolvedValue({ ok: false, status: 403, error: 'not_linked' });
    const { GET } = await import('../route');
    const res = await GET();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ achievements: [] });
    expect(getStudentAchievements).not.toHaveBeenCalled();
  });

  it('returns the resolved student achievements', async () => {
    m(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    m(getStudentAchievements).mockResolvedValue([
      { id: 'a1', name: 'First win', earned_at: '2026-02-01' },
    ]);
    const { GET } = await import('../route');
    const res = await GET();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.achievements).toHaveLength(1);
    expect(getStudentAchievements).toHaveBeenCalledWith('stu-1');
  });

  it('degrades to an empty list when the CE fetch throws', async () => {
    m(resolveStudent).mockResolvedValue({ ok: true, orgId: 'org-1', studentId: 'stu-1' });
    m(getStudentAchievements).mockRejectedValue(new Error('CE down'));
    const { GET } = await import('../route');
    const res = await GET();
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ achievements: [] });
  });
});
