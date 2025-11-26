import { useState, useEffect, useCallback, useMemo } from 'react';

const STORAGE_KEY = 'chess-chat-sessions';

// Chat message interface compatible with existing ChatMessage from useChesster
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  fen?: string;
  timestamp: Date;
  maxTokens?: number;
  provider?: string;
  model?: string;
  response_time_ms?: number;
}

// Chat session interface
export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
  isActive: boolean;
  currentFen: string;
  currentPgn?: string;
}

// Function to generate automatic chat titles based on chess position analysis
export const generateChatTitle = (messages: ChatMessage[], sessionFen?: string): string => {
  // Analyze messages for chess keywords
  const userMessages = messages.filter(msg => msg.role === 'user');
  if (userMessages.length === 0) return 'New Chess Chat';

  const allUserContent = userMessages.map(msg => msg.content.toLowerCase()).join(' ');

  // Enhanced chess opening patterns
  if (allUserContent.includes('sicilian')) {
    if (allUserContent.includes('alapin')) return 'Sicilian Alapin';
    if (allUserContent.includes('dragon')) return 'Sicilian Dragon';
    if (allUserContent.includes('najdorf')) return 'Sicilian Najdorf';
    return 'Sicilian Defense';
  }

  if (allUserContent.includes('caro-kann') || allUserContent.includes('caro kann')) return 'Caro-Kann Defense';
  if (allUserContent.includes('french')) return 'French Defense';
  if (allUserContent.includes('petrov') || allUserContent.includes('russian game')) return 'Petrov Defense';
  if (allUserContent.includes('king\'s indian') || allUserContent.includes('kings indian')) return 'King\'s Indian Defense';

  if (allUserContent.includes('queen\'s gambit') || allUserContent.includes('queens gambit')) {
    if (allUserContent.includes('declined')) return 'Queen\'s Gambit Declined';
    if (allUserContent.includes('accepted')) return 'Queen\'s Gambit Accepted';
    return 'Queen\'s Gambit';
  }

  if (allUserContent.includes('ruy lopez')) return 'Ruy Lopez';
  if (allUserContent.includes('italian')) return 'Italian Game';
  if (allUserContent.includes('london')) return 'London System';
  if (allUserContent.includes('catalan')) return 'Catalan Opening';
  if (allUserContent.includes('nimzo')) return 'Nimzo-Indian Defense';
  if (allUserContent.includes('english')) return 'English Opening';

  // Chess tactics and study patterns
  if (allUserContent.includes('fork')) return 'Tactical Forks';
  if (allUserContent.includes('pin')) return 'Tactical Pins';
  if (allUserContent.includes('skewer')) return 'Skewer Tactics';
  if (allUserContent.includes('sacrifice')) return 'Sacrificial Play';
  if (allUserContent.includes('checkmate')) return 'Checkmate Patterns';

  // Endgame patterns
  if (allUserContent.includes('endgame')) {
    if (allUserContent.includes('king and pawn')) return 'King & Pawn Endgame';
    if (allUserContent.includes('rook')) return 'Rook Endgame';
    return 'Endgame Study';
  }

  // Strategy patterns
  if (allUserContent.includes('strategy')) return 'Chess Strategy';
  if (allUserContent.includes('position') && allUserContent.includes('evaluation')) return 'Position Evaluation';
  if (allUserContent.includes('analysis')) return 'Position Analysis';

  // Fallback: use first few meaningful words from the first user message
  const firstMessage = userMessages[0].content;
  const words = firstMessage.split(' ')
    .filter(word => word.length > 2)
    .slice(0, 3);

  if (words.length === 0) return 'Chess Discussion';

  return words.map((word: string) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
};

export const useChatSessions = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Load sessions from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsedSessions: ChatSession[] = JSON.parse(stored);

        // Ensure all sessions have a currentFen (for backwards compatibility)
        const migratedSessions = parsedSessions.map(session => ({
          ...session,
          currentFen: session.currentFen || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
          messages: session.messages.map(msg => ({
            ...msg,
            timestamp: new Date(msg.timestamp) // Convert string back to Date
          }))
        }));

        setSessions(migratedSessions);

        // Set the most recent session as current if none is selected
        if (migratedSessions.length > 0 && !currentSessionId) {
          const mostRecent = migratedSessions.sort((a, b) => b.updatedAt - a.updatedAt)[0];
          setCurrentSessionId(mostRecent.id);
        }
      } catch (error) {
        console.error('Failed to load chat sessions:', error);
      }
    }
  }, []); // Run once on mount

  // Save sessions to localStorage whenever sessions change
  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    }
  }, [sessions]);

  // Generate unique session ID
  const generateSessionId = useCallback(() => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Create a new chat session
  const createNewSession = useCallback((initialFen?: string) => {
    const newSession: ChatSession = {
      id: generateSessionId(),
      title: 'New Chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isActive: true,
      currentFen: initialFen || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    };

    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    return newSession.id;
  }, [generateSessionId]);

  // Get current session (memoized to prevent unnecessary recalculations)
  const currentSession = useMemo(() => {
    return sessions.find(session => session.id === currentSessionId) || null;
  }, [sessions, currentSessionId]);

  // Helper function to detect chess-related content for better title generation
  const hasChessContent = useCallback((content: string): boolean => {
    const lowerContent = content.toLowerCase();
    const chessKeywords = [
      'sicilian', 'french', 'caro-kann', 'scandinavian', 'alekhine', 'petrov', 'ruy lopez',
      'italian', 'english', 'london', 'catalan', 'nimzo', 'king\'s indian',
      'queen\'s gambit', 'opening', 'defense', 'gambit', 'endgame', 'middlegame',
      'tactics', 'strategy', 'position', 'fen', 'pgn', 'checkmate', 'fork', 'pin',
      'skewer', 'sacrifice', 'analysis', 'engine', 'stockfish', 'pawn', 'knight',
      'bishop', 'rook', 'queen', 'king', 'chess', 'move', 'play'
    ];

    return chessKeywords.some(keyword => lowerContent.includes(keyword));
  }, []);

  // Add message to current session
  const addMessageToSession = useCallback((message: ChatMessage, currentFen?: string) => {
    if (!currentSessionId) {
      // Create new session with the message in a single operation
      const newSessionId = generateSessionId();
      const newSession: ChatSession = {
        id: newSessionId,
        title: 'New Chat',
        messages: [{ ...message, id: message.id || `${Date.now()}`, timestamp: new Date() }],
        createdAt: Date.now(),
        updatedAt: Date.now(),
        isActive: true,
        currentFen: currentFen || 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      };

      // Generate title after adding the message
      newSession.title = generateChatTitle(newSession.messages, currentFen);

      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(newSessionId);
    } else {
      setSessions(prev =>
        prev.map(session =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: [...session.messages, { ...message, id: message.id || `${Date.now()}`, timestamp: new Date() }],
                updatedAt: Date.now(),
                // Regenerate title when it's still "New Chat" or for user messages with chess content
                title: (session.title === 'New Chat' && message.role === 'user') ||
                       (message.role === 'user' && session.messages.length <= 5 && hasChessContent(message.content))
                  ? generateChatTitle([...session.messages, message], currentFen)
                  : session.title,
                // Update FEN if provided
                currentFen: currentFen || session.currentFen
              }
            : session
        )
      );
    }
  }, [currentSessionId, generateSessionId, hasChessContent]);

  // Switch to a different session
  const switchToSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
  }, []);

  // Delete a session
  const deleteSession = useCallback((sessionId: string) => {
    setSessions(prev => {
      const filtered = prev.filter(session => session.id !== sessionId);

      // If the deleted session was current, switch to the most recent one
      if (sessionId === currentSessionId) {
        if (filtered.length > 0) {
          const mostRecent = filtered.sort((a, b) => b.updatedAt - a.updatedAt)[0];
          setCurrentSessionId(mostRecent.id);
        } else {
          setCurrentSessionId(null);
        }
      }

      return filtered;
    });
  }, [currentSessionId]);

  // Rename a session
  const renameSession = useCallback((sessionId: string, newTitle: string) => {
    setSessions(prev =>
      prev.map(session =>
        session.id === sessionId
          ? { ...session, title: newTitle, updatedAt: Date.now() }
          : session
      )
    );
  }, []);

  // Clear all messages in current session
  const clearCurrentSession = useCallback(() => {
    if (currentSessionId) {
      setSessions(prev =>
        prev.map(session =>
          session.id === currentSessionId
            ? { ...session, messages: [], updatedAt: Date.now(), title: 'New Chat' }
            : session
        )
      );
    }
  }, [currentSessionId]);

  // Update session messages (for bulk updates)
  const updateSessionMessages = useCallback((sessionId: string, messages: ChatMessage[]) => {
    setSessions(prev =>
      prev.map(session =>
        session.id === sessionId
          ? { ...session, messages, updatedAt: Date.now() }
          : session
      )
    );
  }, []);

  // Update current session's FEN
  const updateSessionFen = useCallback((fen: string) => {
    if (currentSessionId) {
      setSessions(prev =>
        prev.map(session =>
          session.id === currentSessionId
            ? { ...session, currentFen: fen, updatedAt: Date.now() }
            : session
        )
      );
    }
  }, [currentSessionId]);

  // Update current session's PGN (move history)
  const updateSessionPgn = useCallback((pgn: string) => {
    if (currentSessionId) {
      setSessions(prev =>
        prev.map(session =>
          session.id === currentSessionId
            ? { ...session, currentPgn: pgn, updatedAt: Date.now() }
            : session
        )
      );
    }
  }, [currentSessionId]);

  return {
    sessions,
    currentSessionId,
    currentSession,
    createNewSession,
    addMessageToSession,
    switchToSession,
    deleteSession,
    renameSession,
    clearCurrentSession,
    updateSessionMessages,
    updateSessionFen,
    updateSessionPgn,
  };
};
