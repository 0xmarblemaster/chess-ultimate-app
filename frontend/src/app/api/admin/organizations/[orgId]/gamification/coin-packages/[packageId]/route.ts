/**
 * Admin coin-packages proxy (Coins tab) — per-package endpoints.
 * Clerk-gated → forwards to Flask `/api/admin/.../gamification/coin-packages/<id>`.
 */
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5001';

async function forward(
  method: 'PUT' | 'DELETE',
  orgId: string,
  packageId: string,
  userId: string,
  body?: unknown,
) {
  const res = await fetch(
    `${BACKEND_URL}/api/admin/organizations/${orgId}/gamification/coin-packages/${packageId}`,
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
  { params }: { params: Promise<{ orgId: string; packageId: string }> },
) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId, packageId } = await params;
  const body = await req.json();
  try {
    return await forward('PUT', orgId, packageId, userId, body);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ orgId: string; packageId: string }> },
) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { orgId, packageId } = await params;
  try {
    return await forward('DELETE', orgId, packageId, userId);
  } catch {
    return NextResponse.json({ error: 'Service unavailable' }, { status: 502 });
  }
}
