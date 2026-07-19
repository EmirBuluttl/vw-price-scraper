"""
skoda_scraper.py  —  Škoda Türkiye fiyat scraper'ı
===================================================
Birincil : skoda.com.tr/fiyat-listesi Next.js __NEXT_DATA__ JSON parse
Fallback : HTML scraping
"""

from __future__ import annotations

import json
import logging
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

log = logging.getLogger(__name__)


def _parse_skoda_next_data(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    next_data_script = soup.find("script", id="__NEXT_DATA__")
    if not next_data_script:
        return []

    try:
        js_data = json.loads(next_data_script.string)
    except Exception as e:
        log.warning("Skoda NEXT_DATA JSON parse failed: %s", e)
        return []

    props = js_data.get("props", {})
    page_props = props.get("pageProps", {})
    init_data = page_props.get("initialData2026", {})
    price_list_data = init_data.get("priceListData", {})
    sections = price_list_data.get("priceListSections", [])

    records: list[dict] = []
    seen: set[tuple] = set()

    for sec in sections:
        items = sec.get("items", [])
        for item in items:
            model_name = item.get("title") or ""
            table = item.get("modelPricesTable", {})
            rows_data = table.get("data", [])
            for rd in rows_data:
                hardware = rd.get("hardware", {}).get("value") or ""
                # Get price: discountPrice if available, else currentPrice
                disc_val = rd.get("discountPrice", {}).get("value") or ""
                curr_val = rd.get("currentPrice", {}).get("value") or ""

                price_str = disc_val if disc_val.strip() else curr_val
                if not price_str:
                    continue

                price_int = parse_price_str(price_str)
                if not price_int:
                    continue

                variant = hardware.strip()
                key = (model_name, variant)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "model_name": model_name,
                        "variant": variant,
                        "price_raw": fmt_price(price_int),
                        "price_int": price_int,
                        "currency": "TRY"
                    })
    return records


class SkodaScraper(BaseScraper):
    brand = "Skoda"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("next_data_json", self._fetch_next_data),
        ]

    def _fetch_next_data(self) -> list[dict]:
        r = http_get("https://www.skoda.com.tr/fiyat-listesi")
        return _parse_skoda_next_data(r.text)
