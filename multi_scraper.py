"""
multi_scraper.py  —  Çoklu Marka Araç Fiyat Scraper Ana Scripti
================================================================
Kullanım:
    python multi_scraper.py            # Tüm markalar
    python multi_scraper.py --brand vw # Sadece VW

Her sabah 09:00'da Task Scheduler veya run_multi_scraper.bat ile çalıştırılır.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ─── Loglama ─────────────────────────────────────────────────────────────────
LOG_PATH = Path(__file__).parent / "multi_scraper.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ─── Veritabanı ──────────────────────────────────────────────────────────────
from scrapers.base_scraper import (
    DB_PATH,
    init_db,
    log_run,
    save_records,
)

# ─── Scraper'ları Kaydet ──────────────────────────────────────────────────────
from scrapers.vw_scraper      import VWScraper
from scrapers.skoda_scraper   import SkodaScraper
from scrapers.renault_scraper import RenaultScraper
from scrapers.ford_scraper    import FordScraper
from scrapers.hyundai_scraper import HyundaiScraper
from scrapers.toyota_scraper  import ToyotaScraper
from scrapers.chery_scraper   import CheryScraper
from scrapers.dacia_scraper   import DaciaScraper
from scrapers.kia_scraper     import KiaScraper
from scrapers.fiat_scraper    import FiatScraper
from scrapers.peugeot_scraper import PeugeotScraper
from scrapers.opel_scraper    import OpelScraper
from scrapers.citroen_scraper import CitroenScraper
from scrapers.jeep_scraper    import JeepScraper
from scrapers.alfaromeo_scraper import AlfaRomeoScraper
from scrapers.ds_scraper      import DSScraper
from scrapers.maserati_scraper import MaseratiScraper

ALL_SCRAPERS = [
    VWScraper(),
    SkodaScraper(),
    RenaultScraper(),
    FordScraper(),
    HyundaiScraper(),
    ToyotaScraper(),
    CheryScraper(),
    DaciaScraper(),
    KiaScraper(),
    FiatScraper(),
    PeugeotScraper(),
    OpelScraper(),
    CitroenScraper(),
    JeepScraper(),
    AlfaRomeoScraper(),
    DSScraper(),
    MaseratiScraper(),
]

SCRAPER_MAP = {s.brand.lower(): s for s in ALL_SCRAPERS}


# ─── Konsol Çıktısı ──────────────────────────────────────────────────────────
COL_W = 80

def _print_brand_table(brand: str, records: list[dict], method: str, is_stale: bool) -> None:
    stale_flag = " [STALE]" if is_stale else ""
    source_tag = f"[{method.upper()}]{stale_flag}"
    sep = "-" * COL_W
    print(f"\n{sep}")
    print(f"  {brand.upper():<20} {source_tag}")
    print(sep)
    if records:
        print(f"  {'MODEL':<30} {'VARYANT':<25} {'FIYAT':>16}")
        print("  " + "-" * (COL_W - 2))
        for r in sorted(records, key=lambda x: x.get("price_int") or 0):
            model   = (r["model_name"] or "")[:28]
            variant = (r.get("variant") or "")[:23]
            price   = r.get("price_raw") or "-"
            print(f"  {model:<30} {variant:<25} {price:>16}")
    else:
        print("  [UYARI] Bu marka icin veri bulunamadi.")
    print()


def _print_summary(results: list[tuple]) -> None:
    sep = "=" * COL_W
    print(f"\n{sep}")
    print(f"  OZET  -  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(sep)
    total_records = 0
    for brand, records, method, is_stale in results:
        status = "STALE" if is_stale else ("OK" if records else "FAIL")
        count = len(records)
        total_records += count
        print(f"  {brand:<18} {status:<12} {count:>4} kayit   [{method}]")
    print("  " + "-" * (COL_W - 2))
    print(f"  TOPLAM: {total_records} kayit")
    print(sep + "\n")


# ─── Ana Akış ─────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Çoklu marka araç fiyat scraper")
    parser.add_argument(
        "--brand",
        nargs="*",
        help="Belirli marka(lar): vw skoda renault ford hyundai toyota chery dacia",
    )
    args = parser.parse_args()

    # Çalıştırılacak scraper'ları filtrele
    if args.brand:
        scrapers_to_run = [
            SCRAPER_MAP[b.lower()]
            for b in args.brand
            if b.lower() in SCRAPER_MAP
        ]
        if not scrapers_to_run:
            log.error("Bilinmeyen marka: %s", args.brand)
            sys.exit(1)
    else:
        scrapers_to_run = ALL_SCRAPERS

    log.info("=" * COL_W)
    log.info(
        "ÇOKLU MARKA FİYAT SCRAPER Başlatıldı — %s",
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    log.info("%d marka çalıştırılacak: %s",
             len(scrapers_to_run),
             ", ".join(s.brand for s in scrapers_to_run))
    log.info("=" * COL_W)

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    results: list[tuple] = []

    for scraper in scrapers_to_run:
        log.info("* %s scraper basliyor...", scraper.brand)
        try:
            records, method_used = scraper.run(conn)
            is_stale = method_used == "stale"
            is_failed = method_used == "failed"

            if records and not is_failed:
                inserted = save_records(
                    conn,
                    brand_name=scraper.brand,
                    records=records,
                    source=method_used,
                    is_stale=1 if is_stale else 0,
                )
                status = "fallback" if is_stale else "success"
                log_run(
                    conn,
                    brand=scraper.brand,
                    status=status,
                    method_used=method_used,
                    found=len(records),
                    message=f"{inserted} yeni kayit eklendi",
                )
                log.info(
                    "  [OK] %s - %d kayit (%s)%s",
                    scraper.brand, len(records), method_used,
                    " [STALE]" if is_stale else "",
                )
            else:
                log_run(
                    conn,
                    brand=scraper.brand,
                    status="error",
                    method_used=method_used,
                    found=0,
                    message="Veri bulunamadi",
                )
                log.error("  [FAIL] %s - veri bulunamadi!", scraper.brand)

            results.append((scraper.brand, records, method_used, is_stale))

        except Exception as exc:
            log.error("  [FAIL] %s - kritik hata: %s", scraper.brand, exc, exc_info=True)
            log_run(
                conn, scraper.brand, "error", "exception", 0, str(exc)
            )
            results.append((scraper.brand, [], "exception", False))

    conn.close()

    # Konsol tabloları
    for brand, records, method, is_stale in results:
        _print_brand_table(brand, records, method, is_stale)

    _print_summary(results)


if __name__ == "__main__":
    main()
