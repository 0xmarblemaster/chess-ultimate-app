/**
 * Admin gamification legions proxy (Legions tab) — collection endpoints.
 * Clerk-gated → forwards to Flask `/api/admin/.../gamification/legions`.
 */
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5001';

async function forward(
  method: 'GET' | 'POST',
  orgId: string,
  userId: string,
  body?: unknown,
) {
  const res = await fetch(
    `${BACKEND_URL}/api/admin/organizations/${orgId}/gamification/legions`,
    {
      method,
      headers: { 'Content-Type': 'application/json', 'X-User-Id': userId },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    },
  );
  const data = await res.json().catch(() => ({ error: 'Backend error' }));
  return NextResponse.json(data, { status: res.status });
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ orgId: string }> }) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId } = await params;
  try {
    return await forward('GET', orgId, userId);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ orgId: string }> }) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId } = await params;
  const body = await req.json();
  try {
    return await forward('POST', orgId, userId, body);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}
