'use client';

import { Suspense, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { useDarkMode } from '@/hooks/useDarkMode';
import {
  ReviewBoard,
  ReviewProgress,
  ReviewSidebar,
  EvalBar,
  EvalGraph,
  useReviewStore,
  fetchReview,
} from '@/components/review';
import type { EngineEval } from '@/components/review';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const POLL_MS = 1500;

function uciToLastMove(uci?: string): [string, string] | null {
  if (!uci || uci.length < 4) return null;
  return [uci.slice(0, 2), uci.slice(2, 4)];
}

export default function ReviewPage() {
  // useSearchParams requires a Suspense boundary during prerender.
  return (
    <Suspense fallback={null}>
      <ReviewPageInner />
    </Suspense>
  );
}

function ReviewPageInner() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const id = params?.id ?? '';
  const orientation = (search?.get('orientation') as 'white' | 'black') || 'white';

  const { isDark, toggle } = useDarkMode();
  const { state, dispatch } = useReviewStore(id);
  const { data, currentPly, mode } = state;

  // Poll the backend until the analysis is done (or errors).
  const done = data != null;
  const [progress, setProgressVal] = useState(0);
  const [status, setStatus] = useState<'queued' | 'running' | 'done' | 'error'>('queued');

  useEffect(() => {
    if (!id || done) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const job = await fetchReview(id);
        if (cancelled) return;
        setStatus(job.status);
        setProgressVal(job.progress ?? 0);
        if (job.status === 'done' && job.result) {
          dispatch({ type: 'setData', data: job.result });
          dispatch({ type: 'setPly', ply: job.result.moves.length });
          return;
        }
        if (job.status === 'error') return;
        timer = setTimeout(poll, POLL_MS);
      } catch {
        if (!cancelled) timer = setTimeout(poll, POLL_MS);
      }
    };
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, done, dispatch, setProgressVal, setStatus]);

  // Keyboard navigation ←/→ once loaded.
  useEffect(() => {
    if (!data) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') dispatch({ type: 'stepPly', delta: -1 });
      if (e.key === 'ArrowRight') dispatch({ type: 'stepPly', delta: 1 });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [data, dispatch]);

  const themeAttr = isDark ? 'dark' : 'light';

  const currentMove = data && currentPly >= 1 ? data.moves[currentPly - 1] : null;
  const fen = currentMove?.fen ?? START_FEN;
  const whiteWin = currentMove?.winPercent ?? 50;
  const evaluation: EngineEval = currentMove?.eval ?? { type: 'cp', value: 0 };

  return (
    <div className="review-root" data-theme={themeAttr}>
      <header
        className="top"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '14px 32px',
        }}
      >
        <div
          className="review-heading"
          style={{ fontSize: 19, fontWeight: 800, color: 'var(--review-accent)' }}
        >
          ♞ Chesster{' '}
          <span style={{ color: 'var(--review-text-dim)', fontWeight: 600 }}>· Game Review</span>
        </div>
        <button
          type="button"
          onClick={toggle}
          className="review-ghost-btn"
          style={{ padding: '6px 12px', fontSize: 13 }}
          aria-label="Toggle theme"
        >
          {isDark ? '☾ Dark' : '☀ Light'}
        </button>
      </header>

      {!data ? (
        status === 'error' ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <div className="review-heading" style={{ fontSize: 20, fontWeight: 800 }}>
              Review failed
            </div>
            <p style={{ opacity: 0.7, marginTop: 8 }}>
              We couldn&apos;t analyse this game. Please try again.
            </p>
          </div>
        ) : (
          <ReviewProgress progress={progress} status={status === 'running' ? 'running' : 'queued'} />
        )
      ) : (
        <main
          style={{
            display: 'flex',
            gap: 28,
            padding: '20px 32px',
            alignItems: 'flex-start',
            justifyContent: 'center',
            flexWrap: 'wrap',
          }}
        >
          <section style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', gap: 10 }}>
              <EvalBar whiteWinPercent={whiteWin} evaluation={evaluation} />
              <ReviewBoard
                fen={fen}
                orientation={orientation}
                lastMove={uciToLastMove(currentMove?.uci)}
              />
            </div>
          </section>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, width: 430, maxWidth: '100%' }}>
            <ReviewSidebar
              data={data}
              mode={mode}
              white={{ name: 'White', rating: data.estRating.w }}
              black={{ name: 'Black', rating: data.estRating.b }}
              onStartReview={() => dispatch({ type: 'setMode', mode: 'review' })}
            />
            <EvalGraph
              moves={data.moves}
              keyMoments={data.keyMoments}
              currentPly={currentPly}
              onSelectPly={(ply) => dispatch({ type: 'setPly', ply })}
            />
          </div>
        </main>
      )}
    </div>
  );
}
