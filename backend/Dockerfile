# Imagen de la API. Construir desde la raíz del repositorio:  docker compose -f despliegue/docker/docker-compose.yml up
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN grep -viE '^pytest\b' requirements.txt > req.txt && pip install --no-cache-dir -r req.txt
COPY app ./app
COPY scripts ./scripts
RUN useradd --system orthosync && mkdir -p /datos && chown orthosync /datos
USER orthosync
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
