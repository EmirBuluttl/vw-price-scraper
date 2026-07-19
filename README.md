# 🚗 Çoklu Marka Araç Fiyat Takip Otomasyonu (Multi-Brand Scraper)

Bu proje; Türkiye'de en çok tercih edilen 8 otomobil markasının (**Volkswagen, Skoda, Renault, Ford, Hyundai, Toyota, Chery, Dacia**) sıfır araç donanım ve fiyat listelerini otomatik olarak çeken, bir SQLite veritabanında saklayan, günlük değişimleri raporlayan ve Windows Görev Zamanlayıcı (Task Scheduler) ile her sabah otomatik çalışan bir veri takip sistemidir.

---

## ✨ Özellikler

* **Kurumsal Engellere Takılmaz:** Playwright veya Selenium gibi harici tarayıcı sürücüleri (driver) gerektirmez. Windows terminalinde hafif HTTP kütüphaneleriyle çalışır.
* **Gelişmiş API Entegrasyonları ve Akıllı Bypass:**
  * **Hyundai**: Resmi sayfadaki dinamik model ID'lerini saptayıp resmi Avrupa GraphQL API'sini sorgular.
  * **Toyota**: Toyota Türkiye'nin arka planda beslendiği XML fiyat tablosunu parse eder.
  * **Ford**: Binek, ticari ve FordStore araç fiyat listesi API endpoint'ini doğrudan sorgular.
  * **Chery**: WordPress Divi Table yapısını çözümler ve model görsellerinin isimlerinden model eşleştirmesi yapar.
  * **Skoda**: Next.js `__NEXT_DATA__` JSON yapısını doğrudan sunucu yanıtından ayıklayıp modelleri çeker.
  * **Renault & Dacia**: SSR (Sunucu Tarafından Render Edilmiş) HTML kartlarındaki başlangıç fiyatlarını dinamik okur.
* **Bulunamadı / Boş Sonuç Kabul Etmez:** Her scraper için çok katmanlı fallback (yedek) mekanizmaları mevcuttur. Resmi site çökerse veya bot engeli koyarsa sırasıyla:
  1. Birincil Resmi Kaynak (API / XML Feed / HTML)
  2. Arabam.com API sorgusu
  3. Arabam.com HTML sayfa taraması
  4. Veritabanındaki en son başarılı günün verisi (**stale data**) devreye girer. Bu sayede her sabah mutlaka kesintisiz sonuç üretilir.
* **Windows Konsol Dostu:** CP1254 Türkçe karakter setini kullanan Windows PowerShell ve CMD terminallerinde unicode çökmelerini önlemek için çıktılar ASCII güvenli hale getirilmiştir.

---

## 🏗️ Proje Yapısı

```
vw-price-scraper/
│
├── scrapers/                   # Marka bazlı scraper modülleri
│   ├── __init__.py
│   ├── base_scraper.py         # Ortak arayüz, HTTP sarmalayıcı ve SQLite kayıt mantığı
│   ├── arabam_api.py           # arabam.com API ve HTML fallback yardımcı sınıfı
│   ├── vw_scraper.py           # Doğuş API Gateway
│   ├── skoda_scraper.py        # skoda.com.tr Next.js JSON parser
│   ├── renault_scraper.py      # Renault SSR HTML parser
│   ├── ford_scraper.py         # Ford Web API JSON client
│   ├── hyundai_scraper.py      # Hyundai Resmi GraphQL API client
│   ├── toyota_scraper.py       # Toyota Resmi XML price feed parser
│   ├── chery_scraper.py        # Chery Divi Table Maker parser
│   └── dacia_scraper.py        # Dacia SSR HTML parser
│
├── multi_scraper.py            # Ana orkestrasyon ve günlük tetikleyici script
├── view_multi_data.py          # Terminal veritabanı sorgulayıcı ve analiz programı
├── run_multi_scraper.bat       # Task Scheduler'ın çalıştırdığı toplu iş dosyası
├── setup_multi_task.ps1        # Görev zamanlayıcıyı kuran PowerShell betiği
└── requirements.txt            # Python bağımlılık listesi
```

