/**
 * Avatar renderer — composites equipped cosmetic slot layers over the base
 * character (PRD-gamification.md §7.3). Presentational and framework-light: it
 * takes the resolved item per slot and stacks them by z-order. Art is swappable
 * per item (placeholder SVGs today, D-9), so this never hardcodes art.
 */
import type { ItemRow } from '@/lib/gamification/items';

// z-order + placement of each slot layer over the base (background behind,
// effect on top). Placements are % boxes within the square frame.
const LAYERS: Array<{ slot: string; z: number; style: React.CSSProperties }> = [
  { slot: 'background', z: 0, style: { inset: 0 } },
  { slot: 'cloak', z: 1, style: { inset: '18%' } },
  { slot: 'armor', z: 2, style: { left: '28%', top: '40%', width: '44%', height: '44%' } },
  { slot: 'weapon', z: 4, style: { right: '4%', top: '30%', width: '30%', height: '40%' } },
  { slot: 'shield', z: 5, style: { left: '4%', top: '30%', width: '30%', height: '40%' } },
  { slot: 'helmet', z: 6, style: { left: '30%', top: '2%', width: '40%', height: '40%' } },
  { slot: 'pet', z: 7, style: { right: '2%', bottom: '2%', width: '30%', height: '30%' } },
  { slot: 'frame', z: 8, style: { inset: 0 } },
  { slot: 'effect', z: 9, style: { inset: 0, opacity: 0.7, mixBlendMode: 'screen' } },
];

interface AvatarProps {
  /** Equipped item per slot (from the loadout). */
  equipped: Partial<Record<string, ItemRow>>;
  /** Base character image (e.g. the linked student photo / Clerk avatar). */
  photoUrl?: string | null;
  /** Rendered pixel size. */
  size?: number;
  className?: string;
}

export function Avatar({ equipped, photoUrl, size = 160, className = '' }: AvatarProps) {
  const hasBackground = !!equipped.background?.art_url;
  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-b from-slate-100 to-slate-200 ${className}`}
      style={{ width: size, height: size }}
      data-testid="gamification-avatar"
    >
      {/* Base character, centered above the background layer. */}
      <div
        className="absolute rounded-full overflow-hidden bg-white/70 shadow-inner"
        style={{ left: '25%', top: '22%', width: '50%', height: '50%', zIndex: 3 }}
      >
        {photoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={photoUrl} alt="" className="w-full h-full object-cover" />
        ) : (
          <div
            className={`w-full h-full flex items-center justify-center text-2xl ${
              hasBackground ? 'text-white/90' : 'text-slate-400'
            }`}
          >
            {'\u265F\uFE0E'}
          </div>
        )}
      </div>

      {LAYERS.map(({ slot, z, style }) => {
        const item = equipped[slot];
        if (!item?.art_url) return null;
        return (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={slot}
            src={item.art_url}
            alt={item.name_en}
            className="absolute object-contain pointer-events-none select-none"
            style={{ ...style, zIndex: z }}
          />
        );
      })}
    </div>
  );
}
