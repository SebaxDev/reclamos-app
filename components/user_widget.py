import streamlit as st
from components.auth import logout, check_authentication

def show_user_widget():
    """Widget de usuario premium con diseño mejorado"""
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
    
    # Widget mejorado con HTML/CSS
    st.sidebar.markdown(f"""
    <div style='
        background: {role_config['bg']};
        color: {role_config['text']};
        padding: 1rem;
        border-radius: 10px;
        margin: 0 0 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
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
        
        <style>
            .logout-btn:hover {{
                background-color: #e53935 !important;
            }}
        </style>
        <button onclick="window.logout()" style='
            width: 100%;
            background: rgba(255,255,255,0.1);
            color: white;
            border: none;
            padding: 8px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.2s;
        '>
            🚪 Cerrar sesión
        </button>
    </div>
    
    <script>
    window.logout = function() {{
        parent.window.postMessage({{type: 'streamlit:setComponentValue', value: 'logout'}}, '*');
    }}
    </script>
    """, unsafe_allow_html=True)

    # Alternativa con botón nativo de Streamlit
    if st.sidebar.button(
        "🚪 Cerrar sesión", 
        key="logout_btn", 
        type="primary",
        use_container_width=True,
        help="Cierra tu sesión y limpia todos los datos temporales"
    ):
        st.session_state.logout_clicked = True
        st.rerun()