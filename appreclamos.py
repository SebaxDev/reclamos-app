import streamlit as st
from google.oauth2 import service_account
import gspread
from datetime import datetime
import pytz

# --- CONFIGURACIÓN ---
SHEET_ID = "13R_3Mdr25Jd-nGhK7CxdcbKkFWLc0LPdYrOLOY8sZJo"
WORKSHEET_NAME = "Principal"

# --- AUTENTICACIÓN USANDO SECRETS ---
info = dict(st.secrets["gcp_service_account"])
info["private_key"] = info["private_key"].replace("\\n", "\n")

credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)

client = gspread.authorize(credentials)
sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

# --- TÍTULO ---
st.title("📋 Fusion Reclamos App")

# --- FORMULARIO ---
with st.form("reclamo_formulario"):
    nro_cliente = st.text_input("🔢 N° de Cliente")
    sector = st.text_input("🏙️ Sector / Zona")
    nombre = st.text_input("👤 Nombre del Cliente")
    direccion = st.text_input("📍 Dirección")
    telefono = st.text_input("📞 Teléfono")

    tipo_reclamo = st.selectbox(
        "📌 Tipo de Reclamo",
        ["Sin señal", "Internet lento", "Cable cortado", "Cambio de equipo", "Corte total", "Otros"]
    )

    detalles = st.text_area("📝 Detalles del Reclamo")

    estado = st.selectbox(
        "⚙️ Estado del Reclamo",
        ["Pendiente", "En curso", "Resuelto"],
        index=0
    )

    enviado = st.form_submit_button("✅ Guardar Reclamo")

# --- GUARDADO ---
if enviado:
    argentina = pytz.timezone("America/Argentina/Buenos_Aires")
    fecha_hora = datetime.now(argentina).strftime("%d-%m-%Y %H:%M")
    fila = [
        fecha_hora,
        nro_cliente,
        sector,
        nombre,
        direccion,
        telefono,
        tipo_reclamo,
        detalles,
        estado
    ]
    try:
        sheet.append_row(fila)
        st.success("✅ Reclamo guardado correctamente.")
    except Exception as e:
        st.error(f"❌ Error al guardar el reclamo: {e}")
st.markdown("---")
st.subheader("📊 Reclamos cargados")

# --- Leer datos de la hoja ---
try:
    datos = sheet.get_all_records()
    df = pd.DataFrame(datos)

    # --- Filtros ---
    col1, col2 = st.columns(2)
    with col1:
        filtro_estado = st.selectbox("🔎 Filtrar por estado", ["Todos"] + sorted(df["Estado"].unique()))
    with col2:
        filtro_sector = st.selectbox("🏙️ Filtrar por sector", ["Todos"] + sorted(df["Sector"].unique()))

    # --- Aplicar filtros ---
    if filtro_estado != "Todos":
        df = df[df["Estado"] == filtro_estado]
    if filtro_sector != "Todos":
        df = df[df["Sector"] == filtro_sector]

    # --- Mostrar tabla ---
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.warning(f"No se pudieron cargar los datos: {e}")
