# ui/sidebar.py

import streamlit as st
from api.auth import get_auth_token
from api.campus import get_campus
from config.settings import EXTERNAL_APPS, SEARCH_METHODS, DEFAULT_DAYS_BACK, DEFAULT_MAX_USERS

def render_sidebar():
    """Renderizar el sidebar completo"""
    with st.sidebar:
        # Menú de navegación principal
        st.markdown("## 🚀 42 Network Apps")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎫 Tickets", use_container_width=True, help="Gestión de tickets de la red 42"):
                st.components.v1.html(
                    f'<script>window.open("{EXTERNAL_APPS["tickets"]}", "_blank");</script>',
                    height=0
                )
            
            if st.button("🏆 Ranking Países", use_container_width=True, help="Ranking de países (próximamente)", disabled=True):
                st.info("🚧 Próximamente disponible")
        
        with col2:
            if st.button("📊 42Stats", use_container_width=True, help="Estadísticas generales de 42"):
                st.components.v1.html(
                    f'<script>window.open("{EXTERNAL_APPS["stats"]}", "_blank");</script>',
                    height=0
                )
        
        st.markdown("---")
        
        # Configuración avanzada
        with st.expander("⚙️ Opciones Avanzadas"):
            days_back = st.slider("Días hacia atrás", 1, 30, DEFAULT_DAYS_BACK)
            max_users = st.slider("Máximo de usuarios", 20, 500, DEFAULT_MAX_USERS)
            show_raw_data = st.checkbox("Mostrar datos raw")
            show_charts = st.checkbox("Mostrar gráficos", value=True)
            debug_mode = st.checkbox("Modo debug", value=False)
            
            # Debug específico para campus
            debug_mode_campus = st.checkbox("Debug campus", value=False, help="Muestra información detallada sobre la carga de campus")
            st.session_state.debug_mode_campus = debug_mode_campus
            
            # Nueva opción para método de búsqueda
            search_method = st.selectbox(
                "Método de búsqueda",
                SEARCH_METHODS,
                help="Híbrido: combina ambos métodos para mejores resultados"
            )
            
            # Botón para recargar campus
            if st.button("🔄 Recargar Campus", help="Fuerza la recarga de la lista de campus"):
                st.cache_data.clear()
                st.rerun()
        
        # Estadísticas globales
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
        if not token:
            st.error("❌ Error de autenticación")
            st.stop()
            
        headers = {"Authorization": f"Bearer {token}"}
        
        # Obtener debug_mode del estado si existe
        debug_mode_for_campus = st.session_state.get('debug_mode_campus', False)
        
        campus_list = get_campus(headers, debug_mode_for_campus)
        
        if not campus_list:
            st.error("❌ No se pudieron cargar los campus")
            st.stop()
            
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
        campus_id = None
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
        
        st.markdown("---")
        
        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto-actualizar (60s)", value=False)
        refresh_button = st.button("🔍 Ver usuarios activos", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # Configuración avanzada
        st.markdown("## ⚙️ Opciones Avanzadas")
        days_back = st.slider("Días hacia atrás", 1, 30, DEFAULT_DAYS_BACK)
        max_users = st.slider("Máximo de usuarios", 20, 500, DEFAULT_MAX_USERS)
        show_raw_data = st.checkbox("Mostrar datos raw")
        show_charts = st.checkbox("Mostrar gráficos", value=True)
        debug_mode = st.checkbox("Modo debug", value=False)
        
        # Debug específico para campus
        debug_mode_campus = st.checkbox("Debug campus", value=False, help="Muestra información detallada sobre la carga de campus")
        st.session_state.debug_mode_campus = debug_mode_campus
        
        # Nueva opción para método de búsqueda
        search_method = st.selectbox(
            "Método de búsqueda",
            SEARCH_METHODS,
            help="Híbrido: combina ambos métodos para mejores resultados"
        )
        
        # Botón para recargar campus
        if st.button("🔄 Recargar Campus", help="Fuerza la recarga de la lista de campus"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Estadísticas globales
        st.markdown("## 📊 Estadísticas Globales")
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
    
    # Retornar valores necesarios para el main
    return {
        'headers': headers,
        'selected_campus': selected_campus,
        'selected_country': selected_country,
        'campus_id': campus_id,
        'campus_by_country': campus_by_country,
        'auto_refresh': auto_refresh,
        'refresh_button': refresh_button,
        'days_back': days_back,
        'max_users': max_users,
        'show_raw_data': show_raw_data,
        'show_charts': show_charts,
        'debug_mode': debug_mode,
        'search_method': search_method
    }
