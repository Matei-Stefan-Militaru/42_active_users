# 42 Network - Finding Your Evaluator


THis idea was aborted, we are just trying things.

Dashboard interactivo para encontrar usuarios activos en la red de campus 42.

## 🚀 Características

- **Filtrado por país y campus:** Navega fácilmente por toda la red 42
- **Múltiples métodos de búsqueda:** Híbrido, actividad reciente, ubicaciones activas
- **Análisis temporal:** Distribución de actividad por hora y día
- **Rankings y métricas:** Top usuarios, niveles, wallet y puntos
- **Interfaz optimizada:** Filtros intuitivos y visualizaciones claras

## 📁 Estructura del Proyecto

```
├── app.py                 # Aplicación principal
├── requirements.txt       # Dependencias
├── README.md             # Documentación
├── api/
│   ├── auth.py           # Autenticación con la API 42
│   ├── campus.py         # Gestión de campus
│   └── users.py          # Gestión de usuarios
├── config/
│   └── settings.py       # Configuraciones y constantes
└── ui/
    ├── sidebar.py        # Interfaz del sidebar
    ├── charts.py         # Gráficos y visualizaciones
    └── user_table.py     # Tabla de usuarios y métricas
```

## ⚙️ Configuración

### 1. Credenciales API 42

Agrega las credenciales en los secrets de Streamlit:

```toml
[api42]
client_id = "tu_client_id"
client_secret = "tu_client_secret"
```

### 2. Instalación

```bash
pip install -r requirements.txt
```

### 3. Ejecución

```bash
streamlit run app.py
```

## 🔍 Métodos de Búsqueda

- **Híbrido:** Combina usuarios en campus + actividad reciente (recomendado)
- **Solo actividad reciente:** Busca usuarios con actividad en el período especificado
- **Solo ubicaciones activas:** Solo usuarios actualmente en el campus

## 🛠️ Funcionalidades

### Dashboard Principal
- Métricas en tiempo real de usuarios activos
- Información del campus seleccionado
- Auto-actualización configurable

### Análisis Temporal
- Distribución de actividad por hora del día
- Tendencias de actividad por día
- Filtros por período de tiempo

### Gestión de Usuarios
- Lista filtrable de usuarios activos
- Rankings por nivel y métricas
- Exportación de datos

### Visualizaciones
- Gráficos interactivos con Plotly
- Distribución de niveles
- Top usuarios por diferentes métricas

## 🔧 Configuración Avanzada

### Opciones Disponibles
- **Días hacia atrás:** 1-30 días de actividad
- **Máximo de usuarios:** 20-500 usuarios
- **Modo debug:** Información detallada del proceso
- **Datos raw:** Visualización de datos originales de la API

### Rate Limiting
El sistema maneja automáticamente los límites de la API 42:
- Retry automático con backoff
- Gestión de tokens de acceso
- Cache inteligente para optimizar requests

## 🌍 Cobertura Global

Soporte completo para toda la red 42:
- Más de 40 países
- Más de 100 campus
- Estadísticas globales en tiempo real

## 🚨 Solución de Problemas

### No aparecen usuarios
- Aumenta el rango de días en opciones avanzadas
- Prueba diferentes métodos de búsqueda
- Verifica que el campus seleccionado esté activo

### Errores de autenticación
- Verifica las credenciales en secrets
- Comprueba que el client_id y client_secret sean válidos
- Asegúrate de tener permisos de lectura en la API

### Performance lenta
- Reduce el número máximo de usuarios
- Usa el método "Solo ubicaciones activas" para menos carga
- Activa cache para campus con pocos cambios

## 📊 Métricas Disponibles

- **Usuarios Activos:** Total de usuarios con actividad
- **Usuarios Únicos:** Count único de logins
- **Nivel Promedio:** Media de niveles de 42cursus
- **Usuarios en Campus:** Actualmente en ubicaciones físicas
- **Wallet Promedio:** Media de puntos de wallet
- **Evaluation Points:** Puntos de corrección disponibles

## 🔗 Integración con Otras Apps

El dashboard se integra con otras aplicaciones de la red 42:
- **42Stats:** Estadísticas generales
- **Tickets:** Gestión de tickets
- **Ranking Países:** Rankings globales (próximamente)

## 📈 Roadmap

- [ ] Notificaciones en tiempo real
- [ ] Exportación a Excel/CSV
- [ ] API pública para desarrolladores
- [ ] Integración con calendarios
- [ ] Sistema de favoritos
- [ ] Alertas personalizadas

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

📄 Licencia
Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.
👥 Autores

Desarrollado para la comunidad 42
Mantenido por estudiantes de 42

🙏 Agradecimientos

A la comunidad 42 por el feedback continuo
A Streamlit por la plataforma de desarrollo
A la API 42 por proporcionar los datos necesarios

📞 Soporte
Si tienes problemas o sugerencias:

Revisa la sección de solución de problemas
Busca en los issues existentes
Crea un nuevo issue con detalles del problema
Contacta a través de los canales oficiales de 42


42 Network - Finding Your Evaluator v2.3
Conectando estudiantes de 42 en todo el mundo 🌍
