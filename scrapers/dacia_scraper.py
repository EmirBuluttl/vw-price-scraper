"""
dacia_scraper.py  —  Dacia Türkiye fiyat scraper'ı
===================================================
Birincil : dacia.com.tr ana sayfa (ModelPickerCard SSR HTML)
Fallback A: dacia.com.tr/dacia-fiyat-listeleri.html parse
Fallback B: Model isimleri ile genel HTML taraması
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

PRICE_RE = re.compile(r"₺\s*([\d.,]+)")
DACIA_MODELS = ["logan", "sandero", "stepway", "jogger", "duster", "spring"]


def _parse_dacia_homepage(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[str] = set()

    # ModelPickerCard div'lerini ara
    cards = soup.find_all("div", class_=re.compile(r"ModelPickerCard|VehicleModelCard|ModelCard", re.IGNORECASE))
    for card in cards:
        # Model adı
        title_tag = card.find(class_=re.compile(r"modelName|title|name", re.IGNORECASE))
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title or title in seen:
            continue
        
        # Fiyat
        price_tag = card.find(class_=re.compile(r"price|StartingPrice", re.IGNORECASE))
        if not price_tag:
            continue
        price_text = price_tag.get_text(strip=True)
        m = PRICE_RE.search(price_text)
        if not m:
            continue
        
        price_int = parse_price_str(m.group(1))
        if not price_int:
            continue
            
        seen.add(title)
        records.append({
            "model_name": title,
            "variant": "",
            "price_raw": fmt_price(price_int),
            "price_int": price_int,
            "currency": "TRY"
        })
        
    return records


def _scan_dacia_general(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[str] = set()

    for model in DACIA_MODELS:
        elements = soup.find_all(string=re.compile(rf"\b{model}\b", re.IGNORECASE))
        for elem in elements:
            parent = elem.parent
            for _ in range(6):
                if parent is None:
                    break
                text = parent.get_text(separator=" ")
                m = PRICE_RE.search(text)
                if m:
                    price_int = parse_price_str(m.group(1))
                    if price_int:
                        # Model ismini al
                        model_name = str(elem).strip()
                        if not model_name or len(model_name) > 80:
                            model_name = model.upper()
                        if model_name not in seen:
                            seen.add(model_name)
                            records.append({
                                "model_name": model_name,
                                "variant": "",
                                "price_raw": fmt_price(price_int),
                                "price_int": price_int,
                                "currency": "TRY"
                            })
                        break
                parent = parent.parent
    return records


class DaciaScraper(BaseScraper):
    brand = "Dacia"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("homepage_cards", self._fetch_homepage),
            ("price_list_page", self._fetch_price_list),
            ("general_scan", self._fetch_general),
        ]

    def _fetch_homepage(self) -> list[dict]:
        r = http_get("https://www.dacia.com.tr")
        return _parse_dacia_homepage(r.text)

    def _fetch_price_list(self) -> list[dict]:
        r = http_get("https://www.dacia.com.tr/dacia-fiyat-listeleri.html")
        records = _parse_dacia_homepage(r.text)
        if not records:
            records = _scan_dacia_general(r.text)
        return records

    def _fetch_general(self) -> list[dict]:
        r = http_get("https://www.dacia.com.tr")
        return _scan_dacia_general(r.text)
