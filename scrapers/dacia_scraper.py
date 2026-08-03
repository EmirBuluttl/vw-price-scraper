"""
dacia_scraper.py  —  Dacia Türkiye fiyat scraper'ı (Çift Fiyat Altyapısı Destekli)
===================================================================================
Birincil : Tüm Dacia Model Sayfaları (Sandero, Sandero Stepway, Duster, Jogger, Spring)
Fallback : arabam.com.tr API
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get
from .arabam_api import fetch_arabam_api


class DaciaScraper(BaseScraper):
    brand = "Dacia"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("official_site_json", self._fetch_official_site),
            ("arabam_api_fallback", self._fetch_arabam_fallback),
        ]

    def _fetch_official_site(self) -> list[dict]:
        """Tüm Dacia modellerini ve hem Tavsiye Edilen Liste Fiyatı hem Kampanyalı Fiyatı çek."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
        records: list[dict] = []
        seen: set[tuple] = set()

        # Dacia resmi model sayfaları
        dacia_pages = [
            ("Yeni Sandero", "https://www.dacia.com.tr/modeller/yeni-sandero-bi1-ph2.html"),
            ("Yeni Sandero Stepway", "https://www.dacia.com.tr/modeller/yeni-sandero-stepway-bi1-ph2.html"),
            ("Yeni Duster", "https://www.dacia.com.tr/modeller/yeni-duster.html"),
            ("Yeni Jogger", "https://www.dacia.com.tr/modeller/yeni-jogger.html"),
            ("Fiyat Listesi", "https://www.dacia.com.tr/dacia-fiyat-listesi.html"),
        ]

        for default_name, url in dacia_pages:
            try:
                r = http_get(url, headers=headers)
                match = re.search(r'window\.APP_STATE\s*=\s*JSON\.parse\("(.*?)"\);', r.text, re.DOTALL)
                if not match:
                    continue
                data = json.loads(json.loads(f'"{match.group(1)}"'))

                def extract_trims(d):
                    if isinstance(d, dict):
                        pv = d.get("pricedVersion") or {}
                        v_label = pv.get("label") or pv.get("name") or d.get("versionName") or d.get("trimName")
                        
                        # Model Adı Ayrıştırma (Dacia Fiyat Listesi gibi jenerik başlıkları engelle)
                        m_name = default_name
                        if m_name == "Fiyat Listesi":
                            # Versiyon adından Duster, Sandero, Jogger ayıkla
                            v_lower = (v_label or "").lower()
                            if "duster" in v_lower: m_name = "Duster"
                            elif "stepway" in v_lower: m_name = "Sandero Stepway"
                            elif "sandero" in v_lower: m_name = "Sandero"
                            elif "jogger" in v_lower: m_name = "Jogger"
                            elif "spring" in v_lower: m_name = "Spring"
                            else: m_name = "Dacia"

                        raw_camp = d.get("price") or d.get("displayPrice") or (d.get("webDisplayPrices") or {}).get("displayPrice")
                        raw_list = d.get("listPrice") or d.get("recommendedPrice") or (d.get("webDisplayPrices") or {}).get("listPrice") or raw_camp

                        if v_label and raw_camp:
                            try:
                                camp_p = int(float(raw_camp))
                                list_p = int(float(raw_list)) if raw_list else camp_p
                                if list_p < camp_p: list_p = camp_p

                                if camp_p > 100_000:
                                    key = (m_name, v_label, camp_p)
                                    if key not in seen:
                                        seen.add(key)
                                        disc = max(0, list_p - camp_p)
                                        disc_pct = round((disc / list_p) * 100, 1) if list_p > 0 else 0
                                        records.append({
                                            "model_name": m_name,
                                            "variant": v_label,
                                            "price_raw": fmt_price(camp_p),
                                            "price_int": camp_p,
                                            "list_price_int": list_p,
                                            "campaign_price_int": camp_p,
                                            "discount_amount_int": disc,
                                            "discount_pct": disc_pct,
                                            "currency": "TRY"
                                        })
                            except Exception:
                                pass
                        for v in d.values():
                            extract_trims(v)
                    elif isinstance(d, list):
                        for item in d:
                            extract_trims(item)

                extract_trims(data)
            except Exception:
                pass

        return records

    def _fetch_arabam_fallback(self) -> list[dict]:
        return fetch_arabam_api("dacia")
