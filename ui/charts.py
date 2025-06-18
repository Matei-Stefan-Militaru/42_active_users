# ui/charts.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

def render_charts(df, days_back, selected_campus):
    """Renderizar todos los gráficos"""
    if len(df) == 0:
        return
    
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
            title=f"Distribución de Actividad - {selected_campus}"
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
