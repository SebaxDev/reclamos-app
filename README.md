# 📋 Fusion Reclamos App

Una aplicación moderna y optimizada para la gestión de reclamos técnicos, desarrollada con Streamlit y Google Sheets como base de datos.

## ✨ Características

- 🔐 **Sistema de autenticación** seguro
- 📊 **Dashboard de métricas** en tiempo real
- 🗂️ **Gestión completa de reclamos** (crear, editar, seguimiento, cierre)
- 👥 **Administración de clientes** con historial completo
- 🖨️ **Generación de PDFs** para técnicos
- 📱 **Diseño responsive** y moderno
- ⚡ **Control de API** para evitar bloqueos
- 🎨 **Interfaz intuitiva** con animaciones

## 🚀 Instalación

### Prerrequisitos

- Python 3.8 o superior
- Cuenta de Google con acceso a Google Sheets API
- Streamlit

### Configuración

1. **Clonar el repositorio:**
```bash
git clone https://github.com/tu-usuario/fusion-reclamos-app.git
cd fusion-reclamos-app
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar Google Sheets API:**
   - Crear un proyecto en [Google Cloud Console](https://console.cloud.google.com/)
   - Habilitar Google Sheets API y Google Drive API
   - Crear credenciales de cuenta de servicio
   - Descargar el archivo JSON de credenciales

4. **Configurar secrets.toml:**
```bash
mkdir .streamlit
```

Crear el archivo `.streamlit/secrets.toml`:
```toml
[gcp_service_account]
type = "service_account"
project_id = "tu-project-id"
private_key_id = "tu-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\ntu-private-key\n-----END PRIVATE KEY-----\n"
client_email = "tu-service-account@tu-project.iam.gserviceaccount.com"
client_id = "tu-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/tu-service-account%40tu-project.iam.gserviceaccount.com"

[auth]
admin = "tu-password-admin"
tecnico = "tu-password-tecnico"
```

5. **Configurar Google Sheets:**
   - Crear una hoja de cálculo en Google Sheets
   - Compartir con el email de la cuenta de servicio
   - Crear dos hojas: "Principal" (reclamos) y "Clientes"
   - Actualizar el SHEET_ID en `config/settings.py`

## 🏃‍♂️ Uso

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`

## 📁 Estructura del Proyecto

```
fusion-reclamos-app/
├── app.py                     # Aplicación principal
├── requirements.txt           # Dependencias
├── components/               # Componentes modulares
│   ├── auth.py              # Autenticación
│   ├── navigation.py        # Navegación
│   └── metrics_dashboard.py # Dashboard
├── config/                  # Configuración
│   └── settings.py         # Configuraciones centrales
└── utils/                  # Utilidades
    ├── api_manager.py      # Gestor de API
    ├── data_manager.py     # Gestor de datos
    └── styles.py          # Estilos CSS
```

## 🔧 Configuración Avanzada

### Variables de Entorno

Puedes configurar las siguientes variables en `config/settings.py`:

- `SHEET_ID`: ID de tu Google Sheet
- `API_DELAY`: Tiempo entre llamadas a la API (default: 1.5s)
- `BATCH_DELAY`: Tiempo entre operaciones batch (default: 2.0s)
- `TECNICOS_DISPONIBLES`: Lista de técnicos
- `TIPOS_RECLAMO`: Tipos de reclamos disponibles

### Personalización

- **Estilos**: Modifica `utils/styles.py` para cambiar la apariencia
- **Componentes**: Agrega nuevos componentes en la carpeta `components/`
- **Configuración**: Ajusta parámetros en `config/settings.py`

## 📊 Funcionalidades

### 🏠 Inicio
- Cargar nuevos reclamos
- Validación de clientes existentes
- Prevención de reclamos duplicados

### 📊 Reclamos Cargados
- Vista completa de todos los reclamos
- Filtros por estado, sector y tipo
- Editor de datos en tiempo real
- Métricas por tipo de reclamo

### 📜 Historial por Cliente
- Búsqueda por número de cliente
- Historial completo ordenado por fecha
- Información detallada del cliente

### ✏️ Editar Cliente
- Modificar datos existentes
- Agregar nuevos clientes
- Validaciones de integridad

### 🖨️ Imprimir Reclamos
- Filtrado por tipo de reclamo
- Selección manual de reclamos
- Generación de PDFs optimizados
- Formato técnico compacto

### 👷 Seguimiento Técnico
- Actualización de estados
- Asignación de técnicos
- Vista de reclamos en curso
- PDFs optimizados para técnicos

### ✅ Cierre de Reclamos
- Cierre masivo por técnico
- Actualización de precintos
- Reversión a estado pendiente

## 🛡️ Seguridad

- Autenticación basada en secrets
- Control de acceso por usuario
- Validación de datos de entrada
- Rate limiting para API calls

## 🚀 Despliegue

### Streamlit Cloud

1. Subir el código a GitHub
2. Conectar con Streamlit Cloud
3. Configurar secrets en la interfaz web
4. Desplegar automáticamente

### Docker (Opcional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
```

## 🤝 Contribución

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o consultas:
- Crear un issue en GitHub
- Contactar al equipo de desarrollo

## 🔄 Changelog

### v2.0.0 (Actual)
- ✨ Arquitectura modular completa
- 🎨 Interfaz rediseñada con animaciones
- ⚡ Control optimizado de API
- 📊 Dashboard de métricas mejorado
- 🖨️ Sistema de PDFs avanzado
- 🔐 Sistema de autenticación robusto

### v1.0.0
- 📋 Funcionalidades básicas de gestión
- 🗂️ Integración con Google Sheets
- 📄 Generación básica de reportes