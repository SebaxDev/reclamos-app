"""
Gestor de API para controlar las llamadas a Google Sheets
Versión 3.1 - Solución definitiva para errores de session_state
"""
import time
import streamlit as st
from config.settings import API_DELAY, BATCH_DELAY

def init_api_session_state():
    """Inicializa todas las variables necesarias en session_state"""
    required_vars = {
        'last_api_call': 0,
        'api_calls_count': 0,
        'api_error_count': 0,
        'last_api_error': None,
        'api_initialized': True
    }
    
    for var, default in required_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default

class APIManager:
    def __init__(self):
        init_api_session_state()  # Asegurar inicialización
    
    def wait_for_rate_limit(self, is_batch=False):
        current_time = time.time()
        elapsed = current_time - st.session_state.last_api_call
        delay = BATCH_DELAY if is_batch else API_DELAY
        
        if elapsed < delay:
            time.sleep(delay - elapsed)
        
        st.session_state.last_api_call = time.time()
        st.session_state.api_calls_count += 1
    
    def safe_sheet_operation(self, operation, *args, is_batch=False, **kwargs):
        try:
            self.wait_for_rate_limit(is_batch)
            result = operation(*args, **kwargs)
            return result, None
        except Exception as e:
            error_msg = str(e)
            st.session_state.api_error_count += 1
            st.session_state.last_api_error = error_msg
            return None, f"Error en operación de API: {error_msg}"
    
    def get_api_stats(self):
        return {
            'total_calls': st.session_state.api_calls_count,
            'last_call': st.session_state.last_api_call,
            'error_count': st.session_state.api_error_count,
            'last_error': st.session_state.last_api_error or 'N/A'
        }

# Inicialización global segura
if 'global_api_manager' not in st.session_state:
    init_api_session_state()
    st.session_state.global_api_manager = APIManager()

api_manager = st.session_state.global_api_manager