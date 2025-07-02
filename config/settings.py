"""
Configuración central de la aplicación
"""

# Configuración de Google Sheets
SHEET_ID = "13R_3Mdr25Jd-nGhK7CxdcbKkFWLc0LPdYrOLOY8sZJo"
WORKSHEET_RECLAMOS = "Principal"
WORKSHEET_CLIENTES = "Clientes"

# Columnas esperadas
COLUMNAS_RECLAMOS = [
    "Fecha y hora", "Nº Cliente", "Sector", "Nombre", 
    "Dirección", "Teléfono", "Tipo de reclamo", 
    "Detalles", "Estado", "Técnico", "N° de Precinto", "Atendido por"
]

COLUMNAS_CLIENTES = [
    "Nº Cliente", "Sector", "Nombre", "Dirección", 
    "Teléfono", "N° de Precinto"
]

# Lista de técnicos disponibles
TECNICOS_DISPONIBLES = [
    "Braian", "Conejo", "Juan", "Junior", "Maxi", 
    "Ramon", "Roque", "Viki", "Oficina", "Base"
]

# Tipos de reclamos
TIPOS_RECLAMO = [
    "Conexion C+I", "Conexion Cable", "Conexion Internet", "Suma Internet",
    "Suma Cable", "Reconexion", "Sin Señal Ambos", "Sin Señal Cable",
    "Sin Señal Internet", "Sintonia", "Interferencia", "Traslado",
    "Extension x2", "Extension x3", "Extension x4", "Cambio de Ficha",
    "Cambio de Equipo", "Reclamo", "Desconexion a Pedido"
]

# Configuración de rate limiting
API_DELAY = 1.5  # Segundos entre llamadas a la API
BATCH_DELAY = 2.0  # Segundos entre operaciones batch