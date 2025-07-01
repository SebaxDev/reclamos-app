FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080
CMD ["streamlit", "run", "appreclamos.py", "--server.port=8080", "--server.address=0.0.0.0"]
