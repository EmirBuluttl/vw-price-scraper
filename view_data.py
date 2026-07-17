"""
Veritabanindaki verileri gormek icin yardimci script.
Kullanim:
    python view_data.py              # bugunun verisi
    python view_data.py --all        # tum veriler
    python view_data.py --history    # fiyat gecmisi ozeti
    python view_data.py --logs       # calisma loglari
"""

import sys
import io
# Windows terminal'de UTF-8 zorla
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


import sqlite3
import argparse
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent / "vw_prices.db"


def get_conn():
    if not DB_PATH.exists():
        print("Veritabani bulunamadi. Once scraper.py yi calistirin.")
        exit(1)
    return sqlite3.connect(DB_PATH)


def show_today(conn):
    today = date.today().isoformat()
    rows = conn.execute(
        """SELECT model_name, variant, price_raw, scraped_at
           FROM models WHERE scraped_date = ?
           ORDER BY price_int""",
        (today,),
    ).fetchall()
    print(f"\n[Bugun] {today} tarihinde cekilen veriler -- {len(rows)} model\n")
    print(f"{'MODEL':<25} {'VARYANT':<35} {'FIYAT':>20}  ZAMAN")
    print("-" * 95)
    for r in rows:
        print(f"{r[0]:<25} {(r[1] or ''):<35} {r[2]:>20}  {r[3]}")


def show_all(conn):
    rows = conn.execute(
        """SELECT scraped_date, model_name, variant, price_raw
           FROM models ORDER BY scraped_date DESC, price_int"""
    ).fetchall()
    print(f"\n[Tum Kayitlar] {len(rows)} adet\n")
    print(f"{'TARIH':<12} {'MODEL':<22} {'VARYANT':<30} {'FIYAT':>20}")
    print("-" * 90)
    for r in rows:
        print(f"{r[0]:<12} {r[1]:<22} {(r[2] or ''):<30} {r[3]:>20}")


def show_history(conn):
    """Her model icin fiyat degisimini goster."""
    rows = conn.execute(
        """SELECT model_name, scraped_date, price_raw, price_int
           FROM models
           ORDER BY model_name, scraped_date"""
    ).fetchall()

    from collections import defaultdict
    by_model = defaultdict(list)
    for r in rows:
        by_model[r[0]].append({"date": r[1], "price_raw": r[2], "price_int": r[3]})

    print("\n[Fiyat Gecmisi] Model bazli\n")
    for model, entries in sorted(by_model.items()):
        print(f"  {model}")
        prev = None
        for e in entries:
            change = ""
            if prev and e["price_int"] and prev["price_int"]:
                diff = e["price_int"] - prev["price_int"]
                if diff > 0:
                    change = f"  ARTIS: +{diff:,} TL"
                elif diff < 0:
                    change = f"  DUSUS: {diff:,} TL"
                else:
                    change = "  DEGISMEDI"
            print(f"    {e['date']}  {e['price_raw']:>20}{change}")
            prev = e
        print()


def show_logs(conn):
    rows = conn.execute(
        "SELECT run_at, status, models_found, message FROM scrape_log ORDER BY run_at DESC LIMIT 20"
    ).fetchall()
    print("\n[Calisma Loglari] Son 20 kayit\n")
    print(f"{'ZAMAN':<22} {'DURUM':<10} {'MODEL':>8}  MESAJ")
    print("-" * 80)
    for r in rows:
        durum = "[OK]  " if r[1] == "success" else "[HATA]"
        print(f"{r[0]:<22} {durum} {r[1]:<8} {r[2]:>8}  {r[3]}")


def main():
    parser = argparse.ArgumentParser(description="VW fiyat veritabani goruntuleyici")
    parser.add_argument("--all",     action="store_true", help="Tum kayitlari goster")
    parser.add_argument("--history", action="store_true", help="Fiyat gecmisini goster")
    parser.add_argument("--logs",    action="store_true", help="Calisma loglarini goster")
    args = parser.parse_args()

    conn = get_conn()
    if args.all:
        show_all(conn)
    elif args.history:
        show_history(conn)
    elif args.logs:
        show_logs(conn)
    else:
        show_today(conn)
    conn.close()


if __name__ == "__main__":
    main()
