FROM python:3.11-slim-bookworm

# Systeem dependencies (audio + BirdNET-Analyzer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    alsa-utils \
    ffmpeg \
    libsndfile1 \
    sox \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App bestanden
COPY birdwatch_pi/ ./birdwatch_pi/
COPY server.py .
COPY recorder.py .
COPY analyzer.py .
COPY exporter.py .

# Data directory voor opslag
RUN mkdir -p /data/recordings /data/detections

EXPOSE 7766

CMD ["python", "server.py"]
