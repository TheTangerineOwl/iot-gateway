FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY web/frontend/package.json web/frontend/package-lock.json* ./

RUN npm ci --prefer-offline

COPY web/frontend .

RUN npm run build

FROM python:3.11-slim

WORKDIR /app

COPY --from=frontend-builder /app/static /app/web/static

COPY web/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY web/ /app/web/

ENV WEB__HOST=0.0.0.0
ENV WEB__PORT=8090
ENV PYTHONPATH=/app

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8090/docs', timeout=5)" || exit 1

CMD ["python", "-m", "uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8090"]
