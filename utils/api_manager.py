"""
Gestor de API para controlar las llamadas a Google Sheets
"""
import time
import streamlit as st
from config.settings import API_DELAY, BATCH_DELAY

class APIManager:
    def __init__(self):
        # Inicialización robusta de session_state
        self._init_session_state()
    
    def _init_session_state(self):
        """Garantiza que las variables de sesión existan"""
        defaults = {
            'last_api_call': 0,
            'api_calls_count': 0  # Nombre consistente (agregada la 's')
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def wait_for_rate_limit(self, is_batch=False):
        """Espera el tiempo necesario para respetar el rate limit"""
        current_time = time.time()
        time_since_last_call = current_time - st.session_state.last_api_call
        
        delay = BATCH_DELAY if is_batch else API_DELAY
        
        if time_since_last_call < delay:
            wait_time = delay - time_since_last_call
            time.sleep(wait_time)
        
        # Actualiza con nombres consistentes
        st.session_state.last_api_call = current_time
        st.session_state.api_calls_count += 1  # Ahora con 's'
    
    def safe_sheet_operation(self, operation, *args, is_batch=False, **kwargs):
        """Ejecuta una operación de sheet de forma segura con rate limiting"""
        try:
            self.wait_for_rate_limit(is_batch)
            result = operation(*args, **kwargs)
            return result, None
        except Exception as e:
            error_msg = f"Error en operación de API: {str(e)}"
            st.error(error_msg)
            return None, error_msg
    
    def get_api_stats(self):
        """Retorna estadísticas de uso de la API"""
        # Usa .get() como fallback para evitar errores
        return {
            'total_calls': st.session_state.get('api_calls_count', 0),
            'last_call': st.session_state.get('last_api_call', 0)
        }

# Instancia global del manager (mejorada para evitar reinstanciación)
if 'api_manager' not in st.session_state:
    st.session_state.api_manager = APIManager()

api_manager = st.session_state.api_manager