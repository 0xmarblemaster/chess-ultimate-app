'use client';

import { useState, useEffect } from 'react';

type MascotMood = 'happy' | 'thinking' | 'celebrating' | 'sad' | 'encouraging' | 'neutral';

interface ChessterMascotProps {
  mood?: MascotMood;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  animate?: boolean;
  className?: string;
}

const moodEmojis: Record<MascotMood, string> = {
  happy: '😊',
  thinking: '🤔',
  celebrating: '🎉',
  sad: '😢',
  encouraging: '💪',
  neutral: '😐',
};

const moodColors: Record<MascotMood, string> = {
  happy: 'bg-green-100 border-green-300',
  thinking: 'bg-blue-100 border-blue-300',
  celebrating: 'bg-amber-100 border-amber-300',
  sad: 'bg-gray-100 border-gray-300',
  encouraging: 'bg-purple-100 border-purple-300',
  neutral: 'bg-gray-100 border-gray-300',
};

export function ChessterMascot({
  mood = 'neutral',
  size = 'md',
  animate = true,
  className = '',
}: ChessterMascotProps) {
  const [currentMood, setCurrentMood] = useState(mood);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (mood !== currentMood) {
      setIsAnimating(true);
      const timer = setTimeout(() => {
        setCurrentMood(mood);
        setIsAnimating(false);
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [mood, currentMood]);

  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-16 h-16',
    lg: 'w-24 h-24',
    xl: 'w-32 h-32',
  };

  const knightSizes = {
    sm: 'text-2xl',
    md: 'text-3xl',
    lg: 'text-5xl',
    xl: 'text-6xl',
  };

  const moodBadgeSizes = {
    sm: 'text-xs -top-1 -right-1 w-5 h-5',
    md: 'text-sm -top-1 -right-1 w-6 h-6',
    lg: 'text-base -top-2 -right-2 w-8 h-8',
    xl: 'text-lg -top-2 -right-2 w-10 h-10',
  };

  return (
    <div className={`relative inline-block ${className}`}>
      {/* Main knight character */}
      <div
        className={`${sizeClasses[size]} ${moodColors[currentMood]} border-2 rounded-full flex items-center justify-center shadow-lg transition-all duration-300 ${
          animate && mood === 'celebrating' ? 'animate-bounce' : ''
        } ${animate && mood === 'thinking' ? 'animate-pulse' : ''} ${
          isAnimating ? 'scale-90' : 'scale-100'
        }`}
      >
        <span className={`${knightSizes[size]} select-none`}>♞</span>
      </div>

      {/* Mood indicator badge */}
      <div
        className={`absolute ${moodBadgeSizes[size]} bg-white rounded-full flex items-center justify-center shadow-md border border-gray-200 transition-transform duration-200 ${
          isAnimating ? 'scale-0' : 'scale-100'
        }`}
      >
        {moodEmojis[currentMood]}
      </div>
    </div>
  );
}

// Full mascot with name plate
interface ChessterFullProps extends ChessterMascotProps {
  showName?: boolean;
  name?: string;
}

export function ChessterFull({
  showName = true,
  name = 'Sir Chesster',
  ...props
}: ChessterFullProps) {
  return (
    <div className="flex flex-col items-center gap-2">
      <ChessterMascot {...props} />
      {showName && (
        <div className="text-sm font-medium text-gray-600 bg-white/80 px-2 py-0.5 rounded-full shadow-sm">
          {name}
        </div>
      )}
    </div>
  );
}

// Animated mascot for specific actions
interface AnimatedChessterProps {
  action: 'wave' | 'jump' | 'spin' | 'nod';
  onComplete?: () => void;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function AnimatedChesster({ action, onComplete, size = 'md' }: AnimatedChessterProps) {
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    const duration = action === 'spin' ? 1000 : 600;
    const timer = setTimeout(() => {
      setIsPlaying(false);
      onComplete?.();
    }, duration);
    return () => clearTimeout(timer);
  }, [action, onComplete]);

  const animations: Record<string, string> = {
    wave: 'animate-wiggle',
    jump: 'animate-bounce',
    spin: 'animate-spin',
    nod: 'animate-pulse',
  };

  if (!isPlaying) {
    return <ChessterMascot mood="happy" size={size} />;
  }

  return (
    <div className={animations[action]}>
      <ChessterMascot mood="celebrating" size={size} animate={false} />
    </div>
  );
}
