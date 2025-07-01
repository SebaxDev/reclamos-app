import streamlit as st
import psycopg2
from datetime import datetime
import pytz
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import os
from dotenv import load_dotenv
import threading
import requests
import time
from psycopg2.extras import RealDictCursor
import extra_streamlit_components as stx
from streamlit_extras.colored_header import colored_header
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.stylable_container import stylable_container

# Cargar variables de entorno al inicio
load_dotenv()

# =============================================
# CONFIGURACIÓN INICIAL Y ESTILOS
# =============================================

# Configuración de página
st.set_page_config(
    page_title="Fusion Reclamos App",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS GLOBALES ---
def load_css():
    st.markdown("""
        <style>
            /* Fuentes y colores principales */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
            }
            
            /* Contenedor principal */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                max-width: 95%;
            }
            
            /* Títulos */
            h1, h2, h3, h4, h5, h6 {
                color: #2c3e50;
                font-weight: 600;
            }
            
            /* Botones */
            .stButton>button {
                border-radius: 8px;
                font-weight: 500;
                padding: 0.5rem 1rem;
                transition: all 0.3s ease;
            }
            
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            
            /* Inputs y selects */
            .stTextInput>div>div>input, 
            .stSelectbox>div>div>select,
            .stTextArea>div>div>textarea {
                border-radius: 8px;
                padding: 0.5rem;
            }
            
            /* Dataframes y tablas */
            .stDataFrame {
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            /* Sidebar */
            [data-testid="stSidebar"] {
                background: #f8f9fa;
            }
            
            /* Cards */
            .metric-card {
                background: white;
                border-radius: 10px;
                padding: 1rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                transition: all 0.3s ease;
            }
            
            .metric-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            }
            
            /* Animaciones */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .fade-in {
                animation: fadeIn 0.5s ease-out forwards;
            }
        </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================
# FUNCIONES DE BASE DE DATOS (OPTIMIZADAS)
# =============================================

@st.cache_resource(ttl=300)  # Cache de conexión por 5 minutos
def get_db_connection():
    """Crear una nueva conexión a la base de datos optimizada"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 5432)),
            cursor_factory=RealDictCursor,
            sslmode='require',
            connect_timeout=5,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=3
        )
        return conn
    except Exception as e:
        st.error(f"Error de conexión a la base de datos: {str(e)}")
        return None

@st.cache_data(ttl=60)  # Cache de datos por 1 minuto
def get_clientes():
    """Obtener todos los clientes de la base de datos"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql("SELECT * FROM clientes ORDER BY nro_cliente", conn)
        return df
    except Exception as e:
        st.error(f"Error al obtener clientes: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

@st.cache_data(ttl=60)  # Cache de datos por 1 minuto
def get_reclamos():
    """Obtener todos los reclamos de la base de datos"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    try:
        df = pd.read_sql("""
            SELECT r.*, c.precinto as precinto_cliente 
            FROM reclamos r
            LEFT JOIN clientes c ON r.nro_cliente = c.nro_cliente
            ORDER BY r.fecha_hora DESC
        """, conn)
        return df
    except Exception as e:
        st.error(f"Error al obtener reclamos: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def guardar_reclamo(fila_reclamo):
    """Guardar un nuevo reclamo en la base de datos"""
    conn = get_db_connection()
    if conn is None:
        return False
        
    try:
        with conn.cursor() as cur:
            # Insertar cliente si no existe
            cur.execute("""
                INSERT INTO clientes (nro_cliente, sector, nombre, direccion, telefono, precinto)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (nro_cliente) DO NOTHING
            """, fila_reclamo[1:7])
            
            # Insertar reclamo
            cur.execute("""
                INSERT INTO reclamos 
                (fecha_hora, nro_cliente, sector, nombre, direccion, telefono, 
                 tipo_reclamo, detalles, estado, precinto, atendido_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, fila_reclamo)
            
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al guardar reclamo: {str(e)}")
        return False
    finally:
        conn.close()

# =============================================
# COMPONENTES REUTILIZABLES
# =============================================

def metric_card(title, value, delta=None, help_text=None):
    """Componente de tarjeta métrica estilizada"""
    with stylable_container(
        key=f"metric_{title}",
        css_styles="""
            {
                background: white;
                border-radius: 10px;
                padding: 1rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                transition: all 0.3s ease;
                border-left: 4px solid #4e79a7;
            }
            :hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            }
        """
    ):
        st.metric(label=title, value=value, delta=delta, help=help_text)

def animated_card(content, delay=0):
    """Contenedor con animación de entrada"""
    with stylable_container(
        key=f"animated_{delay}",
        css_styles=f"""
            {{
                animation: fadeIn 0.5s ease-out {delay}s forwards;
                opacity: 0;
            }}
        """
    ):
        content()

# =============================================
# SISTEMA DE AUTENTICACIÓN
# =============================================

def login_section():
    """Sección de login con diseño mejorado"""
    with stylable_container(
        key="login_container",
        css_styles="""
            {
                max-width: 500px;
                margin: 0 auto;
                padding: 2rem;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        """
    ):
        st.title("🔐 Iniciar sesión", anchor=False)
        
        with st.form("login_formulario"):
            usuario = st.text_input("Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña")
            
            with stylable_container(
                key="login_button",
                css_styles="""
                    button {
                        background-color: #4e79a7;
                        color: white;
                        width: 100%;
                    }
                """
            ):
                enviar = st.form_submit_button("Ingresar")

            if enviar:
                if not usuario or not password:
                    st.error("❌ Por favor completa todos los campos")
                else:
                    with st.spinner("Verificando credenciales..."):
                        conn = get_db_connection()
                        if conn is None:
                            st.error("🔴 No se pudo conectar a la base de datos.")
                        else:
                            try:
                                with conn.cursor() as cur:
                                    cur.execute(
                                        "SELECT * FROM usuarios WHERE username = %s AND password = %s",
                                        (usuario, password)
                                    )
                                    resultado = cur.fetchone()
                                    if resultado:
                                        st.session_state.logueado = True
                                        st.session_state.usuario_actual = usuario
                                        st.success("✅ Acceso concedido")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("❌ Usuario o contraseña incorrectos")
                            except Exception as e:
                                st.error(f"⚠️ Error durante el login: {str(e)}")
                            finally:
                                conn.close()
        return False

# =============================================
# SECCIONES PRINCIPALES
# =============================================

def dashboard_section():
    """Sección de dashboard con métricas"""
    colored_header(
        label="📋 Panel de Control",
        description="Resumen general de reclamos",
        color_name="blue-70",
    )
    
    df_reclamos = get_reclamos()
    
    if not df_reclamos.empty:
        df_activos = df_reclamos[df_reclamos["estado"].isin(["Pendiente", "En curso"])]
        
        total = len(df_activos)
        pendientes = len(df_activos[df_activos["estado"] == "Pendiente"])
        en_curso = len(df_activos[df_activos["estado"] == "En curso"])
        resueltos = len(df_reclamos[df_reclamos["estado"] == "Resuelto"])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            metric_card("📄 Total activos", total, help_text="Reclamos pendientes + en curso")
        with col2:
            metric_card("🕒 Pendientes", pendientes, help_text="Reclamos sin asignar")
        with col3:
            metric_card("🔧 En curso", en_curso, help_text="Reclamos en progreso")
        with col4:
            metric_card("✅ Resueltos", resueltos, help_text="Reclamos completados")
        
        style_metric_cards()
    else:
        st.info("📊 No hay reclamos registrados aún")

def nuevo_reclamo_section():
    """Sección para crear nuevos reclamos"""
    colored_header(
        label="📝 Nuevo Reclamo",
        description="Complete los datos del nuevo reclamo",
        color_name="blue-70",
    )
    
    df_clientes = get_clientes()
    df_reclamos = get_reclamos()
    
    with stylable_container(
        key="nuevo_reclamo_container",
        css_styles="""
            {
                padding: 1.5rem;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            }
        """
    ):
        nro_cliente = st.text_input("🔢 N° de Cliente", help="Ingrese el número de cliente").strip()
        cliente_existente = None
        formulario_bloqueado = False

        if nro_cliente:
            # Verificar cliente existente
            if not df_clientes.empty and 'nro_cliente' in df_clientes.columns:
                match = df_clientes[df_clientes["nro_cliente"] == nro_cliente]
                
                if not match.empty:
                    cliente_existente = match.iloc[0]
                    st.success("✅ Cliente reconocido, datos auto-cargados.")
                else:
                    st.info("ℹ️ Cliente no encontrado. Se cargará como Cliente Nuevo.")
            
            # Verificar reclamos activos
            if not df_reclamos.empty and 'nro_cliente' in df_reclamos.columns:
                reclamos_activos = df_reclamos[
                    (df_reclamos["nro_cliente"] == nro_cliente) &
                    (df_reclamos["estado"].isin(["Pendiente", "En curso"]))
                ]

                if not reclamos_activos.empty:
                    st.error("⚠️ Este cliente ya tiene un reclamo sin resolver. No se puede cargar uno nuevo hasta que se cierre el anterior.")
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

                detalles = st.text_area("📝 Detalles del Reclamo", height=100)
                precinto = st.text_input("🔒 N° de Precinto (opcional)", value=cliente_existente.get("precinto", "") if cliente_existente else "")
                atendido_por = st.text_input("👤 Atendido por")

                with stylable_container(
                    key="submit_button",
                    css_styles="""
                        button {
                            background-color: #4e79a7;
                            color: white;
                        }
                    """
                ):
                    enviado = st.form_submit_button("✅ Guardar Reclamo")

                if enviado:
                    if not nro_cliente:
                        st.error("⚠️ Debes ingresar un número de cliente.")
                    elif not atendido_por.strip():
                        st.error("⚠️ El campo 'Atendido por' es obligatorio.")
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
                            if cliente_existente is None:
                                st.info("🗂️ Nuevo cliente agregado a la base de datos.")
                            time.sleep(1)
                            st.rerun()

# =============================================
# ESTRUCTURA PRINCIPAL DE LA APP
# =============================================

def main():
    # Inicializar estado de sesión
    if "logueado" not in st.session_state:
        st.session_state.logueado = False
    if "usuario_actual" not in st.session_state:
        st.session_state.usuario_actual = ""

    # Mostrar login si no está autenticado
    if not st.session_state.logueado:
        login_section()
        return

    # Barra superior con usuario y botón de logout
    with stylable_container(
        key="top_bar",
        css_styles="""
            {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem 1rem;
                background: #f8f9fa;
                border-bottom: 1px solid #e9ecef;
                margin-bottom: 1rem;
            }
        """
    ):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.caption(f"👤 Usuario: **{st.session_state.usuario_actual}**")
        with col2:
            if st.button("🚪 Cerrar sesión"):
                st.session_state.logueado = False
                st.session_state.usuario_actual = ""
                st.rerun()

    # Menú de navegación con pestañas
    opciones_menu = {
        "Inicio": "🏠",
        "Reclamos cargados": "📋",
        "Historial por cliente": "🔍",
        "Editar cliente": "✏️",
        "Imprimir reclamos": "🖨️",
        "Seguimiento técnico": "👷",
        "Cierre de Reclamos": "✅"
    }
    
    selected_tab = stx.tab_bar(data=[
        stx.TabBarItemData(id=key, title=value + " " + key, description="") 
        for key, value in opciones_menu.items()
    ])

    # Mostrar sección según pestaña seleccionada
    if selected_tab == "Inicio":
        dashboard_section()
        nuevo_reclamo_section()
    elif selected_tab == "Reclamos cargados":
        # ... (implementar otras secciones de manera similar)
        pass
    # ... (implementar el resto de las secciones)

if __name__ == "__main__":
    main()
