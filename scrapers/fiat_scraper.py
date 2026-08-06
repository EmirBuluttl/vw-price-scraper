"""
Fiat Turkiye fiyat scraper'i.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, ValidationProfile, fmt_price


class FiatScraper(BaseScraper):
    brand = "Fiat"
    validation_profile = ValidationProfile(
        min_records=10,
        required_models=("Egea Sedan", "Egea Cross", "Topolino", "Fiat 600"),
        min_required_models=4,
    )

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("fiat_playwright_live", self._fetch_fiat_playwright_live),
        ]

    def _fetch_fiat_playwright_live(self) -> list[dict]:
        records: list[dict] = []
        seen: set[tuple] = set()
        url = "https://talep.fiat.com.tr/"

        def open_price_cards(page) -> None:
            try:
                page.get_by_text("Binek Araç Fiyat Listesi").first.click(force=True, timeout=1500)
                page.wait_for_timeout(2000)
            except Exception:
                pass

        try:
            html = self.fetch_page_html(
                url,
                wait_until="networkidle",
                timeout_ms=30000,
                post_load_wait_ms=2500,
                on_after_load=open_price_cards,
            )
            soup = BeautifulSoup(html, "html.parser")
            current_model = "Fiat"

            for table in soup.find_all("table"):
                table_text = table.get_text()
                if "Opsiyon" in table_text and "Manuel" not in table_text and "Otomatik" not in table_text:
                    continue

                m_search = re.search(
                    r"(Egea Cross|Egea Sedan|Egea Hatchback|Topolino|Fiat 600|Fiat 500|Doblo|Fiorino|Ducato|Scudo)",
                    table_text,
                    re.IGNORECASE,
                )
                if m_search:
                    current_model = m_search.group(1)

                for tr in table.find_all("tr"):
                    cols = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                    if len(cols) < 2:
                        continue

                    variant_raw = self._clean_variant(cols[0])
                    if any(token in variant_raw.upper() for token in ["MODEL", "DONANIM", "OPSİYON"]):
                        continue

                    prices_found = []
                    for col_val in cols[1:]:
                        pm = re.search(r"(\d[\d.,\s]+)", col_val)
                        if not pm:
                            continue
                        p_val = int(re.sub(r"[^\d]", "", pm.group(1)))
                        if 100_000 < p_val < 10_000_000:
                            prices_found.append(p_val)

                    if len(prices_found) >= 2:
                        list_price, camp_price = prices_found[0], prices_found[1]
                    elif len(prices_found) == 1:
                        list_price = camp_price = prices_found[0]
                    else:
                        continue

                    year_m = re.search(r"\b(202[4-7])\b", f"{variant_raw} {table_text}")
                    year_val = year_m.group(1) if year_m else "2026"

                    model_name = current_model
                    if "CROSS" in variant_raw.upper() or "TRACTION+" in variant_raw.upper():
                        model_name = "Egea Cross"
                    elif any(token in variant_raw.upper() for token in ["EASY", "URBAN", "LOUNGE"]):
                        model_name = "Egea Sedan"
                    elif "TOPOLINO" in variant_raw.upper():
                        model_name = "Topolino"
                    elif any(token in variant_raw.upper() for token in ["600", "ICON", "LA PRIMA"]):
                        model_name = "Fiat 600"
                    elif "DOBLO" in variant_raw.upper():
                        model_name = "Doblo Combi"
                    elif "FIORINO" in variant_raw.upper():
                        model_name = "Fiorino Combi"

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
        except Exception as e:
            print(f"Playwright Fiat Live Scrape Error: {e}")

        return records

    @staticmethod
    def _clean_variant(value: str) -> str:
        cleaned = value or ""
        replacements = [
            ("GSRDizeloil_barrel", "GSR Dizel"),
            ("Dizeloil_barrel", "Dizel"),
            ("Elektrikliev_station", "Elektrikli"),
            ("Hibritenergy_program_saving", "Hibrit"),
            ("OtomatikMHEV", "Otomatik MHEV"),
            ("OtomatikMultiJet", "Otomatik MultiJet"),
            ("ManuelMultiJet", "Manuel MultiJet"),
            ("HPElektrikli", "HP Elektrikli"),
            ("HPElektrik", "HP Elektrik"),
            ("DCTGSR", "DCT GSR"),
            ("eDCTHibrit", "eDCT Hibrit"),
            ("Traction+Dizel", "Traction+ Dizel"),
            ("83 kW/113 HPElektrikli", "83 kW/113 HP Elektrikli"),
            ("115 kW/156 HPElektrikli", "115 kW/156 HP Elektrikli"),
            ("87 kW/118 HPElektrik", "87 kW/118 HP Elektrik"),
            ("6 kW/8 HPElektrikli", "6 kW/8 HP Elektrikli"),
        ]
        for old, new in replacements:
            cleaned = cleaned.replace(old, new)

        cleaned = re.sub(r"(?<=\d)(?=[A-ZÇĞİÖŞÜ])", " ", cleaned)
        cleaned = re.sub(r"(?<=[A-Za-zÇĞİÖŞÜçğıöşü])(?=\d)", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
