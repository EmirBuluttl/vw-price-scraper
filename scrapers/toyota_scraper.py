"""
toyota_scraper.py  —  Toyota Türkiye fiyat scraper'ı
===================================================
Birincil : Toyota XML fiyat listesi (turkiye.toyota.com.tr/middle/fiyat-listesi/fiyat_v3.xml)
Fallback : arabam.com.tr HTML ve diğer statik sayfalar
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

from .base_scraper import BaseScraper, fmt_price, http_get, parse_price_str

log = logging.getLogger(__name__)

XML_URL = "https://turkiye.toyota.com.tr/middle/fiyat-listesi/fiyat_v3.xml"


def _parse_toyota_xml(xml_text: str) -> list[dict]:
    # UTF-8 BOM temizliği ve XML başlangıcını bulma
    content_str = xml_text.strip()
    xml_start = content_str.find("<?xml")
    if xml_start != -1:
        content_str = content_str[xml_start:]

    try:
        root = ET.fromstring(content_str)
    except Exception as e:
        log.warning("Toyota XML parsing failed: %s", e)
        return []

    records: list[dict] = []
    seen: set[tuple] = set()

    for m in root.findall("Model"):
        # Model aktif değilse atla
        if m.get("Aktifmi") == "0":
            continue

        model_name = m.get("name") or ""
        # Temel model adlarını temizle
        model_name = model_name.replace("Yeni", "").strip()

        prices = m.findall("ModelFiyat")
        for p in prices:
            p_desc = p.find("Model").text if p.find("Model") is not None else ""
            govde = p.find("Govde").text if p.find("Govde") is not None else ""

            # Değişik fiyat sütunlarını öncelik sırasına göre kontrol et
            price_keys = [
                "KampanyaliFiyati2",
                "OTVTesvikli1",
                "KampanyaliFiyati1",
                "ListeFiyati2",
                "ListeFiyati1",
                "OTVMuafiyetli"
            ]

            price_int = None
            price_raw_selected = ""

            for key in price_keys:
                node = p.find(key)
                if node is not None and node.text:
                    parsed = parse_price_str(node.text)
                    if parsed and parsed >= 100_000:
                        price_int = parsed
                        price_raw_selected = node.text.strip()
                        break

            if not price_int:
                continue

            # "ÖTV'li versiyonlarda" gibi ek vergi/aksesuar satırlarını atla
            if "ÖTV" in p_desc or "versiyon" in p_desc.lower() or "fark" in p_desc.lower():
                if price_int < 100_000:
                    continue

            # Variant ismini oluştur
            variant = f"{govde} {p_desc}".strip()
            # UTF-8 decode bozukluklarını düzelt (örnek: YENÄ° -> YENİ)
            variant = variant.replace("YENÄ°", "YENİ").replace("Ã–", "Ö").replace("Ã§", "ç").replace("ÅŸ", "ş")
            model_name_clean = model_name.replace("YENÄ°", "YENİ").replace("Ã–", "Ö").replace("Ã§", "ç")

            key = (model_name_clean, variant)
            if key not in seen:
                seen.add(key)
                records.append({
                    "model_name": model_name_clean,
                    "variant": variant,
                    "price_raw": fmt_price(price_int),
                    "price_int": price_int,
                    "currency": "TRY"
                })

    return records


class ToyotaScraper(BaseScraper):
    brand = "Toyota"

    @property
    def methods(self) -> list[tuple[str, Any]]:
        return [
            ("xml_feed", self._fetch_xml_feed),
        ]

    def _fetch_xml_feed(self) -> list[dict]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Referer": "https://turkiye.toyota.com.tr/middle/fiyat-listesi/"
        }
        r = http_get(XML_URL, headers=headers)
        return _parse_toyota_xml(r.text)
