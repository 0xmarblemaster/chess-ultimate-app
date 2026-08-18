/**
 * Admin gamification seasons proxy (Seasons tab) — per-season endpoints.
 * Clerk-gated → forwards to Flask `/api/admin/.../gamification/seasons/<seasonId>`.
 * Closing a season is a separate job (./close) — not a bare PUT.
 */
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5001';

async function forward(
  method: 'PUT' | 'DELETE',
  orgId: string,
  seasonId: string,
  userId: string,
  body?: unknown,
) {
  const res = await fetch(
    `${BACKEND_URL}/api/admin/organizations/${orgId}/gamification/seasons/${seasonId}`,
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
  { params }: { params: Promise<{ orgId: string; seasonId: string }> },
) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId, seasonId } = await params;
  const body = await req.json();
  try {
    return await forward('PUT', orgId, seasonId, userId, body);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ orgId: string; seasonId: string }> },
) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId, seasonId } = await params;
  try {
    return await forward('DELETE', orgId, seasonId, userId);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}
