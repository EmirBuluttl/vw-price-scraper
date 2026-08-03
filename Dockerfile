# ==============================================================================
# Kurumsal Docker Yapılandırması — Enterprise Price-Scraper Platform
# ==============================================================================

FROM python:3.11-slim

# Sistem ortam değişkenleri
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    PORT=5000

# Çalışma dizini
WORKDIR /app

# Sistem bağımlılıkları ve sağlık kontrolü araçları
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılık dosyalarını kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# Güvenli non-root kullanıcı oluştur ve yetkilendir
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Bağlantı noktası
EXPOSE 5000

# Docker Healthcheck (Uygulama Sağlık Kontrolü)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Uygulamayı gunicorn WSGI sunucusu ile başlat
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
