import React from 'react'
import { Box, Typography } from '@mui/material'
import { useTranslations } from 'next-intl'
import type { Bot } from '@/data/bots'
import { gameTheme } from '@/data/bots'
import { playText, worldName } from '@/lib/botI18n'
import { fredoka, nunito } from '@/lib/fonts'
import BotAvatar from './BotAvatar'

interface GameHeaderProps {
  bot: Bot
  /** Show the animated "thinking…" status inside the speech bubble. */
  thinking: boolean
  /** It is the player's turn to move (drives the "Your move!" status line). */
  yourMove?: boolean
  /** Engine still syncing to the local model (shows a subtle pill). */
  syncing?: boolean
}

const GOLD = '#FFC53D'
const GOLD_TEXT = '#6B4A00'
const INK = '#28324E'

/** Animated "· · ·" dots for the thinking status. */
function ThinkingDots({ color }: { color: string }) {
  return (
    <Box
      component="span"
      aria-hidden="true"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        ml: 0.75,
        '& > span': {
          width: 6,
          height: 6,
          borderRadius: '50%',
          bgcolor: color,
          ml: '3px',
          animation: 'thinkingBounce 1s ease-in-out infinite',
        },
        '& > span:nth-of-type(2)': { animationDelay: '0.15s' },
        '& > span:nth-of-type(3)': { animationDelay: '0.3s' },
        '@keyframes thinkingBounce': {
          '0%, 100%': { opacity: 0.3, transform: 'translateY(0)' },
          '50%': { opacity: 0.9, transform: 'translateY(-3px)' },
        },
      }}
    >
      <span />
      <span />
      <span />
    </Box>
  )
}

/**
 * Chess.com-style in-game bot header: a big rounded-square avatar that visually
 * sits on the board's top edge, a gold ⭐rating badge overlapping its bottom,
 * and a white speech bubble (tail pointing at the avatar) holding the bot name
 * plus a status line — "thinking…" dots while the bot computes, otherwise
 * "Your move!" or the world name.
 *
 * The bubble is always rendered with the same two-line structure so the header
 * keeps a constant height while `thinking` toggles — the board must never shift.
 */
export default function GameHeader({
  bot,
  thinking,
  yourMove = false,
  syncing = false,
}: GameHeaderProps) {
  const t = useTranslations('bots')
  const theme = gameTheme(bot)
  const { deep, tint } = theme

  const statusText = thinking
    ? playText(t, 'thinking', `${bot.name} is thinking`, { name: bot.name })
    : yourMove
      ? playText(t, 'yourMove', 'Your move!')
      : `${theme.worldEmoji} ${worldName(t, bot.tier)}`

  return (
    <Box
      data-testid="game-header"
      data-tier={bot.tier}
      sx={{ display: 'flex', alignItems: 'flex-end', gap: 1.5 }}
    >
      {/* Avatar + gold rating badge */}
      <Box sx={{ position: 'relative', flexShrink: 0 }}>
        <BotAvatar
          bot={bot}
          size={104}
          ringColor="rgba(255,255,255,.95)"
          ringWidth={4}
          tint={tint}
          deep={deep}
          thinking={thinking}
          sx={{
            borderRadius: '26px',
            boxShadow: `0 12px 28px ${deep}5C`,
          }}
        />
        <Box
          component="span"
          sx={{
            position: 'absolute',
            bottom: -10,
            left: '50%',
            transform: 'translateX(-50%)',
            bgcolor: GOLD,
            color: GOLD_TEXT,
            fontFamily: nunito.style.fontFamily,
            fontWeight: 900,
            fontSize: '14px',
            lineHeight: 1,
            borderRadius: '999px',
            px: '11px',
            py: '5px',
            whiteSpace: 'nowrap',
            border: '2px solid #fff',
            boxShadow: `0 4px 10px ${deep}40`,
          }}
        >
          ⭐ {bot.rating}
        </Box>
      </Box>

      {/* Speech bubble: bot name + status line, tail pointing at the avatar. */}
      <Box
        sx={{
          position: 'relative',
          flex: 1,
          minWidth: 0,
          mb: 1.5,
          bgcolor: '#fff',
          borderRadius: '18px',
          px: '16px',
          py: '12px',
          boxShadow: `0 8px 22px ${deep}30`,
        }}
      >
        {/* Tail */}
        <Box
          aria-hidden="true"
          sx={{
            position: 'absolute',
            left: -6,
            top: '50%',
            transform: 'translateY(-50%) rotate(45deg)',
            width: 14,
            height: 14,
            bgcolor: '#fff',
            borderRadius: '3px',
          }}
        />
        <Typography
          component="h2"
          sx={{
            fontFamily: fredoka.style.fontFamily,
            fontWeight: 700,
            fontSize: { xs: '22px', sm: '24px' },
            color: deep,
            lineHeight: 1.1,
          }}
        >
          {bot.name}
        </Typography>
        <Box
          data-testid="thinking-bubble"
          data-thinking={thinking}
          sx={{
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 0.75,
            mt: 0.5,
            fontFamily: nunito.style.fontFamily,
            fontWeight: 800,
            fontSize: '15px',
            color: INK,
            minHeight: 20,
          }}
        >
          <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center' }}>
            {statusText}
            {thinking && <ThinkingDots color={deep} />}
          </Box>
          {syncing && (
            <Box
              component="span"
              data-testid="syncing-pill"
              sx={{
                bgcolor: tint,
                color: deep,
                fontFamily: nunito.style.fontFamily,
                fontWeight: 900,
                fontSize: '11px',
                borderRadius: '999px',
                px: '8px',
                py: '2px',
              }}
            >
              {playText(t, 'syncingEngine', 'Syncing engine…')}
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  )
}
