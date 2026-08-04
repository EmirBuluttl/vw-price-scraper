"""
base_scraper.py  —  Tüm marka scraper'larının türediği soyut taban sınıf (Playwright Canlı Destekli).
=================================================================================================
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
        "Chrome/126.0.0.0 Safari/537.36"
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
    """Retry'lı GET isteği."""
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
    raise RuntimeError("http_get: ulaşılamaz durum")


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
    raise RuntimeError("http_post: ulaşılamaz durum")


def parse_price_str(text: str) -> int | None:
    """'₺1.750.000', '1.750.000 TL', '1750000' gibi string'lerden integer çıkar."""
    import re
    cleaned = re.sub(r"[^\d]", "", text)
    if cleaned and int(cleaned) > 50_000:
        return int(cleaned)
    return None


# ─── Veritabanı Yardımcıları ──────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    """Tüm markalar için normalize edilmiş ilişkisel veritabanı şemasını ve yetki tablosunu oluştur."""
    conn.execute("PRAGMA foreign_keys = ON;")
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS brands (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    UNIQUE NOT NULL,
            code       TEXT,
            created_at TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS models (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id   INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
            name       TEXT    NOT NULL,
            body_type  TEXT,
            created_at TEXT    NOT NULL,
            UNIQUE(brand_id, name)
        );

        CREATE TABLE IF NOT EXISTS variants (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id     INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
            name         TEXT    NOT NULL,
            fuel_type    TEXT,
            transmission TEXT,
            engine_power TEXT,
            model_year   TEXT,
            created_at   TEXT    NOT NULL,
            UNIQUE(model_id, name)
        );

        CREATE TABLE IF NOT EXISTS prices (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id         INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
            price_raw          TEXT    NOT NULL,
            price_int          INTEGER NOT NULL,
            list_price_int     INTEGER,
            campaign_price_int INTEGER,
            discount_amount_int INTEGER DEFAULT 0,
            currency           TEXT    DEFAULT 'TRY',
            scraped_at         TEXT    NOT NULL,
            scraped_date       TEXT    NOT NULL,
            is_latest          INTEGER DEFAULT 1,
            is_active          INTEGER DEFAULT 1,
            is_new_model       INTEGER DEFAULT 0,
            is_new_variant     INTEGER DEFAULT 0,
            previous_price_int INTEGER,
            price_diff         INTEGER DEFAULT 0,
            price_change_pct   REAL    DEFAULT 0.0,
            source             TEXT
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

        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_prices_variant_latest ON prices (variant_id, is_latest);
        CREATE INDEX IF NOT EXISTS idx_prices_date ON prices (scraped_date);
    """)

    # Güvenli Auto Migration
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(prices);")
    existing_cols = {col[1] for col in cursor.fetchall()}
    for col_name, col_def in [
        ("list_price_int", "INTEGER"),
        ("campaign_price_int", "INTEGER"),
        ("discount_amount_int", "INTEGER DEFAULT 0"),
        ("is_active", "INTEGER DEFAULT 1")
    ]:
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE prices ADD COLUMN {col_name} {col_def};")
            except sqlite3.OperationalError:
                pass

    conn.commit()


def save_records(conn: sqlite3.Connection, brand: str, records: list[dict], source: str) -> int:
    """Çekilen verileri normalize ilişkisel şemaya (brands -> models -> variants -> prices) kaydet."""
    if not records:
        return 0

    now = datetime.now().isoformat(timespec="seconds")
    today = date.today().isoformat()
    inserted = 0

    cur = conn.cursor()
    cur.execute("SELECT id FROM brands WHERE name = ?", (brand,))
    row = cur.fetchone()
    if row:
        brand_id = row[0]
    else:
        cur.execute(
            "INSERT INTO brands (name, created_at) VALUES (?, ?)",
            (brand, now),
        )
        brand_id = cur.lastrowid

    for r in records:
        model_name = r.get("model_name", brand)
        variant_name = r.get("variant", "Standart")
        price_int = r.get("price_int", 0)

        if price_int <= 0:
            continue

        cur.execute(
            "SELECT id FROM models WHERE brand_id = ? AND name = ?",
            (brand_id, model_name),
        )
        mrow = cur.fetchone()
        if mrow:
            model_id = mrow[0]
            is_new_model = 0
        else:
            cur.execute(
                "INSERT INTO models (brand_id, name, created_at) VALUES (?, ?, ?)",
                (brand_id, model_name, now),
            )
            model_id = cur.lastrowid
            is_new_model = 1

        cur.execute(
            "SELECT id FROM variants WHERE model_id = ? AND name = ?",
            (model_id, variant_name),
        )
        vrow = cur.fetchone()
        if vrow:
            variant_id = vrow[0]
            is_new_variant = 0
        else:
            cur.execute(
                """INSERT INTO variants (model_id, name, created_at)
                   VALUES (?, ?, ?)""",
                (model_id, variant_name, now),
            )
            variant_id = cur.lastrowid
            is_new_variant = 1

        cur.execute(
            "SELECT price_int FROM prices WHERE variant_id = ? AND is_latest = 1",
            (variant_id,),
        )
        prow = cur.fetchone()
        previous_price_int = prow[0] if prow else None

        price_diff = 0
        price_change_pct = 0.0
        if previous_price_int and previous_price_int != price_int:
            price_diff = price_int - previous_price_int
            price_change_pct = round((price_diff / previous_price_int) * 100, 2)

        list_price_int = r.get("list_price_int", price_int)
        campaign_price_int = r.get("campaign_price_int", price_int)
        discount_amount_int = r.get("discount_amount_int")
        if discount_amount_int is None:
            discount_amount_int = (list_price_int - campaign_price_int) if list_price_int > campaign_price_int else 0

        conn.execute("UPDATE prices SET is_latest = 0 WHERE variant_id = ?", (variant_id,))

        conn.execute(
            """INSERT INTO prices
               (variant_id, price_raw, price_int, list_price_int, campaign_price_int, discount_amount_int,
                currency, scraped_at, scraped_date, is_latest, is_active, is_new_model, is_new_variant,
                previous_price_int, price_diff, price_change_pct, source)
               VALUES (?,?,?,?,?,?,?,?,?,1,1,?,?,?,?,?)""",
            (
                variant_id,
                r.get("price_raw", fmt_price(campaign_price_int)),
                campaign_price_int,
                list_price_int,
                campaign_price_int,
                discount_amount_int,
                r.get("currency", "TRY"),
                now,
                today,
                is_new_model,
                is_new_variant,
                previous_price_int,
                price_diff,
                price_change_pct,
                source,
            ),
        )
        inserted += 1

    conn.commit()
    return inserted


def get_stale_records(conn: sqlite3.Connection, brand: str) -> list[dict]:
    return []


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


# ─── Soyut Taban Sınıf ───────────────────────────────────────────────────────
class BaseScraper(ABC):
    brand: str = ""

    @property
    @abstractmethod
    def methods(self) -> list[tuple[str, Any]]:
        ...

    def run(self, conn: sqlite3.Connection) -> tuple[list[dict], str]:
        """Tüm canlı tarama metodlarını sırayla dener."""
        for method_name, method_func in self.methods:
            try:
                log.info("  [%s] %s canlı Chrome otomasyonu deneniyor...", self.brand, method_name)
                records = method_func()
                if records:
                    log.info(
                        "  [%s] %s -> %d CANLI kayıt bulundu.",
                        self.brand, method_name, len(records),
                    )
                    return records, method_name
                log.warning("  [%s] %s -> boş sonuç.", self.brand, method_name)
            except Exception as exc:
                log.warning("  [%s] %s başarısız: %s", self.brand, method_name, exc)

        # Stale fallback devre dışı — Sadece %100 canlı gerçek veri döndürülür
        log.warning("  [%s] Canlı tarama başarısız oldu. Stale fallback kapalı, bayat veri döndürülmüyor.", self.brand)
        return [], "failed"
