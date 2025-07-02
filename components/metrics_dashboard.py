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
        
        # Distribución por tipo de reclamo (solo activos)
        if not df_activos.empty:
            st.markdown("### 📊 Distribución por tipo de reclamo (activos)")
            conteo_por_tipo = df_activos["Tipo de reclamo"].value_counts().sort_index()
            
            # Mostrar en grid responsive
            tipos = list(conteo_por_tipo.index)
            cantidad = list(conteo_por_tipo.values)
            
            # Crear grid dinámico
            cols_per_row = 4
            for i in range(0, len(tipos), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(tipos):
                        with col:
                            tipo = tipos[i + j]
                            cant = cantidad[i + j]
                            st.markdown(f"""
                            <div class="metric-container" style="text-align: center; padding: 15px;">
                                <h4 style="margin: 0; font-size: 0.9rem; color: #6c757d;">{tipo}</h4>
                                <h2 style="margin: 5px 0 0 0; color: #0d6efd;">{cant}</h2>
                            </div>
                            """, unsafe_allow_html=True)
        
    except Exception as e:
        st.info("No hay datos disponibles para mostrar métricas aún.")
        st.error(f"Error en métricas: {e}")