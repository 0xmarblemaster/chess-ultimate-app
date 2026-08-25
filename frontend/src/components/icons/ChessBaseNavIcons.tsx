'use client';

import { SvgIcon, SvgIconProps } from '@mui/material';

/**
 * ChessBase-style navigation SVG icons (extracted from database.chessbase.com).
 * Shared by every board control bar — the analysis board (AiChessboard), the
 * openings board (DebutBoard) and the Game Review replay bar (PlaybackControls)
 * — so all three stay pixel-identical. Do not fork copies; import from here.
 */

export const CBResetIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 187.862 164">
    <path d="M82,135.848c-29.738,0-53.848-24.109-53.848-53.848S52.262,28.152,82,28.152c9.961,0,19.283,2.715,27.286,7.431 l14.266-24.269C111.364,4.135,97.168,0,82,0C36.713,0,0,36.713,0,82s36.713,82,82,82s82-36.713,82-82h-28.152 C135.848,111.738,111.738,135.848,82,135.848z" />
    <polygon points="111.124,82.652 149.493,16.195 187.862,82.652" />
  </SvgIcon>
);

export const CBGoToStartIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 274.446 170">
    <path d="M274.446,150c0,11-7.794,15.5-17.32,10L144.543,95c-9.526-5.5-9.526-14.5,0-20l112.582-65c9.526-5.5,17.32-1,17.32,10V150z" />
    <path d="M147.223,150c0,11-7.794,15.5-17.32,10L17.32,95c-9.526-5.5-9.526-14.5,0-20l112.583-65c9.526-5.5,17.32-1,17.32,10V150z" />
    <path d="M28,10c0-5.5-4.5-10-10-10h-8C4.5,0,0,4.5,0,10v150c0,5.5,4.5,10,10,10h8c5.5,0,10-4.5,10-10V10z" />
  </SvgIcon>
);

export const CBPreviousMoveIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 137.047 154.695">
    <path d="M137.047,142.347c0,11-7.794,15.5-17.32,10l-112.583-65c-9.526-5.5-9.526-14.5,0-20l112.583-65c9.526-5.5,17.32-1,17.32,10 V142.347z" />
  </SvgIcon>
);

export const CBNextMoveIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 137.047 154.695">
    <path d="M0,12.347c0-11,7.794-15.5,17.32-10l112.583,65c9.526,5.5,9.526,14.5,0,20l-112.583,65c-9.526,5.5-17.32,1-17.32-10V12.347z" />
  </SvgIcon>
);

export const CBGoToEndIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 274.446 170">
    <path d="M0,20C0,9,7.794,4.5,17.32,10l112.583,65c9.526,5.5,9.526,14.5,0,20L17.32,160C7.794,165.5,0,161,0,150V20z" />
    <path d="M127.223,20c0-11,7.794-15.5,17.32-10l112.582,65c9.526,5.5,9.526,14.5,0,20l-112.582,65c-9.526,5.5-17.32,1-17.32-10V20z" />
    <path d="M246.446,160c0,5.5,4.5,10,10,10h8c5.5,0,10-4.5,10-10V10c0-5.5-4.5-10-10-10h-8c-5.5,0-10,4.5-10,10V160z" />
  </SvgIcon>
);

export const CBFlipBoardIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 303.866 170">
    <path d="M274.076,77.414c0-25.335-20.364-45.872-45.485-45.872V0c41.568,1.208,74.902,35.367,74.902,77.362 c0,41.993-33.334,76.154-74.902,77.362v-31.438C253.711,123.285,274.076,102.748,274.076,77.414z" />
    <polygon points="176.938,139.509 229.621,109.018 229.621,170" />
    <path d="M169.956,0v170H0.374V0H169.956z M22.818,147.5h62.346V85h62.346V22.5H85.165V85H22.818V147.5z" />
  </SvgIcon>
);

/** Play triangle — mirrors CBNextMoveIcon's wedge so the replay bar matches. */
export const CBPlayIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 137.047 154.695">
    <path d="M0,12.347c0-11,7.794-15.5,17.32-10l112.583,65c9.526,5.5,9.526,14.5,0,20l-112.583,65c-9.526,5.5-17.32,1-17.32-10V12.347z" />
  </SvgIcon>
);

/** Pause bars, drawn in the same 170-tall coordinate space as the nav icons. */
export const CBPauseIcon = (props: SvgIconProps) => (
  <SvgIcon {...props} viewBox="0 0 130 170">
    <path d="M10,0h30c5.5,0,10,4.5,10,10v150c0,5.5-4.5,10-10,10H10c-5.5,0-10-4.5-10-10V10C0,4.5,4.5,0,10,0z" />
    <path d="M90,0h30c5.5,0,10,4.5,10,10v150c0,5.5-4.5,10-10,10H90c-5.5,0-10-4.5-10-10V10C80,4.5,84.5,0,90,0z" />
  </SvgIcon>
);
