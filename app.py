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
    page_title="42 Network - Finding Your Evaluator",
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

st.markdown('<h1 class="main-header">🚀 42 Network - Finding Your Evaluator</h1>', unsafe_allow_html=True)

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
    # Menú de navegación principal
    st.markdown("## 🚀 42 Network Apps")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎫 Tickets", use_container_width=True, help="Gestión de tickets de la red 42"):
            st.components.v1.html(
                '<script>window.open("https://42activeusers-tickets.streamlit.app/", "_blank");</script>',
                height=0
            )
        
        if st.button("🏆 Ranking Países", use_container_width=True, help="Ranking de países (próximamente)", disabled=True):
            st.info("🚧 Próximamente disponible")
    
    with col2:
        if st.button("📊 42Stats", use_container_width=True, help="Estadísticas generales de 42"):
            st.components.v1.html(
                '<script>window.open("https://42stats.streamlit.app/", "_blank");</script>',
                height=0
            )
    
    st.markdown("---")
    
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
        
        # Debug específico para campus
        debug_mode_campus = st.checkbox("Debug campus", value=False, help="Muestra información detallada sobre la carga de campus")
        st.session_state.debug_mode_campus = debug_mode_campus
        
        # Nueva opción para método de búsqueda
        search_method = st.selectbox(
            "Método de búsqueda",
            ["Híbrido", "Solo actividad reciente", "Solo ubicaciones activas"],
            help="Híbrido: combina ambos métodos para mejores resultados"
        )
        
        # Botón para recargar campus
        if st.button("🔄 Recargar Campus", help="Fuerza la recarga de la lista de campus"):
            st.cache_data.clear()
            st.rerun()
    
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
