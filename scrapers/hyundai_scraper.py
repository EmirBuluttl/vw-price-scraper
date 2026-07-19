"""
hyundai_scraper.py  —  Hyundai Türkiye fiyat scraper'ı
=======================================================
Birincil : Hyundai resmi satış fiyat listesindeki (/satis/fiyat-listesi.html)
           modelId'leri çıkararak, Hyundai Europe'un resmi GraphQL API'sine 
           (/eu/papi) istek atmak.
Fallback : HTML scraping veya eski statik fiyat tespiti
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, http_post, parse_price_str

log = logging.getLogger(__name__)

LIST_URL = "https://www.hyundai.com/tr/tr/satis/fiyat-listesi.html"
GRAPHQL_URL = "https://org-eu-www.hyundai.com/eu/papi"

GRAPHQL_QUERY = """
query HppPriceListTR($service: TrimmedString!, $country: TrimmedString!, $modelId: TrimmedString!) {
  hppPriceListTR(service: $service, country: $country, modelId: $modelId) {
    plant
    productYear
    modelDescription
    powertrainNm
    trimNm
    fuelTypeNm
    transmissionType
    maxPrice
    maxcampaignPrice
  }
}
"""


def _extract_model_ids(html: str) -> list[str]:
    """HTML içindeki ModelPriceTable verilerinden modelId'lerini bul."""
    model_ids = []
    # 1. Strateji: json script etiketleri
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", class_="rc-ModelPriceTable__data")
    for s in scripts:
        content = (s.string or "").strip()
        if content:
            try:
                data = json.loads(content)
                m_id = data.get("modelId")
                if m_id and m_id not in model_ids:
                    model_ids.append(m_id)
            except Exception:
                pass

    # 2. Strateji: Regex ile arama
    matches = re.findall(r'"modelId"\s*:\s*"([^"]+)"', html)
    for m_id in matches:
        if m_id not in model_ids:
            model_ids.append(m_id)

    return model_ids


class HyundaiScraper(BaseScraper):
    brand = "Hyundai"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("graphql_api", self._fetch_graphql),
        ]

    def _fetch_graphql(self) -> list[dict]:
        # Fiyat listesi ana sayfasını çekerek güncel modelId'leri tespit et
        r = http_get(LIST_URL)
        model_ids = _extract_model_ids(r.text)
        
        if not model_ids:
            # Fallback: bilinen temel modelId listesi
            model_ids = [
                'SW|S6||', 'G4|S6||', 'SW|W5||', '1E|W5||', 'GT|W5||', 
                '6X|S5||', '7F|W5||', 'GI|W5||', '9I|W5||', 'AL|*||', 
                'GO|*||', 'JF|W5|EV1|', 'HK|*|EV1|', '7R|B9|*|'
            ]

        records: list[dict] = []
        seen: set[tuple] = set()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": LIST_URL
        }

        for m_id in model_ids:
            payload = {
                "query": GRAPHQL_QUERY,
                "variables": {
                    "service": "S03",
                    "country": "tr",
                    "modelId": m_id
                }
            }
            try:
                res = http_post(GRAPHQL_URL, headers=headers, json=payload)
                data = res.json()
                items = data.get("data", {}).get("hppPriceListTR", []) or []
                
                for item in items:
                    model_desc = item.get("modelDescription") or ""
                    powertrain = item.get("powertrainNm") or ""
                    trim = item.get("trimNm") or ""
                    fuel = item.get("fuelTypeNm") or ""
                    trans = item.get("transmissionType") or ""
                    year = item.get("productYear") or ""

                    # Kampanyalı fiyat varsa onu al, yoksa liste fiyatını al
                    price_val = item.get("maxcampaignPrice") or item.get("maxPrice")
                    if not price_val:
                        continue
                    
                    try:
                        price_int = int(float(str(price_val).replace(",", "").replace(".", "").strip()))
                    except (ValueError, TypeError):
                        continue

                    if price_int < 100_000:
                        continue

                    variant = f"{powertrain} {trim} {fuel} {trans} ({year})".strip()
                    key = (model_desc, variant)
                    if key not in seen:
                        seen.add(key)
                        records.append({
                            "model_name": model_desc,
                            "variant": variant,
                            "price_raw": fmt_price(price_int),
                            "price_int": price_int,
                            "currency": "TRY"
                        })
            except Exception as exc:
                log.warning("Hyundai GraphQL query failed for modelId %s: %s", m_id, exc)

        return records
