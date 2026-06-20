"""
Config Katmanı
==============

Konfigürasyon dosyasını (YAML/JSON) okur, ortam değişkeni yer tutucularını
(``${ENV:DEGISKEN}``) çözer ve doğrular.

Tasarım notları:
  - PyYAML kuruluysa tam YAML desteği kullanılır.
  - Kurulu değilse: dosya JSON ise JSON olarak okunur; değilse gömülü çok
    basit bir YAML alt-küme ayrıştırıcısı devreye girer. Böylece robot harici
    bağımlılık olmadan da çalışabilir.

Kullanım:
    >>> from bistrobot.config.loader import load_config
    >>> cfg = load_config("config/config.yaml")
    >>> cfg["strategy"]["ema_fast"]
    12
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from bistrobot.logging_utils.logger import get_logger

log = get_logger("config")

# ---------------------------------------------------------------------------
# Doğrulama için beklenen alanlar (bölüm -> zorunlu anahtarlar).
# ---------------------------------------------------------------------------
_REQUIRED: Dict[str, List[str]] = {
    "app": ["mode", "timeframe"],
    "broker": ["api_key", "api_secret"],
    "symbols": [],
    "strategy": ["ema_fast", "ema_slow", "rsi_period", "atr_period"],
    "risk": ["account_balance", "risk_per_trade_pct",
             "daily_max_loss_pct", "max_open_positions"],
}

_VALID_MODES = {"backtest", "paper", "live"}
_ENV_PATTERN = re.compile(r"\$\{ENV:([A-Z0-9_]+)\}")


class ConfigError(Exception):
    """Konfigürasyon yükleme/doğrulama hatası."""


def load_config(path: str) -> Dict[str, Any]:
    """Config dosyasını okur, env değişkenlerini çözer ve doğrular.

    Raises:
        ConfigError: Dosya yoksa, ayrıştırılamazsa veya doğrulama başarısızsa.
    """
    if not os.path.exists(path):
        raise ConfigError(f"Config dosyası bulunamadı: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    data = _parse(raw, path)
    data = _resolve_env(data)
    _validate(data)
    log.info("Config yüklendi: %s (mod=%s, %d sembol)",
             path, data["app"]["mode"], len(data.get("symbols", [])))
    return data


# ---------------------------------------------------------------------------
# Ayrıştırma yardımcıları
# ---------------------------------------------------------------------------
def _parse(raw: str, path: str) -> Dict[str, Any]:
    """YAML (varsa) veya JSON / gömülü basit ayrıştırıcı ile çözer."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(raw)
    except ImportError:
        log.warning("PyYAML bulunamadı; gömülü basit ayrıştırıcı kullanılıyor.")
        if path.endswith(".json"):
            return json.loads(raw)
        return _simple_yaml_parse(raw)


def _resolve_env(obj: Any) -> Any:
    """``${ENV:DEGISKEN}`` yer tutucularını ortam değişkenleriyle değiştirir."""
    if isinstance(obj, dict):
        return {k: _resolve_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env(v) for v in obj]
    if isinstance(obj, str):
        def repl(m: "re.Match[str]") -> str:
            var = m.group(1)
            val = os.environ.get(var)
            if val is None:
                log.warning("Ortam değişkeni tanımsız: %s", var)
                return ""
            return val
        return _ENV_PATTERN.sub(repl, obj)
    return obj


def _validate(data: Dict[str, Any]) -> None:
    """Zorunlu alanların ve değer aralıklarının varlığını denetler."""
    if not isinstance(data, dict):
        raise ConfigError("Config kök yapısı bir sözlük olmalı.")

    for section, keys in _REQUIRED.items():
        if section not in data:
            raise ConfigError(f"Eksik config bölümü: '{section}'")
        for key in keys:
            if key not in data[section]:
                raise ConfigError(f"Eksik anahtar: '{section}.{key}'")

    mode = data["app"]["mode"]
    if mode not in _VALID_MODES:
        raise ConfigError(f"Geçersiz mod: '{mode}'. {_VALID_MODES} olmalı.")

    if not data.get("symbols"):
        raise ConfigError("En az bir sembol tanımlanmalı (symbols).")

    risk = data["risk"]
    if not (0 < risk["risk_per_trade_pct"] <= 100):
        raise ConfigError("risk_per_trade_pct 0-100 aralığında olmalı.")
    if not (0 < risk["daily_max_loss_pct"] <= 100):
        raise ConfigError("daily_max_loss_pct 0-100 aralığında olmalı.")
    if risk["max_open_positions"] < 1:
        raise ConfigError("max_open_positions en az 1 olmalı.")

    # Canlı modda placeholder anahtarla çalışmaya karşı uyar.
    if mode == "live" and "PLACEHOLDER" in str(data["broker"]["api_key"]):
        log.warning("CANLI MOD seçili ama API anahtarı PLACEHOLDER! "
                    "Gerçek emir gönderilemez.")


def _simple_yaml_parse(raw: str) -> Dict[str, Any]:
    """PyYAML yokken kullanılan ÇOK BASİT YAML alt-küme ayrıştırıcısı.

    Desteklenenler: iç içe sözlükler (2 boşluk girinti), ``- liste`` öğeleri,
    yorum (``#``), tırnaklı/tırnaksız skalerler, int/float/bool/null tipleri.
    Karmaşık YAML özellikleri (anchor, multi-line vb.) desteklenmez — bu nedenle
    üretimde PyYAML kurmanız önerilir.
    """
    root: Dict[str, Any] = {}
    # Yığın elemanı: (girinti, container, parent_container, key_in_parent).
    # parent/key bilgisi, bir sözlüğü gerektiğinde listeye çevirmek için tutulur.
    stack: List[Any] = [(-1, root, None, None)]

    for line in raw.splitlines():
        # Yorumları ve boş satırları atla.
        if "#" in line:
            line = line.split("#", 1)[0]
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        # Mevcut girintiden derin/eşit kapsayıcıları yığından çıkar.
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        _, container, p_parent, p_key = stack[-1]

        if content.startswith("- "):
            # Liste öğesi. Aktif kapsayıcı dict ise (boş başlatılmıştı) listeye çevir.
            if not isinstance(container, list):
                new_list: List[Any] = []
                if isinstance(p_parent, dict) and p_key is not None:
                    p_parent[p_key] = new_list
                container = new_list
                stack[-1] = (stack[-1][0], container, p_parent, p_key)
            container.append(_coerce(content[2:].strip()))
        elif ":" in content:
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # Alt yapı: önce dict varsay; "- " görülürse listeye dönüşür.
                child: Dict[str, Any] = {}
                if isinstance(container, dict):
                    container[key] = child
                stack.append((indent, child, container, key))
            elif isinstance(container, dict):
                container[key] = _coerce(val)
    return root


def _coerce(val: str) -> Any:
    """Skaler string'i uygun Python tipine çevirir."""
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    low = val.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", "none", ""):
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val
