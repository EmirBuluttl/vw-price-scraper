"""
renault_scraper.py  —  Renault Türkiye fiyat scraper'ı
======================================================
Birincil : Tüm Renault Model İniş Sayfaları (tavsiye edilen kampanya fiyatı extraction)
Fallback : Ana sayfa APP_STATE
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get


class RenaultScraper(BaseScraper):
    brand = "Renault"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("all_model_landing_pages", self._fetch_all_model_pages),
        ]

    def _fetch_all_model_pages(self) -> list[dict]:
        """Tüm Renault model sayfalarını gezerek her donanım paketinin tavsiye edilen kampanya fiyatını çek."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
        records: list[dict] = []
        seen: set[tuple] = set()
        model_urls = set()

        # Ana sayfadan tüm aktif model linklerini dinamik olarak topla (Kategori indeks sayfalarını değil, sadece tekil model sayfalarını al)
        try:
            r_main = http_get("https://www.renault.com.tr", headers=headers)
            soup_main = BeautifulSoup(r_main.text, "html.parser")
            for a in soup_main.find_all("a", href=True):
                href = a.get("href")
                if any(cat in href for cat in ["/binek-araclar/", "/hybrid-araclar/", "/elektrikli-araclar/", "/ticari-araclar/"]) and href.endswith(".html"):
                    if "konfigurator" not in href and "fiyat" not in href:
                        full_url = urljoin("https://www.renault.com.tr", href)
                        model_urls.add(full_url)
        except Exception:
            pass

        if not model_urls:
            model_urls = {
                "https://www.renault.com.tr/hybrid-araclar/yeni-clio.html",
                "https://www.renault.com.tr/binek-araclar/megane-sedan.html",
                "https://www.renault.com.tr/elektrikli-araclar/megane-e-tech-elektrikli.html",
                "https://www.renault.com.tr/elektrikli-araclar/scenic-e-tech-elektrikli.html",
                "https://www.renault.com.tr/hybrid-araclar/rafale.html",
            }

        for url in sorted(model_urls):
            try:
                r = http_get(url, headers=headers)
                match = re.search(r'window\.APP_STATE\s*=\s*JSON\.parse\("(.*?)"\);', r.text, re.DOTALL)
                if not match:
                    continue
                data = json.loads(json.loads(f'"{match.group(1)}"'))
                model_name = url.split("/")[-1].replace(".html", "").replace("-", " ").title()

                # Model parametrelerinden donanımlar (grades) & versiyonlar
                model_params = data.get("page", {}).get("data", {}).get("modelParams", {}).get("data", {})
                grades = model_params.get("grades", [])

                if grades:
                    for g in grades:
                        pv = g.get("pricedVersion") or {}
                        v_label = pv.get("label") or g.get("label") or g.get("code")

                        # Öncelikle tavsiye edilen kampanya fiyatını (priceWoOptionsWoVAT / price / minPrice) al!
                        fin = g.get("finance") or {}
                        p_val = fin.get("priceWoOptionsWoVAT") or fin.get("priceWoOptions") or fin.get("price") or g.get("minPrice")
                        
                        if not p_val:
                            p_val = (g.get("webDisplayPrices") or {}).get("displayPrice")

                        if v_label and p_val:
                            try:
                                p_int = int(float(str(p_val)))
                                if 100_000 < p_int < 10_000_000:
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
                else:
                    def extract_fallback(d):
                        if isinstance(d, dict):
                            pv = d.get("pricedVersion") or {}
                            v_label = pv.get("label") or pv.get("name") or d.get("versionName") or d.get("trimName")
                            fin = d.get("finance") or {}
                            p_val = fin.get("priceWoOptionsWoVAT") or fin.get("priceWoOptions") or fin.get("price") or d.get("minPrice") or (d.get("webDisplayPrices") or {}).get("displayPrice")
                            if v_label and p_val:
                                try:
                                    p_int = int(float(str(p_val)))
                                    if 100_000 < p_int < 10_000_000:
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
                                extract_fallback(v)
                        elif isinstance(d, list):
                            for item in d:
                                extract_fallback(item)

                    extract_fallback(data)
            except Exception:
                pass

        return records
