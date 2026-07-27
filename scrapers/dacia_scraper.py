"""
dacia_scraper.py  —  Dacia Türkiye fiyat scraper'ı
===================================================
Birincil : dacia.com.tr ana sayfa (window.APP_STATE JSON & ModelPickerCard SSR HTML)
Fallback A: dacia.com.tr/modeller.html parse
Fallback B: Model isimleri ile genel HTML taraması
"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

PRICE_RE = re.compile(r"₺\s*([\d.,]+)")
DACIA_MODELS = ["logan", "sandero", "stepway", "jogger", "duster", "spring"]


def _parse_dacia_app_state(html: str) -> list[dict]:
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

                def extract_dacia(d):
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
                            extract_dacia(v)
                    elif isinstance(d, list):
                        for item in d:
                            extract_dacia(item)

                extract_dacia(data)
            except Exception:
                pass

    return records


def _parse_dacia_homepage(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[str] = set()

    cards = soup.find_all("div", class_=re.compile(r"ModelPickerCard|VehicleModelCard|ModelCard", re.IGNORECASE))
    for card in cards:
        title_tag = card.find(class_=re.compile(r"modelName|title|name", re.IGNORECASE))
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title or title in seen:
            continue

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
            "variant": "Başlangıç Fiyatı",
            "price_raw": fmt_price(price_int),
            "price_int": price_int,
            "currency": "TRY"
        })

    return records


class DaciaScraper(BaseScraper):
    brand = "Dacia"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("homepage_cards", self._fetch_homepage),
            ("models_page", self._fetch_models),
        ]

    def _fetch_homepage(self) -> list[dict]:
        r = http_get("https://www.dacia.com.tr")
        records = _parse_dacia_app_state(r.text)
        if not records:
            records = _parse_dacia_homepage(r.text)
        return records

    def _fetch_models(self) -> list[dict]:
        r = http_get("https://www.dacia.com.tr/modeller.html")
        records = _parse_dacia_app_state(r.text)
        if not records:
            records = _parse_dacia_homepage(r.text)
        return records
