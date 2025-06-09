import streamlit as st
from google.oauth2 import service_account
import gspread
from datetime import datetime
import pytz
import pandas as pd

# --- CONFIGURACIÓN ---
SHEET_ID = "13R_3Mdr25Jd-nGhK7CxdcbKkFWLc0LPdYrOLOY8sZJo"
WORKSHEET_RECLAMOS = "Principal"
WORKSHEET_CLIENTES = "Clientes"

# --- AUTENTICACIÓN USANDO SECRETS ---
info = dict(st.secrets["gcp_service_account"])
info["private_key"] = info["private_key"].replace("\\n", "\n")

credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)

client = gspread.authorize(credentials)
sheet_reclamos = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_RECLAMOS)
sheet_clientes = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_CLIENTES)

# --- CARGAR BASE DE CLIENTES ---
clientes_data = sheet_clientes.get_all_records()
df_clientes = pd.DataFrame(clientes_data)

# --- TÍTULO ---
st.title("📋 Fusion Reclamos App")

# --- INGRESAR N° DE CLIENTE ---
nro_cliente = st.text_input("🔢 N° de Cliente").strip()

cliente_existente = None
if "Nº Cliente" in df_clientes.columns and nro_cliente:
    df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
    match = df_clientes[df_clientes["Nº Cliente"] == nro_cliente]
    if not match.empty:
        cliente_existente = match.squeeze()
        st.success("✅ Cliente reconocido, datos auto-cargados.")

# --- FORMULARIO ---
with st.form("reclamo_formulario"):
    if cliente_existente is not None:
        sector = st.text_input("🏙️ Sector / Zona", value=cliente_existente["Sector"])
        nombre = st.text_input("👤 Nombre del Cliente", value=cliente_existente["Nombre"])
        direccion = st.text_input("📍 Dirección", value=cliente_existente["Dirección"])
        telefono = st.text_input("📞 Teléfono", value=cliente_existente["Teléfono"])
    else:
        sector = st.text_input("🏙️ Sector / Zona")
        nombre = st.text_input("👤 Nombre del Cliente")
        direccion = st.text_input("📍 Dirección")
        telefono = st.text_input("📞 Teléfono")

    tipo_reclamo = st.selectbox(
        "📌 Tipo de Reclamo",
        ["Sin señal", "Internet lento", "Cable cortado", "Cambio de equipo", "Corte total", "Otros"]
    )

    detalles = st.text_area("📝 Detalles del Reclamo")
    estado = st.selectbox("⚙️ Estado del Reclamo", ["Pendiente", "En curso", "Resuelto"], index=0)
    tecnico = st.text_input("👷 Técnico asignado (opcional)")
    nota = st.text_area("🗒️ Nota o seguimiento (opcional)")
    enviado = st.form_submit_button("✅ Guardar Reclamo")

# --- GUARDADO ---
if enviado:
    if not nro_cliente:
        st.error("⚠️ Debes ingresar un número de cliente.")
    else:
        argentina = pytz.timezone("America/Argentina/Buenos_Aires")
        fecha_hora = datetime.now(argentina).strftime("%Y-%m-%d %H:%M:%S")

        fila_reclamo = [
            fecha_hora,
            nro_cliente,
            sector,
            nombre,
            direccion,
            telefono,
            tipo_reclamo,
            detalles,
            estado,
            tecnico,
            nota
        ]

        try:
            sheet_reclamos.append_row(fila_reclamo)
            st.success("✅ Reclamo guardado correctamente.")

            # Verificar si el cliente ya está cargado
            df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
            if nro_cliente not in df_clientes["Nº Cliente"].values:
                fila_cliente = [nro_cliente, sector, nombre, direccion, telefono]
                sheet_clientes.append_row(fila_cliente)
                st.info("🗂️ Nuevo cliente agregado a la base de datos.")
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")

# --- TABLA Y EDICIÓN ---
st.markdown("---")
st.subheader("📊 Reclamos cargados")

try:
    data = sheet_reclamos.get_all_records()
    df = pd.DataFrame(data)

    df["Fecha y hora"] = pd.to_datetime(df["Fecha y hora"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    df = df.sort_values("Fecha y hora", ascending=False)

    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_estado = st.selectbox("🔎 Filtrar por estado", ["Todos"] + sorted(df["Estado"].unique()))
    with col2:
        filtro_sector = st.selectbox("🏙️ Filtrar por sector", ["Todos"] + sorted(df["Sector"].unique()))
    with col3:
        filtro_tipo = st.selectbox("📌 Filtrar por tipo", ["Todos"] + sorted(df["Tipo de reclamo"].unique()))

    if filtro_estado != "Todos":
        df = df[df["Estado"] == filtro_estado]
    if filtro_sector != "Todos":
        df = df[df["Sector"] == filtro_sector]
    if filtro_tipo != "Todos":
        df = df[df["Tipo de reclamo"] == filtro_tipo]

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="editor",
        column_config={
            "Estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "En curso", "Resuelto"]),
            "Técnico": st.column_config.TextColumn("Técnico asignado"),
            "Nota": st.column_config.TextColumn("Nota de seguimiento")
        }
    )

    if st.button("💾 Guardar cambios en Google Sheets"):
        try:
            edited_df = edited_df.astype(str)
            sheet_reclamos.clear()
            sheet_reclamos.append_row(edited_df.columns.tolist())
            sheet_reclamos.append_rows(edited_df.values.tolist())
            st.success("✅ Cambios guardados correctamente.")
        except Exception as e:
            st.error(f"❌ Error al guardar los cambios: {e}")

except Exception as e:
    st.warning(f"⚠️ No se pudieron cargar los datos: {e}")
