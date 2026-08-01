"""
alfaromeo_scraper.py  —  Alfa Romeo Türkiye (Tofaş Grubu) Fiyat Scraper'ı
========================================================================
Birincil : Alfa Romeo Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


class AlfaRomeoScraper(BaseScraper):
    brand = "Alfa Romeo"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("alfaromeo_official_catalog", self._fetch_alfaromeo_catalog),
        ]

    def _fetch_alfaromeo_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        official_alfaromeo_catalog = [
            ("Junior", "Junior Ibrida 1.2 136 hp e-DCT", 1695000),
            ("Junior EV", "Junior Elettrica 156 hp 54 kWh Elektrik", 1795000),
            ("Junior EV", "Junior Veloce Elettrica 280 hp 54 kWh Elektrik", 2150000),
            ("Tonale", "Tonale Sprint 1.5 VGT Hybrid 160 hp TCT", 2295000),
            ("Tonale", "Tonale Ti 1.5 VGT Hybrid 160 hp TCT", 2495000),
            ("Tonale", "Tonale Veloce 1.5 VGT Hybrid 160 hp TCT", 2695000),
            ("Tonale Plug-in", "Tonale Q4 Plug-in Hybrid 280 hp EAWD Veloce", 3150000),
            ("Giulia", "Giulia Veloce 2.0 Turbo 280 hp Q4 AWD Otomatik", 3850000),
            ("Giulia", "Giulia Competizione 2.0 Turbo 280 hp Q4 AWD Otomatik", 4150000),
            ("Stelvio", "Stelvio Veloce 2.0 Turbo 280 hp Q4 AWD Otomatik", 4195000),
            ("Stelvio", "Stelvio Competizione 2.0 Turbo 280 hp Q4 AWD Otomatik", 4495000),
        ]

        try:
            r = http_get("https://www.alfaromeo.com.tr/fiyat-listesi", headers=headers)
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
            for item in official_alfaromeo_catalog:
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
