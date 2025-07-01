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
import time
from psycopg2.extras import RealDictCursor

# ======================
# CONFIGURACIÓN INICIAL
# ======================
load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="Fusion Reclamos App",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================
# ESTILOS CSS PERSONALIZADOS
# ======================
st.markdown("""
    <style>
        /* Fuente y colores */
        * {
            font-family: 'Inter', sans-serif;
        }
        
        /* Contenedor principal */
        .main .block-container {
            padding-top: 1rem;
            max-width: 95%;
        }
        
        /* Tarjetas métricas */
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 4px solid #4e79a7;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        }
        
        /* Botones */
        .stButton>button {
            border-radius: 8px;
            font-weight: 500;
            padding: 0.5rem 1rem;
            background-color: #4e79a7;
            color: white;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background-color: #3a5f8a;
            transform: translateY(-2px);
        }
        
        /* Inputs */
        .stTextInput>div>div>input,
        .stSelectbox>div>div>select,
        .stTextArea>div>div>textarea {
            border-radius: 8px;
            padding: 0.75rem;
            border: 1px solid #e0e0e0;
        }
        
        /* Títulos */
        h1, h2, h3 {
            color: #2c3e50;
            border-bottom: 2px solid #4e79a7;
            padding-bottom: 0.5rem;
            margin-bottom: 1.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# ======================
# FUNCIONES DE BASE DE DATOS
# ======================
@st.cache_resource(ttl=300)
def get_db_connection():
    """Conexión optimizada a PostgreSQL con manejo de errores"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 5432)),
            cursor_factory=RealDictCursor,
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"🔴 Error de conexión: {str(e)}")
        return None

@st.cache_data(ttl=60)
def get_clientes():
    """Obtiene todos los clientes con caché"""
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    
    try:
        return pd.read_sql("SELECT * FROM clientes ORDER BY nro_cliente", conn)
    finally:
        conn.close()

@st.cache_data(ttl=60)
def get_reclamos():
    """Obtiene reclamos con join a clientes"""
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    
    try:
        return pd.read_sql("""
            SELECT r.*, c.precinto as precinto_cliente 
            FROM reclamos r
            LEFT JOIN clientes c ON r.nro_cliente = c.nro_cliente
            ORDER BY r.fecha_hora DESC
        """, conn)
    finally:
        conn.close()

def guardar_reclamo(fila_reclamo):
    """Guarda un nuevo reclamo en la base de datos"""
    conn = get_db_connection()
    if not conn: return False
    
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
        st.error(f"🔴 Error al guardar: {str(e)}")
        return False
    finally:
        conn.close()

# ======================
# COMPONENTES DE INTERFAZ
# ======================
def mostrar_metricas():
    """Muestra tarjetas métricas con estilo"""
    df = get_reclamos()
    if df.empty: return
    
    cols = st.columns(4)
    metricas = [
        ("📄 Total Activos", len(df[df["estado"].isin(["Pendiente", "En curso"])])),
        ("🕒 Pendientes", len(df[df["estado"] == "Pendiente"])),
        ("🔧 En Curso", len(df[df["estado"] == "En curso"])),
        ("✅ Resueltos", len(df[df["estado"] == "Resuelto"]))
    ]
    
    for i, (titulo, valor) in enumerate(metricas):
        with cols[i]:
            st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 24px; margin-bottom: 8px;">{titulo.split()[0]}</div>
                    <h3 style="margin: 0;">{titulo.split()[1]}</h3>
                    <h2 style="margin: 0; color: #2c3e50;">{valor}</h2>
                </div>
            """, unsafe_allow_html=True)

def generar_pdf(reclamo):
    """Genera PDF con ReportLab"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 40, f"Reclamo #{reclamo['nro_cliente']}")
    
    # Detalles
    c.setFont("Helvetica", 12)
    detalles = [
        f"Fecha: {reclamo['fecha_hora']}",
        f"Cliente: {reclamo['nombre']}",
        f"Tipo: {reclamo['tipo_reclamo']}",
        f"Estado: {reclamo['estado']}",
        f"Detalles: {reclamo['detalles'][:100]}"
    ]
    
    y = height - 80
    for linea in detalles:
        c.drawString(40, y, linea)
        y -= 20
    
    c.save()
    buffer.seek(0)
    return buffer

