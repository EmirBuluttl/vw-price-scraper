# 🚗 Volkswagen Türkiye - Fiyat Takip Otomasyonu (Scraper)

Bu proje, Volkswagen Türkiye'nin resmi distribütörü Doğuş Oto'nun iç API Gateway altyapısını kullanarak, sıfır araç stoklarını ve donanım bazlı güncel fiyat listelerini otomatik olarak çeken, bir SQLite veritabanında saklayan ve Windows Görev Zamanlayıcı (Task Scheduler) ile günlük olarak kendini güncelleyen bir otomasyon sistemidir.

---

## ✨ Özellikler

* **Kurumsal Kısıtlamalardan Muaf:** Playwright veya Selenium gibi harici tarayıcı sürücüleri (driver) gerektirmez. Bu sayede kurumsal bilgisayarlardaki strict **Group Policy (AppLocker)** engellerine takılmaz.
* **Akıllı Bypass:** Doğrudan Doğuş API Gateway'e POST istekleri göndererek **Cloudflare bot korumasını** ve JavaScript rendering süreçlerini bypass eder.
* **Donanım Seviyesi Detayı:** Sadece model bazlı değil; motor tipi, beygir gücü ve donanım paketi (Life, Style, R-Line, Elegance) bazında net fiyatları çeker.
* **Veritabanı Entegrasyonu:** Çekilen verileri SQLite (`vw_prices.db`) üzerinde tarihsel olarak saklar.
* **Otomatik Çalışma:** Windows Task Scheduler entegrasyonu sayesinde her gün belirlenen saatte arka planda sessizce çalışır.
* **Geçmiş Analizi:** `view_data.py` aracı ile fiyat değişimlerini (artış/düşüş oranlarını) geçmişe dönük analiz eder.

---

## 🏗️ Sistem Mimarisi

```
[Dogus Oto API Gateway] 
        │
        ▼ (requests.post - JSON Payload)
   [scraper.py] 
        │
        ▼ (Varyant Tekilleştirme & Temizleme)
   [SQLite DB (vw_prices.db)] ◄──── [view_data.py] (Raporlama ve Analiz)
```

---

## 🛠️ Kurulum ve Gereksinimler

Projenin çalışabilmesi için bilgisayarınızda **Python 3.x** kurulu olmalıdır.

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/KULLANICI_ADINIZ/vw-price-scraper.git
cd vw-price-scraper
```

### 2. Gerekli Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
```

---

## 🚀 Kullanım Kılavuzu

### 1. Scraper'ı Manuel Çalıştırma
Veritabanını el ile hemen güncellemek için:
```bash
python -X utf8 scraper.py
```

### 2. Kaydedilen Fiyatları Görüntüleme
Bugün çekilen en güncel fiyatları tablo halinde listelemek için:
```bash
python -X utf8 view_data.py
```

### 3. Tüm Tarihsel Verileri Listeleme
```bash
python -X utf8 view_data.py --all
```

### 4. Tarihsel Fiyat Değişim Analizi
Hangi modelin fiyatının ne zaman arttığını veya azaldığını görmek için:
```bash
python -X utf8 view_data.py --history
```

### 5. Çalışma Loglarını İnceleme
```bash
python -X utf8 view_data.py --logs
```

---

## 🕒 Otomatik Günlük Çalıştırma Ayarı

Projenin her gün otomatik olarak arka planda çalışıp fiyatları veritabanına işlemesini sağlamak için Windows Görev Zamanlayıcı'yı kullanabilirsiniz.

1. PowerShell'i **Yönetici Olarak (Run as Administrator)** açın.
2. Klasör içindeki kurulum scriptini çalıştırın:
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\setup_task_scheduler.ps1
   ```

*Bu işlem her sabah saat **09:00'da** `run_scraper.bat` dosyasını tetikleyerek veritabanını güncelleyecektir.*

---

## 🗄️ Veritabanı Şeması

### `models` Tablosu
| Alan Adı | Veri Tipi | Açıklama |
|:---|:---|:---|
| `id` | INTEGER | Birincil Anahtar (Auto Increment) |
| `model_name` | TEXT | Araç Modeli (Örn: Golf, Taigo) |
| `variant` | TEXT | Donanım ve Motor Detayı (Örn: 1.5 eTSI 150 PS Style DSG) |
| `price_raw` | TEXT | Formatlanmış Fiyat Metni (Örn: 2.828.999 TL) |
| `price_int` | INTEGER | Matematiksel Karşılaştırma İçin Tamsayı Fiyat |
| `currency` | TEXT | Para Birimi (Varsayılan: TRY) |
| `scraped_at` | TEXT | Detaylı Zaman Damgası |
| `scraped_date`| TEXT | Günlük Tekilleştirme İçin Tarih (YYYY-MM-DD) |

---

## 📝 Lisans

Bu proje kişisel araştırma ve eğitim amacıyla geliştirilmiştir. Verilerin ticari amaçla kullanımı Doğuş Otomotiv lisans koşullarına tabidir.
