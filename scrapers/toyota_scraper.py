"""
toyota_scraper.py  —  Toyota Türkiye Fiyat Scraper'ı (Playwright Canlı Chrome Otomasyonu)
========================================================================================
Birincil : Playwright ile https://turkiye.toyota.com.tr/middle/fiyatl_aksesuar.html Canlı Sayfa Taraması
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base_scraper import BaseScraper, fmt_price


class ToyotaScraper(BaseScraper):
    brand = "Toyota"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("toyota_playwright_live", self._fetch_toyota_playwright_live),
        ]

    def _fetch_toyota_playwright_live(self) -> list[dict]:
        records: list[dict] = []
        seen: set[tuple] = set()

        url = "https://turkiye.toyota.com.tr/middle/fiyatl_aksesuar.html"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                )
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
                html = page.content()
                browser.close()

                soup = BeautifulSoup(html, "html.parser")
                current_model = "Toyota"

                for table in soup.find_all("table"):
                    table_text = table.get_text()
                    m_search = re.search(r"(Corolla|C-HR|Yaris|RAV4|Hilux|Proace|Camry|Land Cruiser)", table_text, re.IGNORECASE)
                    if m_search:
                        current_model = m_search.group(1)

                    for tr in table.find_all("tr"):
                        cols = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                        if len(cols) >= 2:
                            variant_raw = cols[0]
                            if "MODEL" in variant_raw.upper() or "DONANIM" in variant_raw.upper():
                                continue

                            prices_found = []
                            for col_val in cols[1:]:
                                pm = re.search(r"(\d[\d.,\s]+)", col_val)
                                if pm:
                                    p_val = int(re.sub(r"[^\d]", "", pm.group(1)))
                                    if 100_000 < p_val < 10_000_000:
                                        prices_found.append(p_val)

                            if len(prices_found) >= 2:
                                list_price = prices_found[0]
                                camp_price = prices_found[1]
                            elif len(prices_found) == 1:
                                list_price = prices_found[0]
                                camp_price = prices_found[0]
                            else:
                                continue

                            year_m = re.search(r"\b(202[4-7])\b", f"{variant_raw} {table_text}")
                            year_val = year_m.group(1) if year_m else "2026"

                            model_name = current_model
                            if "COROLLA CROSS" in variant_raw.upper(): model_name = "Corolla Cross"
                            elif "COROLLA HB" in variant_raw.upper(): model_name = "Corolla Hatchback"
                            elif "COROLLA" in variant_raw.upper(): model_name = "Corolla"
                            elif "C-HR" in variant_raw.upper(): model_name = "C-HR"
                            elif "YARIS CROSS" in variant_raw.upper(): model_name = "Yaris Cross"
                            elif "YARIS" in variant_raw.upper(): model_name = "Yaris"
                            elif "RAV4" in variant_raw.upper(): model_name = "RAV4"
                            elif "HILUX" in variant_raw.upper(): model_name = "Hilux"

                            key = (model_name, variant_raw, year_val, camp_price)
                            if key not in seen:
                                seen.add(key)
                                disc = max(0, list_price - camp_price)
                                disc_pct = round((disc / list_price) * 100, 1) if list_price > 0 else 0.0

                                records.append({
                                    "model_name": model_name,
                                    "variant": variant_raw,
                                    "price_raw": fmt_price(camp_price),
                                    "price_int": camp_price,
                                    "list_price_int": list_price,
                                    "campaign_price_int": camp_price,
                                    "discount_amount_int": disc,
                                    "discount_pct": disc_pct,
                                    "model_year": year_val,
                                    "currency": "TRY"
                                })
        except Exception as e:
            print(f"Playwright Toyota Live Scrape Error: {e}")

        return records
