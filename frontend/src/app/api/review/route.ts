import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5001';

/** POST /api/review {pgn} → proxies to Flask, returns {review_id, status}. */
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  if (!body?.pgn || typeof body.pgn !== 'string') {
    return NextResponse.json({ error: 'pgn is required' }, { status: 400 });
  }
  try {
    const res = await fetch(`${BACKEND_URL}/api/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pgn: body.pgn }),
      signal: AbortSignal.timeout(8000),
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Review service unavailable' }, { status: 502 });
  }
}
