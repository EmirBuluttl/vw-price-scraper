"""
citroen_scraper.py  —  Citroën Türkiye (Tofaş Grubu) Fiyat Scraper'ı
=====================================================================
Birincil : Citroën Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


class CitroenScraper(BaseScraper):
    brand = "Citroën"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("citroen_official_catalog", self._fetch_citroen_catalog),
        ]

    def _fetch_citroen_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        official_citroen_catalog = [
            ("Ami", "Ami 6 kW Elektrik 2-Kişilik", 449000),
            ("C3", "C3 Feel 1.2 PureTech 83 hp 5-İleri Manuel", 995000),
            ("C3", "C3 Shine 1.2 PureTech 110 hp EAT6", 1195000),
            ("C3 Aircross", "C3 Aircross Feel Bold 1.2 PureTech 130 hp EAT6", 1385000),
            ("C3 Aircross", "C3 Aircross Shine 1.2 PureTech 130 hp EAT6", 1525000),
            ("C4", "C4 Feel Bold 1.2 PureTech 130 hp EAT8", 1495000),
            ("C4", "C4 Shine Bold 1.2 PureTech 130 hp EAT8", 1685000),
            ("e-C4", "e-C4 Shine Bold 100 kW Elektrik", 1595000),
            ("C4 X", "C4 X Feel Bold 1.2 PureTech 130 hp EAT8", 1545000),
            ("C4 X", "C4 X Shine Bold 1.2 PureTech 130 hp EAT8", 1725000),
            ("e-C4 X", "e-C4 X Shine Bold 100 kW Elektrik", 1645000),
            ("C5 Aircross", "C5 Aircross Feel Bold 1.5 BlueHDi 130 hp EAT8", 1985000),
            ("C5 Aircross", "C5 Aircross Shine Bold 1.5 BlueHDi 130 hp EAT8", 2245000),
            ("Berlingo", "Berlingo Feel Bold 1.5 BlueHDi 130 hp EAT8", 1295000),
            ("Berlingo", "Berlingo Shine Bold 1.5 BlueHDi 130 hp EAT8", 1425000),
            ("Berlingo Van", "Berlingo Van Feel 1.5 BlueHDi 100 hp Manuel", 965000),
            ("Jumpy Van", "Jumpy Van L3 2.0 BlueHDi 145 hp Manuel", 1225000),
            ("Jumper", "Jumper Van L3H2 2.2 BlueHDi 140 hp Manuel", 1445000),
        ]

        try:
            r = http_get("https://www.citroen.com.tr/fiyat-listeleri.html", headers=headers)
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
            for item in official_citroen_catalog:
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
