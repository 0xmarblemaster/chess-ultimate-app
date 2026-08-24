'use client';

/**
 * "Play a friend" entry (phase 3). Pick a time control + colour, create a
 * challenge via POST /api/live-games/challenge, copy the invite link, and navigate
 * the creator to the live-game lobby. Rendered by the play page only when
 * ONLINE_PLAY_ENABLED is on (the flag gate lives at the call site).
 *
 * Two layouts share all of the challenge logic:
 *  - `variant="card"` (default): the original vertical card.
 *  - `variant="horizontal"`: a full-width bar that sits above the bot grid.
 *    Desktop shows a single wrapping row (title + controls + button); below the
 *    `md` breakpoint it collapses to a pill that expands the options inline.
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { playText } from '@/lib/botI18n';
import type { ColorChoice } from '@/lib/live-game/types';

interface TimeControl {
  key: string;
  // Time labels are formatted (e.g. "3 + 2"); `untimedKey` marks the one entry
  // whose label is a localized word rather than a number pair.
  label: string;
  untimedKey?: boolean;
  initialSec: number | null;
  incrementSec: number | null;
}

const TIME_CONTROLS: TimeControl[] = [
  { key: '3+2', label: '3 + 2', initialSec: 180, incrementSec: 2 },
  { key: '5+0', label: '5 + 0', initialSec: 300, incrementSec: 0 },
  { key: '10+0', label: '10 + 0', initialSec: 600, incrementSec: 0 },
  { key: 'untimed', label: 'Untimed', untimedKey: true, initialSec: null, incrementSec: null },
];

const COLORS: Array<{ key: ColorChoice; colorKey: string }> = [
  { key: 'white', colorKey: 'white' },
  { key: 'random', colorKey: 'random' },
  { key: 'black', colorKey: 'black' },
];

const PILL_SX = {
  borderRadius: '12px !important',
  border: '1px solid #E3EAF6 !important',
  px: 2,
} as const;

const SURFACE_SX = {
  bgcolor: '#FFFFFF',
  border: '1px solid #E3EAF6',
  boxShadow: '0 8px 24px rgba(30,60,120,0.08)',
} as const;

type Variant = 'card' | 'horizontal';

interface PlayFriendCardProps {
  variant?: Variant;
}

export default function PlayFriendCard({ variant = 'card' }: PlayFriendCardProps) {
  const t = useTranslations('bots');
  const router = useRouter();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [tcKey, setTcKey] = useState('5+0');
  const [color, setColor] = useState<ColorChoice>('random');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  const createChallenge = async () => {
    if (creating) return;
    setCreating(true);
    setError(null);
    const tc = TIME_CONTROLS.find((x) => x.key === tcKey) ?? TIME_CONTROLS[1];
    try {
      const res = await fetch('/api/live-games/challenge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          colorChoice: color,
          initialSec: tc.initialSec,
          incrementSec: tc.incrementSec,
        }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        setError(body.error || playText(t, 'errCreate', 'Could not create the game. Try again.'));
        setCreating(false);
        return;
      }
      const { gameId, url } = (await res.json()) as { gameId: string; url: string };
      // Best-effort copy the invite link; navigation is what matters.
      try {
        await navigator.clipboard?.writeText(url);
      } catch {
        /* clipboard may be unavailable (permissions / non-secure ctx) */
      }
      router.push(`/play/live/${gameId}`);
    } catch {
      setError(playText(t, 'errNetwork', 'Network error. Try again.'));
      setCreating(false);
    }
  };

  // Pre-resolved localized option labels, shared by both layouts.
  const timeOptions = TIME_CONTROLS.map((tc) => ({
    key: tc.key,
    label: tc.untimedKey ? playText(t, 'untimed', tc.label) : tc.label,
  }));
  const colorOptions = COLORS.map((c) => ({ key: c.key, label: playText(t, c.colorKey, c.key) }));

  const timeGroup = (extraSx?: object) => (
    <ToggleButtonGroup
      value={tcKey}
      exclusive
      onChange={(_e, v) => v && setTcKey(v)}
      sx={{ flexWrap: 'wrap', gap: 1, ...extraSx }}
    >
      {timeOptions.map((o) => (
        <ToggleButton key={o.key} value={o.key} sx={PILL_SX}>
          {o.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );

  const colorGroup = (extraSx?: object) => (
    <ToggleButtonGroup
      value={color}
      exclusive
      onChange={(_e, v) => v && setColor(v as ColorChoice)}
      sx={{ flexWrap: 'wrap', gap: 1, ...extraSx }}
    >
      {colorOptions.map((o) => (
        <ToggleButton key={o.key} value={o.key} sx={PILL_SX}>
          {o.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );

  const caption = (text: string) => (
    <Typography variant="caption" sx={{ display: 'block', fontWeight: 700, color: '#5C6B85', mb: 0.75 }}>
      {text}
    </Typography>
  );

  const errorEl = error && (
    <Typography variant="body2" sx={{ color: '#C62828', mb: 1.5 }}>
      {error}
    </Typography>
  );

  const createButton = (extraSx?: object, label?: string) => (
    <Button
      variant="contained"
      disabled={creating}
      onClick={createChallenge}
      data-testid="create-challenge"
      sx={{
        borderRadius: '999px',
        textTransform: 'none',
        fontWeight: 800,
        py: 1.25,
        whiteSpace: 'nowrap',
        bgcolor: '#2E6BFF',
        '&:hover': { bgcolor: '#2258db' },
        ...extraSx,
      }}
    >
      {creating
        ? playText(t, 'creating', 'Creating…')
        : label ?? playText(t, 'createGameLink', 'Create game link')}
    </Button>
  );

  // ── Default vertical card ────────────────────────────────────────────────
  if (variant === 'card') {
    return (
      <Box
        data-testid="play-friend-card"
        sx={{ p: { xs: 2, sm: 3 }, borderRadius: '20px', ...SURFACE_SX }}
      >
        <Typography variant="body2" sx={{ color: '#5C6B85', mb: 2 }}>
          {playText(t, 'friendSubtitle', 'Create a game and share the link — it opens live for both of you.')}
        </Typography>

        {caption(playText(t, 'timeControl', 'TIME CONTROL'))}
        {timeGroup({ mb: 2 })}

        {caption(playText(t, 'yourColor', 'YOUR COLOR'))}
        {colorGroup({ mb: 2 })}

        {errorEl}
        {createButton({ width: '100%' })}
      </Box>
    );
  }

  // ── Horizontal bar (above the bot grid) ──────────────────────────────────
  const title = (
    <Typography
      component="h2"
      sx={{ m: 0, fontWeight: 800, fontSize: '18px', color: '#1E2A44', display: 'flex', alignItems: 'center', gap: 0.75 }}
    >
      <Box component="span" aria-hidden="true">🤝</Box>
      {playText(t, 'sectionFriend', 'Play a friend')}
    </Typography>
  );

  // Mobile: collapsed pill that expands the options inline. Sane defaults let a
  // user create a game straight from the pill without ever expanding.
  if (isMobile) {
    const tc = TIME_CONTROLS.find((x) => x.key === tcKey) ?? TIME_CONTROLS[1];
    const tcLabel = tc.untimedKey ? playText(t, 'untimed', tc.label) : tc.label;
    const summary = `${tcLabel} · ${playText(t, color, color)}`;
    return (
      <Box
        data-testid="play-friend-bar"
        sx={{ p: 1, borderRadius: expanded ? '20px' : '999px', ...SURFACE_SX }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            component="button"
            type="button"
            onClick={() => setExpanded((e) => !e)}
            aria-expanded={expanded}
            data-testid="play-friend-toggle"
            sx={{
              flex: 1,
              minWidth: 0,
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              px: 1.5,
              py: 1,
              border: 'none',
              borderRadius: '999px',
              bgcolor: 'transparent',
              cursor: 'pointer',
              textAlign: 'left',
              color: '#1E2A44',
            }}
          >
            <Box component="span" aria-hidden="true" sx={{ fontSize: 18 }}>🤝</Box>
            <Box
              component="span"
              sx={{
                fontWeight: 800,
                fontSize: '15px',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                minWidth: 0,
              }}
            >
              {playText(t, 'sectionFriend', 'Play a friend')}
            </Box>
            {!expanded && (
              <Box
                component="span"
                sx={{
                  color: '#5C6B85',
                  fontSize: '13px',
                  minWidth: 0,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {summary}
              </Box>
            )}
            <Box component="span" aria-hidden="true" sx={{ ml: 'auto', color: '#5C6B85' }}>
              {expanded ? '▴' : '▾'}
            </Box>
          </Box>
          {!expanded &&
            createButton(
              { py: 1, px: 2, fontSize: '14px', flexShrink: 0 },
              playText(t, 'createShort', 'Create'),
            )}
        </Box>

        {expanded && (
          <Box sx={{ px: 1, pt: 2, pb: 1 }}>
            {caption(playText(t, 'timeControl', 'TIME CONTROL'))}
            {timeGroup({ mb: 2 })}
            {caption(playText(t, 'yourColor', 'YOUR COLOR'))}
            {colorGroup({ mb: 2 })}
            {errorEl}
            {createButton({ width: '100%' })}
          </Box>
        )}
      </Box>
    );
  }

  // Desktop: single wrapping row — title/subtitle · time · color · button.
  return (
    <Box
      data-testid="play-friend-bar"
      sx={{
        p: { xs: 2, sm: 2.5 },
        borderRadius: '20px',
        ...SURFACE_SX,
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 3,
      }}
    >
      <Box sx={{ flex: '1 1 220px', minWidth: 200 }}>
        {title}
        <Typography variant="body2" sx={{ color: '#5C6B85', mt: 0.25 }}>
          {playText(t, 'friendSubtitle', 'Create a game and share the link — it opens live for both of you.')}
        </Typography>
      </Box>

      <Box>
        {caption(playText(t, 'timeControl', 'TIME CONTROL'))}
        {timeGroup()}
      </Box>

      <Box>
        {caption(playText(t, 'yourColor', 'YOUR COLOR'))}
        {colorGroup()}
      </Box>

      <Box sx={{ ml: { md: 'auto' } }}>{createButton()}</Box>

      {error && <Box sx={{ flexBasis: '100%' }}>{errorEl}</Box>}
    </Box>
  );
}
