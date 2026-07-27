"""
app.py  —  Çoklu Marka Araç Fiyat Scraper Web UI & API Sunucusu
===============================================================
Kullanım:
    python app.py
    (Web tarayıcısında http://localhost:5000 adresine gidin)
"""

from __future__ import annotations

import csv
import io
import os
import sqlite3
import threading
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from scrapers.base_scraper import DB_PATH, init_db, log_run, save_records
from scrapers.vw_scraper import VWScraper
from scrapers.skoda_scraper import SkodaScraper
from scrapers.renault_scraper import RenaultScraper
from scrapers.ford_scraper import FordScraper
from scrapers.hyundai_scraper import HyundaiScraper
from scrapers.toyota_scraper import ToyotaScraper
from scrapers.chery_scraper import CheryScraper
from scrapers.dacia_scraper import DaciaScraper

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "car_price_scraper_secret_key_2026")

ALL_SCRAPERS = [
    VWScraper(),
    SkodaScraper(),
    RenaultScraper(),
    FordScraper(),
    HyundaiScraper(),
    ToyotaScraper(),
    CheryScraper(),
    DaciaScraper(),
]

SCRAPER_MAP = {s.brand.lower(): s for s in ALL_SCRAPERS}
SCRAPE_STATUS = {"running": False, "message": "Boşta", "progress": 0, "last_run": None}


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Yetkisiz erişim. Lütfen giriş yapın."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ─── Auth Rotaları ────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    conn = get_db()
    admin_user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    conn.close()

    if not admin_user:
        return redirect(url_for("setup_admin"))

    if session.get("user"):
        return redirect(url_for("index"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(admin_user["password_hash"], password):
            session["user"] = "admin"
            return redirect(url_for("index"))
        else:
            flash("Hatalı şifre! Lütfen tekrar deneyin.", "danger")

    return render_template("login.html")


@app.route("/setup-admin", methods=["GET", "POST"])
def setup_admin():
    conn = get_db()
    admin_user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()

    if admin_user:
        conn.close()
        return redirect(url_for("login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not password or len(password) < 4:
            flash("Şifre en az 4 karakter olmalıdır.", "warning")
        elif password != confirm:
            flash("Şifreler eşleşmiyor!", "danger")
        else:
            pwd_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                ("admin", pwd_hash, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
            session["user"] = "admin"
            flash("Admin şifreniz başarıyla oluşturuldu!", "success")
            return redirect(url_for("index"))

    conn.close()
    return render_template("setup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── Web UI Ana Sayfa ─────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ─── API Endpoints ───────────────────────────────────────────────────────────

@app.route("/api/summary")
@login_required
def api_summary():
    conn = get_db()
    
    # En son çekilen tarih
    last_date_row = conn.execute("SELECT MAX(scraped_date) as max_date FROM prices").fetchone()
    last_date = last_date_row["max_date"] if last_date_row and last_date_row["max_date"] else None

    # Toplam model/varyant sayısı (Son tarihteki)
    total_models = 0
    if last_date:
        total_models = conn.execute(
            "SELECT COUNT(*) as cnt FROM prices WHERE scraped_date = ?", (last_date,)
        ).fetchone()["cnt"]

    # Yeni Model sayısı (is_new_model = 1)
    new_models_cnt = conn.execute(
        "SELECT COUNT(DISTINCT model_name) as cnt FROM prices WHERE is_new_model = 1"
    ).fetchone()["cnt"]

    # Yeni Paket sayısı (is_new_variant = 1)
    new_variants_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM prices WHERE is_new_variant = 1"
    ).fetchone()["cnt"]

    # Fiyatı Değişenler sayısı (price_diff != 0)
    price_changes_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM prices WHERE price_diff != 0 AND price_diff IS NOT NULL"
    ).fetchone()["cnt"]

    # Marka Bazlı Özet Listesi
    brands_summary = conn.execute("""
        SELECT brand,
               MAX(scraped_date) as last_date,
               COUNT(*) as total_records,
               SUM(CASE WHEN scraped_date = ? THEN 1 ELSE 0 END) as today_records,
               SUM(CASE WHEN is_stale = 1 THEN 1 ELSE 0 END) as stale_count
        FROM prices
        GROUP BY brand
        ORDER BY brand
    """, (last_date,)).fetchall()

    conn.close()

    return jsonify({
        "last_date": last_date,
        "total_models": total_models,
        "new_models_cnt": new_models_cnt,
        "new_variants_cnt": new_variants_cnt,
        "price_changes_cnt": price_changes_cnt,
        "brands": [dict(b) for b in brands_summary],
        "scrape_status": SCRAPE_STATUS
    })


@app.route("/api/prices")
@login_required
def api_prices():
    brand = request.args.get("brand", "").strip()
    search = request.args.get("search", "").strip()
    only_new = request.args.get("only_new", "false").lower() == "true"
    only_changes = request.args.get("only_changes", "false").lower() == "true"
    sort_by = request.args.get("sort", "price_asc")

    conn = get_db()

    # En güncel tarihi bul
    last_date_row = conn.execute("SELECT MAX(scraped_date) as max_date FROM prices").fetchone()
    target_date = last_date_row["max_date"] if last_date_row else None

    if not target_date:
        conn.close()
        return jsonify({"prices": [], "total": 0})

    query = "SELECT * FROM prices WHERE 1=1"
    params = []

    if request.args.get("all_dates") != "true":
        query += " AND scraped_date = ?"
        params.append(target_date)

    if brand and brand.lower() != "all":
        query += " AND LOWER(brand) = ?"
        params.append(brand.lower())

    if search:
        query += " AND (LOWER(brand) LIKE ? OR LOWER(model_name) LIKE ? OR LOWER(variant) LIKE ?)"
        term = f"%{search.lower()}%"
        params.extend([term, term, term])

    if only_new:
        query += " AND (is_new_model = 1 OR is_new_variant = 1)"

    if only_changes:
        query += " AND price_diff != 0 AND price_diff IS NOT NULL"

    # Sıralama
    if sort_by == "price_asc":
        query += " ORDER BY price_int ASC"
    elif sort_by == "price_desc":
        query += " ORDER BY price_int DESC"
    elif sort_by == "brand":
        query += " ORDER BY brand ASC, price_int ASC"
    elif sort_by == "model":
        query += " ORDER BY model_name ASC, price_int ASC"
    else:
        query += " ORDER BY price_int ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    result_list = [dict(r) for r in rows]
    return jsonify({
        "prices": result_list,
        "total": len(result_list),
        "target_date": target_date
    })


def _run_scrapers_thread():
    global SCRAPE_STATUS
    SCRAPE_STATUS["running"] = True
    SCRAPE_STATUS["message"] = "Tarama başlatılıyor..."
    SCRAPE_STATUS["progress"] = 0

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    total_scrapers = len(ALL_SCRAPERS)
    for idx, scraper in enumerate(ALL_SCRAPERS):
        brand_name = scraper.brand
        SCRAPE_STATUS["message"] = f"{brand_name} taranıyor ({idx+1}/{total_scrapers})..."
        SCRAPE_STATUS["progress"] = int(((idx) / total_scrapers) * 100)

        try:
            records, method_used = scraper.run(conn)
            is_stale = method_used == "stale"
            if records and method_used != "failed":
                inserted = save_records(conn, brand_name, records, method_used, 1 if is_stale else 0)
                log_run(conn, brand_name, "fallback" if is_stale else "success", method_used, len(records), f"{inserted} yeni kayıt")
            else:
                log_run(conn, brand_name, "error", method_used, 0, "Veri bulunamadı")
        except Exception as exc:
            log_run(conn, brand_name, "error", "exception", 0, str(exc))

    conn.close()
    SCRAPE_STATUS["running"] = False
    SCRAPE_STATUS["message"] = "Tarama tamamlandı!"
    SCRAPE_STATUS["progress"] = 100
    SCRAPE_STATUS["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/api/trigger-scrape", methods=["POST"])
@login_required
def trigger_scrape():
    global SCRAPE_STATUS
    if SCRAPE_STATUS["running"]:
        return jsonify({"status": "running", "message": "Zaten aktif bir tarama devam ediyor."})

    t = threading.Thread(target=_run_scrapers_thread)
    t.start()
    return jsonify({"status": "started", "message": "Tarama arka planda başlatıldı."})


@app.route("/api/export")
@login_required
def api_export():
    conn = get_db()
    rows = conn.execute("""
        SELECT brand, model_name, variant, price_raw, price_int, currency,
               source, is_stale, is_new_model, is_new_variant, price_diff, price_change_pct, scraped_at
        FROM prices
        ORDER BY brand, model_name, price_int
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Marka", "Model", "Varyant", "Fiyat Metni", "Fiyat (Sayı)", "Para Birimi",
        "Kaynak", "Eski Veri mi?", "Yeni Model mi?", "Yeni Paket mi?", "Fiyat Değişim TL", "Fiyat Değişim %", "Tarih"
    ])
    for r in rows:
        writer.writerow(list(r))

    output.seek(0)
    return Response(
        output.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=car_prices_export.csv"},
    )


if __name__ == "__main__":
    print("=" * 70)
    print("  ÇOKLU MARKA ARAÇ FİYAT SCRAPER WEB PANELİ")
    print("  Tarayıcıda açın: http://localhost:5000")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=True)
