"""
Peugeot Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price


class PeugeotScraper(BaseScraper):
    brand = "Peugeot"
    validation_profile = ValidationProfile(
        min_records=8,
        required_models=("208", "2008", "3008", "408"),
        min_required_models=3,
        required_variant_keywords=("145",),
    )

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("peugeot_playwright_live", self._fetch_peugeot_playwright_live)]

    def _fetch_peugeot_playwright_live(self) -> list[dict]:
        records: list[dict] = []
        seen: set[tuple] = set()
        url = "https://kampanya.peugeot.com.tr/fiyat-listesi/"

        try:
            html = self.fetch_page_html(url, post_load_wait_ms=3000)
            soup = BeautifulSoup(html, "html.parser")
            current_model = "Peugeot"

            for table in soup.find_all("table"):
                table_text = table.get_text(" ", strip=True)
                match = re.search(r"(PEUGEOT\s+[\w\d]+|208|308|408|2008|3008|5008|Rifter|Partner|Expert|Boxer)", table_text, re.IGNORECASE)
                if match:
                    current_model = match.group(1).upper().replace("PEUGEOT", "").strip() or "Peugeot"

                for tr in table.find_all("tr"):
                    cols = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                    if len(cols) < 2:
                        continue

                    variant_raw = cols[0]
                    if "MODELLER" in variant_raw.upper():
                        continue

                    prices_found = []
                    for col_val in cols[1:]:
                        pm = re.search(r"(\d[\d.,\s]+)", col_val)
                        if not pm:
                            continue
                        p_val = int(re.sub(r"[^\d]", "", pm.group(1)))
                        if 100_000 < p_val < 10_000_000:
                            prices_found.append(p_val)

                    if not prices_found:
                        continue

                    if len(prices_found) >= 2:
                        list_price, camp_price = prices_found[0], prices_found[1]
                    else:
                        list_price = camp_price = prices_found[0]

                    year_match = re.search(r"\b(202[4-7])\b", f"{variant_raw} {table_text}")
                    year_val = year_match.group(1) if year_match else "2026"

                    model_name = current_model
                    for token, mapped in [
                        ("5008", "5008"),
                        ("3008", "3008"),
                        ("2008", "2008"),
                        ("408", "408"),
                        ("308", "308"),
                        ("208", "208"),
                    ]:
                        if token in variant_raw:
                            model_name = mapped
                            break
                    if "RIFTER" in variant_raw.upper():
                        model_name = "Rifter"
                    elif "PARTNER" in variant_raw.upper():
                        model_name = "Partner Van"
                    elif "EXPERT" in variant_raw.upper():
                        model_name = "Expert Van"
                    elif "BOXER" in variant_raw.upper():
                        model_name = "Boxer Van"

                    key = (model_name, variant_raw, year_val, camp_price)
                    if key in seen:
                        continue

                    seen.add(key)
                    disc = max(0, list_price - camp_price)
                    disc_pct = round((disc / list_price) * 100, 1) if list_price > 0 else 0.0
                    records.append(
                        {
                            "model_name": model_name,
                            "variant": variant_raw,
                            "price_raw": fmt_price(camp_price),
                            "price_int": camp_price,
                            "list_price_int": list_price,
                            "campaign_price_int": camp_price,
                            "discount_amount_int": disc,
                            "discount_pct": disc_pct,
                            "model_year": year_val,
                            "currency": "TRY",
                        }
                    )
        except Exception as exc:
            print(f"Playwright Peugeot Live Scrape Error: {exc}")

        return records
