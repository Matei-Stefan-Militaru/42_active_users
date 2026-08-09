# ui/user_table.py

import streamlit as st
import pandas as pd

def safe_format_date(date_val):
    """Formatear fechas de manera segura"""
    try:
        if pd.isna(date_val):
            return "N/A"
        if isinstance(date_val, str):
            parsed_date = pd.to_datetime(date_val, utc=True).tz_localize(None)
            return parsed_date.strftime('%d/%m/%Y %H:%M')
        return date_val.strftime('%d/%m/%Y %H:%M')
    except:
        return str(date_val) if date_val else "N/A"

def render_metrics(df):
    """Renderizar las métricas principales"""
    # Métricas principales en 6 columnas más compactas
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("👥", len(df), label_visibility="collapsed")
    
    with col2:
        unique_users = df['Login'].nunique()
        st.metric("👤", unique_users, label_visibility="collapsed")
    
    with col3:
        avg_level = df['Nivel'].mean()
        st.metric("📊", f"{avg_level:.1f}", label_visibility="collapsed")
    
    with col4:
        users_in_campus = len(df[df['Estado'].str.contains('En campus')])
        st.metric("🟢", users_in_campus, label_visibility="collapsed")
    
    with col5:
        max_level = df['Nivel'].max()
        st.metric("🏆", f"{max_level:.1f}", label_visibility="collapsed")
    
    with col6:
        if 'last_update' in st.session_state:
            last_update = st.session_state.last_update.strftime("%H:%M")
            st.metric("🕒", last_update, label_visibility="collapsed")
        else:
            if 'Wallet' in df.columns and not df['Wallet'].isna().all():
                avg_wallet = df['Wallet'].mean()
                st.metric("💰", f"{avg_wallet:.0f}", label_visibility="collapsed")
            else:
                st.metric("💰", "N/A", label_visibility="collapsed")
                
    # Leyenda pequeña debajo
    st.caption("👥 Activos | 👤 Únicos | 📊 Nivel ⌀ | 🟢 En Campus | 🏆 Max | 🕒 Update")

def render_user_table(df):
    """Renderizar la tabla de usuarios con filtros"""
    st.markdown("#### 👥 Users")
    
    # Filtros en una sola fila más compacta
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search_user = st.text_input("Search", placeholder="login...", label_visibility="collapsed")
    with col2:
        min_level = st.number_input("Min", min_value=0.0, max_value=50.0, value=0.0, step=1.0, label_visibility="collapsed")
    with col3:
        status_filter = st.selectbox("Status", ["All", "🟢", "🔵"], label_visibility="collapsed")
    with col4:
        st.write("")  # Espacio para alineación
    
    # Aplicar filtros
    filtered_df = df.copy()
    
    if search_user:
        mask = (filtered_df['Login'].str.contains(search_user, case=False, na=False) |
                filtered_df['Nombre'].str.contains(search_user, case=False, na=False))
        filtered_df = filtered_df[mask]
    
    if min_level > 0:
        filtered_df = filtered_df[filtered_df['Nivel'] >= min_level]
    
    if status_filter != "All":
        if status_filter == "🟢":
            filtered_df = filtered_df[filtered_df['Estado'].str.contains('En campus')]
        elif status_filter == "🔵":
            filtered_df = filtered_df[~filtered_df['Estado'].str.contains('En campus')]
    
    # Formatear para mostrar - solo columnas esenciales
    display_columns = ['Login', 'Estado', 'Ubicación', 'Nivel']
    
    # Add wallet si existe
    if 'Wallet' in filtered_df.columns:
        display_columns.append('Wallet')
    
    display_df = filtered_df[display_columns].copy()
    
    # Formatear datos de manera más compacta
    display_df['Estado'] = display_df['Estado'].apply(lambda x: "🟢" if "En campus" in x else "🔵")
    display_df['Nivel'] = display_df['Nivel'].apply(lambda x: f"{x:.1f}")
    display_df['Ubicación'] = display_df['Ubicación'].apply(lambda x: x if x != "N/A" else "—")
    
    # Acortar logins largos
    display_df['Login'] = display_df['Login'].apply(
        lambda x: x[:15] + "..." if len(str(x)) > 15 else str(x)
    )
    
    # Format wallet si existe
    if 'Wallet' in display_df.columns:
        display_df['Wallet'] = display_df['Wallet'].apply(lambda x: f"{x:.0f}")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=300,
        hide_index=True
    )
    
    st.caption(f"{len(filtered_df)} of {len(df)} users")

def render_raw_data():
    """Renderizar datos raw si están habilitados"""
    if 'users_raw' in st.session_state:
        st.markdown("## 🔍 Datos Raw (Primeros 3 registros)")
        st.json(st.session_state.users_raw[:5])

def render_info_section(df, selected_country, selected_campus, days_back, search_method):
    """Renderizar información temporal y de contexto"""
    if not df.empty:
        fecha_min = df['Última conexión'].min().strftime("%d/%m/%Y %H:%M")
        fecha_max = df['Última conexión'].max().strftime("%d/%m/%Y %H:%M")
        country_info = f" | **País:** {selected_country}" if selected_country != "Todos" else ""
        st.info(f"📅 **Período de actividad:** {fecha_min} → {fecha_max} | **Campus:** {selected_campus}{country_info} | **Método:** {search_method}")

def render_help_section():
    """Renderizar sección de ayuda cuando no hay datos"""
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
