"""
ford_scraper.py  —  Ford Türkiye fiyat scraper'ı
=================================================
Birincil : Ford API Gateway (/fwebapi/main/carPriceListNewUI)
Fallback : HTML scraping
"""

from __future__ import annotations

import logging
from typing import Any
from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

log = logging.getLogger(__name__)

API_URL = "https://www.ford.com.tr/fwebapi/main/carPriceListNewUI"


class FordScraper(BaseScraper):
    brand = "Ford"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("api_binek", lambda: self._fetch_api("Binek")),
            ("api_ticari", lambda: self._fetch_api("Ticari")),
            ("api_fordstore", lambda: self._fetch_api("FordStore")),
        ]

    def _fetch_api(self, car_type: str) -> list[dict]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://www.ford.com.tr/fiyat-listesi/otomobil",
        }
        params = {
            "searchparam": "",
            "cartype": car_type
        }
        r = http_get(API_URL, headers=headers, params=params)
        data = r.json()
        car_list = data.get("carPriceList", [])

        records: list[dict] = []
        seen: set[tuple] = set()

        for model in car_list:
            model_name = model.get("modelName")
            if not model_name:
                continue
            entities = model.get("entities", [])
            for ent in entities:
                desc = ent.get("entityDescription") or ""
                series = ent.get("series") or ""
                year = ent.get("modelYear") or ""
                
                # Get the price (campaigned first, then list price)
                price_val = ent.get("campaignedTurnkeyPrice") or ent.get("deliveredTurnkeyListPrice")
                if not price_val:
                    continue
                
                try:
                    price_int = int(float(str(price_val).replace(",", "").replace(".", "").strip()))
                except (ValueError, TypeError):
                    continue

                if price_int < 100_000:
                    continue

                variant = f"{series} {desc} ({year})".strip()
                key = (model_name, variant)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "model_name": model_name,
                        "variant": variant,
                        "price_raw": fmt_price(price_int),
                        "price_int": price_int,
                        "currency": "TRY"
                    })
        return records
