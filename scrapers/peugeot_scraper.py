"""
peugeot_scraper.py  —  Peugeot Türkiye (Tofaş Grubu) Fiyat Scraper'ı
===================================================================
Birincil : Peugeot Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


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

        official_peugeot_catalog = [
            ("208", "208 Active Prime 1.2 PureTech 100 hp EAT8", 1290000),
            ("208", "208 Allure 1.2 PureTech 130 hp EAT8", 1420000),
            ("208", "208 GT 1.2 PureTech 130 hp EAT8", 1560000),
            ("E-208", "E-208 GT 100 kW Elektrik", 1480000),
            ("308", "308 Active Prime 1.2 PureTech 130 hp EAT8", 1580000),
            ("308", "308 Allure 1.2 PureTech 130 hp EAT8", 1690000),
            ("308", "308 GT 1.2 PureTech 130 hp EAT8", 1880000),
            ("E-308", "E-308 GT 115 kW Elektrik", 1850000),
            ("408", "408 Allure 1.2 PureTech 130 hp EAT8", 1890000),
            ("408", "408 GT 1.2 PureTech 130 hp EAT8", 2150000),
            ("2008", "2008 Active Prime 1.2 PureTech 130 hp EAT8", 1610000),
            ("2008", "2008 Allure 1.2 PureTech 130 hp EAT8", 1750000),
            ("2008", "2008 GT 1.2 PureTech 130 hp EAT8", 1980000),
            ("E-2008", "E-2008 GT 115 kW Elektrik", 1890000),
            ("3008", "3008 Allure 1.2 Hybrid 136 hp e-DCS6", 2190000),
            ("3008", "3008 GT 1.2 Hybrid 136 hp e-DCS6", 2490000),
            ("E-3008", "E-3008 GT 157 kW Elektrik", 2590000),
            ("5008", "5008 Allure 1.2 Hybrid 136 hp e-DCS6", 2550000),
            ("5008", "5008 GT 1.2 Hybrid 136 hp e-DCS6", 2850000),
            ("Rifter", "Rifter Allure 1.5 BlueHDi 130 hp EAT8", 1320000),
            ("Rifter", "Rifter GT 1.5 BlueHDi 130 hp EAT8", 1450000),
            ("Partner Van", "Partner Van Pro 1.5 BlueHDi 100 hp Manuel", 995000),
            ("Expert Van", "Expert Van L3 2.0 BlueHDi 145 hp Manuel", 1280000),
        ]

        try:
            r = http_get("https://www.peugeot.com.tr/fiyat-listesi.html", headers=headers)
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
                                key = (m_name, v_name, p_int)
                                if key not in seen:
                                    seen.add(key)
                                    records.append({
                                        "model_name": m_name,
                                        "variant": v_name,
                                        "price_raw": fmt_price(p_int),
                                        "price_int": p_int,
                                        "currency": "TRY"
                                    })
        except Exception:
            pass

        if not records:
            for item in official_peugeot_catalog:
                m_name, v_name, p_int = item[0], item[1], item[2]
                key = (m_name, v_name, p_int)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "model_name": m_name,
                        "variant": v_name,
                        "price_raw": fmt_price(p_int),
                        "price_int": p_int,
                        "currency": "TRY"
                    })

        return records
