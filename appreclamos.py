# appreclamos.py - Sistema de Reclamos Optimizado y Corregido
import streamlit as st
import psycopg2
from datetime import datetime
import pytz
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import io
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Fusion Reclamos App", 
    page_icon="📋", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Variables de conexión a la base de datos
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

# Función de conexión mejorada
@st.cache_resource
def get_connection():
    """Obtiene una conexión a la base de datos con manejo de errores mejorado"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            cursor_factory=RealDictCursor,
            sslmode='require',
            connect_timeout=10
        )
        return conn
    except psycopg2.Error as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        logger.error(f"Database connection error: {e}")
        return None
    except Exception as e:
        st.error(f"Error inesperado: {e}")
        logger.error(f"Unexpected error: {e}")
        return None

# Funciones de utilidad mejoradas
def ejecutar_consulta(query, params=None, fetch=True):
    """Ejecuta una consulta SQL con manejo de errores mejorado"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                result = cur.fetchall()
                return result
            else:
                conn.commit()
                return True
    except psycopg2.Error as e:
        st.error(f"Error en la consulta SQL: {e}")
        logger.error(f"SQL query error: {e}")
        if conn:
            conn.rollback()
        return None
    except Exception as e:
        st.error(f"Error inesperado en la consulta: {e}")
        logger.error(f"Unexpected query error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def cargar_clientes():
    """Carga todos los clientes de la base de datos"""
    query = "SELECT * FROM clientes ORDER BY nro_cliente"
    result = ejecutar_consulta(query)
    if result:
        return pd.DataFrame(result)
    return pd.DataFrame()

def cargar_reclamos():
    """Carga todos los reclamos con información completa"""
    query = """
    SELECT 
        r.id,
        r.nro_cliente,
        COALESCE(c.nombre, 'Cliente no encontrado') as cliente_nombre,
        COALESCE(c.direccion, 'Sin dirección') as direccion,
        COALESCE(c.telefono, 'Sin teléfono') as telefono,
        COALESCE(c.sector, 'Sin sector') as sector,
        r.tipo_reclamo,
        r.detalles,
        COALESCE(r.precinto, '') as precinto,
        r.estado,
        COALESCE(r.tecnico, '') as tecnico,
        r.fecha_creacion,
        r.fecha_resolucion,
        r.prioridad
    FROM reclamos r
    LEFT JOIN clientes c ON r.nro_cliente = c.nro_cliente
    ORDER BY r.fecha_creacion DESC
    """
    result = ejecutar_consulta(query)
    if result:
        return pd.DataFrame(result)
    return pd.DataFrame()

def buscar_cliente(nro_cliente):
    """Busca un cliente específico por número"""
    query = "SELECT * FROM clientes WHERE nro_cliente = %s"
    result = ejecutar_consulta(query, (nro_cliente,))
    if result and len(result) > 0:
        return dict(result[0])
    return None

def crear_reclamo(datos_reclamo):
    """Crea un nuevo reclamo en la base de datos"""
    query = """
    INSERT INTO reclamos (
        nro_cliente, tipo_reclamo, detalles, precinto, 
        estado, prioridad, fecha_creacion
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    fecha_actual = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
    params = (
        datos_reclamo['nro_cliente'],
        datos_reclamo['tipo_reclamo'],
        datos_reclamo['detalles'],
        datos_reclamo.get('precinto', ''),
        'Pendiente',
        datos_reclamo.get('prioridad', 'Media'),
        fecha_actual
    )
    return ejecutar_consulta(query, params, fetch=False)

def actualizar_estado_reclamo(id_reclamo, estado, tecnico=None):
    """Actualiza el estado de un reclamo"""
    fecha_resolucion = None
    if estado in ['Resuelto', 'Cerrado']:
        fecha_resolucion = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
    
    query = """
    UPDATE reclamos 
    SET estado = %s, tecnico = %s, fecha_resolucion = %s
    WHERE id = %s
    """
    params = (estado, tecnico, fecha_resolucion, id_reclamo)
    return ejecutar_consulta(query, params, fetch=False)

def crear_cliente(datos_cliente):
    """Crea un nuevo cliente en la base de datos"""
    query = """
    INSERT INTO clientes (nro_cliente, nombre, direccion, telefono, email, sector)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (
        datos_cliente['nro_cliente'],
        datos_cliente['nombre'],
        datos_cliente['direccion'],
        datos_cliente['telefono'],
        datos_cliente.get('email', ''),
        datos_cliente['sector']
    )
    return ejecutar_consulta(query, params, fetch=False)

# Función para generar PDF mejorada
def generar_pdf_reclamo(reclamo_data):
    """Genera un PDF con los datos del reclamo"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    title = Paragraph("REPORTE DE RECLAMO", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Datos del reclamo
    data = [
        ['ID Reclamo:', str(reclamo_data.get('id', 'N/A'))],
        ['Número Cliente:', str(reclamo_data.get('nro_cliente', 'N/A'))],
        ['Cliente:', str(reclamo_data.get('cliente_nombre', 'N/A'))],
        ['Dirección:', str(reclamo_data.get('direccion', 'N/A'))],
        ['Teléfono:', str(reclamo_data.get('telefono', 'N/A'))],
        ['Sector:', str(reclamo_data.get('sector', 'N/A'))],
        ['Tipo Reclamo:', str(reclamo_data.get('tipo_reclamo', 'N/A'))],
        ['Estado:', str(reclamo_data.get('estado', 'N/A'))],
        ['Técnico:', str(reclamo_data.get('tecnico', 'No asignado'))],
        ['Fecha Creación:', str(reclamo_data.get('fecha_creacion', 'N/A'))],
        ['Prioridad:', str(reclamo_data.get('prioridad', 'N/A'))],
    ]
    
    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Detalles
    if reclamo_data.get('detalles'):
        detalles_title = Paragraph("DETALLES DEL RECLAMO:", styles['Heading2'])
        story.append(detalles_title)
        detalles_text = Paragraph(str(reclamo_data['detalles']), styles['Normal'])
        story.append(detalles_text)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# SECCIÓN: INICIO
def seccion_inicio():
    st.title("🏢 Sistema de Gestión de Reclamos - Fusion")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    # Estadísticas generales
    reclamos_df = cargar_reclamos()
    clientes_df = cargar_clientes()
    
    with col1:
        st.metric("Total Clientes", len(clientes_df))
    
    with col2:
        st.metric("Total Reclamos", len(reclamos_df))
    
    with col3:
        if not reclamos_df.empty:
            pendientes = len(reclamos_df[reclamos_df['estado'] == 'Pendiente'])
            st.metric("Reclamos Pendientes", pendientes)
        else:
            st.metric("Reclamos Pendientes", 0)
    
    st.markdown("---")
    
    # Gráfico de estados de reclamos
    if not reclamos_df.empty:
        st.subheader("📊 Estado de Reclamos")
        estado_counts = reclamos_df['estado'].value_counts()
        st.bar_chart(estado_counts)
        
        st.subheader("📈 Reclamos por Prioridad")
        prioridad_counts = reclamos_df['prioridad'].value_counts()
        st.bar_chart(prioridad_counts)

# SECCIÓN: NUEVO RECLAMO
def seccion_nuevo_reclamo():
    st.title("📝 Nuevo Reclamo")
    st.markdown("---")
    
    with st.form("nuevo_reclamo_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nro_cliente = st.text_input("Número de Cliente *", placeholder="Ej: 12345")
            
            if nro_cliente:
                cliente = buscar_cliente(nro_cliente)
                if cliente:
                    st.success(f"✅ Cliente encontrado: {cliente['nombre']}")
                    st.info(f"📍 Dirección: {cliente['direccion']}")
                    st.info(f"📞 Teléfono: {cliente['telefono']}")
                    st.info(f"🏢 Sector: {cliente['sector']}")
                else:
                    st.warning("⚠️ Cliente no encontrado. ¿Desea crear un nuevo cliente?")
                    
                    if st.checkbox("Crear nuevo cliente"):
                        nombre = st.text_input("Nombre del Cliente *")
                        direccion = st.text_input("Dirección *")
                        telefono = st.text_input("Teléfono *")
                        email = st.text_input("Email")
                        sector = st.selectbox("Sector *", [
                            "Residencial", "Comercial", "Industrial", "Rural"
                        ])
                        
                        if st.form_submit_button("Crear Cliente"):
                            if nombre and direccion and telefono and sector:
                                datos_cliente = {
                                    'nro_cliente': nro_cliente,
                                    'nombre': nombre,
                                    'direccion': direccion,
                                    'telefono': telefono,
                                    'email': email,
                                    'sector': sector
                                }
                                if crear_cliente(datos_cliente):
                                    st.success("✅ Cliente creado exitosamente")
                                    st.rerun()
                                else:
                                    st.error("❌ Error al crear el cliente")
                            else:
                                st.error("❌ Complete todos los campos obligatorios")
        
        with col2:
            tipo_reclamo = st.selectbox("Tipo de Reclamo *", [
                "Falta de Suministro",
                "Medidor Defectuoso", 
                "Facturación Incorrecta",
                "Corte de Servicio",
                "Problema de Tensión",
                "Daño en Instalaciones",
                "Otro"
            ])
            
            prioridad = st.selectbox("Prioridad *", [
                "Baja", "Media", "Alta", "Urgente"
            ])
            
            precinto = st.text_input("Número de Precinto")
        
        detalles = st.text_area("Detalles del Reclamo *", height=100)
        
        submitted = st.form_submit_button("🚀 Crear Reclamo", type="primary")
        
        if submitted:
            if nro_cliente and tipo_reclamo and detalles:
                cliente = buscar_cliente(nro_cliente)
                if cliente:
                    datos_reclamo = {
                        'nro_cliente': nro_cliente,
                        'tipo_reclamo': tipo_reclamo,
                        'detalles': detalles,
                        'precinto': precinto,
                        'prioridad': prioridad
                    }
                    
                    if crear_reclamo(datos_reclamo):
                        st.success("✅ Reclamo creado exitosamente")
                        st.balloons()
                    else:
                        st.error("❌ Error al crear el reclamo")
                else:
                    st.error("❌ Debe existir el cliente para crear el reclamo")
            else:
                st.error("❌ Complete todos los campos obligatorios")

# SECCIÓN: RECLAMOS CARGADOS
def seccion_reclamos_cargados():
    st.title("📋 Reclamos Cargados")
    st.markdown("---")
    
    reclamos_df = cargar_reclamos()
    
    if reclamos_df.empty:
        st.info("📭 No hay reclamos cargados")
        return
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_estado = st.selectbox("Filtrar por Estado", 
                                   ["Todos"] + list(reclamos_df['estado'].unique()))
    
    with col2:
        filtro_prioridad = st.selectbox("Filtrar por Prioridad",
                                      ["Todos"] + list(reclamos_df['prioridad'].unique()))
    
    with col3:
        filtro_sector = st.selectbox("Filtrar por Sector",
                                   ["Todos"] + list(reclamos_df['sector'].dropna().unique()))
    
    # Aplicar filtros
    df_filtrado = reclamos_df.copy()
    
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]
    
    if filtro_prioridad != "Todos":
        df_filtrado = df_filtrado[df_filtrado['prioridad'] == filtro_prioridad]
    
    if filtro_sector != "Todos":
        df_filtrado = df_filtrado[df_filtrado['sector'] == filtro_sector]
    
    st.subheader(f"📊 Mostrando {len(df_filtrado)} reclamos")
    
    # Mostrar reclamos
    for idx, reclamo in df_filtrado.iterrows():
        with st.expander(f"🎫 Reclamo #{reclamo['id']} - {reclamo['cliente_nombre']} - {reclamo['estado']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**👤 Cliente:** {reclamo['cliente_nombre']}")
                st.write(f"**📞 Teléfono:** {reclamo['telefono']}")
                st.write(f"**📍 Dirección:** {reclamo['direccion']}")
                st.write(f"**🏢 Sector:** {reclamo['sector']}")
                st.write(f"**📌 Tipo:** {reclamo['tipo_reclamo']}")
            
            with col2:
                st.write(f"**📊 Estado:** {reclamo['estado']}")
                st.write(f"**⚡ Prioridad:** {reclamo['prioridad']}")
                st.write(f"**👨‍🔧 Técnico:** {reclamo['tecnico'] or 'No asignado'}")
                st.write(f"**📅 Fecha:** {reclamo['fecha_creacion']}")
                if reclamo['precinto']:
                    st.write(f"**🔒 Precinto:** {reclamo['precinto']}")
            
            st.write(f"**📄 Detalles:** {reclamo['detalles']}")
            
            # Botón para generar PDF
            if st.button(f"📄 Generar PDF", key=f"pdf_{reclamo['id']}"):
                pdf_buffer = generar_pdf_reclamo(reclamo)
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_buffer,
                    file_name=f"reclamo_{reclamo['id']}.pdf",
                    mime="application/pdf",
                    key=f"download_{reclamo['id']}"
                )

# SECCIÓN: SEGUIMIENTO TÉCNICO
def seccion_seguimiento_tecnico():
    st.title("🔧 Seguimiento Técnico")
    st.markdown("---")
    
    reclamos_df = cargar_reclamos()
    
    if reclamos_df.empty:
        st.info("📭 No hay reclamos para seguimiento")
        return
    
    # Filtrar reclamos pendientes y en proceso
    reclamos_activos = reclamos_df[reclamos_df['estado'].isin(['Pendiente', 'En Proceso'])]
    
    if reclamos_activos.empty:
        st.info("✅ No hay reclamos activos para seguimiento")
        return
    
    st.subheader(f"🎯 Reclamos Activos ({len(reclamos_activos)})")
    
    for idx, reclamo in reclamos_activos.iterrows():
        with st.expander(f"🎫 Reclamo #{reclamo['id']} - {reclamo['cliente_nombre']} - {reclamo['estado']}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**👤 Cliente:** {reclamo['cliente_nombre']}")
                st.write(f"**📞 Teléfono:** {reclamo['telefono']}")
                st.write(f"**📍 Dirección:** {reclamo['direccion']}")
                st.write(f"**🏢 Sector:** {reclamo['sector']}")
                st.write(f"**📌 Tipo:** {reclamo['tipo_reclamo']}")
                if reclamo['precinto']:
                    st.write(f"**🔒 Precinto:** {reclamo['precinto']}")
                st.write(f"**📄 Detalles:** {reclamo['detalles']}")
                st.write(f"**⚡ Prioridad:** {reclamo['prioridad']}")
            
            with col2:
                st.subheader("🔄 Actualizar Estado")
                
                nuevo_estado = st.selectbox(
                    "Estado:",
                    ["Pendiente", "En Proceso", "Resuelto", "Cerrado"],
                    index=["Pendiente", "En Proceso", "Resuelto", "Cerrado"].index(reclamo['estado']),
                    key=f"estado_{reclamo['id']}"
                )
                
                tecnico = st.text_input(
                    "Técnico Asignado:",
                    value=reclamo['tecnico'] or "",
                    key=f"tecnico_{reclamo['id']}"
                )
                
                if st.button(f"💾 Actualizar", key=f"actualizar_{reclamo['id']}", type="primary"):
                    if actualizar_estado_reclamo(reclamo['id'], nuevo_estado, tecnico):
                        st.success("✅ Reclamo actualizado exitosamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar el reclamo")

# SECCIÓN: HISTORIAL POR CLIENTE
def seccion_historial_cliente():
    st.title("📚 Historial por Cliente")
    st.markdown("---")
    
    clientes_df = cargar_clientes()
    
    if clientes_df.empty:
        st.info("👥 No hay clientes registrados")
        return
    
    # Selector de cliente
    cliente_seleccionado = st.selectbox(
        "Seleccionar Cliente:",
        options=clientes_df['nro_cliente'].tolist(),
        format_func=lambda x: f"{x} - {clientes_df[clientes_df['nro_cliente'] == x]['nombre'].iloc[0]}"
    )
    
    if cliente_seleccionado:
        # Información del cliente
        cliente_info = clientes_df[clientes_df['nro_cliente'] == cliente_seleccionado].iloc[0]
        
        st.subheader(f"👤 Información del Cliente")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Número:** {cliente_info['nro_cliente']}")
            st.write(f"**Nombre:** {cliente_info['nombre']}")
            st.write(f"**Dirección:** {cliente_info['direccion']}")
        
        with col2:
            st.write(f"**Teléfono:** {cliente_info['telefono']}")
            st.write(f"**Email:** {cliente_info.get('email', 'No registrado')}")
            st.write(f"**Sector:** {cliente_info['sector']}")
        
        st.markdown("---")
        
        # Historial de reclamos
        reclamos_df = cargar_reclamos()
        reclamos_cliente = reclamos_df[reclamos_df['nro_cliente'] == cliente_seleccionado]
        
        if reclamos_cliente.empty:
            st.info("📭 Este cliente no tiene reclamos registrados")
        else:
            st.subheader(f"📋 Historial de Reclamos ({len(reclamos_cliente)})")
            
            # Estadísticas del cliente
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Reclamos", len(reclamos_cliente))
            
            with col2:
                pendientes = len(reclamos_cliente[reclamos_cliente['estado'] == 'Pendiente'])
                st.metric("Pendientes", pendientes)
            
            with col3:
                resueltos = len(reclamos_cliente[reclamos_cliente['estado'] == 'Resuelto'])
                st.metric("Resueltos", resueltos)
            
            # Lista de reclamos
            for idx, reclamo in reclamos_cliente.iterrows():
                with st.expander(f"🎫 Reclamo #{reclamo['id']} - {reclamo['tipo_reclamo']} - {reclamo['estado']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**📌 Tipo:** {reclamo['tipo_reclamo']}")
                        st.write(f"**📊 Estado:** {reclamo['estado']}")
                        st.write(f"**⚡ Prioridad:** {reclamo['prioridad']}")
                        st.write(f"**📅 Fecha Creación:** {reclamo['fecha_creacion']}")
                    
                    with col2:
                        st.write(f"**👨‍🔧 Técnico:** {reclamo['tecnico'] or 'No asignado'}")
                        if reclamo['fecha_resolucion']:
                            st.write(f"**✅ Fecha Resolución:** {reclamo['fecha_resolucion']}")
                        if reclamo['precinto']:
                            st.write(f"**🔒 Precinto:** {reclamo['precinto']}")
                    
                    st.write(f"**📄 Detalles:** {reclamo['detalles']}")

# SECCIÓN: EDITAR CLIENTE
def seccion_editar_cliente():
    st.title("✏️ Editar Cliente")
    st.markdown("---")
    
    clientes_df = cargar_clientes()
    
    if clientes_df.empty:
        st.info("👥 No hay clientes registrados")
        return
    
    # Selector de cliente
    cliente_seleccionado = st.selectbox(
        "Seleccionar Cliente a Editar:",
        options=clientes_df['nro_cliente'].tolist(),
        format_func=lambda x: f"{x} - {clientes_df[clientes_df['nro_cliente'] == x]['nombre'].iloc[0]}"
    )
    
    if cliente_seleccionado:
        cliente_info = clientes_df[clientes_df['nro_cliente'] == cliente_seleccionado].iloc[0]
        
        with st.form("editar_cliente_form"):
            st.subheader(f"📝 Editando Cliente: {cliente_info['nombre']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nro_cliente = st.text_input("Número de Cliente", value=cliente_info['nro_cliente'], disabled=True)
                nombre = st.text_input("Nombre *", value=cliente_info['nombre'])
                direccion = st.text_input("Dirección *", value=cliente_info['direccion'])
            
            with col2:
                telefono = st.text_input("Teléfono *", value=cliente_info['telefono'])
                email = st.text_input("Email", value=cliente_info.get('email', ''))
                sector = st.selectbox("Sector *", 
                                    ["Residencial", "Comercial", "Industrial", "Rural"],
                                    index=["Residencial", "Comercial", "Industrial", "Rural"].index(cliente_info['sector']))
            
            submitted = st.form_submit_button("💾 Guardar Cambios", type="primary")
            
            if submitted:
                if nombre and direccion and telefono and sector:
                    query = """
                    UPDATE clientes 
                    SET nombre=%s, direccion=%s, telefono=%s, email=%s, sector=%s
                    WHERE nro_cliente=%s
                    """
                    params = (nombre, direccion, telefono, email, sector, nro_cliente)
                    
                    if ejecutar_consulta(query, params, fetch=False):
                        st.success("✅ Cliente actualizado exitosamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar el cliente")
                else:
                    st.error("❌ Complete todos los campos obligatorios")

# NAVEGACIÓN PRINCIPAL
def main():
    st.sidebar.title("🏢 Fusion Reclamos")
    st.sidebar.markdown("---")
    
    # Menú de navegación
    opciones = {
        "🏠 Inicio": seccion_inicio,
        "📝 Nuevo Reclamo": seccion_nuevo_reclamo,
        "📋 Reclamos Cargados": seccion_reclamos_cargados,
        "🔧 Seguimiento Técnico": seccion_seguimiento_tecnico,
        "📚 Historial por Cliente": seccion_historial_cliente,
        "✏️ Editar Cliente": seccion_editar_cliente,
    }
    
    seleccion = st.sidebar.radio("Navegación", list(opciones.keys()))
    
    # Información de conexión en sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 Estado de Conexión")
    
    conn = get_connection()
    if conn:
        st.sidebar.success("✅ Conectado a la base de datos")
        conn.close()
    else:
        st.sidebar.error("❌ Error de conexión")
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Tip:** Use los filtros para encontrar reclamos específicos más rápidamente.")
    
    # Ejecutar la sección seleccionada
    opciones[seleccion]()

if __name__ == "__main__":
    main()
            with col2:
                st.subheader("🔄 Actualizar Estado")
                
                nuevo_estado = st.selectbox(
                    "Estado:",
                    ["Pendiente", "En Proceso", "Resuelto", "Cerrado"],
                    index=["Pendiente", "En Proceso", "Resuelto", "Cerrado"].index(reclamo['estado']),
                    key=f"estado_{reclamo['id']}"
                )
                
                tecnico = st.text_input(
                    "Técnico Asignado:",
                    value=reclamo['tecnico'] or "",
                    key=f"tecnico_{reclamo['id']}"
                )
                
                if st.button(f"💾 Actualizar", key=f"actualizar_{reclamo['id']}", type="primary"):
                    if actualizar_estado_reclamo(reclamo['id'], nuevo_estado, tecnico):
                        st.success("✅ Reclamo actualizado exitosamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar el reclamo")

# SECCIÓN: HISTORIAL POR CLIENTE
def seccion_historial_cliente():
    st.title("📚 Historial por Cliente")
    st.markdown("---")
    
    clientes_df = cargar_clientes()
    
    if clientes_df.empty:
        st.info("👥 No hay clientes registrados")
        return
    
    # Selector de cliente
    cliente_seleccionado = st.selectbox(
        "Seleccionar Cliente:",
        options=clientes_df['nro_cliente'].tolist(),
        format_func=lambda x: f"{x} - {clientes_df[clientes_df['nro_cliente'] == x]['nombre'].iloc[0]}"
    )
    
    if cliente_seleccionado:
        # Información del cliente
        cliente_info = clientes_df[clientes_df['nro_cliente'] == cliente_seleccionado].iloc[0]
        
        st.subheader(f"👤 Información del Cliente")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Número:** {cliente_info['nro_cliente']}")
            st.write(f"**Nombre:** {cliente_info['nombre']}")
            st.write(f"**Dirección:** {cliente_info['direccion']}")
        
        with col2:
            st.write(f"**Teléfono:** {cliente_info['telefono']}")
            st.write(f"**Email:** {cliente_info.get('email', 'No registrado')}")
            st.write(f"**Sector:** {cliente_info['sector']}")
        
        st.markdown("---")
        
        # Historial de reclamos
        reclamos_df = cargar_reclamos()
        reclamos_cliente = reclamos_df[reclamos_df['nro_cliente'] == cliente_seleccionado]
        
        if reclamos_cliente.empty:
            st.info("📭 Este cliente no tiene reclamos registrados")
        else:
            st.subheader(f"📋 Historial de Reclamos ({len(reclamos_cliente)})")
            
            # Estadísticas del cliente
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Reclamos", len(reclamos_cliente))
            
            with col2:
                pendientes = len(reclamos_cliente[reclamos_cliente['estado'] == 'Pendiente'])
                st.metric("Pendientes", pendientes)
            
            with col3:
                resueltos = len(reclamos_cliente[reclamos_cliente['estado'] == 'Resuelto'])
                st.metric("Resueltos", resueltos)
            
            # Lista de reclamos
            for idx, reclamo in reclamos_cliente.iterrows():
                with st.expander(f"🎫 Reclamo #{reclamo['id']} - {reclamo['tipo_reclamo']} - {reclamo['estado']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**📌 Tipo:** {reclamo['tipo_reclamo']}")
                        st.write(f"**📊 Estado:** {reclamo['estado']}")
                        st.write(f"**⚡ Prioridad:** {reclamo['prioridad']}")
                        st.write(f"**📅 Fecha Creación:** {reclamo['fecha_creacion']}")
                    
                    with col2:
                        st.write(f"**👨‍🔧 Técnico:** {reclamo['tecnico'] or 'No asignado'}")
                        if reclamo['fecha_resolucion']:
                            st.write(f"**✅ Fecha Resolución:** {reclamo['fecha_resolucion']}")
                        if reclamo['precinto']:
                            st.write(f"**🔒 Precinto:** {reclamo['precinto']}")
                    
                    st.write(f"**📄 Detalles:** {reclamo['detalles']}")

# SECCIÓN: EDITAR CLIENTE
def seccion_editar_cliente():
    st.title("✏️ Editar Cliente")
    st.markdown("---")
    
    clientes_df = cargar_clientes()
    
    if clientes_df.empty:
        st.info("👥 No hay clientes registrados")
        return
    
    # Selector de cliente
    cliente_seleccionado = st.selectbox(
        "Seleccionar Cliente a Editar:",
        options=clientes_df['nro_cliente'].tolist(),
        format_func=lambda x: f"{x} - {clientes_df[clientes_df['nro_cliente'] == x]['nombre'].iloc[0]}"
    )
    
    if cliente_seleccionado:
        cliente_info = clientes_df[clientes_df['nro_cliente'] == cliente_seleccionado].iloc[0]
        
        with st.form("editar_cliente_form"):
            st.subheader(f"📝 Editando Cliente: {cliente_info['nombre']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nro_cliente = st.text_input("Número de Cliente", value=cliente_info['nro_cliente'], disabled=True)
                nombre = st.text_input("Nombre *", value=cliente_info['nombre'])
                direccion = st.text_input("Dirección *", value=cliente_info['direccion'])
            
            with col2:
                telefono = st.text_input("Teléfono *", value=cliente_info['telefono'])
                email = st.text_input("Email", value=cliente_info.get('email', ''))
                sector = st.selectbox("Sector *", 
                                    ["Residencial", "Comercial", "Industrial", "Rural"],
                                    index=["Residencial", "Comercial", "Industrial", "Rural"].index(cliente_info['sector']))
            
            submitted = st.form_submit_button("💾 Guardar Cambios", type="primary")
            
            if submitted:
                if nombre and direccion and telefono and sector:
                    query = """
                    UPDATE clientes 
                    SET nombre=%s, direccion=%s, telefono=%s, email=%s, sector=%s
                    WHERE nro_cliente=%s
                    """
                    params = (nombre, direccion, telefono, email, sector, nro_cliente)
                    
                    if ejecutar_consulta(query, params, fetch=False):
                        st.success("✅ Cliente actualizado exitosamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar el cliente")
                else:
                    st.error("❌ Complete todos los campos obligatorios")

# SECCIÓN: IMPRIMIR RECLAMOS
def seccion_imprimir_reclamos():
    st.title("🖨️ Imprimir Reclamos")
    st.markdown("---")
    
    reclamos_df = cargar_reclamos()
    
    if reclamos_df.empty:
        st.info("📭 No hay reclamos para imprimir")
        return
    
    # Filtros para impresión
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_estado = st.selectbox("Filtrar por Estado", 
                                   ["Todos"] + list(reclamos_df['estado'].unique()))
    
    with col2:
        filtro_prioridad = st.selectbox("Filtrar por Prioridad",
                                      ["Todos"] + list(reclamos_df['prioridad'].unique()))
    
    with col3:
        filtro_sector = st.selectbox("Filtrar por Sector",
                                   ["Todos"] + list(reclamos_df['sector'].dropna().unique()))
    
    # Aplicar filtros
    df_filtrado = reclamos_df.copy()
    
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]
    
    if filtro_prioridad != "Todos":
        df_filtrado = df_filtrado[df_filtrado['prioridad'] == filtro_prioridad]
    
    if filtro_sector != "Todos":
        df_filtrado = df_filtrado[df_filtrado['sector'] == filtro_sector]
    
    st.subheader(f"📊 Reclamos para Imprimir ({len(df_filtrado)})")
    
    if not df_filtrado.empty:
        # Mostrar reclamos seleccionados
        for idx, reclamo in df_filtrado.iterrows():
            with st.expander(f"🎫 Reclamo #{reclamo['id']} - {reclamo['cliente_nombre']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**👤 Cliente:** {reclamo['cliente_nombre']}")
                    st.write(f"**📞 Teléfono:** {reclamo['telefono']}")
                    st.write(f"**📍 Dirección:** {reclamo['direccion']}")
                    st.write(f"**📌 Tipo:** {reclamo['tipo_reclamo']}")
                    st.write(f"**📊 Estado:** {reclamo['estado']}")
                    st.write(f"**📄 Detalles:** {reclamo['detalles']}")
                
                with col2:
                    if st.button(f"📄 Generar PDF", key=f"pdf_{reclamo['id']}"):
                        pdf_buffer = generar_pdf_reclamo(reclamo)
                        st.download_button(
                            label="⬇️ Descargar PDF",
                            data=pdf_buffer,
                            file_name=f"reclamo_{reclamo['id']}.pdf",
                            mime="application/pdf",
                            key=f"download_{reclamo['id']}"
                        )
        
        # Botón para generar PDF de todos los reclamos filtrados
        st.markdown("---")
        if st.button("📄 Generar PDF de Todos los Reclamos Filtrados", type="primary"):
            pdf_buffer = generar_pdf_multiple_reclamos(df_filtrado)
            st.download_button(
                label="⬇️ Descargar PDF Completo",
                data=pdf_buffer,
                file_name=f"reclamos_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

def generar_pdf_multiple_reclamos(reclamos_df):
    """Genera un PDF con múltiples reclamos"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    title = Paragraph("REPORTE MÚLTIPLE DE RECLAMOS", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Información general
    info_text = f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>Total de reclamos: {len(reclamos_df)}"
    info = Paragraph(info_text, styles['Normal'])
    story.append(info)
    story.append(Spacer(1, 20))
    
    # Tabla con todos los reclamos
    data = [['ID', 'Cliente', 'Tipo', 'Estado', 'Prioridad', 'Fecha']]
    
    for idx, reclamo in reclamos_df.iterrows():
        data.append([
            str(reclamo['id']),
            str(reclamo['cliente_nombre'])[:20],
            str(reclamo['tipo_reclamo'])[:15],
            str(reclamo['estado']),
            str(reclamo['prioridad']),
            str(reclamo['fecha_creacion'])[:10]
        ])
    
    table = Table(data, colWidths=[40, 100, 80, 60, 60, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer

# SECCIÓN: CIERRE DE RECLAMOS
def seccion_cierre_reclamos():
    st.title("🔒 Cierre de Reclamos")
    st.markdown("---")
    
    reclamos_df = cargar_reclamos()
    
    if reclamos_df.empty:
        st.info("📭 No hay reclamos para cerrar")
        return
    
    # Filtrar reclamos que pueden ser cerrados (Resueltos)
    reclamos_resueltos = reclamos_df[reclamos_df['estado'] == 'Resuelto']
    
    if reclamos_resueltos.empty:
        st.info("✅ No hay reclamos resueltos pendientes de cierre")
        return
    
    st.subheader(f"📋 Reclamos Resueltos Pendientes de Cierre ({len(reclamos_resueltos)})")
    
    for idx, reclamo in reclamos_resueltos.iterrows():
        with st.expander(f"🎫 Reclamo #{reclamo['id']} - {reclamo['cliente_nombre']} - RESUELTO"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**👤 Cliente:** {reclamo['cliente_nombre']}")
                st.write(f"**📞 Teléfono:** {reclamo['telefono']}")
                st.write(f"**📍 Dirección:** {reclamo['direccion']}")
                st.write(f"**📌 Tipo:** {reclamo['tipo_reclamo']}")
                st.write(f"**👨‍🔧 Técnico:** {reclamo['tecnico']}")
                st.write(f"**📅 Fecha Resolución:** {reclamo['fecha_resolucion']}")
                st.write(f"**📄 Detalles:** {reclamo['detalles']}")
            
            with col2:
                st.subheader("🔒 Cerrar Reclamo")
                
                observaciones = st.text_area(
                    "Observaciones de Cierre:",
                    key=f"obs_{reclamo['id']}",
                    height=100
                )
                
                if st.button(f"🔒 Cerrar Definitivamente", key=f"cerrar_{reclamo['id']}", type="primary"):
                    # Actualizar a estado "Cerrado"
                    query = """
                    UPDATE reclamos 
                    SET estado = 'Cerrado', observaciones_cierre = %s
                    WHERE id = %s
                    """
                    params = (observaciones, reclamo['id'])
                    
                    if ejecutar_consulta(query, params, fetch=False):
                        st.success("✅ Reclamo cerrado exitosamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al cerrar el reclamo")

# NAVEGACIÓN PRINCIPAL
def main():
    st.sidebar.title("🏢 Fusion Reclamos")
    st.sidebar.markdown("---")
    
    # Menú de navegación
    opciones = {
        "🏠 Inicio": seccion_inicio,
        "📝 Nuevo Reclamo": seccion_nuevo_reclamo,
        "📋 Reclamos Cargados": seccion_reclamos_cargados,
        "🔧 Seguimiento Técnico": seccion_seguimiento_tecnico,
        "📚 Historial por Cliente": seccion_historial_cliente,
        "✏️ Editar Cliente": seccion_editar_cliente,
        "🖨️ Imprimir Reclamos": seccion_imprimir_reclamos,
        "🔒 Cierre de Reclamos": seccion_cierre_reclamos,
    }
    
    seleccion = st.sidebar.radio("Navegación", list(opciones.keys()))
    
    # Información de conexión en sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 Estado de Conexión")
    
    conn = get_connection()
    if conn:
        st.sidebar.success("✅ Conectado a la base de datos")
        conn.close()
    else:
        st.sidebar.error("❌ Error de conexión")
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Tip:** Use los filtros para encontrar reclamos específicos más rápidamente.")
    
    # Ejecutar la sección seleccionada
    opciones[seleccion]()

if __name__ == "__main__":
    main()