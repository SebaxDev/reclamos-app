"""
Componente del dashboard de métricas
"""
import streamlit as st
import pandas as pd

def render_metrics_dashboard(df_reclamos):
    """Renderiza el dashboard de métricas con animaciones"""
    try:
        df_metricas = df_reclamos.copy()
        
        # Solo reclamos activos (Pendientes o En curso)
        df_activos = df_metricas[df_metricas["Estado"].isin(["Pendiente", "En curso"])]
        
        total = len(df_activos)
        pendientes = len(df_activos[df_activos["Estado"] == "Pendiente"])
        en_curso = len(df_activos[df_activos["Estado"] == "En curso"])
        resueltos = len(df_metricas[df_metricas["Estado"] == "Resuelto"])
        
        # Métricas principales con efectos hover
        st.markdown("""
        <div style="display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
        """, unsafe_allow_html=True)
        
        colm1, colm2, colm3, colm4 = st.columns(4)
        
        with colm1:
            st.markdown(f"""
            <div class="metric-container hover-card">
                <h3 style="margin: 0; color: #0d6efd;">📄 Total activos</h3>
                <h1 style="margin: 10px 0 0 0; font-size: 2.5rem;">{total}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with colm2:
            st.markdown(f"""
            <div class="metric-container hover-card">
                <h3 style="margin: 0; color: #fd7e14;">🕒 Pendientes</h3>
                <h1 style="margin: 10px 0 0 0; font-size: 2.5rem;">{pendientes}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with colm3:
            st.markdown(f"""
            <div class="metric-container hover-card">
                <h3 style="margin: 0; color: #0dcaf0;">🔧 En curso</h3>
                <h1 style="margin: 10px 0 0 0; font-size: 2.5rem;">{en_curso}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with colm4:
            st.markdown(f"""
            <div class="metric-container hover-card">
                <h3 style="margin: 0; color: #198754;">✅ Resueltos</h3>
                <h1 style="margin: 10px 0 0 0; font-size: 2.5rem;">{resueltos}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
    except Exception as e:
        st.info("No hay datos disponibles para mostrar métricas aún.")
        st.error(f"Error en métricas: {e}")