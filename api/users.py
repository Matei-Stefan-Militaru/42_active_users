# api/users.py

import streamlit as st
import requests
import time
from datetime import datetime, timedelta, timezone
from config.settings import API_BASE_URL, DEFAULT_RETRY_AFTER, DEFAULT_PAGE_SIZE, DETAIL_LIMIT

def get_user_details(user_id, headers):
    """Obtener detalles completos de un usuario incluyendo cursus"""
    try:
        url = f"{API_BASE_URL}/v2/users/{user_id}?filter[cursus]=on"
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
        retry_after = int(response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
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
        f"{API_BASE_URL}/v2/users?filter[campus_id]={campus_id}&range[updated_at]={date_filter_start},{date_filter_end}&sort=-updated_at",
        
        # Método 2: Filtrar por created_at para usuarios nuevos
        f"{API_BASE_URL}/v2/users?filter[campus_id]={campus_id}&range[created_at]={date_filter_start},{date_filter_end}&sort=-created_at",
        
        # Método 3: Campus específico con updated_at
        f"{API_BASE_URL}/v2/campus/{campus_id}/users?range[updated_at]={date_filter_start},{date_filter_end}&sort=-updated_at",
        
        # Método 4: Sin filtro de fecha pero ordenado por actividad
        f"{API_BASE_URL}/v2/campus/{campus_id}/users?sort=-updated_at",
        
        # Método 5: General sin filtros específicos
        f"{API_BASE_URL}/v2/users?filter[campus_id]={campus_id}&sort=-updated_at"
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
                url = f"{base_url}&page[size]={DEFAULT_PAGE_SIZE}&page[number]={page}"
                
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
                    if len(data) < DEFAULT_PAGE_SIZE:
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
    """Obtener usuarios actualmente en el campus usando el campo location"""
    users = []
    
    try:
        status_text.text("🔍 Buscando usuarios actualmente en el campus...")
        
        # Obtener usuarios del campus (método directo)
        campus_users_url = f"{API_BASE_URL}/v2/campus/{campus_id}/users?page[size]={DEFAULT_PAGE_SIZE}"
        
        response = requests.get(campus_users_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            campus_users = response.json()
            if campus_users:
                status_text.text(f"✅ Encontrados {len(campus_users)} usuarios del campus")
                
                # Filtrar usuarios que tienen location (están físicamente en el campus)
                active_users = []
                for user in campus_users:
                    user_location = user.get('location')
                    if user_location and user_location != "unavailable" and user_location.strip():
                        # El usuario está en una ubicación física
                        user['location_active'] = True
                        user['last_location'] = user.get('updated_at')  # Usar updated_at como referencia
                        active_users.append(user)
                        
                        if debug_mode:
                            st.write(f"👤 Usuario activo: {user.get('login', 'N/A')} en {user_location}")
                
                users = active_users
                
                if debug_mode:
                    st.success(f"✅ Encontrados {len(users)} usuarios activamente en campus de {len(campus_users)} totales")
                    if users:
                        locations = [u.get('location', 'N/A') for u in users]
                        unique_locations = list(set(locations))
                        st.write(f"📍 Ubicaciones activas: {', '.join(unique_locations[:10])}")  # Mostrar max 10
            else:
                if debug_mode:
                    st.info("📭 No se encontraron usuarios en este campus")
        else:
            if debug_mode:
                st.warning(f"⚠️ Error obteniendo usuarios del campus: {response.status_code}")
                st.write(f"URL: {campus_users_url}")
                
    except Exception as e:
        if debug_mode:
            st.error(f"❌ Error obteniendo usuarios del campus: {str(e)}")
    
    return users

def get_active_users(campus_id, headers, days_back=1, max_users=200, search_method="Solo ubicaciones activas", debug_mode=False):
    """Obtener usuarios activos usando solo ubicaciones activas para máxima velocidad"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Solo método de ubicaciones activas (más rápido)
        status_text.text("🔍 Buscando usuarios actualmente en el campus...")
        progress_bar.progress(0.2)
        
        location_users = get_users_by_locations(campus_id, headers, status_text, debug_mode)
        
        progress_bar.progress(0.6)
        status_text.text(f"✅ Encontrados {len(location_users)} usuarios en campus")
        
        # Limitar a max_users
        final_users = location_users[:max_users]
        
        # Obtener datos completos para usuarios seleccionados (solo los primeros 50 para velocidad)
        progress_bar.progress(0.8)
        status_text.text("🔍 Obteniendo datos completos...")
        
        enhanced_users = []
        detail_limit = min(50, len(final_users))  # Límite reducido para velocidad
        
        for i, user in enumerate(final_users):
            if i < detail_limit:
                detailed_user = get_user_details(user.get('id'), headers)
                if detailed_user:
                    # Preservar información de ubicación
                    detailed_user['location_active'] = True
                    detailed_user['last_location'] = user.get('last_location')
                    enhanced_users.append(detailed_user)
                else:
                    enhanced_users.append(user)
            else:
                # Para el resto, usar datos básicos (más rápido)
                user['location_active'] = True
                enhanced_users.append(user)
            
            # Actualizar progreso cada 10 usuarios
            if i % 10 == 0:
                progress = 0.8 + (i / len(final_users)) * 0.2
                progress_bar.progress(min(progress, 1.0))
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ Completado: {len(enhanced_users)} usuarios activos en campus")
        time.sleep(1)
        
        return enhanced_users
        
    finally:
        progress_bar.empty()
        status_text.empty()
