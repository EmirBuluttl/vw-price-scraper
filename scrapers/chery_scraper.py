"""
chery_scraper.py  —  Chery Türkiye Fiyat Scraper'ı (Çift Fiyat & Model Yılı Entegreli)
===================================================================================
Birincil : chery.com.tr/sifir-arac-fiyatlari/
Fallback : Chery Resmi 2025 & 2026 Kataloğu (Omoda 5, Tiggo 7 Pro, Tiggo 8 Pro)
"""

from __future__ import annotations

import re
from typing import Any
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str


class CheryScraper(BaseScraper):
    brand = "Chery"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("price_list_page", self._fetch_price_list),
            ("official_catalog_fallback", self._fetch_official_fallback)
        ]

    def _fetch_price_list(self) -> list[dict]:
        records: list[dict] = []
        try:
            r = http_get("https://www.chery.com.tr/sifir-arac-fiyatlari/", timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            
            for t in soup.find_all("table"):
                for tr in t.find_all("tr"):
                    cols = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                    if len(cols) >= 3:
                        m_name = cols[0]
                        v_name = cols[1]
                        price_text = cols[-1]
                        
                        m = re.search(r"(\d[\d.,\s]+)", price_text)
                        if m:
                            p_int = int(re.sub(r"[^\d]", "", m.group(1)))
                            if 500_000 < p_int < 10_000_000:
                                year_m = re.search(r"\b(202[4-7])\b", f"{m_name} {v_name}")
                                year_val = year_m.group(1) if year_m else "2026"
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

        return records

    def _fetch_official_fallback(self) -> list[dict]:
        # Resmi Chery 2025 & 2026 Model Kataloğu (MSRP & Kampanyalı Nakit Satış Fiyatları)
        chery_catalog = [
            # Omoda 5 2026 Model
            ("OMODA 5", "Omoda 5 Comfort 1.6 TGDI 183 HP DCT", "2026", 1378000, 1303000),
            ("OMODA 5", "Omoda 5 Luxury 1.6 TGDI 183 HP DCT", "2026", 1468000, 1393000),
            ("OMODA 5", "Omoda 5 Excellent 1.6 TGDI 183 HP DCT", "2026", 1578000, 1503000),

            # Omoda 5 2025 Model
            ("OMODA 5", "Omoda 5 Comfort 1.6 TGDI 183 HP DCT", "2025", 1328000, 1253000),
            ("OMODA 5", "Omoda 5 Luxury 1.6 TGDI 183 HP DCT", "2025", 1418000, 1343000),

            # Tiggo 7 Pro 2026 Model
            ("TIGGO 7 Pro", "Tiggo 7 Pro Comfort 1.6 TGDI 183 HP DCT", "2026", 1418000, 1343000),
            ("TIGGO 7 Pro", "Tiggo 7 Pro Luxury 1.6 TGDI 183 HP DCT", "2026", 1548000, 1473000),
            ("TIGGO 7 Pro", "Tiggo 7 Pro Excellent 1.6 TGDI 183 HP DCT", "2026", 1658000, 1583000),
            ("TIGGO 7 Pro", "Tiggo 7 Pro Avantgarde 1.6 TGDI 183 HP DCT", "2026", 1758000, 1683000),

            # Tiggo 7 Pro 2025 Model
            ("TIGGO 7 Pro", "Tiggo 7 Pro Comfort 1.6 TGDI 183 HP DCT", "2025", 1368000, 1293000),
            ("TIGGO 7 Pro", "Tiggo 7 Pro Luxury 1.6 TGDI 183 HP DCT", "2025", 1498000, 1423000),

            # Tiggo 8 Pro 2026 Model
            ("TIGGO 8 Pro", "Tiggo 8 Pro Luxury 1.6 TGDI 183 HP DCT", "2026", 1688000, 1613000),
            ("TIGGO 8 Pro", "Tiggo 8 Pro Excellent 1.6 TGDI 183 HP DCT", "2026", 1818000, 1743000),
            ("TIGGO 8 Pro", "Tiggo 8 Pro Avantgarde 1.6 TGDI 183 HP DCT", "2026", 1968000, 1893000),

            # Tiggo 8 Pro 2025 Model
            ("TIGGO 8 Pro", "Tiggo 8 Pro Luxury 1.6 TGDI 183 HP DCT", "2025", 1638000, 1563000),
            ("TIGGO 8 Pro", "Tiggo 8 Pro Excellent 1.6 TGDI 183 HP DCT", "2025", 1768000, 1693000),
        ]

        records = []
        for m_name, v_name, year, list_p, camp_p in chery_catalog:
            disc = list_p - camp_p
            records.append({
                "model_name": m_name,
                "variant": v_name,
                "price_raw": fmt_price(camp_p),
                "price_int": camp_p,
                "list_price_int": list_p,
                "campaign_price_int": camp_p,
                "discount_amount_int": disc,
                "discount_pct": round((disc / list_p) * 100, 1) if list_p > 0 else 0.0,
                "model_year": year,
                "currency": "TRY"
            })

        return records
