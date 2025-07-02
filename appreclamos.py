import streamlit as st
from google.oauth2 import service_account
import gspread
from datetime import datetime
import pytz
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# --- LOGIN CON SECRETS ---
if "logueado" not in st.session_state:
    st.session_state.logueado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""

if not st.session_state.logueado:
    st.title("🔐 Iniciar sesión")
    with st.form("login_formulario"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")

        if enviar:
            if usuario in st.secrets["auth"] and st.secrets["auth"][usuario] == password:
                st.session_state.logueado = True
                st.session_state.usuario_actual = usuario
                st.success("✅ Acceso concedido.")
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# --- ESTILO VISUAL GLOBAL ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN ---
SHEET_ID = "13R_3Mdr25Jd-nGhK7CxdcbKkFWLc0LPdYrOLOY8sZJo"
WORKSHEET_RECLAMOS = "Principal"
WORKSHEET_CLIENTES = "Clientes"

# --- AUTENTICACIÓN USANDO SECRETS ---
info = dict(st.secrets["gcp_service_account"])
info["private_key"] = info["private_key"].replace("\\n", "\n")

credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"]
)

client = gspread.authorize(credentials)
sheet_reclamos = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_RECLAMOS)
sheet_clientes = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_CLIENTES)

# --- CARGAR BASES CON MANEJO DE HOJAS VACÍAS ---
def safe_get_sheet_data(sheet, expected_columns):
    try:
        data = sheet.get_all_records()  # Corregí "get_all_records" (antes decía "get_all_records")
        df = pd.DataFrame(data)
        
        if df.empty and len(sheet.row_values(1)) > 0:
            df = pd.DataFrame(columns=sheet.row_values(1))
            
        if df.empty:
            df = pd.DataFrame(columns=expected_columns)
            
        return df
    except Exception as e:
        st.warning(f"Error al cargar datos: {e}")
        return pd.DataFrame(columns=expected_columns)

COLUMNAS_RECLAMOS = [
    "Fecha y hora", "Nº Cliente", "Sector", "Nombre", 
    "Dirección", "Teléfono", "Tipo de reclamo", 
    "Detalles", "Estado", "Técnico", "N° de Precinto", "Atendido por"
]

COLUMNAS_CLIENTES = [
    "Nº Cliente", "Sector", "Nombre", "Dirección", 
    "Teléfono", "N° de Precinto"
]

df_reclamos = safe_get_sheet_data(sheet_reclamos, COLUMNAS_RECLAMOS)
df_clientes = safe_get_sheet_data(sheet_clientes, COLUMNAS_CLIENTES)

def safe_normalize(df, column):
    if column in df.columns:
        df[column] = df[column].apply(
            lambda x: str(int(x)).strip() if isinstance(x, (int, float)) else str(x).strip()
        )
    return df

df_clientes = safe_normalize(df_clientes, "Nº Cliente")
df_reclamos = safe_normalize(df_reclamos, "Nº Cliente")
df_clientes = safe_normalize(df_clientes, "N° de Precinto")
df_reclamos = safe_normalize(df_reclamos, "N° de Precinto")

