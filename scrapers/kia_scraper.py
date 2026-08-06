"""
Kia Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, http_get


class KiaScraper(BaseScraper):
    brand = "Kia"
    validation_profile = ValidationProfile(
        min_records=5,
        required_models=("Picanto", "Stonic", "Sportage"),
        min_required_models=2,
    )

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("kia_official_catalog", self._fetch_kia_catalog)]

    def _fetch_kia_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        try:
            response = http_get("https://www.kia.com.tr/tr/fiyat-listesi.html", headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            for table in soup.find_all("table"):
                for tr in table.find_all("tr"):
                    cols = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                    if len(cols) < 2:
                        continue

                    model_name = cols[0]
                    variant = cols[1] if len(cols) > 2 else cols[0]
                    price_match = re.search(r"(\d[\d.,\s]+)", cols[-1])
                    if not price_match:
                        continue

                    price_int = int(re.sub(r"[^\d]", "", price_match.group(1)))
                    if not (100_000 < price_int < 10_000_000):
                        continue

                    key = (model_name, variant, price_int)
                    if key in seen:
                        continue
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
        except Exception:
            pass

        return records
