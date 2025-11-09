import chess
import chess.engine
import os
import logging
import threading 
# from backend.services.stockfish_engine import StockfishEngine  # Commented out - module doesn't exist

logger = logging.getLogger(__name__)

STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")
engine: chess.engine.SimpleEngine | None = None
stockfish_analysis_lock = threading.Lock()
# stockfish_service = StockfishEngine()  # Commented out - module doesn't exist

def _create_cache_key(fen_string: str, time_limit: float | None, multipv: int, depth_limit: int | None) -> str:
    """Create a consistent cache key for Stockfish analysis parameters"""
    return f"{fen_string}_{time_limit}_{multipv}_{depth_limit}"

def init_stockfish(force_reinit=False):
    global engine, STOCKFISH_PATH
    if engine is not None and not force_reinit:
        logger.info("Stockfish engine already initialized.")
        return True

    if engine is not None and force_reinit:
        logger.info("Forcing reinitialization of Stockfish engine.")
        quit_stockfish()

    if not STOCKFISH_PATH:
        logger.warning("STOCKFISH_PATH environment variable is not set. Attempting to use default 'stockfish' from PATH.")
        STOCKFISH_PATH = "stockfish"

    try:
        logger.info(f"Attempting to initialize Stockfish engine from: {STOCKFISH_PATH}")
        # Added setpgrp=True for better process management on Unix-like systems
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH, setpgrp=True) 
        logger.info("Stockfish engine initialized successfully.")
        return True
    except FileNotFoundError:
        logger.error(f"Stockfish executable not found at {STOCKFISH_PATH}.")
        engine = None
        return False
    except chess.engine.EngineTerminatedError as e:
        logger.error(f"Stockfish engine terminated unexpectedly during initialization: {e}")
        engine = None
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during Stockfish initialization: {e}")
        engine = None
        return False

def quit_stockfish():
    global engine
    if engine:
        try:
            logger.info("Attempting to quit Stockfish engine.")
            engine.quit()
            logger.info("Stockfish engine quit successfully.")
        except chess.engine.EngineTerminatedError:
            logger.warning("Stockfish engine was already terminated.")
        except Exception as e:
            logger.error(f"Error quitting Stockfish engine: {e}")
        finally:
            engine = None
    else:
        logger.info("Stockfish engine was not running.")

