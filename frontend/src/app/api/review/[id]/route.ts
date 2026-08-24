import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5001';

/** GET /api/review/[id] → proxies to Flask, returns {status, progress, result?}. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const res = await fetch(`${BACKEND_URL}/api/review/${encodeURIComponent(id)}`, {
      signal: AbortSignal.timeout(8000),
      cache: 'no-store',
    });
    if (res.status === 404) {
      return NextResponse.json({ error: 'Review not found' }, { status: 404 });
    }
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Review service unavailable' }, { status: 502 });
  }
}
