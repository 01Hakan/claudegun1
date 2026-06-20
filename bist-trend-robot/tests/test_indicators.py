"""İndikatör birim testleri (SMA, EMA, RSI, MACD, ATR)."""

import unittest

from bistrobot.strategy import indicators as ind


class TestIndicators(unittest.TestCase):
    def test_sma_basic(self):
        vals = [1, 2, 3, 4, 5]
        out = ind.sma(vals, 3)
        # İlk iki değer None, sonra ortalamalar.
        self.assertEqual(out[:2], [None, None])
        self.assertAlmostEqual(out[2], 2.0)
        self.assertAlmostEqual(out[3], 3.0)
        self.assertAlmostEqual(out[4], 4.0)

    def test_sma_invalid_period(self):
        with self.assertRaises(ValueError):
            ind.sma([1, 2, 3], 0)

    def test_ema_length_and_seed(self):
        vals = [float(x) for x in range(1, 21)]
        out = ind.ema(vals, 5)
        self.assertEqual(len(out), len(vals))
        # period-1 indeksine kadar None.
        self.assertTrue(all(o is None for o in out[:4]))
        # Seed = ilk 5 elemanın SMA'sı = 3.0
        self.assertAlmostEqual(out[4], 3.0)
        # EMA monoton artan seri için artmalı.
        self.assertGreater(out[-1], out[5])

    def test_rsi_bounds(self):
        # Sürekli artan seri → RSI 100'e yakın olmalı.
        rising = [float(x) for x in range(1, 40)]
        out = ind.rsi(rising, 14)
        last = out[-1]
        self.assertIsNotNone(last)
        self.assertGreater(last, 95.0)
        self.assertLessEqual(last, 100.0)

        # Sürekli düşen seri → RSI 0'a yakın.
        falling = list(reversed(rising))
        out2 = ind.rsi(falling, 14)
        self.assertLess(out2[-1], 5.0)

    def test_macd_components(self):
        vals = [float(x) for x in range(1, 60)]
        macd_line, signal_line, hist = ind.macd(vals, 12, 26, 9)
        self.assertEqual(len(macd_line), len(vals))
        # Yükselen seride MACD pozitif olmalı.
        self.assertGreater(macd_line[-1], 0)
        # Histogram = macd - signal tutarlılığı.
        i = len(vals) - 1
        self.assertAlmostEqual(hist[i], macd_line[i] - signal_line[i], places=6)

    def test_atr_positive(self):
        highs = [10 + i for i in range(30)]
        lows = [8 + i for i in range(30)]
        closes = [9 + i for i in range(30)]
        out = ind.atr(highs, lows, closes, 14)
        self.assertEqual(len(out), 30)
        self.assertIsNotNone(out[-1])
        self.assertGreater(out[-1], 0)

    def test_atr_length_mismatch(self):
        with self.assertRaises(ValueError):
            ind.atr([1, 2], [1], [1, 2], 1)


if __name__ == "__main__":
    unittest.main()
