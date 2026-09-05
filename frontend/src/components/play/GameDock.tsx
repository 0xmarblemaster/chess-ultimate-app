import React, { useState } from 'react'
import {
  Box,
  Typography,
  Drawer,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material'
import { useTranslations } from 'next-intl'
import type { Bot } from '@/data/bots'
import { gameTheme } from '@/data/bots'
import { playText } from '@/lib/botI18n'
import { fredoka, nunito } from '@/lib/fonts'

interface GameDockProps {
  bot: Bot
  /** Resolved player color for this game. */
  playerColor: 'w' | 'b'
  /** Result text once the game has ended (null while in progress). */
  gameResult: string | null
  onNewGame: () => void
  /** End the game as a loss for the player. */
  onResign: () => void
  /** Show a hint arrow on the board (disabled unless `canHint`). */
  onHint?: () => void
  /** Undo the last player move + bot reply (disabled unless `canTakeback`). */
  onTakeback?: () => void
  /** Flip the board orientation. */
  onFlip?: () => void
  canHint?: boolean
  canTakeback?: boolean
}

const INK = '#28324E'
const INK_SOFT = '#5C6784'
const GOLD = '#FFC53D'
const GOLD_TEXT = '#6B4A00'
const RESIGN_TEXT = '#E5484D'

interface ActionButtonProps {
  icon: string
  label: string
  onClick?: () => void
  disabled?: boolean
  /** Gold "primary" treatment (the Hint action). */
  primary?: boolean
  testId: string
  tint: string
  deep: string
}

/** One labeled icon action in the bottom bar (44px+ touch target). */
function ActionButton({
  icon,
  label,
  onClick,
  disabled = false,
  primary = false,
  testId,
  tint,
  deep,
}: ActionButtonProps) {
  return (
    <Box
      component="button"
      type="button"
      data-testid={testId}
      onClick={onClick}
      disabled={disabled}
      sx={{
        flex: 1,
        minWidth: 56,
        minHeight: 56,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 0.5,
        p: 0,
        border: 'none',
        bgcolor: 'transparent',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        transition: 'opacity 120ms ease, transform 120ms ease',
        '&:not(:disabled):hover': { transform: 'translateY(-1px)' },
      }}
    >
      <Box
        aria-hidden="true"
        sx={{
          width: 48,
          height: 48,
          borderRadius: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '22px',
          lineHeight: 1,
          bgcolor: primary ? GOLD : tint,
          color: primary ? GOLD_TEXT : deep,
          boxShadow: primary ? `0 6px 14px ${GOLD}66` : 'none',
        }}
      >
        {icon}
      </Box>
      <Box
        component="span"
        sx={{ fontFamily: nunito.style.fontFamily, fontWeight: 800, fontSize: '12px', color: INK }}
      >
        {label}
      </Box>
    </Box>
  )
}

/**
 * Chess.com-style bottom action bar: four labeled icon actions —
 * Menu · Resign · Hint (gold/primary) · Take back. The Menu opens a bottom
 * sheet with Flip board, New game, and the player's color line. Resign is gated
 * behind a kid-friendly confirm dialog. Once the game ends, Hint/Take back/
 * Resign are disabled and a prominent New game button is shown instead.
 */
export default function GameDock({
  bot,
  playerColor,
  gameResult,
  onNewGame,
  onResign,
  onHint,
  onTakeback,
  onFlip,
  canHint = false,
  canTakeback = false,
}: GameDockProps) {
  const t = useTranslations('bots')
  const { main, deep, tint, screenGradient } = gameTheme(bot)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  const ended = Boolean(gameResult)

  const colorLabel =
    playerColor === 'w'
      ? playText(t, 'white', 'White')
      : playText(t, 'black', 'Black')

  const handleConfirmResign = () => {
    setConfirmOpen(false)
    onResign()
  }

  const handleMenuNewGame = () => {
    setMenuOpen(false)
    onNewGame()
  }

  const handleFlip = () => {
    setMenuOpen(false)
    onFlip?.()
  }

  return (
    <Box>
      {/* Result + prominent New game once the game has ended. */}
      {ended && (
        <Box sx={{ mb: 1.5, textAlign: 'center' }}>
          <Typography
            sx={{
              fontFamily: nunito.style.fontFamily,
              fontWeight: 900,
              fontSize: '14px',
              color: '#fff',
              mb: 1,
              textShadow: `0 2px 8px ${deep}59`,
            }}
          >
            {gameResult}
          </Typography>
          <Box
            component="button"
            type="button"
            data-testid="new-game-button"
            onClick={onNewGame}
            sx={{
              width: '100%',
              background: screenGradient,
              color: '#fff',
              border: 'none',
              fontFamily: nunito.style.fontFamily,
              fontWeight: 900,
              fontSize: '15px',
              borderRadius: '999px',
              py: '13px',
              cursor: 'pointer',
              boxShadow: `0 8px 18px ${deep}4D`,
            }}
          >
            🔁 {playText(t, 'newGame', 'New game')}
          </Box>
        </Box>
      )}

      {/* Bottom action bar */}
      <Box
        data-testid="game-dock"
        data-tier={bot.tier}
        sx={{
          display: 'flex',
          gap: 0.5,
          bgcolor: 'rgba(255,255,255,.96)',
          borderRadius: '22px',
          px: 1,
          py: 1.25,
          boxShadow: `0 10px 26px ${deep}40`,
        }}
      >
        <ActionButton
          testId="game-menu-button"
          icon="☰"
          label={playText(t, 'menu', 'Menu')}
          onClick={() => setMenuOpen(true)}
          tint={tint}
          deep={deep}
        />
        <ActionButton
          testId="resign-button"
          icon="🏳️"
          label={playText(t, 'resign', 'Resign')}
          onClick={() => setConfirmOpen(true)}
          disabled={ended}
          tint={tint}
          deep={deep}
        />
        <ActionButton
          testId="hint-button"
          icon="💡"
          label={playText(t, 'hint', 'Hint')}
          onClick={onHint}
          disabled={ended || !canHint}
          primary
          tint={tint}
          deep={deep}
        />
        <ActionButton
          testId="takeback-button"
          icon="↩"
          label={playText(t, 'takeBack', 'Take back')}
          onClick={onTakeback}
          disabled={ended || !canTakeback}
          tint={tint}
          deep={deep}
        />
      </Box>

      {/* Menu bottom sheet: Flip board, New game, player color line. */}
      <Drawer
        anchor="bottom"
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        data-testid="game-menu-sheet"
        PaperProps={{
          sx: {
            borderRadius: '22px 22px 0 0',
            p: 2.5,
            maxWidth: 660,
            mx: 'auto',
            width: '100%',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, mb: 2 }}>
          <Box
            aria-hidden="true"
            sx={{
              width: 38,
              height: 38,
              borderRadius: '50%',
              bgcolor: tint,
              border: `2px solid ${main}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              color: INK,
              flexShrink: 0,
            }}
          >
            {playerColor === 'w' ? '♔' : '♚'}
          </Box>
          <Typography
            sx={{ fontFamily: nunito.style.fontFamily, fontWeight: 900, fontSize: '15px', color: INK }}
          >
            {playText(t, 'youAreColor', `You — ${colorLabel}`, { color: colorLabel })}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
          <Box
            component="button"
            type="button"
            data-testid="flip-board-button"
            onClick={handleFlip}
            sx={{
              bgcolor: tint,
              color: deep,
              border: `2px solid ${main}`,
              fontFamily: nunito.style.fontFamily,
              fontWeight: 800,
              fontSize: '15px',
              borderRadius: '14px',
              py: '13px',
              cursor: 'pointer',
            }}
          >
            🔄 {playText(t, 'flipBoard', 'Flip board')}
          </Box>
          {!ended && (
            <Box
              component="button"
              type="button"
              data-testid="new-game-button"
              onClick={handleMenuNewGame}
              sx={{
                background: screenGradient,
                color: '#fff',
                border: 'none',
                fontFamily: nunito.style.fontFamily,
                fontWeight: 900,
                fontSize: '15px',
                borderRadius: '14px',
                py: '13px',
                cursor: 'pointer',
                boxShadow: `0 6px 14px ${deep}4D`,
              }}
            >
              🔁 {playText(t, 'newGame', 'New game')}
            </Box>
          )}
        </Box>
      </Drawer>

      {/* Resign confirm dialog */}
      <Dialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        data-testid="resign-dialog"
        PaperProps={{ sx: { borderRadius: '20px', p: 1 } }}
      >
        <DialogTitle
          sx={{ fontFamily: fredoka.style.fontFamily, fontWeight: 700, color: INK }}
        >
          {playText(t, 'resignConfirmTitle', 'Give up this game?')}
        </DialogTitle>
        <DialogContent>
          <DialogContentText
            sx={{ fontFamily: nunito.style.fontFamily, fontWeight: 700, color: INK_SOFT }}
          >
            {playText(
              t,
              'resignConfirmBody',
              `If you give up, ${bot.name} wins. You can start a new game any time!`,
              { name: bot.name },
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2, gap: 1 }}>
          <Box
            component="button"
            type="button"
            data-testid="resign-cancel"
            onClick={() => setConfirmOpen(false)}
            sx={{
              bgcolor: tint,
              color: deep,
              border: `2px solid ${main}`,
              fontFamily: nunito.style.fontFamily,
              fontWeight: 800,
              fontSize: '14px',
              borderRadius: '999px',
              py: '9px',
              px: '18px',
              cursor: 'pointer',
            }}
          >
            {playText(t, 'resignConfirmCancel', 'Keep playing')}
          </Box>
          <Box
            component="button"
            type="button"
            data-testid="resign-confirm"
            onClick={handleConfirmResign}
            sx={{
              bgcolor: RESIGN_TEXT,
              color: '#fff',
              border: 'none',
              fontFamily: nunito.style.fontFamily,
              fontWeight: 800,
              fontSize: '14px',
              borderRadius: '999px',
              py: '9px',
              px: '18px',
              cursor: 'pointer',
            }}
          >
            {playText(t, 'resignConfirmYes', 'Yes, I give up')}
          </Box>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
