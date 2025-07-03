import streamlit as st
from components.auth import logout, check_authentication

def show_user_widget():
    """Widget de usuario actualizado para Streamlit >=1.28"""
    if not check_authentication():
        return
        
    user = st.session_state.auth['user_info']
    
    # Widget de usuario mejorado
    st.sidebar.markdown(f"""
    <div style='border:1px solid #ddd; padding:10px; border-radius:5px; margin:10px 0;'>
        <p style='margin:0; font-weight:bold;'>👋 {user['nombre']}</p>
        <p style='margin:0; color:#666; font-size:0.8em;'>{user['rol'].upper()}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botón de logout seguro
    if st.sidebar.button("🚪 Cerrar sesión", key="logout_btn", use_container_width=True):
        logout()
        st.rerun()