import unittest
from stockfish_engine import StockfishEngine

class TestStockfishEngine(unittest.TestCase):
    def setUp(self):
        self.engine = StockfishEngine()

    def tearDown(self):
        self.engine.quit()

    def test_healthcheck(self):
        self.assertTrue(self.engine.healthcheck(), "Stockfish healthcheck should return True.")

    def test_analyze_fen(self):
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = self.engine.analyze_fen(test_fen, time_limit=0.5, multipv=2)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        self.assertIn("pv_san", result[0])
        self.assertIn("evaluation_string", result[0])

if __name__ == "__main__":
    unittest.main() 