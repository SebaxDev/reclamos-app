"""
Configuración central de la aplicación
Versión 2.0 - Con gestión de usuarios y permisos
"""

# --------------------------
# CONFIGURACIÓN DE GOOGLE SHEETS
# --------------------------
SHEET_ID = "13R_3Mdr25Jd-nGhK7CxdcbKkFWLc0LPdYrOLOY8sZJo"
WORKSHEET_RECLAMOS = "Reclamos"
WORKSHEET_CLIENTES = "Clientes"
WORKSHEET_USUARIOS = "usuarios"  # Nueva hoja para usuarios

# --------------------------
# ESTRUCTURAS DE DATOS
# --------------------------
COLUMNAS_RECLAMOS = [
    "Fecha y hora", "Nº Cliente", "Sector", "Nombre", 
    "Dirección", "Teléfono", "Tipo de reclamo", 
    "Detalles", "Estado", "Técnico", "N° de Precinto", "Atendido por"
]

COLUMNAS_CLIENTES = [
    "Nº Cliente", "Sector", "Nombre", "Dirección", 
    "Teléfono", "N° de Precinto"
]

COLUMNAS_USUARIOS = [  # Nueva estructura para usuarios
    "username", "password", "nombre", "rol", "activo"
]

# --------------------------
# ROLES Y PERMISOS
# --------------------------
# Definición de permisos por rol
PERMISOS_POR_ROL = {
    'admin': {
        'descripcion': 'Acceso completo a todas las funciones',
        'permisos': ['*']  # El asterisco significa todos los permisos
    },
    'oficina': {
        'descripcion': 'Personal administrativo/atención al cliente',
        'permisos': [
            'inicio', 
            'reclamos_cargados', 
            'historial_cliente',
            'imprimir_reclamos'
        ]
    }
}

# Mapeo de opciones de navegación a permisos
OPCIONES_PERMISOS = {
    "Inicio": "inicio",
    "Reclamos cargados": "reclamos_cargados",
    "Historial por cliente": "historial_cliente",
    "Editar cliente": "editar_cliente",
    "Imprimir reclamos": "imprimir_reclamos",
    "Seguimiento técnico": "seguimiento_tecnico",
    "Cierre de Reclamos": "cierre_reclamos"
}

# --------------------------
# CONFIGURACIÓN DE LA APLICACIÓN
# --------------------------
TECNICOS_DISPONIBLES = [
    "Braian", "Conejo", "Juan", "Junior", "Maxi", 
    "Ramon", "Roque", "Viki", "Oficina", "Base"
]

TIPOS_RECLAMO = [
    "Conexion C+I", "Conexion Cable", "Conexion Internet", "Suma Internet",
    "Suma Cable", "Reconexion", "Sin Señal Ambos", "Sin Señal Cable",
    "Sin Señal Internet", "Sintonia", "Interferencia", "Traslado",
    "Extension", "Extension x3", "Extension x4", "Cambio de Ficha",
    "Cambio de Equipo", "Reclamo", "Desconexion a Pedido"
]

# --------------------------
# SEGURIDAD Y API
# --------------------------
API_DELAY = 1.5  # Segundos entre llamadas a la API
BATCH_DELAY = 2.0  # Segundos entre operaciones batch
SESSION_TIMEOUT = 1800  # 30 minutos de inactividad para cerrar sesión

# --------------------------
# FUNCIONES DE UTILIDAD
# --------------------------
def obtener_permisos_por_rol(rol):
    """Devuelve los permisos asociados a un rol"""
    return PERMISOS_POR_ROL.get(rol, {}).get('permisos', [])

def rol_tiene_permiso(rol, permiso_requerido):
    """Verifica si un rol tiene un permiso específico"""
    if permiso_requerido == 'admin':
        return rol == 'admin'  # Solo los admin pueden gestionar otros admin
    
    permisos = obtener_permisos_por_rol(rol)
    return '*' in permisos or permiso_requerido in permisos

# --------------------------
# CONFIGURACIÓN DE ESTILOS
# --------------------------
COLOR_ADMIN = "#FF5733"  # Naranja
COLOR_OFICINA = "#338AFF"  # Azul