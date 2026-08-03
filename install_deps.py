"""
install_deps.py — Kurumsal Bilgisayarlar İçin Otomatik Bağımlılık Yükleyici
==========================================================================
Kullanım:
    python install_deps.py
"""

import sys
import subprocess

REQUIRED_PACKAGES = [
    "openpyxl",
    "requests",
    "beautifulsoup4",
    "lxml",
    "flask",
    "werkzeug"
]

def main():
    print("=" * 70)
    print(" 🚗 Kurumsal Araç Fiyat Scraper - Otomatik Paket Yükleyici")
    print(f" Aktif Python Yolu: {sys.executable}")
    print("=" * 70)

    for pkg in REQUIRED_PACKAGES:
        print(f"\n[+] '{pkg}' paketi kontrol ediliyor/yükleniyor...")
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            pkg,
            "--trusted-host", "pypi.org",
            "--trusted-host", "files.pythonhosted.org"
        ]
        try:
            subprocess.check_call(cmd)
            print(f"✅ '{pkg}' başarıyla doğrulandı/yüklendi!")
        except Exception as err:
            print(f"❌ '{pkg}' yüklenirken hata oluştu: {err}")

    print("\n" + "=" * 70)
    print(" Test çalıştırılıyor...")
    try:
        import openpyxl
        import flask
        import requests
        print("🎉 TEBRİKLER! Tüm paketler başarıyla yüklendi. 'python app.py' çalıştırabilirsiniz!")
    except Exception as e:
        print(f"⚠️ Hata devam ediyor: {e}")
    print("=" * 70)

if __name__ == "__main__":
    main()
