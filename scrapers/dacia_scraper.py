"""
dacia_scraper.py  —  Dacia Türkiye fiyat scraper'ı
===================================================
Birincil : Tüm Dacia Model İniş Sayfaları (sub-trim & motor bazlı fiyat extraction)
Fallback : Fiyat listesi & Ana sayfa kartları
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get


class DaciaScraper(BaseScraper):
    brand = "Dacia"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("all_model_landing_pages", self._fetch_all_model_pages),
            ("homepage_cards", self._fetch_homepage_cards),
        ]

    def _fetch_all_model_pages(self) -> list[dict]:
        """Tüm Dacia model sayfalarını gezerek her donanım paketini ve motorunu çek."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        dacia_pages = [
            "https://www.dacia.com.tr/dacia-fiyat-listesi.html",
            "https://www.dacia.com.tr/modeller/yeni-jogger.html",
            "https://www.dacia.com.tr/modeller/yeni-sandero-bi1-ph2.html",
            "https://www.dacia.com.tr/modeller/yeni-sandero-stepway-bi1-ph2.html",
        ]

        for url in dacia_pages:
            try:
                r = http_get(url, headers=headers)
                match = re.search(r'window\.APP_STATE\s*=\s*JSON\.parse\("(.*?)"\);', r.text, re.DOTALL)
                if not match:
                    continue
                data = json.loads(json.loads(f'"{match.group(1)}"'))
                model_name = url.split("/")[-1].replace(".html", "").replace("-bi1-ph2", "").replace("-", " ").title()

                def extract_dacia_trims(d):
                    if isinstance(d, dict):
                        pv = d.get("pricedVersion") or {}
                        v_label = pv.get("label") or pv.get("name") or d.get("versionName") or d.get("trimName")
                        price_val = d.get("price") or d.get("displayPrice") or (d.get("webDisplayPrices") or {}).get("displayPrice")
                        
                        if v_label and price_val:
                            try:
                                p_int = int(float(price_val))
                                if p_int > 100_000:
                                    key = (model_name, v_label, p_int)
                                    if key not in seen:
                                        seen.add(key)
                                        records.append({
                                            "model_name": model_name,
                                            "variant": v_label,
                                            "price_raw": fmt_price(p_int),
                                            "price_int": p_int,
                                            "currency": "TRY"
                                        })
                            except Exception:
                                pass
                        for v in d.values():
                            extract_dacia_trims(v)
                    elif isinstance(d, list):
                        for item in d:
                            extract_dacia_trims(item)

                extract_dacia_trims(data)
            except Exception:
                pass

        return records

    def _fetch_homepage_cards(self) -> list[dict]:
        r = http_get("https://www.dacia.com.tr")
        soup = BeautifulSoup(r.text, "html.parser")
        records: list[dict] = []
        return records
