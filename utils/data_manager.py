"""
Gestor de datos para operaciones con Google Sheets
"""
import pandas as pd
import streamlit as st
from utils.api_manager import api_manager

def safe_get_sheet_data(sheet, expected_columns):
    """Carga datos de una hoja de forma segura"""
    try:
        data, error = api_manager.safe_sheet_operation(sheet.get_all_records)
        if error:
            return pd.DataFrame(columns=expected_columns)
        
        df = pd.DataFrame(data)
        
        if df.empty and len(sheet.row_values(1)) > 0:
            df = pd.DataFrame(columns=sheet.row_values(1))
            
        if df.empty:
            df = pd.DataFrame(columns=expected_columns)
            
        return df
    except Exception as e:
        st.warning(f"Error al cargar datos: {e}")
        return pd.DataFrame(columns=expected_columns)

def safe_normalize(df, column):
    """Normaliza una columna de forma segura"""
    if column in df.columns:
        df[column] = df[column].apply(
            lambda x: str(int(x)).strip() if isinstance(x, (int, float)) else str(x).strip()
        )
    return df

def update_sheet_data(sheet, data, is_batch=True):
    """Actualiza datos en una hoja con control de rate limiting"""
    try:
        if isinstance(data, list) and len(data) > 1:
            # Operación batch
            result, error = api_manager.safe_sheet_operation(
                sheet.clear, is_batch=True
            )
            if error:
                return False, error
            
            result, error = api_manager.safe_sheet_operation(
                sheet.append_row, data[0], is_batch=True
            )
            if error:
                return False, error
            
            if len(data) > 1:
                result, error = api_manager.safe_sheet_operation(
                    sheet.append_rows, data[1:], is_batch=True
                )
                if error:
                    return False, error
        else:
            # Operación simple
            result, error = api_manager.safe_sheet_operation(
                sheet.append_row, data, is_batch=False
            )
            if error:
                return False, error
        
        return True, None
    except Exception as e:
        return False, str(e)

def batch_update_sheet(sheet, updates):
    """Realiza múltiples actualizaciones en batch"""
    try:
        result, error = api_manager.safe_sheet_operation(
            sheet.batch_update, updates, is_batch=True
        )
        return result is not None, error
    except Exception as e:
        return False, str(e)