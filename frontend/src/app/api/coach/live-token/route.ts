import { auth } from '@clerk/nextjs/server';
import { GoogleGenAI, Modality } from '@google/genai';

// Region pin is load-bearing: Gemini mint calls are geo-blocked outside iad1.
export const runtime = 'nodejs';
export const preferredRegion = 'iad1';

const LIVE_MODEL = 'gemini-3.1-flash-live-preview';

const COACH_VOICE_PROMPT = `You are a warm, encouraging chess coach speaking out loud with the player.
This is a live voice conversation, so keep your sentences short, natural, and conversational — no markdown,
no bullet points, no long monologues. Talk the way a friendly coach sitting beside the board would.
Guide the player through the current position: ask what they are thinking, react to their ideas, and nudge
them toward good plans without just handing over the answer. Praise sound reasoning and gently redirect
mistakes. You can refer to squares, pieces, threats, and simple plans out loud. Keep the mood light and
supportive, and let the player do most of the thinking. When you are unsure what they see, ask a short
question rather than lecturing.`;

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

  const now = Date.now();
  const expireTime = new Date(now + 30 * 60 * 1000).toISOString();
  const newSessionExpireTime = new Date(now + 60 * 1000).toISOString();

  try {
    const ai = new GoogleGenAI({
      apiKey,
      httpOptions: { apiVersion: 'v1alpha' },
    });

    const token = await ai.authTokens.create({
      config: {
        uses: 1,
        expireTime,
        newSessionExpireTime,
        liveConnectConstraints: {
          model: LIVE_MODEL,
          config: {
            responseModalities: [Modality.AUDIO],
            systemInstruction,
          },
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
