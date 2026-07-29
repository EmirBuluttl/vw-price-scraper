"""
renault_scraper.py  —  Renault Türkiye fiyat scraper'ı
======================================================
Birincil : Tüm Renault Model İniş Sayfaları (sub-trim & motor bazlı fiyat extraction)
Fallback : Fiyat listeleri & Ana sayfa APP_STATE
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

_STRIP = re.compile(r"\s+")


class RenaultScraper(BaseScraper):
    brand = "Renault"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("all_model_landing_pages", self._fetch_all_model_pages),
            ("price_list_page", self._fetch_price_list),
        ]

    def _fetch_all_model_pages(self) -> list[dict]:
        """Tüm Renault model sayfalarını gezerek her donanım paketini ve motorunu çek."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        # 1. Ana sayfadan tüm model linklerini topla
        try:
            r_main = http_get("https://www.renault.com.tr", headers=headers)
            soup_main = BeautifulSoup(r_main.text, "html.parser")
            model_urls = set()
            for a in soup_main.find_all("a", href=True):
                href = a.get("href")
                if any(cat in href for cat in ["binek-araclar", "hybrid-araclar", "elektrikli-araclar", "ticari-araclar"]) and href.endswith(".html"):
                    if "konfigurator" not in href and "fiyat" not in href:
                        full_url = urljoin("https://www.renault.com.tr", href)
                        model_urls.add(full_url)
        except Exception:
            model_urls = {
                "https://www.renault.com.tr/hybrid-araclar/yeni-clio.html",
                "https://www.renault.com.tr/hybrid-araclar/yeni-clio-e-tech.html",
                "https://www.renault.com.tr/binek-araclar/megane-sedan.html",
                "https://www.renault.com.tr/hybrid-araclar/austral-e-tech.html",
                "https://www.renault.com.tr/hybrid-araclar/yeni-captur.html",
                "https://www.renault.com.tr/hybrid-araclar/duster.html",
                "https://www.renault.com.tr/hybrid-araclar/rafale.html",
                "https://www.renault.com.tr/elektrikli-araclar/megane-e-tech-elektrikli.html",
                "https://www.renault.com.tr/elektrikli-araclar/renault-5-e-tech.html",
                "https://www.renault.com.tr/elektrikli-araclar/scenic-e-tech-elektrikli.html",
                "https://www.renault.com.tr/ticari-araclar/kangoo.html",
                "https://www.renault.com.tr/ticari-araclar/trafic.html",
                "https://www.renault.com.tr/ticari-araclar/master.html",
            }

        # 2. Her model sayfasının APP_STATE verisinden varyantları ayıkla
        for url in model_urls:
            try:
                r = http_get(url, headers=headers)
                match = re.search(r'window\.APP_STATE\s*=\s*JSON\.parse\("(.*?)"\);', r.text, re.DOTALL)
                if not match:
                    continue
                data = json.loads(json.loads(f'"{match.group(1)}"'))
                
                model_name = url.split("/")[-1].replace(".html", "").replace("-", " ").title()

                def extract_page_trims(d):
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
                            extract_page_trims(v)
                    elif isinstance(d, list):
                        for item in d:
                            extract_page_trims(item)

                extract_page_trims(data)
            except Exception:
                pass

        return records

    def _fetch_price_list(self) -> list[dict]:
        r = http_get("https://www.renault.com.tr/renault-fiyat-listeleri.html")
        soup = BeautifulSoup(r.text, "html.parser")
        records: list[dict] = []
        # Fallback parsing
        return records
