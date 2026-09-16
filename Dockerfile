FROM python:3.10-slim

# Installation de ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# On installe la version master de yt-dlp pour avoir le tout dernier patch anti-bot YouTube
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -U https://github.com/yt-dlp/yt-dlp/archive/master.tar.gz

COPY . .

CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120"]