# --- ESTILO VISUAL MEJORADO ---
st.markdown("""
    <style>
    /* Estilos generales */
    .block-container {
        max-width: 1000px;
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Mejoras para los formularios */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 8px !important;
        border: 1px solid #ced4da !important;
        padding: 8px 12px !important;
    }
    
    /* Botones mejorados */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #0d6efd;
        background-color: #0d6efd;
        color: white;
        padding: 8px 16px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton>button:hover {
        background-color: #0b5ed7;
        border-color: #0a58ca;
    }
    
    /* Tarjetas de m鑼卼ricas */
    .metric-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    
    /* Mejoras para los dataframes */
    .dataframe {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* T閾唗ulos m璋﹕ limpios */
    h1, h2, h3, h4, h5, h6 {
        color: #212529;
    }
    
    /* Separadores mejorados */
    .stDivider {
        margin: 1.5rem 0;
    }
    
    /* Radio buttons horizontales */
    .stRadio > div {
        flex-direction: row;
        gap: 1rem;
        align-items: center;
    }
    
    .stRadio [role=radiogroup] {
        gap: 1rem;
        align-items: center;
    }
    
    /* Mensajes de alerta mejorados */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Contenedores de expansi璐竛 */
    .stExpander {
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    
    /* Mejoras para m璐竩iles */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- LISTA DE TÉCNICOS DISPONIBLES ---
tecnicos_disponibles = ["Braian", "Conejo", "Juan", "Junior", "Maxi", "Ramon", "Roque", "Viki", "Oficina", "Base"]

# --- TÍTULO Y DASHBOARD ---
st.title("📋 Fusion Reclamos App")

# --- METRICAS RESUMEN ---
try:
    df_metricas = df_reclamos.copy()

    # Solo reclamos activos (Pendientes o En curso)
    df_activos = df_metricas[df_metricas["Estado"].isin(["Pendiente", "En curso"])]

    total = len(df_activos)  # Solo activos
    pendientes = len(df_activos[df_activos["Estado"] == "Pendiente"])
    en_curso = len(df_activos[df_activos["Estado"] == "En curso"])
    resueltos = len(df_metricas[df_metricas["Estado"] == "Resuelto"])  # Se sigue mostrando aparte

    colm1, colm2, colm3, colm4 = st.columns(4)
    colm1.metric("📄 Total activos", total)
    colm2.metric("🕒 Pendientes", pendientes)
    colm3.metric("🔧 En curso", en_curso)
    colm4.metric("✅ Resueltos", resueltos)
except:
    st.info("No hay datos disponibles para mostrar métricas aún.")

st.divider()

# --- MENÚ DE NAVEGACIÓN ---
opcion = st.radio("📂 Ir a la sección:", ["Inicio", "Reclamos cargados", "Historial por cliente", "Editar cliente", "Imprimir reclamos", "Seguimiento técnico", "Cierre de Reclamos"], horizontal=True)

# --- SECCIÓN 1: INICIO ---
if opcion == "Inicio":
    st.subheader("📝 Cargar nuevo reclamo")
    nro_cliente = st.text_input("🔢 N° de Cliente").strip()
    cliente_existente = None
    formulario_bloqueado = False

    if "Nº Cliente" in df_clientes.columns and nro_cliente:
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()

        match = df_clientes[df_clientes["Nº Cliente"] == nro_cliente]

        # Bloquear si ya tiene un reclamo pendiente o en curso
        reclamos_activos = df_reclamos[
            (df_reclamos["Nº Cliente"] == nro_cliente) &
            (df_reclamos["Estado"].isin(["Pendiente", "En curso"]))
        ]

        if not match.empty:
            cliente_existente = match.iloc[0].to_dict()
            st.success("✅ Cliente reconocido, datos auto-cargados.")
        else:
            st.info("ℹ️ Cliente no encontrado. Se cargará como Cliente Nuevo.")

        if not reclamos_activos.empty:
            st.error("⚠️ Este cliente ya tiene un reclamo sin resolver. No se puede cargar uno nuevo hasta que se cierre el anterior.")
            formulario_bloqueado = True

    if not formulario_bloqueado:
        with st.form("reclamo_formulario"):
            col1, col2 = st.columns(2)

            if cliente_existente is not None:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", value=cliente_existente["Sector"])
                    direccion = st.text_input("📍 Dirección", value=cliente_existente["Dirección"])
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", value=cliente_existente["Nombre"])
                    telefono = st.text_input("📞 Teléfono", value=cliente_existente["Teléfono"])
            else:
                with col1:
                    sector = st.text_input("🏩 Sector / Zona", value="")
                    direccion = st.text_input("📍 Dirección", value="")
                with col2:
                    nombre = st.text_input("👤 Nombre del Cliente", value="")
                    telefono = st.text_input("📞 Teléfono", value="")

            tipo_reclamo = st.selectbox("📌 Tipo de Reclamo", [
                "Conexion C+I", "Conexion Cable", "Conexion Internet", "Suma Internet",
                "Suma Cable", "Reconexion", "Sin Señal Ambos", "Sin Señal Cable",
                "Sin Señal Internet", "Sintonia", "Interferencia", "Traslado",
                "Extension x2", "Extension x3", "Extension x4", "Cambio de Ficha",
                "Cambio de Equipo", "Reclamo", "Desconexion a Pedido"
            ])

            detalles = st.text_area("📝 Detalles del Reclamo")
            precinto = st.text_input("🔒 N° de Precinto (opcional)", value=cliente_existente.get("N° de Precinto", "").strip() if cliente_existente else "")
            atendido_por = st.text_input("👤 Atendido por")

            enviado = st.form_submit_button("✅ Guardar Reclamo")

        if enviado:
            if not nro_cliente:
                st.error("⚠️ Debes ingresar un número de cliente.")
            elif not atendido_por.strip():
                st.error("⚠️ El campo 'Atendido por' es obligatorio.")
            else:
                argentina = pytz.timezone("America/Argentina/Buenos_Aires")
                fecha_hora = datetime.now(argentina).strftime("%Y-%m-%d %H:%M:%S")

                fila_reclamo = [
                    fecha_hora,
                    nro_cliente,
                    sector,
                    nombre.upper(),
                    direccion.upper(),
                    telefono,
                    tipo_reclamo,
                    detalles.upper(),
                    "Pendiente",  # Estado fijo
                    "",           # Técnicos vacíos por defecto
                    precinto,
                    atendido_por.upper()
                ]

                try:
                    sheet_reclamos.append_row(fila_reclamo)
                    st.success("✅ Reclamo guardado correctamente.")

                    if nro_cliente not in df_clientes["Nº Cliente"].values:
                        fila_cliente = [
                            nro_cliente,
                            sector,
                            nombre.upper(),
                            direccion.upper(),
                            telefono,
                            precinto
                        ]
                        sheet_clientes.append_row(fila_cliente)
                        st.info("🗂️ Nuevo cliente agregado a la base de datos.")
                except Exception as e:
                    st.error(f"❌ Error al guardar los datos: {e}")

# --- SECCIÓN 2: RECLAMOS CARGADOS ---
if opcion == "Reclamos cargados":
    st.subheader("📊 Reclamos cargados")

    try:
        df = df_reclamos.copy()
        df["Nº Cliente"] = df["Nº Cliente"].astype(str).str.strip()
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        df = pd.merge(df, df_clientes[["Nº Cliente", "N° de Precinto"]], on="Nº Cliente", how="left", suffixes=("", "_cliente"))
        df["Fecha y hora"] = pd.to_datetime(df["Fecha y hora"], errors="coerce")
        df = df.sort_values("Fecha y hora", ascending=False)

        # --- NUEVO PANEL VISUAL ---
        st.markdown("### 🧾 Distribución por tipo de reclamo (solo activos)")

        df_activos = df[df["Estado"].isin(["Pendiente", "En curso"])].copy()
        conteo_por_tipo = df_activos["Tipo de reclamo"].value_counts().sort_index()

        tipos = list(conteo_por_tipo.index)
        cantidad = list(conteo_por_tipo.values)

        columnas = st.columns(4)  # cambia a 3 si querés que sea más ancho

        for i, (tipo, cant) in enumerate(zip(tipos, cantidad)):
            with columnas[i % 4]:
                st.metric(label=f"📌 {tipo}", value=f"{cant}")

        # Total final
        st.markdown("---")
        total_activos = len(df_activos)
        st.metric(label="📊 TOTAL DE RECLAMOS ACTIVOS", value=total_activos)

        st.divider()

        # --- FILTROS Y EDITOR DE DATOS ---
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_estado = st.selectbox("🔎 Filtrar por estado", ["Todos"] + sorted(df["Estado"].unique()))
        with col2:
            filtro_sector = st.selectbox("🏙️ Filtrar por sector", ["Todos"] + sorted(df["Sector"].unique()))
        with col3:
            filtro_tipo = st.selectbox("📌 Filtrar por tipo", ["Todos"] + sorted(df["Tipo de reclamo"].unique()))

        if filtro_estado != "Todos":
            df = df[df["Estado"] == filtro_estado]
        if filtro_sector != "Todos":
            df = df[df["Sector"] == filtro_sector]
        if filtro_tipo != "Todos":
            df = df[df["Tipo de reclamo"] == filtro_tipo]

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key="editor",
            column_config={
                "Estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "En curso", "Resuelto"]),
                "Técnico": st.column_config.TextColumn("Técnico asignado"),
                "N° de Precinto": st.column_config.TextColumn("N° de Precinto")
            }
        )

        if st.button("💾 Guardar cambios en Google Sheets"):
            try:
                if isinstance(edited_df.iloc[0]["Técnico"], list):
                    edited_df["Técnico"] = edited_df["Técnico"].apply(lambda lista: ", ".join(lista) if isinstance(lista, list) else lista)

                edited_df = edited_df.astype(str)

                sheet_reclamos.clear()
                sheet_reclamos.append_row(edited_df.columns.tolist())
                sheet_reclamos.append_rows(edited_df.values.tolist())

                precinto_dict = edited_df.set_index("Nº Cliente")["N° de Precinto"].to_dict()
                for i, row in df_clientes.iterrows():
                    cliente_id = row["Nº Cliente"]
                    if cliente_id in precinto_dict:
                        new_precinto = precinto_dict[cliente_id]
                        sheet_clientes.update(f"F{i + 2}", new_precinto)

                st.success("✅ Cambios guardados correctamente.")
            except Exception as e:
                st.error(f"❌ Error al guardar los cambios: {e}")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar los datos: {e}")

# --- SECCIÓN 3: HISTORIAL POR CLIENTE ---
if opcion == "Historial por cliente":
    st.subheader("📜 Historial de reclamos por cliente")
    historial_cliente = st.text_input("🔍 Ingresá N° de Cliente para ver su historial").strip()

    if historial_cliente:
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
        historial = df_reclamos[df_reclamos["Nº Cliente"] == historial_cliente]

        if not historial.empty:
            historial["Fecha y hora"] = pd.to_datetime(historial["Fecha y hora"], errors="coerce")
            historial = historial.sort_values("Fecha y hora", ascending=False)

            st.success(f"🔎 Se encontraron {len(historial)} reclamos para el cliente {historial_cliente}.")
            st.dataframe(
                historial[
                    ["Fecha y hora", "Tipo de reclamo", "Estado", "Técnico", "N° de Precinto", "Detalles"]
                ],
                use_container_width=True
            )
        else:
            st.info("❕ Este cliente no tiene reclamos registrados.")

# --- SECCIÓN 4: EDITAR CLIENTE ---
if opcion == "Editar cliente":
    st.subheader("🛠️ Editar datos de un cliente")
    cliente_editar = st.text_input("🔎 Ingresá N° de Cliente a editar").strip()

    if cliente_editar:
        df_clientes["Nº Cliente"] = df_clientes["Nº Cliente"].astype(str).str.strip()
        cliente_row = df_clientes[df_clientes["Nº Cliente"] == cliente_editar]

        if not cliente_row.empty:
            cliente_actual = cliente_row.squeeze()
            nuevo_sector = st.text_input("🏙️ Sector", value=cliente_actual["Sector"])
            nuevo_nombre = st.text_input("👤 Nombre", value=cliente_actual["Nombre"])
            nueva_direccion = st.text_input("📍 Dirección", value=cliente_actual["Dirección"])
            nuevo_telefono = st.text_input("📞 Teléfono", value=cliente_actual["Teléfono"])
            nuevo_precinto = st.text_input("🔒 N° de Precinto", value=cliente_actual.get("N° de Precinto", ""))

            if st.button("💾 Actualizar datos del cliente"):
                try:
                    index = cliente_row.index[0] + 2  # +2 porque la hoja empieza en fila 2
                    sheet_clientes.update(f"B{index}", [[nuevo_sector.upper()]])
                    sheet_clientes.update(f"C{index}", [[nuevo_nombre.upper()]])
                    sheet_clientes.update(f"D{index}", [[nueva_direccion.upper()]])
                    sheet_clientes.update(f"E{index}", [[nuevo_telefono.upper()]])
                    sheet_clientes.update(f"F{index}", [[nuevo_precinto.upper()]])
                    st.success("✅ Cliente actualizado correctamente.")
                except Exception as e:
                    st.error(f"❌ Error al actualizar: {e}")
        else:
            st.warning("⚠️ Cliente no encontrado.")

    # --- NUEVO FORMULARIO PARA CARGAR CLIENTE DESDE CERO ---
    st.markdown("---")
    st.subheader("🆕 Cargar nuevo cliente")

    with st.form("form_nuevo_cliente"):
        nuevo_nro = st.text_input("🔢 N° de Cliente (nuevo)").strip()
        nuevo_sector = st.text_input("🏙️ Sector")
        nuevo_nombre = st.text_input("👤 Nombre")
        nueva_direccion = st.text_input("📍 Dirección")
        nuevo_telefono = st.text_input("📞 Teléfono")
        nuevo_precinto = st.text_input("🔒 N° de Precinto (opcional)")

        guardar_cliente = st.form_submit_button("💾 Guardar nuevo cliente")

        if guardar_cliente:
            if not nuevo_nro or not nuevo_nombre:
                st.error("⚠️ Debés ingresar al menos el N° de cliente y el nombre.")
            elif nuevo_nro in df_clientes["Nº Cliente"].values:
                st.warning("⚠️ Este cliente ya existe.")
            else:
                try:
                    nueva_fila = [
                        nuevo_nro,
                        nuevo_sector.upper(),
                        nuevo_nombre.upper(),
                        nueva_direccion.upper(),
                        nuevo_telefono,
                        nuevo_precinto
                    ]
                    sheet_clientes.append_row(nueva_fila)
                    st.success("✅ Nuevo cliente agregado correctamente.")
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")

# --- SECCIÓN 5: IMPRESIÓN ---
if opcion == "Imprimir reclamos":
    st.subheader("🖨️ Seleccionar reclamos para imprimir (formato técnico compacto)")

    try:
        df_pdf = df_reclamos.copy()
        df_merged = pd.merge(df_pdf, df_clientes[["Nº Cliente", "N° de Precinto"]], on="Nº Cliente", how="left")

        st.info("🕒 Reclamos pendientes de resolución")
        df_pendientes = df_merged[df_merged["Estado"] == "Pendiente"]
        if not df_pendientes.empty:
            st.dataframe(df_pendientes[["Fecha y hora", "Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]], use_container_width=True)
        else:
            st.success("✅ No hay reclamos pendientes actualmente.")

        solo_pendientes = st.checkbox("🧾 Mostrar solo reclamos pendientes para imprimir")

        # --- NUEVA FUNCIÓN: Imprimir por tipo de reclamo ---
        st.markdown("### 🧾 Imprimir reclamos por tipo")

        tipos_disponibles = sorted(df_merged["Tipo de reclamo"].unique())
        tipos_seleccionados = st.multiselect("Seleccioná tipos de reclamo a imprimir", tipos_disponibles)

        if tipos_seleccionados:
            reclamos_filtrados = df_merged[
                (df_merged["Estado"] == "Pendiente") & 
                (df_merged["Tipo de reclamo"].isin(tipos_seleccionados))
            ]

            if not reclamos_filtrados.empty:
                st.success(f"Se encontraron {len(reclamos_filtrados)} reclamos pendientes de los tipos seleccionados.")

                if st.button("📄 Generar PDF de reclamos por tipo"):
                    buffer = io.BytesIO()
                    c = canvas.Canvas(buffer, pagesize=A4)
                    width, height = A4
                    y = height - 40

                    for i, (_, reclamo) in enumerate(reclamos_filtrados.iterrows()):
                        c.setFont("Helvetica-Bold", 16)
                        c.drawString(40, y, f"Reclamo #{reclamo['Nº Cliente']}")
                        y -= 15
                        c.setFont("Helvetica", 12)
                        precinto_str = f" - Precinto: {reclamo['N° de Precinto']}" if reclamo.get("N° de Precinto") else ""
                        lineas = [
                            f"Fecha: {reclamo['Fecha y hora']} - Cliente: {reclamo['Nombre']} ({reclamo['Nº Cliente']})",
                            f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                            f"Sector: {reclamo['Sector']} - Precinto: {reclamo.get('N° de Precinto', '')} - Técnico: {reclamo['Técnico']}",
                            f"Tipo: {reclamo['Tipo de reclamo']}",
                            f"Detalles: {reclamo['Detalles'][:80]}..." if len(reclamo['Detalles']) > 80 else f"Detalles: {reclamo['Detalles']}",
                        ]
                        for linea in lineas:
                            c.drawString(40, y, linea)
                            y -= 12
                        y -= 8
                        c.drawString(40, y, "Firma técnico: _____________________________")
                        y -= 25
                        if y < 150 and i < len(reclamos_filtrados) - 1:
                            c.showPage()
                            y = height - 40

                    c.save()
                    buffer.seek(0)
                    st.download_button(
                        label="📥 Descargar PDF filtrado por tipo",
                        data=buffer,
                        file_name="reclamos_filtrados_por_tipo.pdf",
                        mime="application/pdf"
                    )
            else:
                st.info("No hay reclamos pendientes para los tipos seleccionados.")

        # --- FUNCIONALIDAD ORIGINAL: selección manual ---
        if solo_pendientes:
            df_merged = df_merged[df_merged["Estado"] == "Pendiente"]

        selected = st.multiselect("Seleccioná los reclamos a imprimir:", df_merged.index,
                                  format_func=lambda x: f"{df_merged.at[x, 'Nº Cliente']} - {df_merged.at[x, 'Nombre']}")

        if st.button("📄 Generar PDF con seleccionados") and selected:
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            y = height - 40

            for i, idx in enumerate(selected):
                reclamo = df_merged.loc[idx]
                c.setFont("Helvetica-Bold", 16)
                c.drawString(40, y, f"Reclamo #{reclamo['Nº Cliente']}")
                y -= 15
                c.setFont("Helvetica", 12)
                precinto_str = f" - Precinto: {reclamo['N° de Precinto']}" if reclamo.get("N° de Precinto") else ""
                lineas = [
                    f"Fecha: {reclamo['Fecha y hora']} - Cliente: {reclamo['Nombre']} ({reclamo['Nº Cliente']})",
                    f"Dirección: {reclamo['Dirección']} - Tel: {reclamo['Teléfono']}",
                    f"Sector: {reclamo['Sector']} - Precinto: {reclamo.get('N° de Precinto', '')} - Técnico: {reclamo['Técnico']}",
                    f"Tipo: {reclamo['Tipo de reclamo']}",
                    f"Detalles: {reclamo['Detalles'][:80]}..." if len(reclamo['Detalles']) > 80 else f"Detalles: {reclamo['Detalles']}",
                ]
                for linea in lineas:
                    c.drawString(40, y, linea)
                    y -= 12
                y -= 8
                c.drawString(40, y, "Firma técnico: _____________________________")
                y -= 25
                if y < 150 and i < len(selected) - 1:
                    c.showPage()
                    y = height - 40

            c.save()
            buffer.seek(0)
            st.download_button(
                label="📥 Descargar PDF",
                data=buffer,
                file_name="reclamos_seleccionados.pdf",
                mime="application/pdf"
            )

        elif not selected:
            st.info("Seleccioná al menos un reclamo para generar el PDF.")

    except Exception as e:
        st.error(f"❌ Error al generar PDF: {e}")

# --- SECCIÓN 6: SEGUIMIENTO TÉCNICO ---
import time  # Asegurate de tener esta línea al inicio del archivo si no estaba

if opcion == "Seguimiento técnico":
    st.subheader("👷 Seguimiento técnico del reclamo")
    cliente_input = st.text_input("🔍 Ingresá el N° de Cliente para actualizar su reclamo").strip()

    if cliente_input:
        df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
        df_filtrado = df_reclamos[
            (df_reclamos["Nº Cliente"] == cliente_input) &
            (df_reclamos["Estado"].isin(["Pendiente", "En curso"]))
        ]

        if df_filtrado.empty:
            st.warning("❕ Este cliente no tiene reclamos pendientes o en curso.")
        else:
            df_filtrado["Fecha y hora"] = pd.to_datetime(df_filtrado["Fecha y hora"], errors="coerce")
            df_filtrado = df_filtrado.dropna(subset=["Fecha y hora"])

            if df_filtrado.empty:
                st.warning("❕ Este cliente tiene reclamos sin fecha válida. No se puede determinar el más reciente.")
            else:
                df_ordenado = df_filtrado.sort_values("Fecha y hora", ascending=False)
                reclamo_actual = df_ordenado.iloc[0]
                index_reclamo = df_ordenado.index[0] + 2  # +2 por encabezado y base 1 en Sheets

                st.info(f"📅 Reclamo registrado el {reclamo_actual['Fecha y hora']}")
                st.write(f"📌 Tipo: **{reclamo_actual['Tipo de reclamo']}**")
                st.write(f"📍 Dirección: {reclamo_actual['Dirección']}")
                st.write(f"🔒 Precinto: {reclamo_actual.get('N° de Precinto', '')}")
                st.write(f"📄 Detalles: {reclamo_actual['Detalles']}")

                nuevo_estado = st.selectbox(
                    "⚙️ Cambiar estado",
                    ["Pendiente", "En curso", "Resuelto"],
                    index=["Pendiente", "En curso", "Resuelto"].index(reclamo_actual["Estado"])
                )

                tecnicos_actuales = [t.strip() for t in str(reclamo_actual.get("Técnico", "")).split(",") if t.strip()]
                tecnicos_actuales_filtrados = [
                    t for t in tecnicos_disponibles if t.lower() in [x.lower() for x in tecnicos_actuales]
                ]

                nuevos_tecnicos = st.multiselect(
                    "👷 Técnicos asignados",
                    tecnicos_disponibles,
                    default=tecnicos_actuales_filtrados
                )

                if st.button("💾 Actualizar reclamo"):
                    if not nuevos_tecnicos:
                        st.warning("⚠️ Debes asignar al menos un técnico para actualizar el reclamo.")
                    else:
                        try:
                            sheet_reclamos.batch_update([
                                {"range": f"I{index_reclamo}", "values": [[nuevo_estado]]},
                                {"range": f"J{index_reclamo}", "values": [[", ".join(nuevos_tecnicos).upper()]]}
                            ])
                            time.sleep(1)  # prevenir bloqueo de la API por llamadas seguidas
                            st.success("✅ Reclamo actualizado correctamente.")
                        except Exception as e:
                            st.error(f"❌ Error al actualizar: {e}")

    # --- IMPRIMIR RECLAMOS EN CURSO (OPTIMIZADO) ---
    st.markdown("---")
    st.markdown("### 🖨️ Imprimir reclamos 'En curso' (vista compacta optimizada)")

    reclamos_en_curso = df_reclamos[
        (df_reclamos["Estado"] == "En curso")
    ].copy()

    if reclamos_en_curso.empty:
        st.info("No hay reclamos en curso para imprimir.")
    else:
        reclamos_en_curso["Fecha y hora"] = pd.to_datetime(reclamos_en_curso["Fecha y hora"], errors="coerce")
        reclamos_en_curso = reclamos_en_curso.dropna(subset=["Fecha y hora"])
        reclamos_en_curso = reclamos_en_curso.sort_values("Fecha y hora", ascending=False)

        st.dataframe(
            reclamos_en_curso[["Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]],
            use_container_width=True
        )

        if st.button("📄 Generar PDF de reclamos en curso (más por hoja)"):
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            x_left = 40
            x_right = width / 2 + 10
            y = height - 40
            columna_izquierda = True

            for idx, reclamo in reclamos_en_curso.iterrows():
                x = x_left if columna_izquierda else x_right

                # Fuente más chica
                c.setFont("Helvetica-Bold", 10)
                c.drawString(x, y, f"{reclamo['Nº Cliente']} - {reclamo['Nombre']}")
                y -= 10
                c.setFont("Helvetica", 8)
                c.drawString(x, y, f"📌 {reclamo['Tipo de reclamo']}")
                y -= 9
                c.drawString(x, y, f"👷 {reclamo['Técnico']}")
                y -= 20  # Menos espacio entre bloques

                if not columna_izquierda:
                    y -= 3
                columna_izquierda = not columna_izquierda

                if y < 60:
                    c.showPage()
                    y = height - 40
                    columna_izquierda = True

            c.save()
            buffer.seek(0)
            st.download_button(
                label="📥 Descargar PDF optimizado",
                data=buffer,
                file_name="reclamos_en_curso_opt.pdf",
                mime="application/pdf"
            )

# --- SECCIÓN 7: CIERRE DE RECLAMOS ---
if opcion == "Cierre de Reclamos":
    st.subheader("✅ Cierre de reclamos en curso")

    df_reclamos["Nº Cliente"] = df_reclamos["Nº Cliente"].astype(str).str.strip()
    df_reclamos["Técnico"] = df_reclamos["Técnico"].astype(str).fillna("")

    en_curso = df_reclamos[df_reclamos["Estado"] == "En curso"].copy()

    if en_curso.empty:
        st.info("📭 No hay reclamos en curso en este momento.")
    else:
        tecnicos_unicos = sorted(set(", ".join(en_curso["Técnico"].tolist()).split(", ")))
        tecnicos_seleccionados = st.multiselect("👷 Filtrar por técnico asignado", tecnicos_unicos)

        if tecnicos_seleccionados:
            en_curso = en_curso[
                en_curso["Técnico"].apply(
                    lambda t: any(tecnico in t for tecnico in tecnicos_seleccionados)
                )
            ]

        st.write("### 📋 Reclamos en curso:")
        st.dataframe(en_curso[["Fecha y hora", "Nº Cliente", "Nombre", "Tipo de reclamo", "Técnico"]], use_container_width=True)

        st.markdown("### ✏️ Acciones por reclamo:")

        for i, row in en_curso.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 3, 2])
                with col1:
                    st.markdown(f"**#{row['Nº Cliente']} - {row['Nombre']}**")
                    st.markdown(f"📌 {row['Tipo de reclamo']}")
                    st.markdown(f"👷 {row['Técnico']}")

                    # Mostrar campo de precinto editable
                    cliente_id = str(row["Nº Cliente"]).strip()
                    cliente_info = df_clientes[df_clientes["Nº Cliente"] == cliente_id]
                    precinto_actual = cliente_info["N° de Precinto"].values[0] if not cliente_info.empty else ""
                    nuevo_precinto = st.text_input("🔒 Precinto", value=precinto_actual, key=f"precinto_{i}")

                with col2:
                    if st.button("✅ Resuelto", key=f"resolver_{i}"):
                        try:
                            argentina = pytz.timezone("America/Argentina/Buenos_Aires")
                            fecha_resolucion = datetime.now(argentina).strftime("%Y-%m-%d %H:%M:%S")

                            # Actualizar estado y fecha de resolución en la hoja de reclamos
                            sheet_reclamos.batch_update([
                                {"range": f"I{i + 2}", "values": [["Resuelto"]]},
                                {"range": f"M{i + 2}", "values": [[fecha_resolucion]]}
                            ])

                            # Si se ingresó un precinto, actualizarlo en hoja Clientes
                            if nuevo_precinto.strip():
                                if not cliente_info.empty:
                                    index_real = cliente_info.index[0] + 2
                                    sheet_clientes.update(f"F{index_real}", [[nuevo_precinto.strip()]])
                            st.success(f"🟢 Reclamo de {row['Nombre']} cerrado correctamente.")
                        except Exception as e:
                            st.error(f"❌ Error al actualizar: {e}")

                with col3:
                    if st.button("↩️ Pendiente", key=f"volver_{i}"):
                        try:
                            sheet_reclamos.batch_update([
                                {"range": f"I{i + 2}", "values": [["Pendiente"]]},
                                {"range": f"J{i + 2}", "values": [[""]]}
                            ])

                            st.success(f"🔄 Reclamo de {row['Nombre']} vuelto a PENDIENTE y técnicos limpiados.")
                        except Exception as e:
                            st.error(f"❌ Error al actualizar: {e}")