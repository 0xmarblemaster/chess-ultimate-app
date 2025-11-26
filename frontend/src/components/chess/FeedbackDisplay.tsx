/**
 * FeedbackDisplay Component
 *
 * Displays feedback banners for chess move results (correct, incorrect, hint)
 * with animated slide-in transitions and appropriate colors/icons
 */

import React from 'react';

export type FeedbackType = 'idle' | 'correct' | 'incorrect' | 'hint';

interface FeedbackDisplayProps {
  /** Current feedback state */
  feedback: FeedbackType;
  /** Optional custom message to display */
  message?: string;
  /** Optional CSS class name for styling */
  className?: string;
}

interface FeedbackConfig {
  icon: string;
  color: string;
  title: string;
  defaultMessage: string;
}

const FEEDBACK_CONFIGS: Record<Exclude<FeedbackType, 'idle'>, FeedbackConfig> = {
  correct: {
    icon: '✓',
    color: 'bg-green-500',
    title: 'Correct!',
    defaultMessage: 'Great move! You found the solution.',
  },
  incorrect: {
    icon: '✗',
    color: 'bg-red-500',
    title: 'Not quite',
    defaultMessage: 'Try again! Think about what the position needs.',
  },
  hint: {
    icon: '💡',
    color: 'bg-yellow-500',
    title: 'Hint',
    defaultMessage: 'The highlighted square shows where to move.',
  },
};

/**
 * FeedbackDisplay component shows success/error/hint messages
 * with smooth animations
 */
export default function FeedbackDisplay({
  feedback,
  message,
  className = '',
}: FeedbackDisplayProps) {
  // Don't render anything if feedback is idle
  if (feedback === 'idle') {
    return null;
  }

  const config = FEEDBACK_CONFIGS[feedback];

  return (
    <div
      className={`
        banner-slide-in
        ${config.color}
        text-white
        p-4
        rounded-lg
        flex
        items-center
        space-x-3
        mt-4
        shadow-lg
        ${className}
      `}
      role="alert"
      aria-live="polite"
    >
      <span className="text-2xl" aria-hidden="true">
        {config.icon}
      </span>
      <div className="flex-1">
        <h4 className="font-bold text-lg">{config.title}</h4>
        <p className="text-sm">{message || config.defaultMessage}</p>
      </div>
    </div>
  );
}
