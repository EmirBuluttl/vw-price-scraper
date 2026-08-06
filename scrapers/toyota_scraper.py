"""
Toyota Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, parse_price_str


class ToyotaScraper(BaseScraper):
    brand = "Toyota"
    validation_profile = ValidationProfile(
        min_records=10,
        required_models=("Corolla", "Corolla Hybrid", "Corolla Cross Hybrid", "C-HR Hybrid", "Yaris"),
        min_required_models=4,
    )

    SOURCE_URL = "https://turkiye.toyota.com.tr/middle/fiyat-listesi/"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("toyota_official_catalog", self._fetch_toyota_official_catalog)]

    def _fetch_toyota_official_catalog(self) -> list[dict]:
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

            header_text = self._clean_text(rows[0].get_text(" ", strip=True))
            normalized_header = self._latinize(header_text).upper()
            if "VERSIYON" not in normalized_header:
                continue
            if "OTV MUAFIYETLI" in normalized_header:
                continue

            model_name = self._extract_model_name(table)
            if not model_name:
                continue

            for tr in rows[1:]:
                cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
                if len(cols) < 2:
                    continue

                variant_name = cols[0]
                if not variant_name or variant_name.startswith("%") or "RENK FARK" in self._latinize(variant_name).upper():
                    continue

                list_price_int = parse_price_str(cols[1]) if len(cols) >= 2 else 0
                campaign_price_int = parse_price_str(cols[2]) if len(cols) >= 3 else 0

                if not list_price_int:
                    continue
                if not campaign_price_int:
                    campaign_price_int = list_price_int

                model_year = "2026"
                key = (model_name, variant_name, model_year, campaign_price_int)
                if key in seen:
                    continue

                seen.add(key)
                discount_amount = max(0, list_price_int - campaign_price_int)
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

    def _extract_model_name(self, table) -> str | None:
        heading = table.find_previous(["h1", "h2", "h3", "h4", "strong"])
        if heading:
            return self._clean_text(heading.get_text(" ", strip=True))
        return None

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @staticmethod
    def _latinize(value: str) -> str:
        return (
            (value or "")
            .replace("Ç", "C")
            .replace("ç", "c")
            .replace("Ğ", "G")
            .replace("ğ", "g")
            .replace("İ", "I")
            .replace("ı", "i")
            .replace("Ö", "O")
            .replace("ö", "o")
            .replace("Ş", "S")
            .replace("ş", "s")
            .replace("Ü", "U")
            .replace("ü", "u")
        )
