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
            ("api_all", self._fetch_all_categories),
        ]

    def _fetch_all_categories(self) -> list[dict]:
        all_records = []
        seen = set()
        for cat in ["Binek", "Ticari", "FordStore"]:
            try:
                recs = self._fetch_api(cat)
                for r in recs:
                    key = (r["model_name"], r["variant"])
                    if key not in seen:
                        seen.add(key)
                        all_records.append(r)
            except Exception as e:
                log.warning("Ford category %s failed: %s", cat, e)
        return all_records

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
                
                # Get both list price (MSRP) and campaign price
                list_p_val = ent.get("deliveredTurnkeyListPrice") or ent.get("campaignedTurnkeyPrice")
                camp_p_val = ent.get("campaignedTurnkeyPrice") or ent.get("deliveredTurnkeyListPrice")
                if not camp_p_val:
                    continue
                
                try:
                    camp_p_int = int(float(str(camp_p_val).replace(",", "").replace(".", "").strip()))
                    list_p_int = int(float(str(list_p_val).replace(",", "").replace(".", "").strip())) if list_p_val else camp_p_int
                except (ValueError, TypeError):
                    continue

                if camp_p_int < 100_000:
                    continue

                discount_amount = (list_p_int - camp_p_int) if list_p_int > camp_p_int else 0

                variant = f"{series} {desc} ({year})".strip()
                key = (model_name, variant)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "model_name": model_name,
                        "variant": variant,
                        "price_raw": fmt_price(camp_p_int),
                        "price_int": camp_p_int,
                        "list_price_int": list_p_int,
                        "campaign_price_int": camp_p_int,
                        "discount_amount_int": discount_amount,
                        "currency": "TRY"
                    })
        return records
