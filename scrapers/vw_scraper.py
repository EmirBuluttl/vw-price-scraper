"""
Volkswagen Turkiye fiyat scraper.
"""

from __future__ import annotations

from typing import Any

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, http_post

API_URL = "https://gw.dogusoto.com.tr/gw-search-newvehicle/GetVehicleBySearchCriteria"
VW_BRAND_ID = 14913


def _build_payload(brand_id: int, page_size: int = 500) -> dict:
    return {
        "modelId": 0,
        "modelIds": [],
        "permalink": "",
        "searchKey": "",
        "size": 0,
        "pagination": {"page": 1, "pageSize": page_size},
        "isCampaignVehicle": None,
        "isOptionalVehicle": None,
        "year": {"min": 0, "max": 0},
        "price": {"min": 0, "max": 0},
        "sortingCriteria": 1,
        "colorIds": [],
        "brandIds": [brand_id],
        "servicePointIds": [],
        "gearTypes": [],
        "fuelTypeIds": [],
        "caseTypeIds": [],
    }


def _parse_dogusoto_response(data: dict) -> list[dict]:
    results = data.get("data", {}).get("results", [])
    seen: set[tuple] = set()
    records: list[dict] = []

    for item in results:
        model_name = item.get("modelName", "Bilinmiyor").strip()
        variant = (item.get("subModelName") or "").strip()
        model_year = str(item.get("year") or "2026").strip()

        price_val = item.get("price", 0)
        camp_val = item.get("campaignPrice") or price_val
        if not price_val or float(price_val) <= 100_000:
            continue

        list_price_int = int(price_val)
        campaign_price_int = int(camp_val) if camp_val and float(camp_val) > 100_000 else list_price_int
        list_price_int = max(list_price_int, campaign_price_int)

        key = (model_name, variant, model_year, campaign_price_int)
        if key in seen:
            continue
        seen.add(key)

        discount_amount = max(0, list_price_int - campaign_price_int)
        discount_pct = round((discount_amount / list_price_int) * 100, 1) if list_price_int > 0 else 0.0
        records.append(
            {
                "model_name": model_name,
                "variant": variant,
                "price_raw": fmt_price(campaign_price_int),
                "price_int": campaign_price_int,
                "list_price_int": list_price_int,
                "campaign_price_int": campaign_price_int,
                "discount_amount_int": discount_amount,
                "discount_pct": discount_pct,
                "model_year": model_year,
                "currency": "TRY",
            }
        )

    return records


class VWScraper(BaseScraper):
    brand = "Volkswagen"
    validation_profile = ValidationProfile(
        min_records=10,
        required_models=("Polo", "Golf", "Taigo", "T-Roc", "Tiguan"),
        min_required_models=4,
    )

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("dogusoto_api", self._fetch_api)]

    def _fetch_api(self) -> list[dict]:
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://www.dogusoto.com.tr",
            "Referer": "https://www.dogusoto.com.tr/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            response = http_post(API_URL, headers=headers, json=_build_payload(VW_BRAND_ID, 500))
            return _parse_dogusoto_response(response.json())
        except Exception:
            return []
