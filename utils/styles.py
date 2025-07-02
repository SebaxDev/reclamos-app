"""
Estilos CSS centralizados para la aplicación con soporte de modo claro/oscuro
"""

def get_main_styles(dark_mode=False):
    theme_vars = """
        --primary-color: #0d6efd;
        --primary-hover: #0b5ed7;
        --secondary-color: #6c757d;
        --success-color: #198754;
        --warning-color: #fd7e14;
        --danger-color: #dc3545;
        --light-bg: #f8f9fa;
        --text-color: #212529;
        --bg-color: white;
    """ if not dark_mode else """
        --primary-color: #0d6efd;
        --primary-hover: #0a58ca;
        --secondary-color: #adb5bd;
        --success-color: #51cf66;
        --warning-color: #fab005;
        --danger-color: #fa5252;
        --light-bg: #343a40;
        --text-color: #f1f3f5;
        --bg-color: #1c1f23;
    """
    
    return f"""
    <style>
    :root {{
        {theme_vars}
        --border-radius: 8px;
        --border-color: #dee2e6;
        --shadow: 0 2px 4px rgba(0,0,0,0.1);
        --transition: all 0.2s ease;
    }}

    body, .block-container {{
        background-color: var(--bg-color) !important;
        color: var(--text-color) !important;
    }}

    h1 {{
        color: var(--primary-color) !important;
        font-weight: 700;
        margin-bottom: 1.5rem;
    }}

    h2, h3 {{
        color: var(--text-color) !important;
        font-weight: 600;
        margin: 1rem 0 0.5rem 0;
    }}

    .block-container {{
        max-width: 1200px;
        padding: 1rem 2rem;
        animation: fadeIn 0.3s ease-in;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .stTextInput input, .stTextArea textarea, .stSelectbox select {{
        border-radius: var(--border-radius) !important;
        border: 1px solid var(--border-color) !important;
        padding: 10px 14px !important;
        transition: var(--transition) !important;
        font-size: 14px !important;
        color: var(--text-color) !important;
        background-color: var(--light-bg) !important;
    }}

    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {{
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.1) !important;
    }}

    .stButton>button {{
        border-radius: var(--border-radius);
        border: 1px solid var(--primary-color);
        background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
        color: white;
        padding: 10px 20px;
        font-weight: 500;
        transition: var(--transition);
        position: relative;
        overflow: hidden;
    }}

    .stButton>button:hover {{
        transform: translateY(-1px);
        box-shadow: var(--shadow);
        background: linear-gradient(135deg, var(--primary-hover), var(--primary-color));
    }}

    .stButton>button:active {{
        transform: translateY(0);
    }}

    .metric-container {{
        background: var(--light-bg);
        border-radius: 12px;
        padding: 20px;
        box-shadow: var(--shadow);
        margin-bottom: 15px;
        transition: var(--transition);
        border: 1px solid transparent;
    }}

    .metric-container:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-color: var(--primary-color);
    }}

    .dataframe {{
        border-radius: var(--border-radius);
        box-shadow: var(--shadow);
        border: 1px solid var(--border-color);
    }}

    .stRadio > div {{
        background: var(--light-bg);
        border-radius: var(--border-radius);
        padding: 10px;
        flex-direction: row;
        gap: 1rem;
        flex-wrap: wrap;
    }}

    .stRadio [role=radiogroup] {{
        gap: 1rem;
        align-items: center;
    }}

    .stAlert {{
        border-radius: var(--border-radius);
        animation: slideIn 0.3s ease;
    }}

    @keyframes slideIn {{
        from {{ transform: translateX(-20px); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}

    .loading-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.8);
        z-index: 9999;
        display: flex;
        justify-content: center;
        align-items: center;
    }}

    .spinner {{
        border: 3px solid #f3f3f3;
        border-top: 3px solid var(--primary-color);
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
    }}

    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}

    .section-container {{
        background: var(--light-bg);
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: var(--shadow);
        border: 1px solid var(--border-color);
    }}

    @media (max-width: 768px) {{
        .block-container {{
            padding: 1rem;
        }}
        
        .stRadio > div {{
            flex-direction: column;
            align-items: stretch;
        }}
        
        .metric-container {{
            margin-bottom: 10px;
            padding: 15px;
        }}
    }}

    .hover-card {{
        transition: var(--transition);
        cursor: pointer;
    }}

    .hover-card:hover {{
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }}

    .status-badge {{
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
    }}

    .status-pendiente {{
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }}

    .status-en-curso {{
        background: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }}

    .status-resuelto {{
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }}
    </style>
    """

def get_loading_spinner():
    return """
    <div class="loading-overlay">
        <div class="spinner"></div>
    </div>
    """
