"""
Gestor de API para controlar las llamadas a Google Sheets
Versión 3.0 - Con inicialización robusta de session_state
"""
import time
import streamlit as st
from config.settings import API_DELAY, BATCH_DELAY

class APIManager:
    def __init__(self):
        """Inicialización robusta que garantiza la existencia de las variables de estado"""
        self._init_session_state()
    
    def _init_session_state(self):
        """Garantiza que todas las variables de sesión necesarias existan"""
        required_vars = {
            'last_api_call': 0,            # Timestamp de última llamada
            'api_calls_count': 0,          # Contador total de llamadas
            'api_error_count': 0,          # Contador de errores (variable faltante)
            'last_api_error': None         # Último mensaje de error
        }
        
        for var, default in required_vars.items():
            if var not in st.session_state:
                st.session_state[var] = default
    
    def wait_for_rate_limit(self, is_batch=False):
        """Espera el tiempo necesario para respetar el rate limit"""
        current_time = time.time()
        time_since_last_call = current_time - st.session_state.last_api_call
        
        delay = BATCH_DELAY if is_batch else API_DELAY
        
        if time_since_last_call < delay:
            time.sleep(delay - time_since_last_call)
        
        st.session_state.last_api_call = time.time()
        st.session_state.api_calls_count += 1
    
    def safe_sheet_operation(self, operation, *args, is_batch=False, **kwargs):
        """Ejecuta una operación de sheet con manejo de errores y rate limiting"""
        try:
            self.wait_for_rate_limit(is_batch)
            result = operation(*args, **kwargs)
            return result, None
        except Exception as e:
            error_msg = str(e)
            # Actualizar contadores de error de forma segura
            st.session_state.api_error_count = st.session_state.get('api_error_count', 0) + 1
            st.session_state.last_api_error = error_msg
            
            if st.secrets.get("DEBUG", False):
                st.error(f"API Error [{st.session_state.api_error_count}]: {error_msg}")
            
            return None, f"Error en operación de API: {error_msg}"
    
    def get_api_stats(self):
        """Obtiene estadísticas de uso de la API con valores por defecto seguros"""
        return {
            'total_calls': st.session_state.get('api_calls_count', 0),
            'last_call': st.session_state.get('last_api_call', 0),
            'error_count': st.session_state.get('api_error_count', 0),
            'last_error': st.session_state.get('last_api_error', 'N/A')
        }

# Instancia singleton para evitar múltiples inicializaciones
if 'global_api_manager' not in st.session_state:
    st.session_state.global_api_manager = APIManager()

api_manager = st.session_state.global_api_manager