# Usa una imagen ligera con Python
FROM python:3.10-slim

# Establece directorio de trabajo
WORKDIR /app

# Copia los archivos
COPY . .

# Instala dependencias
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expone el puerto que usa Streamlit
EXPOSE 8501

# Comando para ejecutar la app
CMD ["streamlit", "run", "appreclamos.py", "--server.port=8501", "--server.address=0.0.0.0"]
