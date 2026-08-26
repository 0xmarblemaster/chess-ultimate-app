import { auth } from '@clerk/nextjs/server';
import { GoogleGenAI, Modality } from '@google/genai';

// Region pin is load-bearing: Gemini mint calls are geo-blocked outside iad1.
export const runtime = 'nodejs';
export const preferredRegion = 'iad1';

const LIVE_MODEL = 'gemini-3.1-flash-live-preview';

const HERMES_URL = process.env.HERMES_URL || 'http://localhost:8642';

// Voice persona, aligned with the Hermes text coach (profiles/chess-coach/SOUL.md):
// the same Chesster coach — Socratic, ask-before-telling, direct and encouraging —
// expressed for a spoken, real-time conversation.
const COACH_VOICE_PROMPT = `You are Chesster's chess coach, the same coach the player types with — now speaking out loud.
You combine engine-level precision with the teaching instincts of great coaches. Ask before telling: understand
what the player is thinking before handing over answers, and lead them to discover ideas through short questions.
Because this is a live voice conversation, keep your sentences short, natural, and conversational — no markdown,
no bullet points, no long monologues. Talk the way a coach sitting beside the board would. Guide the player through
the current position, react to their ideas, and nudge them toward good plans without just handing over the move.
Be direct and encouraging — believe in them, but don't let them off easy. Praise sound reasoning and gently redirect
mistakes. You can refer to squares, pieces, threats, and simple plans out loud. Never break character or say things
like "as a chess AI". When you are unsure what they see, ask a short question rather than lecturing.`;

// Appended when tools are available, so the voice coach uses them instead of guessing.
const COACH_TOOL_GUIDANCE = `

You have tools. Use board_control to demonstrate ideas directly on the board — set positions, draw arrows,
highlight squares, or step through moves as you explain. Use the engine and database tools (analyze the position,
search master games, opening and position stats, the player's own games and progress) instead of guessing or
inventing lines. Call a tool when it makes your point concrete; keep talking naturally while you do.`;

/**
 * Fetch the chess tools' Gemini functionDeclarations from Hermes. Returns [] on
 * any failure — the voice session must never break because tools are down.
 */
async function fetchToolDeclarations(): Promise<unknown[]> {
  try {
    const res = await fetch(`${HERMES_URL}/api/coach/tools`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      console.warn('[live-token] tools fetch returned', res.status);
      return [];
    }
    const data = await res.json();
    const tools = Array.isArray(data?.tools) ? data.tools : [];
    return tools;
  } catch (err) {
    console.warn('[live-token] failed to fetch tool declarations:', err);
    return [];
  }
}

/**
 * Build a conversation recap block from prior session messages so the voice
 * coach continues seamlessly across modalities. Returns '' if there's nothing.
 */
function buildRecap(
  messages: Array<{ role?: string; content?: string; source?: string }>,
): string {
  const lines = messages
    .filter((m) => m && typeof m.content === 'string' && m.content.trim())
    .map((m) => {
      const label = m.role === 'user' ? 'user' : 'coach';
      const tag = m.source === 'voice' ? ' (spoken)' : '';
      return `[${label}${tag}] ${m.content}`;
    });
  if (lines.length === 0) return '';
  return (
    '\n\nYou are continuing an ongoing coaching conversation. ' +
    'Recent conversation (oldest first):\n' +
    lines.join('\n') +
    '\nContinue seamlessly — do not re-introduce yourself or repeat prior explanations.'
  );
}

const jsonResponse = (body: unknown, status: number) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

/**
 * POST /api/coach/live-token — mint a short-lived Gemini Live ephemeral token.
 * The model + Live config are locked into the token constraint server-side so the
 * browser never holds the raw API key and cannot change what it connects to.
 */
export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return jsonResponse({ error: 'Live coach not configured' }, 500);
  }

  // No required inputs — tolerate a missing or malformed body.
  let body: { fen?: string; session_id?: string; locale?: string } = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  let systemInstruction = COACH_VOICE_PROMPT;
  if (body.fen && typeof body.fen === 'string') {
    systemInstruction += `\nThe current board position (FEN) is: ${body.fen}. Refer to it when relevant.`;
  }

  // Inject shared conversation memory: pull recent messages from Hermes so the
  // voice coach remembers what was said via text (and prior voice). A Hermes
  // failure must never break voice — log and fall back to no recap.
  if (body.session_id && typeof body.session_id === 'string') {
    try {
      const recapRes = await fetch(
        `${HERMES_URL}/api/coach/sessions/${encodeURIComponent(body.session_id)}/messages?limit=20`,
        {
          headers: { 'X-User-Id': userId },
          signal: AbortSignal.timeout(5000),
        },
      );
      if (recapRes.ok) {
        const data = await recapRes.json();
        const messages = Array.isArray(data?.messages) ? data.messages : [];
        systemInstruction += buildRecap(messages);
      } else {
        console.error(
          '[live-token] recap fetch returned',
          recapRes.status,
        );
      }
    } catch (err) {
      console.error('[live-token] failed to fetch conversation recap:', err);
    }
  }

  // Pull tool declarations from Hermes (server-side). Degrade gracefully: if
  // Hermes is down the session still mints, just without tools.
  const functionDeclarations = await fetchToolDeclarations();
  if (functionDeclarations.length > 0) {
    systemInstruction += COACH_TOOL_GUIDANCE;
  }

  const now = Date.now();
  const expireTime = new Date(now + 30 * 60 * 1000).toISOString();
  const newSessionExpireTime = new Date(now + 60 * 1000).toISOString();

  try {
    const ai = new GoogleGenAI({
      apiKey,
      httpOptions: { apiVersion: 'v1alpha' },
    });

    const liveConfig: Record<string, unknown> = {
      responseModalities: [Modality.AUDIO],
      systemInstruction,
    };
    if (functionDeclarations.length > 0) {
      liveConfig.tools = [{ functionDeclarations }];
    }

    const token = await ai.authTokens.create({
      config: {
        uses: 1,
        expireTime,
        newSessionExpireTime,
        liveConnectConstraints: {
          model: LIVE_MODEL,
          config: liveConfig,
        },
        httpOptions: { apiVersion: 'v1alpha' },
      },
    });

    return jsonResponse(
      { token: token.name, model: LIVE_MODEL, expiresAt: expireTime },
      200,
    );
  } catch (err) {
    console.error('[live-token] failed to mint ephemeral token:', err);
    return jsonResponse({ error: 'Failed to start live session' }, 502);
  }
}
