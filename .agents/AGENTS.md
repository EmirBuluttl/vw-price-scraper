# Project Rules & Guidelines

## ⚠️ VERİTABANI VE VERİ SİLME KURALLARI (STRICT DATABASE POLICY)
- **HİÇBİR KOŞULDA VERİTABANINDAN VERİ VEYA TABLO SİLME İŞLEMİ (DELETE / DROP / TRUNCATE) KULLANICIDAN AÇIK ONAY ALINMADAN YAPILAMAZ.**
- Herhangi bir veri silme veya sıfırlama işlemi gerekirse:
  1. Önce veritabanının bir yedeği alınmalıdır (`.db.bak` veya zaman damgalı SQL dump).
  2. Kullanıcıya açıkça sorulmalı ve kullanıcı onayı alınmalıdır.
  3. Açık onay yoksa veritabanı silme/temizleme işlemi YASAKTIR.
