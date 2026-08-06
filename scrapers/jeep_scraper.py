"""
Jeep Turkiye fiyat scraper'i.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, http_get, parse_price_str


class JeepScraper(BaseScraper):
    brand = "Jeep"
    validation_profile = ValidationProfile(
        min_records=4,
        required_models=("Avenger", "Compass"),
        min_required_models=2,
        required_variant_keywords=("Hibrit",),
    )

    SOURCE_URL = "https://arjfiyat.tofas.com.tr/pricelists?brand=jeep&opncl_performance=true&opncl_advertising=true"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("jeep_tofas_iframe_live", self._fetch_jeep_tofas_iframe_live),
        ]

    def _fetch_jeep_tofas_iframe_live(self) -> list[dict]:
        response = http_get(self.SOURCE_URL)
        return self._parse_catalog(response.text)

    def _parse_catalog(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()
        current_model = "Jeep"

        for element in soup.find_all(["h1", "table"]):
            if element.name == "h1":
                heading = self._clean_text(element.get_text(" ", strip=True))
                normalized_model = self._normalize_model_name(heading)
                if normalized_model:
                    current_model = normalized_model
                continue

            table = element
            rows = table.find_all("tr")
            if not rows:
                continue

            table_text = self._clean_text(table.get_text(" ", strip=True)).upper()
            if "TAVSIYE EDILEN ANAHTAR TESLIM FIYATI" not in table_text and "TAVSİYE EDİLEN ANAHTAR TESLİM FİYATI" not in table_text:
                continue

            for tr in rows[1:]:
                cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
                if len(cols) < 6:
                    continue

                raw_model = cols[0]
                if raw_model.upper() == "MODEL":
                    continue

                variant_name = self._build_variant_name(raw_model, cols[1], cols[2], cols[3], cols[4])
                price_int = parse_price_str(cols[5])
                if not price_int:
                    continue

                model_name = self._normalize_model_name(raw_model) or current_model
                model_year = "2026"

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

    def _normalize_model_name(self, value: str) -> str | None:
        upper_value = self._clean_text(value).upper()
        if "AVENGER" in upper_value:
            return "Avenger"
        if "COMPASS" in upper_value:
            return "Compass"
        if "RENEGADE" in upper_value:
            return "Renegade"
        if "WRANGLER" in upper_value:
            return "Wrangler"
        if "CHEROKEE" in upper_value:
            return "Grand Cherokee"
        return None

    def _build_variant_name(self, model: str, cekis: str, donanim: str, sanziman: str, yakit: str) -> str:
        parts = [
            self._clean_text(model),
            self._clean_text(cekis),
            self._clean_text(donanim),
            self._clean_text(sanziman),
            self._clean_text(yakit),
        ]
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _clean_text(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value or "").strip()
        cleaned = cleaned.replace("SUMMİT", "SUMMIT").replace("ELEKTRİKLİ", "ELEKTRIKLI")
        return cleaned
