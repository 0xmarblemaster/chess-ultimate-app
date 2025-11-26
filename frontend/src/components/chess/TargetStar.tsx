/**
 * TargetStar Component
 *
 * A Lichess-inspired golden star indicator for target squares in chess exercises.
 * Features three CSS animations:
 * - star-appear: Initial entrance animation (plays once)
 * - soft-grow: Pulsating scale animation (infinite)
 * - soft-hue: Subtle color shift (infinite)
 */

'use client';

import React from 'react';

interface TargetStarProps {
  /** Chess square notation (e.g., "e4", "f6") */
  square: string;
  /** Board orientation - affects position calculation */
  orientation?: 'white' | 'black';
  /** Whether the star is visible */
  visible?: boolean;
}

/**
 * Calculate the position of a square on the board
 */
function getSquarePosition(square: string, orientation: 'white' | 'black') {
  const file = square.charCodeAt(0) - 'a'.charCodeAt(0); // 0-7 (a-h)
  const rank = parseInt(square[1]) - 1; // 0-7 (1-8)

  // For white orientation: a1 is bottom-left, h8 is top-right
  // For black orientation: a1 is top-right, h8 is bottom-left
  const x = orientation === 'white' ? file : 7 - file;
  const y = orientation === 'white' ? 7 - rank : rank;

  return {
    left: `${x * 12.5 + 6.25}%`, // Center of square
    top: `${y * 12.5 + 6.25}%`,
  };
}

