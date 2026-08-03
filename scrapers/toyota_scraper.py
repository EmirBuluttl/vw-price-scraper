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

            # Hem Liste Fiyatını (MSRP) hem Kampanyalı Fiyatı oku
            list_p_int = None
            for l_key in ["ListeFiyati2", "ListeFiyati1"]:
                l_node = p.find(l_key)
                if l_node is not None and l_node.text:
                    parsed_l = parse_price_str(l_node.text)
                    if parsed_l and parsed_l >= 100_000:
                        list_p_int = parsed_l
                        break

            camp_p_int = None
            for c_key in ["KampanyaliFiyati2", "OTVTesvikli1", "KampanyaliFiyati1"]:
                c_node = p.find(c_key)
                if c_node is not None and c_node.text:
                    parsed_c = parse_price_str(c_node.text)
                    if parsed_c and parsed_c >= 100_000:
                        camp_p_int = parsed_c
                        break

            # Kampanyalı fiyat yoksa liste fiyatını al, liste fiyatı yoksa kampanyalıyı al
            final_campaign_price = camp_p_int if camp_p_int else list_p_int
            final_list_price = list_p_int if list_p_int else final_campaign_price

            if not final_campaign_price:
                continue

            discount_amount = (final_list_price - final_campaign_price) if final_list_price > final_campaign_price else 0

            # "ÖTV'li versiyonlarda" gibi ek vergi/aksesuar satırlarını atla
            if "ÖTV" in p_desc or "versiyon" in p_desc.lower() or "fark" in p_desc.lower():
                if final_campaign_price < 100_000:
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
                    "price_raw": fmt_price(final_campaign_price),
                    "price_int": final_campaign_price,
                    "list_price_int": final_list_price,
                    "campaign_price_int": final_campaign_price,
                    "discount_amount_int": discount_amount,
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
