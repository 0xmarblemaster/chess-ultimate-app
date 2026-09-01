'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import CoachChat, { type CoachChatHandle } from '@/components/coach/CoachChat';
import type { ReviewMove } from './types';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const MOBILE_MAX = 768;

const LOCALE_NAMES: Record<string, string> = {
  en: 'English',
  ru: 'Russian',
  kz: 'Kazakh',
};

/** "12." for a white ply, "12…" for a black ply. */
function moveNumberLabel(ply: number): string {
  const n = Math.floor((ply - 1) / 2) + 1;
  return ply % 2 === 1 ? `${n}.` : `${n}…`;
}

export interface CoachDrawerProps {
  open: boolean;
  onClose: () => void;
  /** Keys the per-game chat thread so scrollback survives a re-open. */
  gameId: string;
  /** The ply currently on the board — scopes every question. */
  move: ReviewMove | null;
}

/**
 * F5 — Coach Drawer (Option C). An on-demand slide-over that wraps the existing
 * threaded {@link CoachChat} (text + voice + TTS) so the player can ask the
 * coach about the exact position under review. Costs zero layout space at rest
 * (fixed overlay); desktop slides over the right sidebar, mobile is a
 * drag-to-expand bottom sheet. The default Review analysis stays mounted and
 * visible underneath — this never touches it.
 */
