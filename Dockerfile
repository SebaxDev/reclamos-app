FROM python:3.9-bullseye as builder

WORKDIR /app
COPY requirements.txt .

# 1. Instala dependencias del sistema y compila paquetes
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && pip install --user --no-warn-script-location -r requirements.txt

# 2. Etapa de producción ligera
FROM python:3.9-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# 3. Configuración final
ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/root/.local/lib/python3.9/site-packages

# 4. Instala solo las dependencias de runtime necesarias
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080
CMD ["streamlit", "run", "appreclamos.py", "--server.port=8080", "--server.address=0.0.0.0"]
