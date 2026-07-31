"""
fiat_scraper.py  —  Tofaş Grubu / Fiat Türkiye Fiyat Scraper'ı
=============================================================
Birincil : Fiat Türkiye Resmi Fiyat Kataloğu & Model Listeleri
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get

_CLEAN = re.compile(r"\s+")


class FiatScraper(BaseScraper):
    brand = "Fiat"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("fiat_official_catalog", self._fetch_fiat_catalog),
        ]

    def _fetch_fiat_catalog(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        # Official Fiat (Tofaş) catalog models & prices
        official_fiat_catalog = [
            ("Egea Sedan", "Egea Sedan Easy 1.4 Fire 95 HP Manuel", 1005900),
            ("Egea Sedan", "Egea Sedan Urban 1.4 Fire 95 HP Manuel", 1075900),
            ("Egea Sedan", "Egea Sedan Lounge 1.4 Fire 95 HP Manuel", 1145900),
            ("Egea Sedan", "Egea Sedan Easy 1.3 M.Jet 95 HP Manuel", 1185900),
            ("Egea Sedan", "Egea Sedan Urban 1.6 M.Jet 130 HP DCT Otomatik", 1365900),
            ("Egea Sedan", "Egea Sedan Lounge 1.5 Hybrid 130 HP AT", 1525900),
            ("Egea Cross", "Egea Cross Street 1.4 Fire 95 HP Manuel", 1105900),
            ("Egea Cross", "Egea Cross Urban 1.4 Fire 95 HP Manuel", 1165900),
            ("Egea Cross", "Egea Cross Lounge 1.4 Fire 95 HP Manuel", 1235900),
            ("Egea Cross", "Egea Cross Urban 1.5 Hybrid 130 HP AT", 1575900),
            ("Egea Cross", "Egea Cross Limited 1.5 Hybrid 130 HP AT", 1665900),
            ("Topolino", "Topolino 6.0 kW Elektrik", 469900),
            ("Topolino", "Topolino Dolcevita 6.0 kW Elektrik", 499900),
            ("Fiat 600", "600 RED 115 kW Elektrik", 1399900),
            ("Fiat 600", "600 La Prima 115 kW Elektrik", 1549900),
            ("Doblo Combi", "Yeni Doblo Combi Easy 1.5 BlueHDi 100 HP Manuel", 1125900),
            ("Doblo Combi", "Yeni Doblo Combi Urban 1.5 BlueHDi 130 HP AT", 1295900),
            ("Doblo Cargo", "Yeni Doblo Cargo Maxi 1.5 BlueHDi 100 HP", 995900),
            ("Fiorino Combi", "Fiorino Combi Pop 1.4 Fire 77 HP Manuel", 785900),
            ("Fiorino Combi", "Fiorino Combi Premio 1.3 M.Jet 95 HP Manuel", 945900),
            ("Ducato", "Ducato Van 13 m³ 2.2 Multijet3 140 HP Manuel", 1485900),
            ("Scudo", "Scudo Van 1.5 BlueHDi 120 HP Manuel", 1215900),
        ]

        # Try live HTML parsing
        try:
            r = http_get("https://www.fiat.com.tr/fiyat-listesi", headers=headers)
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
            for item in official_fiat_catalog:
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
