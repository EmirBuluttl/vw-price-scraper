"""
Peugeot Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, http_get, parse_price_str


class PeugeotScraper(BaseScraper):
    brand = "Peugeot"
    validation_profile = ValidationProfile(
        min_records=10,
        required_models=("2008", "408", "3008", "5008"),
        min_required_models=4,
        required_variant_keywords=("145",),
    )

    MODEL_PATTERNS = (
        ("EXPERT TRAVELLER", "Expert Traveller"),
        ("PARTNER VAN", "Partner Van"),
        ("BOXER MINIBUS", "Boxer Minibus"),
        ("BOXER MINIBÜS", "Boxer Minibus"),
        ("BOXER VAN", "Boxer Van"),
        ("EXPERT VAN", "Expert Van"),
        ("RIFTER", "Rifter"),
        ("E-5008", "E-5008"),
        ("E-3008", "E-3008"),
        ("E-2008", "E-2008"),
        ("E-308", "E-308"),
        ("E-208", "E-208"),
        ("5008", "5008"),
        ("3008", "3008"),
        ("2008", "2008"),
        ("408", "408"),
        ("308", "308"),
        ("208", "208"),
    )

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("peugeot_official_html_live", self._fetch_peugeot_official_html_live),
            ("peugeot_playwright_live", self._fetch_peugeot_playwright_live),
        ]

    def _fetch_peugeot_official_html_live(self) -> list[dict]:
        response = http_get("https://kampanya.peugeot.com.tr/fiyat-listesi/")
        return self._parse_catalog(response.text)

    def _fetch_peugeot_playwright_live(self) -> list[dict]:
        html = self.fetch_page_html(
            "https://kampanya.peugeot.com.tr/fiyat-listesi/",
            post_load_wait_ms=3000,
        )
        return self._parse_catalog(html)

    def _parse_catalog(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()

        for heading in soup.find_all(re.compile(r"^h[1-4]$")):
            heading_text = self._clean_text(heading.get_text(" ", strip=True))
            model_name = self._resolve_model_name(heading_text)
            if not model_name:
                continue

            table = self._find_model_table(heading)
            if table is None:
                continue

            table_text = self._clean_text(table.get_text(" ", strip=True))
            year_match = re.search(r"\b(202[4-7])\s*MY\b", table_text, re.IGNORECASE)
            model_year = year_match.group(1) if year_match else "2026"

            for tr in table.find_all("tr"):
                cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
                if len(cols) < 2:
                    continue

                variant = cols[0]
                if not self._is_variant_row(variant):
                    continue

                prices = [parse_price_str(col) for col in cols[1:]]
                prices = [price for price in prices if price]
                if not prices:
                    continue

                list_price = prices[0]
                campaign_price = prices[1] if len(prices) > 1 else prices[0]
                variant_model = self._resolve_model_name(variant) or model_name
                discount_amount = max(0, list_price - campaign_price)
                discount_pct = round((discount_amount / list_price) * 100, 1) if discount_amount and list_price else 0.0

                key = (variant_model, variant, model_year, campaign_price)
                if key in seen:
                    continue

                seen.add(key)
                records.append(
                    {
                        "model_name": variant_model,
                        "variant": variant,
                        "price_raw": fmt_price(campaign_price),
                        "price_int": campaign_price,
                        "list_price_int": list_price,
                        "campaign_price_int": campaign_price,
                        "discount_amount_int": discount_amount,
                        "discount_pct": discount_pct,
                        "model_year": model_year,
                        "currency": "TRY",
                    }
                )

        return records

    def _find_model_table(self, heading) -> Any | None:
        current = heading
        while current is not None:
            current = current.find_next()
            if current is None:
                return None

            tag_name = getattr(current, "name", "") or ""
            if re.fullmatch(r"h[1-4]", tag_name, re.IGNORECASE):
                return None

            if tag_name != "table":
                continue

            table_text = self._clean_text(current.get_text(" ", strip=True)).upper()
            if "MODELLER" not in table_text:
                continue
            if "OPSIYONLAR" in table_text or "OPSİYONLAR" in table_text:
                continue
            return current

        return None

    def _is_variant_row(self, value: str) -> bool:
        upper_value = self._clean_text(value).upper()
        if not upper_value:
            return False

        blocked_tokens = (
            "MODELLER",
            "OPSIYONLAR",
            "OPSİYONLAR",
            "VERSIYONLAR",
            "VERSİYONLAR",
            "INTERNET SITEMIZDE",
            "İNTERNET SİTEMİZDE",
            "BELIRTILEN ANAHTAR",
            "BELİRTİLEN ANAHTAR",
            "TOFAS",
            "TOFAŞ",
            "YETKILI BAYI ARA",
            "HEMEN KESFET",
            "HEMEN KEŞFET",
        )
        if any(token in upper_value for token in blocked_tokens):
            return False

        if upper_value in {"BENZIN", "BENZİN", "DIZEL", "DİZEL", "HYBRID", "ELEKTRIK", "ELEKTRİK"}:
            return False

        return any(pattern in upper_value for pattern, _ in self.MODEL_PATTERNS)

    def _resolve_model_name(self, text: str) -> str | None:
        upper_text = self._clean_text(text).upper()
        for pattern, model_name in self.MODEL_PATTERNS:
            if pattern in upper_text:
                return model_name
        return None

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()
