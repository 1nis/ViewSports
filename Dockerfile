FROM python:3.9-slim

# Installation de Chromium et drivers
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor.py .

# On lance le script avec l'option -u (unbuffered) pour voir les logs en temps réel dans Portainer
CMD ["python", "-u", "monitor.py"]