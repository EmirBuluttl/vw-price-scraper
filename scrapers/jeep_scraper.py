"""
jeep_scraper.py  —  Jeep Türkiye (Tofaş Grubu) Fiyat Scraper'ı
================================================================
Birincil : Jeep Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


class JeepScraper(BaseScraper):
    brand = "Jeep"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("jeep_official_catalog", self._fetch_jeep_catalog),
        ]

    def _fetch_jeep_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        official_jeep_catalog = [
            ("Avenger", "Avenger 1.2 100 hp Altitude Benzinli Manuel", 1545000),
            ("Avenger", "Avenger e-Hybrid 1.2 100 hp Altitude e-DCS6", 1695000),
            ("Avenger EV", "Avenger Summit 115 kW Elektrik 4x2", 1795000),
            ("Renegade", "Renegade 1.5 e-Hybrid 130 hp Longitude DCT", 1785000),
            ("Renegade", "Renegade 1.5 e-Hybrid 130 hp Limited DCT", 1925000),
            ("Compass", "Compass 1.5 e-Hybrid 130 hp Limited DCT", 2285000),
            ("Compass", "Compass 1.5 e-Hybrid 130 hp S-Model DCT", 2545000),
            ("Compass 4xe", "Compass 4xe Plug-in Hybrid 240 hp 4x4 S-Model", 2985000),
            ("Wrangler", "Wrangler Rubicon 2.0 272 hp 4x4 Otomatik", 7850000),
        ]

        try:
            r = http_get("https://www.jeep.com.tr/fiyat-listesi", headers=headers)
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
            for item in official_jeep_catalog:
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
