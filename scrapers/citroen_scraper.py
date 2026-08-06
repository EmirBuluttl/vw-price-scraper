"""
Citroen Turkiye fiyat scraper'i.
"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import (
    BaseScraper,
    SharedPlaywrightRuntime,
    ValidationProfile,
    _PLAYWRIGHT_STATE,
    fmt_price,
    http_get,
    parse_price_str,
)


class CitroenScraper(BaseScraper):
    brand = "Citroën"
    validation_profile = ValidationProfile(
        min_records=10,
        required_models=("Ami", "C3 Aircross", "C4 X", "C5 Aircross", "Berlingo", "Jumpy Van"),
        min_required_models=5,
        required_variant_keywords=("145",),
    )

    CLICK_FALLBACKS = {
        "c4": "C4 Hybrid 145",
    }

    MODEL_ALIASES = {
        "ami": "Ami",
        "yeni-c3-aircross-suv": "C3 Aircross",
        "e-c3-aircross": "ë-C3 Aircross",
        "c4": "C4",
        "c4x": "C4 X",
        "yeni-c5-aircross-hibrit": "C5 Aircross",
        "yeni-e-c5-aircross": "ë-C5 Aircross",
        "yeni-berlingo": "Berlingo",
        "yeni-berlingo-van": "Berlingo Van",
        "jumpy-van": "Jumpy Van",
        "jumpy-kamyonet": "Jumpy Kamyonet",
        "spacetourer": "Spacetourer",
        "jumper": "Jumper",
    }

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("citroen_playwright_live", self._fetch_citroen_playwright_live),
        ]

    def _fetch_citroen_playwright_live(self) -> list[dict]:
        records: list[dict] = []
        seen: set[tuple[str, str, str, int]] = set()
        runtime = getattr(_PLAYWRIGHT_STATE, "runtime", None)
        owns_runtime = runtime is None
        if owns_runtime:
            runtime = SharedPlaywrightRuntime().start()

        try:
            slug_entries = self._discover_model_entries()
            for slug, display_name in slug_entries:
                html = self._fetch_model_html(slug, display_name, runtime)
                if not html:
                    continue

                page_records = self._parse_model_page(slug, display_name, html)
                for record in page_records:
                    key = (
                        record["model_name"],
                        record["variant"],
                        str(record.get("model_year") or ""),
                        int(record["price_int"]),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append(record)
        finally:
            if owns_runtime:
                runtime.stop()

        return records

    def _discover_model_entries(self) -> list[tuple[str, str]]:
        response = http_get("https://talep.citroen.com.tr/fiyat-listesi")
        soup = BeautifulSoup(response.text, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")
        if not next_data or not next_data.string:
            return []

        data = json.loads(next_data.string)
        entries: list[tuple[str, str]] = []
        for model in data.get("props", {}).get("pageProps", {}).get("models", []):
            attrs = model.get("attributes", {})
            slug = str(attrs.get("Name") or "").strip()
            display_name = self._clean_text(str(attrs.get("DisplayName") or ""))
            if not slug:
                continue
            if attrs.get("FiyatListesindeGoster") or slug in self.CLICK_FALLBACKS:
                entries.append((slug, display_name or self.MODEL_ALIASES.get(slug, slug)))
        return entries

    def _fetch_model_html(self, slug: str, display_name: str, runtime: SharedPlaywrightRuntime) -> str | None:
        direct_url = f"https://talep.citroen.com.tr/fiyat-listesi/arac/{slug}"
        html = self._render_url(direct_url, runtime=runtime, post_load_wait_ms=3500)
        if self._is_valid_model_page(html):
            return html

        click_label = self.CLICK_FALLBACKS.get(slug)
        if not click_label:
            return None

        def navigate_from_landing(page) -> None:
            try:
                locator = page.get_by_text(click_label, exact=False).first
                locator.click(timeout=3000, force=True)
                page.wait_for_timeout(3000)
            except Exception:
                pass

        fallback_html = self._render_url(
            "https://talep.citroen.com.tr/fiyat-listesi/",
            runtime=runtime,
            post_load_wait_ms=2500,
            on_after_load=navigate_from_landing,
        )
        return fallback_html if self._is_valid_model_page(fallback_html) else None

    def _render_url(
        self,
        url: str,
        *,
        runtime: SharedPlaywrightRuntime,
        post_load_wait_ms: int,
        on_after_load=None,
    ) -> str:
        context, page = runtime.new_context_page(navigation_timeout_ms=60000)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            self.dismiss_cookie_banners(page)
            if on_after_load is not None:
                on_after_load(page)
                self.dismiss_cookie_banners(page)
            if post_load_wait_ms > 0:
                page.wait_for_timeout(post_load_wait_ms)
            return page.content()
        finally:
            context.close()

    def _is_valid_model_page(self, html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        if not h1:
            return False
        heading = self._clean_text(h1.get_text(" ", strip=True)).upper()
        return "FİYAT LİSTESİ" in heading or "FIYAT LISTESI" in heading

    def _parse_model_page(self, slug: str, display_name: str, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = next((tbl for tbl in soup.find_all("table") if "Versiyonlar" in tbl.get_text(" ", strip=True)), None)
        if table is None:
            return []

        model_name = self.MODEL_ALIASES.get(slug, self._normalize_display_name(display_name))
        rows = table.find_all("tr")
        if not rows:
            return []

        header_cells = [self._clean_text(cell.get_text(" ", strip=True)) for cell in rows[0].find_all(["th", "td"])]
        campaign_idx = None
        list_idx = None
        year_idx = None
        for idx, header in enumerate(header_cells):
            upper_header = header.upper()
            if "MODEL YILI" in upper_header:
                year_idx = idx
            elif "ANAHTAR TESLIM FIYATI" in upper_header or "ANAHTAR TESLİM FİYATI" in upper_header:
                list_idx = idx
            elif "AVANTAJLI FIYAT" in upper_header or "KAMPANYA" in upper_header or "ÖZEL" in upper_header:
                campaign_idx = idx

        if list_idx is None:
            return []

        records: list[dict] = []
        for tr in rows[1:]:
            cols = [self._clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
            if len(cols) < 4:
                continue

            engine = cols[0]
            trims = self._split_tokens(cols[1])
            years = self._split_tokens(cols[year_idx]) if year_idx is not None and year_idx < len(cols) else ["2026"]
            list_prices = self._extract_prices(cols[list_idx]) if list_idx < len(cols) else []
            campaign_prices = self._extract_prices(cols[campaign_idx]) if campaign_idx is not None and campaign_idx < len(cols) else []

            expanded = max(len(trims), len(years), len(list_prices), len(campaign_prices), 1)
            for idx in range(expanded):
                trim = trims[idx] if idx < len(trims) else (trims[-1] if trims else "")
                year_val = years[idx] if idx < len(years) else (years[-1] if years else "2026")
                list_price = list_prices[idx] if idx < len(list_prices) else (list_prices[-1] if list_prices else None)
                campaign_price = campaign_prices[idx] if idx < len(campaign_prices) else None

                if not list_price and not campaign_price:
                    continue
                final_list = list_price or campaign_price
                final_campaign = campaign_price or list_price
                if not final_list or not final_campaign:
                    continue

                variant_name = " ".join(part for part in (model_name, trim, engine) if part).strip()
                discount_amount = max(0, final_list - final_campaign)
                discount_pct = round((discount_amount / final_list) * 100, 1) if discount_amount and final_list else 0.0
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
                        "model_year": year_val,
                        "currency": "TRY",
                    }
                )

        return records

    @staticmethod
    def _split_tokens(value: str) -> list[str]:
        cleaned = CitroenScraper._clean_text(value)
        parts = [part for part in cleaned.split() if part]
        if not parts:
            return []
        return parts

    @staticmethod
    def _extract_prices(value: str) -> list[int]:
        prices: list[int] = []
        for match in re.findall(r"\d[\d.]+\s*TL", value):
            parsed = parse_price_str(match)
            if parsed:
                prices.append(parsed)
        return prices

    @staticmethod
    def _normalize_display_name(value: str) -> str:
        return CitroenScraper._clean_text(
            value.replace("Hybrid 145", "").replace("Elektrikli", "ë").replace("  ", " ")
        )

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()
