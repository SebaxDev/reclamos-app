"""
Aplicación principal de gestión de reclamos optimizada
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import time
from google.oauth2 import service_account
import gspread
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# Imports de componentes
from components.auth import render_login, check_authentication
from components.navigation import render_navigation, render_user_info
from components.metrics_dashboard import render_metrics_dashboard
from utils.styles import get_main_styles
from utils.data_manager import safe_get_sheet_data, safe_normalize, update_sheet_data, batch_update_sheet
from utils.api_manager import api_manager
from config.settings import *

# Configuración de página
st.set_page_config(
    page_title="Fusion Reclamos App",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Aplicar estilos
st.markdown(get_main_styles(), unsafe_allow_html=True)

# Verificar autenticación
if not check_authentication():
    render_login()
    st.stop()

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
@st.cache_resource
def init_google_sheets():
    """Inicializa la conexión con Google Sheets"""
    try:
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
        
        return sheet_reclamos, sheet_clientes
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None, None

# Inicializar sheets
sheet_reclamos, sheet_clientes = init_google_sheets()

if not sheet_reclamos or not sheet_clientes:
    st.error("No se pudo establecer conexión con Google Sheets")
    st.stop()

# --- CARGAR DATOS ---
@st.cache_data(ttl=30)  # Cache por 30 segundos
def load_data():
    """Carga y procesa los datos de las hojas"""
    df_reclamos = safe_get_sheet_data(sheet_reclamos, COLUMNAS_RECLAMOS)
    df_clientes = safe_get_sheet_data(sheet_clientes, COLUMNAS_CLIENTES)
    
    # Normalizar datos
    df_clientes = safe_normalize(df_clientes, "Nº Cliente")
    df_reclamos = safe_normalize(df_reclamos, "Nº Cliente")
    df_clientes = safe_normalize(df_clientes, "N° de Precinto")
    df_reclamos = safe_normalize(df_reclamos, "N° de Precinto")
    
    return df_reclamos, df_clientes

# Cargar datos con spinner
with st.spinner("Cargando datos..."):
    df_reclamos, df_clientes = load_data()

# --- HEADER DE LA APLICACIÓN ---
st.title("📋 Fusion Reclamos App")
render_user_info()

# --- DASHBOARD DE MÉTRICAS ---
render_metrics_dashboard(df_reclamos)

st.divider()

# --- NAVEGACIÓN ---
opcion = render_navigation()

# --- SECCIÓN 1: INICIO ---
if opcion == "Inicio":
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("📝 Cargar nuevo reclamo")
    
    nro_cliente = st.text_input("🔢 N° de Cliente", placeholder="Ingresa el número de cliente").strip()
    cliente_existente = None
    formulario_bloqueado = False

    if "Nº Cliente" in df_clientes.columns and nro_cliente:
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()

        match = df_clientes[df_clientes["Nº Cliente"] == nro_cliente]

        # Verificar reclamos activos
        reclamos_activos = df_reclamos[
            (df_reclamos["Nº Cliente"] == nro_cliente) &
            (df_reclamos["Estado"].isin(["Pendiente", "En curso"]))
        ]

        if not match.empty:
            cliente_existente = match.iloc[0].to_dict()
            st.success("✅ Cliente reconocido, datos auto-cargados.")
        else:
            st.info("ℹ️ Cliente no encontrado. Se cargará como Cliente Nuevo.")

        if not reclamos_activos.empty:
            st.error("⚠️ Este cliente ya tiene un reclamo sin resolver. No se puede cargar uno nuevo hasta que se cierre el anterior.")
            formulario_bloqueado = True

    if not formulario_bloqueado:
        with st.form("reclamo_formulario"):
            col1, col2 = st.columns(2)

            if cliente_existente is not None:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", value=cliente_existente["Sector"])
                    direccion = st.text_input("📍 Dirección", value=cliente_existente["Dirección"])
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", value=cliente_existente["Nombre"])
                    telefono = st.text_input("📞 Teléfono", value=cliente_existente["Teléfono"])
            else:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", placeholder="Ej: Centro, Norte, Sur")
                    direccion = st.text_input("📍 Dirección", placeholder="Dirección completa")
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", placeholder="Nombre completo")
                    telefono = st.text_input("📞 Teléfono", placeholder="Número de contacto")

            tipo_reclamo = st.selectbox("📌 Tipo de Reclamo", TIPOS_RECLAMO)
            detalles = st.text_area("📝 Detalles del Reclamo", placeholder="Describe el problema o solicitud...")
            
            col3, col4 = st.columns(2)
            with col3:
                precinto = st.text_input("🔒 N° de Precinto (opcional)", 
                                       value=cliente_existente.get("N° de Precinto", "").strip() if cliente_existente else "",
                                       placeholder="Número de precinto")
            with col4:
                atendido_por = st.text_input("👤 Atendido por", placeholder="Nombre de quien atiende")

            col5, col6, col7 = st.columns([1, 2, 1])
            with col6:
                enviado = st.form_submit_button("✅ Guardar Reclamo", use_container_width=True)

        if enviado:
            if not nro_cliente:
                st.error("⚠️ Debes ingresar un número de cliente.")
            elif not atendido_por.strip():
                st.error("⚠️ El campo 'Atendido por' es obligatorio.")
            else:
                with st.spinner("Guardando reclamo..."):
                    argentina = pytz.timezone("America/Argentina/Buenos_Aires")
                    fecha_hora = datetime.now(argentina).strftime("%Y-%m-%d %H:%M:%S")

                    fila_reclamo = [
                        fecha_hora, nro_cliente, sector, nombre.upper(),
                        direccion.upper(), telefono, tipo_reclamo,
                        detalles.upper(), "Pendiente", "", precinto, atendido_por.upper()
                    ]

                    success, error = update_sheet_data(sheet_reclamos, fila_reclamo, is_batch=False)
                    
                    if success:
                        st.success("✅ Reclamo guardado correctamente.")
                        
                        # Agregar cliente si es nuevo
                        if nro_cliente not in df_clientes["Nº Cliente"].values:
                            fila_cliente = [nro_cliente, sector, nombre.upper(), direccion.upper(), telefono, precinto]
                            success_cliente, error_cliente = update_sheet_data(sheet_clientes, fila_cliente, is_batch=False)
                            if success_cliente:
                                st.info("🗂️ Nuevo cliente agregado a la base de datos.")
                        
                        # Limpiar cache para refrescar datos
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Error al guardar: {error}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN 2: RECLAMOS CARGADOS ---
elif opcion == "Reclamos cargados":
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("📊 Gestión de reclamos cargados")

    try:
        df = df_reclamos.copy()
        df["Nº Cliente"] = df["Nº Cliente"].astype(str).str.strip()
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        
        # Merge con datos de clientes
        df = pd.merge(df, df_clientes[["Nº Cliente", "N° de Precinto"]], 
                     on="Nº Cliente", how="left", suffixes=("", "_cliente"))
        
        df["Fecha y hora"] = pd.to_datetime(df["Fecha y hora"], errors="coerce")
        df = df.sort_values("Fecha y hora", ascending=False)

        # Filtros mejorados
        st.markdown("#### 🔍 Filtros de búsqueda")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filtro_estado = st.selectbox("Estado", ["Todos"] + sorted(df["Estado"].unique()))
        with col2:
            filtro_sector = st.selectbox("Sector", ["Todos"] + sorted(df["Sector"].unique()))
        with col3:
            filtro_tipo = st.selectbox("Tipo de reclamo", ["Todos"] + sorted(df["Tipo de reclamo"].unique()))

        # Aplicar filtros
        if filtro_estado != "Todos":
            df = df[df["Estado"] == filtro_estado]
        if filtro_sector != "Todos":
            df = df[df["Sector"] == filtro_sector]
        if filtro_tipo != "Todos":
            df = df[df["Tipo de reclamo"] == filtro_tipo]

        st.markdown(f"**Mostrando {len(df)} reclamos**")

        # Editor de datos mejorado
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key="editor",
            column_config={
                "Estado": st.column_config.SelectboxColumn(
                    "Estado", 
                    options=["Pendiente", "En curso", "Resuelto"],
                    help="Cambia el estado del reclamo"
                ),
                "Técnico": st.column_config.TextColumn(
                    "Técnico asignado",
                    help="Técnicos asignados al reclamo"
                ),
                "N° de Precinto": st.column_config.TextColumn(
                    "N° de Precinto",
                    help="Número de precinto del cliente"
                )
            },
            hide_index=True
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Guardar cambios", use_container_width=True):
                with st.spinner("Guardando cambios..."):
                    try:
                        # Procesar técnicos si están en formato lista
                        if not edited_df.empty and isinstance(edited_df.iloc[0]["Técnico"], list):
                            edited_df["Técnico"] = edited_df["Técnico"].apply(
                                lambda lista: ", ".join(lista) if isinstance(lista, list) else lista
                            )

                        edited_df = edited_df.astype(str)

                        # Actualizar hoja de reclamos
                        data_to_update = [edited_df.columns.tolist()] + edited_df.values.tolist()
                        success, error = update_sheet_data(sheet_reclamos, data_to_update, is_batch=True)
                        
                        if success:
                            st.success("✅ Cambios guardados correctamente.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al guardar: {error}")
                            
                    except Exception as e:
                        st.error(f"❌ Error al procesar los cambios: {e}")

    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar los datos: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN 3: HISTORIAL POR CLIENTE ---
elif opcion == "Historial por cliente":
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("📜 Historial de reclamos por cliente")
    
    historial_cliente = st.text_input("🔍 Ingresá N° de Cliente para ver su historial", placeholder="Número de cliente").strip()

    if historial_cliente:
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
        historial = df_reclamos[df_reclamos["Nº Cliente"] == historial_cliente]

        if not historial.empty:
            historial["Fecha y hora"] = pd.to_datetime(historial["Fecha y hora"], errors="coerce")
            historial = historial.sort_values("Fecha y hora", ascending=False)

            st.success(f"🔎 Se encontraron {len(historial)} reclamos para el cliente {historial_cliente}.")
            
            # Mostrar información del cliente
            cliente_info = df_clientes[df_clientes["Nº Cliente"] == historial_cliente]
            if not cliente_info.empty:
                cliente = cliente_info.iloc[0]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"👤 **{cliente['Nombre']}**")
                with col2:
                    st.info(f"📍 {cliente['Dirección']}")
                with col3:
                    st.info(f"📞 {cliente['Teléfono']}")
            
            st.dataframe(
                historial[["Fecha y hora", "Tipo de reclamo", "Estado", "Técnico", "N° de Precinto", "Detalles"]],
                use_container_width=True
            )
        else:
            st.info("❕ Este cliente no tiene reclamos registrados.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN 4: EDITAR CLIENTE ---
elif opcion == "Editar cliente":
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("🛠️ Editar datos de un cliente")
    
    cliente_editar = st.text_input("🔎 Ingresá N° de Cliente a editar", placeholder="Número de cliente").strip()

    if cliente_editar:
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        cliente_row = df_clientes[df_clientes["Nº Cliente"] == cliente_editar]

        if not cliente_row.empty:
            cliente_actual = cliente_row.squeeze()
            
            with st.form("editar_cliente_form"):
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_sector = st.text_input("🏙️ Sector", value=cliente_actual["Sector"])
                    nuevo_nombre = st.text_input("👤 Nombre", value=cliente_actual["Nombre"])
                    nueva_direccion = st.text_input("📍 Dirección", value=cliente_actual["Dirección"])
                with col2:
                    nuevo_telefono = st.text_input("📞 Teléfono", value=cliente_actual["Teléfono"])
                    nuevo_precinto = st.text_input("🔒 N° de Precinto", value=cliente_actual.get("N° de Precinto", ""))

                actualizar = st.form_submit_button("💾 Actualizar datos del cliente", use_container_width=True)

            if actualizar:
                with st.spinner("Actualizando cliente..."):
                    try:
                        index = cliente_row.index[0] + 2  # +2 porque la hoja empieza en fila 2
                        
                        updates = [
                            {"range": f"B{index}", "values": [[nuevo_sector.upper()]]},
                            {"range": f"C{index}", "values": [[nuevo_nombre.upper()]]},
                            {"range": f"D{index}", "values": [[nueva_direccion.upper()]]},
                            {"range": f"E{index}", "values": [[nuevo_telefono]]},
                            {"range": f"F{index}", "values": [[nuevo_precinto]]}
                        ]
                        
                        success, error = batch_update_sheet(sheet_clientes, updates)
                        
                        if success:
                            st.success("✅ Cliente actualizado correctamente.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al actualizar: {error}")
                            
                    except Exception as e:
                        st.error(f"❌ Error al actualizar: {e}")
        else:
            st.warning("⚠️ Cliente no encontrado.")

    # --- NUEVO FORMULARIO PARA CARGAR CLIENTE DESDE CERO ---
    st.markdown("---")
    st.subheader("🆕 Cargar nuevo cliente")

    with st.form("form_nuevo_cliente"):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nro = st.text_input("🔢 N° de Cliente (nuevo)", placeholder="Número único").strip()
            nuevo_sector = st.text_input("🏙️ Sector", placeholder="Zona o sector")
            nuevo_nombre = st.text_input("👤 Nombre", placeholder="Nombre completo")
        with col2:
            nueva_direccion = st.text_input("📍 Dirección", placeholder="Dirección completa")
            nuevo_telefono = st.text_input("📞 Teléfono", placeholder="Número de contacto")
            nuevo_precinto = st.text_input("🔒 N° de Precinto (opcional)", placeholder="Número de precinto")

        guardar_cliente = st.form_submit_button("💾 Guardar nuevo cliente", use_container_width=True)

        if guardar_cliente:
            if not nuevo_nro or not nuevo_nombre:
                st.error("⚠️ Debés ingresar al menos el N° de cliente y el nombre.")
            elif nuevo_nro in df_clientes["Nº Cliente"].values:
                st.warning("⚠️ Este cliente ya existe.")
            else:
                with st.spinner("Guardando nuevo cliente..."):
                    try:
                        nueva_fila = [
                            nuevo_nro, nuevo_sector.upper(), nuevo_nombre.upper(),
                            nueva_direccion.upper(), nuevo_telefono, nuevo_precinto
                        ]
                        
                        success, error = update_sheet_data(sheet_clientes, nueva_fila, is_batch=False)
                        
                        if success:
                            st.success("✅ Nuevo cliente agregado correctamente.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al guardar: {error}")
                            
                    except Exception as e:
                        st.error(f"❌ Error al guardar: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN 5: IMPRIMIR RECLAMOS ---
elif opcion == "Imprimir reclamos":
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("🖨️ Seleccionar reclamos para imprimir (formato técnico compacto)")

    try:
        df_pdf = df_reclamos.copy()
        df_merged = pd.merge(df_pdf, df_clientes[["Nº Cliente", "N° de Precinto"]], on="Nº Cliente", how="left")

        # Mostrar reclamos pendientes
        st.info("🕒 Reclamos pendientes de resolución")
        df_pendientes = df_merged[df_merged["Estado"] == "Pendiente"]
        if not df_pendientes.empty:
            st.dataframe(df_pendientes[["Fecha y hora", "Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]], use_container_width=True)
        else:
            st.success("✅ No hay reclamos pendientes actualmente.")

        solo_pendientes = st.checkbox("🧾 Mostrar solo reclamos pendientes para imprimir")

        # --- IMPRIMIR POR TIPO DE RECLAMO ---
        st.markdown("### 🧾 Imprimir reclamos por tipo")

        tipos_disponibles = sorted(df_merged["Tipo de reclamo"].unique())
        tipos_seleccionados = st.multiselect("Seleccioná tipos de reclamo a imprimir", tipos_disponibles)

        if tipos_seleccionados:
            reclamos_filtrados = df_merged[
                (df_merged["Estado"] == "Pendiente") & 
                (df_merged["Tipo de reclamo"].isin(tipos_seleccionados))
            ]

            if not reclamos_filtrados.empty:
                st.success(f"Se encontraron {len(reclamos_filtrados)} reclamos pendientes de los tipos seleccionados.")

                if st.button("📄 Generar PDF de reclamos por tipo"):
                    with st.spinner("Generando PDF..."):
                        buffer = io.BytesIO()
                        c = canvas.Canvas(buffer, pagesize=A4)
                        width, height = A4
                        y = height - 40

                        for i, (_, reclamo) in enumerate(reclamos_filtrados.iterrows()):
                            c.setFont("Helvetica-Bold", 16)
                            c.drawString(40, y, f"Reclamo #{reclamo['Nº Cliente']}")
                            y -= 15
                            c.setFont("Helvetica", 12)
                            
                            lineas = [
                                f"Fecha: {reclamo['Fecha y hora']} - Cliente: {reclamo['Nombre']} ({reclamo['Nº Cliente']})",
                                f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                                f"Sector: {reclamo['Sector']} - Precinto: {reclamo.get('N° de Precinto', '')} - Técnico: {reclamo['Técnico']}",
                                f"Tipo: {reclamo['Tipo de reclamo']}",
                                f"Detalles: {reclamo['Detalles'][:80]}..." if len(reclamo['Detalles']) > 80 else f"Detalles: {reclamo['Detalles']}",
                            ]
                            
                            for linea in lineas:
                                c.drawString(40, y, linea)
                                y -= 12
                            y -= 8
                            c.drawString(40, y, "Firma técnico: _____________________________")
                            y -= 25
                            
                            if y < 150 and i < len(reclamos_filtrados) - 1:
                                c.showPage()
                                y = height - 40

                        c.save()
                        buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Descargar PDF filtrado por tipo",
                            data=buffer,
                            file_name="reclamos_filtrados_por_tipo.pdf",
                            mime="application/pdf"
                        )
            else:
                st.info("No hay reclamos pendientes para los tipos seleccionados.")

        # --- SELECCIÓN MANUAL ---
        st.markdown("### 📋 Selección manual de reclamos")
        
        if solo_pendientes:
            df_merged = df_merged[df_merged["Estado"] == "Pendiente"]

        selected = st.multiselect(
            "Seleccioná los reclamos a imprimir:", 
            df_merged.index,
            format_func=lambda x: f"{df_merged.at[x, 'Nº Cliente']} - {df_merged.at[x, 'Nombre']}"
        )

        if st.button("📄 Generar PDF con seleccionados") and selected:
            with st.spinner("Generando PDF..."):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4
                y = height - 40

                for i, idx in enumerate(selected):
                    reclamo = df_merged.loc[idx]
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(40, y, f"Reclamo #{reclamo['Nº Cliente']}")
                    y -= 15
                    c.setFont("Helvetica", 12)
                    
                    lineas = [
                        f"Fecha: {reclamo['Fecha y hora']} - Cliente: {reclamo['Nombre']} ({reclamo['Nº Cliente']})",
                        f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                        f"Sector: {reclamo['Sector']} - Precinto: {reclamo.get('N° de Precinto', '')} - Técnico: {reclamo['Técnico']}",
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
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN 6: SEGUIMIENTO TÉCNICO ---
elif opcion == "Seguimiento técnico":
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("👷 Seguimiento técnico del reclamo")
    
    cliente_input = st.text_input("🔍 Ingresá el N° de Cliente para actualizar su reclamo", placeholder="Número de cliente").strip()

    if cliente_input:
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
        df_filtrado = df_reclamos[
            (df_reclamos["Nº Cliente"] == cliente_input) &
            (df_reclamos["Estado"].isin(["Pendiente", "En curso"]))
        ]

        if df_filtrado.empty:
            st.warning("❕ Este cliente no tiene reclamos pendientes o en curso.")
        else:
            df_filtrado["Fecha y hora"] = pd.to_datetime(df_filtrado["Fecha y hora"], errors="coerce")
            df_filtrado = df_filtrado.dropna(subset=["Fecha y hora"])

            if df_filtrado.empty:
                st.warning("❕ Este cliente tiene reclamos sin fecha válida. No se puede determinar el más reciente.")
            else:
                df_ordenado = df_filtrado.sort_values("Fecha y hora", ascending=False)
                reclamo_actual = df_ordenado.iloc[0]
                index_reclamo = df_ordenado.index[0] + 2  # +2 por encabezado y base 1 en Sheets

                # Mostrar información del reclamo
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"📅 **Fecha:** {reclamo_actual['Fecha y hora']}")
                    st.info(f"📌 **Tipo:** {reclamo_actual['Tipo de reclamo']}")
                    st.info(f"📍 **Dirección:** {reclamo_actual['Dirección']}")
                with col2:
                    st.info(f"🔒 **Precinto:** {reclamo_actual.get('N° de Precinto', 'No asignado')}")
                    st.info(f"📞 **Teléfono:** {reclamo_actual['Teléfono']}")
                    st.info(f"👤 **Atendido por:** {reclamo_actual['Atendido por']}")

                st.markdown(f"**📄 Detalles:** {reclamo_actual['Detalles']}")

                # Formulario de actualización
                with st.form("actualizar_reclamo"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nuevo_estado = st.selectbox(
                            "⚙️ Cambiar estado",
                            ["Pendiente", "En curso", "Resuelto"],
                            index=["Pendiente", "En curso", "Resuelto"].index(reclamo_actual["Estado"])
                        )
                    
                    with col2:
                        tecnicos_actuales = [t.strip() for t in str(reclamo_actual.get("Técnico", "")).split(",") if t.strip()]
                        tecnicos_actuales_filtrados = [
                            t for t in TECNICOS_DISPONIBLES if t.lower() in [x.lower() for x in tecnicos_actuales]
                        ]

                        nuevos_tecnicos = st.multiselect(
                            "👷 Técnicos asignados",
                            TECNICOS_DISPONIBLES,
                            default=tecnicos_actuales_filtrados
                        )

                    actualizar = st.form_submit_button("💾 Actualizar reclamo", use_container_width=True)

                if actualizar:
                    if not nuevos_tecnicos:
                        st.warning("⚠️ Debes asignar al menos un técnico para actualizar el reclamo.")
                    else:
                        with st.spinner("Actualizando reclamo..."):
                            try:
                                updates = [
                                    {"range": f"I{index_reclamo}", "values": [[nuevo_estado]]},
                                    {"range": f"J{index_reclamo}", "values": [[", ".join(nuevos_tecnicos).upper()]]}
                                ]
                                
                                success, error = batch_update_sheet(sheet_reclamos, updates)
                                
                                if success:
                                    st.success("✅ Reclamo actualizado correctamente.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al actualizar: {error}")
                                    
                            except Exception as e:
                                st.error(f"❌ Error al actualizar: {e}")

    # --- IMPRIMIR RECLAMOS EN CURSO ---
    st.markdown("---")
    st.markdown("### 🖨️ Imprimir reclamos 'En curso' (vista compacta optimizada)")

    reclamos_en_curso = df_reclamos[df_reclamos["Estado"] == "En curso"].copy()

    if reclamos_en_curso.empty:
        st.info("No hay reclamos en curso para imprimir.")
    else:
        reclamos_en_curso["Fecha y hora"] = pd.to_datetime(reclamos_en_curso["Fecha y hora"], errors="coerce")
        reclamos_en_curso = reclamos_en_curso.dropna(subset=["Fecha y hora"])
        reclamos_en_curso = reclamos_en_curso.sort_values("Fecha y hora", ascending=False)

        st.dataframe(
            reclamos_en_curso[["Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]],
            use_container_width=True
        )

        if st.button("📄 Generar PDF de reclamos en curso (más por hoja)"):
            with st.spinner("Generando PDF optimizado..."):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                x_left = 40
                x_right = width / 2 + 10
                y = height - 40
                columna_izquierda = True

                for idx, reclamo in reclamos_en_curso.iterrows():
                    x = x_left if columna_izquierda else x_right

                    # Fuente más chica
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(x, y, f"{reclamo['Nº Cliente']} - {reclamo['Nombre']}")
                    y -= 10
                    c.setFont("Helvetica", 8)
                    c.drawString(x, y, f"📌 {reclamo['Tipo de reclamo']}")
                    y -= 9
                    c.drawString(x, y, f"👷 {reclamo['Técnico']}")
                    y -= 20  # Menos espacio entre bloques

                    if not columna_izquierda:
                        y -= 3
                    columna_izquierda = not columna_izquierda

                    if y < 60:
                        c.showPage()
                        y = height - 40
                        columna_izquierda = True

                c.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Descargar PDF optimizado",
                    data=buffer,
                    file_name="reclamos_en_curso_opt.pdf",
                    mime="application/pdf"
                )
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN 7: CIERRE DE RECLAMOS ---
elif opcion == "Cierre de Reclamos":
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("✅ Cierre de reclamos en curso")

    df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
    df_reclamos["Técnico"] = df_reclamos["Técnico"].astype(str).fillna("")

    en_curso = df_reclamos[df_reclamos["Estado"] == "En curso"].copy()

    if en_curso.empty:
        st.info("📭 No hay reclamos en curso en este momento.")
    else:
        # Filtro por técnico
        tecnicos_unicos = sorted(set(", ".join(en_curso["Técnico"].tolist()).split(", ")))
        tecnicos_seleccionados = st.multiselect("👷 Filtrar por técnico asignado", tecnicos_unicos)

        if tecnicos_seleccionados:
            en_curso = en_curso[
                en_curso["Técnico"].apply(
                    lambda t: any(tecnico in t for tecnico in tecnicos_seleccionados)
                )
            ]

        st.write("### 📋 Reclamos en curso:")
        st.dataframe(en_curso[["Fecha y hora", "Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]], use_container_width=True)

        st.markdown("### ✏️ Acciones por reclamo:")

        for i, row in en_curso.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 2])
                
                with col1:
                    st.markdown(f"**#{row['Nº Cliente']} - {row['Nombre']}**")
                    st.markdown(f"📌 {row['Tipo de reclamo']}")
                    st.markdown(f"👷 {row['Técnico']}")

                    # Campo de precinto editable
                    cliente_id = str(row["Nº Cliente"]).strip()
                    cliente_info = df_clientes[df_clientes["Nº Cliente"] == cliente_id]
                    precinto_actual = cliente_info["N° de Precinto"].values[0] if not cliente_info.empty else ""
                    nuevo_precinto = st.text_input("🔒 Precinto", value=precinto_actual, key=f"precinto_{i}")

                with col2:
                    if st.button("✅ Resuelto", key=f"resolver_{i}", use_container_width=True):
                        with st.spinner("Cerrando reclamo..."):
                            try:
                                argentina = pytz.timezone("America/Argentina/Buenos_Aires")
                                fecha_resolucion = datetime.now(argentina).strftime("%Y-%m-%d %H:%M:%S")

                                updates = [{"range": f"I{i + 2}", "values": [["Resuelto"]]}]
                                
                                # Si hay columna de fecha de resolución, agregarla
                                if len(COLUMNAS_RECLAMOS) > 12:
                                    updates.append({"range": f"M{i + 2}", "values": [[fecha_resolucion]]})

                                success, error = batch_update_sheet(sheet_reclamos, updates)

                                if success:
                                    # Actualizar precinto si se ingresó uno
                                    if nuevo_precinto.strip() and not cliente_info.empty:
                                        index_real = cliente_info.index[0] + 2
                                        update_precinto = [{"range": f"F{index_real}", "values": [[nuevo_precinto.strip()]]}]
                                        batch_update_sheet(sheet_clientes, update_precinto)
                                    
                                    st.success(f"🟢 Reclamo de {row['Nombre']} cerrado correctamente.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al actualizar: {error}")
                                    
                            except Exception as e:
                                st.error(f"❌ Error al actualizar: {e}")

                with col3:
                    if st.button("↩️ Pendiente", key=f"volver_{i}", use_container_width=True):
                        with st.spinner("Cambiando estado..."):
                            try:
                                updates = [
                                    {"range": f"I{i + 2}", "values": [["Pendiente"]]},
                                    {"range": f"J{i + 2}", "values": [[""]]}
                                ]
                                
                                success, error = batch_update_sheet(sheet_reclamos, updates)
                                
                                if success:
                                    st.success(f"🔄 Reclamo de {row['Nombre']} vuelto a PENDIENTE y técnicos limpiados.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al actualizar: {error}")
                                    
                            except Exception as e:
                                st.error(f"❌ Error al actualizar: {e}")

                st.divider()
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("---")
st.markdown("### 📊 Estadísticas de la sesión")
api_stats = api_manager.get_api_stats()
col1, col2 = st.columns(2)
with col1:
    st.metric("🔄 Llamadas a la API", api_stats['total_calls'])
with col2:
    if api_stats['last_call'] > 0:
        last_call_time = datetime.fromtimestamp(api_stats['last_call']).strftime("%H:%M:%S")
        st.metric("🕐 Última llamada", last_call_time)