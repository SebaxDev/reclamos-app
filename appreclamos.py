import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from datetime import datetime

# Conectar con Google Sheets
SHEET_ID = "13R_3Mdr25Jd-nGhK7CxdcbKkFWLc0LPdYrOLOY8sZJo"
SHEET_NAME = "Fusion Reclamos App"  # Podés crear la hoja con ese nombre

# Carga de credenciales desde secrets o archivo
credentials = service_account.Credentials.from_service_account_file(
    "credenciales.json",  # reemplazar si usás secrets
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)

client = gspread.authorize(credentials)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Título
st.title("Fusion Reclamos App")

# Formulario
with st.form("reclamo_form"):
    nro_cliente = st.text_input("N° de Cliente")
    sector = st.text_input("Sector")
    nombre = st.text_input("Nombre del Cliente")
    direccion = st.text_input("Dirección")
    telefono = st.text_input("Teléfono")
    
    tipo_reclamo = st.selectbox(
        "Tipo de Reclamo",
        ["Sin señal", "Lento", "Cambio de equipo", "Corte total", "Otros"]
    )
    
    detalles = st.text_area("Detalles del Reclamo")
    estado = st.selectbox("Estado", ["Pendiente", "En curso", "Resuelto"], index=0)
    
    submit = st.form_submit_button("Guardar reclamo")

# Guardar en Sheets
if submit:
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    datos = [fecha_hora, nro_cliente, sector, nombre, direccion, telefono, tipo_reclamo, detalles, estado]
    sheet.append_row(datos)
    st.success("✅ Reclamo guardado correctamente.")
