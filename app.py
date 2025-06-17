import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

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
    .status-success { 
        background: #e8f5e8; 
        border-left: 4px solid #4caf50; 
        padding: 10px; 
        border-radius: 4px; 
    }
    .status-info { 
        background: #e3f2fd; 
        border-left: 4px solid #2196f3; 
        padding: 10px; 
        border-radius: 4px; 
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🚀 42 Network - Usuarios Activos</h1>', unsafe_allow_html=True)

# Configuración en sidebar
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    
    with st.expander("🔐 Configurar Credenciales"):
        st.markdown("Agrega esto a tus secrets:")
        st.code("""
[api42]
client_id = "TU_CLIENT_ID"
client_secret = "TU_CLIENT_SECRET"
        """, language="toml")
    
    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-actualizar (60s)", value=False)
    refresh_button = st.button("🔍 Ver usuarios activos", type="primary", use_container_width=True)
    
    # Configuración avanzada
    with st.expander("⚙️ Opciones Avanzadas"):
        days_back = st.slider("Días hacia atrás", 1, 7, 1)
        show_raw_data = st.checkbox("Mostrar datos raw")
        show_charts = st.checkbox("Mostrar gráficos", value=True)

# Obtener credenciales (usando tu estructura)
credentials = st.secrets.get("api42", {})
client_id = credentials.get("client_id")
client_secret = credentials.get("client_secret")

if not client_id or not client_secret:
    st.error("❌ Faltan credenciales en los secrets. Verifica que estén correctamente configuradas en [api42].")
    st.stop()

# Función de autenticación (basada en tu código)
@st.cache_data(ttl=3500)
def get_auth_token(client_id, client_secret):
    """Obtener token de acceso"""
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

# Función para obtener campus (usando tu código con cache)
@st.cache_data(ttl=3600)
def get_campus(headers):
    """Obtener lista de campus"""
    try:
        res = requests.get("https://api.intra.42.fr/v2/campus", headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
        else:
            st.error(f"❌ Error al obtener campus: {res.status_code}")
            return []
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return []

# Función para obtener usuarios activos (basada en tu código)
def get_active_users(campus_id, headers, days_back=1):
    """Obtener usuarios activos basado en tu código funcional"""
    users = []
    page = 1
    now = datetime.utcnow()
    past_date = now - timedelta(days=days_back)
    date_filter = past_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    max_pages = 20  # Límite de páginas para evitar bucles infinitos
    
    while page <= max_pages:
        try:
            status_text.text(f"Cargando página {page}...")
            
            url = (
                f"https://api.intra.42.fr/v2/campus/{campus_id}/users?"
                f"page[size]=100&page[number]={page}&"
                f"sort=-updated_at&filter[updated_at]={date_filter},"
            )
            
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                data = res.json()
                if not data:  # No más datos
                    break
                    
                users.extend(data)
                page += 1
                
                # Actualizar progreso
                progress = min(page / max_pages, 1.0)
                progress_bar.progress(progress)
                
            elif res.status_code == 429:
                retry_after = int(res.headers.get('Retry-After', 2))
                status_text.text(f"⏳ Rate limit - esperando {retry_after}s...")
                time.sleep(retry_after)
                
            else:
                st.warning(f"⚠️ Error HTTP {res.status_code} en página {page}")
                break
                
        except requests.exceptions.Timeout:
            st.warning(f"⚠️ Timeout en página {page} - continuando...")
            break
        except Exception as e:
            st.error(f"❌ Error en página {page}: {str(e)}")
            break
    
    progress_bar.empty()
    status_text.empty()
    
    return users

# Auto-refresh logic
if auto_refresh:
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    if time.time() - st.session_state.last_refresh > 60:
        st.session_state.last_refresh = time.time()
        st.rerun()

# Obtener token
token = get_auth_token(client_id, client_secret)
if not token:
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

# Obtener campus
campus_list = get_campus(headers)
if not campus_list:
    st.error("❌ No se pudieron cargar los campus")
    st.stop()

campus_dict = {campus["name"]: campus["id"] for campus in campus_list}

# Selector de campus
selected_campus = st.selectbox(
    "🏫 Selecciona un campus",
    list(campus_dict.keys()),
    index=0 if campus_dict else 0
)

if selected_campus:
    campus_id = campus_dict[selected_campus]
    
    # Mostrar información del campus seleccionado
    st.sidebar.markdown(f"**Campus seleccionado:** {selected_campus} (ID: {campus_id})")
    st.sidebar.markdown('<div class="status-success">✅ Conectado</div>', unsafe_allow_html=True)

# Trigger para cargar datos
if refresh_button or (auto_refresh and 'users_data' not in st.session_state):
    with st.spinner(f"🔍 Cargando usuarios activos de {selected_campus}..."):
        users = get_active_users(campus_id, headers, days_back)
        
        if not users:
            st.info(f"📝 No se encontraron usuarios activos en {selected_campus} en los últimos {days_back} día(s).")
            st.session_state.users_data = pd.DataFrame()
        else:
            # Procesar datos (usando tu estructura)
            df = pd.DataFrame([
                {
                    "Login": user["login"],
                    "Nombre": user["displayname"],
                    "Correo": user["email"],
                    "Última conexión": user["updated_at"],
                    "Nivel": user.get("cursus_users", [{}])[0].get("level", 0) if user.get("cursus_users") else 0,
                    "Campus": user.get("campus", [{}])[0].get("name", "N/A") if user.get("campus") else "N/A"
                }
                for user in users
            ])
            
            # Procesar timestamps
            df["Última conexión"] = pd.to_datetime(df["Última conexión"]).dt.tz_localize(None)
            
            # Guardar en session state
            st.session_state.users_data = df
            st.session_state.users_raw = users
            st.session_state.last_update = datetime.now()
            st.session_state.selected_campus = selected_campus
            st.session_state.days_back = days_back
            
            st.success(f"✅ Usuarios activos en {selected_campus} (últimos {days_back} día(s)): **{len(df)}**")

# Mostrar datos si están disponibles
if 'users_data' in st.session_state and not st.session_state.users_data.empty:
    df = st.session_state.users_data
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Usuarios Activos", len(df))
    
    with col2:
        # Usuarios únicos por login
        unique_users = df['Login'].nunique()
        st.metric("👤 Usuarios Únicos", unique_users)
    
    with col3:
        # Promedio de nivel
        avg_level = df['Nivel'].mean()
        st.metric("📊 Nivel Promedio", f"{avg_level:.1f}")
    
    with col4:
        # Última actualización
        if 'last_update' in st.session_state:
            last_update = st.session_state.last_update.strftime("%H:%M:%S")
            st.metric("🕒 Actualizado", last_update)
    
    # Información temporal
    fecha_min = df['Última conexión'].min().strftime("%d/%m/%Y %H:%M")
    fecha_max = df['Última conexión'].max().strftime("%d/%m/%Y %H:%M")
    st.info(f"📅 **Período de actividad:** {fecha_min} → {fecha_max} | **Campus:** {st.session_state.get('selected_campus', 'N/A')}")
    
    # Gráficos (si están habilitados)
    if show_charts:
        # Actividad por hora del día
        st.markdown("## 📈 Actividad por Hora del Día")
        
        df_chart = df.copy()
        df_chart['hora'] = df_chart['Última conexión'].dt.hour
        counts = df_chart['hora'].value_counts().sort_index()
        
        # Usar plotly.express como en tu código
        chart = px.bar(
            x=counts.index, 
            y=counts.values, 
            labels={"x": "Hora del Día", "y": "Usuarios Activos"}, 
            title=f"Distribución de Actividad - {st.session_state.get('selected_campus', 'Campus')}"
        )
        
        # Personalizar
        chart.update_traces(marker_color='rgba(102, 126, 234, 0.8)')
        chart.update_layout(
            height=400,
            showlegend=False,
            xaxis=dict(tickmode='linear', tick0=0, dtick=1),
            plot_bgcolor='white'
        )
        
        st.plotly_chart(chart, use_container_width=True)
        
        # Gráfico adicional: Distribución por días
        st.markdown("## 📅 Actividad por Días")
        
        df_chart['fecha'] = df_chart['Última conexión'].dt.date
        daily_counts = df_chart['fecha'].value_counts().sort_index()
        
        chart_daily = px.line(
            x=daily_counts.index, 
            y=daily_counts.values, 
            labels={"x": "Fecha", "y": "Usuarios Activos"}, 
            title="Tendencia de Actividad Diaria"
        )
        
        chart_daily.update_traces(line_color='rgba(118, 75, 162, 0.8)', line_width=3)
        chart_daily.update_layout(height=350, plot_bgcolor='white')
        
        st.plotly_chart(chart_daily, use_container_width=True)
        
        # Top usuarios por nivel
        if len(df) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏆 Top 10 Usuarios por Nivel")
                top_users = df.nlargest(10, 'Nivel')[['Login', 'Nombre', 'Nivel']]
                st.dataframe(top_users, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("### 📊 Distribución de Niveles")
                level_ranges = pd.cut(df['Nivel'], bins=[0, 5, 10, 15, 20, float('inf')], 
                                    labels=['0-5', '6-10', '11-15', '16-20', '20+'])
                level_counts = level_ranges.value_counts()
                
                fig_levels = px.pie(
                    values=level_counts.values, 
                    names=level_counts.index,
                    title="Distribución por Rangos de Nivel"
                )
                fig_levels.update_layout(height=300)
                st.plotly_chart(fig_levels, use_container_width=True)
    
    # Tabla principal
    st.markdown("## 👥 Lista de Usuarios Activos")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        search_user = st.text_input("🔍 Buscar por login/nombre", placeholder="Escribe aquí...")
    with col2:
        min_level = st.number_input("📊 Nivel mínimo", min_value=0, max_value=50, value=0)
    
    # Aplicar filtros
    filtered_df = df.copy()
    if search_user:
        mask = (filtered_df['Login'].str.contains(search_user, case=False, na=False) |
                filtered_df['Nombre'].str.contains(search_user, case=False, na=False))
        filtered_df = filtered_df[mask]
    
    if min_level > 0:
        filtered_df = filtered_df[filtered_df['Nivel'] >= min_level]
    
    # Formatear para mostrar
    display_df = filtered_df[['Login', 'Nombre', 'Nivel', 'Última conexión']].copy()
    display_df['Última conexión'] = display_df['Última conexión'].dt.strftime('%d/%m/%Y %H:%M')
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    # Datos raw si están habilitados
    if show_raw_data and 'users_raw' in st.session_state:
        st.markdown("## 🔍 Datos Raw (Primeros 3 registros)")
        st.json(st.session_state.users_raw[:3])

else:
    # Estado inicial
    st.info("👆 Selecciona un campus y haz clic en **'Ver usuarios activos'** para cargar los datos")
    
    # Información de ayuda
    with st.expander("ℹ️ Información de Uso"):
        st.markdown("""
        **¿Qué muestra este dashboard?**
        - 👥 **Usuarios activos:** Estudiantes que han tenido actividad reciente en el campus
        - 📊 **Análisis temporal:** Cuándo son más activos los usuarios durante el día
        - 🏆 **Rankings:** Top usuarios por nivel y distribución
        - 📈 **Tendencias:** Patrones de actividad por días
        
        **Funcionalidades:**
        - ✅ **Selección de campus:** Cualquier campus de la red 42
        - ✅ **Filtros temporales:** Configurable de 1 a 7 días
        - ✅ **Auto-actualización:** Cada 60 segundos si está habilitada
        - ✅ **Búsqueda y filtros:** Por usuario y nivel
        - ✅ **Visualizaciones interactivas:** Gráficos responsive
        
        **Configuración de credenciales:**
        ```toml
        [api42]
        client_id = "tu_client_id"
        client_secret = "tu_client_secret"
        ```
        """)

# Footer
st.markdown("---")
campus_name = st.session_state.get('selected_campus', 'Ninguno')
days = st.session_state.get('days_back', days_back)
st.markdown(
    f"💡 **42 Network Dashboard** | "
    f"Campus: {campus_name} | "
    f"Período: {days} día(s) | "
    f"🔄 Auto-actualizar: {'✅' if auto_refresh else '❌'}"
)
