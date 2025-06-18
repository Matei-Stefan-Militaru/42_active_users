# app.py

import streamlit as st
import pandas as pd
import time
import sys
import os
from datetime import datetime, timedelta, timezone

# Agregar el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Imports locales
    from config.settings import MAIN_CSS, APP_CONFIG, AUTO_REFRESH_INTERVAL
    from api.users import get_active_users
    from ui.sidebar import render_sidebar
    from ui.charts import render_charts
    from ui.user_table import render_metrics, render_user_table, render_raw_data, render_info_section, render_help_section
except ImportError as e:
    st.error(f"Error importando módulos: {e}")
    st.error("Asegúrate de que todos los archivos estén en las carpetas correctas y que existan los archivos __init__.py")
    st.stop()

# Configuración de página
st.set_page_config(**APP_CONFIG)

# CSS optimizado
st.markdown(MAIN_CSS, unsafe_allow_html=True)

# Header principal
st.markdown('<h1 class="main-header">🚀 42 Network - Finding Your Evaluator</h1>', unsafe_allow_html=True)

try:
    # Renderizar sidebar y obtener configuración
    sidebar_config = render_sidebar()
    
    # Extraer valores del sidebar
    headers = sidebar_config['headers']
    selected_campus = sidebar_config['selected_campus']
    selected_country = sidebar_config['selected_country']
    campus_id = sidebar_config['campus_id']
    auto_refresh = sidebar_config['auto_refresh']
    refresh_button = sidebar_config['refresh_button']
    days_back = sidebar_config['days_back']
    max_users = sidebar_config['max_users']
    show_raw_data = sidebar_config['show_raw_data']
    show_charts = sidebar_config['show_charts']
    debug_mode = sidebar_config['debug_mode']
    search_method = sidebar_config['search_method']
    
except Exception as e:
    st.error(f"Error en la configuración del sidebar: {e}")
    st.stop()

# Auto-refresh logic
if auto_refresh:
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    if time.time() - st.session_state.last_refresh > AUTO_REFRESH_INTERVAL:
        st.session_state.last_refresh = time.time()
        st.rerun()

# Verificar que se haya seleccionado un campus válido
if not selected_campus or not campus_id:
    st.error("❌ Selecciona un campus válido en la barra lateral")
    st.stop()

# Trigger para cargar datos
if refresh_button or (auto_refresh and 'users_data' not in st.session_state):
    with st.spinner(f"🔍 Cargando usuarios activos de {selected_campus}..."):
        try:
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
        
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            if debug_mode:
                st.exception(e)

# Mostrar datos si están disponibles
if 'users_data' in st.session_state and not st.session_state.users_data.empty:
    df = st.session_state.users_data
    
    try:
        # Renderizar métricas principales
        render_metrics(df)
        
        # Información temporal mejorada
        render_info_section(df, selected_country, st.session_state.get('selected_campus', 'N/A'), 
                           st.session_state.get('days_back', days_back), 
                           st.session_state.get('search_method', 'N/A'))
        
        # Gráficos (si están habilitados)
        if show_charts:
            render_charts(df, st.session_state.get('days_back', days_back), 
                         st.session_state.get('selected_campus', 'Campus'))
        
        # Tabla principal con filtros
        render_user_table(df)
        
        # Datos raw si están habilitados
        if show_raw_data:
            render_raw_data()
    
    except Exception as e:
        st.error(f"Error renderizando la interfaz: {e}")
        if debug_mode:
            st.exception(e)

else:
    # Estado inicial - mostrar ayuda
    render_help_section()

# Footer mejorado
st.markdown("---")
campus_name = st.session_state.get('selected_campus', 'Ninguno')
days = st.session_state.get('days_back', days_back if 'days_back' in locals() else 7)
method = st.session_state.get('search_method', search_method if 'search_method' in locals() else 'N/A')
country_name = selected_country if 'selected_country' in locals() and selected_country else 'N/A'
auto_refresh_status = auto_refresh if 'auto_refresh' in locals() else False
debug_status = debug_mode if 'debug_mode' in locals() else False

st.markdown(
    f"💡 **42 Network - Finding Your Evaluator v2.3** | "
    f"País: {country_name} | "
    f"Campus: {campus_name} | "
    f"Período: {days} día(s) | "
    f"Método: {method} | "
    f"🔄 Auto-actualizar: {'✅' if auto_refresh_status else '❌'} | "
    f"🐛 Debug: {'✅' if debug_status else '❌'}"
)
