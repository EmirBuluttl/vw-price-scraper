# VW Price Scraper Live Catalog Engine

Türkiye distribütör sitelerindeki güncel sıfır araç katalog fiyatlarını canlı olarak tarayan, SQLite veritabanına kaydeden ve Flask tabanlı web panelinde gösteren çok markalı fiyat takip sistemidir.

6 Ağustos 2026 itibarıyla aktif canlı kapsam:

- Volkswagen
- Skoda
- Renault
- Ford
- Hyundai
- Toyota
- Chery
- Dacia
- Kia
- Fiat
- Peugeot
- Opel
- Citroën
- Jeep
- Alfa Romeo
- DS Automobiles

Kapsam dışı:

- Maserati

## Temel prensipler

- Yalnızca canlı ve resmi kaynaklardan veri alınır.
- Canlı veri doğrulanamazsa kayıt kabul edilmez.
- Bayat veri canlıymış gibi sunulmaz.
- Her marka için güvenilir veri yolu doğrulanır, ilk doğrulanmış sonuç kabul edilir.

## Mimari özet

- Backend: Python 3.13 + Flask
- Veritabanı: SQLite
- Tarama: Playwright + resmi HTML / JSON / API kaynakları
- Frontend: Vanilla JS + HTML + CSS

Sistemde toplu tarama sırasında ortak Playwright runtime kullanılır. Bu sayede her marka için ayrı ayrı Chromium açılıp kapanmadığı için timeout ve kaynak birikmesi azaltılır.

## Resmi veri kaynakları

- Volkswagen: Doğuş Oto API
- Skoda: Next.js `__NEXT_DATA__`
- Renault: `best.renault.com.tr` canlı fiyat tabloları
- Ford: resmi fiyat API
- Hyundai: resmi GraphQL
- Toyota: resmi fiyat listesi sayfası
- Chery: resmi fiyat sayfasındaki render edilmiş DOM tabloları
- Dacia: resmi site state verisi
- Kia: resmi fiyat listesi sayfası
- Fiat / Peugeot / Opel / Citroën / Jeep / Alfa Romeo / DS: resmi katalog / iframe / canlı sayfa kaynakları

## Kurulum

### 1) Repoyu çek

```powershell
git clone https://github.com/EmirBuluttl/price-scraper.git
cd price-scraper
```

### 2) Python sanal ortamı oluştur

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Bağımlılıkları kur

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4) Playwright Chromium kur

```powershell
python -m playwright install chromium
```

Not: Bazı kurum ağlarında ilk kurulum sırasında güvenlik duvarı / proxy nedeniyle ek izin gerekebilir.

## Çalıştırma

Varsayılan:

```powershell
python app.py
```

Özel port:

```powershell
$env:PORT="5001"
python app.py
```

Ardından tarayıcıdan:

- `http://localhost:5000`
- veya port değiştirdiysen ilgili port

## Erişim modeli

- Uygulama arayüzü herkese açıktır.
- Admin kurulumu zorunlu değildir.
- Tekli canlı tarama ve toplu canlı tarama için ayrıca admin girişi gerekmez.

## Başka bilgisayarda kurulum

Yeni bir bilgisayarda minimum akış:

```powershell
git clone https://github.com/EmirBuluttl/price-scraper.git
cd price-scraper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

Eğer aynı ağdaki başka cihazlardan erişilecekse sunucuyu çalıştıran makinenin IPv4 adresi ile erişebilirsin:

- `http://192.168.x.x:5000`

## Manuel test önerisi

Uygulama açıldıktan sonra önce tekli marka testleri, sonra toplu test yapılmalı.

### Tekli marka testleri

Önerilen kontrol sırası:

1. Peugeot
2. Toyota
3. Kia
4. Renault
5. Chery

Kontrol örnekleri:

- Peugeot 408:
  - `Yeni 408 ALLURE 1.2 Hybrid 145hp eDCS6`
  - `Yeni 408 GT 1.2 Hybrid 145hp eDCS6`

- Toyota Corolla Hybrid:
  - `1.8 Hybrid Dream e-CVT`
  - `1.8 Hybrid Dream-X-Pack e-CVT`
  - `1.8 Hybrid Flame X-Pack e-CVT`

- Kia Sportage:
  - `Live`
  - `Vision`
  - `Cool`
  - `Elegance`
  - `Prestige`
  - `GT-Line`

- Renault Yeni Clio:
  - `evolution plus TCe EDC 115 hp`
  - `esprit alpine TCe EDC 115 hp`

- Chery:
  - `Tiggo 7 Pro Max`
  - `Tiggo 8 Pro Max`
  - varyantlarda `145hp`

### Toplu test

- `Fiyatları Canlı Tara` tetiklenir
- boş sonuç yağmuru olmamalı
- doğrulanmayan veri kaydedilmemeli
- Maserati aktif listede görünmemeli

## Veritabanı notları

- Ana veritabanı: `car_prices.db`
- Uygulama test sırasında istenirse ayrı DB ile de çalıştırılabilir:
  - `PRICE_SCRAPER_DB_PATH`
  - `SCRAPER_DB_PATH`

Örnek:

```powershell
$env:PRICE_SCRAPER_DB_PATH="C:\temp\car_prices_test.db"
python app.py
```

## Önemli operasyon notları

- `main` sunuma hazır dal olarak kullanılmalıdır.
- yeni scraper geliştirmeleri önce izole test DB üzerinde doğrulanmalıdır.
- canlı veri değişirse marka bazlı scraper tekrar gözden geçirilmelidir.

## Sık görülen sorunlar

### `ModuleNotFoundError`

Sanal ortam aktif değilse:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### `playwright` veya browser hatası

Chromium eksik olabilir:

```powershell
python -m playwright install chromium
```

### `Address already in use`

Port değiştir:

```powershell
$env:PORT="5001"
python app.py
```

### Tarama yavaşsa

- marka siteleri canlı yanıt veriyor mu kontrol et
- kurum ağı Playwright trafiğini yavaşlatıyor olabilir
- önce tekli marka scrape ile doğrula

## Sunum için kısa özet

Bu proje, Türkiye otomotiv distribütör sitelerindeki resmi fiyat kataloglarını canlı okuyup doğrulayan ve yalnızca doğrulanmış sonuçları gösteren bir fiyat takip motorudur. Temel farkı, eski veri fallback’ini kapatması ve her marka için doğrulama kontratı uygulamasıdır.
