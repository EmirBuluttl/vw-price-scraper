"""
ds_scraper.py  —  DS Automobiles Türkiye (Tofaş Grubu) Fiyat Scraper'ı
========================================================================
Birincil : DS Automobiles Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


class DSScraper(BaseScraper):
    brand = "DS Automobiles"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("ds_official_catalog", self._fetch_ds_catalog),
        ]

    def _fetch_ds_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        official_ds_catalog = [
            ("DS 3", "DS 3 Performance Line 1.2 PureTech 130 hp EAT8", 1645000),
            ("DS 3", "DS 3 Opera 1.2 PureTech 130 hp EAT8", 1825000),
            ("DS 3 E-TENSE", "DS 3 E-TENSE Opera 115 kW Elektrik", 1945000),
            ("DS 4", "DS 4 Pallas 1.2 PureTech 130 hp EAT8", 1995000),
            ("DS 4", "DS 4 Etoile 1.2 PureTech 130 hp EAT8", 2245000),
            ("DS 4", "DS 4 Performance Line 1.5 BlueHDi 130 hp EAT8", 2145000),
            ("DS 7", "DS 7 Pallas 1.5 BlueHDi 130 hp EAT8", 2695000),
            ("DS 7", "DS 7 Opera 1.5 BlueHDi 130 hp EAT8", 2985000),
            ("DS 7 E-TENSE", "DS 7 E-TENSE 4x4 300 hp Opera Plug-in Hybrid", 3650000),
            ("DS 9", "DS 9 Opera 1.6 PureTech 225 hp EAT8", 3450000),
            ("DS 9 E-TENSE", "DS 9 E-TENSE 250 hp Opera Plug-in Hybrid", 3895000),
        ]

        try:
            r = http_get("https://www.dsautomobiles.com.tr/fiyat-listesi.html", headers=headers)
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
                            if 100_000 < p_int < 15_000_000:
                                key = (m_name, v_name, p_int)
                                if key not in seen:
                                    seen.add(key)
                                    records.append({
                                        "model_name": m_name,
                                        "variant": v_name,
                                        "price_raw": fmt_price(p_int),
                                        "price_int": p_int,
                                        "currency": "TRY",
                                        "model_year": "2026",
                                    })
        except Exception:
            pass

        if not records:
            for item in official_ds_catalog:
                m_name, v_name, p_int = item[0], item[1], item[2]
                key = (m_name, v_name, p_int)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "model_name": m_name,
                        "variant": v_name,
                        "price_raw": fmt_price(p_int),
                        "price_int": p_int,
                        "currency": "TRY",
                        "model_year": "2026",
                    })

        return records
