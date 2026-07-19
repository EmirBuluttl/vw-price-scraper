"""
base_scraper.py  —  Tüm marka scraper'larının türediği soyut taban sınıf.
==========================================================================
Her scraper:
  1. Önce birincil kaynağı (API / HTML) dener.
  2. Başarısız olursa sıradaki fallback'e geçer.
  3. Tüm kaynaklar başarısız olursa veritabanındaki son başarılı veriyi
     `is_stale=1` olarak döndürür — "bulunamadı" çıktısı asla kabul edilmez.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "car_prices.db"

# ─── Ortak HTTP Session ───────────────────────────────────────────────────────
_SESSION: requests.Session | None = None

HEADERS_DEFAULT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update(HEADERS_DEFAULT)
    return _SESSION


def http_get(url: str, **kwargs) -> requests.Response:
    """Retry'lı GET isteği. 3 deneme, exponential backoff."""
    session = get_session()
    for attempt in range(3):
        try:
            r = session.get(url, timeout=kwargs.pop("timeout", 20), **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == 2:
                raise
            wait = 2 ** attempt
            log.warning("  GET %s hata (%s) — %ds beklenecek...", url, e, wait)
            time.sleep(wait)
    raise RuntimeError("http_get: ulaşılamaz durum")  # pragma: no cover


def http_post(url: str, **kwargs) -> requests.Response:
    """Retry'lı POST isteği."""
    session = get_session()
    for attempt in range(3):
        try:
            r = session.post(url, timeout=kwargs.pop("timeout", 20), **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == 2:
                raise
            wait = 2 ** attempt
            log.warning("  POST %s hata (%s) — %ds beklenecek...", url, e, wait)
            time.sleep(wait)
    raise RuntimeError("http_post: ulaşılamaz durum")  # pragma: no cover


# ─── Veritabanı Yardımcıları ──────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    """Tüm markalar için ortak şemayı oluştur (yoksa)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS prices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            brand        TEXT    NOT NULL,
            model_name   TEXT    NOT NULL,
            variant      TEXT,
            price_raw    TEXT,
            price_int    INTEGER,
            currency     TEXT    DEFAULT 'TRY',
            source       TEXT,
            is_stale     INTEGER DEFAULT 0,
            scraped_at   TEXT    NOT NULL,
            scraped_date TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scrape_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            brand        TEXT    NOT NULL,
            run_at       TEXT    NOT NULL,
            status       TEXT    NOT NULL,
            method_used  TEXT,
            models_found INTEGER DEFAULT 0,
            message      TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_prices_brand_date
            ON prices (brand, scraped_date);
    """)
    conn.commit()


def save_records(
    conn: sqlite3.Connection,
    brand: str,
    records: list[dict],
    source: str,
    is_stale: int = 0,
) -> int:
    """Bugün kaydedilmemiş kayıtları ekle. Döndürülen değer eklenen satır sayısı."""
    today = date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    inserted = 0
    for r in records:
        exists = conn.execute(
            """SELECT 1 FROM prices
               WHERE brand=? AND model_name=? AND variant=? AND scraped_date=?""",
            (brand, r["model_name"], r.get("variant", ""), today),
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO prices
                   (brand, model_name, variant, price_raw, price_int, currency,
                    source, is_stale, scraped_at, scraped_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    brand,
                    r["model_name"],
                    r.get("variant", ""),
                    r.get("price_raw", ""),
                    r.get("price_int"),
                    r.get("currency", "TRY"),
                    source,
                    is_stale,
                    now,
                    today,
                ),
            )
            inserted += 1
    conn.commit()
    return inserted


def get_stale_records(conn: sqlite3.Connection, brand: str) -> list[dict]:
    """Söz konusu markanın veritabanındaki en son başarılı çekimini döndür."""
    rows = conn.execute(
        """SELECT model_name, variant, price_raw, price_int, currency
           FROM prices
           WHERE brand = ?
             AND is_stale = 0
             AND scraped_date = (
                 SELECT MAX(scraped_date) FROM prices
                 WHERE brand = ? AND is_stale = 0
             )""",
        (brand, brand),
    ).fetchall()
    return [
        {
            "model_name": r[0],
            "variant": r[1],
            "price_raw": r[2],
            "price_int": r[3],
            "currency": r[4],
        }
        for r in rows
    ]


def log_run(
    conn: sqlite3.Connection,
    brand: str,
    status: str,
    method_used: str = "",
    found: int = 0,
    message: str = "",
) -> None:
    conn.execute(
        """INSERT INTO scrape_log
           (brand, run_at, status, method_used, models_found, message)
           VALUES (?,?,?,?,?,?)""",
        (brand, datetime.now().isoformat(timespec="seconds"), status, method_used, found, message),
    )
    conn.commit()


def fmt_price(value: int | float) -> str:
    """1750000 → '1.750.000 TL'"""
    return f"{int(value):,} TL".replace(",", ".")


def parse_price_str(text: str) -> int | None:
    """
    '₺1.750.000', '1.750.000 TL', '1750000' gibi string'lerden
    integer çıkar. Başarısız olursa None.
    """
    import re
    cleaned = re.sub(r"[^\d]", "", text)
    if cleaned and int(cleaned) > 50_000:
        return int(cleaned)
    return None


# ─── Soyut Taban Sınıf ───────────────────────────────────────────────────────
class BaseScraper(ABC):
    """
    Her marka scraper'ı bu sınıfı miras alır ve `methods` property'sini
    uygular. `methods`, adı-ve-callable çiftlerinin sıralı listesidir;
    başarılı ilk sonuç kullanılır.
    """

    brand: str = ""  # Alt sınıf dolduracak

    @property
    @abstractmethod
    def methods(self) -> list[tuple[str, Any]]:
        """
        [('api', self._fetch_api), ('html', self._fetch_html), ...]
        sırasıyla denenir. Her callable () → list[dict] döndürmeli.
        Boş liste veya exception → sonraki denenir.
        """
        ...

    def run(self, conn: sqlite3.Connection) -> tuple[list[dict], str]:
        """
        Tüm metodları sırayla dener.
        Returns: (records, method_used)
        """
        for method_name, method_func in self.methods:
            try:
                log.info("  [%s] %s deneniyor...", self.brand, method_name)
                records = method_func()
                if records:
                    log.info(
                        "  [%s] %s -> %d kayıt bulundu.",
                        self.brand, method_name, len(records),
                    )
                    return records, method_name
                log.warning("  [%s] %s -> boş sonuç.", self.brand, method_name)
            except Exception as exc:
                log.warning("  [%s] %s başarısız: %s", self.brand, method_name, exc)

        # Tüm metodlar başarısız → stale data
        stale = get_stale_records(conn, self.brand)
        if stale:
            log.warning(
                "  [%s] Tüm metodlar başarısız, %d kayıt stale olarak kullanılıyor.",
                self.brand, len(stale),
            )
            return stale, "stale"

        log.error("  [%s] Hiç veri bulunamadı ve stale kayıt da yok!", self.brand)
        return [], "failed"
