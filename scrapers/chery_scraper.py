"""
Chery Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, parse_price_str


class CheryScraper(BaseScraper):
    brand = "Chery"
    validation_profile = ValidationProfile(
        min_records=4,
        required_models=("Tiggo 7 Pro Max", "Tiggo 8 Pro Max"),
        min_required_models=2,
        required_variant_keywords=("145hp",),
    )

    SOURCE_URL = "https://chery.com.tr/sifir-arac-fiyatlari/"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("chery_official_dom_live", self._fetch_chery_official_dom_live)]

    def _fetch_chery_official_dom_live(self) -> list[dict]:
        html = self.fetch_page_html(self.SOURCE_URL, post_load_wait_ms=4000)
        return self._parse_catalog(html)

    def _parse_catalog(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()

        for table in soup.select(".dvmd_tm_table"):
            model_name = self._extract_model_name(table)
            if not model_name:
                continue

            for row in table.select("[role='row']"):
                cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in row.select("[role='columnheader'], [role='cell']")]
                if len(cols) < 3:
                    continue
                if cols[0] == "Model Yılı":
                    continue

                model_year = cols[0]
                variant_name = cols[1]
                price_int = parse_price_str(cols[2])
                if not price_int:
                    continue

                key = (model_name, variant_name, model_year, price_int)
                if key in seen:
                    continue

                seen.add(key)
                records.append(
                    {
                        "model_name": model_name,
                        "variant": variant_name,
                        "price_raw": fmt_price(price_int),
                        "price_int": price_int,
                        "list_price_int": price_int,
                        "campaign_price_int": price_int,
                        "discount_amount_int": 0,
                        "discount_pct": 0.0,
                        "model_year": model_year,
                        "currency": "TRY",
                    }
                )

        return records

    def _extract_model_name(self, table) -> str | None:
        container = table.find_parent(class_="et_pb_row")
        if not container:
            return None

        image = container.find("img")
        if image:
            src = (image.get("src") or "").lower()
            if "tiggo8" in src:
                return "Tiggo 8 Pro Max"
            if "tiggo7" in src:
                return "Tiggo 7 Pro Max"
            if "omoda" in src:
                return "Omoda 5 Pro"

        text = self._clean_text(container.get_text(" ", strip=True)).upper()
        if "TIGGO8" in text or "TIGGO 8" in text:
            return "Tiggo 8 Pro Max"
        if "TIGGO7" in text or "TIGGO 7" in text:
            return "Tiggo 7 Pro Max"
        if "OMODA" in text:
            return "Omoda 5 Pro"
        return None

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()
