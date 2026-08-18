/**
 * Admin gamification legions proxy (Legions tab) — per-legion endpoints.
 * Clerk-gated → forwards to Flask `/api/admin/.../gamification/legions/<legionId>`.
 */
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5001';

async function forward(
  method: 'PUT' | 'DELETE',
  orgId: string,
  legionId: string,
  userId: string,
  body?: unknown,
) {
  const res = await fetch(
    `${BACKEND_URL}/api/admin/organizations/${orgId}/gamification/legions/${legionId}`,
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

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ orgId: string; legionId: string }> },
) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId, legionId } = await params;
  const body = await req.json();
  try {
    return await forward('PUT', orgId, legionId, userId, body);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ orgId: string; legionId: string }> },
) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId, legionId } = await params;
  try {
    return await forward('DELETE', orgId, legionId, userId);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}
