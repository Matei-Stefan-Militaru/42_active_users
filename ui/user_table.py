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

def render_user_table(df):
    """Renderizar la tabla de usuarios con filtros"""
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
    
    # Formatear datos
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

def render_raw_data():
    """Renderizar datos raw si están habilitados"""
    if 'users_raw' in st.session_state:
        st.markdown("## 🔍 Datos Raw (Primeros 3 registros)")
        st.json(st.session_state.users_raw[:3])

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
