import type { ReviewJob } from './types';

/** POST a PGN to the review pipeline. Returns the review id + initial status. */
export async function startReview(pgn: string): Promise<{ review_id: string; status: string }> {
  const res = await fetch('/api/review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pgn }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.error || `Review request failed (${res.status})`);
  }
  return res.json();
}

/** Poll the review job. */
export async function fetchReview(id: string): Promise<ReviewJob> {
  const res = await fetch(`/api/review/${id}`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Review fetch failed (${res.status})`);
  }
  return res.json();
}
