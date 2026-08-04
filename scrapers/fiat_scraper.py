"""
fiat_scraper.py  —  Fiat Türkiye Fiyat Scraper'ı (Playwright Canlı Chrome Otomasyonu)
======================================================================================
Birincil : Playwright ile https://talep.fiat.com.tr/ Canlı Sayfa Taraması
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base_scraper import BaseScraper, fmt_price


class FiatScraper(BaseScraper):
    brand = "Fiat"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("fiat_playwright_live", self._fetch_fiat_playwright_live),
        ]

    def _fetch_fiat_playwright_live(self) -> list[dict]:
        records: list[dict] = []
        seen: set[tuple] = set()

        url = "https://talep.fiat.com.tr/"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                )
                page.goto(url, wait_until="networkidle", timeout=20000)
                
                # Tıklanabilir kategori kartlarına tıkla
                cat_btn = page.get_by_text("Binek Araç Fiyat Listesi").first
                if cat_btn:
                    cat_btn.click()
                    page.wait_for_timeout(2000)

                soup = BeautifulSoup(page.content(), "html.parser")
                browser.close()

                current_model = "Fiat"

                for table in soup.find_all("table"):
                    table_text = table.get_text()
                    if "Opsiyon" in table_text and "Manuel" not in table_text and "Otomatik" not in table_text:
                        continue

                    m_search = re.search(r"(Egea Cross|Egea Sedan|Egea Hatchback|Topolino|Fiat 600|Fiat 500|Doblo|Fiorino|Ducato|Scudo)", table_text, re.IGNORECASE)
                    if m_search:
                        current_model = m_search.group(1)

                    for tr in table.find_all("tr"):
                        cols = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                        if len(cols) >= 2:
                            variant_raw = cols[0]
                            if "MODEL" in variant_raw.upper() or "DONANIM" in variant_raw.upper() or "OPSİYON" in variant_raw.upper():
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
                            if "CROSS" in variant_raw.upper() or "TRACTION+" in variant_raw.upper(): model_name = "Egea Cross"
                            elif "EASY" in variant_raw.upper() or "URBAN" in variant_raw.upper() or "LOUNGE" in variant_raw.upper(): model_name = "Egea Sedan"
                            elif "TOPOLINO" in variant_raw.upper(): model_name = "Topolino"
                            elif "600" in variant_raw.upper() or "ICON" in variant_raw.upper() or "LA PRIMA" in variant_raw.upper(): model_name = "Fiat 600"
                            elif "DOBLO" in variant_raw.upper(): model_name = "Doblo Combi"
                            elif "FIORINO" in variant_raw.upper(): model_name = "Fiorino Combi"

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
            print(f"Playwright Fiat Live Scrape Error: {e}")

        return records
