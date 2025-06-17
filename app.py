import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Configuración de página
st.set_page_config(
    page_title="42 Active Users Dashboard",
    page_icon="🚀",
    layout="wide"
)

# CSS optimizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .status-success { 
        background: #e8f5e8; 
        border-left: 4px solid #4caf50; 
        padding: 10px; 
        border-radius: 4px; 
    }
    .status-error { 
        background: #ffebee; 
        border-left: 4px solid #f44336; 
        padding: 10px; 
        border-radius: 4px; 
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🚀 42 Network Active Users</h1>', unsafe_allow_html=True)

# Configuración en sidebar
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    
    # Campus selector mejorado
    campus_options = {
        "Barcelona": 46,
        "Madrid": 47,
        "Paris": 1,
        "Málaga": 101
    }
    
    selected_campus_name = st.selectbox(
        "🏫 Seleccionar Campus",
        options=list(campus_options.keys()),
        index=0
    )
    campus_id = campus_options[selected_campus_name]
    
    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-actualizar (30s)", value=False)
    refresh_button = st.button("🔄 Actualizar Ahora", type="primary", use_container_width=True)
    
    # Configuración avanzada
    with st.expander("⚙️ Opciones Avanzadas"):
        per_page = st.slider("Resultados por página", 50, 100, 100)
        show_raw_data = st.checkbox("Mostrar datos raw")
        max_pages = st.slider("Páginas máximas", 1, 10, 5)

# Función de autenticación mejorada
@st.cache_data(ttl=3500)  # Cache por 58 minutos (tokens duran 1 hora)
def get_auth_token(client_id, client_secret):
    """Obtener token de autenticación con cache"""
    auth_url = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    try:
        response = requests.post(auth_url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            st.error(f"❌ Error de autenticación: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None

# Función optimizada para obtener usuarios
def get_active_users_optimized(campus_id, token, per_page=100, max_pages=5):
    """Obtener usuarios activos de forma optimizada"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.intra.42.fr/v2/campus/{campus_id}/locations"
    params = {"per_page": per_page}
    
    all_users = []
    page_count = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while url and page_count < max_pages:
        try:
            status_text.text(f"Cargando página {page_count + 1}...")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                all_users.extend(data)
                page_count += 1
                
                # Actualizar progreso
                progress = min(page_count / max_pages, 1.0)
                progress_bar.progress(progress)
                
                # Obtener siguiente URL
                url = response.links.get("next", {}).get("url")
                params = None  # Solo usar params en primera petición
                
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 2))
                status_text.text(f"⏳ Rate limit - esperando {retry_after}s...")
                time.sleep(retry_after)
                
            else:
                st.warning(f"⚠️ Error HTTP {response.status_code}")
                break
                
        except requests.exceptions.Timeout:
            st.warning("⚠️ Timeout - intentando continuar...")
            break
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            break
    
    progress_bar.empty()
    status_text.empty()
    
    return all_users

# Función para procesar datos de usuarios
@st.cache_data
def process_user_data(users_raw):
    """Procesar datos de usuarios de forma eficiente"""
    processed_data = []
    
    for user_location in users_raw:
        user_info = user_location.get('user', {})
        if isinstance(user_info, dict) and user_info.get('login'):
            processed_data.append({
                'login': user_info.get('login'),
                'displayname': user_info.get('displayname', 'N/A'),
                'begin_at': user_location.get('begin_at'),
                'end_at': user_location.get('end_at'),
                'host': user_location.get('host'),
                'campus_id': user_location.get('campus_id')
            })
    
    return pd.DataFrame(processed_data) if processed_data else pd.DataFrame()

# Obtener credenciales
try:
    credentials = st.secrets.get("api", {})
    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")
    
    if not client_id or not client_secret:
        st.error("❌ Configura las credenciales en los secrets de Streamlit")
        st.info("Ve a Settings > Secrets y agrega:")
        st.code("""
[api]
client_id = "tu_client_id"
client_secret = "tu_client_secret"
        """)
        st.stop()
        
except Exception:
    st.error("❌ No se pueden leer las credenciales")
    st.stop()

# Auto-refresh logic
if auto_refresh:
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    if time.time() - st.session_state.last_refresh > 30:
        st.session_state.last_refresh = time.time()
        st.rerun()

# Trigger para actualizar datos
should_refresh = (
    refresh_button or 
    'users_data' not in st.session_state or 
    'current_campus' not in st.session_state or 
    st.session_state.get('current_campus') != campus_id
)

if should_refresh:
    # Autenticar
    with st.spinner("🔐 Autenticando..."):
        token = get_auth_token(client_id, client_secret)
        
        if not token:
            st.stop()
    
    # Mostrar estado en sidebar
    st.sidebar.markdown('<div class="status-success">✅ Autenticado</div>', unsafe_allow_html=True)
    
    # Obtener datos
    with st.spinner(f"📍 Cargando datos de {selected_campus_name}..."):
        users_raw = get_active_users_optimized(campus_id, token, per_page, max_pages)
        
        if users_raw:
            df = process_user_data(users_raw)
            
            # Guardar en session state
            st.session_state.users_data = df
            st.session_state.users_raw = users_raw
            st.session_state.current_campus = campus_id
            st.session_state.last_update = datetime.now()
            
            st.success(f"✅ {len(users_raw)} registros cargados, {len(df)} usuarios procesados")
        else:
            st.warning(f"⚠️ No se encontraron sesiones iniciadas en {selected_campus_name}")
            st.session_state.users_data = pd.DataFrame()

# Mostrar dashboard si hay datos
if 'users_data' in st.session_state and not st.session_state.users_data.empty:
    df = st.session_state.users_data
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🚀 Sesiones Iniciadas", len(df))
    
    with col2:
        unique_users = df['login'].nunique()
        st.metric("👤 Usuarios Únicos", unique_users)
    
    with col3:
        active_hosts = df['host'].nunique()
        st.metric("💻 Equipos Únicos", active_hosts)
    
    with col4:
        if 'last_update' in st.session_state:
            last_update = st.session_state.last_update.strftime("%H:%M:%S")
            st.metric("🕒 Última Actualización", last_update)
    
    # Procesar timestamps para gráficos
    df_viz = df.copy()
    
    try:
        # Convertir timestamps
        df_viz['begin_at'] = pd.to_datetime(df_viz['begin_at'], errors='coerce')
        df_viz = df_viz.dropna(subset=['begin_at'])
        
        if len(df_viz) > 0:
            df_viz['hour'] = df_viz['begin_at'].dt.hour
            df_viz['date'] = df_viz['begin_at'].dt.date
            
            # Gráfico de actividad por hora (usando el código que funciona)
            st.markdown("## 📈 Sesiones Iniciadas por Hora del Día")
            
            # Información temporal
            if len(df_viz) > 0:
                fecha_min = df_viz['begin_at'].min().strftime("%d/%m/%Y %H:%M")
                fecha_max = df_viz['begin_at'].max().strftime("%d/%m/%Y %H:%M")
                st.info(f"📅 **Período de datos:** {fecha_min} → {fecha_max}")
            
            # Usar el gráfico que funciona (basado en tu código)
            df_viz["hora"] = pd.to_datetime(df_viz["begin_at"]).dt.hour
            counts = df_viz["hora"].value_counts().sort_index()
            
            chart = px.bar(
                x=counts.index, 
                y=counts.values, 
                labels={"x": "Hora del Día", "y": "Sesiones Iniciadas"}, 
                title=f"Sesiones Iniciadas por Hora - Campus {selected_campus_name}"
            )
            
            # Personalizar el gráfico
            chart.update_traces(marker_color='rgba(102, 126, 234, 0.8)')
            chart.update_layout(
                height=400,
                showlegend=False,
                xaxis=dict(tickmode='linear', tick0=0, dtick=1),
                plot_bgcolor='white'
            )
            
            st.plotly_chart(chart, use_container_width=True)
            
            # Top equipos más utilizados
            if len(df) > 0:
                st.markdown("## 💻 Equipos Más Utilizados")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    host_counts = df['host'].value_counts().head(10)
                    
                    fig_hosts = go.Figure()
                    fig_hosts.add_trace(go.Bar(
                        y=host_counts.index[::-1],  # Invertir para mostrar el mayor arriba
                        x=host_counts.values[::-1],
                        orientation='h',
                        marker_color='rgba(118, 75, 162, 0.8)',
                        hovertemplate='<b>Equipo:</b> %{y}<br><b>Sesiones:</b> %{x}<extra></extra>'
                    ))
                    
                    fig_hosts.update_layout(
                        title="Top 10 Equipos Más Utilizados",
                        height=400,
                        xaxis_title="Sesiones Iniciadas",
                        yaxis_title="Equipo",
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_hosts, use_container_width=True)
                
                with col2:
                    # Usuarios más activos
                    user_counts = df['login'].value_counts().head(10)
                    
                    fig_users = go.Figure()
                    fig_users.add_trace(go.Bar(
                        y=user_counts.index[::-1],
                        x=user_counts.values[::-1],
                        orientation='h',
                        marker_color='rgba(102, 126, 234, 0.8)',
                        hovertemplate='<b>Usuario:</b> %{y}<br><b>Sesiones:</b> %{x}<extra></extra>'
                    ))
                    
                    fig_users.update_layout(
                        title="Top 10 Usuarios Más Activos",
                        height=400,
                        xaxis_title="Sesiones Iniciadas",
                        yaxis_title="Usuario",
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_users, use_container_width=True)
            
    except Exception as e:
        st.warning(f"⚠️ Error al procesar datos para visualización: {str(e)}")
    
    # Tabla de sesiones iniciadas
    st.markdown("## 🚀 Sesiones Iniciadas")
    
    # Preparar datos para mostrar
    display_df = df[['login', 'displayname', 'host', 'begin_at']].copy()
    
    # Formatear timestamps
    try:
        display_df['begin_at'] = pd.to_datetime(display_df['begin_at'], errors='coerce')
        display_df['formatted_time'] = display_df['begin_at'].dt.strftime('%H:%M:%S').fillna('N/A')
    except:
        display_df['formatted_time'] = 'N/A'
    
    # Reorganizar columnas
    display_df = display_df[['login', 'displayname', 'host', 'formatted_time']]
    display_df.columns = ['Login', 'Nombre', 'Equipo', 'Hora Inicio']
    
    # Filtros rápidos
    col1, col2 = st.columns(2)
    with col1:
        search_user = st.text_input("🔍 Buscar usuario", placeholder="Escribe un login...")
    with col2:
        search_host = st.text_input("🔍 Buscar equipo", placeholder="Escribe un nombre de equipo...")
    
    # Aplicar filtros
    filtered_df = display_df.copy()
    if search_user:
        filtered_df = filtered_df[filtered_df['Login'].str.contains(search_user, case=False, na=False)]
    if search_host:
        filtered_df = filtered_df[filtered_df['Equipo'].str.contains(search_host, case=False, na=False)]
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # Datos raw si está habilitado
    if show_raw_data and 'users_raw' in st.session_state:
        st.markdown("## 🔍 Datos Raw (Primeros 3 registros)")
        st.json(st.session_state.users_raw[:3])

else:
    # Estado inicial
    st.info(f"👆 Selecciona un campus y haz clic en **'Actualizar Ahora'** para cargar las sesiones iniciadas")
    
    # Mostrar información de ayuda
    with st.expander("ℹ️ Información"):
        st.markdown("""
        **Campuses disponibles:**
        - Barcelona: ID 46
        - Madrid: ID 47
        - Paris: ID 1
        - Málaga: ID 101
        
        **Qué muestra este dashboard:**
        - 🚀 **Sesiones iniciadas:** Cada vez que un estudiante inicia sesión en un equipo
        - 📊 **Distribución temporal:** Cuándo se inician más sesiones durante el día
        - 💻 **Equipos más utilizados:** Qué computadores son más populares
        - 👤 **Usuarios más activos:** Quién inicia más sesiones
        
        **Características técnicas:**
        - ✅ Cache inteligente para mejor rendimiento
        - ✅ Manejo de rate limits automático
        - ✅ Visualizaciones interactivas
        - ✅ Filtros de búsqueda
        - ✅ Auto-actualización opcional
        """)

# Footer
st.markdown("---")
st.markdown(
    f"💡 **Dashboard 42 Network** | "
    f"Campus: {selected_campus_name} ({campus_id}) | "
    f"🔄 Auto-actualizar: {'✅' if auto_refresh else '❌'}"
)
