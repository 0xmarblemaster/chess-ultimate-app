'use client';

export interface PlayerInfo {
  name: string;
  rating?: number;
  color: 'w' | 'b';
  accuracy: number;
}

function Player({ p }: { p: PlayerInfo }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }} data-testid={`player-${p.color}`}>
      <span
        style={{
          width: 34,
          height: 34,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          color: '#fff',
          background: p.color === 'w' ? 'var(--review-accent)' : '#27272A',
        }}
      >
        {p.name.charAt(0).toUpperCase()}
      </span>
      <span style={{ fontWeight: 700, fontSize: 15 }} className="review-heading">
        {p.name}
        {p.rating != null && (
          <span style={{ opacity: 0.55, fontWeight: 500 }}> ({p.rating})</span>
        )}
      </span>
      <span
        data-testid={`player-acc-${p.color}`}
        style={{
          marginLeft: 'auto',
          fontWeight: 800,
          fontSize: 13,
          padding: '3px 10px',
          borderRadius: 5,
          background: 'var(--review-tint-2)',
          color: 'var(--review-accent)',
        }}
      >
        {p.accuracy.toFixed(1)}
      </span>
    </div>
  );
}

export interface PlayersAccuracyRowProps {
  white: PlayerInfo;
  black: PlayerInfo;
}

/** Both players with their accuracy chips (Part B "players+accuracy row"). */
export default function PlayersAccuracyRow({ white, black }: PlayersAccuracyRowProps) {
  return (
    <div
      className="review-card"
      data-testid="players-accuracy-row"
      style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}
    >
      <Player p={black} />
      <Player p={white} />
    </div>
  );
}
