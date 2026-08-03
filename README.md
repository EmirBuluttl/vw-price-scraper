# 🚗 Kurumsal Çoklu Marka Araç Fiyat Takip & Analiz Portalı (Multi-Brand Scraper)

Bu proje; Türkiye otomotiv pazarında yer alan **17 aktif otomobil markasının** (**Volkswagen, Skoda, Renault, Ford, Hyundai, Toyota, Chery, Dacia, Kia, Fiat, Peugeot, Opel, Citroën, Jeep, Alfa Romeo, DS Automobiles, Maserati**) sıfır kilometre araç donanım ve fiyat listelerini otomatik olarak çeken, ilişkisel SQLite veritabanında saklayan, zaman çizelgeli fiyat değişim analizi sunan ve **Gelişmiş Web Paneli (Flask + Glassmorphism UI)** üzerinden yönetilen kurumsal bir fiyat takip platformudur.

---

## ✨ Öne Çıkan Özellikler

- **🎛️ 3-Grup Sekme Mimarisi (Gelişmiş Filtreleme)**:
  - **`🌐 Tüm Markalar`**: 17 markanın tamamını listeler.
  - **`🏢 Tofaş Grubu`**: Sadece Tofaş/Stellantis markalarını (*Fiat, Peugeot, Opel, Citroën, Jeep, Alfa Romeo, DS, Maserati*) listeler.
  - **`🚗 Bağımsız Markalar`**: Sadece Tofaş dışı bağımsız markaları (*VW, Skoda, Renault, Ford, Hyundai, Toyota, Kia, Chery, Dacia*) listeler.
  - **Model Menüsü İzolasyonu**: Marka butonuna doğrudan basılmadığı sürece model menüsü kesinlikle açılmaz, ekranı kalabalıklaştırmaz.

- **📊 Tarihsel Fiyat Analizi & İnteraktif Trend Grafiği (Chart.js)**:
  - Seçilen iki tarih arasındaki net TL ve % değişim farkı, dönem içi min/max fiyatlar dinamik hesaplanır.
  - **Chart.js Çizgi Grafiği** ile zam dönemleri (Yeşil) ve indirim dönemleri (Kırmızı) görselleştirilir.

- **📗 Biçimlendirilmiş Renkli Excel (.xlsx) İhracatı**:
  - OpenPyXL entegrasyonu ile indirilen Excel dosyalarında fiyatı artan araçlar **YEŞİL**, düşenler **KIRMIZI** dolgu ile vurgulanır.
  - Değişim yüzdeleri (`+%5.00` gibi) ve `Fark Tipi` sütunları tam doğrulukla hesaplanır.

- **🛡️ Kurumsal Uyumlu Anti-Bot ve Fallback (Stale Data) Güvenliği**:
  - Cloudflare/Akamai bot engellerine karşı tarayıcı başlıkları (`User-Agent`, `Sec-Fetch-*`) ve 3 kademeli retry mekanizması mevcuttur.
  - Bir markanın sitesi bakıma girdiğinde sistem çökmez; veritabanındaki son doğrulanmış veriyi (**stale data**) kullanarak kesintisiz hizmet verir.

---

## 🏗️ Proje Yapısı

```text
vw-price-scraper/
│
├── scrapers/                   # 17 Marka İçin Özel Scraper Modülleri
│   ├── base_scraper.py         # Ortak arayüz, HTTP retry & SQLite kayıt mantığı
│   ├── vw_scraper.py           # Doğuş Oto API Gateway
│   ├── skoda_scraper.py        # Skoda Next.js JSON Parser
│   ├── renault_scraper.py      # Renault Tekil Model Landing Page Parser
│   ├── ford_scraper.py         # Ford Web API JSON Client
│   ├── hyundai_scraper.py      # Hyundai Resmi GraphQL API Client
│   ├── toyota_scraper.py       # Toyota XML Price Feed Parser
│   ├── chery_scraper.py        # Chery Divi Table Parser
│   ├── dacia_scraper.py        # Dacia HTML Parser
│   ├── kia_scraper.py          # Kia Katalog Parser
│   ├── fiat_scraper.py         # Fiat Katalog Parser
│   ├── peugeot_scraper.py      # Peugeot Katalog Parser
│   ├── opel_scraper.py         # Opel Katalog Parser
│   ├── citroen_scraper.py      # Citroën Katalog Parser
│   ├── jeep_scraper.py         # Jeep Katalog Parser
│   ├── alfaromeo_scraper.py   # Alfa Romeo Katalog Parser
│   ├── ds_scraper.py           # DS Automobiles Katalog Parser
│   └── maserati_scraper.py     # Maserati Katalog Parser
│
├── app.py                      # Flask REST API & Web Sunucusu
├── multi_scraper.py            # Tüm scraper'ları çalıştıran orkestrasyon betiği
├── car_prices.db               # İlişkisel SQLite Veritabanı
├── templates/                  # Jinja2 HTML Arayüz Şablonları (index.html, login.html)
├── static/                     # CSS Stilleri ve JavaScript (app.js, style.css)
└── requirements.txt            # Python Bağımlılık Listesi
```

