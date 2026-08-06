"""
Dacia Turkiye fiyat scraper.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, http_get


class DaciaScraper(BaseScraper):
    brand = "Dacia"
    validation_profile = ValidationProfile(
        min_records=4,
        required_models=("Sandero", "Duster", "Jogger"),
        min_required_models=2,
    )

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("official_site_json", self._fetch_official_site)]

    def _fetch_official_site(self) -> list[dict]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        pages = [
            ("Yeni Sandero", "https://www.dacia.com.tr/modeller/yeni-sandero-bi1-ph2.html"),
            ("Yeni Sandero Stepway", "https://www.dacia.com.tr/modeller/yeni-sandero-stepway-bi1-ph2.html"),
            ("Yeni Duster", "https://www.dacia.com.tr/modeller/yeni-duster.html"),
            ("Yeni Jogger", "https://www.dacia.com.tr/modeller/yeni-jogger.html"),
            ("Fiyat Listesi", "https://www.dacia.com.tr/dacia-fiyat-listesi.html"),
        ]

        for default_name, url in pages:
            try:
                response = http_get(url, headers=headers)
                match = re.search(r'window\.APP_STATE\s*=\s*JSON\.parse\("(.*?)"\);', response.text, re.DOTALL)
                if not match:
                    continue
                data = json.loads(json.loads(f'"{match.group(1)}"'))

                def extract_trims(payload):
                    if isinstance(payload, dict):
                        priced_version = payload.get("pricedVersion") or {}
                        variant_label = priced_version.get("label") or priced_version.get("name") or payload.get("versionName") or payload.get("trimName")

                        model_name = default_name
                        if model_name == "Fiyat Listesi":
                            variant_lower = (variant_label or "").lower()
                            if "duster" in variant_lower:
                                model_name = "Duster"
                            elif "stepway" in variant_lower:
                                model_name = "Sandero Stepway"
                            elif "sandero" in variant_lower:
                                model_name = "Sandero"
                            elif "jogger" in variant_lower:
                                model_name = "Jogger"
                            elif "spring" in variant_lower:
                                model_name = "Spring"
                            else:
                                model_name = "Dacia"

                        raw_campaign = payload.get("price") or payload.get("displayPrice") or (payload.get("webDisplayPrices") or {}).get("displayPrice")
                        raw_list = payload.get("listPrice") or payload.get("recommendedPrice") or (payload.get("webDisplayPrices") or {}).get("listPrice") or raw_campaign

                        if variant_label and raw_campaign:
                            try:
                                campaign_price = int(float(raw_campaign))
                                list_price = int(float(raw_list)) if raw_list else campaign_price
                                list_price = max(list_price, campaign_price)

                                if campaign_price > 100_000:
                                    key = (model_name, variant_label, campaign_price)
                                    if key not in seen:
                                        seen.add(key)
                                        discount_amount = max(0, list_price - campaign_price)
                                        discount_pct = round((discount_amount / list_price) * 100, 1) if list_price > 0 else 0.0
                                        records.append(
                                            {
                                                "model_name": model_name,
                                                "variant": variant_label,
                                                "price_raw": fmt_price(campaign_price),
                                                "price_int": campaign_price,
                                                "list_price_int": list_price,
                                                "campaign_price_int": campaign_price,
                                                "discount_amount_int": discount_amount,
                                                "discount_pct": discount_pct,
                                                "currency": "TRY",
                                            }
                                        )
                            except Exception:
                                pass

                        for value in payload.values():
                            extract_trims(value)
                    elif isinstance(payload, list):
                        for item in payload:
                            extract_trims(item)

                extract_trims(data)
            except Exception:
                pass

        return records
