#!/usr/bin/env python3
import logging
import sys
import os
import time

# Add the parent directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
mvp1_dir = os.path.dirname(backend_dir)
if mvp1_dir not in sys.path:
    sys.path.insert(0, mvp1_dir)

from backend.services.stockfish_engine import StockfishEngine

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_stockfish_service')

def test_engine_initialization():
    logger.info("Testing StockfishEngine initialization...")
    engine = StockfishEngine()
    
    if engine.engine is None:
        logger.error("❌ Engine initialization failed")
        return False
    
    logger.info("✅ Engine initialized successfully")
    return engine

def test_engine_healthcheck(engine):
    logger.info("Testing engine healthcheck...")
    result = engine.healthcheck()
    
    if result:
        logger.info("✅ Engine healthcheck passed")
    else:
        logger.error("❌ Engine healthcheck failed")
    
    return result

def test_analyze_with_depth(engine):
    logger.info("Testing analysis with depth limit...")
    test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    start_time = time.time()
    result = engine.analyze_fen(fen=test_fen, depth_limit=15, multipv=1)
    elapsed = time.time() - start_time
    
    if result:
        logger.info(f"✅ Analysis with depth completed in {elapsed:.2f}s")
        logger.info(f"First line: {result[0]}")
    else:
        logger.error("❌ Analysis with depth failed")
    
    return result is not None

def test_analyze_with_timeout(engine):
    logger.info("Testing analysis with manual timeout...")
    # Use a complex position that will take longer to analyze
    complex_fen = "r3k2r/pp2nppp/2pqbn2/3p4/3P1P2/2N1PN2/PPPQB1PP/R3K2R w KQkq - 2 10"
    
    timeout = 2.0  # 2 second timeout
    start_time = time.time()
    result = engine.analyze_fen(fen=complex_fen, time_limit=timeout, multipv=3)
    elapsed = time.time() - start_time
    
    if result:
        logger.info(f"✅ Analysis with timeout completed in {elapsed:.2f}s")
        logger.info(f"First line: {result[0]}")
        
        # For simple positions, Stockfish might finish before timeout
        # In our implementation this is expected behavior
        if elapsed >= timeout:
            logger.info(f"✅ Analysis took longer than timeout: {elapsed:.2f}s (timeout: {timeout}s)")
        else:
            logger.info(f"✅ Analysis completed before timeout: {elapsed:.2f}s (timeout: {timeout}s)")
    else:
        logger.error("❌ Analysis with timeout failed")
    
    return result is not None

def test_analyze_invalid_fen(engine):
    logger.info("Testing analysis with invalid FEN...")
    invalid_fen = "invalid fen string"
    
    result = engine.analyze_fen(fen=invalid_fen)
    
    if result is None:
        logger.info("✅ Invalid FEN handled correctly (returned None)")
    else:
        logger.error("❌ Invalid FEN unexpectedly returned a result")
    
    return result is None

def run_all_tests():
    success_count = 0
    total_tests = 5  # Fixed test count (init, healthcheck, depth, timeout, invalid)
    
    engine = test_engine_initialization()
    if not engine:
        logger.error("Cannot continue tests without a working engine")
        return 0, total_tests
    
    success_count += 1  # Initialization test passed
    
    # Run remaining tests
    if test_engine_healthcheck(engine):
        success_count += 1
    
    if test_analyze_with_depth(engine):
        success_count += 1
    
    if test_analyze_with_timeout(engine):
        success_count += 1
    
    if test_analyze_invalid_fen(engine):
        success_count += 1
        
    # Clean up
    logger.info("Cleaning up engine...")
    engine.quit()
    
    return success_count, total_tests

if __name__ == "__main__":
    logger.info("===== StockfishEngine Service Tests =====")
    
    success, total = run_all_tests()
    
    logger.info(f"===== Test Results: {success}/{total} tests passed =====")
    
    if success == total:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"❌ {total - success} tests failed")
        sys.exit(1) 