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
    layout="wide"
)

# CSS mejorado pero ligero
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
    .status-success { background: #e8f5e8; border-left: 4px solid #4caf50; padding: 10px; border-radius: 4px; }
    .status-info { background: #e3f2fd; border-left: 4px solid #2196f3; padding: 10px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🚀 42 Network Active Users</h1>', unsafe_allow_html=True)

# Configuración rápida en sidebar
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    
    with st.expander("🔐 Configurar Credenciales"):
        st.code("""
[api]
client_id = "TU_CLIENT_ID"
client_secret = "TU_CLIENT_SECRET"
        """, language="toml")
    
    # Campus ID selector
    campus_id = st.number_input(
        "🏫 Campus ID", 
        value=46, 
        min_value=1, 
        help="ID del campus a consultar (46 = Barcelona)"
    )
    
    # Botón de actualización
    refresh = st.button("🔄 Actualizar", type="primary", use_container_width=True)
    
    # Configuración opcional
    with st.expander("⚙️ Configuración Avanzada"):
        per_page = st.slider("Resultados por página", 50, 100, 100)
        show_raw_data = st.checkbox("Mostrar datos raw", value=False)

# Obtener credenciales
credentials = st.secrets.get("api", {})
client_id = credentials.get("client_id")
client_secret = credentials.get("client_secret")

if not client_id or not client_secret:
    st.error("❌ Faltan credenciales en los secrets")
    st.stop()

# Función rápida de autenticación (sin cache innecesario)
def get_auth_token():
    auth_url = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    response = requests.post(auth_url, data=data)
    if response.status_code != 200:
        st.error("❌ Error de autenticación")
        return None
    
    return response.json().get("access_token")

# Función optimizada para obtener usuarios (SIN delays artificiales)
def get_active_users_fast(campus_id, headers, per_page=100):
    """Obtener usuarios activos de forma rápida"""
    url = f"https://api.intra.42.fr/v2/campus/{campus_id}/locations"
    params = {"per_page": per_page}
    
    all_users = []
    
    while url:
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                all_users.extend(data)
                
                # Paginación
                url = response.links.get("next", {}).get("url")
                params = None  # Solo usar params en la primera petición
                
            elif response.status_code == 429:
                # Rate limit - esperar solo el tiempo mínimo necesario
                retry_after = int(response.headers.get('Retry-After', 1))
                st.warning(f"⏳ Esperando {retry_after}s...")
                time.sleep(retry_after)
                
            else:
                st.warning(f"⚠️ Error {response.status_code}")
                break
                
        except Exception as e:
            st.error(f"❌ Error: {e}")
            break
    
    return all_users

# Autenticar solo cuando sea necesario
if refresh or 'access_token' not in st.session_state:
    with st.spinner("🔐 Conectando..."):
        token = get_auth_token()
        if token:
            st.session_state.access_token = token
            st.sidebar.markdown('<div class="status-success">✅ Conectado</div>', unsafe_allow_html=True)
        else:
            st.stop()

headers = {"Authorization": f"Bearer {st.session_state.access_token}"}

# Obtener datos solo cuando se solicite
if refresh or 'users_data' not in st.session_state:
    with st.spinner(f"📍 Cargando campus {campus_id}..."):
        users = get_active_users_fast(campus_id, headers, per_page)
        
        if users:
            st.session_state.users_data = users
            st.session_state.last_update = datetime.now()
            st.success(f"✅ {len(users)} registros cargados")
        else:
            st.warning("⚠️ No se encontraron usuarios activos")
            st.session_state.users_data = []

# Mostrar datos si están disponibles
if 'users_data' in st.session_state and st.session_state.users_data:
    users = st.session_state.users_data
    
    # Procesar datos de forma eficiente
    processed_data = []
    for user_location in users:
        if isinstance(user_location.get('user'), dict):
            processed_data.append({
                'login': user_location['user'].get('login'),
                'displayname': user_location['user'].get('displayname'),
                'begin_at': user_location.get('begin_at'),
                'end_at': user_location.get('end_at'),
                'host': user_location.get('host')
            })
    
    if processed_data:
        df = pd.DataFrame(processed_data)
        
        # Métricas rápidas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Usuarios Activos", len(df))
        with col2:
            unique_users = df['login'].nunique()
            st.metric("👤 Usuarios Únicos", unique_users)
        with col3:
            active_hosts = df['host'].nunique()
            st.metric("💻 Equipos Activos", active_hosts)
        with col4:
            if 'last_update' in st.session_state:
                last_update = st.session_state.last_update.strftime("%H:%M:%S")
                st.metric("🕒 Actualizado", last_update)
        
        # Procesar timestamps de forma segura
        try:
            df['begin_at'] = pd.to_datetime(df['begin_at'], errors='coerce')
            df['hora'] = df['begin_at'].dt.hour
            
            # Gráfico de actividad por hora (optimizado)
            df_valid = df.dropna(subset=['hora'])
            if len(df_valid) > 0:
                st.markdown("## 📈 Actividad por Hora")
                
                hour_counts = df_valid['hora'].value_counts().sort_index()
                
                # Gráfico optimizado
                fig = go.Figure(data=[
                    go.Bar(
                        x=hour_counts.index,
                        y=hour_counts.values,
                        marker_color='rgba(102, 126, 234, 0.8)',
                        name='Usuarios Activos'
                    )
                ])
                
                fig.update_layout(
                    title="Distribución por Hora del Día",
                    xaxis_title="Hora",
                    yaxis_title="Usuarios",
                    height=400,
                    showlegend=False,
                    xaxis=dict(tickmode='linear', tick0=0, dtick=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.warning(f"⚠️ Error al procesar timestamps: {e}")
        
        # Tabla de usuarios
        st.markdown("## 👥 Usuarios Activos")
        
        # Preparar datos para mostrar
        display_df = df[['login', 'displayname', 'host', 'begin_at']].copy()
        
        # Formatear timestamps
        try:
            display_df['begin_at'] = pd.to_datetime(display_df['begin_at'], errors='coerce')
            display_df['begin_at'] = display_df['begin_at'].dt.strftime('%H:%M:%S')
            display_df['begin_at'] = display_df['begin_at'].fillna('N/A')
        except:
            display_df['begin_at'] = 'N/A'
        
        # Renombrar columnas
        display_df.columns = ['Login', 'Nombre', 'Equipo', 'Hora Inicio']
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # Datos raw opcionales
        if show_raw_data:
            st.markdown("## 🔍 Datos Raw")
            st.json(users[:3])  # Solo mostrar los primeros 3 para no sobrecargar
    
    else:
        st.info("📝 No hay datos de usuarios para mostrar")

elif 'users_data' in st.session_state:
    st.info("⚠️ No hay usuarios activos en este momento")
else:
    st.info("👆 Haz clic en 'Actualizar' para cargar los datos")

# Footer simple
st.markdown("---")
st.markdown(
    "💡 **Tips:** "
    "Campus Barcelona = 46 | "
    "Campus Madrid = 47 | "
    "Actualiza manualmente para datos frescos"
)