# ======================
# INTERFAZ PRINCIPAL
# ======================
def main():
    # Estado de sesión
    if "logueado" not in st.session_state:
        st.session_state.logueado = False
    if "usuario_actual" not in st.session_state:
        st.session_state.usuario_actual = ""
    
    # --- LOGIN ---
    if not st.session_state.logueado:
        with st.container():
            st.title("🔐 Inicio de Sesión")
            
            with st.form("login_form"):
                usuario = st.text_input("Usuario")
                password = st.text_input("Contraseña", type="password")
                
                if st.form_submit_button("Ingresar"):
                    # Verificación simple (reemplazar con DB)
                    if usuario == "admin" and password == "admin123":
                        st.session_state.logueado = True
                        st.session_state.usuario_actual = usuario
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")
        return
    
    # --- BARRA SUPERIOR ---
    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.title("📋 Fusion Reclamos")
            st.caption(f"👤 Usuario: {st.session_state.usuario_actual}")
        with col2:
            if st.button("🚪 Cerrar Sesión"):
                st.session_state.logueado = False
                st.rerun()
    
    # --- PESTAÑAS PRINCIPALES ---
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Inicio", "📋 Reclamos", "👷 Técnicos", "⚙️ Configuración"])
    
    # --- INICIO ---
    with tab1:
        st.header("Panel Principal")
        mostrar_metricas()
        
        with st.expander("➕ Nuevo Reclamo", expanded=True):
            with st.form("nuevo_reclamo_form"):
                nro_cliente = st.text_input("🔢 N° de Cliente")
                
                col1, col2 = st.columns(2)
                nombre = col1.text_input("👤 Nombre")
                sector = col2.text_input("🏢 Sector")
                
                tipo_reclamo = st.selectbox(
                    "📌 Tipo de Reclamo",
                    ["Conexión", "Reparación", "Facturación", "Otro"]
                )
                
                detalles = st.text_area("📝 Detalles", height=100)
                
                if st.form_submit_button("✅ Guardar Reclamo"):
                    fecha_hora = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
                    fila_reclamo = [
                        fecha_hora, nro_cliente, sector, nombre, 
                        "", "", tipo_reclamo, detalles, "Pendiente", "", "Sistema"
                    ]
                    
                    if guardar_reclamo(fila_reclamo):
                        st.success("Reclamo registrado correctamente")
                        time.sleep(1)
                        st.rerun()
    
    # --- RECLAMOS ---
    with tab2:
        st.header("Gestión de Reclamos")
        df = get_reclamos()
        
        if not df.empty:
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                filtro_estado = st.selectbox(
                    "Filtrar por estado",
                    ["Todos"] + list(df["estado"].unique())
                )
            with col2:
                filtro_tipo = st.selectbox(
                    "Filtrar por tipo",
                    ["Todos"] + list(df["tipo_reclamo"].unique())
                )
            
            # Aplicar filtros
            if filtro_estado != "Todos":
                df = df[df["estado"] == filtro_estado]
            if filtro_tipo != "Todos":
                df = df[df["tipo_reclamo"] == filtro_tipo]
            
            # Mostrar tabla
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "estado": st.column_config.SelectboxColumn(
                        "Estado",
                        options=["Pendiente", "En curso", "Resuelto"]
                    )
                }
            )
            
            # Exportar a PDF
            if st.button("📄 Generar Reporte PDF"):
                buffer = generar_pdf(df.iloc[0])
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=buffer,
                    file_name=f"reclamo_{df.iloc[0]['nro_cliente']}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("No hay reclamos registrados")
    
    # --- TÉCNICOS ---
    with tab3:
        st.header("Asignación Técnica")
        st.write("Funcionalidad en desarrollo...")
    
    # --- CONFIGURACIÓN ---
    with tab4:
        st.header("Configuración del Sistema")
        st.write("Opciones administrativas")

if __name__ == "__main__":
    main()
