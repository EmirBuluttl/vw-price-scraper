"""
DS Automobiles Turkiye fiyat scraper'i.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, http_get, parse_price_str


class DSScraper(BaseScraper):
    brand = "DS Automobiles"
    validation_profile = ValidationProfile(
        min_records=2,
        required_models=("DS 7", "N°4"),
        min_required_models=2,
        required_variant_keywords=("BlueHDi",),
    )

    MODEL_URLS = {
        "DS 7": "https://talep.dsautomobiles.com.tr/fiyat-listesi-ds7.html",
        "N°4": "https://talep.dsautomobiles.com.tr/fiyat-listesi-n4.html",
    }

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("ds_official_catalog", self._fetch_ds_official_catalog),
        ]

    def _fetch_ds_official_catalog(self) -> list[dict]:
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()

        for model_name, url in self.MODEL_URLS.items():
            response = http_get(url)
            html = response.content.decode("utf-8", errors="replace")
            page_records = self._parse_model_page(model_name, html)
            for record in page_records:
                key = (
                    record["model_name"],
                    record["variant"],
                    record["model_year"],
                    record["price_int"],
                )
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)

        return records

    def _parse_model_page(self, model_name: str, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict] = []

        for li in soup.find_all("li"):
            em_values = [self._clean_text(em.get_text(" ", strip=True)) for em in li.find_all("em")]
            if len(em_values) < 2:
                continue

            variant_name = em_values[0]
            price_int = parse_price_str(em_values[1])
            if not variant_name or not price_int:
                continue

            normalized_model = self._normalize_model_name(variant_name) or model_name
            model_year = self._extract_model_year(li.get_text(" ", strip=True))

            records.append(
                {
                    "model_name": normalized_model,
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
        normalized = self._latinize(self._clean_text(value)).upper()
        if normalized.startswith("DS 7"):
            return "DS 7"
        if normalized.startswith("N4") or normalized.startswith("N°4"):
            return "N°4"
        if normalized.startswith("DS 4"):
            return "DS 4"
        return None

    def _extract_model_year(self, text: str) -> str:
        match = re.search(r"\b(202[4-7])\b", text)
        if match:
            return match.group(1)
        return "2026"

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @staticmethod
    def _latinize(value: str) -> str:
        cleaned = value or ""
        return (
            cleaned.replace("Ç", "C")
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
            .replace("°", "")
            .replace("É", "E")
            .replace("é", "e")
        )
