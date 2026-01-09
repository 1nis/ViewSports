# On utilise une image python officielle mais pas "slim" pour avoir plus de dépendances système de base
FROM python:3.9

# Installation explicite de Chromium et des dépendances graphiques manquantes
# (libgbm1 et libnss3 sont souvent les responsables des crashs)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libgbm1 \
    libnss3 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor.py .

# Le flag -u est important pour voir les logs Python dans Docker
CMD ["python", "-u", "monitor.py"]