"""
Renault Turkiye fiyat scraper.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price


class RenaultScraper(BaseScraper):
    brand = "Renault"
    validation_profile = ValidationProfile(
        min_records=6,
        required_models=("Clio", "Captur", "Austral"),
        min_required_models=2,
    )

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [("renault_playwright_live", self._fetch_renault_playwright_live)]

    def _fetch_renault_playwright_live(self) -> list[dict]:
        records: list[dict] = []
        seen: set[tuple] = set()
        url = "https://www.renault.com.tr/fiyat-listesi.html"

        try:
            html = self.fetch_page_html(url, post_load_wait_ms=3000)
            soup = BeautifulSoup(html, "html.parser")
            current_model = "Renault"

            for table in soup.find_all("table"):
                table_text = table.get_text(" ", strip=True)
                match = re.search(r"(Clio|Megane|Captur|Austral|Duster|Symbioz|Scenic|Taliant|Koleos|Express|Master|Kangoo)", table_text, re.IGNORECASE)
                if match:
                    current_model = match.group(1)

                for tr in table.find_all("tr"):
                    cols = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                    if len(cols) < 2:
                        continue

                    variant_raw = cols[0]
                    if any(token in variant_raw.upper() for token in ["MODEL", "DONANIM"]):
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
                    if "CLIO" in variant_raw.upper():
                        model_name = "Clio"
                    elif "MEGANE" in variant_raw.upper():
                        model_name = "Megane Sedan"
                    elif "CAPTUR" in variant_raw.upper():
                        model_name = "Captur"
                    elif "AUSTRAL" in variant_raw.upper():
                        model_name = "Austral"
                    elif "DUSTER" in variant_raw.upper():
                        model_name = "Renault Duster"
                    elif "SYMBIOZ" in variant_raw.upper():
                        model_name = "Symbioz"
                    elif "SCENIC" in variant_raw.upper():
                        model_name = "Scenic E-Tech"

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
            print(f"Playwright Renault Live Scrape Error: {exc}")

        return records
