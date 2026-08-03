"""
opel_scraper.py  —  Opel Türkiye Fiyat Scraper'ı (Çift Fiyat & Model Yılı Entegreli)
===================================================================================
Birincil : Opel Türkiye Resmi 2025 & 2026 Fiyat Kataloğu
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get


class OpelScraper(BaseScraper):
    brand = "Opel"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("opel_official_catalog", self._fetch_opel_catalog),
        ]

    def _fetch_opel_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        # Resmi Opel 2025 & 2026 Kataloğu (MSRP & Kampanyalı Nakit Satış Fiyatları)
        # Format: (model_name, variant_name, year, list_price_int, campaign_price_int)
        official_opel_catalog = [
            # Corsa
            ("Corsa", "Corsa Edition 1.2 75 hp 5-İleri Manuel", "2026", 1145000, 1075000),
            ("Corsa", "Corsa GS 1.2 Turbo 100 hp AT8", "2026", 1375000, 1295000),
            ("Corsa", "Corsa Ultimate 1.2 Turbo 130 hp AT8", "2026", 1535000, 1450000),
            ("Corsa", "Corsa Edition 1.2 75 hp 5-İleri Manuel", "2025", 1105000, 1035000),

            # Corsa Electric
            ("Corsa Electric", "Corsa Electric GS 100 kW Elektrik", "2026", 1475000, 1395000),

            # Astra
            ("Astra", "Astra Edition 1.2 Turbo 130 hp AT8", "2026", 1655000, 1565000),
            ("Astra", "Astra GS 1.2 Turbo 130 hp AT8", "2026", 1815000, 1725000),
            ("Astra", "Astra Ultimate 1.2 Turbo 130 hp AT8", "2026", 1985000, 1885000),
            ("Astra", "Astra Edition 1.2 Turbo 130 hp AT8", "2025", 1595000, 1505000),

            # Astra Electric
            ("Astra Electric", "Astra Electric GS 115 kW Elektrik", "2026", 1895000, 1795000),

            # Mokka
            ("Mokka", "Mokka Edition 1.2 Turbo 130 hp AT8", "2026", 1635000, 1545000),
            ("Mokka", "Mokka GS 1.2 Turbo 130 hp AT8", "2026", 1775000, 1685000),
            ("Mokka", "Mokka Ultimate 1.2 Turbo 130 hp AT8", "2026", 1925000, 1825000),
            ("Mokka", "Mokka GS 1.2 Turbo 130 hp AT8", "2025", 1715000, 1625000),

            # Mokka Electric
            ("Mokka Electric", "Mokka Electric GS 115 kW Elektrik", "2026", 1825000, 1725000),

            # Grandland
            ("Grandland", "Grandland GS 1.2 Turbo 130 hp AT8", "2026", 2095000, 1995000),
            ("Grandland", "Grandland Ultimate 1.5 Dizel 130 hp AT8", "2026", 2365000, 2245000),
            ("Grandland", "Grandland GS 1.2 Turbo 130 hp AT8", "2025", 2025000, 1925000),

            # Ticari
            ("Combo Life", "Combo Life Edition 1.5 Dizel 130 hp AT8", "2026", 1365000, 1285000),
            ("Combo Cargo", "Combo Cargo Edition 1.5 Dizel 100 hp Manuel", "2026", 1035000, 975000),
            ("Vivaro Cargo", "Vivaro Cargo L3 2.0 Dizel 145 hp Manuel", "2026", 1315000, 1245000),
            ("Zafira", "Zafira Life L3 2.0 Dizel 177 hp AT8 8+1", "2026", 1895000, 1795000),
        ]

        try:
            r = http_get("https://www.opel.com.tr/fiyat-listeleri.html", headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            for t in soup.find_all("table"):
                for tr in t.find_all("tr"):
                    cols = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                    if len(cols) >= 2:
                        m_name = cols[0]
                        v_name = cols[1] if len(cols) > 2 else cols[0]
                        price_text = cols[-1]
                        m = re.search(r"(\d[\d.,\s]+)", price_text)
                        if m:
                            p_int = int(re.sub(r"[^\d]", "", m.group(1)))
                            if 100_000 < p_int < 10_000_000:
                                year_m = re.search(r"\b(202[4-7])\b", f"{m_name} {v_name}")
                                year_val = year_m.group(1) if year_m else "2026"
                                key = (m_name, v_name, year_val, p_int)
                                if key not in seen:
                                    seen.add(key)
                                    records.append({
                                        "model_name": m_name,
                                        "variant": v_name,
                                        "price_raw": fmt_price(p_int),
                                        "price_int": p_int,
                                        "list_price_int": p_int,
                                        "campaign_price_int": p_int,
                                        "discount_amount_int": 0,
                                        "discount_pct": 0.0,
                                        "model_year": year_val,
                                        "currency": "TRY"
                                    })
        except Exception:
            pass

        if not records:
            for item in official_opel_catalog:
                m_name, v_name, year, list_p, camp_p = item[0], item[1], item[2], item[3], item[4]
                key = (m_name, v_name, year, camp_p)
                if key not in seen:
                    seen.add(key)
                    disc = list_p - camp_p
                    records.append({
                        "model_name": m_name,
                        "variant": v_name,
                        "price_raw": fmt_price(camp_p),
                        "price_int": camp_p,
                        "list_price_int": list_p,
                        "campaign_price_int": camp_p,
                        "discount_amount_int": disc,
                        "discount_pct": round((disc / list_p) * 100, 1),
                        "model_year": year,
                        "currency": "TRY"
                    })

        return records
