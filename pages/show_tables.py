import streamlit as st
import pandas as pd

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="📊 Estadísticas de Puntos", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
:root {
    --accent:#00d4ff; --green:#00ff88; --orange:#ff8c00;
    --surface:#161920; --border:#2a2f3d; --muted:#64748b;
}
.stApp { background:#0d0f14; }
.page-title { font-family:'JetBrains Mono',monospace; font-size:2rem; font-weight:700; color:var(--accent); }
.page-sub   { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--muted); margin-bottom:1.5rem; }
.stat-card  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1.2rem; text-align:center; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:2.2rem; font-weight:700; color:var(--green); }
.stat-lbl   { font-size:0.75rem; color:var(--muted); margin-top:4px; letter-spacing:1px; }
.summary-box  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.5rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }
.summary-row  { display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0; border-bottom:1px solid var(--border); }
.summary-row:last-child { border-bottom:none; }
.summary-label { color:var(--muted); font-size:0.8rem; }
.summary-value { font-weight:700; font-size:1rem; color:#e2e8f0; }
.section-title { font-family:'JetBrains Mono',monospace; font-size:1rem; font-weight:700;
                 color:var(--accent); margin:1.5rem 0 0.8rem 0; letter-spacing:1px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">📊 Analizador Estadístico de Puntos</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Sube el CSV generado para calcular métricas, máximos, mínimos y distribución sin consumir API</div>', unsafe_allow_html=True)

# ── Selector/Cargador de Archivo ──────────────────────────────────────────────
uploaded_file = st.file_uploader("📥 Arrastra aquí el archivo CSV generado en la página anterior", type=["csv"])

if uploaded_file is not None:
    try:
        # Leer el CSV descargado
        df = pd.read_csv(uploaded_file)
        
        # Detectar dinámicamente cuál es la columna de puntos (la que no es 'Login' ni 'Estatus')
        columnas_puntos = [c for c in df.columns if c not in ["Login", "Estatus"]]
        
        if not columnas_puntos:
            st.error("❌ El archivo no contiene columnas de puntos válidas. Asegúrate de que es el CSV correcto.")
            st.stop()
            
        col_pts = columnas_puntos[0] # Tomamos la primera columna de puntos disponible
        
        st.success(f"📈 Analizando datos para la columna: **{col_pts}**")
        
        # ── Limpieza de Datos ─────────────────────────────────────────────────
        # Eliminar registros donde los puntos sean NaN o nulos
        df_clean = df.dropna(subset=[col_pts]).copy()
        
        # Filtro por si hay algún valor administrativo erróneo (outliers negativos severos)
        OUTLIER_THRESHOLD = -100
        outliers = df_clean[df_clean[col_pts] < OUTLIER_THRESHOLD]
        df_clean = df_clean[df_clean[col_pts] >= OUTLIER_THRESHOLD]
        
        if df_clean.empty:
            st.warning("⚠️ No hay datos numéricos suficientes en el archivo para generar estadísticas.")
            st.stop()
            
        # Convertir explícitamente a enteros para evitar decimales molestos (.0)
        df_clean[col_pts] = df_clean[col_pts].astype(int)
        
        # Avisar si se quitaron usuarios raros
        if not outliers.empty:
            st.caption(f"⚠️ Se excluyeron {len(outliers)} usuarios con valores anómalos menores a {OUTLIER_THRESHOLD} pts.")

        # ── Cálculos Estadísticos Básicos ─────────────────────────────────────
        total_puntos = int(df_clean[col_pts].sum())
        media_puntos = df_clean[col_pts].mean()
        mediana_puntos = df_clean[col_pts].median()
        max_puntos = int(df_clean[col_pts].max())
        min_puntos = int(df_clean[col_pts].min())
        
        # Encontrar al top mover / estudiante con más puntos
        top_student_row = df_clean.loc[df_clean[col_pts].idxmax()]
        top_login = top_student_row["Login"]
        
        # Número total de estudiantes procesados con éxito
        total_estudiantes = len(df_clean)

        # ── Bloque 1: Tarjetas de Alto Nivel ──────────────────────────────────
        st.markdown('---')
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{total_puntos:,}</div><div class="stat-lbl">TOTAL PUNTOS</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{media_puntos:.2f}</div><div class="stat-lbl">MEDIA POR ALUMNO</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-val">{mediana_puntos:.1f}</div><div class="stat-lbl">MEDIANA</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{total_estudiantes}</div><div class="stat-lbl">ALUMNOS EVALUADOS</div></div>', unsafe_allow_html=True)

        # ── Bloque 2: Distribución y Líderes ──────────────────────────────────
        st.markdown('---')
        col_izq, col_der = st.columns(2)
        
        with col_izq:
            st.markdown(f'<div class="section-title">📊 RESUMEN GENERAL ({col_pts})</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="summary-box">
                <div class="summary-row">
                    <span class="summary-label">PUNTUACIÓN MÁXIMA</span>
                    <span class="summary-value" style="color:var(--green)">{max_puntos} pts ({top_login})</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label">PUNTUACIÓN MÍNIMA</span>
                    <span class="summary-value">{min_puntos} pts</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label">DESVIACIÓN ESTÁNDAR</span>
                    <span class="summary-value">{df_clean[col_pts].std():.2f} pts</span>
                </div>
                <div class="summary-row">
                    <span class="summary-label">ESTUDIANTES CON 0 PUNTOS</span>
                    <span class="summary-value" style="color:var(--orange)">{len(df_clean[df_clean[col_pts] == 0])} usuarios</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_der:
            st.markdown('<div class="section-title">🏆 TOP 5 ESTUDIANTES CON MÁS PUNTOS</div>', unsafe_allow_html=True)
            top_5 = df_clean.nlargest(5, col_pts)
            
            for _, row in top_5.iterrows():
                st.markdown(f"""
                <div class="summary-box" style="padding: 0.6rem 1.5rem;">
                    <div class="summary-row">
                        <span class="summary-label" style="color:#e2e8f0; font-weight:bold;">{row['Login']}</span>
                        <span class="summary-value" style="color:var(--accent)">{int(row[col_pts])} pts</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # ── Bloque 3: Tabla Interactiva Filtrable ─────────────────────────────
        st.markdown('---')
        st.markdown('<div class="section-title">📋 TABLA DE DATOS PROCESADA</div>', unsafe_allow_html=True)
        
        # Buscador interno rápido
        search_query = st.text_input("🔍 Buscar por login de estudiante:", "").strip().lower()
        if search_query:
            df_render = df_clean[df_clean["Login"].str.lower().str.contains(search_query)]
        else:
            df_render = df_clean
            
        st.dataframe(
            df_render.sort_values(by=col_pts, ascending=False),
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "Login": st.column_config.TextColumn("Login de Estudiante", width="medium"),
                col_pts: st.column_config.NumberColumn(col_pts, format="%d pts"),
                "Estatus": st.column_config.TextColumn("Resultado API", width="small")
            }
        )

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo CSV: {e}")
else:
    st.info("💡 Por favor, arrastra o selecciona el archivo `.csv` descargado previamente para ver el desglose estadístico.")
