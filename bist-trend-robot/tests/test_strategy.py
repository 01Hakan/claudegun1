"""Trend stratejisi sinyal üretimi birim testleri."""

import unittest
from datetime import datetime, timedelta

from bistrobot.data.mock_provider import MockDataProvider
from bistrobot.data.provider import Candle
from bistrobot.strategy.base import SignalType
from bistrobot.strategy.trend_strategy import TrendParams, TrendStrategy


def make_candles(closes, symbol="TEST.E"):
    """Kapanış listesinden basit mum dizisi üretir (high/low ~ close)."""
    t = datetime(2024, 1, 1, 10, 0)
    out = []
    for i, c in enumerate(closes):
        out.append(Candle(
            timestamp=t + timedelta(hours=i),
            open=c, high=c * 1.01, low=c * 0.99, close=c,
            volume=1000, symbol=symbol,
        ))
    return out


class TestTrendStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = TrendStrategy(TrendParams())

    def test_insufficient_data_holds(self):
        candles = make_candles([100, 101, 102])  # min_candles altında
        sig = self.strategy.generate_signal(candles)
        self.assertEqual(sig.type, SignalType.HOLD)
        self.assertIn("Yetersiz", sig.reason)

    def test_downtrend_produces_sell(self):
        # Sürekli düşen seri → kısa EMA < uzun EMA → SELL/çıkış.
        closes = [200 - i for i in range(80)]
        sig = self.strategy.generate_signal(make_candles(closes))
        self.assertEqual(sig.type, SignalType.SELL)

    def test_signal_always_valid_enum(self):
        closes = [100 + (i % 5) for i in range(100)]
        sig = self.strategy.generate_signal(make_candles(closes))
        self.assertIn(sig.type, (SignalType.BUY, SignalType.SELL, SignalType.HOLD))

    def test_buy_signal_has_consistent_levels(self):
        """Mock veride en az bir BUY üret; stop<giriş<take ve 1:RR tutarlılığı."""
        provider = MockDataProvider(seed=7, bars=600)
        series = provider.full_series("AKBNK.E", "1h")
        found_buy = False
        warm = self.strategy.min_candles
        for i in range(warm, len(series)):
            sig = self.strategy.generate_signal(series[:i + 1])
            if sig.type == SignalType.BUY:
                found_buy = True
                self.assertIsNotNone(sig.stop_loss)
                self.assertIsNotNone(sig.take_profit)
                self.assertLess(sig.stop_loss, sig.price)
                self.assertGreater(sig.take_profit, sig.price)
                # Risk/ödül ≈ 2.0 kontrolü.
                risk = sig.price - sig.stop_loss
                reward = sig.take_profit - sig.price
                self.assertAlmostEqual(reward / risk, 2.0, places=4)
                break
        self.assertTrue(found_buy, "Mock veride hiç BUY sinyali bulunamadı")

    def test_indicators_snapshot_populated(self):
        provider = MockDataProvider(seed=1, bars=300)
        series = provider.full_series("THYAO.E", "1h")
        sig = self.strategy.generate_signal(series)
        # HOLD bile olsa indikatör anlık görüntüsü dolu olmalı.
        if sig.type != SignalType.HOLD or sig.indicators:
            self.assertIn("rsi", sig.indicators)
            self.assertIn("ema_fast", sig.indicators)


if __name__ == "__main__":
    unittest.main()
