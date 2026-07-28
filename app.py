"""
app.py  —  Coklu Marka Arac Fiyat Scraper Web UI & API Sunucusu
===============================================================
Kullanim:
    python app.py
    (Web tarayicisinda http://localhost:5000 adresine gidin)
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
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

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
SCRAPE_STATUS = {"running": False, "message": "Bosta", "progress": 0, "last_run": None}


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
                return jsonify({"error": "Yetkisiz erisim. Lutfen giris yapin."}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# --- Auth Rotalari ------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    if not users:
        return redirect(url_for("setup_admin"))

    if session.get("user"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username_input = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        matched_user = None
        for u in users:
            if username_input:
                if u["username"].lower() == username_input.lower() and check_password_hash(u["password_hash"], password):
                    matched_user = u
                    break
            else:
                if check_password_hash(u["password_hash"], password):
                    matched_user = u
                    break

        if matched_user:
            session["user"] = matched_user["username"]
            return redirect(url_for("index"))
        else:
            flash("Hatali kullanici adi veya sifre!", "danger")

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
            flash("Sifre en az 4 karakter olmalidir.", "warning")
        elif password != confirm:
            flash("Sifreler eslesmiyor!", "danger")
        else:
            pwd_hash = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                ("admin", pwd_hash, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
            session["user"] = "admin"
            flash("Admin sifreniz basariyla olusturuldu!", "success")
            return redirect(url_for("index"))

    conn.close()
    return render_template("setup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- Web UI Ana Sayfa ---------------------------------------------------------

@app.route("/")
@login_required
def index():
    return render_template("index.html")


# --- API Endpoints -----------------------------------------------------------

@app.route("/api/summary")
@login_required
def api_summary():
    conn = get_db()
    
    last_date_row = conn.execute("SELECT MAX(scraped_date) as max_date FROM prices").fetchone()
    last_date = last_date_row["max_date"] if last_date_row and last_date_row["max_date"] else None

    # Toplam model/varyant sayisi (is_latest = 1)
    total_models = conn.execute(
        "SELECT COUNT(*) as cnt FROM prices WHERE is_latest = 1"
    ).fetchone()["cnt"]

    # Yeni Model sayisi (is_new_model = 1 AND is_latest = 1)
    new_models_cnt = conn.execute(
        "SELECT COUNT(DISTINCT v.model_id) as cnt FROM prices p JOIN variants v ON p.variant_id = v.id WHERE p.is_new_model = 1 AND p.is_latest = 1"
    ).fetchone()["cnt"]

    # Yeni Paket sayisi (is_new_variant = 1 AND is_latest = 1)
    new_variants_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM prices WHERE is_new_variant = 1 AND is_latest = 1"
    ).fetchone()["cnt"]

    # Fiyati Degisenler sayisi (price_diff != 0 AND is_latest = 1)
    price_changes_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM prices WHERE price_diff != 0 AND price_diff IS NOT NULL AND is_latest = 1"
    ).fetchone()["cnt"]

    # Marka Bazli Ozet Listesi
    brands_summary = conn.execute("""
        SELECT b.name as brand,
               MAX(p.scraped_date) as last_date,
               COUNT(p.id) as total_records,
               SUM(CASE WHEN p.is_latest = 1 THEN 1 ELSE 0 END) as today_records
        FROM brands b
        LEFT JOIN models m ON m.brand_id = b.id
        LEFT JOIN variants v ON v.model_id = m.id
        LEFT JOIN prices p ON p.variant_id = v.id
        GROUP BY b.id, b.name
        ORDER BY b.name
    """).fetchall()

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
    fuel = request.args.get("fuel", "").strip()
    body = request.args.get("body", "").strip()
    trans = request.args.get("trans", "").strip()
    only_new = request.args.get("only_new", "false").lower() == "true"
    only_changes = request.args.get("only_changes", "false").lower() == "true"
    sort_by = request.args.get("sort", "price_asc")

    conn = get_db()

    last_date_row = conn.execute("SELECT MAX(scraped_date) as max_date FROM prices").fetchone()
    target_date = last_date_row["max_date"] if last_date_row else None

    query = """
        SELECT p.id, b.name as brand, m.name as model_name, v.name as variant,
               v.fuel_type, v.transmission, v.engine_power, m.body_type,
               p.price_raw, p.price_int, p.currency, p.scraped_at, p.scraped_date,
               p.is_latest, p.is_new_model, p.is_new_variant, p.previous_price_int,
               p.price_diff, p.price_change_pct, p.source
        FROM prices p
        JOIN variants v ON p.variant_id = v.id
        JOIN models m ON v.model_id = m.id
        JOIN brands b ON m.brand_id = b.id
        WHERE 1=1
    """
    params = []

    if request.args.get("all_dates") != "true":
        query += " AND p.is_latest = 1"

    if brand and brand.lower() != "all":
        query += " AND LOWER(b.name) = ?"
        params.append(brand.lower())

    if fuel and fuel.lower() != "all":
        query += " AND LOWER(v.fuel_type) = ?"
        params.append(fuel.lower())

    if body and body.lower() != "all":
        query += " AND LOWER(m.body_type) LIKE ?"
        params.append(f"%{body.lower()}%")

    if trans and trans.lower() != "all":
        query += " AND LOWER(v.transmission) = ?"
        params.append(trans.lower())

    if search:
        query += " AND (LOWER(b.name) LIKE ? OR LOWER(m.name) LIKE ? OR LOWER(v.name) LIKE ?)"
        term = f"%{search.lower()}%"
        params.extend([term, term, term])

    if only_new:
        query += " AND (p.is_new_model = 1 OR p.is_new_variant = 1)"

    if only_changes:
        query += " AND p.price_diff != 0 AND p.price_diff IS NOT NULL"

    # Siralama
    if sort_by == "price_asc":
        query += " ORDER BY p.price_int ASC"
    elif sort_by == "price_desc":
        query += " ORDER BY p.price_int DESC"
    elif sort_by == "brand":
        query += " ORDER BY b.name ASC, p.price_int ASC"
    elif sort_by == "model":
        query += " ORDER BY m.name ASC, p.price_int ASC"
    else:
        query += " ORDER BY p.price_int ASC"

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
    SCRAPE_STATUS["message"] = "Tarama baslatiliyor..."
    SCRAPE_STATUS["progress"] = 0

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    total_scrapers = len(ALL_SCRAPERS)
    for idx, scraper in enumerate(ALL_SCRAPERS):
        brand_name = scraper.brand
        SCRAPE_STATUS["message"] = f"{brand_name} taraniyor ({idx+1}/{total_scrapers})..."
        SCRAPE_STATUS["progress"] = int(((idx) / total_scrapers) * 100)

        try:
            records, method_used = scraper.run(conn)
            is_stale = method_used == "stale"
            if records and method_used != "failed":
                inserted = save_records(conn, brand_name, records, method_used, 1 if is_stale else 0)
                log_run(conn, brand_name, "fallback" if is_stale else "success", method_used, len(records), f"{inserted} yeni kayit")
            else:
                log_run(conn, brand_name, "error", method_used, 0, "Veri bulunamadi")
        except Exception as exc:
            log_run(conn, brand_name, "error", "exception", 0, str(exc))

    conn.close()
    SCRAPE_STATUS["running"] = False
    SCRAPE_STATUS["message"] = "Tarama tamamlandi!"
    SCRAPE_STATUS["progress"] = 100
    SCRAPE_STATUS["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/api/trigger-scrape", methods=["POST"])
@login_required
def trigger_scrape():
    global SCRAPE_STATUS
    if session.get("user") != "admin":
        return jsonify({"status": "error", "message": "Canli tarama baslatma yetkisi sadece Admin kullanicisindadir."}), 403

    if SCRAPE_STATUS["running"]:
        return jsonify({"status": "running", "message": "Zaten aktif bir tarama devam ediyor."})

    t = threading.Thread(target=_run_scrapers_thread)
    t.start()
    return jsonify({"status": "started", "message": "Tarama arka planda baslatildi."})


@app.route("/api/export")
@login_required
def api_export():
    conn = get_db()
    rows = conn.execute("""
        SELECT b.name as brand, m.name as model_name, v.name as variant,
               p.price_raw, p.price_int, p.currency, p.source,
               p.is_latest, p.is_new_model, p.is_new_variant, p.price_diff, p.price_change_pct, p.scraped_at
        FROM prices p
        JOIN variants v ON p.variant_id = v.id
        JOIN models m ON v.model_id = m.id
        JOIN brands b ON m.brand_id = b.id
        WHERE p.is_latest = 1
        ORDER BY b.name, m.name, p.price_int
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Marka", "Model", "Varyant", "Fiyat Metni", "Fiyat (Sayi)", "Para Birimi",
        "Kaynak", "En Guncel (Latest)?", "Yeni Model mi?", "Yeni Paket mi?", "Fiyat Degisim TL", "Fiyat Degisim %", "Tarih"
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
    print("  COKLU MARKA ARAC FIYAT SCRAPER WEB PANELI")
    print("  Tarayicida acin: http://localhost:5000")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=True)
