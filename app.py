import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
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

# Función para obtener campus con paginación mejorada
@st.cache_data(ttl=3600)
def get_campus(headers, debug_mode=False):
    """Obtener lista completa de campus con paginación"""
    all_campus = []
    page = 1
    max_pages = 20  # Límite de seguridad
    
    try:
        while page <= max_pages:
            # Usar paginación para obtener todos los campus
            url = f"https://api.intra.42.fr/v2/campus?page[size]=100&page[number]={page}"
            
            if debug_mode:
                st.write(f"🔍 Obteniendo campus - Página {page}: {url}")
            
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                data = res.json()
                
                if not data:  # No hay más datos
                    break
                
                all_campus.extend(data)
                
                if debug_mode:
                    st.write(f"✅ Página {page}: {len(data)} campus encontrados")
                
                # Si obtenemos menos de 100, probablemente es la última página
                if len(data) < 100:
                    break
                    
                page += 1
            else:
                if debug_mode:
                    st.error(f"❌ Error en página {page}: {res.status_code}")
                break
        
        if debug_mode:
            st.success(f"✅ Total campus obtenidos: {len(all_campus)}")
            
            # Mostrar campus por país para debug
            campus_by_country_debug = {}
            for campus in all_campus:
                country = campus.get("country", "Sin País")
                if country not in campus_by_country_debug:
                    campus_by_country_debug[country] = []
                campus_by_country_debug[country].append(campus.get("name", "Sin nombre"))
            
            st.write("📍 Campus por país encontrados:")
            for country, campus_names in sorted(campus_by_country_debug.items()):
                st.write(f"**{country}:** {len(campus_names)} campus")
                if country == "Spain":  # Mostrar detalles de España
                    for name in sorted(campus_names):
                        st.write(f"  - {name}")
        
        return all_campus
        
    except Exception as e:
        st.error(f"❌ Error obteniendo campus: {str(e)}")
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
        return None

def handle_rate_limit(response, status_text, debug_mode=False):
    """Manejar rate limiting de la API"""
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 2))
        if debug_mode:
            st.warning(f"⏳ Rate limit alcanzado - esperando {retry_after}s...")
        status_text.text(f"⏳ Rate limit - esperando {retry_after}s...")
        time.sleep(retry_after)
        return True
    return False

