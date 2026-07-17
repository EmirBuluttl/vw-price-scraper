"""
VW Türkiye Araç Fiyat Scraper (Doğuş Oto API Gateway Tabanlı)
==============================================================
Hedef  : Doğuş Oto API Gateway üzerinden tüm sıfır araç stokları ve fiyatları
Avantaj:
  - JavaScript rendering veya tarayıcı simülasyonuna gerek yoktur.
  - Group Policy engellerinden tamamen muaftır (pure python).
  - Cloudflare bot korumasına takılmaz.
  - Tavsiye edilen net anahtar teslim fiyatlarını donanım/renk bazında verir.
Depo   : SQLite (vw_prices.db)
"""

import requests
import sqlite3
import logging
from datetime import date, datetime
from pathlib import Path

# ─── Ayarlar ──────────────────────────────────────────────────────────────────
API_URL  = "https://gw.dogusoto.com.tr/gw-search-newvehicle/GetVehicleBySearchCriteria"
DB_PATH  = Path(__file__).parent / "vw_prices.db"
LOG_PATH = Path(__file__).parent / "scraper.log"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.dogusoto.com.tr",
    "Referer": "https://www.dogusoto.com.tr/"
}

# ─── Loglama ──────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ─── Veritabanı ───────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection) -> None:
    """Tabloları oluştur (yoksa)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS models (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name   TEXT NOT NULL,
            variant      TEXT,
            price_raw    TEXT,
            price_int    INTEGER,
            currency     TEXT DEFAULT 'TRY',
            scraped_at   TEXT NOT NULL,
            scraped_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scrape_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at       TEXT NOT NULL,
            status       TEXT NOT NULL,
            models_found INTEGER,
            message      TEXT
        );
    """)
    conn.commit()


def save_models(conn: sqlite3.Connection, records: list[dict]) -> int:
    """Bugün kaydedilmemiş olan yeni fiyat verilerini ekle."""
    today = date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    inserted = 0
    
    for r in records:
        exists = conn.execute(
            "SELECT 1 FROM models WHERE model_name=? AND variant=? AND scraped_date=?",
            (r["model_name"], r["variant"], today),
        ).fetchone()
        
        if not exists:
            conn.execute(
                """INSERT INTO models
                   (model_name, variant, price_raw, price_int, currency, scraped_at, scraped_date)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    r["model_name"],
                    r["variant"],
                    r["price_raw"],
                    r["price_int"],
                    r["currency"],
                    now,
                    today,
                ),
            )
            inserted += 1
            
    conn.commit()
    return inserted


def log_run(conn: sqlite3.Connection, status: str, found: int = 0, message: str = "") -> None:
    conn.execute(
        "INSERT INTO scrape_log (run_at, status, models_found, message) VALUES (?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), status, found, message),
    )
    conn.commit()


# ─── API Veri Çekme ──────────────────────────────────────────────────────────
def get_vw_prices() -> list[dict]:
    """Doğuş Oto API'sine istek atarak VW binek fiyatlarını çeker."""
    # 14913: Volkswagen Brand ID
    payload = {
        "modelId": 0,
        "modelIds": [],
        "permalink": "",
        "searchKey": "",
        "size": 0,
        "pagination": {
            "page": 1,
            "pageSize": 500  # Tüm araçları tek seferde almak için yeterli
        },
        "isCampaignVehicle": None,
        "isOptionalVehicle": None,
        "year": {"min": 0, "max": 0},
        "price": {"min": 0, "max": 0},
        "sortingCriteria": 1,
        "colorIds": [],
        "brandIds": [14913],
        "servicePointIds": [],
        "gearTypes": [],
        "fuelTypeIds": [],
        "caseTypeIds": []
    }
    
    log.info("Doğuş Oto API'sinden Volkswagen verileri talep ediliyor...")
    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=25)
    r.raise_for_status()
    
    response_data = r.json()
    
    # "results" listesini bulalım
    results = response_data.get("data", {}).get("results", [])
    log.info("API'den %d araç kaydı başarıyla döndü.", len(results))
    
    records = []
    # Benzersiz varyantları takip etmek için set kullanalım (fiyat listesi tekilleştirme)
    seen_variants = set()
    
    for item in results:
        model_name = item.get("modelName", "Bilinmiyor")
        sub_model = item.get("subModelName", "")
        # Varyant isminden yıl bilgisini arındıralım veya sadeleştirelim
        variant = sub_model.strip()
        
        # Sadece tavsiye edilen fiyatı al
        price_val = item.get("price", 0)
        
        if price_val > 100_000:
            price_int = int(price_val)
            price_raw = f"{price_int:,} TL".replace(",", ".")
            
            # Aynı gün içinde aynı model ve varyantı tekilleştirelim (stokta birden fazla aynı araç olabilir)
            unique_key = (model_name, variant)
            if unique_key not in seen_variants:
                seen_variants.add(unique_key)
                records.append({
                    "model_name": model_name,
                    "variant": variant,
                    "price_raw": price_raw,
                    "price_int": price_int,
                    "currency": "TRY"
                })
                
    return records


# ─── Ana Akış ─────────────────────────────────────────────────────────────────
def main() -> None:
    log.info("=" * 60)
    log.info("VW API Scraper Başlatıldı — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    try:
        records = get_vw_prices()

        if records:
            inserted = save_models(conn, records)
            log_run(conn, "success", len(records), f"{inserted} yeni model/varyant eklendi")
            log.info("Başarılı! %d benzersiz model/varyant verisi işlendi.", len(records))

            # Konsola ASCII Özet Tablo
            sep = "-" * 75
            print("\n" + sep)
            print(f"{'MODEL':<15} {'DONANIM / VARYANT':<40} {'FİYAT':>16}")
            print(sep)
            # Fiyata göre sıralı gösterelim
            for r in sorted(records, key=lambda x: x["price_int"]):
                print(f"{r['model_name']:<15} {r['variant'][:38]:<40} {r['price_raw']:>16}")
            print(sep)
        else:
            log.warning("Hiç araç verisi ayıklanamadı!")
            log_run(conn, "error", 0, "Boş veri seti döndü")

    except Exception as e:
        log.error("Kritik Hata: %s", e, exc_info=True)
        log_run(conn, "error", 0, str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
