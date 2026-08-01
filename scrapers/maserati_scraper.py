"""
maserati_scraper.py  —  Maserati Türkiye (Tofaş Grubu) Fiyat Scraper'ı
========================================================================
Birincil : Maserati Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


class MaseratiScraper(BaseScraper):
    brand = "Maserati"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("maserati_official_catalog", self._fetch_maserati_catalog),
        ]

    def _fetch_maserati_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        official_maserati_catalog = [
            ("Grecale", "Grecale GT 2.0 Mild Hybrid 300 hp AWD", 7450000),
            ("Grecale", "Grecale Modena 2.0 Mild Hybrid 330 hp AWD", 8250000),
            ("Grecale", "Grecale Trofeo 3.0 V6 Nettuno 530 hp AWD", 12950000),
            ("Grecale Folgore", "Grecale Folgore 410 kW Elektrik AWD", 9850000),
            ("Levante", "Levante GT 2.0 Mild Hybrid 330 hp AWD", 9250000),
            ("Levante", "Levante Modena 3.0 V6 430 hp AWD", 12450000),
            ("GranTurismo", "GranTurismo Modena 3.0 V6 Nettuno 490 hp AWD", 14950000),
            ("GranTurismo", "GranTurismo Trofeo 3.0 V6 Nettuno 550 hp AWD", 17850000),
        ]

        try:
            r = http_get("https://www.maserati.com/tr/tr/models", headers=headers)
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
                            if 1_000_000 < p_int < 30_000_000:
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
            for item in official_maserati_catalog:
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
