/**
 * GET /api/chess-empire/link/status
 *
 * Returns the current Clerk user's Chess Empire link state
 * (`no_link` | `pending_confirm` | `verified`). No params — the row is
 * resolved by the caller's Clerk session. Polled by the `no_link` view on the
 * dashboard to detect when the async webhook (or the client claim) has written
 * the member row, so it can `router.refresh()` into the personalized page.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';
import { getMembershipStateForUser } from '@/lib/chess-empire-member';
import {
  autoClaimPendingCookie,
  hasLivePendingCookie,
} from '@/lib/pending-registration';

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  try {
    // Auto-claim any pending cookie before reporting state, so a polling client
    // that never managed a body-JWT replay still links from the cookie alone.
    await autoClaimPendingCookie(userId);
    const membership = await getMembershipStateForUser(userId);
    // `recoverable` tells a still-`no_link` client whether the branch link can
    // yet complete from server-side cookie state, or whether it's a dead end
    // (e.g. an external browser after an in-app-webview OAuth bounce, which
    // carries no pending cookie). The `state` field is unchanged.
    const recoverable = await hasLivePendingCookie();
    return NextResponse.json({
      state: membership.state,
      role: membership.role,
      recoverable,
    });
  } catch (err) {
    console.error('[chess-empire/link/status] lookup failed', err);
    return NextResponse.json({ error: 'server_error' }, { status: 500 });
  }
}
