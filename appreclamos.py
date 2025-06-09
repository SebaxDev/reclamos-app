import streamlit as st
from google.oauth2 import service_account
import gspread
from datetime import datetime
import pytz
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# --- ESTILO VISUAL GLOBAL ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

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

# --- TÍTULO Y DASHBOARD ---
st.title("📋 Fusion Reclamos App")

# --- METRICAS RESUMEN ---
try:
    data_metricas = sheet_reclamos.get_all_records()
    df_metricas = pd.DataFrame(data_metricas)
    total = len(df_metricas)
    pendientes = len(df_metricas[df_metricas["Estado"] == "Pendiente"])
    resueltos = len(df_metricas[df_metricas["Estado"] == "Resuelto"])
    en_curso = len(df_metricas[df_metricas["Estado"] == "En curso"])

    colm1, colm2, colm3, colm4 = st.columns(4)
    colm1.metric("📄 Total", total)
    colm2.metric("🕒 Pendientes", pendientes)
    colm3.metric("🔧 En curso", en_curso)
    colm4.metric("✅ Resueltos", resueltos)
except:
    st.info("No hay datos disponibles para mostrar métricas aún.")

st.divider()

# --- FORMULARIO DE RECLAMOS ---
st.subheader("📝 Cargar nuevo reclamo")

nro_cliente = st.text_input("🔢 N° de Cliente").strip()
cliente_existente = None
if "Nº Cliente" in df_clientes.columns and nro_cliente:
    df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
    match = df_clientes[df_clientes["Nº Cliente"] == nro_cliente]
    if not match.empty:
        cliente_existente = match.squeeze()
        st.success("✅ Cliente reconocido, datos auto-cargados.")

with st.form("reclamo_formulario"):
    col1, col2 = st.columns(2)
    if cliente_existente is not None:
        with col1:
            sector = st.text_input("🏙️ Sector / Zona", value=cliente_existente["Sector"])
            direccion = st.text_input("📍 Dirección", value=cliente_existente["Dirección"])
        with col2:
            nombre = st.text_input("👤 Nombre del Cliente", value=cliente_existente["Nombre"])
            telefono = st.text_input("📞 Teléfono", value=cliente_existente["Teléfono"])
    else:
        with col1:
            sector = st.text_input("🏙️ Sector / Zona")
            direccion = st.text_input("📍 Dirección")
        with col2:
            nombre = st.text_input("👤 Nombre del Cliente")
            telefono = st.text_input("📞 Teléfono")

    tipo_reclamo = st.selectbox("📌 Tipo de Reclamo", [
        "Conexion C+I", "Conexion Cable", "Conexion Internet", "Suma Internet",
        "Suma Cable", "Reconexion", "Sin Señal Ambos", "Sin Señal Cable",
        "Sin Señal Internet", "Sintonia", "Interferencia", "Traslado",
        "Extension x2", "Extension x3", "Extension x4", "Cambio de Ficha",
        "Cambio de Equipo", "Reclamo"])

    detalles = st.text_area("📝 Detalles del Reclamo")
    estado = st.selectbox("⚙️ Estado del Reclamo", ["Pendiente", "En curso", "Resuelto"], index=0)
    tecnico = st.text_input("👷 Técnico asignado (opcional)")
    nota = st.text_area("🗒️ Nota o seguimiento (opcional)")
    atendido_por = st.text_input("👤 Atendido por")
    enviado = st.form_submit_button("✅ Guardar Reclamo")

if enviado:
    if not nro_cliente:
        st.error("⚠️ Debes ingresar un número de cliente.")
    else:
        argentina = pytz.timezone("America/Argentina/Buenos_Aires")
        fecha_hora = datetime.now(argentina).strftime("%Y-%m-%d %H:%M:%S")
        fila_reclamo = [fecha_hora, nro_cliente, sector, nombre, direccion, telefono,
                        tipo_reclamo, detalles, estado, tecnico, nota, atendido_por]
        try:
            sheet_reclamos.append_row(fila_reclamo)
            st.success("✅ Reclamo guardado correctamente.")
            df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
            if nro_cliente not in df_clientes["Nº Cliente"].values:
                fila_cliente = [nro_cliente, sector, nombre, direccion, telefono]
                sheet_clientes.append_row(fila_cliente)
                st.info("🗂️ Nuevo cliente agregado a la base de datos.")
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")