export default function CoachDrawer({ open, onClose, gameId, move }: CoachDrawerProps) {
  const t = useTranslations('gameReview');
  const locale = useLocale();
  const chatRef = useRef<CoachChatHandle>(null);

  // Responsive mode: desktop slide-over vs mobile bottom sheet.
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.innerWidth <= MOBILE_MAX,
  );
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= MOBILE_MAX);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Lazy-mount CoachChat on first open, then keep it mounted so the scrollback
  // (and voice session) persist across toggles within the review session.
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    if (open) setMounted(true);
  }, [open]);

  // Per-game thread: reuse the Hermes session across re-opens of the same game.
  const sessionKey = `review-coach-sess:${gameId}`;
  const [sessionId, setSessionId] = useState<string | null>(null);
  useEffect(() => {
    try {
      setSessionId(localStorage.getItem(sessionKey));
    } catch {
      /* private mode — start fresh */
    }
  }, [sessionKey]);
  const handleSessionCreated = useCallback(
    (id: string) => {
      setSessionId(id);
      try {
        localStorage.setItem(sessionKey, id);
      } catch {
        /* ignore */
      }
    },
    [sessionKey],
  );

  // Mobile bottom-sheet height (vh), adjustable via the drag handle.
  const [sheetVh, setSheetVh] = useState(62);
  const dragRef = useRef<{ startY: number; startVh: number } | null>(null);
  const onDragStart = useCallback(
    (clientY: number) => {
      dragRef.current = { startY: clientY, startVh: sheetVh };
    },
    [sheetVh],
  );
  const onDragMove = useCallback(
    (clientY: number) => {
      const d = dragRef.current;
      if (!d) return;
      const deltaVh = ((d.startY - clientY) / window.innerHeight) * 100;
      setSheetVh(Math.min(92, Math.max(30, d.startVh + deltaVh)));
    },
    [],
  );
  const onDragEnd = useCallback(() => {
    const d = dragRef.current;
    dragRef.current = null;
    // Flicked down past the collapse threshold → close.
    if (d && sheetVh <= 34) onClose();
  }, [sheetVh, onClose]);

  // Move-context chip: the position every question is scoped to.
  const moveLabel = move ? `${moveNumberLabel(move.ply)} ${move.san}` : '';
  const classificationLabel = move ? t(`classifications.${move.classification}`) : '';
  const contextChip = move
    ? t('coach.drawer.contextChip', { move: moveLabel, classification: classificationLabel })
    : '';

  // Grounding preamble prepended to every outgoing question (invisible in the
  // bubble). Uses Review's own 11-tier label and asks the coach to answer in the
  // active locale — matching the F1/F3 grounding + i18n rules.
  const localeName = LOCALE_NAMES[locale] ?? locale;
  const contextNote = move
    ? `[Review context] The player is reviewing ${moveNumberLabel(move.ply)} ${move.san} (${move.uci}), ` +
      `which Review's engine classified as "${move.classification}". Answer specifically about this exact ` +
      `position (FEN provided), grounded in the engine's evaluation — do not invent a different best move. ` +
      `Reply in ${localeName}.`
    : undefined;

  const starters = [
    t('coach.drawer.starterBlunder'),
    t('coach.drawer.starterBetter'),
    t('coach.drawer.starterPlan'),
  ];

  const currentFen = move?.fen ?? START_FEN;

  const panelStyle: React.CSSProperties = isMobile
    ? {
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        height: `${sheetVh}vh`,
        transform: open ? 'translateY(0)' : 'translateY(100%)',
        borderTopLeftRadius: 18,
        borderTopRightRadius: 18,
      }
    : {
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: 430,
        maxWidth: '100%',
        transform: open ? 'translateX(0)' : 'translateX(100%)',
      };

  return (
    <>
      {/* Backdrop — mobile only, so the desktop board/evals stay interactive. */}
      {isMobile && (
        <div
          data-testid="coach-drawer-backdrop"
          onClick={onClose}
          aria-hidden
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            opacity: open ? 1 : 0,
            pointerEvents: open ? 'auto' : 'none',
            transition: 'opacity 220ms ease',
            zIndex: 60,
          }}
        />
      )}

      <div
        data-testid="coach-drawer"
        data-open={open ? 'true' : 'false'}
        data-mode={isMobile ? 'mobile' : 'desktop'}
        role="dialog"
        aria-modal={isMobile ? 'true' : undefined}
        aria-hidden={open ? undefined : 'true'}
        style={{
          ...panelStyle,
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--review-card-solid, #1a1a1a)',
          borderLeft: isMobile ? undefined : '1px solid var(--review-card-border, rgba(148,163,184,0.12))',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          transition: 'transform 260ms cubic-bezier(0.22, 1, 0.36, 1)',
          pointerEvents: open ? 'auto' : 'none',
          zIndex: 61,
        }}
      >
        {/* Drag handle — mobile only (drag-to-expand / flick-down to close). */}
        {isMobile && (
          <div
            data-testid="coach-drawer-handle"
            onPointerDown={(e) => onDragStart(e.clientY)}
            onPointerMove={(e) => dragRef.current && onDragMove(e.clientY)}
            onPointerUp={onDragEnd}
            onTouchStart={(e) => onDragStart(e.touches[0].clientY)}
            onTouchMove={(e) => onDragMove(e.touches[0].clientY)}
            onTouchEnd={onDragEnd}
            style={{ padding: '10px 0 6px', display: 'flex', justifyContent: 'center', cursor: 'grab', touchAction: 'none' }}
          >
            <span style={{ width: 40, height: 4, borderRadius: 999, background: 'var(--review-text-dim, #64748b)' }} />
          </div>
        )}

        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
            padding: '12px 14px',
            borderBottom: '1px solid var(--review-card-border, rgba(148,163,184,0.12))',
          }}
        >
          <span className="review-heading" style={{ fontWeight: 800, fontSize: 15, color: '#14b8a6' }}>
            ♞ {t('coach.drawer.title')}
          </span>
          <button
            type="button"
            data-testid="coach-drawer-close"
            onClick={onClose}
            aria-label={t('coach.drawer.close')}
            className="review-ghost-btn"
            style={{ padding: '6px 12px', fontSize: 13 }}
          >
            ✕
          </button>
        </div>

        {/* Move-context chip — scopes every question to the ply on the board. */}
        {contextChip && (
          <div style={{ padding: '10px 14px 4px' }}>
            <span
              data-testid="coach-drawer-context-chip"
              style={{
                display: 'inline-block',
                padding: '4px 10px',
                borderRadius: 999,
                fontSize: 12.5,
                fontWeight: 700,
                color: '#14b8a6',
                background: 'rgba(20, 184, 166, 0.12)',
                border: '1px solid rgba(20, 184, 166, 0.35)',
              }}
            >
              {contextChip}
            </span>
          </div>
        )}

        {/* Beginner starter chips — one-tap prompts scoped to the current move. */}
        <div
          data-testid="coach-drawer-starters"
          style={{ display: 'flex', flexWrap: 'wrap', gap: 6, padding: '6px 14px 10px' }}
        >
          {starters.map((prompt) => (
            <button
              key={prompt}
              type="button"
              data-testid="coach-drawer-starter"
              onClick={() => chatRef.current?.send(prompt)}
              style={{
                padding: '5px 10px',
                borderRadius: 999,
                fontSize: 12.5,
                fontWeight: 600,
                color: 'var(--review-text, #e2e8f0)',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                cursor: 'pointer',
              }}
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Threaded chat (text + voice + TTS) — reused wholesale from /coach. */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          {mounted && (
            <CoachChat
              ref={chatRef}
              currentFen={currentFen}
              sessionId={sessionId}
              contextNote={contextNote}
              onSessionCreated={handleSessionCreated}
              onBoardActions={() => {
                /* Review board is read-only here; coach explains, not drives. */
              }}
            />
          )}
        </div>
      </div>
    </>
  );
}
