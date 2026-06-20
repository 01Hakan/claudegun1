"""
Data Katmanı — Yahoo Finance Gerçek Veri Sağlayıcı
==================================================

``IDataProvider`` arayüzünün, Yahoo Finance'in herkese açık "chart" JSON
ucundan GERÇEK BIST mum verisi çeken implementasyonu.

Özellikler:
  - API anahtarı GEREKTİRMEZ, saf Python (urllib) — ek bağımlılık yok.
  - BIST sembol eşlemesi: "AKBNK.E" / "AKBNK"  →  "AKBNK.IS" (Yahoo formatı).
  - 1m/5m/15m/30m/1h/1d intraday mum desteği.
  - Yalnızca TAMAMLANMIŞ (kapanmış) mumları döndürür; oluşmakta olan
    (yarım) son mum filtrelenir — sinyal üretiminde look-ahead/yanıltıcı
    veri önlenir.
  - Üstel geri-çekilmeli (exponential backoff) yeniden deneme.

⚠️ NOT: Yahoo verisi resmî/garanti bir kaynak değildir; ücretsiz, gecikmeli
ve zaman zaman eksik olabilir. Eğitim/geliştirme ve backtest içindir. Canlı
emir için aracı kurumunuzun resmî veri akışını kullanın.

# >>> GERÇEK API ENTEGRASYON NOKTASI:
#     Emir gönderme için ayrıca IOrderExecutor'ı uygulayan bir broker sınıfı
#     gerekir; bu sınıf YALNIZCA veri sağlar (read-only).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable, List, Optional

from bistrobot.data.provider import Candle, IDataProvider
from bistrobot.logging_utils.logger import get_logger

log = get_logger("data.yahoo")

# Europe/Istanbul yerel saatine çevirmek için (BIST seans saatleri tutarlılığı).
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    _IST_TZ: Optional["ZoneInfo"] = ZoneInfo("Europe/Istanbul")
except Exception:  # zoneinfo/tzdata yoksa UTC'ye düş
    _IST_TZ = None

_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"

# Robot timeframe -> Yahoo interval eşlemesi.
_INTERVAL_MAP = {
    "1m": "1m", "2m": "2m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "60m", "60m": "60m", "90m": "90m", "1d": "1d", "1wk": "1wk",
}

# Interval -> saniye (mum süresi; tamamlanmışlık kontrolü için).
_INTERVAL_SECONDS = {
    "1m": 60, "2m": 120, "5m": 300, "15m": 900, "30m": 1800,
    "60m": 3600, "90m": 5400, "1d": 86400, "1wk": 604800,
}

# Interval -> yaklaşık BIST seans bar/gün (range hesabı için kaba tahmin).
# BIST pay piyasası ~ 10:00–18:00 (≈8 saat).
_BARS_PER_DAY = {
    "1m": 480, "2m": 240, "5m": 96, "15m": 32, "30m": 16,
    "60m": 8, "90m": 6, "1d": 1, "1wk": 0.2,
}

# Yahoo'nun intraday için izin verdiği yaklaşık maksimum geçmiş (gün).
_MAX_DAYS = {
    "1m": 7, "2m": 60, "5m": 60, "15m": 60, "30m": 60,
    "60m": 730, "90m": 60, "1d": 100000, "1wk": 100000,
}


class YahooDataProvider(IDataProvider):
    """Yahoo Finance tabanlı gerçek (read-only) veri sağlayıcı.

    Args:
        suffix: BIST sembolleri için Yahoo son eki (varsayılan ".IS").
        timeout: HTTP istek zaman aşımı (saniye).
        attempts: Hata durumunda maksimum deneme sayısı.
        base_delay: İlk geri-çekilme süresi (her denemede ikiye katlanır).
        sleeper: Bekleme fonksiyonu (test için enjekte edilebilir).
    """

    def __init__(self, suffix: str = ".IS", timeout: float = 10.0,
                 attempts: int = 4, base_delay: float = 2.0,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.suffix = suffix
        self.timeout = timeout
        self.attempts = attempts
        self.base_delay = base_delay
        self._sleep = sleeper

    # ----- Sembol eşleme ---------------------------------------------------
    def to_yahoo_symbol(self, symbol: str) -> str:
        """BIST sembolünü Yahoo formatına çevirir.

        Örnekler:
            "AKBNK.E" -> "AKBNK.IS"
            "AKBNK"   -> "AKBNK.IS"
            "THYAO.IS"-> "THYAO.IS"  (zaten Yahoo formatı)
        """
        s = symbol.strip().upper()
        if s.endswith(".IS"):
            return s
        # BIST pay piyasası son eki ".E" (Equity) -> at, yerine ".IS" koy.
        if s.endswith(".E"):
            s = s[:-2]
        elif "." in s:
            # Başka bir pazar son eki varsa (ör. .V, .F) sadece kökü al.
            s = s.split(".", 1)[0]
        return f"{s}{self.suffix}"

    # ----- IDataProvider implementasyonu -----------------------------------
    def get_historical_candles(self, symbol: str, timeframe: str,
                               limit: int) -> List[Candle]:
        interval = self._interval(timeframe)
        candles = self._fetch(symbol, interval, limit)
        # En yeni `limit` tamamlanmış mum.
        return candles[-limit:] if 0 < limit < len(candles) else candles

    def get_latest_candle(self, symbol: str, timeframe: str) -> Candle:
        interval = self._interval(timeframe)
        # Son tamamlanmış mumu güvenle almak için birkaç bar iste.
        candles = self._fetch(symbol, interval, limit=5)
        if not candles:
            raise RuntimeError(f"{symbol} için Yahoo'dan mum verisi alınamadı")
        return candles[-1]

    # ----- İç yardımcılar --------------------------------------------------
    def _interval(self, timeframe: str) -> str:
        if timeframe not in _INTERVAL_MAP:
            raise ValueError(f"Desteklenmeyen timeframe: {timeframe}")
        return _INTERVAL_MAP[timeframe]

    def _range_seconds(self, interval: str, limit: int) -> int:
        """İstenen mum sayısını kapsayacak geçmiş aralığını (saniye) hesaplar."""
        bpd = _BARS_PER_DAY.get(interval, 8) or 0.2
        # Hafta sonu/tatil boşlukları için ~1.8x tampon + 5 gün.
        days_needed = (limit / bpd) * 1.8 + 5
        days_needed = min(days_needed, _MAX_DAYS.get(interval, 730))
        return int(days_needed * 86400)

    def _build_url(self, yahoo_symbol: str, interval: str, limit: int) -> str:
        now = int(time.time())
        period1 = now - self._range_seconds(interval, limit)
        return (f"{_BASE_URL}{urllib.parse.quote(yahoo_symbol)}"
                f"?interval={interval}&period1={period1}&period2={now}"
                f"&includePrePost=false&events=div%2Csplit")

    def _fetch(self, symbol: str, interval: str, limit: int) -> List[Candle]:
        """Veriyi retry ile indirir ve Candle listesine çevirir."""
        ysym = self.to_yahoo_symbol(symbol)
        url = self._build_url(ysym, interval, limit)
        payload = self._http_get_with_retry(url)
        return self._parse(payload, interval, symbol)

    def _http_get_with_retry(self, url: str) -> dict:
        """Üstel geri-çekilmeli HTTP GET → JSON sözlük."""
        last_exc: Optional[Exception] = None
        for n in range(self.attempts):
            try:
                return self._http_get(url)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                delay = self.base_delay * (2 ** n)
                log.warning("Yahoo isteği hatası (deneme %d/%d): %s — %.0fs sonra",
                            n + 1, self.attempts, exc, delay)
                if n < self.attempts - 1:
                    self._sleep(delay)
        assert last_exc is not None
        raise last_exc

    def _http_get(self, url: str) -> dict:
        """Tek HTTP GET (User-Agent başlığıyla; Yahoo varsayılan UA'yı engeller)."""
        req = urllib.request.Request(url, headers={
            "User-Agent": ("Mozilla/5.0 (compatible; BIST-Trend-Robot/1.0; "
                           "+educational)"),
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    def _parse(self, payload: dict, interval: str, symbol: str) -> List[Candle]:
        """Yahoo chart JSON'unu tamamlanmış Candle listesine dönüştürür."""
        chart = (payload or {}).get("chart", {})
        err = chart.get("error")
        if err:
            raise RuntimeError(f"Yahoo hata ({symbol}): {err}")
        results = chart.get("result") or []
        if not results:
            return []

        res = results[0]
        timestamps = res.get("timestamp") or []
        quote = (res.get("indicators", {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        interval_sec = _INTERVAL_SECONDS.get(interval, 3600)
        now = time.time()
        candles: List[Candle] = []

        for i, ts in enumerate(timestamps):
            # Eksik (null) barları atla — tatil/işlemsiz dönemler.
            o, h, l, c = (self._at(opens, i), self._at(highs, i),
                          self._at(lows, i), self._at(closes, i))
            if None in (o, h, l, c):
                continue
            # Yalnızca TAMAMLANMIŞ mumlar: bar bitişi gelecekte ise atla.
            if ts + interval_sec > now:
                continue
            candles.append(Candle(
                timestamp=self._to_local(ts),
                open=float(o), high=float(h), low=float(l), close=float(c),
                volume=float(self._at(volumes, i) or 0.0),
                symbol=symbol,
            ))
        log.debug("Yahoo: %s için %d tamamlanmış mum (%s)",
                  symbol, len(candles), interval)
        return candles

    @staticmethod
    def _at(seq: list, i: int):
        return seq[i] if i < len(seq) else None

    @staticmethod
    def _to_local(epoch: int) -> datetime:
        """Epoch saniyeyi Europe/Istanbul yerel saatine (naive) çevirir."""
        dt_utc = datetime.fromtimestamp(epoch, tz=timezone.utc)
        if _IST_TZ is not None:
            return dt_utc.astimezone(_IST_TZ).replace(tzinfo=None)
        return dt_utc.replace(tzinfo=None)
