FROM python:3.9 as builder

WORKDIR /app
COPY requirements.txt .

# Instala herramientas de compilación
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev libpq-dev && \
    pip install --user -r requirements.txt

# Etapa final ligera
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Asegura el PATH y limpia
ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/root/.local/lib/python3.9/site-packages

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080
CMD ["streamlit", "run", "appreclamos.py", "--server.port=8080", "--server.address=0.0.0.0"]
