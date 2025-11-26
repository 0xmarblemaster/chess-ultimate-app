/**
 * ArrowOverlay Component
 *
 * Draws SVG arrows on the chess board to show the path from a piece to a target.
 * Arrows are styled like Lichess with a green/olive color and smooth curves.
 */

'use client';

import React from 'react';

interface ArrowOverlayProps {
  /** Starting square (where the piece is) */
  fromSquare: string;
  /** Target square (where to go) */
  toSquare: string;
  /** Board orientation */
  orientation?: 'white' | 'black';
  /** Whether arrows are visible */
  visible?: boolean;
  /** Intermediate squares for multi-move paths */
  intermediateSquares?: string[];
}

/**
 * Convert chess square notation to board coordinates (0-7)
 */
function squareToCoords(square: string, orientation: 'white' | 'black') {
  const file = square.charCodeAt(0) - 'a'.charCodeAt(0); // 0-7 (a-h)
  const rank = parseInt(square[1]) - 1; // 0-7 (1-8)

  // Adjust for board orientation
  const x = orientation === 'white' ? file : 7 - file;
  const y = orientation === 'white' ? 7 - rank : rank;

  return { x, y };
}

/**
 * Get center position of a square as percentage
 */
function getSquareCenter(square: string, orientation: 'white' | 'black') {
  const { x, y } = squareToCoords(square, orientation);
  return {
    x: x * 12.5 + 6.25, // Center of square (12.5% per square)
    y: y * 12.5 + 6.25,
  };
}

export default function ArrowOverlay({
  fromSquare,
  toSquare,
  orientation = 'white',
  visible = true,
  intermediateSquares = [],
}: ArrowOverlayProps) {
  if (!visible || !fromSquare || !toSquare) return null;

  // Build the path: from -> intermediates -> to
  const allSquares = [fromSquare, ...intermediateSquares, toSquare];
  const points = allSquares.map((sq) => getSquareCenter(sq, orientation));

  return (
    <>
      <style jsx>{`
        @keyframes arrow-appear {
          0% {
            stroke-opacity: 0;
            fill-opacity: 0;
            stroke-dashoffset: 100;
          }
          100% {
            stroke-opacity: 0.5;
            fill-opacity: 0.5;
            stroke-dashoffset: 0;
          }
        }

        .arrow-overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 50;
        }

        .arrow-path {
          animation: arrow-appear 0.5s ease-out forwards;
          stroke-opacity: 0.5;
        }
      `}</style>

      <svg className="arrow-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          {/* Arrowhead marker */}
          <marker
            id="arrowhead"
            markerWidth="3"
            markerHeight="3"
            refX="2"
            refY="1.5"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <polygon points="0 0, 3 1.5, 0 3" fill="#659550" fillOpacity="0.5" />
          </marker>
        </defs>

        {/* Draw arrows between consecutive points */}
        {points.slice(0, -1).map((point, index) => {
          const nextPoint = points[index + 1];

          // Calculate direction for slight offset (avoid covering pieces)
          const dx = nextPoint.x - point.x;
          const dy = nextPoint.y - point.y;
          const length = Math.sqrt(dx * dx + dy * dy);
          const unitX = dx / length;
          const unitY = dy / length;

          // First arrow starts offset from center (to not cover the piece)
          // Subsequent arrows start where the previous arrow's head ended
          const startOffset = index === 0 ? 3 : -1; // -1 to overlap with previous arrowhead
          const endOffset = 4; // Stop before reaching center (for arrowhead)

          const startX = point.x + unitX * startOffset;
          const startY = point.y + unitY * startOffset;
          const endX = nextPoint.x - unitX * endOffset;
          const endY = nextPoint.y - unitY * endOffset;

          return (
            <line
              key={`arrow-${index}`}
              className="arrow-path"
              x1={startX}
              y1={startY}
              x2={endX}
              y2={endY}
              stroke="#659550"
              strokeWidth="2.5"
              strokeLinecap="round"
              markerEnd="url(#arrowhead)"
              strokeOpacity="0.5"
              style={{ animationDelay: `${index * 0.15}s` }}
            />
          );
        })}
      </svg>
    </>
  );
}
