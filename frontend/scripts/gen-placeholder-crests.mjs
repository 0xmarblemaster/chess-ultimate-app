#!/usr/bin/env node
/**
 * Placeholder legion-crest art generator (PRD-gamification.md §8.1, D-9).
 *
 * Emits a style-guided SVG per seed legion under
 * `frontend/public/gamification/crests/<slug>.svg` — a heraldic shield in the
 * legion's colours with a centred totem glyph, so the /legion and /cup surfaces
 * read as one set until the director's final crests arrive (swapped per-legion
 * via admin `crest_url`, zero schema impact — same pattern as item art).
 *
 * Also prints the matching SQL seed VALUES for the migration to stdout, so the
 * committed art and the seeded legions can never drift.
 *
 *   node scripts/gen-placeholder-crests.mjs        # write SVGs
 *   node scripts/gen-placeholder-crests.mjs --sql  # print SQL seed rows only
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(__dirname, '../public/gamification/crests');

// Totem glyphs — a single centred emblem path each (128 viewBox), on the shield.
const TOTEM = {
  leopard:
    'M64 40 C50 40 42 52 42 66 C42 84 52 94 64 94 C76 94 86 84 86 66 C86 52 78 40 64 40 Z M52 60 A5 5 0 1 0 52 70 A5 5 0 0 0 52 60 Z M76 60 A5 5 0 1 0 76 70 A5 5 0 0 0 76 60 Z M58 78 H70 L64 86 Z',
  eagle:
    'M64 34 L74 50 L96 46 L82 62 L96 78 L74 74 L64 94 L54 74 L32 78 L46 62 L32 46 L54 50 Z',
  bear:
    'M64 42 C50 42 40 54 40 70 C40 86 51 96 64 96 C77 96 88 86 88 70 C88 54 78 42 64 42 Z M46 40 A9 9 0 1 0 46 58 A9 9 0 0 0 46 40 Z M82 40 A9 9 0 1 0 82 58 A9 9 0 0 0 82 40 Z M64 72 A5 5 0 1 0 64 82 A5 5 0 0 0 64 72 Z',
  wolf:
    'M40 40 L52 58 L64 44 L76 58 L88 40 L84 74 C84 90 74 98 64 98 C54 98 44 90 44 74 Z M56 66 A4 4 0 1 0 56 74 A4 4 0 0 0 56 66 Z M72 66 A4 4 0 1 0 72 74 A4 4 0 0 0 72 66 Z',
  fox: 'M40 42 L58 56 H70 L88 42 L84 72 C84 88 74 96 64 96 C54 96 44 88 44 72 Z M56 64 A4 4 0 1 0 56 72 A4 4 0 0 0 56 64 Z M72 64 A4 4 0 1 0 72 72 A4 4 0 0 0 72 64 Z',
  lion:
    'M64 40 C48 40 36 54 36 72 C36 90 48 98 64 98 C80 98 92 90 92 72 C92 54 80 40 64 40 Z M64 40 L58 26 L64 32 L70 26 Z M54 66 A5 5 0 1 0 54 76 A5 5 0 0 0 54 66 Z M74 66 A5 5 0 1 0 74 76 A5 5 0 0 0 74 66 Z',
};

// The seed legions — single source of truth for art + seed rows. ce_branch_id is
// left NULL: the admin maps each legion to a CE branch in the Legions tab (§15).
// name_ru is the school's Russian totem name; slug names the SVG + sku.
const LEGIONS = [
  ['snow-leopards', 'leopard', 'Снежные Барсы', 'Snow Leopards', '#38bdf8', '#0369a1'],
  ['golden-eagles', 'eagle', 'Золотые Орлы', 'Golden Eagles', '#f59e0b', '#b45309'],
  ['iron-bears', 'bear', 'Железные Медведи', 'Iron Bears', '#94a3b8', '#334155'],
  ['grey-wolves', 'wolf', 'Серые Волки', 'Grey Wolves', '#64748b', '#1e293b'],
  ['red-foxes', 'fox', 'Рыжие Лисы', 'Red Foxes', '#fb923c', '#c2410c'],
  ['crimson-lions', 'lion', 'Багровые Львы', 'Crimson Lions', '#ef4444', '#991b1b'],
];

function svg(totem, primary, deep) {
  const glyph = TOTEM[totem];
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="${totem} crest">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${primary}"/>
      <stop offset="1" stop-color="${deep}"/>
    </linearGradient>
  </defs>
  <path d="M64 8 L112 24 V64 C112 96 90 114 64 122 C38 114 16 96 16 64 V24 Z" fill="url(#bg)"/>
  <path d="M64 8 L112 24 V64 C112 96 90 114 64 122 C38 114 16 96 16 64 V24 Z" fill="none" stroke="#ffffff" stroke-opacity="0.4" stroke-width="3"/>
  <path d="${glyph}" fill="#ffffff" fill-opacity="0.92"/>
</svg>
`;
}

function seedRows() {
  return LEGIONS.map((row) => {
    const [slug, totem, ru, en, primary, deep] = row;
    const esc = (s) => s.replace(/'/g, "''");
    return `  ('${esc(ru)}','${esc(totem)}','/gamification/crests/${slug}.svg','${primary}','${deep}')`;
  }).join(',\n');
}

if (process.argv.includes('--sql')) {
  process.stdout.write(seedRows() + '\n');
} else {
  mkdirSync(OUT_DIR, { recursive: true });
  for (const [slug, totem, , , primary, deep] of LEGIONS) {
    writeFileSync(resolve(OUT_DIR, `${slug}.svg`), svg(totem, primary, deep));
  }
  process.stderr.write(`Wrote ${LEGIONS.length} crest SVGs to ${OUT_DIR}\n`);
}
