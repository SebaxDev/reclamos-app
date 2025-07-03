"""
Componente de autenticación simplificado
Versión sin hashing para proyectos pequeños
"""
import streamlit as st
from utils.data_manager import safe_get_sheet_data
from config.settings import (
    WORKSHEET_USUARIOS,
    COLUMNAS_USUARIOS,
    PERMISOS_POR_ROL
)
import time

def init_auth_session():
    """Inicializa las variables de sesión"""
    if 'auth' not in st.session_state:
        st.session_state.auth = {
            'logged_in': False,
            'user_info': None
        }

def logout():
    """Cierra la sesión del usuario"""
    st.session_state.auth = {'logged_in': False, 'user_info': None}
    st.cache_data.clear()  # Limpiar caché de datos

def verify_credentials(username, password, sheet_usuarios):
    """
    Verifica credenciales en texto plano
    """
    try:
        df_usuarios = safe_get_sheet_data(sheet_usuarios, COLUMNAS_USUARIOS)
        
        usuario = df_usuarios[
            (df_usuarios["username"].str.lower() == username.lower()) & 
            (df_usuarios["password"] == password) &  # Comparación directa
            (df_usuarios["activo"] == True
        )]
        
        if not usuario.empty:
            return {
                "username": usuario.iloc[0]["username"],
                "nombre": usuario.iloc[0]["nombre"],
                "rol": usuario.iloc[0]["rol"].lower(),
                "permisos": PERMISOS_POR_ROL.get(usuario.iloc[0]["rol"].lower(), {}).get('permisos', [])
            }
    except Exception as e:
        st.error(f"Error en autenticación: {str(e)}")
    return None

def render_login(sheet_usuarios):
    """Formulario de login simplificado"""
    st.markdown("""
    <div class="section-container" style="max-width: 400px; margin: 50px auto;">
        <h1 style="text-align: center; margin-bottom: 30px;">🔐 Iniciar sesión</h1>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_formulario"):
        username = st.text_input("👤 Usuario").strip()
        password = st.text_input("🔒 Contraseña", type="password")
        
        if st.form_submit_button("Ingresar"):
            if not username or not password:
                st.error("Usuario y contraseña son requeridos")
            else:
                user_info = verify_credentials(username, password, sheet_usuarios)
                if user_info:
                    st.session_state.auth = {
                        'logged_in': True,
                        'user_info': user_info
                    }
                    st.success(f"✅ Bienvenido, {user_info['nombre']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas o usuario inactivo")

def check_authentication():
    """Verifica si el usuario está autenticado"""
    init_auth_session()
    return st.session_state.auth['logged_in']

def has_permission(required_permission):
    """Verifica permisos del usuario"""
    if not check_authentication():
        return False
        
    user_info = st.session_state.auth.get('user_info')
    if not user_info:
        return False
        
    # Admin tiene acceso completo
    if user_info['rol'] == 'admin':
        return True
        
    return required_permission in user_info.get('permisos', [])

def render_user_info():
    """Muestra información del usuario con estilo mejorado"""
    if check_authentication():
        user_info = st.session_state.auth['user_info']
        
        # Personaliza ícono y color según el rol
        if user_info['rol'] == 'admin':
            rol_icono = "👑"
            rol_color = "#FF5733"  # Rojo/naranja para admin
        else:
            rol_icono = "💼"
            rol_color = "#338AFF"  # Azul para oficina

        # Estilo mejorado con HTML/CSS
        st.sidebar.markdown(f"""
        <div style="
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            background-color: #f0f2f6;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <p style="margin: 0; font-weight: bold; font-size: 1.1rem;">
                👋 ¡Bienvenido, <span style="color: #2c3e50;">{user_info['nombre']}</span>!
            </p>
            <p style="margin: 5px 0 0; font-size: 0.9rem;">
                {rol_icono} <span style="color: {rol_color}; font-weight: bold;">{user_info['rol'].upper()}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.sidebar.button("🚪 Cerrar sesión", key="logout_btn"):
            logout()
            st.rerun()