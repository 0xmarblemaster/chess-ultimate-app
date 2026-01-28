// frontend/src/lib/clawdbot/onboarding.ts
import { callGateway } from './gateway';
import { getUserWorkspace, generatePlayerProfileTemplate } from './workspace';
import type { CoachingResponse } from './types';

export async function initializeUserWorkspace(
  userId: string,
  displayName: string
): Promise<CoachingResponse> {
  const workspace = getUserWorkspace(userId);
  const profileContent = generatePlayerProfileTemplate(displayName, userId);

  // Use Clawdbot to create the workspace structure
  const initPrompt = `
Create the following directory structure and files for a new chess coaching student:

1. Create directory: ${workspace.basePath}
2. Create directory: ${workspace.gamesPath}
3. Create directory: ${workspace.gamesPath}/analysis
4. Create directory: ${workspace.lessonsPath}
5. Create directory: ${workspace.progressPath}
6. Create directory: ${workspace.memoryPath}
7. Create directory: ${workspace.chatsPath}
8. Create directory: ${workspace.activityPath}

9. Create file ${workspace.profilePath} with content:
\`\`\`markdown
${profileContent}
\`\`\`

10. Create file ${workspace.progressPath}/themes.json with content:
\`\`\`json
{
  "themes": {},
  "lastUpdated": "${new Date().toISOString()}",
  "weeklyProgress": []
}
\`\`\`

11. Create file ${workspace.activityPath}/summary.json with content:
\`\`\`json
{
  "totalSessions": 0,
  "lastActive": "${new Date().toISOString()}",
  "joinedAt": "${new Date().toISOString()}",
  "highlights": []
}
\`\`\`

12. Create file ${workspace.progressPath}/puzzles.json with content:
\`\`\`json
{
  "totalSolved": 0,
  "totalAttempted": 0,
  "currentRating": 1200,
  "peakRating": 1200,
  "lastUpdated": "${new Date().toISOString()}"
}
\`\`\`

Confirm when complete.
`.trim();

  return callGateway(userId, {
    action: 'update-profile',
    payload: { message: initPrompt }
  });
}

export async function checkWorkspaceExists(userId: string): Promise<boolean> {
  const workspace = getUserWorkspace(userId);
  
  // Use Clawdbot to check if profile exists
  const checkPrompt = `
Check if the file ${workspace.profilePath} exists.
Reply with exactly "EXISTS" if it does, or "NOT_FOUND" if it doesn't.
`.trim();

  const response = await callGateway(userId, {
    action: 'chat',
    payload: { message: checkPrompt },
    timeout: 5000
  });

  return response.success && (response.content?.includes('EXISTS') ?? false);
}
