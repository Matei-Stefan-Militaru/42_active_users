import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# Configuración de página
st.set_page_config(
    page_title="42 Active Users Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar el diseño
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    .status-success {
        background: #e8f5e8;
        border: 1px solid #4caf50;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 1rem;
        color: #2e7d32;
    }
    
    .status-info {
        background: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 1rem;
        color: #1565c0;
    }
    
    .chart-container {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Función para obtener todos los campus
@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_all_campus(headers):
    """Obtener lista de todos los campus"""
    url = "https://api.intra.42.fr/v2/campus"
    all_campus = []
    
    while url:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                st.error(f"Error al obtener campus: {response.status_code}")
                break
            
            data = response.json()
            all_campus.extend(data)
            
            # Paginación
            url = response.links.get("next", {}).get("url")
            
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            break
    
    return all_campus

# Función para obtener usuarios activos de un campus
def get_active_users_by_campus(campus_id, headers, max_pages=10):
    """Obtener usuarios activos de un campus específico"""
    url = f"https://api.intra.42.fr/v2/campus/{campus_id}/locations"
    params = {"per_page": 100}
    
    users = []
    page_count = 0
    
    while url and page_count < max_pages:
        try:
            response = requests.get(url, headers=headers, params=params if page_count == 0 else None)
            if response.status_code != 200:
                st.warning(f"Error al obtener datos del campus {campus_id}: {response.status_code}")
                break
            
            data = response.json()
            users.extend(data)
            
            # Paginación
            url = response.links.get("next", {}).get("url")
            page_count += 1
            
            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            st.error(f"Error de conexión para campus {campus_id}: {e}")
            break
    
    return users

# Header principal
st.markdown('<h1 class="main-header">🚀 42 Network Active Users Dashboard</h1>', unsafe_allow_html=True)
st.markdown("### Monitoreo en tiempo real de estudiantes activos en los campus de 42")

# Sidebar para configuración
with st.sidebar:
    st.markdown("## ⚙️ Configuración API")
    
    # Mostrar cómo configurar secrets
    with st.expander("🔐 Configurar Credenciales"):
        st.markdown("Agrega esto a tus secrets en Streamlit:")
        st.code("""
[api]
client_id = "TU_CLIENT_ID"
client_secret = "TU_CLIENT_SECRET"
        """, language="toml")
    
    # Obtener credenciales
    credentials = st.secrets.get("api", {})
    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")
    
    if not client_id or not client_secret:
        st.error("❌ Faltan credenciales en los secrets")
        st.stop()
    else:
        st.markdown('<div class="status-success">✅ Credenciales configuradas correctamente</div>', unsafe_allow_html=True)

# Autenticación
with st.spinner("🔐 Autenticando con la API de 42..."):
    auth_url = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    auth_response = requests.post(auth_url, data=data)
    
    if auth_response.status_code != 200:
        st.error("❌ Error al obtener el token de acceso")
        st.write(auth_response.json())
        st.stop()
    
    access_token = auth_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {access_token}"}

# Mostrar estado de la API
with st.sidebar:
    st.markdown('<div class="status-info">🔒 Autenticación exitosa</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-info">⚡ Límites: 2 req/seg, 1200 req/hora</div>', unsafe_allow_html=True)

# Obtener lista de campus
with st.spinner("📍 Cargando campus disponibles..."):
    all_campus = get_all_campus(headers)

if not all_campus:
    st.error("No se pudieron cargar los campus")
    st.stop()

# Crear diccionario de países y campus
countries = {}
campus_dict = {}

for campus in all_campus:
    country = campus.get('country', 'Unknown')
    campus_name = campus.get('name', f"Campus {campus.get('id')}")
    campus_id = campus.get('id')
    
    if country not in countries:
        countries[country] = []
    
    countries[country].append({
        'name': campus_name,
        'id': campus_id,
        'city': campus.get('city', 'Unknown')
    })
    
    campus_dict[f"{campus_name} ({country})"] = {
        'id': campus_id,
        'country': country,
        'city': campus.get('city', 'Unknown')
    }

# Filtros en la sidebar
with st.sidebar:
    st.markdown("## 🔍 Filtros")
    
    # Filtro por país
    selected_countries = st.multiselect(
        "🌍 Países",
        options=list(countries.keys()),
        default=list(countries.keys())[:3] if len(countries) > 3 else list(countries.keys()),
        help="Selecciona los países que quieres monitorear"
    )
    
    # Filtro por campus basado en países seleccionados
    available_campus = []
    for country in selected_countries:
        for campus in countries[country]:
            available_campus.append(f"{campus['name']} ({country})")
    
    selected_campus = st.multiselect(
        "🏫 Campus",
        options=available_campus,
        default=available_campus[:5] if len(available_campus) > 5 else available_campus,
        help="Selecciona los campus específicos"
    )
    
    # Botón para actualizar datos
    refresh_data = st.button("🔄 Actualizar Datos", type="primary", use_container_width=True)

# Procesar datos si se seleccionaron campus
if selected_campus and (refresh_data or 'users_data' not in st.session_state):
    all_users_data = []
    
    # Barra de progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, campus_key in enumerate(selected_campus):
        campus_info = campus_dict[campus_key]
        campus_id = campus_info['id']
        
        status_text.text(f"📍 Cargando {campus_key}...")
        
        # Obtener usuarios activos
        users = get_active_users_by_campus(campus_id, headers)
        
        # Procesar datos
        for user_location in users:
            if isinstance(user_location.get('user'), dict):
                user_data = {
                    'login': user_location['user'].get('login'),
                    'displayname': user_location['user'].get('displayname', user_location['user'].get('login')),
                    'begin_at': user_location.get('begin_at'),
                    'end_at': user_location.get('end_at'),
                    'campus': campus_key.split(' (')[0],  # Nombre del campus sin país
                    'country': campus_info['country'],
                    'city': campus_info['city'],
                    'host': user_location.get('host'),
                    'campus_id': campus_id
                }
                all_users_data.append(user_data)
        
        # Actualizar progreso
        progress_bar.progress((i + 1) / len(selected_campus))
    
    # Guardar en session state
    st.session_state.users_data = all_users_data
    status_text.text("✅ ¡Datos cargados correctamente!")
    time.sleep(1)
    status_text.empty()
    progress_bar.empty()

# Mostrar datos si están disponibles
if 'users_data' in st.session_state and st.session_state.users_data:
    df = pd.DataFrame(st.session_state.users_data)
    
    # Estadísticas generales
    st.markdown("## 📊 Estadísticas Generales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "👥 Usuarios Activos", 
            len(df),
            help="Total de estudiantes conectados actualmente"
        )
    
    with col2:
        active_campus = df['campus'].nunique()
        st.metric(
            "🏫 Campus Activos", 
            active_campus,
            help="Número de campus con estudiantes conectados"
        )
    
    with col3:
        countries_active = df['country'].nunique()
        st.metric(
            "🌍 Países", 
            countries_active,
            help="Países con actividad actual"
        )
    
    with col4:
        # Calcular usuarios únicos
        unique_users = df['login'].nunique()
        st.metric(
            "👤 Usuarios Únicos", 
            unique_users,
            help="Estudiantes únicos (sin duplicados)"
        )
    
    # Convertir timestamps
    df['begin_at'] = pd.to_datetime(df['begin_at'])
    df['hora'] = df['begin_at'].dt.hour
    df['fecha'] = df['begin_at'].dt.date
    
    # Gráfico principal - Actividad por hora
    st.markdown("## 📈 Actividad por Hora del Día")
    
    hour_counts = df['hora'].value_counts().sort_index()
    
    # Crear gráfico con Plotly
    fig_hours = go.Figure()
    
    fig_hours.add_trace(go.Bar(
        x=hour_counts.index,
        y=hour_counts.values,
        marker_color='rgba(102, 126, 234, 0.8)',
        marker_line_color='rgba(102, 126, 234, 1)',
        marker_line_width=2,
        name='Usuarios Activos'
    ))
    
    fig_hours.update_layout(
        title={
            'text': 'Distribución de Usuarios Activos por Hora',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        xaxis_title="Hora del Día",
        yaxis_title="Número de Usuarios",
        template="plotly_white",
        height=400,
        showlegend=False
    )
    
    fig_hours.update_xaxis(tickmode='linear', tick0=0, dtick=1)
    
    st.plotly_chart(fig_hours, use_container_width=True)
    
    # Gráficos adicionales
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🌍 Usuarios por País")
        country_counts = df['country'].value_counts()
        
        fig_countries = px.pie(
            values=country_counts.values,
            names=country_counts.index,
            title="Distribución por Países"
        )
        fig_countries.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_countries, use_container_width=True)
    
    with col2:
        st.markdown("### 🏫 Usuarios por Campus")
        campus_counts = df['campus'].value_counts()
        
        fig_campus = px.bar(
            x=campus_counts.values,
            y=campus_counts.index,
            orientation='h',
            title="Actividad por Campus"
        )
        fig_campus.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_campus, use_container_width=True)
    
    # Tabla de usuarios activos
    st.markdown("## 👥 Usuarios Activos Actualmente")
    
    # Filtros para la tabla
    col1, col2, col3 = st.columns(3)
    
    with col1:
        country_filter = st.selectbox(
            "Filtrar por País",
            options=['Todos'] + list(df['country'].unique()),
            key='country_filter'
        )
    
    with col2:
        campus_filter = st.selectbox(
            "Filtrar por Campus",
            options=['Todos'] + list(df['campus'].unique()),
            key='campus_filter'
        )
    
    with col3:
        show_duplicates = st.checkbox(
            "Mostrar usuarios duplicados",
            help="Algunos usuarios pueden aparecer en múltiples ubicaciones"
        )
    
    # Aplicar filtros
    filtered_df = df.copy()
    
    if country_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['country'] == country_filter]
    
    if campus_filter != 'Todos':
        filtered_df = filtered_df[filtered_df['campus'] == campus_filter]
    
    if not show_duplicates:
        filtered_df = filtered_df.drop_duplicates(subset=['login'])
    
    # Preparar datos para mostrar
    display_df = filtered_df[['login', 'displayname', 'campus', 'country', 'host', 'begin_at']].copy()
    display_df['begin_at'] = display_df['begin_at'].dt.strftime('%H:%M:%S')
    display_df = display_df.rename(columns={
        'login': 'Login',
        'displayname': 'Nombre',
        'campus': 'Campus',
        'country': 'País',
        'host': 'Puesto',
        'begin_at': 'Hora Inicio'
    })
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
    
    # Información adicional
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"📊 **Mostrando:** {len(filtered_df)} usuarios")
    
    with col2:
        last_update = datetime.now().strftime("%H:%M:%S")
        st.info(f"🕒 **Última actualización:** {last_update}")

elif selected_campus:
    st.info("👆 Haz clic en '🔄 Actualizar Datos' para cargar la información")
else:
    st.warning("⚠️ Selecciona al menos un campus para ver los datos")

# Footer
st.markdown("---")
st.markdown(
    "💡 **Tip:** Los datos se actualizan en tiempo real. "
    "Usa los filtros para enfocarte en campus específicos."
)
