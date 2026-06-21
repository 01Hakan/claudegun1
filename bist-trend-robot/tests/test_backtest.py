"""Backtest motoru ve tek-gün işlem penceresi (trade_from_ts) testleri."""

import unittest
from datetime import datetime

from bistrobot.backtest.engine import Backtester
from bistrobot.data.mock_provider import MockDataProvider
from bistrobot.risk.manager import RiskParams
from bistrobot.strategy.trend_strategy import TrendParams, TrendStrategy


class TestBacktest(unittest.TestCase):
    def setUp(self):
        self.strategy = TrendStrategy(TrendParams())
        self.risk = RiskParams(account_balance=100_000)
        provider = MockDataProvider(seed=42, bars=600)
        self.data = {"AKBNK.E": provider.full_series("AKBNK.E", "1h")}

    def test_full_run_produces_result(self):
        bt = Backtester(self.strategy, self.risk, commission_pct=0.0)
        result = bt.run(self.data)
        self.assertEqual(result.initial_balance, 100_000)
        self.assertGreater(result.num_trades, 0)
        # Öz sermaye sayısal ve pozitif olmalı.
        self.assertGreater(result.final_equity, 0)
        # Kazanma oranı 0–100 aralığında.
        self.assertGreaterEqual(result.win_rate_pct, 0)
        self.assertLessEqual(result.win_rate_pct, 100)

    def test_trade_from_ts_limits_window(self):
        series = self.data["AKBNK.E"]
        # İşlem penceresini son ~%2'lik kısma kısıtla.
        cutoff = series[int(len(series) * 0.98)].timestamp

        bt_full = Backtester(self.strategy, self.risk)
        bt_window = Backtester(self.strategy, self.risk)
        full = bt_full.run(self.data)
        windowed = bt_window.run(self.data, trade_from_ts=cutoff)

        # Daraltılmış pencerede işlem sayısı tüm dönemden az olmalı.
        self.assertLess(windowed.num_trades, full.num_trades)

    def test_no_trades_when_window_after_data(self):
        # İşlem penceresi tüm verinin SONRASINDA → hiç pozisyon açılmamalı.
        future = datetime(2999, 1, 1)
        bt = Backtester(self.strategy, self.risk)
        result = bt.run(self.data, trade_from_ts=future)
        self.assertEqual(result.num_trades, 0)
        # Sermaye değişmemeli (işlem ve komisyon yok).
        self.assertAlmostEqual(result.final_equity, 100_000, places=2)


if __name__ == "__main__":
    unittest.main()
