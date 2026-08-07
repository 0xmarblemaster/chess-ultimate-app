import { Fragment } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import s from "./landing.module.css";

// Design test page (Linear DNA study) — not linked from anywhere, noindex.
export const metadata: Metadata = {
  title: "Chesster — the training system for serious chess",
  robots: { index: false, follow: false },
};

// Italian Game after 6...a6 — r1bqk2r/1pp2ppp/p1np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1
const FEN_ROWS = [
  "r.bqk..r",
  ".pp..ppp",
  "p.np.n..",
  "..b.p...",
  "..B.P...",
  "..PP.N..",
  "PP...PPP",
  "RNBQ.RK.",
];

const GLYPH: Record<string, string> = {
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟",
};

const MOVES: [string, string, string][] = [
  ["1.", "e4", "e5"],
  ["2.", "Nf3", "Nc6"],
  ["3.", "Bc4", "Bc5"],
  ["4.", "c3", "Nf6"],
  ["5.", "d3", "d6"],
  ["6.", "O-O", "a6"],
];

function Board() {
  return (
    <div className={s.board} role="img" aria-label="Chessboard, Italian Game after six moves">
      {FEN_ROWS.flatMap((row, r) =>
        row.split("").map((ch, c) => {
          const dark = (r + c) % 2 === 1;
          const isWhite = ch !== "." && ch === ch.toUpperCase();
          return (
            <div key={`${r}-${c}`} className={`${s.sq} ${dark ? s.sqD : s.sqL}`}>
              {ch !== "." && (
                <span className={isWhite ? s.pw : s.pb}>
                  {GLYPH[ch.toLowerCase()]}
                </span>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}

export default function LandingTest() {
  return (
    <div className={s.page}>
      <nav className={s.nav}>
        <Link href="/landing-test" className={s.wordmark}>
          <span className={s.knight}>♞</span> Chesster
        </Link>
        <div className={s.navRight}>
          <Link href="/sign-in" className={s.navLink}>
            Sign in
          </Link>
          <Link href="/sign-up" className={s.pill}>
            Get started
          </Link>
        </div>
      </nav>

      <header className={s.hero}>
        <h1 className={s.h1}>The training system for serious chess.</h1>
        <p className={s.heroSub}>
          Courses, puzzles, and engine analysis in one place — built on a
          database of 4.35 million master games.
        </p>
        <div className={s.heroCtas}>
          <Link href="/sign-up" className={`${s.pill} ${s.pillLg}`}>
            Start training
          </Link>
          <Link href="/database" className={s.ghost}>
            Open the database →
          </Link>
        </div>
      </header>

      <div className={s.mockWrap}>
        <div className={s.mock}>
          <div className={`${s.mockPane} ${s.movesPane}`}>
            <p className={s.mockPaneTitle}>MOVES</p>
            <div className={s.moves}>
              {MOVES.map(([n, w, b], i) => (
                <Fragment key={n}>
                  <span className={s.moveNum}>{n}</span>
                  <span>{w}</span>
                  <span className={i === MOVES.length - 1 ? s.moveCur : undefined}>
                    {b}
                  </span>
                </Fragment>
              ))}
            </div>
          </div>
          <div className={s.boardPane}>
            <Board />
          </div>
          <div className={`${s.mockPane} ${s.analysisPane}`}>
            <p className={s.mockPaneTitle}>ANALYSIS</p>
            <div className={s.evalRow}>
              <span className={s.evalNum}>+0.28</span>
              <span className={s.evalMeta}>Stockfish 17 · depth 24</span>
            </div>
            <div className={s.lineRow}>7.Re1 Ba7 8.Bb3 O-O</div>
            <div className={s.lineRow}>7.Bb3 O-O 8.Nbd2 Ba7</div>
            <div className={s.lineRow}>7.h3 O-O 8.Re1 h6</div>
          </div>
        </div>
      </div>

      <div className={s.sections}>
        <section className={`${s.band} ${s.bandRaised}`}>
          <div className={s.bandInner}>
            <h2 className={s.h2}>Study lines, not lists.</h2>
            <p className={s.bandBody}>
              Everything is connected to real positions: open a course chapter,
              drill the tactic, check the engine — without leaving the board.
            </p>
            <div className={s.featGrid}>
              <div className={s.featCard}>
                <h3 className={s.featName}>Courses</h3>
                <p className={s.featDesc}>
                  Structured openings, middlegame plans, and endgame technique
                  — one path per level.
                </p>
              </div>
              <div className={s.featCard}>
                <h3 className={s.featName}>Puzzles</h3>
                <p className={s.featDesc}>
                  Tactics pulled from real games, matched to your current
                  rating.
                </p>
              </div>
              <div className={s.featCard}>
                <h3 className={s.featName}>Analysis</h3>
                <p className={s.featDesc}>
                  Stockfish evaluation on every move, running right in the
                  browser.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className={s.band}>
          <div className={s.bandInner}>
            <h2 className={s.h2}>Every master game since 1994.</h2>
            <p className={s.bandBody}>
              The full tournament record, indexed position by position. Search
              any line and see how masters actually played it.
            </p>
            <div className={s.statRow}>
              <div className={s.stat}>
                <div className={s.statNum}>4.35M</div>
                <div className={s.statLabel}>games</div>
              </div>
              <div className={s.stat}>
                <div className={s.statNum}>285M</div>
                <div className={s.statLabel}>indexed positions</div>
              </div>
              <div className={s.stat}>
                <div className={s.statNum}>116K</div>
                <div className={s.statLabel}>players</div>
              </div>
            </div>
          </div>
        </section>

        <section className={`${s.band} ${s.bandRaised}`}>
          <div className={s.bandInner}>
            <h2 className={s.h2}>Sparring partners at every level.</h2>
            <p className={s.bandBody}>
              Play opponents that feel human — or ones that definitely
              don&apos;t.
            </p>
            <div className={s.featGrid}>
              <div className={s.featCard}>
                <h3 className={s.featName}>Maia</h3>
                <p className={s.featDesc}>
                  A neural network trained to play like a human at your rating
                  — blunders included.
                </p>
              </div>
              <div className={s.featCard}>
                <h3 className={s.featName}>Stockfish</h3>
                <p className={s.featDesc}>
                  The strongest engine in the world, when you want to be
                  punished precisely.
                </p>
              </div>
              <div className={s.featCard}>
                <h3 className={s.featName}>Tournaments</h3>
                <p className={s.featDesc}>
                  Organized play with standings, rounds, and a leaderboard for
                  your club.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <section className={s.finalCta}>
        <h2 className={s.h2}>Ready when you are.</h2>
        <div className={s.finalCtas}>
          <Link href="/sign-up" className={`${s.pill} ${s.pillLg}`}>
            Start training
          </Link>
        </div>
      </section>

      <footer className={s.footer}>
        <span>♞ Chesster</span>
        <div className={s.footerLinks}>
          <Link href="/sign-in">Sign in</Link>
          <Link href="/for-schools">For schools</Link>
        </div>
        <span>© 2026 Chesster</span>
      </footer>
    </div>
  );
}
