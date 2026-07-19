"""
view_multi_data.py  —  Çoklu marka veritabanı görüntüleyici
============================================================
Kullanım:
    python view_multi_data.py                        # Bugünün tüm verileri
    python view_multi_data.py --brand renault        # Tek marka
    python view_multi_data.py --all                  # Tüm geçmiş kayıtlar
    python view_multi_data.py --history              # Fiyat geçmişi
    python view_multi_data.py --history --brand ford # Tek markanın geçmişi
    python view_multi_data.py --logs                 # Çalışma logları
    python view_multi_data.py --summary              # Marka özet tablosu
"""

from __future__ import annotations

import argparse
import io
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Windows terminal UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = Path(__file__).parent / "car_prices.db"
COL = 90


def get_conn() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print("Veritabanı bulunamadı. Önce multi_scraper.py'yi çalıştırın.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


# ─── Görüntüleme Fonksiyonları ────────────────────────────────────────────────

def show_today(conn: sqlite3.Connection, brand: str | None) -> None:
    today = date.today().isoformat()
    query = """SELECT brand, model_name, variant, price_raw, source, is_stale, scraped_at
               FROM prices WHERE scraped_date = ?"""
    params = [today]
    if brand:
        query += " AND LOWER(brand) = ?"
        params.append(brand.lower())
    query += " ORDER BY brand, price_int"
    rows = conn.execute(query, params).fetchall()
    print(f"\n[Bugün] {today} — {len(rows)} kayıt\n")
    print(f"  {'MARKA':<14} {'MODEL':<28} {'VARYANT':<22} {'FİYAT':>16}  KAYNAK   SAAT")
    print("  " + "─" * (COL - 2))
    for r in rows:
        stale = " ⚠" if r[5] else ""
        print(
            f"  {r[0]:<14} {(r[1] or '')[:26]:<28} {(r[2] or '')[:20]:<22}"
            f" {(r[3] or '—'):>16}  {(r[4] or ''):<8}{stale}  {r[6]}"
        )


def show_all(conn: sqlite3.Connection, brand: str | None) -> None:
    query = """SELECT scraped_date, brand, model_name, variant, price_raw, source, is_stale
               FROM prices"""
    params: list = []
    if brand:
        query += " WHERE LOWER(brand) = ?"
        params.append(brand.lower())
    query += " ORDER BY scraped_date DESC, brand, price_int"
    rows = conn.execute(query, params).fetchall()
    print(f"\n[Tüm Kayıtlar] {len(rows)} adet\n")
    print(f"  {'TARİH':<12} {'MARKA':<14} {'MODEL':<26} {'VARYANT':<20} {'FİYAT':>16}  KAYNAK")
    print("  " + "─" * (COL - 2))
    for r in rows:
        stale = " ⚠" if r[6] else ""
        print(
            f"  {r[0]:<12} {r[1]:<14} {(r[2] or '')[:24]:<26}"
            f" {(r[3] or '')[:18]:<20} {(r[4] or '—'):>16}  {(r[5] or '')}{stale}"
        )


def show_history(conn: sqlite3.Connection, brand: str | None) -> None:
    query = """SELECT brand, model_name, scraped_date, price_raw, price_int, is_stale
               FROM prices"""
    params: list = []
    if brand:
        query += " WHERE LOWER(brand) = ?"
        params.append(brand.lower())
    query += " ORDER BY brand, model_name, scraped_date"
    rows = conn.execute(query, params).fetchall()

    by_brand_model: dict = defaultdict(list)
    for r in rows:
        key = (r[0], r[1])
        by_brand_model[key].append({"date": r[2], "price_raw": r[3], "price_int": r[4], "stale": r[5]})

    print("\n[Fiyat Geçmişi]\n")
    for (brand_name, model_name), entries in sorted(by_brand_model.items()):
        print(f"  {brand_name} — {model_name}")
        prev = None
        for e in entries:
            change = ""
            if prev and e["price_int"] and prev["price_int"]:
                diff = e["price_int"] - prev["price_int"]
                if diff > 0:
                    change = f"  ▲ +{diff:,} TL".replace(",", ".")
                elif diff < 0:
                    change = f"  ▼ {diff:,} TL".replace(",", ".")
                else:
                    change = "  = değişmedi"
            stale = " ⚠" if e["stale"] else ""
            print(f"    {e['date']}  {(e['price_raw'] or '—'):>20}{change}{stale}")
            prev = e
        print()


def show_logs(conn: sqlite3.Connection, brand: str | None) -> None:
    query = "SELECT brand, run_at, status, method_used, models_found, message FROM scrape_log"
    params: list = []
    if brand:
        query += " WHERE LOWER(brand) = ?"
        params.append(brand.lower())
    query += " ORDER BY run_at DESC LIMIT 50"
    rows = conn.execute(query, params).fetchall()
    print(f"\n[Çalışma Logları] Son {len(rows)} kayıt\n")
    print(f"  {'MARKA':<14} {'ZAMAN':<22} {'DURUM':<10} {'YÖNTEM':<16} {'KAYIT':>6}  MESAJ")
    print("  " + "─" * (COL - 2))
    for r in rows:
        durum = "✓ OK  " if r[2] == "success" else ("⚠ FALL" if r[2] == "fallback" else "✗ HATA")
        print(
            f"  {r[0]:<14} {r[1]:<22} {durum:<10} {(r[3] or ''):<16}"
            f" {r[4]:>6}  {r[5] or ''}"
        )


def show_summary(conn: sqlite3.Connection) -> None:
    """Her markanın son çekim tarihi ve kayıt sayısı."""
    rows = conn.execute(
        """SELECT brand,
                  MAX(scraped_date) as last_date,
                  COUNT(*) as total,
                  SUM(CASE WHEN scraped_date = date('now') THEN 1 ELSE 0 END) as today,
                  SUM(CASE WHEN is_stale = 1 THEN 1 ELSE 0 END) as stale_count
           FROM prices
           GROUP BY brand
           ORDER BY brand"""
    ).fetchall()
    print("\n[Marka Özeti]\n")
    print(f"  {'MARKA':<16} {'SON TARİH':<14} {'TOPLAM':>8} {'BUGÜN':>8} {'STALE':>8}")
    print("  " + "─" * 58)
    for r in rows:
        print(f"  {r[0]:<16} {r[1]:<14} {r[2]:>8} {r[3]:>8} {r[4]:>8}")


# ─── Ana Akış ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Çoklu marka fiyat veritabanı görüntüleyici")
    parser.add_argument("--brand",   help="Marka filtresi (örn: renault, ford, vw)")
    parser.add_argument("--all",     action="store_true", help="Tüm geçmiş kayıtlar")
    parser.add_argument("--today",   action="store_true", help="Bugünkü kayıtlar (Varsayılan)")
    parser.add_argument("--history", action="store_true", help="Fiyat geçmişi")
    parser.add_argument("--logs",    action="store_true", help="Çalışma logları")
    parser.add_argument("--summary", action="store_true", help="Marka özet tablosu")
    args = parser.parse_args()

    conn = get_conn()
    if args.summary:
        show_summary(conn)
    elif args.all:
        show_all(conn, args.brand)
    elif args.history:
        show_history(conn, args.brand)
    elif args.logs:
        show_logs(conn, args.brand)
    else:
        # Default or explicit --today
        show_today(conn, args.brand)
    conn.close()


if __name__ == "__main__":
    main()
