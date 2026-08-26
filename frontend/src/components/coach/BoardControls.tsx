'use client';

import React from 'react';
import { Box } from '@mui/material';
import { useTranslations } from 'next-intl';
import {
  CBResetIcon,
  CBGoToStartIcon,
  CBPreviousMoveIcon,
  CBNextMoveIcon,
  CBGoToEndIcon,
  CBFlipBoardIcon,
} from '@/components/icons/ChessBaseNavIcons';

interface CoachBoardControlsProps {
  onReset: () => void;
  onFirst: () => void;
  onPrev: () => void;
  onNext: () => void;
  onLast: () => void;
  onFlip: () => void;
  boardSize?: number;
}

export default function CoachBoardControls({
  onReset,
  onFirst,
  onPrev,
  onNext,
  onLast,
  onFlip,
  boardSize = 520,
}: CoachBoardControlsProps) {
  const t = useTranslations('coach');

  // Board Control Bar — matches the canonical Database/Analysis board NAV exactly.
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderRadius: 0,
        height: 38,
        width: boardSize,
        overflow: 'hidden',
      }}
    >
      {[
        { icon: <CBResetIcon sx={{ width: 22, height: 22 }} />, onClick: onReset, title: t('resetBoard'), flex: 1 },
        { icon: <CBGoToStartIcon sx={{ width: 18, height: 14 }} />, onClick: onFirst, title: t('firstMove'), flex: 1 },
        { icon: <CBPreviousMoveIcon sx={{ width: 14, height: 15 }} />, onClick: onPrev, title: t('previousMove'), flex: 1.42 },
        { icon: <CBNextMoveIcon sx={{ width: 14, height: 15 }} />, onClick: onNext, title: t('nextMove'), flex: 1.42 },
        { icon: <CBGoToEndIcon sx={{ width: 18, height: 14 }} />, onClick: onLast, title: t('lastMove'), flex: 1 },
        { icon: <CBFlipBoardIcon sx={{ width: 26, height: 22 }} />, onClick: onFlip, title: t('flipBoard'), flex: 1 },
      ].map((btn, i) => (
        <Box
          key={i}
          onClick={btn.onClick}
          title={btn.title}
          sx={{
            flex: btn.flex,
            height: 38,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: 'text.secondary',
            padding: '5px',
            transition: 'background-color 0.15s, color 0.15s',
            '&:hover': {
              backgroundColor: 'rgba(31,41,55,0.06)',
              color: 'text.primary',
            },
          }}
        >
          {btn.icon}
        </Box>
      ))}
    </Box>
  );
}
