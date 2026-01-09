FROM python:3.9-slim

WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du script
COPY monitor.py .

# Lancement
CMD ["python", "-u", "monitor.py"]