def analyze_fen_with_stockfish(
    fen_string: str, 
    time_limit: float | None = None,
    multipv: int = 1, 
    depth_limit: int | None = None
) -> list[dict] | None:
    """
    Analyze FEN with Stockfish engine (now with caching)
    
    Args:
        fen_string: The FEN string to analyze
        time_limit: Time limit in seconds for analysis
        multipv: Number of principal variations to return
        depth_limit: Maximum depth to search
        
    Returns:
        List of analysis results or None if analysis fails
    """
    global engine
    
    # Import cache locally to avoid circular imports
    try:
        from etl.agents.cache_manager import stockfish_cache
    except ImportError:
        # Fallback if cache is not available
        stockfish_cache = None
    
    # Check cache first
    if stockfish_cache:
        cached_result = stockfish_cache.get(
            fen_string, 
            time_limit=time_limit, 
            multipv=multipv, 
            depth_limit=depth_limit
        )
        if cached_result is not None:
            logger.debug(f"Returning cached analysis for FEN: {fen_string[:30]}...")
            return cached_result

    if engine is None:
        logger.warning("Stockfish engine not initialized. Attempting to initialize now.")
        if not init_stockfish():
            logger.error("Failed to initialize Stockfish for analysis.")
            return None
        elif engine is None: 
            logger.error("Engine is still None after init_stockfish attempt.")
            return None

    try:
        board = chess.Board(fen_string)
    except ValueError as e:
        logger.error(f"Invalid FEN: '{fen_string}'. Error: {e}")
        return None

    limit_args = {}
    if depth_limit is not None:
        limit_args['depth'] = depth_limit
    elif time_limit is not None and time_limit > 0:
        limit_args['time'] = time_limit
    if not limit_args: # No effective limits were set
        logger.debug(f"No time/depth limit specified for FEN: {fen_string}. Applying default fallback.")
        limit_args['depth'] = 12  # Fallback to depth 12 if nothing specified

    limit = chess.engine.Limit(**limit_args)
    analysis_results = []

    logger.debug(f"Acquiring analysis lock for FEN: {fen_string} with limit {limit_args}")
    print(f"[DEBUG] Stockfish analysis limit_args: {limit_args}", flush=True)
    with stockfish_analysis_lock:
        logger.debug(f"Lock acquired. Analyzing FEN: {fen_string}")
        try:
            logger.info(f"Engine object type before calling position: {type(engine)}")
            logger.info(f"Engine object attributes: {dir(engine)}")
            pv_infos = [None] * multipv
            with engine.analysis(board, limit, multipv=multipv) as analysis:
                for info in analysis:
                    if "multipv" in info:
                        idx = info["multipv"] - 1
                        if 0 <= idx < multipv:
                            pv_infos[idx] = info
            for idx, info in enumerate(pv_infos):
                if info is None:
                    continue
                score_wdl = info.get("score")
                pv_moves = info.get("pv", [])
                depth = info.get("depth", 0)
                print(f"[DEBUG] PV {idx+1}: depth={depth}, pv_moves={len(pv_moves)}, pv={pv_moves}", flush=True)

                if not pv_moves:
                    continue

                # Convert PV (principal variation) moves to SAN
                pv_san_list = []
                temp_board = board.copy()
                for move in pv_moves:
                    try:
                        san = temp_board.san(move)
                        pv_san_list.append(san)
                        temp_board.push(move)
                    except Exception as e:
                        logger.error(f"Error converting move {move} to SAN: {e}")
                        break

                # Limit PV to 9 half-moves to keep UI clean
                max_moves_to_show = min(9, len(pv_moves))
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
                })
        except chess.engine.EngineError as e:
            logger.error(f"Stockfish engine error for FEN '{fen_string}': {e}")
            if "pipe" in str(e).lower() or "died" in str(e).lower(): # More general check
                logger.warning("Attempting to re-initialize Stockfish due to critical error.")
                init_stockfish(force_reinit=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during analysis for FEN '{fen_string}': {e}", exc_info=True)
            return None
        finally:
            logger.debug(f"Released analysis lock for FEN: {fen_string}.")

    if not analysis_results and multipv > 0:
        logger.warning(f"Analysis for FEN: {fen_string} yielded no lines (expected {multipv}).")
        result = []
    else:
        result = analysis_results
    
    # Cache the result before returning
    if stockfish_cache:
        stockfish_cache.set(
            fen_string, 
            result, 
            time_limit=time_limit, 
            multipv=multipv, 
            depth_limit=depth_limit
        )
    
    return result

def analyze_fen_with_stockfish_service(
    fen_string: str,
    time_limit: float | None = None,
    multipv: int = 1,
    depth_limit: int | None = None
) -> list[dict] | None:
    """
    Uses the new modular StockfishEngine service for analysis (now with caching).
    This is a drop-in alternative to analyze_fen_with_stockfish.
    
    Args:
        fen_string: The FEN string representing the position to analyze
        time_limit: Time in seconds to spend on analysis (used as a manual timeout)
        multipv: Number of principal variations to calculate
        depth_limit: Maximum depth to search
        
    Returns:
        List of analysis results or None if analysis fails
    """
    logger.info("[StockfishAnalyzer] Using StockfishEngine service for FEN analysis.")
    
    # Import cache locally to avoid circular imports
    try:
        from etl.agents.cache_manager import stockfish_cache
    except ImportError:
        # Fallback if cache is not available
        stockfish_cache = None
    
    # Check cache first
    if stockfish_cache:
        cached_result = stockfish_cache.get(
            fen_string, 
            time_limit=time_limit, 
            multipv=multipv, 
            depth_limit=depth_limit
        )
        if cached_result is not None:
            logger.debug(f"Returning cached analysis for FEN: {fen_string[:30]}...")
            return cached_result
    
    # If not in cache, perform analysis using the service
    try:
        result = analyze_fen_with_stockfish(
            fen_string=fen_string,
            time_limit=time_limit,
            multipv=multipv,
            depth_limit=depth_limit
        )
        
        # Cache the result
        if stockfish_cache:
            stockfish_cache.set(
                fen_string, 
                result, 
                time_limit=time_limit, 
                multipv=multipv, 
                depth_limit=depth_limit
            )
        
        return result
        
    except Exception as e:
        logger.error(f"StockfishEngine service error for FEN '{fen_string}': {e}")
        return None

# Initialize the engine when the module is loaded.
# This ensures 'engine' is available for analyze_fen_with_stockfish
# However, consider lazy initialization if the module might be imported
# in contexts where the engine isn't immediately needed or might fail.
# For this application, eager initialization is probably fine.
# Ensure the global engine is None before the first call to allow the lazy check in analyze_fen_with_stockfish to work as intended for the first call.
# However, init_stockfish() at module level is fine if it correctly handles not re-creating if one exists.
# Let's rely on the check within analyze_fen_with_stockfish or app.py ensuring it's called.
# init_stockfish() # Let's comment this out to ensure the first call comes from analysis or app startup.

if __name__ == '__main__':
    # Example Usage:
    test_fen_initial = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    test_fen_mate = "4k3/7R/3KN3/8/8/8/8/8 w - - 0 1" # Mate in 1 (Re7# or Rd8# or Rh8#)
    
    print(f"--- Testing analysis for: {test_fen_initial} ---")
    analysis1 = analyze_fen_with_stockfish(test_fen_initial, time_limit=0.5, multipv=3)
    if analysis1:
        for line in analysis1:
            print(line)
    else:
        print("Analysis failed for initial position.")

    print(f"\n--- Testing analysis for: {test_fen_mate} ---")
    analysis2 = analyze_fen_with_stockfish(test_fen_mate, time_limit=0.5, multipv=3)
    if analysis2:
        for line in analysis2:
            print(line)
    else:
        print("Analysis failed for mate position.")

    # Test re-initialization (optional)
    # print("\n--- Testing re-initialization ---")
    # if init_stockfish(force_reinit=True):
    #     analysis3 = analyze_fen_with_stockfish(test_fen_initial, time_limit=0.1, multipv=1)
    #     if analysis3:
    #         print(analysis3[0])
    # else:
    #     print("Re-initialization failed.")
        
    quit_stockfish() 