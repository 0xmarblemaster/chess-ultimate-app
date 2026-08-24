# Game Review — Phase 3 Report

**Scope:** Frontend design system + Highlights UI + entry points. Backend
untouched (frozen contract). Base = proto2 Chesster Light, dark = proto3
Midnight Glass — one component tree, two themes via CSS vars.

## What was built

### 1. Design tokens (`src/app/globals.css`)
- `--color-classification-*` — 10 frozen, theme-invariant hex + a neutral
  `forced`. Exactly the palette from the teardown (brilliant `#26C2A3` …
  blunder `#FA412D`).
- `--review-*` themable set scoped to `.review-root`, overridden by
  `.review-root[data-theme="dark"]`. Covers fonts (Inter / Space Grotesk),
  page bg (radial gradient in dark), cards/glass, accent + CTA gradients,
  tints, board light/dark squares, eval-bar track/fill, graph line, glow.
- Component classes: `.review-card`, `.review-cta`, `.review-ghost-btn`,
  `.review-heading`, plus a chessground `cg-board` conic-gradient recolour so
  the board uses the themed square colours.
- Fonts loaded the Next-idiomatic way in `src/app/review/layout.tsx`
  (`next/font/google` Inter + Space_Grotesk → CSS variables).

### 2. `ClassificationIcon` (`src/components/review/ClassificationIcon.tsx`)
Single SVG keyed by type, `viewBox="0 0 18 19"`, exact 4-layer anatomy
(shadow disc → colored disc → glyph shadow → white glyph). Six glyph shapes
(brilliant `!!`, great `!`, best star, excellent thumb, book, blunder `??`)
are the exact paths extracted from the prototypes; the four that appear in no
reference (good check, inaccuracy `?!`, mistake `?`, miss ✗) are hand-authored
clean white glyphs with the same disc anatomy. Sizes: `size={18}` (move list,
Phase 4), `size={24}` (tally), no size = 100% of parent (board, Phase 4).

### 3. Route `/review/[id]` (`src/app/review/[id]/page.tsx`)
- Polls `GET /api/review/[id]` every 1.5s; shows themed `ReviewProgress`
  (0–1 bar) while `status !== done`; error panel on failure.
- `EvalBar` — stacked track + white fill positioned by
  `translate3d(0, 100−whiteWin%, 0)` with `transition: transform .5s ease`;
  score label flips side by who leads.
- `ReviewBoard` — reuses the app's `ChessgroundBoard` (`viewOnly`), themed
  squares, board shadow. Renders the final position by default (ply = last),
  or ply 0. (On-board badges/tints/stepper are Phase 4.)
- `EvalGraph` — hand-rolled SVG area chart, per-ply eval clamped ±6,
  classification-coloured key-moment dots with halo, hover crosshair,
  click-to-jump (sets current ply), current-ply marker.
- `ReviewSidebar` (Highlights mode): CoachIntro, two AccuracyCards (arc sweeps
  0→value on mount ~1s), players+accuracy row, TallyTable (24px icons, counts
  coloured by classification), GameRating (estRating), PhaseStats, and the
  Start Review CTA. The CTA flips the store to `mode:"review"` and renders a
  placeholder panel (full stepper = Phase 4).
- State: one reducer store (`reviewStore.ts`) — `{reviewId, data, currentPly,
  mode}` (Zustand isn't a dep). Keyboard ←/→ steps plies. Theme toggle button
  wired to the app's `useDarkMode()` so light/dark can be eyeballed live.

### 4. Entry points — shared `StartReviewButton`
`<StartReviewButton game={{pgn, isFinished?, orientation?}} source=... />`.
Gating in one place: `canReview(game, source)` — database always true,
bot/online only when finished; disabled + tooltip "Finish the game to unlock
Review". POSTs the PGN to `/api/review`, routes to
`/review/[id]?source=&orientation=`. Self-contained inline styling (renders
outside `.review-root`).

Wired into all three surfaces:
- **Bot** — `GameEndModal` gained an optional `reviewPgn`; `src/app/play/page.tsx`
  passes `chess.pgn()` (the modal only shows once the game is over → finished).
- **Online** — `LiveGameEndModal` gained `reviewPgn`;
  `src/app/play/live/[gameId]/page.tsx` rebuilds a PGN from the live UCI move
  list (`buildReviewPgn`) and passes it on the game-over screen.
- **Database** — `src/app/database/page.tsx` renders a "Review this game"
  button below the board using the active game's `.pgn` (always reviewable).

API proxies (`BACKEND_URL`, server-only, following the app's existing pattern):
`src/app/api/review/route.ts` (POST) and `src/app/api/review/[id]/route.ts` (GET).

i18n: `gameReview` label added to the `gameEnd` namespace in en/ru/kz.

## Surfaces note
All three surfaces exist. There is also a **separate, pre-existing** review
system (`src/hooks/useGameReview.ts`, `src/app/game/page.tsx`) — left untouched;
this phase builds the new Flask-pipeline `/review/[id]` route per the brief.

## Tests (`src/components/review/__tests__/`, Vitest + RTL)
- `ClassificationIcon` — all 11 types render, correct disc fill, viewBox, sizes.
- `EvalBar` — `whiteFillOffset` math + `evalLabel` + rendered transform.
- `EvalGraph` — clamping, series length, one halo dot per key moment coloured
  by classification, current-ply marker.
- `TallyTable` — counts + colours from fixture, forced hidden when zero.
- `StartReviewButton` — `canReview` gating (bot/online finished vs in-progress,
  database always), disabled+tooltip, POST→route, error via `onError`.

25 review tests pass; 90 pass across review + existing play modal suites.
`npx tsc --noEmit` clean for all new files (2 remaining errors are pre-existing
in unrelated test files). `npx eslint` clean (0 errors). `next build` compiles
successfully with `/review/[id]`, `/api/review`, `/api/review/[id]` in the tree.

## How to eyeball light vs dark against the prototype PNGs
1. Start backend (Stockfish) + `npm run dev`; open a finished bot game and click
   **Game Review**, or from the database viewer click **Review this game**.
2. On `/review/[id]`, use the header **☀/☾ toggle** (or the global theme switch)
   to flip themes.
3. Compare side-by-side:
   - Light → `/root/clawd/prototypes/game-review/proto2-chesster.png`
     (teal accent `#0d9488`, Inter, `#FAFAFA` page, `#F0F4FF`/`#B3C2E0` board).
   - Dark → `/root/clawd/prototypes/game-review/proto3-midnight.png`
     (indigo `#818CF8`, Space Grotesk headings, radial-gradient page,
     glass panels, `#3D4763`/`#252E47` board, `#151B2E` eval track).
   Classification badge colours must read identically in both themes.
