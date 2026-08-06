"""
Kia Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, parse_price_str


class KiaScraper(BaseScraper):
    brand = "Kia"
    validation_profile = ValidationProfile(
        min_records=8,
        required_models=("Picanto", "Stonic", "Sportage", "EV3"),
        min_required_models=4,
    )

    SOURCE_URL = "https://www.kia.com/tr/satis-merkezi/fiyat-listesi.html"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("kia_official_catalog", self._fetch_kia_catalog)]

    def _fetch_kia_catalog(self) -> list[dict]:
        html = self.fetch_page_html(self.SOURCE_URL, post_load_wait_ms=4000)
        return self._parse_catalog(html)

    def _parse_catalog(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            header_cells = [self._clean_text(cell.get_text(" ", strip=True)) for cell in rows[0].find_all(["th", "td"])]
            header_text = " ".join(header_cells)
            if "Modeli" not in header_text or "Anahtar Teslim Satış Fiyatı" not in header_text:
                continue

            for tr in rows[1:]:
                cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
                if len(cols) < 6:
                    continue

                variant_base = cols[0]
                fuel_type = cols[1]
                trim = cols[2]
                list_price_int = parse_price_str(cols[3])
                discount_amount = parse_price_str(cols[4]) or 0
                campaign_price_int = parse_price_str(cols[5]) or list_price_int
                if not list_price_int:
                    continue

                model_name = self._extract_model_name(variant_base)
                variant_name = f"{variant_base} {fuel_type} {trim}".strip()
                model_year = "2026"

                key = (model_name, variant_name, model_year, campaign_price_int)
                if key in seen:
                    continue

                seen.add(key)
                discount_amount = max(discount_amount, list_price_int - campaign_price_int, 0)
                discount_pct = round((discount_amount / list_price_int) * 100, 1) if list_price_int > 0 else 0.0
                records.append(
                    {
                        "model_name": model_name,
                        "variant": variant_name,
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

    def _extract_model_name(self, variant_base: str) -> str:
        text = self._clean_text(variant_base)
        if " - " in text:
            text = text.split(" - ", 1)[0]
        return text.split()[0] if text else "Kia"

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()
