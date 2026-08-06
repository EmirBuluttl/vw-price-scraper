"""
Renault Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, parse_price_str


class RenaultScraper(BaseScraper):
    brand = "Renault"
    validation_profile = ValidationProfile(
        min_records=8,
        required_models=("Yeni Clio", "Captur", "Austral"),
        min_required_models=3,
    )

    SOURCE_URL = "https://best.renault.com.tr/fiyat-listesi/?kat=Binek"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("renault_best_live", self._fetch_renault_best_live)]

    def _fetch_renault_best_live(self) -> list[dict]:
        html = self.fetch_page_html(self.SOURCE_URL, post_load_wait_ms=4000)
        return self._parse_catalog(html)

    def _parse_catalog(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()

        for table in soup.select("table.price-table"):
            row_container = table.find_parent(class_="row")
            model_name = self._extract_model_name(row_container, table)
            if not model_name:
                continue

            headers = [
                self._clean_text(cell.get_text(" ", strip=True))
                for cell in table.select("thead th")
            ]
            year_match = re.search(r"\b(202[4-7])\b", " ".join(headers))
            model_year = year_match.group(1) if year_match else "2026"

            for tr in table.select("tbody tr"):
                cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
                if len(cols) < 2:
                    continue

                variant_name = cols[0]
                if not variant_name or variant_name.lower() == "opsiyonlar":
                    continue

                price_int = parse_price_str(cols[1])
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

    def _extract_model_name(self, row_container, table) -> str | None:
        if row_container:
            image = row_container.find("img")
            if image:
                alt = self._clean_text(image.get("alt", ""))
                if alt:
                    return alt

        heading = table.find_previous(["h1", "h2", "h3"])
        if heading:
            return self._clean_text(heading.get_text(" ", strip=True))
        return None

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()
