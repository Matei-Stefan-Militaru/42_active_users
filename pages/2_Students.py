import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Students Directory", page_icon="🎓", layout="wide")

# Estilos CSS (Mantenemos tu estética Matrix/Cyberpunk)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
:root {
    --accent:#00d4ff; --green:#00ff88; --orange:#ff8c00;
    --purple:#a855f7; --red:#ff4444; --surface:#161920;
    --border:#2a2f3d; --muted:#64748b;
}
.stApp { background:#0d0f14; }
.page-title { font-family:'JetBrains Mono',monospace; font-size:2rem; font-weight:700; color:var(--accent); }
.page-sub   { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--muted); margin-bottom:1.5rem; }
.section-title { font-family:'JetBrains Mono',monospace; font-size:0.9rem; font-weight:700; color:var(--accent); margin:1.25rem 0 0.6rem 0; letter-spacing:1px; }
.stat-card  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:0.9rem; text-align:center; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:1.6rem; font-weight:700; color:var(--accent); }
.stat-lbl   { font-size:0.6rem; color:var(--muted); margin-top:2px; letter-spacing:0.5px; }
.summary-box  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.5rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }
.summary-row  { display:flex; justify-content:space-between; align-items:center; padding:0.3rem 0; border-bottom:1px solid var(--border); }
.summary-value { font-weight:700; font-size:0.9rem; color:#e2e8f0; }
</style>
""", unsafe_allow_html=True)

# ── Funciones de API (Se mantienen igual para que funcione) ────────────────────
def get_token():
    try:
        cid, csec = st.secrets["api42"]["client_id"], st.secrets["api42"]["client_secret"]
        resp = requests.post("https://api.intra.42.fr/oauth/token", data={
            "grant_type": "client_credentials", "client_id": cid, "client_secret": csec
        }, timeout=10)
        return resp.json().get("access_token") if resp.status_code == 200 else None
    except: return None

def get_headers(force=False):
    if force or "api_headers" not in st.session_state:
        token = get_token()
        if not token: return None
        st.session_state["api_headers"] = {"Authorization": f"Bearer {token}"}
    return st.session_state["api_headers"]

def api_get(url, headers):
    return requests.get(url, headers=headers, timeout=20)

def detect_grade(cu, now_utc):
    user = cu.get("user", {})
    active, bh = user.get("active?", True), cu.get("blackholed_at")
    if not active and bh: return "Blackholed"
    return (cu.get("grade") or "Outercore").strip()

def fetch_students(campus_id, headers, max_pages):
    results = []
    bar = st.progress(0)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    for page in range(1, max_pages + 1):
        url = f"https://api.intra.42.fr/v2/cursus/21/cursus_users?filter[campus_id]={campus_id}&page[size]=100&page[number]={page}&sort=-updated_at"
        resp = api_get(url, headers)
        if resp.status_code != 200: break
        data = resp.json()
        if not data: break
        for cu in data:
            user = cu.get("user", {})
            grade = detect_grade(cu, now_utc)
            results.append({
                "Login": user.get("login", ""),
                "Grade": grade,
                "Level": round(float(cu.get("level", 0)), 2),
                "Updated": cu.get("updated_at", ""),
                "Kind": user.get("kind", ""),
                "Eval Points": int(user.get("correction_point", 0) or 0)
            })
        bar.progress(page/max_pages)
        if len(data) < 100: break
    return results

# ── Sidebar: Navegación y Carga ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧭 Navegación")
    page = st.radio("Ir a:", ["Directorio Principal", "Reporte Especial 19.02"])
    st.markdown("---")
    load_btn = st.button("🚀 Cargar/Actualizar Datos", use_container_width=True)
    
    if load_btn:
        h = get_headers(force=True)
        if h:
            with st.spinner("Descargando..."):
                data = fetch_students(46, h, 50)
                if data:
                    df = pd.DataFrame(data)
                    df["Updated"] = pd.to_datetime(df["Updated"]).dt.tz_localize(None)
                    st.session_state["raw_df"] = df
                    st.session_state["last_ts"] = datetime.now().strftime("%H:%M:%S")
                    st.success("¡Datos listos!")

# Verificar si hay datos
if "raw_df" not in st.session_state:
    st.info("👈 Usa el botón 'Cargar Datos' en la barra lateral para empezar.")
    st.stop()

df_main = st.session_state["raw_df"].copy()

# ── LÓGICA DE PÁGINAS ────────────────────────────────────────────────────────

if page == "Directorio Principal":
    st.markdown('<div class="page-title">🎓 42 Students Directory</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Vista General de todos los alumnos cargados</div>', unsafe_allow_html=True)
    
    # Stats rápidos
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alumnos", len(df_main))
    c2.metric("Activos (Sin BH)", len(df_main[df_main["Grade"] != "Blackholed"]))
    c3.metric("Nivel Medio", f"{df_main['Level'].mean():.2f}")
    
    st.dataframe(df_main, use_container_width=True, hide_index=True)

# ── NUEVA PÁGINA: REPORTE 19.02 ───────────────────────────────────────────────
elif page == "Reporte Especial 19.02":
    st.markdown('<div class="page-title">📅 Reporte: Especial 19 de Febrero</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Análisis de alumnos que estuvieron activos o tuvieron hitos este día.</div>', unsafe_allow_html=True)
    
    target_date = datetime(2025, 2, 19).date() # Puedes cambiar el año si es 2024
    
    # 1. Filtrar por los que tuvieron CUALQUIER actualización el 19.02
    df_feb19_updated = df_main[df_main["Updated"].dt.date == target_date]
    
    # 2. Filtrar los que están ACTIVOS (No Blackholed) para descargar
    df_activos_ahora = df_main[df_main["Grade"] != "Blackholed"]
    
    # UI de la página
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown('<div class="section-title">📊 COHORTE ACTIVOS (CURSUS)</div>', unsafe_allow_html=True)
        st.write("Estos son los alumnos que actualmente no han caído en el Black Hole.")
        
        logins_activos = "\n".join(df_activos_ahora["Login"].tolist())
        st.download_button(
            label=f"📥 Descargar Usernames Activos ({len(df_activos_ahora)})",
            data=logins_activos,
            file_name=f"logins_activos_fecha_19_02.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col_right:
        st.markdown('<div class="section-title">🔍 ACTIVIDAD EL 19.02</div>', unsafe_allow_html=True)
        if not df_feb19_updated.empty:
            st.success(f"Se detectaron {len(df_feb19_updated)} alumnos con actividad en Intra este día.")
            st.dataframe(df_feb19_updated[["Login", "Grade", "Level"]], height=200)
        else:
            st.warning("No hubo actualizaciones de perfiles registradas el 19.02 en esta carga.")

    st
