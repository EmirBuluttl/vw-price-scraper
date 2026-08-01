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
            currency           TEXT    DEFAULT 'TRY',
            scraped_at         TEXT    NOT NULL,
            scraped_date       TEXT    NOT NULL,
            is_latest          INTEGER DEFAULT 1,
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

    conn.commit()


def parse_vehicle_attributes(brand: str, model_name: str, variant: str) -> tuple[str, str, str, str]:
    """Araç markası, modeli ve varyantından yakıt, vites, kasa ve motor gücü özniteliklerini ayıkla."""
    import re
    text = f"{brand} {model_name} {variant}"

    # Yakıt Tipi
    fuel = "Benzin"
    if re.search(r"elektrik|ev\b|\bkw\b", text, re.I):
        fuel = "Elektrik"
    elif re.search(r"hybrid|hibrit|e-cvt|hev|mhev|etsi|e-tec", text, re.I):
        fuel = "Hibrit"
    elif re.search(r"d-4d|dizel|dci|crdi|ecoblue|1\.5 d|2\.2 d|tdi", text, re.I):
        fuel = "Dizel"
    elif re.search(r"lpg|gpl", text, re.I):
        fuel = "LPG"

    # Şanzıman Tipi
    trans = "Otomatik"
    if re.search(r"m/t|manuel|ileri manuel|\bmt\b", text, re.I):
        trans = "Manuel"

    # Kasa Tipi
    body = "Binek"
    if re.search(r"suv|cross|c-hr|kuga|puma|tucson|bayon|kona|duster|captur|austral|taigo|t-cross|t-roc|tiguan|tayron|kodiaq|karoq|kamiq", text, re.I):
        body = "SUV"
    elif re.search(r"sedan|corolla|passat|megane sedan", text, re.I):
        body = "Sedan"
    elif re.search(r"hatchback|htb|clio|i20|i10|golf|polo|fabia|scala|yaris|sandero", text, re.I):
        body = "Hatchback"
    elif re.search(r"van|cargo|kamyonet|panelvan|combi|master|transit|custom|courier|hilux|prado|proace|kangoo|staria", text, re.I):
        body = "Ticari / Pick-up"

    # Motor / Güç (PS/HP/kW)
    hp_match = re.search(r"(\d+\s*(?:ps|hp|kw))", text, re.I)
    engine_power = hp_match.group(1).upper() if hp_match else ""

    return fuel, trans, body, engine_power


def save_records(
    conn: sqlite3.Connection,
    brand_name: str,
    records: list[dict],
    source: str,
    is_stale: int = 0,
) -> int:
    """Normalize edilmiş tablolara (brands, models, variants, prices) veri yaz ve delta hesapla."""
    today = date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    inserted = 0

    # 1. Brand Kaydet / Al
    brand_row = conn.execute("SELECT id FROM brands WHERE name = ?", (brand_name,)).fetchone()
    if brand_row:
        brand_id = brand_row[0]
    else:
        cursor = conn.execute("INSERT INTO brands (name, code, created_at) VALUES (?, ?, ?)",
                              (brand_name, brand_name.lower(), now))
        brand_id = cursor.lastrowid

    for r in records:
        model_name = r["model_name"]
        variant_name = r.get("variant", "") or "Standart"
        price_int = r.get("price_int")
        if not price_int:
            continue

        fuel_type, transmission, body_type, engine_power = parse_vehicle_attributes(brand_name, model_name, variant_name)

        # 2. Model Kaydet / Al
        model_row = conn.execute("SELECT id FROM models WHERE brand_id = ? AND name = ?", (brand_id, model_name)).fetchone()
        if model_row:
            model_id = model_row[0]
        else:
            cursor = conn.execute("INSERT INTO models (brand_id, name, body_type, created_at) VALUES (?, ?, ?, ?)",
                                  (brand_id, model_name, body_type, now))
            model_id = cursor.lastrowid

        # 3. Variant Kaydet / Al
        variant_row = conn.execute("SELECT id FROM variants WHERE model_id = ? AND name = ?", (model_id, variant_name)).fetchone()
        if variant_row:
            variant_id = variant_row[0]
        else:
            cursor = conn.execute("""
                INSERT INTO variants (model_id, name, fuel_type, transmission, engine_power, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (model_id, variant_name, fuel_type, transmission, engine_power, now))
            variant_id = cursor.lastrowid

        # 4. Bugün aynı varyant için fiyat eklenmiş mi kontrol et
        exists = conn.execute(
            "SELECT 1 FROM prices WHERE variant_id=? AND scraped_date=?",
            (variant_id, today),
        ).fetchone()

        if not exists:
            # Delta Hesaplamaları
            prev_model_exists = conn.execute(
                """SELECT 1 FROM prices p JOIN variants v ON p.variant_id = v.id
                   WHERE v.model_id=? AND p.scraped_date < ?""",
                (model_id, today),
            ).fetchone()
            is_new_model = 1 if not prev_model_exists else 0

            prev_variant_row = conn.execute(
                """SELECT price_int FROM prices
                   WHERE variant_id=? AND scraped_date < ?
                   ORDER BY scraped_date DESC, id DESC LIMIT 1""",
                (variant_id, today),
            ).fetchone()

            is_new_variant = 1 if not prev_variant_row else 0
            previous_price_int = None
            price_diff = 0
            price_change_pct = 0.0

            if prev_variant_row and prev_variant_row[0] and price_int:
                previous_price_int = prev_variant_row[0]
                price_diff = price_int - previous_price_int
                if previous_price_int > 0:
                    price_change_pct = round((price_diff / previous_price_int) * 100, 2)

            # Önceki is_latest = 1 olan kaydı 0 yap
            conn.execute("UPDATE prices SET is_latest = 0 WHERE variant_id = ?", (variant_id,))

            conn.execute(
                """INSERT INTO prices
                   (variant_id, price_raw, price_int, currency, scraped_at, scraped_date,
                    is_latest, is_new_model, is_new_variant, previous_price_int, price_diff, price_change_pct, source)
                   VALUES (?,?,?,?,?,?,1,?,?,?,?,?,?)""",
                (
                    variant_id,
                    r.get("price_raw", fmt_price(price_int)),
                    price_int,
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
    """Söz konusu markanın veritabanındaki en son başarılı çekimini döndür."""
    rows = conn.execute(
        """SELECT m.name as model_name, v.name as variant, p.price_raw, p.price_int, p.currency
           FROM prices p
           JOIN variants v ON p.variant_id = v.id
           JOIN models m ON v.model_id = m.id
           JOIN brands b ON m.brand_id = b.id
           WHERE b.name = ? AND p.is_latest = 1""",
        (brand,),
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