def get_users_by_activity(campus_id, headers, days_back, max_users, status_text, progress_bar, debug_mode=False):
    """Obtener usuarios con actividad reciente usando múltiples endpoints"""
    users = []
    
    # Calcular fechas correctamente
    now = datetime.now(timezone.utc)
    past_date = now - timedelta(days=days_back)
    
    # Formatear fechas para la API (ISO 8601)
    date_filter_start = past_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_filter_end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    if debug_mode:
        st.info(f"🔍 Buscando actividad entre: {date_filter_start} y {date_filter_end}")
    
    status_text.text(f"🔍 Buscando usuarios con actividad reciente ({days_back} días)...")
    
    # Endpoints a probar con diferentes estrategias
    endpoints_to_try = [
        # Método 1: Filtrar por updated_at (actividad general)
        f"https://api.intra.42.fr/v2/users?filter[campus_id]={campus_id}&range[updated_at]={date_filter_start},{date_filter_end}&sort=-updated_at",
        
        # Método 2: Filtrar por created_at para usuarios nuevos
        f"https://api.intra.42.fr/v2/users?filter[campus_id]={campus_id}&range[created_at]={date_filter_start},{date_filter_end}&sort=-created_at",
        
        # Método 3: Campus específico con updated_at
        f"https://api.intra.42.fr/v2/campus/{campus_id}/users?range[updated_at]={date_filter_start},{date_filter_end}&sort=-updated_at",
        
        # Método 4: Sin filtro de fecha pero ordenado por actividad
        f"https://api.intra.42.fr/v2/campus/{campus_id}/users?sort=-updated_at",
        
        # Método 5: General sin filtros específicos
        f"https://api.intra.42.fr/v2/users?filter[campus_id]={campus_id}&sort=-updated_at"
    ]
    
    for method_idx, base_url in enumerate(endpoints_to_try):
        if len(users) >= max_users:
            break
            
        status_text.text(f"🔍 Método {method_idx + 1}/{len(endpoints_to_try)}: Probando endpoint...")
        
        page = 1
        max_pages = min(10, (max_users // 100) + 1)
        method_users = []
        
        while page <= max_pages and len(method_users) < max_users:
            try:
                # Construir URL con paginación
                url = f"{base_url}&page[size]=100&page[number]={page}"
                
                if debug_mode:
                    st.code(f"URL: {url}")
                
                response = requests.get(url, headers=headers, timeout=20)
                
                # Manejar rate limiting
                if handle_rate_limit(response, status_text, debug_mode):
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data:
                        if debug_mode:
                            st.info(f"📭 Método {method_idx + 1}, página {page}: Sin datos")
                        break
                    
                    # Filtrar usuarios por fecha manualmente si la API no lo hizo
                    filtered_users = []
                    for user in data:
                        # Verificar fecha de actividad
                        user_updated = user.get('updated_at')
                        user_created = user.get('created_at')
                        
                        # Parsear fechas
                        activity_date = None
                        for date_str in [user_updated, user_created]:
                            if date_str:
                                try:
                                    activity_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                    break
                                except:
                                    continue
                        
                        # Verificar si está en el rango de fechas
                        if activity_date and activity_date >= past_date:
                            # Verificar que pertenece al campus correcto
                            user_campus = user.get('campus', [])
                            campus_match = False
                            
                            if isinstance(user_campus, list):
                                campus_ids = [c.get('id') for c in user_campus if c]
                                campus_match = campus_id in campus_ids
                            elif isinstance(user_campus, dict):
                                campus_match = user_campus.get('id') == campus_id
                            
                            if campus_match:
                                user['location_active'] = False
                                user['activity_date'] = activity_date
                                filtered_users.append(user)
                    
                    method_users.extend(filtered_users)
                    
                    if debug_mode:
                        st.info(f"✅ Método {method_idx + 1}, página {page}: {len(filtered_users)} usuarios válidos de {len(data)} totales")
                    
                    # Si no hay más datos, parar
                    if len(data) < 100:
                        break
                        
                    page += 1
                    
                    # Actualizar progreso
                    progress = 0.1 + (method_idx / len(endpoints_to_try)) * 0.6 + (page / max_pages) * 0.1
                    progress_bar.progress(min(progress, 0.7))
                    
                elif response.status_code == 403:
                    if debug_mode:
                        st.warning(f"⚠️ Método {method_idx + 1}: Sin permisos para este endpoint")
                    break
                else:
                    if debug_mode:
                        st.warning(f"⚠️ Método {method_idx + 1}, página {page}: Error {response.status_code}")
                    break
                    
            except Exception as e:
                if debug_mode:
                    st.error(f"❌ Error en método {method_idx + 1}, página {page}: {str(e)}")
                break
        
        # Agregar usuarios únicos de este método
        for user in method_users:
            user_id = user.get('id')
            # Evitar duplicados
            if user_id and not any(u.get('id') == user_id for u in users):
                users.append(user)
        
        status_text.text(f"✅ Método {method_idx + 1}: {len(method_users)} usuarios encontrados (Total: {len(users)})")
        
        if len(users) >= max_users:
            break
    
    return users[:max_users]

def get_users_by_locations(campus_id, headers, status_text, debug_mode=False):
    """Obtener usuarios actualmente en el campus usando locations"""
    users = []
    
    try:
        status_text.text("🔍 Buscando usuarios actualmente en el campus...")
        locations_url = f"https://api.intra.42.fr/v2/campus/{campus_id}/locations?page[size]=100&filter[active]=true"
        
        response = requests.get(locations_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            locations = response.json()
            if locations:
                status_text.text(f"✅ Encontradas {len(locations)} ubicaciones activas")
                
                for location in locations:
                    if location.get('user') and location.get('end_at') is None:
                        user_data = location['user']
                        user_data['last_location'] = location.get('begin_at')
                        user_data['location_active'] = True
                        users.append(user_data)
                
                if debug_mode:
                    st.success(f"✅ Encontrados {len(users)} usuarios en ubicaciones activas")
            else:
                if debug_mode:
                    st.info("📭 No hay ubicaciones activas en este momento")
        else:
            if debug_mode:
                st.warning(f"⚠️ Error obteniendo locations: {response.status_code}")
                
    except Exception as e:
        if debug_mode:
            st.error(f"❌ Error obteniendo locations: {str(e)}")
    
    return users

# Función principal mejorada para obtener usuarios activos
def get_active_users(campus_id, headers, days_back=1, max_users=100, search_method="Híbrido", debug_mode=False):
    """Obtener usuarios activos usando múltiples enfoques mejorados"""
    all_users = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Método 1: Usuarios actualmente en el campus (solo si está habilitado)
        if search_method in ["Híbrido", "Solo ubicaciones activas"]:
            location_users = get_users_by_locations(campus_id, headers, status_text, debug_mode)
            
            for user in location_users:
                user_id = user.get('id')
                if user_id:
                    all_users[user_id] = user
            
            progress_bar.progress(0.3)
            status_text.text(f"✅ Usuarios en campus: {len(location_users)}")
        
        # Método 2: Usuarios con actividad reciente (solo si está habilitado)
        if search_method in ["Híbrido", "Solo actividad reciente"]:
            activity_users = get_users_by_activity(
                campus_id, headers, days_back, max_users, 
                status_text, progress_bar, debug_mode
            )
            
            for user in activity_users:
                user_id = user.get('id')
                if user_id and user_id not in all_users:
                    all_users[user_id] = user
            
            progress_bar.progress(0.7)
            status_text.text(f"✅ Usuarios con actividad reciente: {len(activity_users)}")
        
        final_users = list(all_users.values())[:max_users]
        
        # Obtener datos completos para usuarios seleccionados
        progress_bar.progress(0.8)
        status_text.text("🔍 Obteniendo datos completos de usuarios...")
        
        enhanced_users = []
        detail_limit = min(50, len(final_users))  # Límite para evitar sobrecarga
        
        for i, user in enumerate(final_users):
            if i < detail_limit:
                detailed_user = get_user_details(user.get('id'), headers)
                if detailed_user:
                    # Preservar información de ubicación si existe
                    if user.get('location_active'):
                        detailed_user['location_active'] = True
                        detailed_user['last_location'] = user.get('last_location')
                    enhanced_users.append(detailed_user)
                else:
                    enhanced_users.append(user)
            else:
                enhanced_users.append(user)
            
            # Actualizar progreso
            if i % 10 == 0:
                progress = 0.8 + (i / len(final_users)) * 0.2
                progress_bar.progress(min(progress, 1.0))
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ Completado: {len(enhanced_users)} usuarios procesados")
        time.sleep(1)  # Mostrar el mensaje final brevemente
        
        return enhanced_users
        
    finally:
        progress_bar.empty()
        status_text.empty()

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
    
    st.markdown("---")
    
    # Obtener credenciales
    credentials = st.secrets.get("api42", {})
    client_id = credentials.get("client_id")
    client_secret = credentials.get("client_secret")

    if not client_id or not client_secret:
        st.error("❌ Faltan credenciales en los secrets. Verifica que estén correctamente configuradas en [api42].")
        st.stop()
    
    # Obtener token para cargar campus
    token = get_auth_token(client_id, client_secret)
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Obtener debug_mode del estado si existe
        debug_mode_for_campus = st.session_state.get('debug_mode_campus', False)
        
        campus_list = get_campus(headers, debug_mode_for_campus)
        
        if campus_list:
            # Crear diccionarios organizados por país
            campus_by_country = {}
            for campus in campus_list:
                country = campus.get("country", "Sin País")
                if country not in campus_by_country:
                    campus_by_country[country] = []
                campus_by_country[country].append(campus)
            
            # Filtros de ubicación
            st.markdown("## 🌍 Selección de Campus")
            
            # Filtro por país
            countries = sorted(campus_by_country.keys())
            selected_country = st.selectbox(
                "🌎 País",
                ["Todos"] + countries,
                index=0
            )
            
            # Filtro por campus basado en el país seleccionado
            if selected_country == "Todos":
                available_campus = campus_list
            else:
                available_campus = campus_by_country[selected_country]
            
            campus_dict = {campus["name"]: campus["id"] for campus in available_campus}
            
            selected_campus = st.selectbox(
                "🏫 Campus",
                list(campus_dict.keys()),
                index=0 if campus_dict else 0
            )
            
            # Mostrar información del campus seleccionado
            if selected_campus:
                campus_id = campus_dict[selected_campus]
                selected_campus_data = next((c for c in available_campus if c["name"] == selected_campus), None)
                
                if selected_campus_data:
                    st.markdown("### 📍 Campus Seleccionado")
                    st.markdown(f"**🏫 Nombre:** {selected_campus}")
                    st.markdown(f"**🌎 País:** {selected_campus_data.get('country', 'N/A')}")
                    st.markdown(f"**🆔 ID:** {campus_id}")
                    if selected_campus_data.get('city'):
                        st.markdown(f"**🏙️ Ciudad:** {selected_campus_data.get('city')}")
                    st.markdown('<div class="status-success">✅ Conectado</div>', unsafe_allow_html=True)
        else:
            st.error("❌ No se pudieron cargar los campus")
            st.stop()
    else:
        st.error("❌ Error de autenticación")
        st.stop()
    
    st.markdown("---")
    
    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-actualizar (60s)", value=False)
    refresh_button = st.button("🔍 Ver usuarios activos", type="primary", use_container_width=True)
    
    st.markdown("---")
    
    # Configuración avanzada
    with st.expander("⚙️ Opciones Avanzadas"):
        days_back = st.slider("Días hacia atrás", 1, 30, 7)
        max_users = st.slider("Máximo de usuarios", 20, 500, 200)
        show_raw_data = st.checkbox("Mostrar datos raw")
        show_charts = st.checkbox("Mostrar gráficos", value=True)
        debug_mode = st.checkbox("Modo debug", value=False)
        
        # Nueva opción para método de búsqueda
        search_method = st.selectbox(
            "Método de búsqueda",
            ["Híbrido", "Solo actividad reciente", "Solo ubicaciones activas"],
            help="Híbrido: combina ambos métodos para mejores resultados"
        )
    
    # Información adicional sobre el país/campus
    if selected_country != "Todos":
        with st.expander(f"🌍 Información de {selected_country}"):
            country_campus = campus_by_country[selected_country]
            st.markdown(f"**Total de campus:** {len(country_campus)}")
            st.markdown("**Campus disponibles:**")
            for campus in country_campus:
                emoji = "📍" if campus["name"] == selected_campus else "🏫"
                st.markdown(f"- {emoji} {campus['name']}")
                if campus.get('city'):
                    st.markdown(f"  📍 {campus['city']}")
    
    # Estadísticas globales
    if campus_list:
        with st.expander("📊 Estadísticas Globales"):
            total_campus = len(campus_list)
            total_countries = len(campus_by_country)
            st.metric("🌍 Total Países", total_countries)
            st.metric("🏫 Total Campus", total_campus)
            
            # Top 5 países con más campus
            country_counts = {country: len(campuses) for country, campuses in campus_by_country.items()}
            top_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            st.markdown("**🏆 Top 5 Países:**")
            for country, count in top_countries:
                st.markdown(f"- {country}: {count} campus")

# Auto-refresh logic
if auto_refresh:
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    if time.time() - st.session_state.last_refresh > 60:
        st.session_state.last_refresh = time.time()
        st.rerun()

# Verificar que se haya seleccionado un campus válido
if not selected_campus or not campus_id:
    st.error("❌ Selecciona un campus válido en la barra lateral")
    st.stop()

# Trigger para cargar datos
if refresh_button or (auto_refresh and 'users_data' not in st.session_state):
    with st.spinner(f"🔍 Cargando usuarios activos de {selected_campus}..."):
        users = get_active_users(campus_id, headers, days_back, max_users, search_method, debug_mode)
        
        if not users:
            st.info(f"📝 No se encontraron usuarios activos en {selected_campus} en los últimos {days_back} día(s).")
            st.session_state.users_data = pd.DataFrame()
        else:
            # Procesar datos mejorado
            df_data = []
            for user in users:
                try:
                    # Determinar la fecha de última actividad con prioridad
                    last_activity = None
                    activity_sources = [
                        user.get("last_location"),  # Ubicación más reciente
                        user.get("updated_at"),     # Última actualización
                        user.get("created_at")      # Creación (fallback)
                    ]
                    
                    for activity_time in activity_sources:
                        if activity_time:
                            try:
                                if isinstance(activity_time, str):
                                    # Manejar diferentes formatos de fecha
                                    if activity_time.endswith('Z'):
                                        last_activity = activity_time
                                    else:
                                        last_activity = activity_time
                                    break
                            except:
                                continue
                    
                    user_info = {
                        "ID": user.get("id", 0),
                        "Login": user.get("login", "N/A"),
                        "Nombre": user.get("displayname", user.get("first_name", "") + " " + user.get("last_name", "")).strip(),
                        "Correo": user.get("email", "N/A"),
                        "Última conexión": last_activity,
                        "Estado": "🟢 En campus" if user.get("location_active", False) else "🔵 Activo recientemente",
                        "Nivel": 0.0,
                        "Campus": "N/A",
                        "Wallet": user.get("wallet", 0),
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
                    continue
            
            df = pd.DataFrame(df_data)
            
            # Procesar timestamps con mejor manejo de errores
            if not df.empty:
                # Función para parsear fechas de manera robusta
                def parse_date(date_str):
                    if pd.isna(date_str) or date_str in [None, "", "N/A"]:
                        return pd.NaT
                    
                    try:
                        # Intentar parsear como ISO format
                        if isinstance(date_str, str):
                            if date_str.endswith('Z'):
                                return pd.to_datetime(date_str, utc=True).tz_localize(None)
                            else:
                                return pd.to_datetime(date_str, utc=True).tz_localize(None)
                        return pd.to_datetime(date_str, utc=True).tz_localize(None)
                    except:
                        return pd.NaT
                
                df["Última conexión"] = df["Última conexión"].apply(parse_date)
                
                # Filtrar usuarios con fechas válidas
                df = df.dropna(subset=["Última conexión"])
                
                # Filtrar por rango de fechas especificado
                if len(df) > 0:
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    past_date = now - timedelta(days=days_back)
                    
                    # Filtrar usuarios dentro del rango
                    date_mask = df["Última conexión"] >= past_date
                    df = df[date_mask]
                
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
            st.session_state.search_method = search_method
            
            if len(df) > 0:
                st.success(f"✅ Usuarios activos en {selected_campus} (últimos {days_back} día(s)): **{len(df)}**")
            else:
                st.warning(f"⚠️ No se encontraron usuarios con actividad en {selected_campus} en los últimos {days_back} día(s). Prueba aumentar el rango de días o cambiar el método de búsqueda.")

# Mostrar datos si están disponibles
if 'users_data' in st.session_state and not st.session_state.users_data.empty:
    df = st.session_state.users_data
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Usuarios Activos", len(df))
    
    with col2:
        unique_users = df['Login'].nunique()
        st.metric("👤 Usuarios Únicos", unique_users)
    
    with col3:
        avg_level = df['Nivel'].mean()
        st.metric("📊 Nivel Promedio", f"{avg_level:.1f}")
    
    with col4:
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
        if 'Wallet' in df.columns and not df['Wallet'].isna().all():
            avg_wallet = df['Wallet'].mean()
            st.metric("💰 Wallet Promedio", f"{avg_wallet:.0f}")
        else:
            st.metric("💰 Wallet Promedio", "N/A")
    
    # Información temporal mejorada
    if not df.empty:
        fecha_min = df['Última conexión'].min().strftime("%d/%m/%Y %H:%M")
        fecha_max = df['Última conexión'].max().strftime("%d/%m/%Y %H:%M")
        search_method_used = st.session_state.get('search_method', 'N/A')
        country_info = f" | **País:** {selected_country}" if selected_country != "Todos" else ""
        st.info(f"📅 **Período de actividad:** {fecha_min} → {fecha_max} | **Campus:** {st.session_state.get('selected_campus', 'N/A')}{country_info} | **Método:** {search_method_used}")
    
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
        
        # Actividad por día
        if days_back > 1:
            st.markdown("## 📊 Actividad por Día")
            
            df_chart = df.copy()
            df_chart['fecha'] = df_chart['Última conexión'].dt.date
            daily_counts = df_chart['fecha'].value_counts().sort_index()
            
            if not daily_counts.empty:
                chart_daily = px.line(
                    x=daily_counts.index, 
                    y=daily_counts.values,
                    labels={"x": "Fecha", "y": "Usuarios Activos"},
                    title=f"Tendencia de Actividad - Últimos {days_back} días"
                )
                
                chart_daily.update_traces(line_color='rgba(102, 126, 234, 0.8)', line_width=3)
                chart_daily.update_layout(
                    height=300,
                    showlegend=False,
                    plot_bgcolor='white'
                )
                
                st.plotly_chart(chart_daily, use_container_width=True)
        
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
                
                # Asegurar que tenemos las columnas necesarias
                base_columns = ['Login', 'Nombre', 'Nivel']
                available_columns = [col for col in base_columns if col in df.columns]
                
                if 'Wallet' in df.columns:
                    available_columns.append('Wallet')
                
                # Obtener top usuarios (máximo 10 o los que haya)
                num_users = min(10, len(df))
                top_users = df.nlargest(num_users, 'Nivel')[available_columns]
                
                if not top_users.empty:
                    # Formatear la tabla
                    display_top = top_users.copy()
                    display_top['Nivel'] = display_top['Nivel'].apply(lambda x: f"{x:.1f}")
                    
                    if 'Wallet' in display_top.columns:
                        display_top['Wallet'] = display_top['Wallet'].apply(lambda x: f"{x:.0f}")
                    
                    # Limitar el ancho de las columnas de texto
                    if 'Nombre' in display_top.columns:
                        display_top['Nombre'] = display_top['Nombre'].apply(
                            lambda x: x[:20] + "..." if len(str(x)) > 20 else str(x)
                        )
                    
                    st.dataframe(
                        display_top, 
                        use_container_width=True, 
                        hide_index=True,
                        height=min(350, (len(display_top) + 1) * 35)  # Altura dinámica
                    )
                else:
                    st.info("No hay usuarios con niveles para mostrar")
    
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
        
        **Funcionalidades principales:**
        - ✅ **Filtrado por país y campus:** Navega fácilmente por toda la red 42
        - ✅ **Múltiples métodos de búsqueda:** Híbrido, actividad reciente, ubicaciones activas
        - ✅ **Análisis temporal:** Distribución de actividad por hora y día
        - ✅ **Rankings y métricas:** Top usuarios, niveles, wallet y puntos
        - ✅ **Interfaz optimizada:** Filtros intuitivos y visualizaciones claras
        
        **Métodos de búsqueda:**
        - **Híbrido:** Combina usuarios en campus + actividad reciente (recomendado)
        - **Solo actividad reciente:** Busca usuarios con actividad en el período especificado
        - **Solo ubicaciones activas:** Solo usuarios actualmente en el campus
        
        **Configuración de credenciales:**
        ```toml
        [api42]
        client_id = "tu_client_id"
        client_secret = "tu_client_secret"
        ```
        
        **Solución de problemas:**
        - Si no aparecen usuarios, prueba aumentar el rango de días
        - Activa el modo debug para ver información detallada del proceso
        - Prueba diferentes métodos de búsqueda si uno no funciona bien
        """)

# Footer mejorado
st.markdown("---")
campus_name = st.session_state.get('selected_campus', 'Ninguno')
days = st.session_state.get('days_back', days_back)
method = st.session_state.get('search_method', search_method)
country_name = selected_country if 'selected_country' in locals() else 'N/A'
st.markdown(
    f"💡 **42 Network Dashboard v2.3** | "
    f"País: {country_name} | "
    f"Campus: {campus_name} | "
    f"Período: {days} día(s) | "
    f"Método: {method} | "
    f"🔄 Auto-actualizar: {'✅' if auto_refresh else '❌'} | "
    f"🐛 Debug: {'✅' if debug_mode else '❌'}"
)
