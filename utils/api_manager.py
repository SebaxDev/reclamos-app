"""
Módulo para gestión segura de datos con Google Sheets
Versión 3.0 - Con manejo robusto de errores y compatibilidad con API
"""
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
import gspread
from utils.api_manager import api_manager

def safe_get_sheet_data(sheet, expected_columns):
    """
    Obtiene datos de una hoja de cálculo con validación de columnas
    
    Args:
        sheet: Objeto de hoja de cálculo de gspread
        expected_columns: Lista de columnas esperadas
        
    Returns:
        DataFrame con los datos o DataFrame vacío si hay error
    """
    try:
        # Obtener todos los registros
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        # Validar columnas
        missing_cols = [col for col in expected_columns if col not in df.columns]
        if missing_cols:
            st.warning(f"Advertencia: Faltan columnas {missing_cols} en la hoja")
            # Agregar columnas faltantes vacías
            for col in missing_cols:
                df[col] = ""
        
        return df
    
    except Exception as e:
        st.error(f"Error al obtener datos: {str(e)}")
        # Devolver DataFrame vacío con columnas esperadas
        return pd.DataFrame(columns=expected_columns)

def safe_normalize(df, column_name):
    """
    Normaliza una columna asegurando tipo string y sin valores nulos
    
    Args:
        df: DataFrame a normalizar
        column_name: Nombre de la columna a normalizar
        
    Returns:
        DataFrame con la columna normalizada
    """
    try:
        if column_name in df.columns:
            df[column_name] = df[column_name].astype(str).str.strip().fillna("")
        return df
    except Exception as e:
        st.warning(f"Advertencia: No se pudo normalizar {column_name}: {str(e)}")
        return df

def update_sheet_data(sheet, data, is_batch=False):
    """
    Actualiza datos en una hoja de cálculo con manejo seguro de errores
    
    Args:
        sheet: Objeto de hoja de cálculo
        data: Datos a escribir (lista o lista de listas)
        is_batch: Si es True, data es una lista de filas
        
    Returns:
        tuple: (success, error)
    """
    try:
        # Limpieza y conversión de datos
        def clean_value(value):
            if value is None:
                return ""
            if isinstance(value, (int, float)):
                return str(int(value)) if value == int(value) else str(value)
            return str(value).strip()
        
        if is_batch:
            # Operación por lotes
            cleaned_data = []
            for row in data:
                cleaned_row = [clean_value(value) for value in row]
                cleaned_data.append(cleaned_row)
            
            result, error = api_manager.safe_sheet_operation(
                sheet.update,
                cleaned_data,
                is_batch=True
            )
        else:
            # Operación de una sola fila
            cleaned_data = [clean_value(value) for value in data]
            
            result, error = api_manager.safe_sheet_operation(
                sheet.append_row,
                cleaned_data
            )
        
        return (True, None) if result else (False, error)
        
    except Exception as e:
        error_msg = f"Error en actualización: {str(e)}"
        st.error(error_msg)
        return False, error_msg

def batch_update_sheet(sheet, updates):
    """
    Actualización por lotes con formato específico para celdas
    
    Args:
        sheet: Objeto de hoja de cálculo
        updates: Lista de dicts con formato {'range': 'A1:B2', 'values': [[...]]}
        
    Returns:
        tuple: (success, error)
    """
    try:
        # Validar formato de updates
        for update in updates:
            if not all(key in update for key in ('range', 'values')):
                raise ValueError("Formato incorrecto en updates")
        
        result, error = api_manager.safe_sheet_operation(
            sheet.batch_update,
            updates,
            is_batch=True
        )
        
        return (True, None) if result else (False, error)
        
    except Exception as e:
        error_msg = f"Error en batch update: {str(e)}"
        st.error(error_msg)
        return False, error_msg

def validate_sheet_connection(sheet):
    """
    Valida que la conexión con la hoja sea funcional
    
    Args:
        sheet: Objeto de hoja de cálculo
        
    Returns:
        bool: True si la conexión es válida
    """
    try:
        # Intenta obtener el título como prueba de conexión
        sheet.title
        return True
    except Exception as e:
        st.error(f"Conexión inválida con la hoja: {str(e)}")
        return False