---

## 🛠️ Kurulum ve Gereksinimler

Bilgisayarınızda **Python 3.10 veya daha yeni bir sürüm** kurulu olmalıdır.

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/EmirBuluttl/vw-price-scraper.git
cd vw-price-scraper
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktif Edin
```powershell
python -m venv .venv
# Windows PowerShell için aktifleştirme:
.venv\Scripts\activate
```

### 3. Gerekli Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
```

---

## 🚀 Kullanım Kılavuzu

### 1. Scraper'ları Manuel Çalıştırma

* **Tüm Markaları Taramak İçin:**
  ```bash
  python multi_scraper.py
  ```
* **Sadece Belirli Markaları Taramak İçin:**
  ```bash
  python multi_scraper.py --brand toyota chery
  ```

### 2. Kaydedilen Verileri Görüntüleme

Toplanan verileri terminalden incelemek için [view_multi_data.py](view_multi_data.py) scriptini kullanabilirsiniz:

* **Bugünün Fiyat Listesini Listeleme:**
  ```bash
  python view_multi_data.py --today
  ```
* **Genel Marka Özet Tablosu (En son ne zaman çekildi, kaç adet aktif veri var):**
  ```bash
  python view_multi_data.py --summary
  ```
* **Belirli Bir Markayı Filtreleme:**
  ```bash
  python view_multi_data.py --brand ford
  ```
* **Tarihsel Fiyat Değişim Analizi (Artış/Azalış Miktarları):**
  ```bash
  python view_multi_data.py --history
  ```
* **Son Çalıştırma Logları:**
  ```bash
  python view_multi_data.py --logs
  ```

---

## 🕒 Otomatik Günlük Çalıştırma Ayarı (Windows Task Scheduler)

Sistemin her sabah saat **09:00'da** bilgisayarınız açıldığında arka planda otomatik çalışması için:

1. **PowerShell'i Yönetici Olarak Başlatın**.
2. Proje dizinine giderek aşağıdaki komutla zamanlayıcı betiğini çalıştırın:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\setup_multi_task.ps1
   ```

*Bu işlem her sabah arka planda `run_multi_scraper.bat` dosyasını tetikler, verileri çeker ve veritabanını sessizce günceller.*

---

## 🗄️ Veritabanı Şeması (`car_prices.db`)

Sistemde toplanan tüm fiyatlar `prices` tablosunda saklanır:

| Kolon Adı | Veri Tipi | Açıklama |
|:---|:---|:---|
| `brand` | TEXT | Araç Markası (Örn: Toyota, Hyundai, Ford) |
| `model_name` | TEXT | Araç Modeli (Örn: Corolla, Tucson, Focus) |
| `variant` | TEXT | Donanım ve Motor Detayı (Örn: COROLLA 1.5 Dream Multidrive S) |
| `price_raw` | TEXT | Formatlanmış Liste Fiyatı (Örn: 2.040.000 TL) |
| `price_int` | INTEGER | Matematiksel Karşılaştırma İçin Tamsayı Fiyat (Örn: 2040000) |
| `currency` | TEXT | Para Birimi (Örn: TRY) |
| `source` | TEXT | Fiyatın Çekildiği Kaynak Metodu (Örn: xml_feed, graphql_api) |
| `is_stale` | INTEGER | 1 ise veri fallback olarak eski tarihten kurtarılmıştır, 0 ise tazedir |
| `scraped_at` | TEXT | Detaylı Zaman Damgası (ISO Format) |
| `scraped_date`| TEXT | Günlük Tekilleştirme İçin Tarih (YYYY-MM-DD) |

---

## 📝 Lisans

Bu proje kişisel araştırma ve eğitim amacıyla geliştirilmiştir. Verilerin ticari amaçla kullanımı ilgili dağıtıcıların lisans ve kullanım koşullarına tabidir.
