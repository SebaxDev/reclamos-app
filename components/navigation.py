"""
Componente de navegación
"""
import streamlit as st

def render_navigation():
    """Renderiza el menú de navegación mejorado"""
    st.markdown("### 🧭 Navegación")
    
    opciones = [
        "🏠 Inicio", 
        "📊 Reclamos cargados", 
        "📜 Historial por cliente", 
        "✏️ Editar cliente", 
        "🖨️ Imprimir reclamos", 
        "👷 Seguimiento técnico", 
        "✅ Cierre de Reclamos"
    ]
    
    # Crear navegación con iconos
    opcion = st.radio(
        "Selecciona una sección:",
        opciones,
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Extraer solo el nombre sin emoji para compatibilidad
    opcion_clean = opcion.split(" ", 1)[1] if " " in opcion else opcion
    
    return opcion_clean

def render_user_info():
    """Renderiza información del usuario logueado"""
    if st.session_state.get("usuario_actual"):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"👋 Bienvenido, **{st.session_state.usuario_actual}**")
        with col2:
            if st.button("🚪 Cerrar sesión"):
                st.session_state.logueado = False
                st.session_state.usuario_actual = ""
                st.rerun()