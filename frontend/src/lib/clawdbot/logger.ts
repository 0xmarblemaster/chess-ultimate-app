// frontend/src/lib/clawdbot/logger.ts
// Fire-and-forget logging utilities for chat and activity tracking
import { callGateway } from './gateway';
import { getUserWorkspace } from './workspace';
import type { ActivityEventType } from './types';

/**
 * Log a chat conversation to the user's workspace.
 * Fire-and-forget — never blocks UX.
 */
export function logChat(
  userId: string,
  source: string,
  messages: Array<{ role: string; content: string; timestamp?: string }>
): void {
  const workspace = getUserWorkspace(userId);
  const date = new Date().toISOString().split('T')[0];
  const filePath = `${workspace.chatsPath}/${date}-${source}.jsonl`;

  const entry = JSON.stringify({
    timestamp: new Date().toISOString(),
    source,
    messages: messages.map(m => ({
      role: m.role,
      content: m.content.substring(0, 2000), // Truncate long messages
      timestamp: m.timestamp || new Date().toISOString(),
    })),
  });

  const prompt = `Append the following line to the file ${filePath} (create if it doesn't exist). Do NOT respond with analysis — just append and confirm.

\`\`\`
${entry}
\`\`\``;

  callGateway(userId, {
    action: 'log-chat',
    payload: { message: prompt },
    timeout: 10000,
  }).catch(() => {});
}

/**
 * Log an activity event to the user's workspace.
 * Fire-and-forget — never blocks UX.
 */
export function logActivity(
  userId: string,
  type: ActivityEventType,
  data: Record<string, unknown>
): void {
  const workspace = getUserWorkspace(userId);
  const date = new Date().toISOString().split('T')[0];
  const filePath = `${workspace.activityPath}/${date}.jsonl`;

  const entry = JSON.stringify({
    timestamp: new Date().toISOString(),
    type,
    data,
  });

  const prompt = `Append the following line to the file ${filePath} (create if it doesn't exist). Do NOT respond with analysis — just append and confirm.

\`\`\`
${entry}
\`\`\``;

  callGateway(userId, {
    action: 'log-activity',
    payload: { message: prompt },
    timeout: 10000,
  }).catch(() => {});
}
