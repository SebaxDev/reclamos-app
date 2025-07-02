"""
Módulo para gestión segura de datos con Google Sheets
Versión 3.1 - Con manejo robusto de errores y compatibilidad con API
"""
import streamlit as st
import time

class ApiManager:
    def __init__(self):
        self.total_calls = 0
        self.error_count = 0
        self.last_call = 0

    def safe_sheet_operation(self, func, *args, is_batch=False, **kwargs):
        """
        Ejecuta una operación segura sobre la API de Google Sheets
        
        Args:
            func: función de gspread a ejecutar
            *args: argumentos posicionales para la función
            is_batch: bool, si es operación por lote (sólo informativo)
            **kwargs: argumentos clave
        
        Returns:
            tuple: (resultado, error) donde error es None si fue exitoso
        """
        try:
            self.total_calls += 1
            self.last_call = time.time()
            result = func(*args, **kwargs)
            return result, None
        except Exception as e:
            self.error_count += 1
            return None, str(e)

    def get_api_stats(self):
        """
        Devuelve estadísticas de uso de la API actual
        """
        return {
            "total_calls": self.total_calls,
            "error_count": self.error_count,
            "last_call": self.last_call
        }

# Instancia única global
api_manager = ApiManager()

def init_api_session_state():
    """
    Inicializa api_manager en st.session_state si no existe aún
    """
    if "api_stats" not in st.session_state:
        st.session_state.api_stats = api_manager.get_api_stats()
