"""
chery_scraper.py  —  Chery Türkiye fiyat scraper'ı
===================================================
Birincil : chery.com.tr/sifir-arac-fiyatlari/ (Divi Table Maker + Image parsing)
Fallback A: arabam.com.tr API (Chery sıfır araç listesi)
Fallback B: arabam.com.tr HTML sayfası
Fallback C: Ana sayfa genel tarama
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str
from .arabam_api import fetch_arabam_api, fetch_arabam_html

PRICE_RE = re.compile(r"₺\s*([\d.,]+)")
TL_RE = re.compile(r"([\d]{3}[\d.,\s]+)\s*TL", re.IGNORECASE)


def _parse_divi_table_with_images(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []
    seen: set[tuple] = set()

    # Divi satırlarını (et_pb_row) bul
    rows = soup.find_all("div", class_=re.compile(r"et_pb_row"))

    for row in rows:
        # Görsel isminden modeli tespit et
        model_name = ""
        img = row.find("img")
        if img:
            src = (img.get("src") or img.get("data-src") or "").lower()
            if "tiggo8" in src:
                model_name = "TIGGO 8 Pro"
            elif "tiggo7-comfort" in src:
                model_name = "TIGGO 7 Pro Comfort"
            elif "tiggo7" in src:
                model_name = "TIGGO 7 Pro"
            elif "omoda5" in src:
                model_name = "OMODA 5"
            elif "omoda" in src:
                model_name = "OMODA 5"
        
        # Görselden bulunamadıysa başlığa bak
        if not model_name:
            prev = row.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
            if prev:
                heading = prev.get_text(strip=True)
                if "tiggo" in heading.lower():
                    model_name = "Tiggo"
                elif "omoda" in heading.lower():
                    model_name = "Omoda"
                else:
                    model_name = heading
        
        if not model_name:
            model_name = "Chery"

        # Tablodaki hücreleri bul
        cells = row.find_all("div", class_=re.compile(r"dvmd_tm_tcell"))
        if not cells:
            continue

        # Hücreleri satır bazlı grupla
        row_cells = {}
        for c in cells:
            classes = c.get("class", [])
            row_class = [cl for cl in classes if "dvmd_tm_row_" in cl]
            if row_class:
                row_idx = row_class[0].split("_")[-1]
                if row_idx not in row_cells:
                    row_cells[row_idx] = []
                row_cells[row_idx].append(c.get_text(strip=True))

        for r_idx, txts in sorted(row_cells.items(), key=lambda x: int(x[0])):
            if len(txts) < 3:
                continue
            
            # Başlık satırını atla
            if "Model Yılı" in txts[0] or "Donanım" in txts[1]:
                continue
                
            year = txts[0]
            variant = txts[1]
            price_str = txts[2]

            price_int = parse_price_str(price_str)
            if not price_int:
                continue

            variant_full = f"{variant} ({year})".strip()
            key = (model_name, variant_full)
            if key not in seen:
                seen.add(key)
                records.append({
                    "model_name": model_name,
                    "variant": variant_full,
                    "price_raw": fmt_price(price_int),
                    "price_int": price_int,
                    "currency": "TRY"
                })

    return records


class CheryScraper(BaseScraper):
    brand = "Chery"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("price_list_page", self._fetch_price_list),
            ("arabam_api", self._fetch_arabam),
            ("arabam_html", self._fetch_arabam_html),
        ]

    def _fetch_price_list(self) -> list[dict]:
        r = http_get("https://www.chery.com.tr/sifir-arac-fiyatlari/")
        return _parse_divi_table_with_images(r.text)

    def _fetch_arabam(self) -> list[dict]:
        return fetch_arabam_api("chery")

    def _fetch_arabam_html(self) -> list[dict]:
        return fetch_arabam_html("chery")
