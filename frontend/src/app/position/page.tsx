"use client";

import { useState, useEffect, useRef } from "react";
import { Box, Stack, IconButton } from "@mui/material";
import { Menu as MenuIcon } from "@mui/icons-material";
import { Chess } from "chess.js";
import AiChessboardPanel from "@/componets/analysis/AiChessboard";
import useChesster from "@/hooks/useChesster";
// Clerk authentication disabled for local development
// import { useSession } from "@clerk/nextjs";
import { purpleTheme } from "@/theme/theme";
import Loader from "@/componets/loading/Loader";
import Warning from "@/componets/loading/SignUpWarning";
import ChessterAnalysisView from "@/componets/analysis/ChessterAnalysisView";
import ChatSidebar from "@/componets/ChatSidebar";
import { useChatSessions } from "@/hooks/useChatSessions";

export default function PositionPage() {
  // const session = useSession();
  // Simulated session for no-auth mode
  const session = { isLoaded: true, isSignedIn: true };
  const [game, setGame] = useState(new Chess());
  const [fen, setFen] = useState(game.fen());

  // Ref to track if we're loading messages from session (prevent save loop)
  const isLoadingFromSession = useRef(false);

  // Chat sidebar state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Chat session management
  const {
    sessions,
    currentSessionId,
    currentSession,
    createNewSession,
    switchToSession,
    deleteSession,
    renameSession,
    updateSessionFen,
    addMessageToSession,
    updateSessionMessages,
  } = useChatSessions();

  const {
    setLlmAnalysisResult,
    stockfishAnalysisResult,
    setStockfishAnalysisResult,
    openingData,
    setOpeningData,
    llmLoading,
    stockfishLoading,
    openingLoading,
    legalMoves,
    handleFutureMoveLegalClick,
    moveSquares,
    setMoveSquares,
    chatMessages,
    setChatMessages,
    chatInput,
    setChatInput,
    chatLoading,
    sessionMode,
    lichessOpeningData,
    lichessOpeningLoading,
    setSessionMode,
    engineDepth,
    setEngineDepth,
    engineLines,
    setEngineLines,
    engine,
    fetchOpeningData,
    sendChatMessage,
    handleChatKeyPress,
    clearChatHistory,
    analyzeWithStockfish,
    formatEvaluation,
    formatPrincipalVariation,
    handleEngineLineClick,
    abortChatMessage,
    handleOpeningMoveClick,
    handleMoveClick,
    chessdbdata,
    loading,
    queueing,
    error,
    refetch,
    requestAnalysis,
  } = useChesster(fen);

  // Chat session handlers
  const handleNewChat = () => {
    // Reset to starting position
    const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    const resetGame = new Chess();
    setGame(resetGame);
    setFen(startingFen);
    setLlmAnalysisResult(null);

    // Clear chat messages
    setChatMessages([]);

    // Create new session with starting position
    createNewSession(startingFen);
  };

  const handleSelectSession = (sessionId: string) => {
    switchToSession(sessionId);
  };

  // Sync board FEN with current session
  useEffect(() => {
    if (currentSession && currentSession.currentFen && currentSession.currentFen !== fen) {
      try {
        const sessionGame = new Chess();
        sessionGame.load(currentSession.currentFen);
        setGame(sessionGame);
        setFen(sessionGame.fen());
      } catch (error) {
        console.error('Invalid FEN in session, using default:', error);
        const defaultGame = new Chess();
        setGame(defaultGame);
        setFen(defaultGame.fen());
        updateSessionFen(defaultGame.fen());
      }
    }
  }, [currentSessionId, currentSession]);

  // Load chat messages from current session when session changes
  useEffect(() => {
    if (currentSession) {
      isLoadingFromSession.current = true;
      setChatMessages(currentSession.messages || []);
      // Reset flag after a short delay
      setTimeout(() => {
        isLoadingFromSession.current = false;
      }, 100);
    } else if (chatMessages.length > 0) {
      setChatMessages([]);
    }
  }, [currentSessionId]);

  // Save chat messages to current session when they change (with debounce)
  useEffect(() => {
    // Don't save if we're currently loading from session
    if (isLoadingFromSession.current) {
      return;
    }

    if (currentSessionId && chatMessages.length > 0) {
      const timeoutId = setTimeout(() => {
        updateSessionMessages(currentSessionId, chatMessages);
      }, 300);

      return () => clearTimeout(timeoutId);
    }
  }, [chatMessages, currentSessionId, updateSessionMessages]);

  // Update session FEN when board changes (with debounce)
  useEffect(() => {
    if (currentSessionId && fen) {
      const timeoutId = setTimeout(() => {
        updateSessionFen(fen);
      }, 300);

      return () => clearTimeout(timeoutId);
    }
  }, [fen, currentSessionId, updateSessionFen]);

  if (!session.isLoaded) {
    return <Loader />;
  }

  if (!session.isSignedIn) {
    return <Warning />;
  }

  return (
    <Box
      sx={{
        display: "flex",
        backgroundColor: purpleTheme.background.main,
        minHeight: "100vh",
        position: "relative",
      }}
    >
      {/* Chat Sidebar */}
      <Box
        sx={{
          flexShrink: 0,
          transition: "all 0.3s ease",
        }}
      >
        <ChatSidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          onDeleteSession={deleteSession}
          onRenameSession={renameSession}
          isCollapsed={isSidebarCollapsed}
          currentBoardFen={fen}
        />
      </Box>

      {/* Sidebar Toggle Button */}
      <IconButton
        onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        sx={{
          position: "fixed",
          top: 16,
          left: isSidebarCollapsed ? 72 : 336,
          zIndex: 1300,
          backgroundColor: purpleTheme.accent,
          color: "#fff",
          "&:hover": {
            backgroundColor: `${purpleTheme.accent}dd`,
          },
          transition: "left 0.3s ease",
          boxShadow: "0 4px 12px rgba(138, 43, 226, 0.3)",
          display: { xs: "none", md: "flex" },
        }}
      >
        <MenuIcon />
      </IconButton>

      {/* Main Content Area */}
      <Box
        sx={{
          flex: 1,
          p: 4,
          minWidth: 0,
          overflow: "hidden",
        }}
      >
        <Stack direction={{ xs: "column", lg: "row" }} spacing={4}>
        {/* Chessboard Section */}
        <Box sx={{ flex: "0 0 auto" }}>
          <AiChessboardPanel
            game={game}
            fen={fen}
            moveSquares={moveSquares}
            setMoveSquares={setMoveSquares}
            engine={engine}
            setFen={setFen}
            setGame={setGame}
            setLlmAnalysisResult={setLlmAnalysisResult}
            setOpeningData={setOpeningData}
            setStockfishAnalysisResult={setStockfishAnalysisResult}
            fetchOpeningData={fetchOpeningData}
            analyzeWithStockfish={analyzeWithStockfish}
            llmLoading={llmLoading}
            stockfishLoading={stockfishLoading}
            stockfishAnalysisResult={stockfishAnalysisResult}
            openingLoading={openingLoading}
          />
        </Box>

        <Box sx={{ flex: 1, minWidth: 0, maxWidth: "100%" }}>
          <ChessterAnalysisView
            isGameReviewMode={false}
            stockfishAnalysisResult={stockfishAnalysisResult}
            stockfishLoading={stockfishLoading}
            handleEngineLineClick={handleEngineLineClick}
            engineDepth={engineDepth}
            fen={fen}
            engineLines={engineLines}
            engine={engine}
            analyzeWithStockfish={analyzeWithStockfish}
            formatEvaluation={formatEvaluation}
            formatPrincipalVariation={formatPrincipalVariation}
            setEngineDepth={setEngineDepth}
            setEngineLines={setEngineLines}
            openingLoading={openingLoading}
            openingData={openingData}
            lichessOpeningData={lichessOpeningData}
            lichessOpeningLoading={lichessOpeningLoading}
            handleOpeningMoveClick={handleOpeningMoveClick}
            chessdbdata={chessdbdata}
            handleMoveClick={handleMoveClick}
            queueing={queueing}
            error={error}
            loading={loading}
            refetch={refetch}
            requestAnalysis={requestAnalysis}
            legalMoves={legalMoves}
            handleFutureMoveLegalClick={handleFutureMoveLegalClick}
            chatMessages={chatMessages}
            chatInput={chatInput}
            setChatInput={setChatInput}
            sendChatMessage={sendChatMessage}
            chatLoading={chatLoading}
            abortChatMessage={abortChatMessage}
            handleChatKeyPress={handleChatKeyPress}
            clearChatHistory={clearChatHistory}
            sessionMode={sessionMode}
            gameReviewTheme={null}
            setSessionMode={setSessionMode}
            llmLoading={llmLoading}
          />
        </Box>
      </Stack>
      </Box>
    </Box>
  );
}
