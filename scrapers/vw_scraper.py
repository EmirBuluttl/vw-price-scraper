"""
vw_scraper.py  —  Volkswagen Türkiye fiyat scraper'ı
=====================================================
Kaynak: Doğuş Oto API Gateway (JSON)
Mevcut scraper.py mantığı buraya taşındı; geriye dönük uyumluluk
için scraper.py olduğu gibi bırakıldı.
"""

from __future__ import annotations

from .base_scraper import BaseScraper, fmt_price, http_post

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
        model_name = item.get("modelName", "Bilinmiyor")
        variant = (item.get("subModelName") or "").strip()
        price_val = item.get("price", 0)
        if price_val and float(price_val) > 100_000:
            price_int = int(price_val)
            key = (model_name, variant)
            if key not in seen:
                seen.add(key)
                records.append(
                    {
                        "model_name": model_name,
                        "variant": variant,
                        "price_raw": fmt_price(price_int),
                        "price_int": price_int,
                        "currency": "TRY",
                    }
                )
    return records


class VWScraper(BaseScraper):
    brand = "Volkswagen"

    @property
    def methods(self):
        return [("dogusoto_api", self._fetch_api)]

    def _fetch_api(self) -> list[dict]:
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://www.dogusoto.com.tr",
            "Referer": "https://www.dogusoto.com.tr/",
        }
        r = http_post(
            API_URL,
            headers=headers,
            json=_build_payload(VW_BRAND_ID),
        )
        return _parse_dogusoto_response(r.json())
