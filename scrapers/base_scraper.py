"""
Shared scraper base utilities and validation pipeline.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

import requests

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "car_prices.db"

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

PLAYWRIGHT_USER_AGENT = HEADERS_DEFAULT["User-Agent"]
_PLAYWRIGHT_STATE = threading.local()


@dataclass
class ValidationProfile:
    min_records: int = 1
    required_models: tuple[str, ...] = ()
    min_required_models: int = 0
    required_variant_keywords: tuple[str, ...] = ()
    forbid_methods: tuple[str, ...] = ()


@dataclass
class ValidationResult:
    accepted: bool
    message: str
    normalized_records: list[dict] = field(default_factory=list)


class SharedPlaywrightRuntime:
    """Uses a single Chromium instance for an entire scrape run."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright_manager = None
        self._playwright = None
        self.browser = None

    def start(self) -> "SharedPlaywrightRuntime":
        if self.browser is not None:
            return self

        from playwright.sync_api import sync_playwright

        self._playwright_manager = sync_playwright()
        self._playwright = self._playwright_manager.start()
        self.browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        return self

    def stop(self) -> None:
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None

        if self._playwright_manager is not None:
            try:
                self._playwright_manager.stop()
            except Exception:
                pass
            self._playwright_manager = None
            self._playwright = None

    def new_context_page(
        self,
        *,
        default_timeout_ms: int = 10000,
        navigation_timeout_ms: int = 30000,
    ):
        self.start()
        context = self.browser.new_context(
            user_agent=PLAYWRIGHT_USER_AGENT,
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            viewport={"width": 1440, "height": 2200},
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(default_timeout_ms)
        page.set_default_navigation_timeout(navigation_timeout_ms)
        return context, page


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update(HEADERS_DEFAULT)
    return _SESSION


def http_get(url: str, **kwargs) -> requests.Response:
    session = get_session()
    timeout = kwargs.pop("timeout", 20)
    for attempt in range(3):
        try:
            response = session.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt == 2:
                raise
            wait = 2**attempt
            log.warning("  GET %s hata (%s) - %ds beklenecek...", url, exc, wait)
            time.sleep(wait)
    raise RuntimeError("http_get reached unreachable state")


def http_post(url: str, **kwargs) -> requests.Response:
    session = get_session()
    timeout = kwargs.pop("timeout", 20)
    for attempt in range(3):
        try:
            response = session.post(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt == 2:
                raise
            wait = 2**attempt
            log.warning("  POST %s hata (%s) - %ds beklenecek...", url, exc, wait)
            time.sleep(wait)
    raise RuntimeError("http_post reached unreachable state")


def parse_price_str(text: str) -> int | None:
    import re

    cleaned = re.sub(r"[^\d]", "", text)
    if cleaned and int(cleaned) > 50_000:
        return int(cleaned)
    return None


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.executescript(
        """
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
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            variant_id          INTEGER NOT NULL REFERENCES variants(id) ON DELETE CASCADE,
            price_raw           TEXT    NOT NULL,
            price_int           INTEGER NOT NULL,
            list_price_int      INTEGER,
            campaign_price_int  INTEGER,
            discount_amount_int INTEGER DEFAULT 0,
            currency            TEXT    DEFAULT 'TRY',
            scraped_at          TEXT    NOT NULL,
            scraped_date        TEXT    NOT NULL,
            is_latest           INTEGER DEFAULT 1,
            is_active           INTEGER DEFAULT 1,
            is_new_model        INTEGER DEFAULT 0,
            is_new_variant      INTEGER DEFAULT 0,
            previous_price_int  INTEGER,
            price_diff          INTEGER DEFAULT 0,
            price_change_pct    REAL    DEFAULT 0.0,
            source              TEXT
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
        """
    )

    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(prices);")
    existing_cols = {col[1] for col in cursor.fetchall()}
    for col_name, col_def in [
        ("list_price_int", "INTEGER"),
        ("campaign_price_int", "INTEGER"),
        ("discount_amount_int", "INTEGER DEFAULT 0"),
        ("is_active", "INTEGER DEFAULT 1"),
    ]:
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE prices ADD COLUMN {col_name} {col_def};")
            except sqlite3.OperationalError:
                pass

    conn.commit()


def save_records(conn: sqlite3.Connection, brand: str, records: list[dict], source: str) -> int:
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
        cur.execute("INSERT INTO brands (name, created_at) VALUES (?, ?)", (brand, now))
        brand_id = cur.lastrowid

    seen_variant_ids: set[int] = set()

    for record in records:
        model_name = record.get("model_name", brand)
        variant_name = record.get("variant", "Standart")
        price_int = record.get("price_int", 0)
        if price_int <= 0:
            continue

        cur.execute("SELECT id FROM models WHERE brand_id = ? AND name = ?", (brand_id, model_name))
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

        cur.execute("SELECT id FROM variants WHERE model_id = ? AND name = ?", (model_id, variant_name))
        vrow = cur.fetchone()
        if vrow:
            variant_id = vrow[0]
            is_new_variant = 0
        else:
            cur.execute(
                "INSERT INTO variants (model_id, name, created_at) VALUES (?, ?, ?)",
                (model_id, variant_name, now),
            )
            variant_id = cur.lastrowid
            is_new_variant = 1

        seen_variant_ids.add(int(variant_id))

        cur.execute("SELECT price_int FROM prices WHERE variant_id = ? AND is_latest = 1", (variant_id,))
        prow = cur.fetchone()
        previous_price_int = prow[0] if prow else None

        price_diff = 0
        price_change_pct = 0.0
        if previous_price_int and previous_price_int != price_int:
            price_diff = price_int - previous_price_int
            price_change_pct = round((price_diff / previous_price_int) * 100, 2)

        list_price_int = record.get("list_price_int", price_int)
        campaign_price_int = record.get("campaign_price_int", price_int)
        discount_amount_int = record.get("discount_amount_int")
        if discount_amount_int is None:
            discount_amount_int = (list_price_int - campaign_price_int) if list_price_int > campaign_price_int else 0

        conn.execute("UPDATE prices SET is_latest = 0 WHERE variant_id = ?", (variant_id,))
        conn.execute(
            """
            INSERT INTO prices
            (variant_id, price_raw, price_int, list_price_int, campaign_price_int, discount_amount_int,
             currency, scraped_at, scraped_date, is_latest, is_active, is_new_model, is_new_variant,
             previous_price_int, price_diff, price_change_pct, source)
            VALUES (?,?,?,?,?,?,?,?,?,1,1,?,?,?,?,?)
            """,
            (
                variant_id,
                record.get("price_raw", fmt_price(campaign_price_int)),
                campaign_price_int,
                list_price_int,
                campaign_price_int,
                discount_amount_int,
                record.get("currency", "TRY"),
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

    if seen_variant_ids:
        placeholders = ",".join("?" for _ in seen_variant_ids)
        cur.execute(
            f"""
            UPDATE prices
            SET is_latest = 0,
                is_active = 0
            WHERE is_latest = 1
              AND variant_id IN (
                  SELECT v.id
                  FROM variants v
                  JOIN models m ON v.model_id = m.id
                  WHERE m.brand_id = ?
              )
              AND variant_id NOT IN ({placeholders})
            """,
            (brand_id, *sorted(seen_variant_ids)),
        )

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
        """
        INSERT INTO scrape_log
        (brand, run_at, status, method_used, models_found, message)
        VALUES (?,?,?,?,?,?)
        """,
        (brand, datetime.now().isoformat(timespec="seconds"), status, method_used, found, message),
    )
    conn.commit()


def fmt_price(value: int | float) -> str:
    return f"{int(value):,} TL".replace(",", ".")


class BaseScraper(ABC):
    brand: str = ""
    validation_profile = ValidationProfile()

    @property
    @abstractmethod
    def methods(self) -> list[tuple[str, Any]]:
        ...

    def run(
        self,
        conn: sqlite3.Connection,
        runtime: SharedPlaywrightRuntime | None = None,
    ) -> tuple[list[dict], str, ValidationResult]:
        previous_runtime = getattr(_PLAYWRIGHT_STATE, "runtime", None)
        _PLAYWRIGHT_STATE.runtime = runtime
        last_result = ValidationResult(False, "Canli veri dogrulanamadi.")
        try:
            for method_name, method_func in self.methods:
                try:
                    log.info("  [%s] %s veri yolu deneniyor...", self.brand, method_name)
                    records = method_func()
                    validation = self.validate_records(method_name, records)
                    last_result = validation
                    if validation.accepted:
                        log.info(
                            "  [%s] %s -> %d dogrulanmis kayit kabul edildi.",
                            self.brand,
                            method_name,
                            len(validation.normalized_records),
                        )
                        return validation.normalized_records, method_name, validation
                    log.warning("  [%s] %s reddedildi: %s", self.brand, method_name, validation.message)
                except Exception as exc:
                    log.warning("  [%s] %s basarisiz: %s", self.brand, method_name, exc)

            log.warning("  [%s] Canli tarama basarisiz oldu. Dogrulanmayan veri kaydedilmiyor.", self.brand)
            return [], "failed", last_result
        finally:
            _PLAYWRIGHT_STATE.runtime = previous_runtime

    def validate_records(self, method_name: str, records: list[dict]) -> ValidationResult:
        profile = self.validation_profile
        method_lower = method_name.lower()

        if any(token in method_lower for token in ("fallback", "static", "mock", "sample", "hardcoded", "demo")):
            return ValidationResult(False, f"{method_name} canli olmayan fallback gibi gorunuyor.")

        if any(method_lower == item.lower() for item in profile.forbid_methods):
            return ValidationResult(False, f"{method_name} bu marka icin guvenilir kabul edilmiyor.")

        normalized_records: list[dict] = []
        seen_keys: set[tuple[str, str, str, int]] = set()
        invalid_count = 0

        for raw in records or []:
            normalized = self.normalize_record(raw)
            if normalized is None:
                invalid_count += 1
                continue

            record_key = (
                self._normalize_text(normalized["model_name"]),
                self._normalize_text(normalized["variant"]),
                self._normalize_text(str(normalized.get("model_year") or "")),
                int(normalized["price_int"]),
            )
            if record_key in seen_keys:
                continue
            seen_keys.add(record_key)
            normalized_records.append(normalized)

        if not normalized_records:
            if invalid_count:
                return ValidationResult(False, f"{method_name} yalnizca gecersiz kayitlar uretti.")
            return ValidationResult(False, f"{method_name} bos sonuc verdi.")

        if len(normalized_records) < profile.min_records:
            return ValidationResult(False, f"{method_name} sadece {len(normalized_records)} kayit urettigi icin reddedildi.")

        if profile.required_models:
            discovered_models = {self._normalize_text(r["model_name"]) for r in normalized_records}
            hits = [
                model_name
                for model_name in profile.required_models
                if any(self._normalize_text(model_name) in discovered for discovered in discovered_models)
            ]
            required_hit_count = profile.min_required_models or len(profile.required_models)
            if len(hits) < required_hit_count:
                return ValidationResult(
                    False,
                    f"{method_name} marka kontratini gecemedi. Beklenen modellerin sadece {len(hits)} tanesi bulundu.",
                )

        if profile.required_variant_keywords:
            variant_text = " ".join(self._normalize_text(r["variant"]) for r in normalized_records)
            missing_keywords = [
                keyword
                for keyword in profile.required_variant_keywords
                if self._normalize_text(keyword) not in variant_text
            ]
            if missing_keywords:
                return ValidationResult(
                    False,
                    f"{method_name} kritik varyant ipuclarini icermiyor: {', '.join(missing_keywords)}",
                )

        return ValidationResult(
            True,
            f"{method_name} dogrulandi. {len(normalized_records)} kayit kabul edildi.",
            normalized_records=normalized_records,
        )

    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any] | None:
        model_name = str(record.get("model_name") or "").strip()
        variant = str(record.get("variant") or "").strip()
        price_val = record.get("price_int")

        if isinstance(price_val, bool):
            price_int = None
        elif isinstance(price_val, (int, float)):
            price_int = int(price_val)
        else:
            price_int = parse_price_str(str(price_val or ""))

        if not model_name or not variant or not price_int or price_int < 100_000:
            return None

        normalized = dict(record)
        normalized["model_name"] = model_name
        normalized["variant"] = variant
        normalized["price_int"] = price_int
        normalized["price_raw"] = record.get("price_raw") or fmt_price(price_int)
        normalized["currency"] = record.get("currency") or "TRY"

        if record.get("list_price_int") is not None:
            normalized["list_price_int"] = int(record["list_price_int"])
        if record.get("campaign_price_int") is not None:
            normalized["campaign_price_int"] = int(record["campaign_price_int"])

        return normalized

    def fetch_page_html(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 30000,
        post_load_wait_ms: int = 2000,
        on_after_load: Callable[[Any], None] | None = None,
    ) -> str:
        runtime = getattr(_PLAYWRIGHT_STATE, "runtime", None)
        owns_runtime = runtime is None
        if owns_runtime:
            runtime = SharedPlaywrightRuntime().start()

        context, page = runtime.new_context_page(navigation_timeout_ms=timeout_ms)
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            self.dismiss_cookie_banners(page)
            if on_after_load is not None:
                on_after_load(page)
                self.dismiss_cookie_banners(page)
            if post_load_wait_ms > 0:
                page.wait_for_timeout(post_load_wait_ms)
            self.dismiss_cookie_banners(page)
            return page.content()
        finally:
            try:
                context.close()
            finally:
                if owns_runtime:
                    runtime.stop()

    def dismiss_cookie_banners(self, page: Any) -> None:
        import re

        selectors = [
            "#onetrust-accept-btn-handler",
            "#onetrust-reject-all-handler",
            ".onetrust-close-btn-handler",
            "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
            "#CybotCookiebotDialogBodyButtonAccept",
            "button[aria-label='Accept']",
            "button[aria-label='Kabul et']",
            "[data-testid='cookie-accept-all']",
            "[data-testid='accept-all-cookies']",
            ".cookie-accept",
            ".accept-cookies",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=400):
                    locator.click(timeout=800, force=True)
                    page.wait_for_timeout(200)
            except Exception:
                pass

        text_patterns = [
            re.compile(r"tumunu kabul", re.I),
            re.compile(r"kabul et", re.I),
            re.compile(r"accept all", re.I),
            re.compile(r"allow all", re.I),
            re.compile(r"agree", re.I),
        ]
        for pattern in text_patterns:
            try:
                button = page.get_by_role("button", name=pattern).first
                if button.is_visible(timeout=400):
                    button.click(timeout=800, force=True)
                    page.wait_for_timeout(200)
            except Exception:
                pass

        try:
            page.evaluate(
                """
                () => {
                    const selectors = [
                        '#onetrust-consent-sdk',
                        '#onetrust-banner-sdk',
                        '.onetrust-pc-dark-filter',
                        '#CybotCookiebotDialog',
                        '.cookie-banner',
                        '.cookie-consent',
                        '.fc-consent-root',
                        '.qc-cmp2-container'
                    ];
                    selectors.forEach((selector) => {
                        document.querySelectorAll(selector).forEach((node) => node.remove());
                    });
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                }
                """
            )
        except Exception:
            pass

    def _normalize_text(self, text: str) -> str:
        return (
            text.lower()
            .replace("ë", "e")
            .replace("é", "e")
            .replace("ç", "c")
            .replace("ş", "s")
            .replace("ı", "i")
            .replace("ö", "o")
            .replace("ü", "u")
        )
