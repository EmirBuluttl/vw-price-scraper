"""
arabam_api.py  —  arabam.com.tr API üzerinden marka fiyat çekme
================================================================
arabam.com.tr yeni araç fiyat API'si herkese açıktır ve
Ford, Chery, Hyundai, Toyota dahil tüm markaları kapsar.

Bu modül, fallback olarak tüm scraper'ların kullanabileceği
merkezi bir arabam.com.tr yardımcısı sağlar.
"""

from __future__ import annotations

import re
from .base_scraper import http_get, fmt_price, parse_price_str

# arabam.com.tr sıfır araç fiyat endpoint'leri
ARABAM_BASE = "https://www.arabam.com"
ARABAM_SIFIR_API = "https://api.arabam.com/v5/catalog/sifir"
ARABAM_SIFIR_SEARCH = "https://www.arabam.com/sifir/{brand_slug}"

# Bilinen marka slug'ları
BRAND_SLUGS = {
    "ford":    "ford",
    "chery":   "chery",
    "hyundai": "hyundai",
    "toyota":  "toyota",
    "renault": "renault",
    "vw":      "volkswagen",
    "volkswagen": "volkswagen",
}

PRICE_RE = re.compile(r"([\d]{3}[\d.,\s]+)\s*(?:TL|₺)", re.IGNORECASE)
TL_INLINE = re.compile(r"₺\s*([\d.,]+)")


def fetch_arabam_api(brand_slug: str) -> list[dict]:
    """
    arabam.com.tr sıfır araç API'sini sorgula.
    Döndürülen liste: [{"model_name", "variant", "price_raw", "price_int", "currency"}]
    """
    url = f"https://api.arabam.com/v5/catalog/new-car/listings?make={brand_slug}&take=200&skip=0"
    try:
        r = http_get(url, headers={"Accept": "application/json",
                                   "Origin": "https://www.arabam.com",
                                   "Referer": "https://www.arabam.com/"})
        data = r.json()
    except Exception:
        # Fallback: HTML sayfasını parse et
        return fetch_arabam_html(brand_slug)

    records: list[dict] = []
    seen: set[tuple] = set()
    items = data if isinstance(data, list) else data.get("data", data.get("items", data.get("listings", [])))

    for item in items:
        if not isinstance(item, dict):
            continue
        model_name = (
            item.get("modelName") or item.get("model") or
            item.get("ModelName") or item.get("title") or ""
        )
        variant = (
            item.get("subModelName") or item.get("variant") or
            item.get("trim") or ""
        )
        price_val = (
            item.get("price") or item.get("Price") or
            item.get("listPrice") or 0
        )
        if not model_name:
            continue
        price_int = None
        if price_val:
            try:
                price_int = int(float(str(price_val).replace(",", "").replace(".", "").strip()))
                if price_int < 100_000:
                    price_int = None
            except (ValueError, TypeError):
                pass
        if not price_int:
            continue
        key = (model_name, variant)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "model_name": str(model_name)[:60],
                "variant": str(variant)[:60],
                "price_raw": fmt_price(price_int),
                "price_int": price_int,
                "currency": "TRY",
            }
        )
    return records


def fetch_arabam_html(brand_slug: str) -> list[dict]:
    """arabam.com.tr HTML sayfasından fiyat parse et."""
    from bs4 import BeautifulSoup
    url = f"https://www.arabam.com/sifir/{brand_slug}"
    try:
        r = http_get(url, headers={"Accept": "text/html"})
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return []
    records: list[dict] = []
    seen: set[str] = set()

    # Arabam ürün kartları: class içinde "listing" veya "car-card"
    cards = soup.find_all(
        ["div", "article", "li"],
        class_=re.compile(r"listing|car-card|product|item|vehicle", re.IGNORECASE)
    )
    for card in cards:
        text = card.get_text(separator="\n")
        m = TL_INLINE.search(text) or PRICE_RE.search(text)
        if not m:
            continue
        price_int = parse_price_str(m.group(1))
        if not price_int:
            continue
        heading = card.find(re.compile(r"h[1-6]|strong"))
        model_name = heading.get_text(strip=True)[:60] if heading else ""
        if not model_name or model_name in seen:
            continue
        seen.add(model_name)
        records.append(
            {
                "model_name": model_name,
                "variant": "",
                "price_raw": fmt_price(price_int),
                "price_int": price_int,
                "currency": "TRY",
            }
        )
    return records
