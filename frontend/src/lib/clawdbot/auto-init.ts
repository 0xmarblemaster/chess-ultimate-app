// frontend/src/lib/clawdbot/auto-init.ts
// Idempotent user registration — checks workspace, creates if missing, logs login
import { checkWorkspaceExists, initializeUserWorkspace } from './onboarding';

interface ClerkUserInfo {
  firstName?: string | null;
  lastName?: string | null;
  username?: string | null;
  emailAddress?: string | null;
}

function getDisplayName(user: ClerkUserInfo): string {
  if (user.firstName) {
    return user.lastName ? `${user.firstName} ${user.lastName}` : user.firstName;
  }
  return user.username || user.emailAddress || 'Chess Player';
}

/**
 * Ensures a user workspace exists in Clawdbot. Idempotent — safe to call on every login.
 * Non-blocking: callers should fire-and-forget with .catch(() => {}).
 */
export async function ensureUserRegistered(
  userId: string,
  clerkUser: ClerkUserInfo
): Promise<{ ready: boolean; isNew: boolean }> {
  try {
    const exists = await checkWorkspaceExists(userId);

    if (exists) {
      // Workspace exists — log login timestamp (fire-and-forget)
      logLoginTimestamp(userId).catch(() => {});
      return { ready: true, isNew: false };
    }

    // Workspace doesn't exist — create it
    const displayName = getDisplayName(clerkUser);
    const result = await initializeUserWorkspace(userId, displayName);

    if (result.success) {
      return { ready: true, isNew: true };
    }

    console.warn('[clawdbot/auto-init] Workspace creation returned failure:', result.error);
    return { ready: false, isNew: false };
  } catch (err) {
    console.warn('[clawdbot/auto-init] ensureUserRegistered failed (non-fatal):', err);
    return { ready: false, isNew: false };
  }
}

async function logLoginTimestamp(userId: string): Promise<void> {
  const { callGateway } = await import('./gateway');
  const { getUserWorkspace } = await import('./workspace');
  const workspace = getUserWorkspace(userId);
  const now = new Date().toISOString();

  await callGateway(userId, {
    action: 'log-activity',
    payload: {
      message: `Append to ${workspace.activityPath}/${now.split('T')[0]}.jsonl:\n${JSON.stringify({ type: 'login', userId, timestamp: now })}`
    },
    timeout: 5000
  });
}
