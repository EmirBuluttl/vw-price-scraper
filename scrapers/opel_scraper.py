"""
Opel Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price, http_get, parse_price_str


class OpelScraper(BaseScraper):
    brand = "Opel"
    validation_profile = ValidationProfile(
        min_records=8,
        required_models=("Corsa", "Astra", "Mokka", "Grandland"),
        min_required_models=4,
        required_variant_keywords=("145",),
    )

    TRIM_TOKENS = (
        "Edition",
        "GS",
        "Ultimate",
        "Elegance",
        "Enjoy",
        "GSE",
    )

    MODEL_NORMALIZATION = {
        "Yeni Astra": "Astra",
    }

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("opel_official_html_live", self._fetch_opel_official_html_live),
            ("opel_playwright_live", self._fetch_opel_playwright_live),
        ]

    def _fetch_opel_official_html_live(self) -> list[dict]:
        response = http_get("https://fiyatlisteleri.opel.com.tr/tum-araclar")
        return self._parse_catalog(response.text)

    def _fetch_opel_playwright_live(self) -> list[dict]:
        html = self.fetch_page_html("https://fiyatlisteleri.opel.com.tr/tum-araclar", post_load_wait_ms=3000)
        return self._parse_catalog(html)

    def _parse_catalog(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()

        for heading in soup.find_all(re.compile(r"^h1$")):
            raw_model = self._clean_text(heading.get_text(" ", strip=True))
            if not raw_model:
                continue

            model_name = self.MODEL_NORMALIZATION.get(raw_model, raw_model)
            table = self._find_model_table(heading)
            if table is None:
                continue

            header_cells = [self._clean_text(cell.get_text(" ", strip=True)) for cell in table.find_all("tr")[0].find_all(["th", "td"])]
            price_columns = self._select_latest_price_columns(header_cells)
            if price_columns is None:
                continue

            model_year, list_idx, campaign_idx = price_columns

            for tr in table.find_all("tr")[1:]:
                cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
                if len(cols) < 3:
                    continue

                engine = cols[0]
                trims_text = cols[1]
                if not engine or not trims_text:
                    continue

                list_prices = self._extract_prices(cols, list_idx)
                campaign_prices = self._extract_prices(cols, campaign_idx) if campaign_idx is not None else []
                trims = self._split_trims(trims_text)

                variants = self._expand_variants(model_name, engine, trims, list_prices, campaign_prices)
                for variant_name, list_price, campaign_price in variants:
                    if not list_price and not campaign_price:
                        continue

                    final_list = list_price or campaign_price
                    final_campaign = campaign_price or list_price
                    if not final_list or not final_campaign:
                        continue

                    discount_amount = max(0, final_list - final_campaign)
                    discount_pct = round((discount_amount / final_list) * 100, 1) if discount_amount and final_list else 0.0

                    key = (model_name, variant_name, model_year, final_campaign)
                    if key in seen:
                        continue

                    seen.add(key)
                    records.append(
                        {
                            "model_name": model_name,
                            "variant": variant_name,
                            "price_raw": fmt_price(final_campaign),
                            "price_int": final_campaign,
                            "list_price_int": final_list,
                            "campaign_price_int": final_campaign,
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
            if re.fullmatch(r"h1", tag_name, re.IGNORECASE):
                return None

            if tag_name != "table":
                continue

            table_text = self._clean_text(current.get_text(" ", strip=True)).upper()
            if "MOTOR / ŞANZIMAN" in table_text or "MOTOR / SANZIMAN" in table_text:
                return current

        return None

    def _select_latest_price_columns(self, headers: list[str]) -> tuple[str, int, int | None] | None:
        year_candidates: dict[int, dict[str, int]] = {}
        for index, header in enumerate(headers):
            header_clean = self._clean_text(header)
            year_match = re.search(r"MY(\d{2})", header_clean, re.IGNORECASE)
            year_value = int(year_match.group(1)) if year_match else 0
            bucket = year_candidates.setdefault(year_value, {})
            upper_header = header_clean.upper()
            if "ANAHTAR TESLIM FIYATI" in upper_header or "ANAHTAR TESLİM FİYATI" in upper_header:
                bucket["list"] = index
            if "KAMPANYALI" in upper_header or "LANSMANA ÖZEL" in upper_header:
                bucket["campaign"] = index

        valid_years = [(year, cols) for year, cols in year_candidates.items() if "list" in cols or "campaign" in cols]
        if not valid_years:
            return None

        latest_year, latest_cols = sorted(valid_years, key=lambda item: item[0], reverse=True)[0]
        model_year = f"20{latest_year:02d}" if latest_year else "2026"
        return model_year, latest_cols.get("list", -1), latest_cols.get("campaign")

    def _extract_prices(self, cols: list[str], index: int | None) -> list[int]:
        if index is None or index < 0 or index >= len(cols):
            return []
        text = cols[index]
        prices: list[int] = []
        for match in re.findall(r"\d[\d.]+\s*TL", text):
            parsed = parse_price_str(match)
            if parsed:
                prices.append(int(parsed))
        return prices

    def _split_trims(self, text: str) -> list[str]:
        parts = [part for part in self._clean_text(text).split() if part]
        recognized = [part for part in parts if part in self.TRIM_TOKENS]
        return recognized or [self._clean_text(text)]

    def _expand_variants(
        self,
        model_name: str,
        engine: str,
        trims: list[str],
        list_prices: list[int],
        campaign_prices: list[int],
    ) -> list[tuple[str, int | None, int | None]]:
        trim_count = len(trims)
        if trim_count <= 1:
            trim = trims[0] if trims else ""
            return [(self._build_variant_name(model_name, trim, engine), list_prices[0] if list_prices else None, campaign_prices[0] if campaign_prices else None)]

        expanded: list[tuple[str, int | None, int | None]] = []
        for idx, trim in enumerate(trims):
            list_price = list_prices[idx] if idx < len(list_prices) else (list_prices[-1] if list_prices else None)
            campaign_price = campaign_prices[idx] if idx < len(campaign_prices) else None
            expanded.append((self._build_variant_name(model_name, trim, engine), list_price, campaign_price))
        return expanded

    @staticmethod
    def _build_variant_name(model_name: str, trim: str, engine: str) -> str:
        return " ".join(part for part in (model_name, trim, engine) if part).strip()

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()
