"""Mock emir yürütücü (simülatör) birim testleri."""

import unittest

from bistrobot.execution.executor import OrderSide, OrderStatus, PriceType
from bistrobot.execution.mock_executor import MockOrderExecutor


class TestMockExecutor(unittest.TestCase):
    def setUp(self):
        self.ex = MockOrderExecutor(commission_pct=0.0)

    def test_create_and_fill(self):
        order = self.ex.create_order("AKBNK.E", OrderSide.BUY, 100,
                                     PriceType.MARKET, price=50.0,
                                     stop_loss=48.0, take_profit=54.0)
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(order.filled_price, 50.0)
        self.assertEqual(len(self.ex.get_positions()), 1)

    def test_reject_zero_qty(self):
        order = self.ex.create_order("AKBNK.E", OrderSide.BUY, 0,
                                     PriceType.MARKET, price=50.0)
        self.assertEqual(order.status, OrderStatus.REJECTED)
        self.assertEqual(len(self.ex.get_positions()), 0)

    def test_take_profit_trigger(self):
        self.ex.create_order("THYAO.E", OrderSide.BUY, 100, PriceType.MARKET,
                             price=100.0, stop_loss=95.0, take_profit=110.0)
        # Fiyat TP'ye ulaşınca pozisyon kapanmalı.
        self.ex.mark_price("THYAO.E", 110.0)
        self.assertEqual(len(self.ex.get_positions()), 0)
        # K/Z = (110-100)*100 = 1000.
        self.assertAlmostEqual(self.ex.realized_pnl, 1000.0)
        self.assertEqual(len(self.ex.closed_trades), 1)

    def test_stop_loss_trigger(self):
        self.ex.create_order("GARAN.E", OrderSide.BUY, 100, PriceType.MARKET,
                             price=100.0, stop_loss=95.0, take_profit=110.0)
        self.ex.mark_price("GARAN.E", 95.0)
        self.assertEqual(len(self.ex.get_positions()), 0)
        self.assertAlmostEqual(self.ex.realized_pnl, -500.0)  # (95-100)*100

    def test_opposite_order_closes(self):
        self.ex.create_order("ASELS.E", OrderSide.BUY, 100, PriceType.MARKET,
                             price=100.0)
        # Karşı (SELL) emir → kapatır.
        self.ex.create_order("ASELS.E", OrderSide.SELL, 100, PriceType.MARKET,
                             price=105.0)
        self.assertEqual(len(self.ex.get_positions()), 0)
        self.assertAlmostEqual(self.ex.realized_pnl, 500.0)

    def test_cancel_order(self):
        order = self.ex.create_order("AKBNK.E", OrderSide.BUY, 100,
                                     PriceType.MARKET, price=50.0)
        # FILLED emir iptal edilemez.
        self.assertFalse(self.ex.cancel_order(order.order_id))
        self.assertFalse(self.ex.cancel_order("YOK-123"))

    def test_commission_applied(self):
        ex = MockOrderExecutor(commission_pct=0.1)  # %0.1
        ex.create_order("AKBNK.E", OrderSide.BUY, 100, PriceType.MARKET,
                        price=100.0)  # nominal 10.000 → komisyon 10
        self.assertAlmostEqual(ex.commission_paid, 10.0)

    def test_on_close_callback(self):
        captured = {}
        ex = MockOrderExecutor(on_close=lambda pnl, ts: captured.update(pnl=pnl))
        ex.create_order("AKBNK.E", OrderSide.BUY, 10, PriceType.MARKET,
                        price=100.0, stop_loss=90.0, take_profit=120.0)
        ex.mark_price("AKBNK.E", 120.0)
        self.assertIn("pnl", captured)
        self.assertAlmostEqual(captured["pnl"], 200.0)  # (120-100)*10


if __name__ == "__main__":
    unittest.main()
