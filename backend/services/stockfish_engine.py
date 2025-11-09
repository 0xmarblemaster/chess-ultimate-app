import os
import chess
import chess.engine
import logging
import concurrent.futures
import time

class StockfishEngine:
    def __init__(self, path=None, depth=15):
        self.logger = logging.getLogger(__name__)
        self.path = path or os.getenv("STOCKFISH_PATH") or "/usr/local/bin/stockfish"
        self.depth = depth
        self.engine = None
        self.current_board = chess.Board()  # Default to starting position
        self._init_engine()

    def _init_engine(self):
        try:
            self.logger.info(f"Initializing Stockfish engine at: {self.path}")
            self.engine = chess.engine.SimpleEngine.popen_uci(self.path)
            self.logger.info("Stockfish engine initialized successfully.")
            if self.engine and self.engine.id:
                self.logger.info(f"Using Stockfish version: {self.engine.id.get('name', 'unknown')}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Stockfish: {e}")
            self.engine = None

    def set_fen_position(self, fen):
        """
        Set the current position for analysis.
        
        Args:
            fen: FEN string representing the position
            
        Returns:
            True if position was set successfully, False otherwise
        """
        try:
            self.current_board = chess.Board(fen)
            self.logger.info(f"Position set to FEN: {fen}")
            return True
        except ValueError as e:
            self.logger.error(f"Invalid FEN: {fen}. Error: {e}")
            return False

    def analyze_current_position(self, depth_limit=15, time_limit=None, multipv=1):
        """
        Analyze the current board position.
        
        Args:
            depth_limit: Maximum depth to search
            time_limit: Maximum time in seconds to search
            multipv: Number of principal variations to calculate
            
        Returns:
            List of analysis results or None if analysis fails
        """
        try:
            self.logger.info(f"Analyzing current position: {self.current_board.fen()}")
            result = self.analyze_fen(
                self.current_board.fen(),
                depth_limit=depth_limit,
                time_limit=time_limit,
                multipv=multipv
            )
            self.logger.info(f"Analysis complete: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error analyzing current position: {str(e)}")
            return None

    def analyze_fen(self, fen, time_limit=None, multipv=1, depth_limit=None):
        """
        Analyze a chess position and return evaluation lines.
        
        Args:
            fen: The FEN string representing the position to analyze
            time_limit: Time in seconds to spend on analysis (used as a manual timeout)
            multipv: Number of principal variations to calculate
            depth_limit: Maximum depth to search
            
        Returns:
            List of analysis results or None if analysis fails
        """
        if self.engine is None:
            self.logger.warning("Stockfish engine not initialized. Attempting to reinitialize.")
            self._init_engine()
            if self.engine is None:
                self.logger.error("Stockfish engine could not be initialized.")
                return None
        
        try:
            board = chess.Board(fen)
        except ValueError as e:
            self.logger.error(f"Invalid FEN: {fen}. Error: {e}")
            return None
        
        # Configure limit parameters
        limit_args = {}
        if depth_limit is not None:
            limit_args['depth'] = depth_limit
        else:
            # Default to depth 18 if no specific limits (increased from 12)
            limit_args['depth'] = 18
            
        limit = chess.engine.Limit(**limit_args)
        analysis_results = []
        
        # Determine max analysis time (either from time_limit parameter or default)
        max_analysis_time = 15.0  # Default timeout in seconds (increased from 10.0)
        if time_limit is not None and time_limit > 0:
            max_analysis_time = time_limit
            
        try:
            pv_infos = [None] * multipv
            with self.engine.analysis(board, limit, multipv=multipv) as analysis:
                start_time = time.time()
                for info in analysis:
                    # Manual timeout handling
                    if time.time() - start_time > max_analysis_time:
                        self.logger.info(f"Manual timeout reached after {max_analysis_time}s")
                        analysis.stop()
                        break
                    
                    if "multipv" in info:
                        idx = info["multipv"] - 1
                        if 0 <= idx < multipv:
                            pv_infos[idx] = info
            
            # Process analysis results
            for idx, info in enumerate(pv_infos):
                if info is None:
                    continue
                score_wdl = info.get("score")
                pv_moves = info.get("pv", [])
                depth = info.get("depth", 0)
                if not pv_moves:
                    continue
                pv_san_list = []
                temp_board = board.copy()
                for move in pv_moves:
                    try:
                        san = temp_board.san(move)
                        pv_san_list.append(san)
                        temp_board.push(move)
                    except ValueError as e:
                        self.logger.error(f"Error converting move {move} to SAN: {e}")
                        break

                # Limit number of moves shown (to reduce UI clutter)
                max_moves_to_show = min(10, len(pv_moves))  # Changed from 9 to 10 for exactly 5 full moves
                pv_san_list = pv_san_list[:max_moves_to_show]
                pv_san = " ".join(pv_san_list)
                evaluation_numerical = 0.0
                evaluation_string = "0.00"
                mate_in = None
                if score_wdl:
                    if score_wdl.is_mate():
                        mate_in_val = score_wdl.relative.mate()
                        mate_in = mate_in_val
                        evaluation_string = f"M{abs(mate_in_val)}"
                        # Use large finite numbers instead of infinity to avoid JSON serialization issues
                        evaluation_numerical = 999.99 if mate_in_val > 0 else -999.99
                    else:
                        cp_score = score_wdl.relative.cp
                        if cp_score is not None:
                            evaluation_numerical = cp_score / 100.0
                            evaluation_string = f"{evaluation_numerical:+.2f}"
                analysis_results.append({
                    "line_number": idx + 1,
                    "pv_san": pv_san,
                    "evaluation_numerical": evaluation_numerical,
                    "evaluation_string": evaluation_string,
                    "mate_in": mate_in,
                    "depth": depth,
                    "bestmove": pv_san_list[0] if pv_san_list else None,
                    "score": evaluation_numerical,
                })
        except (chess.engine.EngineError, concurrent.futures.TimeoutError, concurrent.futures.CancelledError) as e:
            self.logger.error(f"Stockfish engine error or timeout during analysis: {e}")
            # Attempt to reinitialize the engine after an error
            self._init_engine()
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
            return None
            
        # Return empty list instead of None if we got no results but didn't encounter errors
        if not analysis_results and multipv > 0:
            self.logger.warning(f"Analysis for FEN: {fen} yielded no lines (expected {multipv}).")
            return []
            
        return analysis_results

    def healthcheck(self):
        try:
            board = chess.Board()  # startpos
            move = self.engine.play(board, chess.engine.Limit(depth=1)).move
            return move is not None
        except Exception as e:
            self.logger.error(f"Stockfish healthcheck failed: {e}")
            return False

    def quit(self):
        if self.engine:
            try:
                self.engine.quit()
                self.logger.info("Stockfish engine quit successfully.")
            except Exception as e:
                self.logger.error(f"Error quitting Stockfish engine: {e}")
            finally:
                self.engine = None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = StockfishEngine()
    print("Healthcheck:", engine.healthcheck())
    test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    print(f"Analyzing FEN: {test_fen}")
    result = engine.analyze_fen(test_fen, time_limit=0.5, multipv=3)
    if result:
        for line in result:
            print(line)
    else:
        print("Analysis failed.")
    engine.quit()

# Global instance for use by other modules
stockfish_engine_instance = StockfishEngine() 