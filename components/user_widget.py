import streamlit as st
from auth import logout, check_authentication

def show_user_widget():
    """Widget independiente que siempre funciona"""
    if not check_authentication():
        return
        
    user = st.session_state.auth['user_info']
    
    st.sidebar.markdown(f"""
    <div style='border:1px solid #ddd; padding:10px; border-radius:5px; margin:10px 0;'>
        <p style='margin:0; font-weight:bold;'>👋 {user['nombre']}</p>
        <p style='margin:0; color:#666; font-size:0.8em;'>{user['rol'].upper()}</p>
        <button onclick="window.location.href='?logout=true'" style='width:100%; margin-top:5px;'>
            🚪 Cerrar sesión
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    if st.experimental_get_query_params().get('logout'):
        logout()
        st.experimental_set_query_params()
        st.rerun()