---

## 💻 Kurumsal Bilgisayarda Sıfırdan Kurulum Rehberi

Kurumsal bilgisayarınızda projeyi sıfırdan çalıştırmak için aşağıdaki adımları sırasıyla uygulayın:

### 1. Adım: Projeyi Bilgisayarınıza Çekin

Komut İstemcisi (CMD) veya PowerShell açıp projeyi indirin:
```cmd
git clone https://github.com/EmirBuluttl/vw-price-scraper.git
cd vw-price-scraper
```
*(Eğer proje zaten bilgisayarınızdaysa en son güncellemeleri çekin: `git pull origin main`)*

---

### 2. Adım: Kütüphaneleri Doğru Şekilde Yükleyin

⚠️ **ÖNEMLİ (Kurumsal Ortam Uyarısı)**: Bağımlılıkları doğrudan aktif Python yürütücüsüne yüklemek için `pip` yerine **`python -m pip`** komutunu kullanın:

```cmd
python -m pip install -r requirements.txt
```

#### 🛠️ Kurumsal Proxy / Şirket Güvenlik Duvarı Takılması Durumunda:
Eğer şirketinizin güvenlik duvarı SSL sertifikası hatası verirse şu komutu kullanabilirsiniz:
```cmd
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

---

### 3. Adım: Kurulumu Doğrulayın

Kütüphanelerin tam yüklendiğini teyit etmek için şu hızlı testi çalıştırın:
```cmd
python -c "import openpyxl; import flask; import requests; print('✅ TÜM KURULUM BAŞARILI!')"
```
Ekranda **`✅ TÜM KURULUM BAŞARILI!`** çıktısını görüyorsanız sistem hazırdır.

---

### 4. Adım: Web Sunucusunu Başlatın

```cmd
python app.py
```

Terminalde şu çıktıyı göreceksiniz:
```text
======================================================================
  KURUMSAL COKLU MARKA ARAC FIYAT SCRAPER WEB PANELI
  Tarayicida acin: http://localhost:5000
======================================================================
 * Running on http://0.0.0.0:5000
```

---

### 5. Adım: Web Paneline Erişin

1. Terminal ekranını kapatmayın (arka planda sunucu olarak çalışır).
2. Tarayıcınızı açıp adres çubuğuna yazın:
   ```text
   http://localhost:5000
   ```
3. **İlk Giriş / Yönetici Kurulumu**:
   - Eğer veritabanı sıfırsa sistem sizi **`/setup-admin`** ekranına yönlendirir. Kendinize bir Admin şifresi belirleyin.
   - Şifre belirledikten sonra `admin` kullanıcı adı ve şifrenizle sisteme giriş yapabilirsiniz.

---

### 🌐 Ofis / Şirket Ağındaki Diğer Bilgisayarlardan Erişmek İçin

Web sunucusu `0.0.0.0` portunda çalıştığı için aynı şirket Wi-Fi/LAN ağı üzerindeki diğer bilgisayarlardan veya tabletlerden de erişilebilir:

1. Sunucu bilgisayarda CMD'ye `ipconfig` yazıp IPv4 adresinizi öğrenin (Örn: `192.168.1.50`).
2. Ağdaki diğer bilgisayarların tarayıcısından şu adrese girin:
   ```text
   http://192.168.1.50:5000
   ```

---

## 🛠️ Sıkça Karşılaşılan Sorunlar & Çözümleri

### ❓ `ModuleNotFoundError: No module named 'openpyxl'` veya `'flask'`
- **Neden**: `pip` komutu sistemdeki farklı bir Python sürümüne kütüphane yüklemiş olabilir.
- **Çözüm**: Doğrudan aktif Python'a yüklemek için şu komutu çalıştırın:
  ```cmd
  python -m pip install openpyxl flask requests beautifulsoup4 werkzeug lxml
  ```

### ❓ Port 5000 Kullanımda / `Address already in use` Hatası
- **Neden**: Bilgisayarınızda Port 5000 başka bir servis (AirPlay veya çakışan sunucu) tarafından kullanılıyordur.
- **Çözüm**: `app.py` dosyasının en altındaki `port=5000` değerini `port=5050` yapıp kaydedin ve tekrar `python app.py` çalıştırın.

---

## 📝 Lisans ve Kurumsal Kullanım

Bu proje kurumsal otomotiv piyasa analizi ve fiyat takibi amacıyla geliştirilmiştir. Toplanan tüm veriler distribütörlerin kamuya açık liste fiyatlarıdır.
