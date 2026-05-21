import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone, date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="📅 Generador por Fechas", page_icon="📅", layout="wide")

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
.section-title { font-family:'JetBrains Mono',monospace; font-size:1.1rem; font-weight:700; color:var(--accent); margin-top:1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">📅 Generador de Puntos por Fecha</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Consulta el saldo exacto de puntos de toda la cohorte en una fecha específica</div>', unsafe_allow_html=True)

# ── Auth (API 42) ─────────────────────────────────────────────────────────────
def get_token():
    try:
        cid  = st.secrets["api42"]["client_id"]
        csec = st.secrets["api42"]["client_secret"]
        resp = requests.post("https://api.intra.42.fr/oauth/token", data={
            "grant_type":    "client_credentials",
            "client_id":      cid,
            "client_secret": csec,
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        st.error(f"❌ Token error {resp.status_code}: {resp.text}")
    except Exception as e:
        st.error(f"Auth error: {e}")
    return None

def get_headers(force=False):
    token_ts = st.session_state.get("token_ts")
    now      = datetime.now(timezone.utc)
    expired  = not token_ts or (now - token_ts).total_seconds() > 5400
    if force or expired or "api_headers" not in st.session_state:
        token = get_token()
        if not token:
            return None
        st.session_state["api_headers"] = {"Authorization": f"Bearer {token}"}
        st.session_state["token_ts"]    = now
    return st.session_state["api_headers"]

def api_get(url, headers):
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code == 401:
        headers = get_headers(force=True)
        if headers:
            resp = requests.get(url, headers=headers, timeout=20)
    return resp

headers = get_headers()
if not headers:
    st.error("❌ No se pudo autenticar. Revisa los secrets.")
    st.stop()

# ── Métodos de Inferencia de Puntos Históricos ────────────────────────────────
def fetch_full_history(user_id, headers):
    """Descarga todo el historial de puntos de un alumno."""
    all_records = []
    page = 1
    while True:
        url = f"https://api.intra.42.fr/v2/users/{user_id}/correction_point_historics?page[size]=100&page[number]={page}&sort=-created_at"
        resp = api_get(url, headers)
        
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            time.sleep(wait)
            continue
            
        if resp.status_code != 200:
            break
            
        data = resp.json()
        if not data:
            break
            
        all_records.extend(data)
        if len(data) < 100:
            break
        page += 1
        
    if not all_records:
        return None
        
    df = pd.DataFrame(all_records)
    date_col = "created_at" if "created_at" in df.columns else "updated_at"
    df["created_at_dt"] = pd.to_datetime(df[date_col], utc=True, errors="coerce").dt.tz_localize(None)
    return df.sort_values("created_at_dt", ascending=False).reset_index(drop=True)

def pts_on_date(df, target_date):
    """Calcula el saldo exacto al final del día buscado (EOD)."""
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    before = df[df["created_at_dt"] <= end_of_day]
    
    if not before.empty:
        row = before.iloc[0]
        total = row.get("total")
        return int(total) if total is not None and pd.notna(total) else 0

    if not df.empty:
        oldest = df.iloc[-1]
        total_oldest = oldest.get("total")
        sum_oldest   = oldest.get("sum", 0)
        if total_oldest is not None and pd.notna(total_oldest):
            return max(int(total_oldest) - int(sum_oldest or 0), 0)
            
    return 0

# ── Sidebar / Carga de la lista base ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛠️ Configuración")
    uploaded_file = st.file_uploader("1. Sube un CSV base para extraer los Logins", type=["csv"])
    
    opcion = st.selectbox("2. Fecha a generar", ["Hoy (Tiempo Real)", "Fecha Pasada Personalizada"])
    
    if opcion == "Hoy (Tiempo Real)":
        target_date = date.today()
        opcion_dia = f"{target_date.strftime('%d/%m/%Y')} (Hoy)"
    else:
        target_date = st.date_input("Selecciona la fecha histórica", value=date(2026, 5, 19))
        opcion_dia = target_date.strftime('%d/%m/%Y')

selected_logins = []
if uploaded_file is not None:
    try:
        df_base = pd.read_csv(uploaded_file)
        col_login = [c for c in df_base.columns if "login" in c.lower() or "student" in c.lower()]
        if col_login:
            selected_logins = df_base[col_login[0]].dropna().unique().tolist()
            st.sidebar.success(f"👥 Cargados {len(selected_logins)} logins únicos.")
        else:
            st.sidebar.error("❌ No se encontró columna 'Login' en el archivo.")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# ── Flujo de Procesamiento y Renderizado ──────────────────────────────────────
nombre_columna_puntos = f"Puntos_{opcion_dia.split(' ')[0].replace('/', '_')}"

if not selected_logins:
    st.info("💡 Por favor, sube un CSV válido en la barra lateral que contenga la lista de alumnos que deseas evaluar.")
else:
    st.markdown(f'<div class="section-title">🚀 Generación de Datos para el {opcion_dia}</div>', unsafe_allow_html=True)
    
    btn_procesar = st.button("Iniciar Extracción e Inferencia", type="primary", use_container_width=True)

    if btn_procesar:
        progress_bar = st.progress(0, text="Conectando con la Intranet de 42...")
        status_text = st.empty()
        
        resultados = []
        total_estudiantes = len(selected_logins)

        for idx, login in enumerate(selected_logins):
            login_clean = str(login).strip()
            status_text.text(f"⏳ {idx+1}/{total_estudiantes} — Analizando: {login_clean}")
            progress_bar.progress((idx + 1) / total_estudiantes)

            # 1. Intentar consulta estándar del Perfil del usuario
            resp_user = api_get(f"https://api.intra.42.fr/v2/users/{login_clean}", headers)
            
            # ── SISTEMA DE FALLBACK ANTE CUALQUIER FALLO DE PERFIL (No encontrado / Caída de API) ──
            if resp_user.status_code != 200:
                # Intentamos atacar directamente la ruta de históricos para recuperar su balance transaccional
                url_fallback = f"https://api.intra.42.fr/v2/users/{login_clean}/correction_point_historics?page[size]=100&sort=-created_at"
                resp_fb = api_get(url_fallback, headers)
                
                if resp_fb.status_code == 200 and resp_fb.json():
                    # Si tiene históricos, construimos el dataframe simulado y aplicamos la inferencia temporal de la fecha solicitada
                    all_fb_records = resp_fb.json()
                    df_fb = pd.DataFrame(all_fb_records)
                    date_col = "created_at" if "created_at" in df_fb.columns else "updated_at"
                    df_fb["created_at_dt"] = pd.to_datetime(df_fb[date_col], utc=True, errors="coerce").dt.tz_localize(None)
                    df_fb = df_fb.sort_values("created_at_dt", ascending=False).reset_index(drop=True)
                    
                    puntos_pasados = pts_on_date(df_fb, target_date)
                    resultados.append({
                        "Login": login_clean, 
                        nombre_columna_puntos: int(puntos_pasados), 
                        "Estatus": "Recuperado via Historial"
                    })
                else:
                    # En última instancia, si de verdad no hay rastro, ponemos 0 para no corromper la columna con textos
                    resultados.append({
                        "Login": login_clean, 
                        nombre_columna_puntos: 0, 
                        "Estatus": "Inaccesible (Asumido 0)"
                    })
                continue
            
            # 2. Si el perfil responde correctamente
            user_data = resp_user.json()
            user_id = user_data.get("id")
            puntos_actuales = user_data.get("correction_point", 0)
            puntos_actuales = int(puntos_actuales) if puntos_actuales is not None else 0
            
            if not user_id:
                resultados.append({"Login": login_clean, nombre_columna_puntos: puntos_actuales, "Estatus": "OK (Perfil sin ID)"})
                continue

            # Optimización crítica si la fecha solicitada es hoy
            if target_date == date.today():
                resultados.append({"Login": login_clean, nombre_columna_puntos: puntos_actuales, "Estatus": "OK"})
            else:
                # Consultar historial completo del estudiante para extraer el balance de la fecha pedida
                hist_df = fetch_full_history(user_id, headers)
                if hist_df is None or hist_df.empty:
                    # Si no hay transacciones registradas en su cuenta, su saldo histórico siempre ha sido su saldo actual
                    resultados.append({"Login": login_clean, nombre_columna_puntos: puntos_actuales, "Estatus": "OK (Sin transacciones)"})
                else:
                    puntos_pasados = pts_on_date(hist_df, target_date)
                    resultados.append({"Login": login_clean, nombre_columna_puntos: int(puntos_pasados), "Estatus": "OK"})

        progress_bar.empty()
        status_text.empty()

        st.session_state["tabla_independiente"] = pd.DataFrame(resultados)
        st.session_state["fecha_procesada_label"] = opcion_dia.split(" ")[0].replace("/", "_")

    # Renderizado y descarga segura
    if "tabla_independiente" in st.session_state:
        df_resultado = st.session_state["tabla_independiente"].copy()
        label_fecha = st.session_state.get("fecha_procesada_label", opcion_dia.split(" ")[0].replace("/", "_"))
        
        st.markdown('---')
        st.markdown('### 📋 Tabla de Resultados Generada')
        
        st.dataframe(
            df_resultado.sort_values(by=df_resultado.columns[1], ascending=False),
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                nombre_columna_puntos: st.column_config.NumberColumn(nombre_columna_puntos, format="%d pts")
            }
        )
        
        csv_data = df_resultado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"⬇️ Descargar Tabla de Puntos ({label_fecha}).csv",
            data=csv_data,
            file_name=f"eval_points_{label_fecha}.csv",
            mime="text/csv",
            use_container_width=True
        )
