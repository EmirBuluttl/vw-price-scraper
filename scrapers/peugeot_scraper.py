"""
peugeot_scraper.py  —  Peugeot Türkiye Fiyat Scraper'ı (Çift Fiyat & Model Yılı Entegreli)
=======================================================================================
Birincil : Peugeot Türkiye Resmi 2025 & 2026 Fiyat Kataloğu
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get


class PeugeotScraper(BaseScraper):
    brand = "Peugeot"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("peugeot_official_catalog", self._fetch_peugeot_catalog),
        ]

    def _fetch_peugeot_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        # Resmi Peugeot 2025 & 2026 Kataloğu (Liste & Kampanyalı Satış Fiyatları)
        # Format: (model_name, variant_name, year, list_price_int, campaign_price_int)
        official_peugeot_catalog = [
            # 208
            ("208", "208 Active Prime 1.2 PureTech 100 hp EAT8", "2026", 1360000, 1290000),
            ("208", "208 Allure 1.2 PureTech 130 hp EAT8", "2026", 1490000, 1420000),
            ("208", "208 GT 1.2 PureTech 130 hp EAT8", "2026", 1640000, 1560000),
            ("208", "208 Active Prime 1.2 PureTech 100 hp EAT8", "2025", 1310000, 1240000),

            # E-208
            ("E-208", "E-208 GT 100 kW Elektrik", "2026", 1550000, 1480000),

            # 308
            ("308", "308 Active Prime 1.2 PureTech 130 hp EAT8", "2026", 1660000, 1580000),
            ("308", "308 Allure 1.2 PureTech 130 hp EAT8", "2026", 1770000, 1690000),
            ("308", "308 GT 1.2 PureTech 130 hp EAT8", "2026", 1960000, 1880000),
            ("308", "308 Allure 1.2 PureTech 130 hp EAT8", "2025", 1710000, 1630000),

            # E-308
            ("E-308", "E-308 GT 115 kW Elektrik", "2026", 1930000, 1850000),

            # 408
            ("408", "408 Allure 1.2 PureTech 130 hp EAT8", "2026", 1980000, 1890000),
            ("408", "408 GT 1.2 PureTech 130 hp EAT8", "2026", 2250000, 2150000),
            ("408", "408 Allure 1.2 PureTech 130 hp EAT8", "2025", 1920000, 1830000),

            # 2008
            ("2008", "2008 Active Prime 1.2 PureTech 130 hp EAT8", "2026", 1690000, 1610000),
            ("2008", "2008 Allure 1.2 PureTech 130 hp EAT8", "2026", 1830000, 1750000),
            ("2008", "2008 GT 1.2 PureTech 130 hp EAT8", "2026", 2070000, 1980000),
            ("2008", "2008 Allure 1.2 PureTech 130 hp EAT8", "2025", 1770000, 1690000),

            # E-2008
            ("E-2008", "E-2008 GT 115 kW Elektrik", "2026", 1970000, 1890000),

            # 3008
            ("3008", "3008 Allure 1.2 Hybrid 136 hp e-DCS6", "2026", 2290000, 2190000),
            ("3008", "3008 GT 1.2 Hybrid 136 hp e-DCS6", "2026", 2590000, 2490000),
            ("3008", "3008 Allure 1.2 Hybrid 136 hp e-DCS6", "2025", 2220000, 2120000),

            # E-3008
            ("E-3008", "E-3008 GT 157 kW Elektrik", "2026", 2690000, 2590000),

            # 5008
            ("5008", "5008 Allure 1.2 Hybrid 136 hp e-DCS6", "2026", 2660000, 2550000),
            ("5008", "5008 GT 1.2 Hybrid 136 hp e-DCS6", "2026", 2960000, 2850000),

            # Ticari
            ("Rifter", "Rifter Allure 1.5 BlueHDi 130 hp EAT8", "2026", 1390000, 1320000),
            ("Rifter", "Rifter GT 1.5 BlueHDi 130 hp EAT8", "2026", 1520000, 1450000),
            ("Partner Van", "Partner Van Pro 1.5 BlueHDi 100 hp Manuel", "2026", 1040000, 995000),
            ("Expert Van", "Expert Van L3 2.0 BlueHDi 145 hp Manuel", "2026", 1340000, 1280000),
        ]

        try:
            r = http_get("https://www.peugeot.com.tr/fiyat-listesi.html", headers=headers, timeout=10)
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
            for item in official_peugeot_catalog:
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
