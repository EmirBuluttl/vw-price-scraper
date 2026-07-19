"""
renault_scraper.py  —  Renault Türkiye fiyat scraper'ı
======================================================
Birincil : renault.com.tr ana sayfa (SSR HTML içinde model kartları)
Fallback A: renault.com.tr/renault-fiyat-listeleri.html (HTML tablo arama)
Fallback B: Ürün detay sayfaları üzerinden fiyat çekme

Renault sitesi React SSR kullanır; JS çalıştırmadan ham HTML'de fiyatlar
zaten gömülü gelir — Playwright gerekmez.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

# Model adları içinde kırpılacak ifadeler
_STRIP = re.compile(r"\s+")

# renault.com.tr ana sayfasından doğrudan parse edilen fiyat kartı yapısı:
# <div class="VehicleModelCard__modelName_price">MODEL ADI
#   <div class="ModelStartingPrice">
#     <span class="NormalizedPrice ...">başlangıç fiyatı ₺X.XXX.XXX ...
PRICE_RE = re.compile(r"₺\s*([\d.,]+)")


def _clean_model(raw: str) -> str:
    return _STRIP.sub(" ", raw).strip()


def _parse_vehicle_cards(html: str) -> list[dict]:
    """VehicleModelCard div'lerini parse et."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[str] = set()

    cards = soup.find_all("div", class_=re.compile(r"VehicleModelCard__modelName_price"))
    for card in cards:
        # Model adı: div'in doğrudan metin içeriği (alt elemanlardan önce)
        raw_texts = [t for t in card.strings]
        if not raw_texts:
            continue
        model_name = _clean_model(raw_texts[0])
        if not model_name or model_name in seen:
            continue

        # Fiyat: ₺X.XXX.XXX kalıbı
        price_tag = card.find(class_=re.compile(r"NormalizedPrice"))
        if not price_tag:
            continue
        price_text = price_tag.get_text(separator=" ")
        m = PRICE_RE.search(price_text)
        if not m:
            continue

        price_int = parse_price_str(m.group(1))
        if not price_int:
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


def _parse_price_tables(html: str) -> list[dict]:
    """Fiyat listesi sayfasındaki tablo veya div yapısından fiyat çek."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[str] = set()

    # ₺ işareti veya TL içeren metin bloklarını tara
    price_blocks = soup.find_all(
        string=re.compile(r"₺|TL", re.IGNORECASE)
    )
    for block in price_blocks:
        text = block.strip()
        m = PRICE_RE.search(text)
        if not m:
            continue
        price_int = parse_price_str(m.group(1))
        if not price_int:
            continue

        # Yakın çevreden model adı almaya çalış
        parent = block.parent
        for _ in range(5):  # 5 seviye yukarı çık
            if parent is None:
                break
            sibling_texts = [
                t.strip()
                for t in parent.stripped_strings
                if len(t.strip()) > 2
                   and not re.search(r"₺|TL|\d{3,}", t)
                   and not t.strip().lower().startswith(("başlangıç", "fiyat"))
            ]
            if sibling_texts:
                model_name = sibling_texts[0][:60]
                break
            parent = parent.parent
        else:
            continue

        if model_name and model_name not in seen:
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


class RenaultScraper(BaseScraper):
    brand = "Renault"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("homepage_cards", self._fetch_homepage),
            ("price_list_page", self._fetch_price_list),
            ("models_page", self._fetch_models_page),
        ]

    def _fetch_homepage(self) -> list[dict]:
        """Ana sayfa SSR HTML'inden VehicleModelCard'ları parse et."""
        r = http_get("https://www.renault.com.tr")
        return _parse_vehicle_cards(r.text)

    def _fetch_price_list(self) -> list[dict]:
        """Fiyat listeleri sayfası."""
        r = http_get("https://www.renault.com.tr/renault-fiyat-listeleri.html")
        records = _parse_price_tables(r.text)
        if not records:
            records = _parse_vehicle_cards(r.text)
        return records

    def _fetch_models_page(self) -> list[dict]:
        """Modeller sayfası."""
        r = http_get("https://www.renault.com.tr/araclar.html")
        records = _parse_vehicle_cards(r.text)
        if not records:
            records = _parse_price_tables(r.text)
        return records
