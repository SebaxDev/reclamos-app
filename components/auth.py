"""
Componente de autenticación
"""
import streamlit as st

def render_login():
    """Renderiza el formulario de login con estilos mejorados"""
    st.markdown("""
    <div class="section-container" style="max-width: 400px; margin: 50px auto;">
        <h1 style="text-align: center; margin-bottom: 30px;">🔐 Iniciar sesión</h1>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_formulario"):
        st.markdown("### Credenciales de acceso")
        usuario = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
        password = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            enviar = st.form_submit_button("🚀 Ingresar", use_container_width=True)
        
        if enviar:
            if usuario in st.secrets["auth"] and st.secrets["auth"][usuario] == password:
                st.session_state.logueado = True
                st.session_state.usuario_actual = usuario
                st.success("✅ Acceso concedido. Redirigiendo...")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

def check_authentication():
    """Verifica el estado de autenticación"""
    if "logueado" not in st.session_state:
        st.session_state.logueado = False
    if "usuario_actual" not in st.session_state:
        st.session_state.usuario_actual = ""
    
    return st.session_state.logueado