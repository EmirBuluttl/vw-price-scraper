"""
reset_admin.py  —  Admin Kullanıcı Yetkilerini ve Şifresini Kendinize Bağlama Scripti
===================================================================================
Kullanım:
    python reset_admin.py --username admin --password "SizinBelirlediginizSifre"
"""

import sqlite3
import argparse
import sys
import io
from werkzeug.security import generate_password_hash

# Windows konsol Unicode desteği
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = "car_prices.db"

def set_admin_credentials(username: str, raw_password: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Tablo var mı kontrol et
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        );
    """)
    
    pw_hash = generate_password_hash(raw_password)
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    
    # Var olan tüm admin yetkilerini temizle ve sadece bu kullanıcıya tekil yetki bağla
    conn.execute("DELETE FROM users")
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, pw_hash, now)
    )
    conn.commit()
    conn.close()
    
    print("=" * 60)
    print(" PROJE YETKILERI BASARIYLA KENDINIZE BAGLANDI!")
    print("=" * 60)
    print(f"  Kullanici Adi : {username}")
    print(f"  Yeni Sifre    : {'*' * len(raw_password)}")
    print(f"  Erisim Paneli : http://localhost:5000/login")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Admin Şifresini ve Yetkilerini Kendinize Bağlayın")
    parser.add_argument("--username", default="admin", help="Admin kullanıcı adı")
    parser.add_argument("--password", required=True, help="Belirleyeceğiniz yeni şifre")
    
    args = parser.parse_args()
    set_admin_credentials(args.username, args.password)
