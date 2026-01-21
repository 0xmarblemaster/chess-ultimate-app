'use client';

type ChessLevel = 'pawn' | 'knight' | 'bishop' | 'rook' | 'queen' | 'king';

interface LevelConfig {
  name: string;
  icon: string;
  minXp: number;
  maxXp: number;
  color: string;
  bgColor: string;
}

const LEVELS: Record<ChessLevel, LevelConfig> = {
  pawn: {
    name: 'Pawn',
    icon: '♟',
    minXp: 0,
    maxXp: 100,
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
  },
  knight: {
    name: 'Knight',
    icon: '♞',
    minXp: 100,
    maxXp: 500,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
  },
  bishop: {
    name: 'Bishop',
    icon: '♝',
    minXp: 500,
    maxXp: 1500,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
  },
  rook: {
    name: 'Rook',
    icon: '♜',
    minXp: 1500,
    maxXp: 5000,
    color: 'text-purple-600',
    bgColor: 'bg-purple-100',
  },
  queen: {
    name: 'Queen',
    icon: '♛',
    minXp: 5000,
    maxXp: 15000,
    color: 'text-amber-600',
    bgColor: 'bg-amber-100',
  },
  king: {
    name: 'King',
    icon: '♚',
    minXp: 15000,
    maxXp: Infinity,
    color: 'text-red-600',
    bgColor: 'bg-red-100',
  },
};

export function getLevelFromXp(xp: number): ChessLevel {
  if (xp >= 15000) return 'king';
  if (xp >= 5000) return 'queen';
  if (xp >= 1500) return 'rook';
  if (xp >= 500) return 'bishop';
  if (xp >= 100) return 'knight';
  return 'pawn';
}

export function getNextLevelXp(currentXp: number): number {
  const level = getLevelFromXp(currentXp);
  return LEVELS[level].maxXp;
}

export function getLevelProgress(xp: number): number {
  const level = getLevelFromXp(xp);
  const config = LEVELS[level];
  if (config.maxXp === Infinity) return 100;
  const range = config.maxXp - config.minXp;
  const progress = xp - config.minXp;
  return Math.min(100, Math.round((progress / range) * 100));
}

interface LevelBadgeProps {
  xp: number;
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
  showProgress?: boolean;
}

export function LevelBadge({ xp, size = 'md', showName = true, showProgress = false }: LevelBadgeProps) {
  const level = getLevelFromXp(xp);
  const config = LEVELS[level];
  const progress = getLevelProgress(xp);

  const sizeClasses = {
    sm: { badge: 'w-8 h-8 text-lg', text: 'text-xs' },
    md: { badge: 'w-12 h-12 text-2xl', text: 'text-sm' },
    lg: { badge: 'w-16 h-16 text-4xl', text: 'text-base' },
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`${sizeClasses[size].badge} ${config.bgColor} rounded-full flex items-center justify-center shadow-md`}
      >
        <span className={config.color}>{config.icon}</span>
      </div>
      {showName && (
        <span className={`${sizeClasses[size].text} font-semibold ${config.color}`}>
          {config.name}
        </span>
      )}
      {showProgress && config.maxXp !== Infinity && (
        <div className="w-full mt-1">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${config.bgColor.replace('100', '500')} transition-all duration-500`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-0.5">
            <span>{xp.toLocaleString()} XP</span>
            <span>{config.maxXp.toLocaleString()} XP</span>
          </div>
        </div>
      )}
    </div>
  );
}

interface LevelProgressCardProps {
  xp: number;
}

export function LevelProgressCard({ xp }: LevelProgressCardProps) {
  const level = getLevelFromXp(xp);
  const config = LEVELS[level];
  const progress = getLevelProgress(xp);
  const nextLevelXp = getNextLevelXp(xp);
  const xpToNext = nextLevelXp - xp;

  const levelOrder: ChessLevel[] = ['pawn', 'knight', 'bishop', 'rook', 'queen', 'king'];
  const currentIndex = levelOrder.indexOf(level);
  const nextLevel = currentIndex < levelOrder.length - 1 ? levelOrder[currentIndex + 1] : null;

  return (
    <div className={`${config.bgColor} rounded-2xl p-4 shadow-md`}>
      <div className="flex items-center gap-4">
        <div className="text-5xl">{config.icon}</div>
        <div className="flex-1">
          <div className={`text-xl font-bold ${config.color}`}>
            {config.name} Level
          </div>
          <div className="text-sm text-gray-600">
            {xp.toLocaleString()} XP total
          </div>
        </div>
      </div>

      {nextLevel && (
        <div className="mt-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">{xpToNext.toLocaleString()} XP to {LEVELS[nextLevel].name}</span>
            <span className="font-medium">{progress}%</span>
          </div>
          <div className="h-3 bg-white/50 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r from-${config.color.split('-')[1]}-400 to-${config.color.split('-')[1]}-600 transition-all duration-500`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
