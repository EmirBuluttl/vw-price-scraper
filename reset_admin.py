"""
reset_admin.py  —  Proje Yetki Bağlama ve Geçici Sunum Hesabı Yönetimi
====================================================================
Kullanım:
  1. Ana Şifrenizi Değiştirip Yetkiyi Üzerinize Alma:
     python reset_admin.py --password "KendiGizliSifreniz"

  2. Sunum Yapacak Kişiye Geçici "Demo" Hesabı Açma:
     python reset_admin.py --create-demo "DemoSifresi123"

  3. Sunum Yapan Kişinin Erişimini Anında İPTAL ETME (Kapatma):
     python reset_admin.py --revoke-demo
"""

import sqlite3
import argparse
import sys
import io
from datetime import datetime
from werkzeug.security import generate_password_hash

# Windows konsol Unicode desteği
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = "car_prices.db"

def init_users_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        );
    """)

def set_admin_credentials(raw_password: str, username: str = "admin"):
    conn = sqlite3.connect(DB_PATH)
    init_users_table(conn)
    
    pw_hash = generate_password_hash(raw_password)
    now = datetime.now().isoformat(timespec="seconds")
    
    # Admin yetkisini güncelle veya ekle
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, pw_hash, now)
    )
    conn.commit()
    conn.close()
    
    print("=" * 65)
    print(" [OK] PROJE ANA YETKISI VE ADMIN SIFRESI KENDINIZE BAGLANDI!")
    print("=" * 65)
    print(f"  Kullanici Adi : {username}")
    print(f"  Yeni Sifre    : {'*' * len(raw_password)}")
    print(f"  Erisim Adresi : http://localhost:5000/login")
    print("=" * 65)

def create_demo_user(demo_password: str):
    conn = sqlite3.connect(DB_PATH)
    init_users_table(conn)
    
    pw_hash = generate_password_hash(demo_password)
    now = datetime.now().isoformat(timespec="seconds")
    
    conn.execute("DELETE FROM users WHERE username = 'demo'")
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES ('demo', ?, ?)",
        (pw_hash, now)
    )
    conn.commit()
    conn.close()
    
    print("=" * 65)
    print(" [OK] SUNUM YAPACAK KISI ICIN GECICI DEMO HESABI OLUSTURULDU!")
    print("=" * 65)
    print("  Kullanici Adi : demo")
    print(f"  Demo Sifresi  : {demo_password}")
    print("  Not           : Bu bilgiyi sunum yapacak kisiye verebilirsiniz.")
    print("=" * 65)

def revoke_demo_user():
    conn = sqlite3.connect(DB_PATH)
    init_users_table(conn)
    
    conn.execute("DELETE FROM users WHERE username = 'demo'")
    conn.commit()
    conn.close()
    
    print("=" * 65)
    print(" [KAPATILDI] DEMO HESABININ ERISIMI ANINDA IPTAL EDILDI!")
    print("=" * 65)
    print("  Sunum yapan kisi artik bu hesapla giris yapamaz.")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proje Yetki ve Sunum Hesabı Yönetimi")
    parser.add_argument("--password", help="Kendi Admin ana şifrenizi belirleyin")
    parser.add_argument("--username", default="admin", help="Admin kullanıcı adı")
    parser.add_argument("--create-demo", help="Sunum yapacak kişiye vereceğiniz geçici demo şifresi")
    parser.add_argument("--revoke-demo", action="store_true", help="Demo hesabının erişimini anında kapatır/iptal eder")
    
    args = parser.parse_args()

    if args.revoke_demo:
        revoke_demo_user()
    elif args.create_demo:
        create_demo_user(args.create_demo)
    elif args.password:
        set_admin_credentials(args.password, args.username)
    else:
        parser.print_help()