# --- VISUALIZACIÓN Y EDICIÓN DE RECLAMOS ---
st.divider()
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

# --- EDICIÓN DE CLIENTES ---
st.divider()
st.subheader("🛠️ Editar datos de un cliente")

cliente_editar = st.text_input("🔎 Ingresá N° de Cliente a editar").strip()
if cliente_editar:
    df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
    cliente_row = df_clientes[df_clientes["Nº Cliente"] == cliente_editar]
    if not cliente_row.empty:
        cliente_actual = cliente_row.squeeze()
        nuevo_sector = st.text_input("🏙️ Sector", value=cliente_actual["Sector"])
        nuevo_nombre = st.text_input("👤 Nombre", value=cliente_actual["Nombre"])
        nueva_direccion = st.text_input("📍 Dirección", value=cliente_actual["Dirección"])
        nuevo_telefono = st.text_input("📞 Teléfono", value=cliente_actual["Teléfono"])
        if st.button("💾 Actualizar datos del cliente"):
            try:
                index = cliente_row.index[0] + 2
                sheet_clientes.update(f"B{index}", nuevo_sector)
                sheet_clientes.update(f"C{index}", nuevo_nombre)
                sheet_clientes.update(f"D{index}", nueva_direccion)
                sheet_clientes.update(f"E{index}", nuevo_telefono)
                st.success("✅ Cliente actualizado correctamente.")
            except Exception as e:
                st.error(f"❌ Error al actualizar: {e}")
    else:
        st.warning("⚠️ Cliente no encontrado.")

# --- IMPRESIÓN DE RECLAMOS EN FORMATO COMPACTO ---
st.divider()
st.subheader("🖨️ Seleccionar reclamos para imprimir (formato técnico compacto)")

try:
    data = sheet_reclamos.get_all_records()
    df_pdf = pd.DataFrame(data)

    if not df_pdf.empty:
        selected = st.multiselect("Seleccioná los reclamos a imprimir:", df_pdf.index,
                                  format_func=lambda x: f"{df_pdf.at[x, 'Nº Cliente']} - {df_pdf.at[x, 'Nombre']}")

        if st.button("📄 Generar PDF con seleccionados") and selected:
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            y = height - 40

            for i, idx in enumerate(selected):
                reclamo = df_pdf.loc[idx]
                c.setFont("Helvetica-Bold", 20)
                c.drawString(40, y, f"Reclamo #{idx + 1}")
                y -= 15
                c.setFont("Helvetica", 15)
                lineas = [
                    f"Fecha: {reclamo['Fecha y hora']} - Cliente: {reclamo['Nombre']} ({reclamo['Nº Cliente']})",
                    f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                    f"Sector: {reclamo['Sector']} - Técnico: {reclamo['Técnico']}",
                    f"Tipo: {reclamo['Tipo de reclamo']}",
                    f"Detalles: {reclamo['Detalles'][:80]}..." if len(reclamo['Detalles']) > 80 else f"Detalles: {reclamo['Detalles']}",
                ]
                for linea in lineas:
                    c.drawString(40, y, linea)
                    y -= 12
                y -= 8
                c.drawString(40, y, "Firma técnico: _____________________________")
                y -= 25
                if y < 150 and i < len(selected) - 1:
                    c.showPage()
                    y = height - 40

            c.save()
            buffer.seek(0)
            st.download_button(
                label="📥 Descargar PDF",
                data=buffer,
                file_name="reclamos_seleccionados.pdf",
                mime="application/pdf"
            )
    else:
        st.info("No hay reclamos disponibles para imprimir.")
except Exception as e:
    st.error(f"❌ Error al generar PDF: {e}")
