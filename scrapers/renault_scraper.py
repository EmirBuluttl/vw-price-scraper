"""
renault_scraper.py  —  Renault Türkiye fiyat scraper'ı
======================================================
Birincil : renault.com.tr/renault-fiyat-listeleri.html (window.APP_STATE JSON parse)
Fallback A: renault.com.tr ana sayfa (SSR HTML içinde model kartları)
Fallback B: Ürün detay sayfaları üzerinden fiyat çekme
"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

_STRIP = re.compile(r"\s+")
PRICE_RE = re.compile(r"₺\s*([\d.,]+)")


def _clean_model(raw: str) -> str:
    return _STRIP.sub(" ", raw).strip()


def _parse_app_state(html: str) -> list[dict]:
    """renault.com.tr üzerindeki window.APP_STATE JSON yapısını çöz ve modelleri çek."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[str] = set()

    for s in soup.find_all("script"):
        text = s.get_text()
        if "window.APP_STATE=JSON.parse(" in text:
            match = re.search(r'window\.APP_STATE=JSON\.parse\("(.*?)"\);', text, re.DOTALL)
            if not match:
                continue
            try:
                raw_json_escaped = match.group(1)
                data = json.loads(json.loads(f'"{raw_json_escaped}"'))

                def extract_models(d):
                    if isinstance(d, dict):
                        if "modelAdmin" in d and "modelData" in d:
                            admin = d["modelAdmin"]
                            m_data = d["modelData"]
                            name = admin.get("modelName") or admin.get("shortModelName")
                            min_price = m_data.get("minPrice") or m_data.get("webDisplayPrices", {}).get("displayPrice")
                            if name and min_price:
                                price_int = int(float(min_price))
                                if price_int > 100_000 and name not in seen:
                                    seen.add(name)
                                    records.append({
                                        "model_name": name,
                                        "variant": "Başlangıç Fiyatı",
                                        "price_raw": fmt_price(price_int),
                                        "price_int": price_int,
                                        "currency": "TRY"
                                    })
                        for k, v in d.items():
                            extract_models(v)
                    elif isinstance(d, list):
                        for item in d:
                            extract_models(item)

                extract_models(data)
            except Exception:
                pass

    return records


def _parse_vehicle_cards(html: str) -> list[dict]:
    """VehicleModelCard div'lerini parse et."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[str] = set()

    cards = soup.find_all("div", class_=re.compile(r"VehicleModelCard__modelName_price"))
    for card in cards:
        raw_texts = [t for t in card.strings]
        if not raw_texts:
            continue
        model_name = _clean_model(raw_texts[0])
        if not model_name or model_name in seen:
            continue

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
                "variant": "Başlangıç Fiyatı",
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
            ("price_list_page", self._fetch_price_list),
            ("homepage_cards", self._fetch_homepage),
        ]

    def _fetch_price_list(self) -> list[dict]:
        """Fiyat listeleri sayfası APP_STATE JSON parsing."""
        r = http_get("https://www.renault.com.tr/renault-fiyat-listeleri.html")
        records = _parse_app_state(r.text)
        if not records:
            records = _parse_vehicle_cards(r.text)
        return records

    def _fetch_homepage(self) -> list[dict]:
        """Ana sayfa SSR HTML'inden VehicleModelCard'ları parse et."""
        r = http_get("https://www.renault.com.tr")
        records = _parse_app_state(r.text)
        if not records:
            records = _parse_vehicle_cards(r.text)
        return records
