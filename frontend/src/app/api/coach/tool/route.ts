import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

const HERMES_URL = process.env.HERMES_URL || 'http://localhost:8642';

// Some tools run Stockfish or hit external APIs — allow a generous timeout.
const TOOL_TIMEOUT_MS = 90000;

/**
 * POST /api/coach/tool — proxy a single voice-coach tool call to Hermes.
 * Body: { name, args, session_id? }. Clerk-authenticated; the browser never
 * talks to Hermes directly and the user identity is set server-side.
 */
export async function POST(request: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  let body: { name?: string; args?: Record<string, unknown>; session_id?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!body.name || typeof body.name !== 'string') {
    return NextResponse.json({ error: 'Missing tool name' }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${HERMES_URL}/api/coach/tool/${encodeURIComponent(body.name)}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': userId,
        },
        body: JSON.stringify({
          args: body.args ?? {},
          session_id: body.session_id,
        }),
        signal: AbortSignal.timeout(TOOL_TIMEOUT_MS),
      },
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: `Hermes error: ${response.status}` },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
