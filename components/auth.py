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
    try:
        df_usuarios = safe_get_sheet_data(sheet_usuarios, COLUMNAS_USUARIOS)
        
        # Normalización de datos
        df_usuarios["username"] = df_usuarios["username"].str.strip().str.lower()
        df_usuarios["password"] = df_usuarios["password"].astype(str).str.strip()
        
        # Manejo flexible de campo 'activo'
        df_usuarios["activo"] = df_usuarios["activo"].astype(str).str.upper().isin(["SI", "TRUE", "1", "SÍ", "VERDADERO"])
        
        usuario = df_usuarios[
            (df_usuarios["username"] == username.strip().lower()) & 
            (df_usuarios["password"] == password.strip()) &
            (df_usuarios["activo"])
        ]
        
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
    """Versión mejorada con iconos y estilo"""
    if not check_authentication():
        return
        
    user_info = st.session_state.auth['user_info']
    role_config = {
        'admin': {'icon': '👑', 'color': '#FF5733'},
        'oficina': {'icon': '💼', 'color': '#338AFF'}
    }
    config = role_config.get(user_info['rol'], {'icon': '👤', 'color': '#555'})
    
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <span style="font-size: 1.5rem;">{config['icon']}</span>
            <div>
                <p style="margin: 0; font-weight: bold;">{user_info['nombre']}</p>
                <p style="margin: 0; color: {config['color']}; font-size: 0.8rem;">
                    {user_info['rol'].upper()}
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            logout()
            st.rerun()
        st.markdown("---")