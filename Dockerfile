FROM python:3.9-slim as builder

WORKDIR /app
COPY requirements.txt .

# Instala herramientas de compilación
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --user -r requirements.txt

# Etapa final más ligera
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Asegúrate de que los scripts en .local estén en el PATH
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8080
CMD ["streamlit", "run", "appreclamos.py", "--server.port=8080", "--server.address=0.0.0.0"]
