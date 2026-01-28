// frontend/src/lib/clawdbot/types.ts
export interface UserWorkspace {
  userId: string;
  basePath: string;
  profilePath: string;
  gamesPath: string;
  lessonsPath: string;
  progressPath: string;
  memoryPath: string;
  chatsPath: string;
  activityPath: string;
}

export interface CoachingSession {
  sessionKey: string;
  userId: string;
  createdAt: Date;
  lastActiveAt: Date;
}

export interface CoachingRequest {
  action: CoachingAction;
  payload: Record<string, unknown>;
  timeout?: number;
}

export type CoachingAction = 
  | 'chat'
  | 'review-game'
  | 'generate-lesson'
  | 'get-progress'
  | 'update-profile'
  | 'log-chat'
  | 'log-activity'
  | 'get-memory';

export type ActivityEventType = 
  | 'puzzle_attempt'
  | 'lesson_progress'
  | 'game_session'
  | 'position_analysis'
  | 'chat_message';

export interface ActivityEvent {
  type: ActivityEventType;
  userId: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface CoachingResponse {
  success: boolean;
  content?: string;
  error?: string;
  sessionKey?: string;
}
