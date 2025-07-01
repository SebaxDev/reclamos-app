import streamlit as st
from datetime import datetime
import pytz
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# Configuración de credenciales desde variables de entorno
creds_dict = {
    "type": os.environ.get("GCP_TYPE"),
    "project_id": os.environ.get("GCP_PROJECT_ID"),
    "private_key_id": os.environ.get("GCP_PRIVATE_KEY_ID"),
    "private_key": os.environ.get("GCP_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.environ.get("GCP_CLIENT_EMAIL"),
    "client_id": os.environ.get("GCP_CLIENT_ID"),
    "auth_uri": os.environ.get("GCP_AUTH_URI"),
    "token_uri": os.environ.get("GCP_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.environ.get("GCP_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.environ.get("GCP_CLIENT_CERT_URL")
}

# Autenticación
try:
    creds = service_account.Credentials.from_service_account_info(creds_dict)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds = creds.with_scopes(scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.environ.get("GOOGLE_SHEETS_ID"))
    worksheet = sheet.worksheet("Fusion Reclamos App")  # Reemplaza con tu nombre de hoja
except Exception as e:
    st.error(f"🚨 Error al conectar con Google Sheets: {str(e)}")

# =============================================
# CONFIGURACIÓN INICIAL
# =============================================
st.set_page_config(
    page_title="Fusion Reclamos App",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://www.google.com',
        'About': "### App de Gestión de Reclamos v2.0\nSistema para registro y seguimiento de reclamos técnicos"
    }
)

# =============================================
# CONEXIÓN A GOOGLE SHEETS (REEMPLAZA POSTGRESQL)
# =============================================
@st.cache_resource
def get_google_sheet():
    """Conecta con Google Sheets usando credenciales"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", 
                "https://www.googleapis.com/auth/drive"]
        
        creds_json = {
            "type": st.secrets["type"],
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets["private_key_id"],
            "private_key": st.secrets["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets["client_id"],
            "auth_uri": st.secrets["auth_uri"],
            "token_uri": st.secrets["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["client_x509_cert_url"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        gc = gspread.authorize(creds)
        return gc.open_by_key(st.secrets["SHEET_ID"])
    except Exception as e:
        st.error(f"🚨 Error al conectar con Google Sheets: {str(e)}")
        return None

# =============================================
# FUNCIONES PRINCIPALES (GOOGLE SHEETS)
# =============================================
def get_clientes():
    """Obtiene todos los clientes"""
    try:
        sheet = get_google_sheet().worksheet("clientes")
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Error al obtener clientes: {str(e)}")
        return pd.DataFrame(columns=['nro_cliente', 'sector', 'nombre', 'direccion', 'telefono', 'precintos'])

def get_reclamos():
    """Obtiene todos los reclamos"""
    try:
        sheet = get_google_sheet().worksheet("reclamos")
        df = pd.DataFrame(sheet.get_all_records())
        
        # Convertir tipos de datos
        if not df.empty:
            df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
            if 'fecha_resolucion' in df.columns:
                df['fecha_resolucion'] = pd.to_datetime(df['fecha_resolucion'])
        return df
    except Exception as e:
        st.error(f"Error al obtener reclamos: {str(e)}")
        return pd.DataFrame(columns=['id', 'fecha_hora', 'nro_cliente', 'sector', 'nombre', 'direccion', 
                                   'telefono', 'tipo_reclamo', 'detalles', 'estado', 'tecnico', 'precinto', 
                                   'atendido_por', 'fecha_resolucion'])

def guardar_reclamo(fila_reclamo):
    """Guarda un nuevo reclamo en Google Sheets"""
    try:
        sheet = get_google_sheet().worksheet("reclamos")
        
        # Insertar cliente si no existe
        clientes_sheet = get_google_sheet().worksheet("clientes")
        nro_cliente = fila_reclamo[1]  # Posición del nro_cliente en la lista
        
        # Verificar si el cliente ya existe
        try:
            clientes_sheet.find(nro_cliente)
        except gspread.exceptions.CellNotFound:
            # Insertar nuevo cliente
            cliente_data = fila_reclamo[1:7]  # [nro_cliente, sector, nombre, direccion, telefono, precinto]
            clientes_sheet.append_row(cliente_data)
        
        # Guardar reclamo (convertir datetime a string)
        fila_reclamo[0] = str(fila_reclamo[0])  # fecha_hora
        sheet.append_row(fila_reclamo)
        return True
    except Exception as e:
        st.error(f"Error al guardar reclamo: {str(e)}")
        return False

def actualizar_reclamo(id_reclamo, nuevos_datos):
    """Actualiza un reclamo existente"""
    try:
        sheet = get_google_sheet().worksheet("reclamos")
        records = sheet.get_all_records()
        
        # Buscar fila por ID
        for idx, row in enumerate(records, start=2):  # Empieza en 2 (fila 1 es headers)
            if str(row['id']) == str(id_reclamo):
                # Actualizar campos
                for key, value in nuevos_datos.items():
                    sheet.update_cell(idx, list(row.keys()).index(key) + 1, value)
                return True
        return False
    except Exception as e:
        st.error(f"Error al actualizar reclamo: {str(e)}")
        return False

# =============================================
# SISTEMA DE LOGIN (CON GOOGLE SHEETS)
# =============================================
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
            try:
                sheet = get_google_sheet().worksheet("usuarios")
                usuarios = pd.DataFrame(sheet.get_all_records())
                
                if not usuarios.empty:
                    user = usuarios[(usuarios['username'] == usuario) & (usuarios['password'] == password)]
                    if not user.empty:
                        st.session_state.logueado = True
                        st.session_state.usuario_actual = usuario
                        st.success("✅ Acceso concedido")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
                else:
                    st.error("No hay usuarios registrados")
            except Exception as e:
                st.error(f"Error durante el login: {str(e)}")
    st.stop()

# =============================================
# INTERFAZ PRINCIPAL (STREAMLIT)
# =============================================
# --- ESTILOS ---
st.markdown("""
    <style>
    .block-container { max-width: 1000px; }
    .stButton>button { border-radius: 8px; }
    .metric-container { background: #f8f9fa; border-radius: 10px; padding: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- LISTA DE TÉCNICOS ---
tecnicos_disponibles = ["Braian", "Conejo", "Juan", "Junior", "Maxi", "Ramon", "Roque", "Viki", "Oficina", "Base"]

# --- TÍTULO Y DASHBOARD ---
st.title("📋 Fusion Reclamos App")
st.caption(f"👤 Usuario: {st.session_state.usuario_actual}")

# --- MÉTRICAS ---
try:
    df_reclamos = get_reclamos()
    if not df_reclamos.empty:
        df_activos = df_reclamos[df_reclamos["estado"].isin(["Pendiente", "En curso"])]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("📄 Total activos", len(df_activos))
        with col2: st.metric("🕒 Pendientes", len(df_activos[df_activos["estado"] == "Pendiente"]))
        with col3: st.metric("🔧 En curso", len(df_activos[df_activos["estado"] == "En curso"]))
        with col4: st.metric("✅ Resueltos", len(df_reclamos[df_reclamos["estado"] == "Resuelto"]))
    else:
        st.info("📊 No hay reclamos registrados aún")
except Exception as e:
    st.error(f"⚠️ Error al cargar métricas: {str(e)}")

st.divider()

# --- MENÚ DE NAVEGACIÓN ---
opciones_menu = [
    "Inicio", "Reclamos cargados", "Historial por cliente", 
    "Editar cliente", "Imprimir reclamos", "Seguimiento técnico", 
    "Cierre de Reclamos"
]
opcion = st.radio("📂 Ir a la sección:", opciones_menu, horizontal=True, label_visibility="collapsed")
st.divider()

# --- SECCIÓN 1: INICIO (CARGAR RECLAMO) ---
if opcion == "Inicio":
    st.subheader("📝 Cargar nuevo reclamo")
    
    df_clientes = get_clientes()
    df_reclamos = get_reclamos()
    
    nro_cliente = st.text_input("🔢 N° de Cliente", help="Ingrese el número de cliente").strip()
    cliente_existente = None
    formulario_bloqueado = False

    if nro_cliente:
        # Verificar cliente existente
        if not df_clientes.empty:
            match = df_clientes[df_clientes["nro_cliente"] == nro_cliente]
            if not match.empty:
                cliente_existente = match.iloc[0]
                st.success("✅ Cliente reconocido, datos auto-cargados.")
            else:
                st.info("ℹ️ Cliente no encontrado. Se cargará como nuevo.")
        
        # Verificar reclamos activos
        if not df_reclamos.empty:
            reclamos_activos = df_reclamos[
                (df_reclamos["nro_cliente"] == nro_cliente) &
                (df_reclamos["estado"].isin(["Pendiente", "En curso"]))
            ]
            if not reclamos_activos.empty:
                st.error("⚠️ Este cliente ya tiene un reclamo sin resolver.")
                formulario_bloqueado = True

    if not formulario_bloqueado:
        with st.form("reclamo_formulario"):
            col1, col2 = st.columns(2)
            if cliente_existente is not None:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", value=cliente_existente.get("sector", ""))
                    direccion = st.text_input("📍 Dirección", value=cliente_existente.get("direccion", ""))
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", value=cliente_existente.get("nombre", ""))
                    telefono = st.text_input("📞 Teléfono", value=cliente_existente.get("telefono", ""))
            else:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", value="")
                    direccion = st.text_input("📍 Dirección", value="")
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", value="")
                    telefono = st.text_input("📞 Teléfono", value="")

            tipo_reclamo = st.selectbox("📌 Tipo de Reclamo", [
                "Conexion C+I", "Conexion Cable", "Conexion Internet", "Suma Internet",
                "Suma Cable", "Reconexion", "Sin Señal Ambos", "Sin Señal Cable",
                "Sin Señal Internet", "Sintonia", "Interferencia", "Traslado",
                "Extension x2", "Extension x3", "Extension x4", "Cambio de Ficha",
                "Cambio de Equipo", "Reclamo", "Desconexion a Pedido"
            ])

            detalles = st.text_area("📝 Detalles del Reclamo")
            precinto = st.text_input("🔒 N° de Precinto (opcional)", value=cliente_existente.get("precinto", "") if cliente_existente else "")
            atendido_por = st.text_input("👤 Atendido por", value=st.session_state.usuario_actual)

            enviado = st.form_submit_button("✅ Guardar Reclamo", use_container_width=True)

        if enviado:
            if not nro_cliente or not atendido_por:
                st.error("⚠️ Completa los campos obligatorios.")
            else:
                fecha_hora = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
                fila_reclamo = [
                    fecha_hora,
                    nro_cliente,
                    sector,
                    nombre.upper(),
                    direccion.upper(),
                    telefono,
                    tipo_reclamo,
                    detalles.upper(),
                    "Pendiente",
                    precinto,
                    atendido_por.upper()
                ]
                
                if guardar_reclamo(fila_reclamo):
                    st.success("✅ Reclamo guardado correctamente.")
                    time.sleep(1)
                    st.rerun()

# --- SECCIÓN 2: RECLAMOS CARGADOS ---
elif opcion == "Reclamos cargados":
    st.subheader("📊 Reclamos cargados")
    try:
        df = get_reclamos()
        
        if df.empty:
            st.info("No hay reclamos registrados aún.")
            st.stop()
            
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1: filtro_estado = st.selectbox("🔎 Estado", ["Todos"] + sorted(df["estado"].unique()))
        with col2: filtro_sector = st.selectbox("🏙️ Sector", ["Todos"] + sorted(df["sector"].unique()))
        with col3: filtro_tipo = st.selectbox("📌 Tipo", ["Todos"] + sorted(df["tipo_reclamo"].unique()))

        if filtro_estado != "Todos": df = df[df["estado"] == filtro_estado]
        if filtro_sector != "Todos": df = df[df["sector"] == filtro_sector]
        if filtro_tipo != "Todos": df = df[df["tipo_reclamo"] == filtro_tipo]

        # Editor de datos
        edited_df = st.data_editor(
            df,
            column_config={
                "estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "En curso", "Resuelto"]),
                "tecnico": st.column_config.TextColumn("Técnico"),
                "precinto": st.column_config.TextColumn("Precinto")
            },
            hide_index=True,
            key="editor_reclamos"
        )

        if st.button("💾 Guardar cambios", use_container_width=True):
            for _, row in edited_df.iterrows():
                actualizar_reclamo(row['id'], {
                    'estado': row['estado'],
                    'tecnico': row['tecnico'],
                    'precinto': row['precinto']
                })
            st.success("✅ Cambios guardados.")
            time.sleep(1)
            st.rerun()
                
    except Exception as e:
        st.error(f"Error al cargar reclamos: {str(e)}")

# --- SECCIÓN 3: HISTORIAL POR CLIENTE ---
elif opcion == "Historial por cliente":
    st.subheader("📜 Historial por cliente")
    nro_cliente = st.text_input("🔍 Ingrese N° de Cliente").strip()
    
    if nro_cliente:
        try:
            df = get_reclamos()
            historial = df[df["nro_cliente"] == nro_cliente]
            
            if not historial.empty:
                st.dataframe(historial, hide_index=True)
            else:
                st.info("❕ No hay reclamos para este cliente.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- BOTÓN DE LOGOUT ---
if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    st.session_state.logueado = False
    st.session_state.usuario_actual = ""
    st.rerun()