#!/usr/bin/env node
/**
 * Placeholder cosmetic-item art generator (PRD-gamification.md §7.2, D-9).
 *
 * Emits a style-guided SVG per catalog item under
 * `frontend/public/gamification/items/<sku>.svg` — consistent silhouette per
 * slot, consistent palette/pip per rarity, so the shop reads as one set until
 * the director's final art arrives (swapped per-item via admin `art_url`).
 *
 * Also prints the matching SQL seed VALUES for the migration to stdout, so the
 * committed art and the seeded catalog can never drift.
 *
 *   node scripts/gen-placeholder-items.mjs        # write SVGs
 *   node scripts/gen-placeholder-items.mjs --sql  # print SQL seed rows only
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(__dirname, '../public/gamification/items');

// Rarity palette + shop price (whole numbers, §7.1).
const RARITY = {
  common: { base: '#94a3b8', deep: '#475569', price: 10 },
  rare: { base: '#3b82f6', deep: '#1d4ed8', price: 30 },
  epic: { base: '#a855f7', deep: '#6d28d9', price: 75 },
  legendary: { base: '#f59e0b', deep: '#b45309', price: 150 },
};

// Slot glyphs — a single centered emblem path each (128 viewBox).
const GLYPH = {
  shield: 'M64 20 L104 34 V64 C104 92 86 106 64 116 C42 106 24 92 24 64 V34 Z',
  helmet: 'M32 60 C32 34 52 22 64 22 C76 22 96 34 96 60 V78 H80 V64 H72 V78 H56 V64 H48 V78 H32 Z',
  weapon: 'M60 18 H68 V78 H80 L64 98 L48 78 H60 Z M44 78 H84 V88 H44 Z',
  armor: 'M40 30 L64 40 L88 30 V70 C88 96 64 108 64 108 C64 108 40 96 40 70 Z',
  cloak: 'M64 22 C50 22 44 30 44 30 L24 104 L64 92 L104 104 L84 30 C84 30 78 22 64 22 Z',
  pet: 'M64 46 C48 46 38 60 38 76 C38 94 50 102 64 102 C78 102 90 94 90 76 C90 60 80 46 64 46 Z M44 34 A9 9 0 1 0 44 52 A9 9 0 0 0 44 34 Z M84 34 A9 9 0 1 0 84 52 A9 9 0 0 0 84 34 Z',
  background: 'M22 34 H106 V94 H22 Z M22 78 L46 58 L66 74 L90 50 L106 64 V94 H22 Z M84 46 A8 8 0 1 0 84 62 A8 8 0 0 0 84 46 Z',
  frame: 'M26 26 H102 V102 H26 Z M40 40 V88 H88 V40 Z',
  effect: 'M64 20 L72 50 L102 58 L72 66 L64 96 L56 66 L26 58 L56 50 Z',
};

// The catalog — single source of truth for art + seed. 25 items, 9 slots.
// kind: default (free starter, auto-granted, price NULL) | purchasable.
const CATALOG = [
  ['shield_bronze', 'shield', 'common', 'default', 'Bronze Shield', 'Бронзовый щит', 'Қола қалқан'],
  ['shield_iron', 'shield', 'common', 'purchasable', 'Iron Shield', 'Железный щит', 'Темір қалқан'],
  ['shield_azure', 'shield', 'rare', 'purchasable', 'Azure Shield', 'Лазурный щит', 'Көгілдір қалқан'],
  ['shield_dragon', 'shield', 'epic', 'purchasable', 'Dragon Shield', 'Драконий щит', 'Айдаһар қалқаны'],
  ['helmet_leather', 'helmet', 'common', 'default', 'Leather Cap', 'Кожаный шлем', 'Былғары дулыға'],
  ['helmet_knight', 'helmet', 'rare', 'purchasable', 'Knight Helm', 'Рыцарский шлем', 'Рыцарь дулығасы'],
  ['helmet_royal', 'helmet', 'epic', 'purchasable', 'Royal Helm', 'Королевский шлем', 'Патша дулығасы'],
  ['weapon_dagger', 'weapon', 'common', 'purchasable', 'Dagger', 'Кинжал', 'Қанжар'],
  ['weapon_sword', 'weapon', 'rare', 'purchasable', 'Steel Sword', 'Стальной меч', 'Болат қылыш'],
  ['weapon_flameblade', 'weapon', 'legendary', 'purchasable', 'Flameblade', 'Пламенный клинок', 'Жалынды семсер'],
  ['armor_tunic', 'armor', 'common', 'default', 'Cloth Tunic', 'Холщовая туника', 'Мата көйлек'],
  ['armor_chain', 'armor', 'rare', 'purchasable', 'Chainmail', 'Кольчуга', 'Сауыт'],
  ['armor_plate', 'armor', 'epic', 'purchasable', 'Plate Armor', 'Латные доспехи', 'Тақта сауыт'],
  ['cloak_gray', 'cloak', 'common', 'purchasable', 'Gray Cloak', 'Серый плащ', 'Сұр шапан'],
  ['cloak_royal', 'cloak', 'rare', 'purchasable', 'Royal Cloak', 'Королевский плащ', 'Патша шапаны'],
  ['pet_kitten', 'pet', 'common', 'purchasable', 'Kitten', 'Котёнок', 'Мысық'],
  ['pet_falcon', 'pet', 'rare', 'purchasable', 'Falcon', 'Сокол', 'Сұңқар'],
  ['pet_dragon', 'pet', 'legendary', 'purchasable', 'Baby Dragon', 'Дракончик', 'Кішкентай айдаһар'],
  ['background_meadow', 'background', 'common', 'default', 'Meadow', 'Луг', 'Шалғын'],
  ['background_castle', 'background', 'rare', 'purchasable', 'Castle', 'Замок', 'Қамал'],
  ['background_nebula', 'background', 'epic', 'purchasable', 'Nebula', 'Туманность', 'Тұмандық'],
  ['frame_bronze', 'frame', 'common', 'purchasable', 'Bronze Frame', 'Бронзовая рамка', 'Қола жақтау'],
  ['frame_gold', 'frame', 'legendary', 'purchasable', 'Gold Frame', 'Золотая рамка', 'Алтын жақтау'],
  ['effect_sparkle', 'effect', 'rare', 'purchasable', 'Sparkle', 'Искры', 'Ұшқын'],
  ['effect_aura', 'effect', 'epic', 'purchasable', 'Aura', 'Аура', 'Аура'],
];

function svg(slot, rarity) {
  const { base, deep } = RARITY[rarity];
  const glyph = GLYPH[slot];
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="${slot} ${rarity}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${base}"/>
      <stop offset="1" stop-color="${deep}"/>
    </linearGradient>
  </defs>
  <rect x="4" y="4" width="120" height="120" rx="22" fill="url(#bg)"/>
  <rect x="4" y="4" width="120" height="120" rx="22" fill="none" stroke="#ffffff" stroke-opacity="0.35" stroke-width="2"/>
  <path d="${glyph}" fill="#ffffff" fill-opacity="0.92"/>
  <circle cx="108" cy="20" r="7" fill="${deep}" stroke="#ffffff" stroke-opacity="0.7" stroke-width="1.5"/>
</svg>
`;
}

function seedRows() {
  return CATALOG.map((row, i) => {
    const [sku, slot, rarity, kind, en, ru, kk] = row;
    const price = kind === 'default' ? 'NULL' : RARITY[rarity].price;
    const esc = (s) => s.replace(/'/g, "''");
    return `  ('${sku}','${slot}','${rarity}','${kind}',${price},'${esc(en)}','${esc(ru)}','${esc(kk)}','/gamification/items/${sku}.svg',${i + 1})`;
  }).join(',\n');
}

if (process.argv.includes('--sql')) {
  process.stdout.write(seedRows() + '\n');
} else {
  mkdirSync(OUT_DIR, { recursive: true });
  for (const [sku, slot, rarity] of CATALOG) {
    writeFileSync(resolve(OUT_DIR, `${sku}.svg`), svg(slot, rarity));
  }
  process.stderr.write(`Wrote ${CATALOG.length} SVGs to ${OUT_DIR}\n`);
}
