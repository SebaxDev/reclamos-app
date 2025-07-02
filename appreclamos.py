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

# --- Cargar variables de entorno ---
load_dotenv()

# --- Configuración de página ---
st.set_page_config(
    page_title="Fusion Reclamos App",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://www.google.com',
        'Report a bug': None,
        'About': "### App de Gestión de Reclamos v2.0\nSistema para registro y seguimiento de reclamos técnicos"
    }
)

# --- Mantener viva la app en Fly.io si aplica ---
def keep_alive():
    while True:
        try:
            if 'RENDER_EXTERNAL_URL' in os.environ:
                requests.get(os.environ['RENDER_EXTERNAL_URL'], timeout=10)
        except:
            pass
        time.sleep(240)

if 'RENDER' in os.environ:
    threading.Thread(target=keep_alive, daemon=True).start()

# --- Verificar variables de entorno necesarias ---
def verificar_variables_entorno():
    requeridas = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_PORT']
    faltantes = [v for v in requeridas if not os.getenv(v)]

    if faltantes:
        st.error(f"""
        🔧 **Configuración requerida**

        Faltan las siguientes variables en `.env`:
        {', '.join(faltantes)}

        Ingresalas desde Neon Console > Connection Details
        """)
        return False
    return True

# --- Conexión a la base de datos ---
def get_db_connection():
    if not verificar_variables_entorno():
        return None
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 5432)),
            cursor_factory=RealDictCursor,
            sslmode='require',
            connect_timeout=8,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=3
        )
        # Test rápido
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return conn
    except Exception as e:
        print("Error conexión DB:", e)
        return None

