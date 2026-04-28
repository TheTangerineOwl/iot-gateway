FROM python:3.13-slim

# Системные зависимости (psycopg binary требует libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r base_requirements.txt

COPY .env.example .env

RUN mkdir -p logs data

RUN cp config/configuration/public_config_whitelist.example.txt config/configuration/public_config_whitelist.txt

# Порты, которые слушает шлюз
EXPOSE 8081
EXPOSE 8082
EXPOSE 5683/udp

CMD ["python", "main.py"]
