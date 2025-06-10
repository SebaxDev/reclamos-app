import streamlit as st
from google.oauth2 import service_account
import gspread
from datetime import datetime
import pytz
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# --- LOGIN CON SECRETS ---
if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

if not st.session_state.logueado:
    st.title("🔐 Iniciar sesión")
    with st.form("login_formulario"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")

        if enviar:
            if usuario in st.secrets["auth"] and st.secrets["auth"][usuario] == password:
                st.session_state.logueado = True
                st.session_state.usuario_actual = usuario
                st.success("✅ Acceso concedido.")
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

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

# --- CARGAR BASES ---
clientes_data = sheet_clientes.get_all_records()
df_clientes = pd.DataFrame(clientes_data)
reclamos_data = sheet_reclamos.get_all_records()
df_reclamos = pd.DataFrame(reclamos_data)

# --- TÍTULO Y DASHBOARD ---
st.title("📋 Fusion Reclamos App")

# --- METRICAS RESUMEN ---
try:
    df_metricas = df_reclamos.copy()
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

# --- MENÚ DE NAVEGACIÓN ---
opcion = st.radio("📂 Ir a la sección:", ["Inicio", "Historial por cliente", "Editar cliente", "Imprimir reclamos"], horizontal=True)

# --- SECCIÓN 1: INICIO (CARGA + LISTA DE RECLAMOS) ---
if opcion == "Inicio":
    st.subheader("📝 Cargar nuevo reclamo")
    nro_cliente = st.text_input("🔢 N° de Cliente").strip()
    cliente_existente = None
    formulario_bloqueado = False

    if "Nº Cliente" in df_clientes.columns and nro_cliente:
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
        match = df_clientes[df_clientes["Nº Cliente"] == nro_cliente]
        reclamos_pendientes = df_reclamos[(df_reclamos["Nº Cliente"] == nro_cliente) & (df_reclamos["Estado"] == "Pendiente")]
        if not match.empty:
            cliente_existente = match.squeeze()
            st.success("✅ Cliente reconocido, datos auto-cargados.")
        if not reclamos_pendientes.empty:
            st.error("⚠️ Este cliente ya tiene un reclamo pendiente. No se puede cargar uno nuevo hasta que se resuelva el anterior.")
            formulario_bloqueado = True

    if not formulario_bloqueado:
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
                    if nro_cliente not in df_clientes["Nº Cliente"].values:
                        fila_cliente = [nro_cliente, sector, nombre, direccion, telefono]
                        sheet_clientes.append_row(fila_cliente)
                        st.info("🗂️ Nuevo cliente agregado a la base de datos.")
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")

    st.divider()
    st.subheader("📊 Reclamos cargados")
    try:
        df = df_reclamos.copy()
        df["Fecha y hora"] = pd.to_datetime(df["Fecha y hora"], errors="coerce")
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

# --- SECCIÓN 2: HISTORIAL POR CLIENTE ---
if opcion == "Historial por cliente":
    st.subheader("📜 Historial de reclamos por cliente")
    historial_cliente = st.text_input("🔍 Ingresá N° de Cliente para ver su historial").strip()

    if historial_cliente:
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
        historial = df_reclamos[df_reclamos["Nº Cliente"] == historial_cliente]

        if not historial.empty:
            historial["Fecha y hora"] = pd.to_datetime(historial["Fecha y hora"], errors="coerce")
            historial = historial.sort_values("Fecha y hora", ascending=False)

            st.success(f"🔎 Se encontraron {len(historial)} reclamos para el cliente {historial_cliente}.")
            st.dataframe(
                historial[
                    ["Fecha y hora", "Tipo de reclamo", "Estado", "Técnico", "Nota", "Detalles"]
                ],
                use_container_width=True
            )
        else:
            st.info("❕ Este cliente no tiene reclamos registrados.")

# --- SECCIÓN 3: EDITAR CLIENTE ---
if opcion == "Editar cliente":
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

# --- SECCIÓN 4: IMPRESIÓN ---
if opcion == "Imprimir reclamos":
    st.subheader("🖨️ Seleccionar reclamos para imprimir (formato técnico compacto)")

    try:
        df_pdf = df_reclamos.copy()

        st.info("🕒 Reclamos pendientes de resolución")
        df_pendientes = df_pdf[df_pdf["Estado"] == "Pendiente"]
        if not df_pendientes.empty:
            st.dataframe(df_pendientes[["Fecha y hora", "Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]], use_container_width=True)
        else:
            st.success("✅ No hay reclamos pendientes actualmente.")

        solo_pendientes = st.checkbox("🧾 Mostrar solo reclamos pendientes para imprimir")

        if solo_pendientes:
            df_pdf = df_pdf[df_pdf["Estado"] == "Pendiente"]

        selected = st.multiselect("Seleccioná los reclamos a imprimir:", df_pdf.index,
                                  format_func=lambda x: f"{df_pdf.at[x, 'Nº Cliente']} - {df_pdf.at[x, 'Nombre']}")

        if st.button("📄 Generar PDF con seleccionados") and selected:
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            y = height - 40

            for i, idx in enumerate(selected):
                reclamo = df_pdf.loc[idx]
                c.setFont("Helvetica-Bold", 16)
                c.drawString(40, y, f"Reclamo #{reclamo['Nº Cliente']}")
                y -= 15
                c.setFont("Helvetica", 12)
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

        elif not selected:
            st.info("Seleccioná al menos un reclamo para generar el PDF.")

    except Exception as e:
        st.error(f"❌ Error al generar PDF: {e}")
