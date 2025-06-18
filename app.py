import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json

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
        max_users = st.slider("Máximo de usuarios", 20, 200, 100)
        show_raw_data = st.checkbox("Mostrar datos raw")
        show_charts = st.checkbox("Mostrar gráficos", value=True)
        debug_mode = st.checkbox("Modo debug", value=False)

# Obtener credenciales
credentials = st.secrets.get("api42", {})
client_id = credentials.get("client_id")
client_secret = credentials.get("client_secret")

if not client_id or not client_secret:
    st.error("❌ Faltan credenciales en los secrets. Verifica que estén correctamente configuradas en [api42].")
    st.stop()

# Función de autenticación
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

# Función para obtener campus
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

# Función para obtener datos completos de un usuario
def get_user_details(user_id, headers):
    """Obtener detalles completos de un usuario incluyendo cursus"""
    try:
        url = f"https://api.intra.42.fr/v2/users/{user_id}?filter[cursus]=on"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        if debug_mode:
            st.warning(f"Error obteniendo detalles de usuario {user_id}: {str(e)}")
        return None

# Función para obtener usuarios activos
def get_active_users(campus_id, headers, days_back=1, max_users=100):
    """Obtener usuarios activos usando múltiples enfoques"""
    users = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Método 1: Intentar con locations (usuarios actualmente en el campus)
    try:
        status_text.text("🔍 Buscando usuarios actualmente en el campus...")
        locations_url = f"https://api.intra.42.fr/v2/campus/{campus_id}/locations?page[size]=100&filter[active]=true"
        
        res = requests.get(locations_url, headers=headers, timeout=20)
        if res.status_code == 200:
            locations = res.json()
            if locations:
                status_text.text(f"✅ Encontradas {len(locations)} ubicaciones activas")
                # Extraer usuarios de las ubicaciones activas
                location_users = []
                for i, location in enumerate(locations):
                    if location.get('user') and location.get('end_at') is None:
                        user_data = location['user']
                        user_data['last_location'] = location.get('begin_at')
                        user_data['location_active'] = True
                        location_users.append(user_data)
                    
                    # Actualizar progreso
                    if i % 10 == 0:
                        progress_bar.progress(0.3 * (i / len(locations)))
                
                if location_users:
                    users.extend(location_users)
                    status_text.text(f"✅ Encontrados {len(location_users)} usuarios en ubicaciones activas")
                    
    except Exception as e:
        st.warning(f"⚠️ Error obteniendo locations: {str(e)}")
    
    progress_bar.progress(0.4)
    
    # Método 2: Buscar usuarios con actividad reciente
    status_text.text("🔍 Buscando usuarios con actividad reciente...")
    page = 1
    now = datetime.now(datetime.UTC)  # Fixed deprecated datetime.utcnow()
    past_date = now - timedelta(days=days_back)
    date_filter = past_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    max_pages = min(10, max_users // 100 + 1)
    recent_users = []
    
    while page <= max_pages and len(recent_users) < max_users:
        try:
            status_text.text(f"Cargando página {page} de usuarios recientes...")
            
            # Usar diferentes endpoints según disponibilidad
            urls_to_try = [
                f"https://api.intra.42.fr/v2/campus/{campus_id}/users?page[size]=100&page[number]={page}&sort=-updated_at&filter[updated_at]={date_filter},",
                f"https://api.intra.42.fr/v2/campus/{campus_id}/users?page[size]=100&page[number]={page}&sort=-updated_at",
                f"https://api.intra.42.fr/v2/users?page[size]=100&page[number]={page}&sort=-updated_at&filter[campus_id]={campus_id}"
            ]
            
            success = False
            for url in urls_to_try:
                try:
                    res = requests.get(url, headers=headers, timeout=20)
                    
                    if res.status_code == 200:
                        data = res.json()
                        if data:
                            # Filtrar por campus si es necesario
                            filtered_data = []
                            for user in data:
                                user_campus = user.get('campus', [])
                                if isinstance(user_campus, list):
                                    campus_ids = [c.get('id') for c in user_campus]
                                    if campus_id in campus_ids:
                                        user['location_active'] = False
                                        filtered_data.append(user)
                                elif isinstance(user_campus, dict) and user_campus.get('id') == campus_id:
                                    user['location_active'] = False
                                    filtered_data.append(user)
                            
                            recent_users.extend(filtered_data)
                            success = True
                            break
                            
                    elif res.status_code == 429:
                        retry_after = int(res.headers.get('Retry-After', 2))
                        status_text.text(f"⏳ Rate limit - esperando {retry_after}s...")
                        time.sleep(retry_after)
                        
                except Exception as e:
                    if debug_mode:
                        st.warning(f"Error con URL {url}: {str(e)}")
                    continue
            
            if not success:
                break
                
            page += 1
            
            # Actualizar progreso
            progress = 0.4 + (page / max_pages) * 0.4
            progress_bar.progress(min(progress, 0.8))
            
        except Exception as e:
            st.error(f"❌ Error en página {page}: {str(e)}")
            break
    
    # Combinar usuarios únicos
    all_users = {}
    
    # Agregar usuarios de locations (prioridad)
    for user in users:
        user_id = user.get('id')
        if user_id:
            all_users[user_id] = user
    
    # Agregar usuarios recientes
    for user in recent_users:
        user_id = user.get('id')
        if user_id and user_id not in all_users:
            all_users[user_id] = user
    
    final_users = list(all_users.values())[:max_users]
    
    progress_bar.progress(0.9)
    status_text.text("🔍 Obteniendo datos completos de usuarios...")
    
    # Obtener datos completos para algunos usuarios (especialmente para niveles)
    enhanced_users = []
    for i, user in enumerate(final_users):
        if i < min(20, len(final_users)):  # Solo para los primeros 20 para no sobrecargar
            detailed_user = get_user_details(user.get('id'), headers)
            if detailed_user:
                enhanced_users.append(detailed_user)
            else:
                enhanced_users.append(user)
        else:
            enhanced_users.append(user)
        
        # Actualizar progreso
        if i % 5 == 0:
            progress = 0.9 + (i / len(final_users)) * 0.1
            progress_bar.progress(min(progress, 1.0))
    
    progress_bar.empty()
    status_text.empty()
    
    return enhanced_users

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
        users = get_active_users(campus_id, headers, days_back, max_users)
        
        if not users:
            st.info(f"📝 No se encontraron usuarios activos en {selected_campus} en los últimos {days_back} día(s).")
            st.session_state.users_data = pd.DataFrame()
        else:
            # Procesar datos mejorado
            df_data = []
            for user in users:
                try:
                    # Determinar la fecha de última actividad
                    last_activity = user.get("last_location") or user.get("updated_at") or user.get("created_at")
                    
                    user_info = {
                        "ID": user.get("id", 0),
                        "Login": user.get("login", "N/A"),
                        "Nombre": user.get("displayname", user.get("first_name", "") + " " + user.get("last_name", "")).strip(),
                        "Correo": user.get("email", "N/A"),
                        "Última conexión": last_activity,
                        "Estado": "🟢 En campus" if user.get("location_active", False) else "🔵 Activo recientemente",
                        "Nivel": 0.0,
                        "Campus": "N/A",
                        "Wallet": user.get("wallet", 0),  # This might be None or missing
                        "Evaluation Points": user.get("correction_point", 0)
                    }
                    
                    # Obtener nivel del cursus de manera más robusta
                    cursus_users = user.get("cursus_users", [])
                    if cursus_users:
                        # Buscar 42cursus primero
                        for cursus in cursus_users:
                            cursus_info = cursus.get("cursus", {})
                            if cursus_info.get("name") == "42cursus" or cursus_info.get("slug") == "42cursus":
                                user_info["Nivel"] = round(cursus.get("level", 0), 2)
                                break
                        else:
                            # Si no hay 42cursus, tomar el nivel más alto
                            max_level = 0
                            for cursus in cursus_users:
                                level = cursus.get("level", 0)
                                if level > max_level:
                                    max_level = level
                            user_info["Nivel"] = round(max_level, 2)
                    
                    # Obtener campus
                    campus_info = user.get("campus", [])
                    if isinstance(campus_info, list) and campus_info:
                        user_info["Campus"] = campus_info[0].get("name", "N/A")
                    elif isinstance(campus_info, dict):
                        user_info["Campus"] = campus_info.get("name", "N/A")
                    
                    df_data.append(user_info)
                    
                except Exception as e:
                    if debug_mode:
                        st.warning(f"⚠️ Error procesando usuario {user.get('login', 'unknown')}: {str(e)}")
                    continue
            
            df = pd.DataFrame(df_data)
            
            # Procesar timestamps
            if not df.empty:
                df["Última conexión"] = pd.to_datetime(df["Última conexión"], errors='coerce').dt.tz_localize(None)
                
                # Filtrar usuarios con datos válidos
                df = df.dropna(subset=["Última conexión"])
                
                # Ordenar por última conexión
                df = df.sort_values("Última conexión", ascending=False)
                
                # Ensure numeric columns are properly handled
                df['Wallet'] = pd.to_numeric(df['Wallet'], errors='coerce').fillna(0)
                df['Evaluation Points'] = pd.to_numeric(df['Evaluation Points'], errors='coerce').fillna(0)
                df['Nivel'] = pd.to_numeric(df['Nivel'], errors='coerce').fillna(0.0)
            
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
    
    # Métricas adicionales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        users_in_campus = len(df[df['Estado'].str.contains('En campus')])
        st.metric("🟢 En Campus", users_in_campus)
    
    with col2:
        max_level = df['Nivel'].max()
        st.metric("🏆 Nivel Máximo", f"{max_level:.1f}")
    
    with col3:
        # Fixed: Check if Wallet column exists and has valid data
        if 'Wallet' in df.columns and not df['Wallet'].isna().all():
            avg_wallet = df['Wallet'].mean()
            st.metric("💰 Wallet Promedio", f"{avg_wallet:.0f}")
        else:
            st.metric("💰 Wallet Promedio", "N/A")
    
    # Información temporal
    if not df.empty:
        fecha_min = df['Última conexión'].min().strftime("%d/%m/%Y %H:%M")
        fecha_max = df['Última conexión'].max().strftime("%d/%m/%Y %H:%M")
        st.info(f"📅 **Período de actividad:** {fecha_min} → {fecha_max} | **Campus:** {st.session_state.get('selected_campus', 'N/A')}")
    
    # Gráficos (si están habilitados)
    if show_charts and len(df) > 0:
        # Actividad por hora del día
        st.markdown("## 📈 Actividad por Hora del Día")
        
        df_chart = df.copy()
        df_chart['hora'] = df_chart['Última conexión'].dt.hour
        counts = df_chart['hora'].value_counts().sort_index()
        
        if not counts.empty:
            chart = px.bar(
                x=counts.index, 
                y=counts.values, 
                labels={"x": "Hora del Día", "y": "Usuarios Activos"}, 
                title=f"Distribución de Actividad - {st.session_state.get('selected_campus', 'Campus')}"
            )
            
            chart.update_traces(marker_color='rgba(102, 126, 234, 0.8)')
            chart.update_layout(
                height=400,
                showlegend=False,
                xaxis=dict(tickmode='linear', tick0=0, dtick=1),
                plot_bgcolor='white'
            )
            
            st.plotly_chart(chart, use_container_width=True)
        
        # Distribución de niveles mejorada
        st.markdown("## 📊 Distribución de Niveles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Histograma de niveles
            if df['Nivel'].max() > 0:
                fig_hist = px.histogram(
                    df, 
                    x='Nivel', 
                    nbins=20,
                    title="Distribución de Niveles",
                    labels={"Nivel": "Nivel", "count": "Cantidad de Usuarios"}
                )
                fig_hist.update_layout(height=300)
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Top usuarios por nivel
            if len(df) > 0:
                st.markdown("### 🏆 Top 10 Usuarios por Nivel")
                # Select columns that exist in the dataframe
                columns_to_show = ['Login', 'Nombre', 'Nivel']
                if 'Wallet' in df.columns:
                    columns_to_show.append('Wallet')
                
                top_users = df.nlargest(10, 'Nivel')[columns_to_show]
                
                # Formatear la tabla
                display_top = top_users.copy()
                display_top['Nivel'] = display_top['Nivel'].apply(lambda x: f"{x:.1f}")
                if 'Wallet' in display_top.columns:
                    display_top['Wallet'] = display_top['Wallet'].apply(lambda x: f"{x:.0f}")
                
                st.dataframe(display_top, use_container_width=True, hide_index=True)
    
    # Tabla principal con filtros mejorados
    st.markdown("## 👥 Lista de Usuarios Activos")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        search_user = st.text_input("🔍 Buscar por login/nombre", placeholder="Escribe aquí...")
    with col2:
        min_level = st.number_input("📊 Nivel mínimo", min_value=0.0, max_value=50.0, value=0.0, step=0.1)
    with col3:
        status_filter = st.selectbox("📍 Estado", ["Todos", "🟢 En campus", "🔵 Activo recientemente"])
    
    # Aplicar filtros
    filtered_df = df.copy()
    
    if search_user:
        mask = (filtered_df['Login'].str.contains(search_user, case=False, na=False) |
                filtered_df['Nombre'].str.contains(search_user, case=False, na=False))
        filtered_df = filtered_df[mask]
    
    if min_level > 0:
        filtered_df = filtered_df[filtered_df['Nivel'] >= min_level]
    
    if status_filter != "Todos":
        filtered_df = filtered_df[filtered_df['Estado'] == status_filter]
    
    # Formatear para mostrar - only include columns that exist
    base_columns = ['Login', 'Nombre', 'Estado', 'Nivel', 'Última conexión']
    display_columns = base_columns.copy()
    
    # Add optional columns if they exist
    if 'Wallet' in filtered_df.columns:
        display_columns.insert(-1, 'Wallet')  # Insert before 'Última conexión'
    if 'Evaluation Points' in filtered_df.columns:
        display_columns.insert(-1, 'Evaluation Points')
    
    display_df = filtered_df[display_columns].copy()
    
    # Formatear fechas de manera segura
    def safe_format_date(date_val):
        try:
            if pd.isna(date_val):
                return "N/A"
            if isinstance(date_val, str):
                parsed_date = pd.to_datetime(date_val, utc=True).tz_localize(None)
                return parsed_date.strftime('%d/%m/%Y %H:%M')
            return date_val.strftime('%d/%m/%Y %H:%M')
        except:
            return str(date_val) if date_val else "N/A"
    
    display_df['Última conexión'] = display_df['Última conexión'].apply(safe_format_date)
    display_df['Nivel'] = display_df['Nivel'].apply(lambda x: f"{x:.1f}")
    
    # Format optional columns if they exist
    if 'Wallet' in display_df.columns:
        display_df['Wallet'] = display_df['Wallet'].apply(lambda x: f"{x:.0f}")
    if 'Evaluation Points' in display_df.columns:
        display_df['Evaluation Points'] = display_df['Evaluation Points'].apply(lambda x: f"{x:.0f}")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    st.info(f"📊 Mostrando {len(filtered_df)} de {len(df)} usuarios")
    
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
        - 💰 **Métricas:** Wallet, puntos de evaluación y más
        
        **Funcionalidades mejoradas:**
        - ✅ **Obtención de niveles:** Datos completos del cursus 42
        - ✅ **Filtros avanzados:** Por estado, nivel mínimo y búsqueda
        - ✅ **Métricas extendidas:** Wallet, puntos de evaluación
        - ✅ **Visualizaciones mejoradas:** Histogramas y distribuciones
        - ✅ **Modo debug:** Para diagnosticar problemas
        
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
    f"💡 **42 Network Dashboard v2.0** | "
    f"Campus: {campus_name} | "
    f"Período: {days} día(s) | "
    f"🔄 Auto-actualizar: {'✅' if auto_refresh else '❌'} | "
    f"🐛 Debug: {'✅' if debug_mode else '❌'}"
)
