# 1. Base Image: Python 3.11'in hafif (slim) sürümünü kullanıyoruz.
# Neden Slim? Gereksiz Linux araçları yoktur, güvenlik açığı azdır, boyutu küçüktür.
FROM python:3.11-slim

# 2. Çalışma Dizini: Konteynırın içinde kodlarımız nerede duracak?
WORKDIR /app

# 3. Performans Ayarı: Python'ın çıktıları tamponlamasını (buffer) engeller.
# Böylece logları anlık olarak terminalde görebiliriz.
ENV PYTHONUNBUFFERED=1

# 4. Bağımlılıkların Yüklenmesi:
# Önce sadece requirements.txt'yi kopyalıyoruz (Docker Cache mantığı).
COPY requirements.txt .
# --no-cache-dir: İndirilen dosyaları kurulumdan sonra siler, yer kaplamaz.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Kodların Kopyalanması:
# Bilgisayarındaki tüm kodları konteynırın içine atıyoruz.
COPY . .

# 6. Başlatma Komutu:
# Konteynır ayağa kalktığında ne yapsın?
# Şimdilik ana uygulamamızı çalıştırsın.
CMD ["python", "main.py"]