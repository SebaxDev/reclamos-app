import streamlit as st
from components.auth import logout, check_authentication

def show_user_widget():
    """Widget de usuario simplificado sin botón HTML"""
    if not check_authentication():
        return
        
    user = st.session_state.auth['user_info']
    
    # Configuración de colores según el rol
    role_colors = {
        'admin': {'bg': '#4a148c', 'text': '#ffffff', 'icon': '👑'},
        'oficina': {'bg': '#1565c0', 'text': '#ffffff', 'icon': '💼'},
        'default': {'bg': '#2c3e50', 'text': '#ecf0f1', 'icon': '👤'}
    }
    
    role_config = role_colors.get(user['rol'].lower(), role_colors['default'])
    
    # Widget simplificado sin botón HTML/JavaScript
    with st.sidebar:
        st.markdown(f"""
        <div style='
            background: {role_config['bg']};
            color: {role_config['text']};
            padding: 1rem;
            border-radius: 10px;
            margin: 0 0 1rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        '>
            <div style='
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 10px;
            '>
                <span style='font-size: 1.8rem;'>{role_config['icon']}</span>
                <div>
                    <h3 style='
                        margin: 0;
                        font-weight: 600;
                        font-size: 1.1rem;
                    '>{user['nombre']}</h3>
                    <p style='
                        margin: 0;
                        opacity: 0.9;
                        font-size: 0.85rem;
                    '>{user['rol'].upper()}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Botón nativo de Streamlit para cerrar sesión
        if st.button(
            "🚪 Cerrar sesión",
            key="logout_btn",
            use_container_width=True,
            help="Cierra tu sesión y limpia todos los datos temporales"
        ):
            st.session_state.logout_clicked = True
            st.rerun()