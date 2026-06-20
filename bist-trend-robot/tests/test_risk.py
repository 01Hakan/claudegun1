"""Risk yönetimi ve pozisyon boyutu birim testleri."""

import unittest
from datetime import date

from bistrobot.risk.manager import RiskManager, RiskParams, position_size


class TestPositionSize(unittest.TestCase):
    def test_basic_sizing(self):
        # 100.000 bakiye, %1 risk = 1.000 TL risk; stop mesafesi 2 TL → 500 adet.
        qty = position_size(100_000, stop_distance=2.0, risk_pct=1.0)
        self.assertEqual(qty, 500)

    def test_affordability_cap(self):
        # Risk 1.000 TL / 0.10 stop = 10.000 adet ister; ama fiyat 50 TL.
        # 100.000 / 50 = 2.000 adet ile sınırlı (kaldıraçsız spot).
        qty = position_size(100_000, stop_distance=0.10, risk_pct=1.0, price=50.0)
        self.assertEqual(qty, 2_000)

    def test_invalid_inputs(self):
        self.assertEqual(position_size(0, 2.0, 1.0), 0)
        self.assertEqual(position_size(100_000, 0, 1.0), 0)
        self.assertEqual(position_size(100_000, 2.0, 0), 0)

    def test_floor_rounding(self):
        # 1.000 / 3 = 333.33 → 333 (aşağı yuvarlama).
        qty = position_size(100_000, stop_distance=3.0, risk_pct=1.0)
        self.assertEqual(qty, 333)


class TestRiskManager(unittest.TestCase):
    def setUp(self):
        self.params = RiskParams(account_balance=100_000, risk_per_trade_pct=1.0,
                                 daily_max_loss_pct=3.0, max_open_positions=2)
        self.rm = RiskManager(self.params)
        self.today = date(2024, 1, 2)

    def test_approve_normal(self):
        d = self.rm.evaluate(entry_price=100.0, stop_loss=98.0, today=self.today)
        self.assertTrue(d.approved)
        self.assertEqual(d.quantity, 500)  # 1000 risk / 2 stop

    def test_max_open_positions(self):
        self.rm.register_open()
        self.rm.register_open()
        d = self.rm.evaluate(100.0, 98.0, self.today)
        self.assertFalse(d.approved)
        self.assertIn("açık pozisyon", d.reason.lower())

    def test_daily_loss_limit(self):
        # Gün başı 100.000; %3 = 3.000 limit. 3.500 zarar yaz.
        self.rm._roll_day(self.today)
        self.rm.register_close(-3_500, self.today)
        self.assertTrue(self.rm.daily_loss_breached(self.today))
        d = self.rm.evaluate(100.0, 98.0, self.today)
        self.assertFalse(d.approved)
        self.assertIn("zarar", d.reason.lower())

    def test_invalid_stop_distance(self):
        d = self.rm.evaluate(100.0, 100.0, self.today)
        self.assertFalse(d.approved)

    def test_halt_blocks(self):
        self.rm.halt("test")
        d = self.rm.evaluate(100.0, 98.0, self.today)
        self.assertFalse(d.approved)
        self.rm.resume()
        self.assertTrue(self.rm.evaluate(100.0, 98.0, self.today).approved)

    def test_new_day_resets_loss(self):
        self.rm._roll_day(self.today)
        self.rm.register_close(-3_500, self.today)
        self.assertTrue(self.rm.daily_loss_breached(self.today))
        # Ertesi gün limit sıfırlanmalı.
        next_day = date(2024, 1, 3)
        self.assertFalse(self.rm.daily_loss_breached(next_day))


if __name__ == "__main__":
    unittest.main()