# --- Inicializar estructura de la base ---
def init_db():
    try:
        conn = get_db_connection()
        if conn is None:
            return False

        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    username VARCHAR(50) PRIMARY KEY,
                    password VARCHAR(100) NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    nro_cliente VARCHAR(20) PRIMARY KEY,
                    sector VARCHAR(100),
                    nombre VARCHAR(100),
                    direccion VARCHAR(200),
                    telefono VARCHAR(50),
                    precinto VARCHAR(50)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reclamos (
                    id SERIAL PRIMARY KEY,
                    fecha_hora TIMESTAMP NOT NULL,
                    nro_cliente VARCHAR(20) REFERENCES clientes(nro_cliente),
                    sector VARCHAR(100),
                    nombre VARCHAR(100),
                    direccion VARCHAR(200),
                    telefono VARCHAR(50),
                    tipo_reclamo VARCHAR(50),
                    detalles TEXT,
                    estado VARCHAR(20) CHECK (estado IN ('Pendiente', 'En curso', 'Resuelto')),
                    tecnico VARCHAR(200),
                    precinto VARCHAR(50),
                    atendido_por VARCHAR(100),
                    fecha_resolucion TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT INTO usuarios (username, password)
                VALUES ('admin', 'AdminSeguro123!')
                ON CONFLICT (username) DO NOTHING
            """)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Error al inicializar DB:", e)
        return False

# --- Consultas comunes ---
def get_clientes():
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        df = pd.read_sql("SELECT * FROM clientes ORDER BY nro_cliente", conn)
        conn.close()
        return df
    except Exception as e:
        print("Error get_clientes:", e)
        return pd.DataFrame()

def get_reclamos():
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        df = pd.read_sql("""
            SELECT r.*, c.precinto as precinto_cliente 
            FROM reclamos r
            LEFT JOIN clientes c ON r.nro_cliente = c.nro_cliente
            ORDER BY r.fecha_hora DESC
        """, conn)
        conn.close()
        return df
    except Exception as e:
        print("Error get_reclamos:", e)
        return pd.DataFrame()

def guardar_reclamo(fila_reclamo):
    try:
        conn = get_db_connection()
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO clientes (nro_cliente, sector, nombre, direccion, telefono, precinto)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (nro_cliente) DO NOTHING
            """, fila_reclamo[1:7])
            cur.execute("""
                INSERT INTO reclamos 
                (fecha_hora, nro_cliente, sector, nombre, direccion, telefono, 
                 tipo_reclamo, detalles, estado, precinto, atendido_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, fila_reclamo)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Error guardar_reclamo:", e)
        return False

# --- Sistema de login ---
if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

if not verificar_variables_entorno():
    st.stop()

if not st.session_state.logueado:
    st.title("🔐 Iniciar sesión")
    with st.form("login_formulario"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")

        if enviar:
            if not usuario or not password:
                st.error("❌ Completá todos los campos.")
            else:
                with st.spinner("Verificando..."):
                    try:
                        conn = get_db_connection()
                        if conn is None:
                            st.error("🔴 No se pudo conectar a la base de datos.")
                        else:
                            with conn.cursor() as cur:
                                cur.execute("SELECT * FROM usuarios WHERE username = %s AND password = %s", (usuario, password))
                                if cur.fetchone():
                                    st.session_state.logueado = True
                                    st.session_state.usuario_actual = usuario
                                    st.success("✅ Acceso concedido")
                                    conn.close()
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Usuario o contraseña incorrectos.")
                                    conn.close()
                    except Exception as e:
                        st.error("⚠️ Error durante el login")
                        print("Login error:", e)
    st.stop()

if not init_db():
    st.error("No se pudo inicializar la base de datos. Verificá la conexión.")
    st.stop()

# --- ESTILO VISUAL MEJORADO ---
st.markdown("""
    <style>
    /* Estilos generales */
    .block-container {
        max-width: 1000px;
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Mejoras para los formularios */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 8px !important;
        border: 1px solid #ced4da !important;
        padding: 8px 12px !important;
    }
    
    /* Botones mejorados */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #0d6efd;
        background-color: #0d6efd;
        color: white;
        padding: 8px 16px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton>button:hover {
        background-color: #0b5ed7;
        border-color: #0a58ca;
    }
    
    /* Tarjetas de m茅tricas */
    .metric-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    
    /* Mejoras para los dataframes */
    .dataframe {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* T铆tulos m谩s limpios */
    h1, h2, h3, h4, h5, h6 {
        color: #212529;
    }
    
    /* Separadores mejorados */
    .stDivider {
        margin: 1.5rem 0;
    }
    
    /* Radio buttons horizontales */
    .stRadio > div {
        flex-direction: row;
        gap: 1rem;
        align-items: center;
    }
    
    .stRadio [role=radiogroup] {
        gap: 1rem;
        align-items: center;
    }
    
    /* Mensajes de alerta mejorados */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Contenedores de expansi贸n */
    .stExpander {
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    
    /* Mejoras para m贸viles */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- LISTA DE TÉCNICOS DISPONIBLES ---
tecnicos_disponibles = ["Braian", "Conejo", "Juan", "Junior", "Maxi", "Ramon", "Roque", "Viki", "Oficina", "Base"]

# --- TÍTULO Y DASHBOARD ---
st.title("📋 Fusion Reclamos App")
st.caption(f"👤 Usuario: {st.session_state.usuario_actual}")

# --- MÉTRICAS RESUMEN ---
try:
    df_reclamos = get_reclamos()
    if not df_reclamos.empty and "estado" in df_reclamos.columns:
        df_activos = df_reclamos[df_reclamos["estado"].isin(["Pendiente", "En curso"])]

        total = len(df_activos)
        pendientes = len(df_activos[df_activos["estado"] == "Pendiente"])
        en_curso = len(df_activos[df_activos["estado"] == "En curso"])
        resueltos = len(df_reclamos[df_reclamos["estado"] == "Resuelto"])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total activos", total, help="Reclamos pendientes + en curso")
        with col2:
            st.metric("🕒 Pendientes", pendientes, help="Reclamos sin asignar")
        with col3:
            st.metric("🔧 En curso", en_curso, help="Reclamos en proceso")
        with col4:
            st.metric("✅ Resueltos", resueltos, help="Reclamos finalizados")
    else:
        st.info("📭 No hay reclamos registrados aún.")
except Exception as e:
    st.warning("⚠️ Error al cargar métricas")
    print("Métricas error:", e)

st.divider()

# --- MENÚ DE NAVEGACIÓN ---
opciones_menu = [
    "Inicio", "Reclamos cargados", "Historial por cliente", 
    "Editar cliente", "Imprimir reclamos", "Seguimiento técnico", 
    "Cierre de Reclamos"
]
opcion = st.radio("📂 Ir a la sección:", opciones_menu, horizontal=True, label_visibility="collapsed")

st.divider()

# --- SECCIÓN 1: INICIO ---
if opcion == "Inicio":
    st.subheader("📝 Cargar nuevo reclamo")

    # Obtener datos una sola vez
    df_clientes = get_clientes()
    df_reclamos = get_reclamos()

    nro_cliente = st.text_input("🔢 N° de Cliente", help="Ingrese el número de cliente").strip()
    cliente_existente = None
    formulario_bloqueado = False

    if nro_cliente:
        # Verificar si el cliente ya existe
        if not df_clientes.empty and 'nro_cliente' in df_clientes.columns:
            match = df_clientes[df_clientes["nro_cliente"] == nro_cliente]
            if not match.empty:
                cliente_existente = match.iloc[0]
                st.success("✅ Cliente reconocido, datos auto-cargados.")
            else:
                st.info("ℹ️ Cliente no encontrado. Se cargará como nuevo.")
        else:
            st.info("ℹ️ No hay clientes registrados aún. Se cargará como nuevo.")

        # Verificar si tiene reclamos activos
        if not df_reclamos.empty and 'nro_cliente' in df_reclamos.columns:
            activos = df_reclamos[
                (df_reclamos["nro_cliente"] == nro_cliente) &
                (df_reclamos["estado"].isin(["Pendiente", "En curso"]))
            ]
            if not activos.empty:
                st.error("⚠️ Este cliente ya tiene un reclamo sin resolver. Cerralo antes de crear otro.")
                formulario_bloqueado = True

    if not formulario_bloqueado:
        with st.form("reclamo_formulario"):
            col1, col2 = st.columns(2)

            # Campos con autocompletado si el cliente existe
            sector = cliente_existente.get("sector", "") if cliente_existente else ""
            direccion = cliente_existente.get("direccion", "") if cliente_existente else ""
            nombre = cliente_existente.get("nombre", "") if cliente_existente else ""
            telefono = cliente_existente.get("telefono", "") if cliente_existente else ""
            precinto = cliente_existente.get("precinto", "") if cliente_existente else ""

            with col1:
                sector = st.text_input("🏘️ Sector / Zona", value=sector)
                direccion = st.text_input("📍 Dirección", value=direccion)
            with col2:
                nombre = st.text_input("👤 Nombre del Cliente", value=nombre)
                telefono = st.text_input("📞 Teléfono", value=telefono)

            tipo_reclamo = st.selectbox("📌 Tipo de Reclamo", [
                "Conexion C+I", "Conexion Cable", "Conexion Internet", "Suma Internet",
                "Suma Cable", "Reconexion", "Sin Señal Ambos", "Sin Señal Cable",
                "Sin Señal Internet", "Sintonia", "Interferencia", "Traslado",
                "Extension x2", "Extension x3", "Extension x4", "Cambio de Ficha",
                "Cambio de Equipo", "Reclamo", "Desconexion a Pedido"
            ], help="Seleccione el tipo de reclamo")

            detalles = st.text_area("📝 Detalles del Reclamo", help="Describa el problema en detalle")
            precinto = st.text_input("🔒 N° de Precinto (opcional)", value=precinto)
            atendido_por = st.text_input("👤 Atendido por", help="Nombre de quien registra el reclamo")

            enviado = st.form_submit_button("✅ Guardar Reclamo", use_container_width=True)

        if enviado:
            if not nro_cliente:
                st.error("⚠️ Debes ingresar un número de cliente.")
            elif not atendido_por.strip():
                st.error("⚠️ El campo 'Atendido por' es obligatorio.")
            else:
                try:
                    fecha_hora = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
                    fila_reclamo = [
                        fecha_hora,
                        nro_cliente,
                        sector.strip(),
                        nombre.strip().upper(),
                        direccion.strip().upper(),
                        telefono.strip(),
                        tipo_reclamo.strip(),
                        detalles.strip().upper(),
                        "Pendiente",
                        precinto.strip(),
                        atendido_por.strip().upper()
                    ]

                    if guardar_reclamo(fila_reclamo):
                        st.success("✅ Reclamo guardado correctamente.")
                        if cliente_existente is None:
                            st.info("📂 Nuevo cliente agregado a la base de datos.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar el reclamo.")
                except Exception as e:
                    st.error("⚠️ Error inesperado al guardar")
                    print("Error al guardar reclamo:", e)
					
# --- SECCIÓN 2: RECLAMOS CARGADOS ---
elif opcion == "Reclamos cargados":
    st.subheader("📊 Reclamos cargados")
    try:
        df = get_reclamos()

        if df.empty:
            st.info("No hay reclamos registrados aún.")
            st.stop()

        # Panel visual por tipo
        st.markdown("### 📈 Distribución por tipo de reclamo (solo activos)")
        if "estado" in df.columns and "tipo_reclamo" in df.columns:
            df_activos = df[df["estado"].isin(["Pendiente", "En curso"])]
            if not df_activos.empty:
                conteo = df_activos["tipo_reclamo"].value_counts().sort_index()
                columnas = st.columns(4)
                for i, (tipo, cantidad) in enumerate(conteo.items()):
                    with columnas[i % 4]:
                        st.metric(label=f"📌 {tipo}", value=f"{cantidad}")
            st.metric(label="📊 TOTAL DE RECLAMOS ACTIVOS", value=len(df_activos))

        st.divider()

        # --- FILTROS ---
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_estado = st.selectbox("🔎 Filtrar por estado", ["Todos"] + sorted(df["estado"].dropna().unique()))
        with col2:
            filtro_sector = st.selectbox("🏙️ Filtrar por sector", ["Todos"] + sorted(df["sector"].dropna().unique()))
        with col3:
            filtro_tipo = st.selectbox("📌 Filtrar por tipo", ["Todos"] + sorted(df["tipo_reclamo"].dropna().unique()))

        if filtro_estado != "Todos":
            df = df[df["estado"] == filtro_estado]
        if filtro_sector != "Todos":
            df = df[df["sector"] == filtro_sector]
        if filtro_tipo != "Todos":
            df = df[df["tipo_reclamo"] == filtro_tipo]

        # --- EDITOR DE RECLAMOS ---
        st.markdown("### 📝 Editar reclamos")

        # Convertir a string para evitar errores de representación
        df_editable = df.copy()
        df_editable = df_editable.fillna("").astype(str)

        if "id" not in df_editable.columns:
            st.error("❌ No se encontró el campo 'id' en los reclamos. No se puede editar.")
            st.stop()

        edited_df = st.data_editor(
            df_editable,
            use_container_width=True,
            column_config={
                "estado": st.column_config.SelectboxColumn(
                    "Estado",
                    options=["Pendiente", "En curso", "Resuelto"],
                    help="Cambiar estado del reclamo"
                ),
                "tecnico": st.column_config.TextColumn("Técnico asignado", help="Asignar técnico(s)"),
                "precinto": st.column_config.TextColumn("N° de Precinto", help="Actualizar precinto")
            },
            hide_index=True
        )

        if st.button("💾 Guardar cambios", use_container_width=True):
            try:
                conn = get_db_connection()
                if conn is None:
                    st.error("❌ Error de conexión con la base de datos")
                else:
                    with conn.cursor() as cur:
                        for _, row in edited_df.iterrows():
                            # Validar ID antes del update
                            if row["id"]:
                                cur.execute("""
                                    UPDATE reclamos 
                                    SET estado = %s, 
                                        tecnico = %s, 
                                        precinto = %s
                                    WHERE id = %s
                                """, (
                                    row["estado"],
                                    row["tecnico"],
                                    row["precinto"],
                                    int(row["id"])
                                ))
                    conn.commit()
                    conn.close()
                    st.success("✅ Cambios guardados correctamente.")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error("⚠️ Error al guardar cambios.")
                print("Error en guardar cambios:", e)

    except Exception as e:
        st.error("❌ Error al cargar reclamos.")
        print("Error reclamos cargados:", e)

# --- SECCIÓN 3: HISTORIAL POR CLIENTE ---
elif opcion == "Historial por cliente":
    st.subheader("📖 Historial de reclamos por cliente")

    historial_cliente = st.text_input(
        "🔍 Ingresá N° de Cliente para ver su historial",
        help="Ingrese el número de cliente"
    ).strip()

    if historial_cliente:
        try:
            conn = get_db_connection()
            if conn is None:
                st.error("❌ Error de conexión con la base de datos")
            else:
                historial = pd.read_sql("""
                    SELECT fecha_hora, tipo_reclamo, estado, tecnico, precinto, detalles
                    FROM reclamos 
                    WHERE nro_cliente = %s
                    ORDER BY fecha_hora DESC
                """, conn, params=(historial_cliente,))
                conn.close()

                if not historial.empty:
                    st.success(f"🔎 Se encontraron {len(historial)} reclamos para el cliente {historial_cliente}.")
                    st.dataframe(historial, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ Este cliente no tiene reclamos registrados.")
        except Exception as e:
            st.error("⚠️ Error al cargar historial")
            print("Error historial por cliente:", e)

# --- SECCIÓN 4: EDITAR CLIENTE ---
elif opcion == "Editar cliente":
    st.subheader("🛠️ Editar datos de un cliente")
    cliente_editar = st.text_input("🔎 Ingresá N° de Cliente a editar", help="Ingrese el número de cliente").strip()

    if cliente_editar:
        try:
            conn = get_db_connection()
            if conn is None:
                st.error("❌ Error de conexión con la base de datos")
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM clientes WHERE nro_cliente = %s", (cliente_editar,))
                    cliente_row = cur.fetchone()

                    if cliente_row:
                        with st.form("form_editar_cliente"):
                            nuevo_sector = st.text_input("🏙️ Sector", value=cliente_row["sector"] or "")
                            nuevo_nombre = st.text_input("👤 Nombre", value=cliente_row["nombre"] or "")
                            nueva_direccion = st.text_input("📍 Dirección", value=cliente_row["direccion"] or "")
                            nuevo_telefono = st.text_input("📞 Teléfono", value=cliente_row["telefono"] or "")
                            nuevo_precinto = st.text_input("🔒 N° de Precinto", value=cliente_row["precinto"] or "")

                            if st.form_submit_button("💾 Actualizar datos del cliente", use_container_width=True):
                                try:
                                    cur.execute("""
                                        UPDATE clientes 
                                        SET sector = %s, nombre = %s, direccion = %s, 
                                            telefono = %s, precinto = %s
                                        WHERE nro_cliente = %s
                                    """, (
                                        nuevo_sector.strip().upper(),
                                        nuevo_nombre.strip().upper(),
                                        nueva_direccion.strip().upper(),
                                        nuevo_telefono.strip(),
                                        nuevo_precinto.strip(),
                                        cliente_editar
                                    ))
                                    conn.commit()
                                    st.success("✅ Cliente actualizado correctamente.")
                                except Exception as e:
                                    st.error("⚠️ Error al actualizar cliente.")
                                    print("Error al actualizar cliente:", e)
                    else:
                        st.warning("⚠️ Cliente no encontrado.")
        except Exception as e:
            st.error("❌ Error de conexión.")
            print("Error conexión editar cliente:", e)
        finally:
            if conn:
                conn.close()

    # --- CARGAR NUEVO CLIENTE ---
    st.divider()
    st.subheader("🆕 Cargar nuevo cliente")
    with st.form("form_nuevo_cliente"):
        nuevo_nro = st.text_input("🔢 N° de Cliente (nuevo)", help="Número único de cliente").strip()
        nuevo_sector = st.text_input("🏙️ Sector", help="Zona o sector del cliente")
        nuevo_nombre = st.text_input("👤 Nombre", help="Nombre completo del cliente")
        nueva_direccion = st.text_input("📍 Dirección", help="Dirección completa")
        nuevo_telefono = st.text_input("📞 Teléfono", help="Teléfono de contacto")
        nuevo_precinto = st.text_input("🔒 N° de Precinto (opcional)", help="Número de precinto si aplica")

        if st.form_submit_button("💾 Guardar nuevo cliente", use_container_width=True):
            if not nuevo_nro or not nuevo_nombre:
                st.error("⚠️ Debés ingresar al menos el N° de cliente y el nombre.")
            else:
                try:
                    conn = get_db_connection()
                    if conn is None:
                        st.error("❌ Error de conexión con la base de datos")
                    else:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO clientes 
                                (nro_cliente, sector, nombre, direccion, telefono, precinto)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                nuevo_nro.strip(),
                                nuevo_sector.strip().upper(),
                                nuevo_nombre.strip().upper(),
                                nueva_direccion.strip().upper(),
                                nuevo_telefono.strip(),
                                nuevo_precinto.strip()
                            ))
                            conn.commit()
                            st.success("✅ Nuevo cliente agregado correctamente.")
                            time.sleep(1)
                            st.rerun()
                except psycopg2.errors.UniqueViolation:
                    st.warning("⚠️ Este cliente ya existe.")
                except Exception as e:
                    st.error("❌ Error al guardar nuevo cliente.")
                    print("Error al guardar cliente nuevo:", e)
                finally:
                    if conn:
                        conn.close()

# --- SECCIÓN 5: IMPRESIÓN ---
elif opcion == "Imprimir reclamos":
    st.subheader("🖨️ Seleccionar reclamos para imprimir")
    try:
        df = get_reclamos()

        if df.empty:
            st.info("📭 No hay reclamos registrados aún.")
            st.stop()

        st.info("🕒 Reclamos pendientes de resolución")
        df_pendientes = df[df["estado"] == "Pendiente"]
        if not df_pendientes.empty:
            st.dataframe(
                df_pendientes[["fecha_hora", "nro_cliente", "nombre", "tipo_reclamo", "tecnico"]],
                use_container_width=True, hide_index=True
            )
        else:
            st.success("✅ No hay reclamos pendientes actualmente.")

        solo_pendientes = st.checkbox("📌 Mostrar solo reclamos pendientes para imprimir")
        if solo_pendientes:
            df = df[df["estado"] == "Pendiente"]

        # --- Selección por tipo ---
        st.markdown("### 📌 Imprimir reclamos por tipo")
        tipos_disponibles = sorted(df["tipo_reclamo"].dropna().unique())
        tipos_seleccionados = st.multiselect("Seleccioná tipos de reclamo a imprimir", tipos_disponibles)

        if tipos_seleccionados:
            df_filtrado = df[df["tipo_reclamo"].isin(tipos_seleccionados)]
            st.info(f"📌 Mostrando {len(df_filtrado)} reclamos de los tipos seleccionados")
        else:
            df_filtrado = df

        # --- Selección manual ---
        selected = st.multiselect(
            "Seleccioná reclamos específicos:",
            df_filtrado.index,
            format_func=lambda x: f"{df_filtrado.at[x, 'nro_cliente']} - {df_filtrado.at[x, 'nombre']}"
        )

        # --- Generar PDF ---
        if st.button("📄 Generar PDF", use_container_width=True):
            if not selected and not tipos_seleccionados:
                st.warning("⚠️ Seleccioná al menos un reclamo")
            else:
                reclamos_a_imprimir = df_filtrado.loc[selected] if selected else df_filtrado

                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4
                y = height - 40

                for i, (_, reclamo) in enumerate(reclamos_a_imprimir.iterrows()):
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(40, y, f"Reclamo #{reclamo.get('nro_cliente', '')}")
                    y -= 20

                    c.setFont("Helvetica", 12)
                    detalles = [
                        f"Fecha: {reclamo.get('fecha_hora', '')}",
                        f"Cliente: {reclamo.get('nombre', '')} ({reclamo.get('nro_cliente', '')})",
                        f"Dirección: {reclamo.get('direccion', '')}",
                        f"Tel: {reclamo.get('telefono', '')}",
                        f"Sector: {reclamo.get('sector', '')} | Precinto: {reclamo.get('precinto', '')}",
                        f"Técnico: {reclamo.get('tecnico', '')}",
                        f"Tipo: {reclamo.get('tipo_reclamo', '')}",
                        f"Detalles: {reclamo.get('detalles', '')[:100]}{'...' if len(reclamo.get('detalles', '')) > 100 else ''}"
                    ]

                    for linea in detalles:
                        c.drawString(40, y, linea)
                        y -= 15

                    y -= 10
                    c.drawString(40, y, "Firma técnico: _____________________________")
                    y -= 30

                    if y < 100 and i < len(reclamos_a_imprimir) - 1:
                        c.showPage()
                        y = height - 40

                c.save()
                buffer.seek(0)

                st.download_button(
                    label="📥 Descargar PDF",
                    data=buffer,
                    file_name="reclamos.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    except Exception as e:
        st.error("❌ Error al generar PDF.")
        print("Error impresión PDF:", e)

# --- SECCIÓN 6: SEGUIMIENTO TÉCNICO ---
elif opcion == "Seguimiento técnico":
    st.subheader("🛠️ Seguimiento técnico del reclamo")

    cliente_input = st.text_input(
        "🔍 Ingresá el N° de Cliente para actualizar su reclamo",
        help="Ingrese el número de cliente"
    ).strip()

    if cliente_input:
        try:
            conn = get_db_connection()
            if conn is None:
                st.error("❌ Error de conexión con la base de datos")
            else:
                df_filtrado = pd.read_sql("""
                    SELECT * FROM reclamos 
                    WHERE nro_cliente = %s 
                    AND estado IN ('Pendiente', 'En curso')
                    ORDER BY fecha_hora DESC
                    LIMIT 1
                """, conn, params=(cliente_input,))

                if not df_filtrado.empty:
                    reclamo_actual = df_filtrado.iloc[0]

                    st.info(f"🕒 Reclamo registrado el {reclamo_actual.get('fecha_hora', 'Sin fecha')}")
                    st.write(f"📌 Tipo: **{reclamo_actual.get('tipo_reclamo', 'No registrado')}**")
                    st.write(f"📍 Dirección: {reclamo_actual.get('direccion', 'Sin dirección')}")
                    st.write(f"🔒 Precinto: {reclamo_actual.get('precinto', 'No informado')}")
                    st.write(f"📄 Detalles: {reclamo_actual.get('detalles', 'Sin detalles')}")

                    nuevo_estado = st.selectbox(
                        "🔄 Cambiar estado",
                        ["Pendiente", "En curso", "Resuelto"],
                        index=["Pendiente", "En curso", "Resuelto"].index(reclamo_actual.get("estado", "Pendiente"))
                    )

                    tecnicos_actuales = []
                    if reclamo_actual.get("tecnico"):
                        tecnicos_actuales = [t.strip() for t in reclamo_actual.get("tecnico", "").split(",") if t.strip()]

                    nuevos_tecnicos = st.multiselect(
                        "👷 Técnicos asignados",
                        tecnicos_disponibles,
                        default=[t for t in tecnicos_disponibles if t in tecnicos_actuales],
                        help="Seleccione los técnicos asignados"
                    )

                    if st.button("💾 Actualizar reclamo", use_container_width=True):
                        if not nuevos_tecnicos:
                            st.warning("⚠️ Debes asignar al menos un técnico")
                        else:
                            try:
                                with conn.cursor() as cur:
                                    cur.execute("""
                                        UPDATE reclamos 
                                        SET estado = %s, 
                                            tecnico = %s
                                        WHERE id = %s
                                    """, (
                                        nuevo_estado,
                                        ", ".join(nuevos_tecnicos),
                                        reclamo_actual["id"]
                                    ))
                                conn.commit()
                                st.success("✅ Reclamo actualizado correctamente.")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error("⚠️ Error al actualizar el reclamo.")
                                print("Error en actualización:", e)
                else:
                    st.warning("ℹ️ Este cliente no tiene reclamos pendientes o en curso.")
        except Exception as e:
            st.error("❌ Error de conexión.")
            print("Error seguimiento técnico:", e)
        finally:
            if conn:
                conn.close()

# --- SECCIÓN 7: CIERRE DE RECLAMOS ---
elif opcion == "Cierre de Reclamos":
    st.subheader("✅ Cierre de reclamos en curso")
    try:
        conn = get_db_connection()
        if conn is None:
            st.error("❌ Error de conexión con la base de datos")
        else:
            en_curso = pd.read_sql("""
                SELECT r.*, c.precinto as precinto_cliente 
                FROM reclamos r
                LEFT JOIN clientes c ON r.nro_cliente = c.nro_cliente
                WHERE r.estado = 'En curso'
            """, conn)

            if en_curso.empty:
                st.info("📭 No hay reclamos en curso en este momento.")
            else:
                # --- Filtro por técnico ---
                tecnicos_unicos = sorted(set(", ".join(en_curso["tecnico"].fillna("")).split(", ")))
                tecnicos_unicos = [t for t in tecnicos_unicos if t]  # Quitar vacíos
                tecnicos_seleccionados = st.multiselect("👷 Filtrar por técnico asignado", tecnicos_unicos)

                if tecnicos_seleccionados:
                    en_curso = en_curso[
                        en_curso["tecnico"].apply(
                            lambda t: any(tecnico in str(t) for tecnico in tecnicos_seleccionados)
                        )
                    ]

                st.dataframe(
                    en_curso[["nro_cliente", "nombre", "tipo_reclamo", "tecnico"]],
                    use_container_width=True,
                    hide_index=True
                )

                for _, row in en_curso.iterrows():
                    with st.expander(f"📂 Reclamo #{row['nro_cliente']} - {row['nombre']}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            nuevo_precinto = st.text_input(
                                "🔒 Precinto",
                                value=row.get("precinto_cliente", ""),
                                key=f"precinto_{row['id']}"
                            )

                        with col2:
                            if st.button("✅ Marcar como Resuelto", key=f"resolver_{row['id']}", use_container_width=True):
                                try:
                                    with conn.cursor() as cur:
                                        # Marcar como resuelto
                                        cur.execute("""
                                            UPDATE reclamos 
                                            SET estado = 'Resuelto',
                                                fecha_resolucion = %s
                                            WHERE id = %s
                                        """, (
                                            datetime.now(pytz.timezone("America/Argentina/Buenos_Aires")),
                                            row["id"]
                                        ))

                                        # Actualizar precinto si se modificó
                                        if nuevo_precinto.strip():
                                            cur.execute("""
                                                UPDATE clientes 
                                                SET precinto = %s 
                                                WHERE nro_cliente = %s
                                            """, (
                                                nuevo_precinto.strip(),
                                                row["nro_cliente"]
                                            ))

                                    conn.commit()
                                    st.success(f"✅ Reclamo de {row['nombre']} cerrado correctamente.")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error("⚠️ Error al cerrar reclamo.")
                                    print("Error cierre reclamo:", e)
        conn.close()
    except Exception as e:
        st.error("❌ Error de conexión.")
        print("Error en cierre reclamos:", e)

# --- SIDEBAR INFORMATIVO + LOGOUT ---
with st.sidebar:
    st.markdown("## 👤 Sesión activa")
    st.write(f"**Usuario:** `{st.session_state.usuario_actual}`")
    
    hora_actual = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires")).strftime("%d/%m/%Y %H:%M:%S")
    st.write(f"🕒 **Hora actual:** {hora_actual}")
    
    # Resumen rápido del sistema
    df_reclamos_sidebar = get_reclamos()
    if not df_reclamos_sidebar.empty:
        activos_sidebar = df_reclamos_sidebar[df_reclamos_sidebar["estado"].isin(["Pendiente", "En curso"])]
        st.metric("📋 Reclamos activos", len(activos_sidebar))
    else:
        st.metric("📋 Reclamos activos", 0)

    st.divider()

    # Cierre de sesión con confirmación
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        confirm = st.radio("¿Estás seguro?", ["No", "Sí"], index=0, horizontal=True)
        if confirm == "Sí":
            st.session_state.logueado = False
            st.session_state.usuario_actual = ""
            st.rerun()
