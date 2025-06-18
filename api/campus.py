# api/campus.py

import streamlit as st
import requests
from config.settings import API_BASE_URL, DEFAULT_MAX_PAGES, DEFAULT_PAGE_SIZE

@st.cache_data(ttl=3600)
def get_campus(headers, debug_mode=False):
    """Obtener lista completa de campus con paginación"""
    all_campus = []
    page = 1
    max_pages = DEFAULT_MAX_PAGES
    
    try:
        while page <= max_pages:
            url = f"{API_BASE_URL}/v2/campus?page[size]={DEFAULT_PAGE_SIZE}&page[number]={page}"
            
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
                if len(data) < DEFAULT_PAGE_SIZE:
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
