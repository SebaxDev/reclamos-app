"""
Aplicación principal de gestión de reclamos optimizada
Versión 2.0 - Con manejo robusto de API y session_state
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
from components.auth import has_permission, check_authentication, render_login, render_user_info
from components.navigation import render_navigation, render_user_info
from components.metrics_dashboard import render_metrics_dashboard
from utils.styles import get_main_styles
from utils.data_manager import safe_get_sheet_data, safe_normalize, update_sheet_data, batch_update_sheet
from utils.api_manager import api_manager, init_api_session_state  # Import modificado
from config.settings import *
from components.user_widget import show_user_widget

# --------------------------------------------------
# INICIALIZACIÓN GARANTIZADA
# --------------------------------------------------
if 'app_initialized' not in st.session_state:
    init_api_session_state()  # Inicializa API
    st.session_state.app_initialized = True  # Marcar app como inicializada
    st.session_state.df_reclamos = pd.DataFrame()  # Dataframes iniciales
    st.session_state.df_clientes = pd.DataFrame()
# --------------------------
# INICIALIZACIONES
# --------------------------

# Configuración de página
st.set_page_config(
    page_title="Fusion Reclamos App",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 1. Función para detectar modo oscuro del sistema 
def is_system_dark_mode():
    import platform
    if platform.system() == "Windows":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
            return value == 0  # 0 = oscuro, 1 = claro
        except:
            return False
    elif platform.system() == "Darwin":  # macOS
        import subprocess
        try:
            result = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'], capture_output=True, text=True)
            return "Dark" in result.stdout
        except:
            return False
    else:  # Linux/otros
        return False

# 2. Inicializar modo oscuro
if 'modo_oscuro' not in st.session_state:
    st.session_state.modo_oscuro = is_system_dark_mode()

# 3. Sidebar con toggle
with st.sidebar:
    st.session_state.modo_oscuro = st.toggle(
        "🌙 Modo oscuro",
        value=st.session_state.modo_oscuro,
        key="dark_mode_toggle"
    )
    show_user_widget()

# 4. Aplicar estilos
st.markdown(get_main_styles(dark_mode=st.session_state.modo_oscuro), unsafe_allow_html=True)

# --------------------------
# CONEXIÓN CON GOOGLE SHEETS
# --------------------------

@st.cache_resource
def init_google_sheets():
    """Inicializa la conexión con Google Sheets con manejo de errores mejorado"""
    try:
        # Cargar credenciales de forma segura
        if 'gcp_service_account' not in st.secrets:
            raise ValueError("No se encontraron credenciales en st.secrets")
            
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"]
        )
        
        client = gspread.authorize(credentials)
        
        # Validar existencia de las hojas
        try:
            sheet_reclamos = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_RECLAMOS)
            sheet_clientes = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_CLIENTES)
            sheet_usuarios = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_USUARIOS)
            return sheet_reclamos, sheet_clientes, sheet_usuarios
        except gspread.WorksheetNotFound as e:
            raise ValueError(f"Hoja no encontrada: {str(e)}")
            
    except Exception as e:
        st.error(f"🔴 Error crítico al conectar con Google Sheets: {str(e)}")
        st.stop()
        return None, None, None

# Inicializar conexión con Google Sheets
with st.spinner("Conectando con Google Sheets..."):
    sheet_reclamos, sheet_clientes, sheet_usuarios = init_google_sheets()
    if not all([sheet_reclamos, sheet_clientes, sheet_usuarios]):
        st.stop()

# Verificar autenticación
if not check_authentication():
    render_login(sheet_usuarios)
    st.stop()

# Obtener información del usuario actual
user_info = st.session_state.auth.get('user_info', {})
user_role = user_info.get('rol', '')
# --------------------------
# CARGA DE DATOS
# --------------------------

@st.cache_data(ttl=30, show_spinner="Cargando datos...")
def cargar_datos():
    """Carga datos de Google Sheets con manejo de errores"""
    try:
        # Cargar datos de las hojas
        df_reclamos = safe_get_sheet_data(sheet_reclamos, COLUMNAS_RECLAMOS)
        df_clientes = safe_get_sheet_data(sheet_clientes, COLUMNAS_CLIENTES)
        df_usuarios = safe_get_sheet_data(sheet_usuarios, COLUMNAS_USUARIOS)
        
        if df_reclamos.empty or df_clientes.empty:
            st.warning("⚠️ Algunas hojas están vacías")
        
        # Normalizar columnas clave
        for col in ["Nº Cliente", "N° de Precinto"]:
            df_clientes = safe_normalize(df_clientes, col)
            df_reclamos = safe_normalize(df_reclamos, col)
            
        return df_reclamos, df_clientes, df_usuarios
        
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()  # Retorna 3 DataFrames vacíos

# Cargar datos y guardar en session_state
df_reclamos, df_clientes, df_usuarios = cargar_datos()
st.session_state.df_reclamos = df_reclamos
st.session_state.df_clientes = df_clientes

# --------------------------
# INTERFAZ PRINCIPAL
# --------------------------
st.markdown("---")
# Header
st.title("📋 Fusion Reclamos App")

# Dashboard de métricas
render_metrics_dashboard(df_reclamos)
st.divider()

# Navegación
opcion = render_navigation()

# --------------------------
# SECCIÓN 1: INICIO - NUEVO RECLAMO
# --------------------------

if opcion == "Inicio" and has_permission('inicio'):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("📝 Cargar nuevo reclamo")

    nro_cliente = st.text_input("🔢 N° de Cliente", placeholder="Ingresa el número de cliente").strip()
    cliente_existente = None
    formulario_bloqueado = False

    # Validación de cliente existente
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

            reclamo_vigente = reclamos_activos.sort_values("Fecha y hora", ascending=False).iloc[0]

            with st.expander("🔍 Ver detalles del reclamo activo"):
                st.markdown(f"**📅 Fecha del reclamo:** {reclamo_vigente['Fecha y hora']}")
                st.markdown(f"**👤 Cliente:** {reclamo_vigente['Nombre']}")
                st.markdown(f"**📌 Tipo de reclamo:** {reclamo_vigente['Tipo de reclamo']}")
                st.markdown(f"**📝 Detalles:** {reclamo_vigente['Detalles'][:250]}{'...' if len(reclamo_vigente['Detalles']) > 250 else ''}")
                st.markdown(f"**⚙️ Estado:** {reclamo_vigente['Estado']}")
                st.markdown(f"**👷 Técnico asignado:** {reclamo_vigente.get('Técnico', 'No asignado') or 'No asignado'}")
                st.markdown(f"**🙍‍♂️ Atendido por:** {reclamo_vigente.get('Atendido por', 'N/A')}")

    if not formulario_bloqueado:
        with st.form("reclamo_formulario", clear_on_submit=True):
            col1, col2 = st.columns(2)

            # Campos del formulario con valores por defecto si el cliente existe
            if cliente_existente:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", value=cliente_existente.get("Sector", ""))
                    direccion = st.text_input("📍 Dirección", value=cliente_existente.get("Dirección", ""))
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", value=cliente_existente.get("Nombre", ""))
                    telefono = st.text_input("📞 Teléfono", value=cliente_existente.get("Teléfono", ""))
            else:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", placeholder="Coloque número de sector")
                    direccion = st.text_input("📍 Dirección", placeholder="Dirección completa")
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", placeholder="Nombre completo")
                    telefono = st.text_input("📞 Teléfono", placeholder="Número de contacto")

            tipo_reclamo = st.selectbox("📌 Tipo de Reclamo", TIPOS_RECLAMO)
            detalles = st.text_area("📝 Detalles del Reclamo", placeholder="Describe el problema o solicitud...", height=100)

            col3, col4 = st.columns(2)
            with col3:
                precinto = st.text_input("🔒 N° de Precinto (opcional)", 
                                       value=cliente_existente.get("N° de Precinto", "").strip() if cliente_existente else "",
                                       placeholder="Número de precinto")
            with col4:
                atendido_por = st.text_input("👤 Atendido por", placeholder="Nombre de quien atiende", value=st.session_state.get("current_user", ""))

            enviado = st.form_submit_button("✅ Guardar Reclamo", use_container_width=True)

        if enviado:
            # Validación de campos obligatorios
            if not nro_cliente:
                st.error("⚠️ Debes ingresar un número de cliente.")
            elif not all([nombre.strip(), direccion.strip(), atendido_por.strip()]):
                st.error("⚠️ Los campos marcados con asterisco (*) son obligatorios.")
            else:
                with st.spinner("Guardando reclamo..."):
                    try:
                        # Preparar datos
                        argentina = pytz.timezone("America/Argentina/Buenos_Aires")
                        fecha_hora = datetime.now(argentina).strftime("%d/%m/%Y %H:%M:%S")

                        fila_reclamo = [
                            fecha_hora, nro_cliente, sector, nombre.upper(),
                            direccion.upper(), telefono, tipo_reclamo,
                            detalles.upper(), "Pendiente", "", precinto, atendido_por.upper()
                        ]

                        # Operación segura con API Manager
                        success, error = api_manager.safe_sheet_operation(
                            sheet_reclamos.append_row,
                            fila_reclamo
                        )

                        if success:
                            st.success("✅ Reclamo guardado correctamente.")

                            # Agregar cliente si es nuevo
                            if nro_cliente not in df_clientes["Nº Cliente"].values:
                                fila_cliente = [nro_cliente, sector, nombre.upper(), direccion.upper(), telefono, precinto]
                                success_cliente, _ = api_manager.safe_sheet_operation(
                                    sheet_clientes.append_row,
                                    fila_cliente
                                )
                                if success_cliente:
                                    st.info("🗂️ Nuevo cliente agregado a la base de datos.")

                            # Limpiar cache y refrescar
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al guardar: {error}")
                    except Exception as e:
                        st.error(f"❌ Error inesperado: {str(e)}")

    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# SECCIÓN 2: RECLAMOS CARGADOS
# ----------------------------
elif opcion == "Reclamos cargados" and has_permission('reclamos_cargados'):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("📊 Gestión de reclamos cargados")

    try:
        # Copia del dataframe original
        df = df_reclamos.copy()

        # Normalización de columnas clave
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        df["Nº Cliente"] = df["Nº Cliente"].astype(str).str.strip()

        # Merge con datos del cliente
        df = pd.merge(df, df_clientes[["Nº Cliente", "N° de Precinto", "Teléfono"]], 
                      on="Nº Cliente", how="left", suffixes=("", "_cliente"))

        # Procesamiento de fechas
        df["Fecha y hora"] = pd.to_datetime(df["Fecha y hora"], errors="coerce")
        df = df.sort_values("Fecha y hora", ascending=False)

        # ==============================
        # MINI PANEL: Reclamos por tipo
        # ==============================
        df_activos = df[df["Estado"].isin(["Pendiente", "En curso"])]

        if not df_activos.empty:
            conteo_por_tipo = df_activos["Tipo de reclamo"].value_counts().sort_index()

            st.markdown("#### 📊 Distribución de reclamos activos por tipo")
            st.markdown('<div style="margin-top: -10px; margin-bottom: 10px;">', unsafe_allow_html=True)

            tipos = list(conteo_por_tipo.index)
            cantidad = list(conteo_por_tipo.values)

            cols_per_row = 4
            for i in range(0, len(tipos), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(tipos):
                        tipo = tipos[i + j]
                        cant = cantidad[i + j]
                        
                        # Estilos dinámicos
                        color_cantidad = "#dc3545" if cant > 10 else "#0d6efd"  # rojo si > 10
                        font_size = "1.4rem" if cant > 10 else "1.2rem"
                        bg_color = "#f8f9fa"
            
                        with col:
                            st.markdown(f"""
                                <div style="
                                    text-align: center;
                                    padding: 5px 4px;
                                    border-radius: 8px;
                                    background-color: {bg_color};
                                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                                    margin-bottom: 8px;
                                ">
                                    <h5 style="margin: 0; font-size: 0.70rem; color: #6c757d;">{tipo}</h5>
                                    <h4 style="margin: 2px 0 0 0; color: {color_cantidad}; font-size: {font_size};">{cant}</h4>
                                </div>
                            """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # ==============================
        # FILTROS
        # ==============================
        st.markdown("#### 🔍 Filtros de búsqueda")
        col1, col2, col3 = st.columns(3)

        with col1:
            filtro_estado = st.selectbox("Estado", ["Todos"] + sorted(df["Estado"].unique()))
        with col2:
            filtro_sector = st.selectbox("Sector", ["Todos"] + sorted(df["Sector"].unique()))
        with col3:
            filtro_tipo = st.selectbox("Tipo de reclamo", ["Todos"] + sorted(df["Tipo de reclamo"].unique()))

        # Aplicar filtros
        df_filtrado = df.copy()
        if filtro_estado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Estado"] == filtro_estado]
        if filtro_sector != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Sector"] == filtro_sector]
        if filtro_tipo != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Tipo de reclamo"] == filtro_tipo]

        st.markdown(f"**Mostrando {len(df_filtrado)} reclamos**")

        # ==============================
        # TABLA NO EDITABLE
        # ==============================
        columnas_visibles = ["Fecha y hora", "Nº Cliente", "Nombre", "Sector", "Tipo de reclamo", "Teléfono"]
        st.dataframe(df_filtrado[columnas_visibles], use_container_width=True, hide_index=True)

        # ==============================
        # FORMULARIO DE EDICIÓN MANUAL
        # ==============================
        st.markdown("---")
        st.markdown("### ✏️ Editar un reclamo puntual")

        # Selector por Nº Cliente - Nombre
        df_filtrado["label_selector"] = df_filtrado["Nº Cliente"] + " - " + df_filtrado["Nombre"]
        selector = st.selectbox(
            "Seleccioná un reclamo por Nº de Cliente y Nombre",
            [""] + df_filtrado["label_selector"].tolist()
        )

        if selector:
            nro_cliente = selector.split(" - ")[0]
            reclamo_actual = df[df["Nº Cliente"] == nro_cliente].iloc[0]

            nueva_direccion = st.text_input("Dirección", value=reclamo_actual.get("Dirección", ""))
            nuevo_telefono = st.text_input("Teléfono", value=reclamo_actual.get("Teléfono", ""))
            nuevo_tipo = st.selectbox("Tipo de reclamo", sorted(df["Tipo de reclamo"].unique()), 
                                      index=sorted(df["Tipo de reclamo"].unique()).index(reclamo_actual["Tipo de reclamo"]))
            nuevos_detalles = st.text_area("Detalles del reclamo", value=reclamo_actual.get("Detalles", ""), height=100)
            nuevo_precinto = st.text_input("N° de Precinto", value=reclamo_actual.get("N° de Precinto", ""))

            if st.button("💾 Guardar cambios", key="guardar_reclamo_individual", use_container_width=True):
                with st.spinner("Guardando cambios..."):
                    try:
                        idx_original = df[df["Nº Cliente"] == nro_cliente].index[0]

                        df.loc[idx_original, "Dirección"] = nueva_direccion
                        df.loc[idx_original, "Teléfono"] = nuevo_telefono
                        df.loc[idx_original, "Tipo de reclamo"] = nuevo_tipo
                        df.loc[idx_original, "Detalles"] = nuevos_detalles
                        df.loc[idx_original, "N° de Precinto"] = nuevo_precinto

                        df = df.astype(str)

                        data_to_update = [df.columns.tolist()] + df.values.tolist()
                        success, error = api_manager.safe_sheet_operation(
                            sheet_reclamos.update,
                            data_to_update,
                            is_batch=True
                        )

                        if success:
                            st.success("✅ Reclamo actualizado correctamente.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al guardar: {error}")
                    except Exception as e:
                        st.error(f"❌ Error al procesar: {str(e)}")

    except Exception as e:
        st.error(f"⚠️ Error en la gestión de reclamos: {str(e)}")

    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# SECCIÓN 3: HISTORIAL POR CLIENTE
# --------------------------

elif opcion == "Historial por cliente" and has_permission('historial_cliente'):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("📜 Historial de reclamos por cliente")
    
    historial_cliente = st.text_input("🔍 Ingresá N° de Cliente para ver su historial", 
                                     placeholder="Número de cliente", 
                                     key="input_historial").strip()

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
                with st.expander("📋 Información del Cliente", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**👤 Nombre:** {cliente['Nombre']}")
                    with col2:
                        st.markdown(f"**📍 Dirección:** {cliente['Dirección']}")
                    with col3:
                        st.markdown(f"**📞 Teléfono:** {cliente['Teléfono']}")
            
            # Mostrar historial en tabla
            st.dataframe(
                historial[["Fecha y hora", "Tipo de reclamo", "Estado", "Técnico", "N° de Precinto", "Detalles"]],
                use_container_width=True,
                height=400
            )
            
            # Opción para exportar a CSV
            csv = historial.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar historial a CSV",
                data=csv,
                file_name=f"historial_cliente_{historial_cliente}.csv",
                mime="text/csv"
            )
        else:
            st.info("❕ Este cliente no tiene reclamos registrados.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# SECCIÓN 4: EDITAR CLIENTE
# --------------------------

elif opcion == "Editar cliente" and user_role == 'admin':
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("🛠️ Editar datos de un cliente")
    
    cliente_editar = st.text_input("🔎 Ingresá N° de Cliente a editar", 
                                  placeholder="Número de cliente",
                                  key="input_editar_cliente").strip()

    if cliente_editar:
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        cliente_row = df_clientes[df_clientes["Nº Cliente"] == cliente_editar]

        if not cliente_row.empty:
            cliente_actual = cliente_row.iloc[0]
            
            with st.form("editar_cliente_form"):
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_sector = st.text_input("🏙️ Sector", value=cliente_actual.get("Sector", ""))
                    nuevo_nombre = st.text_input("👤 Nombre", value=cliente_actual.get("Nombre", ""))
                with col2:
                    nueva_direccion = st.text_input("📍 Dirección", value=cliente_actual.get("Dirección", ""))
                    nuevo_telefono = st.text_input("📞 Teléfono", value=cliente_actual.get("Teléfono", ""))
                
                nuevo_precinto = st.text_input("🔒 N° de Precinto", 
                                             value=cliente_actual.get("N° de Precinto", ""),
                                             help="Número de precinto del medidor")

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
                        
                        success, error = api_manager.safe_sheet_operation(
                            batch_update_sheet,
                            sheet_clientes,
                            updates,
                            is_batch=True
                        )
                        
                        if success:
                            st.success("✅ Cliente actualizado correctamente.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al actualizar: {error}")
                            
                    except Exception as e:
                        st.error(f"❌ Error inesperado: {str(e)}")
        else:
            st.warning("⚠️ Cliente no encontrado.")

    # Formulario para nuevo cliente
    st.markdown("---")
    st.subheader("🆕 Cargar nuevo cliente")

    with st.form("form_nuevo_cliente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_nro = st.text_input("🔢 N° de Cliente (nuevo)", placeholder="Número único").strip()
            nuevo_sector = st.text_input("🏙️ Sector", placeholder="Zona o sector")
        with col2:
            nuevo_nombre = st.text_input("👤 Nombre", placeholder="Nombre completo")
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
                        
                        success, error = api_manager.safe_sheet_operation(
                            sheet_clientes.append_row,
                            nueva_fila
                        )
                        
                        if success:
                            st.success("✅ Nuevo cliente agregado correctamente.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error al guardar: {error}")
                            
                    except Exception as e:
                        st.error(f"❌ Error inesperado: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# SECCIÓN 5: IMPRIMIR RECLAMOS
# --------------------------

elif opcion == "Imprimir reclamos" and has_permission('imprimir_reclamos'):
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("🖨️ Seleccionar reclamos para imprimir (formato técnico compacto)")

    try:
        # Preparar datos
        df_pdf = df_reclamos.copy()
        df_merged = pd.merge(df_pdf, df_clientes[["Nº Cliente", "N° de Precinto"]], 
                            on="Nº Cliente", how="left", suffixes=("", "_cliente"))

        # Mostrar reclamos pendientes
        with st.expander("🕒 Reclamos pendientes de resolución", expanded=True):
            df_pendientes = df_merged[df_merged["Estado"] == "Pendiente"]
            if not df_pendientes.empty:
                st.dataframe(df_pendientes[["Fecha y hora", "Nº Cliente", "Nombre", "Dirección", "Sector", "Tipo de reclamo"]], 
                            use_container_width=True)
            else:
                st.success("✅ No hay reclamos pendientes actualmente.")

        solo_pendientes = st.checkbox("🧾 Mostrar solo reclamos pendientes para imprimir", value=True)

        # --- IMPRIMIR POR TIPO DE RECLAMO ---
        st.markdown("### 🧾 Imprimir reclamos por tipo")
        
        tipos_disponibles = sorted(df_merged["Tipo de reclamo"].unique())
        tipos_seleccionados = st.multiselect(
            "Seleccioná tipos de reclamo a imprimir", 
            tipos_disponibles,
            default=tipos_disponibles[0] if tipos_disponibles else None
        )

        if tipos_seleccionados:
            reclamos_filtrados = df_merged[
                (df_merged["Estado"] == "Pendiente") & 
                (df_merged["Tipo de reclamo"].isin(tipos_seleccionados))
            ]

            if not reclamos_filtrados.empty:
                st.success(f"Se encontraron {len(reclamos_filtrados)} reclamos pendientes de los tipos seleccionados.")

                if st.button("📄 Generar PDF de reclamos por tipo", key="pdf_tipo"):
                    with st.spinner("Generando PDF..."):
                        buffer = io.BytesIO()
                        c = canvas.Canvas(buffer, pagesize=A4)
                        width, height = A4
                        y = height - 40
                        
                        # Encabezado
                        c.setFont("Helvetica-Bold", 18)
                        c.drawString(40, y, f"RECLAMOS PENDIENTES - {datetime.now().strftime('%d/%m/%Y')}")
                        y -= 30
                        
                        for i, (_, reclamo) in enumerate(reclamos_filtrados.iterrows()):
                            c.setFont("Helvetica-Bold", 16)
                            c.drawString(40, y, f"#{reclamo['Nº Cliente']} - {reclamo['Nombre']}")
                            y -= 15
                            c.setFont("Helvetica", 13)
                            
                            lineas = [
                                f"Fecha: {reclamo['Fecha y hora']}",
                                f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                                f"Sector: {reclamo['Sector']} - Precinto: {reclamo.get('N° de Precinto', 'N/A')}",
                                f"Tipo: {reclamo['Tipo de reclamo']}",
                                f"Detalles: {reclamo['Detalles'][:100]}..." if len(reclamo['Detalles']) > 100 else f"Detalles: {reclamo['Detalles']}",
                            ]
                            
                            for linea in lineas:
                                c.drawString(40, y, linea)
                                y -= 12
                            
                            y -= 8
                            c.line(40, y, width-40, y)
                            y -= 15
                            
                            if y < 100 and i < len(reclamos_filtrados) - 1:
                                c.showPage()
                                y = height - 40
                                c.setFont("Helvetica-Bold", 18)
                                c.drawString(40, y, f"RECLAMOS PENDIENTES (cont.) - {datetime.now().strftime('%d/%m/%Y')}")
                                y -= 30

                        c.save()
                        buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Descargar PDF filtrado por tipo",
                            data=buffer,
                            file_name=f"reclamos_{'_'.join(tipos_seleccionados)}.pdf",
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
            format_func=lambda x: f"{df_merged.at[x, 'Nº Cliente']} - {df_merged.at[x, 'Nombre']}",
            key="multiselect_reclamos"
        )

        if st.button("📄 Generar PDF con seleccionados", key="pdf_manual") and selected:
            with st.spinner("Generando PDF..."):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4
                y = height - 40
                
                # Encabezado
                c.setFont("Helvetica-Bold", 18)
                c.drawString(40, y, f"RECLAMOS SELECCIONADOS - {datetime.now().strftime('%d/%m/%Y')}")
                y -= 30

                for i, idx in enumerate(selected):
                    reclamo = df_merged.loc[idx]
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(40, y, f"#{reclamo['Nº Cliente']} - {reclamo['Nombre']}")
                    y -= 15
                    c.setFont("Helvetica", 13)
                    
                    lineas = [
                        f"Fecha: {reclamo['Fecha y hora']}",
                        f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                        f"Sector: {reclamo['Sector']} - Precinto: {reclamo.get('N° de Precinto', 'N/A')}",
                        f"Tipo: {reclamo['Tipo de reclamo']}",
                        f"Detalles: {reclamo['Detalles'][:100]}..." if len(reclamo['Detalles']) > 100 else f"Detalles: {reclamo['Detalles']}",
                    ]
                    
                    for linea in lineas:
                        c.drawString(40, y, linea)
                        y -= 12
                    
                    y -= 8
                    c.line(40, y, width-40, y)
                    y -= 15
                    
                    if y < 100 and i < len(selected) - 1:
                        c.showPage()
                        y = height - 40
                        c.setFont("Helvetica-Bold", 18)
                        c.drawString(40, y, f"RECLAMOS SELECCIONADOS (cont.) - {datetime.now().strftime('%d/%m/%Y')}")
                        y -= 30

                c.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Descargar PDF seleccionados",
                    data=buffer,
                    file_name="reclamos_seleccionados.pdf",
                    mime="application/pdf"
                )

        elif not selected:
            st.info("Seleccioná al menos un reclamo para generar el PDF.")

        # --- NUEVO BLOQUE: EXPORTAR TODOS LOS ACTIVOS ---
        st.markdown("### 📦 Exportar todos los reclamos 'Pendiente' y 'En curso'")

        todos_filtrados = df_merged[df_merged["Estado"].isin(["Pendiente", "En curso"])].copy()

        if not todos_filtrados.empty:
            if st.button("📄 Generar PDF de todos los reclamos activos", key="pdf_todos"):
                with st.spinner("Generando PDF completo..."):
                    buffer = io.BytesIO()
                    c = canvas.Canvas(buffer, pagesize=A4)
                    width, height = A4
                    y = height - 40

                    c.setFont("Helvetica-Bold", 18)
                    c.drawString(40, y, f"TODOS LOS RECLAMOS ACTIVOS - {datetime.now().strftime('%d/%m/%Y')}")
                    y -= 30

                    for i, (_, reclamo) in enumerate(todos_filtrados.iterrows()):
                        c.setFont("Helvetica-Bold", 16)
                        c.drawString(40, y, f"#{reclamo['Nº Cliente']} - {reclamo['Nombre']}")
                        y -= 15
                        c.setFont("Helvetica", 13)
                        lineas = [
                                f"Fecha: {reclamo['Fecha y hora']}",
                                f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                                f"Sector: {reclamo['Sector']} - Precinto: {reclamo.get('N° de Precinto', 'N/A')}",
                                f"Tipo: {reclamo['Tipo de reclamo']}",
                                f"Detalles: {reclamo['Detalles'][:100]}..." if len(reclamo['Detalles']) > 100 else f"Detalles: {reclamo['Detalles']}",
                        ]
                        for linea in lineas:
                            c.drawString(40, y, linea)
                            y -= 12

                        y -= 10
                        c.line(40, y, width-40, y)
                        y -= 15

                        if y < 100:
                            c.showPage()
                            y = height - 40
                            c.setFont("Helvetica-Bold", 18)
                            c.drawString(40, y, f"RECLAMOS ACTIVOS (cont.) - {datetime.now().strftime('%d/%m/%Y')}")
                            y -= 30

                    c.save()
                    buffer.seek(0)

                    st.download_button(
                        label="📥 Descargar TODOS los reclamos activos en PDF",
                        data=buffer,
                        file_name="reclamos_activos_completo.pdf",
                        mime="application/pdf"
                    )
        else:
            st.info("🎉 No hay reclamos activos actualmente.")

    except Exception as e:
        st.error(f"❌ Error al generar PDF: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# SECCIÓN 6: SEGUIMIENTO TÉCNICO
# --------------------------

elif opcion == "Seguimiento técnico" and user_role == 'admin':
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.subheader("👷 Seguimiento técnico del reclamo")
    
    cliente_input = st.text_input("🔍 Ingresá el N° de Cliente para actualizar su reclamo", 
                                 placeholder="Número de cliente",
                                 key="input_seguimiento").strip()

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
                with st.expander("📋 Información del Reclamo", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**📅 Fecha:** {reclamo_actual['Fecha y hora']}")
                        st.markdown(f"**📌 Tipo:** {reclamo_actual['Tipo de reclamo']}")
                        st.markdown(f"**📍 Dirección:** {reclamo_actual['Dirección']}")
                    with col2:
                        st.markdown(f"**🔒 Precinto:** {reclamo_actual.get('N° de Precinto', 'No asignado')}")
                        st.markdown(f"**📞 Teléfono:** {reclamo_actual['Teléfono']}")
                        st.markdown(f"**👤 Atendido por:** {reclamo_actual['Atendido por']}")
                    
                    st.markdown(f"**📄 Detalles:** {reclamo_actual['Detalles']}")

                # Formulario de actualización
                with st.form("actualizar_reclamo"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nuevo_estado = st.selectbox(
                            "⚙️ Cambiar estado",
                            ["Pendiente", "En curso", "Resuelto"],
                            index=["Pendiente", "En curso", "Resuelto"].index(reclamo_actual["Estado"]),
                            key="select_estado"
                        )
                    
                    with col2:
                        tecnicos_actuales = [t.strip() for t in str(reclamo_actual.get("Técnico", "")).split(",") if t.strip()]
                        tecnicos_actuales_filtrados = [
                            t for t in TECNICOS_DISPONIBLES if t.lower() in [x.lower() for x in tecnicos_actuales]
                        ]

                        nuevos_tecnicos = st.multiselect(
                            "👷 Técnicos asignados",
                            TECNICOS_DISPONIBLES,
                            default=tecnicos_actuales_filtrados,
                            key="multiselect_tecnicos"
                        )

                    actualizar = st.form_submit_button("💾 Actualizar reclamo", use_container_width=True)

                if actualizar:
                    if not nuevos_tecnicos and nuevo_estado == "En curso":
                        st.warning("⚠️ Debes asignar al menos un técnico para marcar como 'En curso'.")
                    else:
                        with st.spinner("Actualizando reclamo..."):
                            try:
                                updates = [
                                    {"range": f"I{index_reclamo}", "values": [[nuevo_estado]]},
                                    {"range": f"J{index_reclamo}", "values": [[", ".join(nuevos_tecnicos).upper()]]}
                                ]
                                
                                success, error = api_manager.safe_sheet_operation(
                                    batch_update_sheet,
                                    sheet_reclamos,
                                    updates,
                                    is_batch=True
                                )
                                
                                if success:
                                    st.success("✅ Reclamo actualizado correctamente.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al actualizar: {error}")
                                    
                            except Exception as e:
                                st.error(f"❌ Error inesperado: {str(e)}")

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
            reclamos_en_curso[["Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico", "Fecha y hora"]],
            use_container_width=True,
            height=400
        )

        if st.button("📄 Generar PDF de reclamos en curso", key="pdf_en_curso"):
            with st.spinner("Generando PDF optimizado..."):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                x_left = 40
                x_right = width / 2 + 10
                y = height - 40
                columna_izquierda = True

                # Encabezado
                c.setFont("Helvetica-Bold", 14)
                c.drawString(x_left, y, "RECLAMOS EN CURSO - " + datetime.now().strftime("%d/%m/%Y"))
                y -= 30

                for idx, reclamo in reclamos_en_curso.iterrows():
                    x = x_left if columna_izquierda else x_right

                    # Fuente más pequeña para más información
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(x, y, f"{reclamo['Nº Cliente']} - {reclamo['Nombre']}")
                    y -= 12
                    
                    c.setFont("Helvetica", 8)
                    c.drawString(x, y, f"📅 {reclamo['Fecha y hora'].strftime('%d/%m %H:%M')}")
                    y -= 10
                    c.drawString(x, y, f"📌 {reclamo['Tipo de reclamo']}")
                    y -= 10
                    c.drawString(x, y, f"👷 {reclamo['Técnico']}")
                    y -= 15
                    
                    if not columna_izquierda:
                        y -= 5
                    columna_izquierda = not columna_izquierda

                    if y < 60:
                        c.showPage()
                        y = height - 40
                        columna_izquierda = True
                        c.setFont("Helvetica-Bold", 14)
                        c.drawString(x_left, y, "RECLAMOS EN CURSO (cont.) - " + datetime.now().strftime("%d/%m/%Y"))
                        y -= 30

                c.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Descargar PDF optimizado",
                    data=buffer,
                    file_name="reclamos_en_curso.pdf",
                    mime="application/pdf"
                )
    
    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# SECCIÓN 7: CIERRE DE RECLAMOS
# --------------------------
elif opcion == "Cierre de Reclamos" and user_role == 'admin':
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
        tecnicos_seleccionados = st.multiselect("👷 Filtrar por técnico asignado", tecnicos_unicos, key="filtro_tecnicos")

        if tecnicos_seleccionados:
            en_curso = en_curso[
                en_curso["Técnico"].apply(
                    lambda t: any(tecnico.lower() in t.lower() for tecnico in tecnicos_seleccionados)
                )
            ]

        st.write("### 📋 Reclamos en curso:")
        st.dataframe(en_curso[["Fecha y hora", "Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]], 
                    use_container_width=True,
                    height=400)

        st.markdown("### ✏️ Acciones por reclamo:")

        for i, row in en_curso.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**#{row['Nº Cliente']} - {row['Nombre']}**")
                    st.markdown(f"📅 {row['Fecha y hora']}")
                    st.markdown(f"📌 {row['Tipo de reclamo']}")
                    st.markdown(f"👷 {row['Técnico']}")

                    # Campo de precinto editable
                    cliente_id = str(row["Nº Cliente"]).strip()
                    cliente_info = df_clientes[df_clientes["Nº Cliente"] == cliente_id]
                    precinto_actual = cliente_info["N° de Precinto"].values[0] if not cliente_info.empty else ""
                    nuevo_precinto = st.text_input("🔒 Precinto", 
                                                  value=precinto_actual, 
                                                  key=f"precinto_{i}",
                                                  help="Actualizar número de precinto si es necesario")

                with col2:
                    if st.button("✅ Resuelto", key=f"resolver_{i}", use_container_width=True):
                        with st.spinner("Cerrando reclamo..."):
                            try:
                                updates = [{"range": f"I{i + 2}", "values": [["Resuelto"]]}]

                                # Agregar fecha de resolución si corresponde
                                if len(COLUMNAS_RECLAMOS) > 12:
                                    argentina = pytz.timezone("America/Argentina/Buenos_Aires")
                                    fecha_resolucion = datetime.now(argentina).strftime("%d/%m/%Y %H:%M:%S")
                                    updates.append({"range": f"M{i + 2}", "values": [[fecha_resolucion]]})

                                # Actualizar precinto en hoja de reclamos (visual)
                                if nuevo_precinto.strip() and nuevo_precinto != precinto_actual:
                                    updates.append({"range": f"F{i + 2}", "values": [[nuevo_precinto.strip()]]})

                                # Ejecutar actualizaciones en hoja de reclamos
                                success, error = api_manager.safe_sheet_operation(
                                    batch_update_sheet,
                                    sheet_reclamos,
                                    updates,
                                    is_batch=True
                                )

                                if success:
                                    # También actualizar en hoja de CLIENTES si el cliente existe
                                    if nuevo_precinto.strip() and nuevo_precinto != precinto_actual and not cliente_info.empty:
                                        index_cliente_en_clientes = cliente_info.index[0] + 2
                                        success_precinto, error_precinto = api_manager.safe_sheet_operation(
                                            sheet_clientes.update,
                                            f"F{index_cliente_en_clientes}",
                                            [[nuevo_precinto.strip()]]
                                        )
                                        if not success_precinto:
                                            st.warning(f"⚠️ Precinto guardado en reclamo pero no en hoja de clientes: {error_precinto}")

                                    st.success(f"🟢 Reclamo de {row['Nombre']} cerrado correctamente.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al actualizar: {error}")

                            except Exception as e:
                                st.error(f"❌ Error inesperado: {str(e)}")

                with col3:
                    if st.button("↩️ Pendiente", key=f"volver_{i}", use_container_width=True):
                        with st.spinner("Cambiando estado..."):
                            try:
                                updates = [
                                    {"range": f"I{i + 2}", "values": [["Pendiente"]]},
                                    {"range": f"J{i + 2}", "values": [[""]]}  # Limpiar técnico
                                ]

                                success, error = api_manager.safe_sheet_operation(
                                    batch_update_sheet,
                                    sheet_reclamos,
                                    updates,
                                    is_batch=True
                                )

                                if success:
                                    st.success(f"🔄 Reclamo de {row['Nombre']} vuelto a PENDIENTE.")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error al actualizar: {error}")

                            except Exception as e:
                                st.error(f"❌ Error inesperado: {str(e)}")

                st.divider()

    st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# FOOTER
# --------------------------
st.markdown("---")
st.markdown("### 📊 Estadísticas de la sesión")

# Mostrar estadísticas de API de forma segura
try:
    api_stats = api_manager.get_api_stats()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🔄 Llamadas a la API", api_stats.get('total_calls', 0))
    
    with col2:
        if api_stats.get('last_call', 0) > 0:
            last_call_time = datetime.fromtimestamp(api_stats['last_call']).strftime("%H:%M:%S")
            st.metric("🕐 Última llamada", last_call_time)
        else:
            st.metric("🕐 Última llamada", "N/A")
    
    with col3:
        st.metric("⚠️ Errores API", api_stats.get('error_count', 0))

except Exception as e:
    st.error(f"Error al cargar estadísticas: {str(e)}")
