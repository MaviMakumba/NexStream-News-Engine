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
# BuildKit cache mount: indirilen wheel'ler image KATMANINA girmez (boyut artmaz)
# ama build'ler ARASINDA saklanır. Eskiden `--no-cache-dir` vardı; torch/transformers
# gibi GB'larca paket her denemede sıfırdan iniyordu — hem 85 dk sürüyordu hem de
# indirilen byte arttıkça rastgele bozulma ("PACKAGES DO NOT MATCH THE HASHES")
# riski büyüyordu. --retries/--timeout ise tekil ağ hatalarını kendi içinde toparlar.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 --timeout 120 -r requirements.txt

# 5. Kodların Kopyalanması:
# Bilgisayarındaki tüm kodları konteynırın içine atıyoruz.
COPY . .

# 6. Non-root kullanıcı (güvenlik denetimi): container escape sınıfı bir zafiyet
# çıkarsa root-in-container host'ta root'a çok daha kısa bir yol demek. --create-home
# ile gerçek bir HOME açılıyor ki SentenceTransformer'ın indirdiği model cache'i
# (~/.cache/huggingface) bu kullanıcı altında sorunsuz yazılabilsin.
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# 7. Başlatma Komutu:
# Konteynır ayağa kalktığında ne yapsın?
# Şimdilik ana uygulamamızı çalıştırsın.
CMD ["python", "main.py"]