import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Students Directory", page_icon="🎓", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# ── Auth & API Fetch ──────────────────────────────────────────────────────────
def get_token():
    try:
        cid  = st.secrets["api42"]["client_id"]
        csec = st.secrets["api42"]["client_secret"]
        resp = requests.post("https://api.intra.42.fr/oauth/token", data={
            "grant_type":    "client_credentials",
            "client_id":      cid,
            "client_secret": csec,
        }, timeout=10)
        return resp.json().get("access_token") if resp.status_code == 200 else None
    except:
        return None

def get_headers(force=False):
    if force or "api_headers" not in st.session_state:
        token = get_token()
        if not token: return None
        st.session_state["api_headers"] = {"Authorization": f"Bearer {token}"}
    return st.session_state["api_headers"]

def detect_grade(cu: dict) -> str:
    user = cu.get("user", {})
    active = user.get("active?", True)
    bh = cu.get("blackholed_at")
    raw = (cu.get("grade") or "").strip()
    if not active and bh: return "Blackholed"
    if raw: return raw
    return "Outercore" if not cu.get("end_at") and not bh else "Sin grade"

def fetch_students(campus_id, headers, max_pages):
    results = []
    bar = st.progress(0, text="Iniciando descarga de la base de datos...")
    
    # Contenedor de texto para los mensajes de lectura de página
    status_msg = st.empty()
    
    page = 1
    while page <= max_pages:
        # Informar en tiempo real qué página se está leyendo
        status_msg.markdown(f"📖 **Leyendo página {page}...** Solicitando próximos 100 registros a la API.")
        
        url = f"https://api.intra.42.fr/v2/cursus/21/cursus_users?filter[campus_id]={campus_id}&page[size]=100&page[number]={page}&sort=-updated_at"
        resp = requests.get(url, headers=headers, timeout=20)
        
        # ── CONTROL DE RATE LIMITS ──
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            status_msg.warning(f"⏳ **Rate limit alcanzado en página {page}.** El script se pausa por {wait} segundos...")
            time.sleep(wait)
            continue # Reintenta exactamente la misma página
            
        if resp.status_code != 200: 
            st.error(f"❌ Error de API en página {page} ({resp.status_code}): {resp.text[:150]}")
            break
            
        data = resp.json()
        if not data: 
            status_msg.info(f"🏁 Fin de los datos detectado en la página {page} (Vacía).")
            break

        # Mensaje de éxito parcial para la página actual
        status_msg.success(f"✅ ¡Página {page} recibida con éxito! Filtrando admins y procesando estudiantes...")

        for cu in data:
            user = cu.get("user", {})
            if not user: continue
            
            kind = user.get("kind", "")
            if kind != "student":
                continue
                
            bh_raw = cu.get("blackholed_at")
            created_raw = cu.get("created_at")
            
            results.append({
                "Login": user.get("login", ""),
                "Display Name": user.get("displayname", ""),
                "Kind": kind,
                "Current Grade": detect_grade(cu),
                "Level": round(float(cu.get("level", 0)), 2),
                "BH_Raw": bh_raw,
                "Created_Raw": created_raw
            })
            
        # Actualizar barra visual de Streamlit (estimada sobre el max_pages)
        bar.progress(min(page / max_pages, 1.0))
        
        if len(data) < 100: 
            status_msg.info(f"🏁 Última página alcanzada ({page}). No hay más registros pendientes.")
            break
            
        page += 1
        
        # Pausa corta de cortesía para mitigar el límite por segundo
        time.sleep(0.5)
        
    # Limpieza de los indicadores temporales al finalizar con éxito
    time.sleep(1)
    bar.empty()
    status_msg.empty()
    
    return results

# ── Sidebar Control ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧭 Navegación")
    page = st.radio("Sección:", ["Directorio Actual", "Histórico 19.02.2025"])
    st.markdown("---")
    load_btn = st.button("🚀 Cargar alumnos desde API", type="primary", use_container_width=True)

if load_btn:
    h = get_headers(force=True)
    if h:
        with st.spinner("Conectando con la Intra de 42 y filtrando Staff..."):
            rows = fetch_students(46, h, 100)
            if rows:
                df = pd.DataFrame(rows)
                # Convertir fechas nativas para la lógica temporal
                df["BH_Date"] = pd.to_datetime(df["BH_Raw"], errors='coerce').dt.date
                df["Created_Date"] = pd.to_datetime(df["Created_Raw"], errors='coerce').dt.date
                st.session_state["students_master_df"] = df
                st.success(f"✅ {len(df)} estudiantes reales procesados (Admins excluidos).")
            else:
                st.warning("⚠️ No se encontraron registros de estudiantes.")

if "students_master_df" not in st.session_state:
    st.info("👆 Por favor, pulsa **Cargar alumnos** en el menú izquierdo para iniciar la aplicación.")
    st.stop()

df_master = st.session_state["students_master_df"].copy()

# ── PÁGINA 1: VISTA ACTUAL ────────────────────────────────────────────────────
if page == "Directorio Actual":
    st.markdown('<div class="page-title">🎓 42 Students Directory (Hoy)</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Estado actual en tiempo real de los estudiantes cargados (Excluidos cuentas Staff/Admin)</div>', unsafe_allow_html=True)
    
    st.dataframe(df_master[["Login", "Display Name", "Kind", "Current Grade", "Level"]], use_container_width=True, hide_index=True)

# ── PÁGINA 2: HISTÓRICO RECONSTRUIDO 19.02 ────────────────────────────────────
elif page == "Histórico 19.02.2025":
    st.markdown('<div class="page-title">📅 Reconstrucción Histórica: 19.02.2025</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Filtrado inteligente: Muestra quiénes tenían el Cursus activo estrictamente en esa fecha (Solo Estudiantes).</div>', unsafe_allow_html=True)
    
    fecha_corte = datetime(2025, 2, 19).date()
    
    # Viaje en el tiempo sobre el dataframe ya limpio de admins
    df_historico = df_master[
        (df_master["Created_Date"] <= fecha_corte) & 
        ((df_master["BH_Date"].isna()) | (df_master["BH_Date"] > fecha_corte))
    ]
    
    logins_txt = "\n".join(df_historico["Login"].dropna().tolist())
    
    # Interfaz de Descarga y Métricas
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="section-title">📥 DESCARGA DE USERMANES</div>', unsafe_allow_html=True)
        st.download_button(
            label=f"💾 Descargar Logins Activos el 19.02 ({len(df_historico)})",
            data=logins_txt,
            file_name=f"logins_activos_al_19_02_2025.txt",
            mime="text/plain",
            use_container_width=True,
            type="primary"
        )
    
    with c2:
        st.markdown('<div class="section-title">📊 ESTADÍSTICAS RECONSTRUIDAS</div>', unsafe_allow_html=True)
        caidos_hoy = df_historico[df_historico["Current Grade"] == "Blackholed"]
        st.write(f"• **Alumnos reales activos en el Cursus ese día:** {len(df_historico)}")
        st.write(f"• **De esos alumnos, ¿cuántos han caído en el Black Hole a día de hoy?:** {len(caidos_hoy)}")

    st.markdown("---")
    st.markdown('<div class="section-title">📋 LISTA COMPLETA DE LA COHORTE EN ESA FECHA</div>', unsafe_allow_html=True)
    
    st.dataframe(
        df_historico[["Login", "Display Name", "Kind", "Level", "Current Grade"]].rename(
            columns={"Current Grade": "Estado Actual (Hoy)"}
        ),
        use_container_width=True,
        hide_index=True
    )
