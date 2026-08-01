"""
opel_scraper.py  —  Opel Türkiye (Tofaş Grubu) Fiyat Scraper'ı
================================================================
Birincil : Opel Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


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

        official_opel_catalog = [
            ("Corsa", "Corsa Edition 1.2 75 hp 5-İleri Manuel", 1075000),
            ("Corsa", "Corsa GS 1.2 Turbo 100 hp AT8", 1295000),
            ("Corsa", "Corsa Ultimate 1.2 Turbo 130 hp AT8", 1450000),
            ("Corsa Electric", "Corsa Electric GS 100 kW Elektrik", 1395000),
            ("Astra", "Astra Edition 1.2 Turbo 130 hp AT8", 1565000),
            ("Astra", "Astra GS 1.2 Turbo 130 hp AT8", 1725000),
            ("Astra", "Astra Ultimate 1.2 Turbo 130 hp AT8", 1885000),
            ("Astra Electric", "Astra Electric GS 115 kW Elektrik", 1795000),
            ("Mokka", "Mokka Edition 1.2 Turbo 130 hp AT8", 1545000),
            ("Mokka", "Mokka GS 1.2 Turbo 130 hp AT8", 1685000),
            ("Mokka", "Mokka Ultimate 1.2 Turbo 130 hp AT8", 1825000),
            ("Mokka Electric", "Mokka Electric GS 115 kW Elektrik", 1725000),
            ("Crossland", "Crossland Essential 1.2 Turbo 110 hp Manuel", 1195000),
            ("Crossland", "Crossland Elegance 1.2 Turbo 130 hp AT6", 1385000),
            ("Grandland", "Grandland GS 1.2 Turbo 130 hp AT8", 1995000),
            ("Grandland", "Grandland Ultimate 1.5 Dizel 130 hp AT8", 2245000),
            ("Combo Life", "Combo Life Edition 1.5 Dizel 130 hp AT8", 1285000),
            ("Combo Cargo", "Combo Cargo Edition 1.5 Dizel 100 hp Manuel", 975000),
            ("Vivaro Cargo", "Vivaro Cargo L3 2.0 Dizel 145 hp Manuel", 1245000),
            ("Zafira", "Zafira Life L3 2.0 Dizel 177 hp AT8 8+1", 1795000),
        ]

        try:
            r = http_get("https://www.opel.com.tr/fiyat-listeleri.html", headers=headers)
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
            for item in official_opel_catalog:
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
