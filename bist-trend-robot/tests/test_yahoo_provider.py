"""
Yahoo veri sağlayıcı birim testleri.

Ağ erişimi GEREKTİRMEZ: HTTP katmanı (`_http_get`) sahte bir yanıtla
değiştirilir; böylece sembol eşleme, JSON ayrıştırma ve "tamamlanmış mum"
filtresi deterministik olarak test edilir.
"""

import time
import unittest

from bistrobot.data.yahoo_provider import YahooDataProvider


def _fake_payload(base_ts: int, interval_sec: int, n: int, include_forming: bool):
    """n adet tamamlanmış + (opsiyonel) 1 oluşmakta olan bar üretir."""
    timestamps, opens, highs, lows, closes, volumes = [], [], [], [], [], []
    for i in range(n):
        timestamps.append(base_ts + i * interval_sec)
        price = 100.0 + i
        opens.append(price); highs.append(price + 1)
        lows.append(price - 1); closes.append(price + 0.5)
        volumes.append(1000 + i)
    # Bir null bar (işlemsiz dönem) — atlanmalı.
    timestamps.insert(2, base_ts + 2 * interval_sec - 1)
    for arr in (opens, highs, lows, closes, volumes):
        arr.insert(2, None)
    if include_forming:
        # Geleceğe taşan (henüz kapanmamış) bar — filtrelenmeli.
        timestamps.append(int(time.time()) + interval_sec)
        opens.append(999); highs.append(1000); lows.append(998)
        closes.append(999.5); volumes.append(5)
    return {
        "chart": {"error": None, "result": [{
            "timestamp": timestamps,
            "indicators": {"quote": [{
                "open": opens, "high": highs, "low": lows,
                "close": closes, "volume": volumes,
            }]},
        }]}
    }


class TestSymbolMapping(unittest.TestCase):
    def setUp(self):
        self.p = YahooDataProvider()

    def test_dot_e_suffix(self):
        self.assertEqual(self.p.to_yahoo_symbol("AKBNK.E"), "AKBNK.IS")

    def test_plain_symbol(self):
        self.assertEqual(self.p.to_yahoo_symbol("thyao"), "THYAO.IS")

    def test_already_is(self):
        self.assertEqual(self.p.to_yahoo_symbol("GARAN.IS"), "GARAN.IS")

    def test_other_market_suffix(self):
        self.assertEqual(self.p.to_yahoo_symbol("ASELS.F"), "ASELS.IS")


class TestParsingAndFilters(unittest.TestCase):
    def setUp(self):
        # Ağ çağrısını sahteleyerek deterministik veri ver.
        self.p = YahooDataProvider(sleeper=lambda _s: None)
        # Tamamlanmış barlar geçmişte olsun.
        base = int(time.time()) - 100 * 3600
        self._payload = _fake_payload(base, 3600, n=10, include_forming=True)
        self.p._http_get = lambda url: self._payload  # type: ignore

    def test_filters_null_and_forming(self):
        candles = self.p.get_historical_candles("AKBNK.E", "1h", limit=50)
        # 10 tamamlanmış bar; null bar ve oluşmakta olan bar atlanmalı.
        self.assertEqual(len(candles), 10)
        # Sembol orijinal BIST formatında korunur.
        self.assertEqual(candles[0].symbol, "AKBNK.E")
        # OHLC tutarlılığı.
        self.assertTrue(all(c.high >= c.low for c in candles))

    def test_limit_slicing(self):
        candles = self.p.get_historical_candles("AKBNK.E", "1h", limit=3)
        self.assertEqual(len(candles), 3)

    def test_latest_candle_is_completed(self):
        latest = self.p.get_latest_candle("AKBNK.E", "1h")
        # En güncel TAMAMLANMIŞ bar dönmeli (gelecekteki bar değil).
        self.assertLess(latest.timestamp.timestamp() if hasattr(latest.timestamp, "timestamp")
                        else 0, time.time() + 1)

    def test_invalid_timeframe(self):
        with self.assertRaises(ValueError):
            self.p.get_historical_candles("AKBNK.E", "3h", limit=10)

    def test_yahoo_error_raises(self):
        self.p._http_get = lambda url: {"chart": {"error": "Not Found", "result": None}}  # type: ignore
        with self.assertRaises(RuntimeError):
            self.p.get_latest_candle("YOKKK.E", "1h")

    def test_retry_then_success(self):
        calls = {"n": 0}

        def flaky(url):
            calls["n"] += 1
            if calls["n"] < 3:
                raise OSError("geçici ağ hatası")
            return self._payload

        self.p._http_get = flaky  # type: ignore
        candles = self.p.get_historical_candles("AKBNK.E", "1h", limit=50)
        self.assertEqual(calls["n"], 3)  # 2 hata + 1 başarı
        self.assertEqual(len(candles), 10)


if __name__ == "__main__":
    unittest.main()