export default function TargetStar({ square, orientation = 'white', visible = true }: TargetStarProps) {
  if (!visible || !square) return null;

  const position = getSquarePosition(square, orientation);

  return (
    <>
      {/* CSS Keyframes */}
      <style jsx>{`
        @keyframes star-appear {
          0% {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.3);
          }
          50% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1.1);
          }
          100% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
        }

        @keyframes soft-grow {
          0%, 100% {
            transform: translate(-50%, -50%) scale(1);
          }
          50% {
            transform: translate(-50%, -50%) scale(1.15);
          }
        }

        @keyframes soft-hue {
          0%, 100% {
            filter: hue-rotate(0deg) brightness(1);
          }
          50% {
            filter: hue-rotate(10deg) brightness(1.1);
          }
        }

        .target-star {
          position: absolute;
          width: 15%;
          height: 15%;
          z-index: 100;
          pointer-events: none;
          animation:
            star-appear 0.6s ease-in-out forwards,
            soft-grow 1.7s ease-in-out 0.7s infinite,
            soft-hue 0.7s ease-in-out 0.7s infinite;
          transform-origin: center center;
        }

        .target-star svg {
          width: 100%;
          height: 100%;
          filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
        }
      `}</style>

      <div
        className="target-star"
        style={{
          left: position.left,
          top: position.top,
          transform: 'translate(-50%, -50%)',
        }}
      >
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
          <defs>
            {/* Golden radial gradient - main fill */}
            <radialGradient id="starGold" cx="50%" cy="40%" r="60%" fx="50%" fy="30%">
              <stop offset="0%" stopColor="#FFE343" />
              <stop offset="55%" stopColor="#FFE241" />
              <stop offset="75%" stopColor="#FFDF3A" />
              <stop offset="89%" stopColor="#FEDA2F" />
              <stop offset="100%" stopColor="#FED31E" />
            </radialGradient>

            {/* Orange glow gradient - depth effect */}
            <radialGradient id="starOrange" cx="50%" cy="60%" r="70%">
              <stop offset="0%" stopColor="#FF8000" stopOpacity="0" />
              <stop offset="54%" stopColor="#FD7F00" stopOpacity="0.54" />
              <stop offset="74%" stopColor="#F67C00" stopOpacity="0.74" />
              <stop offset="88%" stopColor="#EB7600" stopOpacity="0.88" />
              <stop offset="100%" stopColor="#D86D00" />
            </radialGradient>

            {/* Border gradient */}
            <radialGradient id="starBorder" cx="50%" cy="55%" r="50%">
              <stop offset="0%" stopColor="#A3541E" stopOpacity="0.5" />
              <stop offset="51%" stopColor="#A5551D" stopOpacity="0.76" />
              <stop offset="70%" stopColor="#AC5819" stopOpacity="0.85" />
              <stop offset="83%" stopColor="#B75E12" stopOpacity="0.91" />
              <stop offset="93%" stopColor="#C86609" stopOpacity="0.97" />
              <stop offset="100%" stopColor="#D86D00" />
            </radialGradient>

            {/* Highlight gradient */}
            <radialGradient id="starHighlight" cx="45%" cy="35%" r="40%">
              <stop offset="0%" stopColor="#FFEC5F" />
              <stop offset="100%" stopColor="#FFEC5F" stopOpacity="0" />
            </radialGradient>
          </defs>

          <g transform="translate(50, 50) scale(3.5)">
            {/* Main star shape - 5-pointed star */}
            <path
              d="M0.52 -8.94L3.15 -3.61C3.18 -3.53 3.26 -3.48 3.34 -3.47L9.22 -2.61C9.69 -2.54 9.88 -1.96 9.54 -1.62L5.41 2.4C5.27 2.53 5.21 2.73 5.24 2.91L6.22 8.6C6.3 9.07 5.8 9.43 5.38 9.21L0.11 6.45C0.04 6.41 -0.05 6.41 -0.12 6.45L-5.38 9.21C-5.81 9.43 -6.3 9.07 -6.22 8.6L-5.21 2.74C-5.2 2.66 -5.22 2.58 -5.29 2.52L-9.54 -1.63C-9.88 -1.97 -9.69 -2.55 -9.22 -2.62L-3.34 -3.47C-3.26 -3.49 -3.18 -3.54 -3.15 -3.61L-0.52 -8.94C-0.31 -9.37 0.31 -9.37 0.52 -8.94Z"
              fill="url(#starGold)"
            />

            {/* Orange glow overlay */}
            <path
              d="M0.52 -8.94L3.15 -3.61C3.18 -3.53 3.26 -3.48 3.34 -3.47L9.22 -2.61C9.69 -2.54 9.88 -1.96 9.54 -1.62L5.41 2.4C5.27 2.53 5.21 2.73 5.24 2.91L6.22 8.6C6.3 9.07 5.8 9.43 5.38 9.21L0.11 6.45C0.04 6.41 -0.05 6.41 -0.12 6.45L-5.38 9.21C-5.81 9.43 -6.3 9.07 -6.22 8.6L-5.21 2.74C-5.2 2.66 -5.22 2.58 -5.29 2.52L-9.54 -1.63C-9.88 -1.97 -9.69 -2.55 -9.22 -2.62L-3.34 -3.47C-3.26 -3.49 -3.18 -3.54 -3.15 -3.61L-0.52 -8.94C-0.31 -9.37 0.31 -9.37 0.52 -8.94Z"
              fill="url(#starOrange)"
              opacity="0.5"
            />

            {/* Highlight on top */}
            <path
              d="M0.52 -8.94L3.15 -3.61C3.18 -3.53 3.26 -3.48 3.34 -3.47L9.22 -2.61C9.69 -2.54 9.88 -1.96 9.54 -1.62L5.41 2.4C5.27 2.53 5.21 2.73 5.24 2.91L6.22 8.6C6.3 9.07 5.8 9.43 5.38 9.21L0.11 6.45C0.04 6.41 -0.05 6.41 -0.12 6.45L-5.38 9.21C-5.81 9.43 -6.3 9.07 -6.22 8.6L-5.21 2.74C-5.2 2.66 -5.22 2.58 -5.29 2.52L-9.54 -1.63C-9.88 -1.97 -9.69 -2.55 -9.22 -2.62L-3.34 -3.47C-3.26 -3.49 -3.18 -3.54 -3.15 -3.61L-0.52 -8.94C-0.31 -9.37 0.31 -9.37 0.52 -8.94Z"
              fill="url(#starHighlight)"
              opacity="0.24"
            />

            {/* Border/outline */}
            <path
              d="M6.22 8.6L5.24 2.91C5.21 2.73 5.27 2.54 5.41 2.4L9.54 -1.63C9.88 -1.97 9.69 -2.55 9.22 -2.62L3.34 -3.47C3.26 -3.49 3.18 -3.54 3.15 -3.61L0.52 -8.94C0.31 -9.37 -0.3 -9.37 -0.52 -8.94L-3.15 -3.61C-3.18 -3.54 -3.26 -3.49 -3.34 -3.47L-9.22 -2.62C-9.69 -2.55 -9.88 -1.97 -9.54 -1.63L-5.28 2.52C-5.22 2.58 -5.19 2.66 -5.21 2.74L-6.22 8.6C-6.3 9.07 -5.8 9.43 -5.38 9.21L-0.11 6.45C-0.04 6.41 0.04 6.41 0.12 6.45L5.38 9.21C5.8 9.43 6.3 9.07 6.22 8.6ZM5.79 8.9C5.75 8.93 5.66 8.98 5.53 8.91L0.27 6.15C0.19 6.1 0.1 6.08 0.01 6.08C-0.09 6.08 -0.18 6.1 -0.26 6.15L-5.52 8.91C-5.65 8.98 -5.74 8.92 -5.78 8.9C-5.82 8.87 -5.91 8.79 -5.88 8.65L-4.89 2.8C-4.85 2.61 -4.91 2.42 -5.05 2.29L-9.31 -1.86C-9.41 -1.96 -9.39 -2.07 -9.37 -2.12C-9.35 -2.17 -9.31 -2.27 -9.17 -2.29L-3.29 -3.15C-3.1 -3.18 -2.94 -3.3 -2.86 -3.46L-0.23 -8.79C-0.17 -8.92 -0.05 -8.93 0 -8.93C0.05 -8.93 0.15 -8.92 0.22 -8.79L2.85 -3.46C2.93 -3.29 3.09 -3.17 3.28 -3.15L9.16 -2.29C9.3 -2.27 9.35 -2.17 9.36 -2.12C9.38 -2.07 9.4 -1.96 9.3 -1.86L5.17 2.17C4.95 2.37 4.86 2.67 4.9 2.97L5.88 8.65C5.91 8.79 5.83 8.87 5.79 8.9Z"
              fill="url(#starBorder)"
            />
          </g>
        </svg>
      </div>
    </>
  );
}
