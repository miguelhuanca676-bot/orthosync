# Imagen del servicio de inferencia (CNN). Los modelos se montan como volumen en /modelos.
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN grep -viE '^(pytest|httpx)\b' requirements.txt > req.txt && pip install --no-cache-dir -r req.txt
COPY cnn ./cnn
RUN useradd --system orthosync
USER orthosync
ENV ORTHOSYNC_MODELOS=/modelos
EXPOSE 8001
CMD ["uvicorn", "cnn.main:app", "--host", "0.0.0.0", "--port", "8001"]
