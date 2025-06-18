import streamlit as st
import plotly.express as px
import pandas as pd


def render_metrics(df):
    """Renderiza las métricas principales"""
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


def render_additional_metrics(df):
    """Renderiza métricas adicionales"""
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


def render_activity_by_hour(df):
    """Renderiza el gráfico de actividad por hora"""
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


def render_activity_by_day(df, days_back):
    """Renderiza el gráfico de actividad por día"""
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


def render_level_distribution(df):
    """Renderiza la distribución de niveles y top usuarios"""
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


def render_temporal_info(df, selected_country, search_method_used):
    """Renderiza información temporal"""
    if not df.empty:
        fecha_min = df['Última conexión'].min().strftime("%d/%m/%Y %H:%M")
        fecha_max = df['Última conexión'].max().strftime("%d/%m/%Y %H:%M")
        country_info = f" | **País:** {selected_country}" if selected_country != "Todos" else ""
        st.info(f"📅 **Período de actividad:** {fecha_min} → {fecha_max} | **Campus:** {st.session_state.get('selected_campus', 'N/A')}{country_info} | **Método:** {search_method_used}")


def render_all_charts(df, days_back, selected_country, search_method_used):
    """Renderiza todos los gráficos y métricas"""
    # Métricas principales
    render_metrics(df)
    
    # Métricas adicionales
    render_additional_metrics(df)
    
    # Información temporal
    render_temporal_info(df, selected_country, search_method_used)
    
    # Gráficos de actividad
    render_activity_by_hour(df)
    render_activity_by_day(df, days_back)
    
    # Distribución de niveles
    render_level_distribution(df)
