FROM python:3.9-slim

# Ajout de libgbm1, libnss3 et des polices (fonts-liberation) souvent manquants sur slim
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libgbm1 \
    libnss3 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor.py .

CMD ["python", "-u", "monitor.py"]