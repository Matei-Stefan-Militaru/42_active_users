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
    f"Método: {method} | "Add commentMore actions
    f"🔄 Auto-actualizar: {'✅' if auto_refresh else '❌'} | "
    f"🐛 Debug: {'✅' if debug_mode else '❌'}"
)
