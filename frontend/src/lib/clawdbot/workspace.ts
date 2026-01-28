// frontend/src/lib/clawdbot/workspace.ts
import type { UserWorkspace } from './types';

const USERS_BASE_PATH = '/root/clawd/users';

export function getUserWorkspace(userId: string): UserWorkspace {
  const basePath = `${USERS_BASE_PATH}/${userId}`;
  return {
    userId,
    basePath,
    profilePath: `${basePath}/PLAYER.md`,
    gamesPath: `${basePath}/games`,
    lessonsPath: `${basePath}/lessons`,
    progressPath: `${basePath}/progress`,
    memoryPath: `${basePath}/memory`,
    chatsPath: `${basePath}/chats`,
    activityPath: `${basePath}/activity`
  };
}

export function getSessionKey(userId: string): string {
  return `agent:chess:user:${userId}`;
}

export function generatePlayerProfileTemplate(displayName: string, userId: string): string {
  return `# Player Profile

## Player Information
- **Name:** ${displayName}
- **Clerk ID:** ${userId}
- **Joined:** ${new Date().toISOString().split('T')[0]}
- **Preferred Style:** Not yet determined

## Ratings
- **Puzzles:** Starting
- **Games vs AI:** Not played

## Strengths (identified from analysis)
- To be determined through play

## Weaknesses (to work on)
- To be determined through play

## Current Goals
1. Complete onboarding
2. Establish baseline skill level
3. Set learning objectives

## Coaching Notes
- New player - gather preferences through interaction
`;
}
