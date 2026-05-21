Aquí tienes el código completo para tu archivo de Streamlit (por ejemplo, puedes llamarlo `pag_generador_fechas.py`).

He unificado la estructura que venías usando con toda la lógica de autenticación, el control de flujo, el **parche de seguridad por si falla la API** (calculando el último saldo conocido para que no rompa la consistencia numérica) y la reconstrucción matemática inversa si consultas una fecha pasada.

```python
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

# ── Métodos de Historial ──────────────────────────────────────────────────────
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
    """Calcula matemáticamente el saldo en el día objetivo (EOD)."""
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
    
    # Selector de fecha destino
    opcion = st.selectbox("2. Fecha a generar", ["Hoy (Tiempo Real)", "Fecha Pasada Personalizada"])
    
    if opcion == "Hoy (Tiempo Real)":
        target_date = date.today()
        opcion_dia = f"{target_date.strftime('%d/%m/%Y')} (Hoy)"
    else:
        target_date = st.date_input("Selecciona la fecha histórica", value=date(2026, 5, 19))
        opcion_dia = target_date.strftime('%d/%m/%Y')

# Process list base
selected_logins = []
if uploaded_file is not None:
    try:
        df_base = pd.read_csv(uploaded_file)
        # Buscar columna de usuarios de forma flexible
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

            # 1. Consulta estándar del Perfil
            resp_user = api_get(f"https://api.intra.42.fr/v2/users/{login_clean}", headers)
            
            # ── PARCHE: FALLBACK ANTE FALLO DE LA API O LOGIN CAMBIADO/INACTIVO ──
            if resp_user.status_code != 200:
                # Segundo intento directo a través de sus históricos
                url_fallback = f"https://api.intra.42.fr/v2/users/{login_clean}/correction_point_historics?page[size]=1&sort=-created_at"
                resp_fb = api_get(url_fallback, headers)
                
                if resp_fb.status_code == 200 and resp_fb.json():
                    # Extrae el último total conocido en el sistema transaccional
                    ultimo_evento = resp_fb.json()[0]
                    puntos_estimados = ultimo_evento.get("total", 0)
                    resultados.append({
                        "Login": login_clean, 
                        nombre_columna_puntos: int(puntos_estimados) if puntos_estimados else 0, 
                        "Estatus": "OK (Último conocido via Historial)"
                    })
                else:
                    # Forzar 0 numérico para no romper cálculos del analizador estadístico
                    resultados.append({
                        "Login": login_clean, 
                        nombre_columna_puntos: 0, 
                        "Estatus": "No encontrado (Asumido 0)"
                    })
                continue
            
            # 2. Si la API responde correctamente
            user_data = resp_user.json()
            user_id = user_data.get("id")
            puntos_actuales = user_data.get("correction_point", 0)
            
            if not user_id:
                resultados.append({"Login": login_clean, nombre_columna_puntos: int(puntos_actuales or 0), "Estatus": "OK (Sin ID corporativo)"})
                continue

            # Si es el día de hoy, evitamos pedir el historial completo (Ahorro crítico de Rate Limits)
            if target_date == date.today():
                resultados.append({"Login": login_clean, nombre_columna_puntos: int(puntos_actuales or 0), "Estatus": "OK"})
            else:
                hist_df = fetch_full_history(user_id, headers)
                if hist_df is None or hist_df.empty:
                    # Si no hay eventos, significa que su balance actual es el que ha tenido siempre
                    resultados.append({"Login": login_clean, nombre_columna_puntos: int(puntos_actuales or 0), "Estatus": "OK (Sin movimientos)"})
                else:
                    puntos_pasados = pts_on_date(hist_df, target_date)
                    resultados.append({"Login": login_clean, nombre_columna_puntos: int(puntos_pasados), "Estatus": "OK"})

        progress_bar.empty()
        status_text.empty()

        # Guardar en persistencia de sesión de Streamlit
        st.session_state["tabla_independiente"] = pd.DataFrame(resultados)
        st.session_state["fecha_procesada_label"] = opcion_dia.split(" ")[0].replace("/", "_")

    # Renderizado y descarga de la tabla generada
    if "tabla_independiente" in st.session_state:
        df_resultado = st.session_state["tabla_independiente"].copy()
        label_fecha = st.session_state["fecha_processed_label"] if "fecha_processed_label" in st.session_state else opcion_dia.split(" ")[0].replace("/", "_")
        
        st.markdown('---')
        st.markdown('### 📋 Tabla de Resultados Generada')
        
        # Formateador visual para asegurar que se vean como enteros limpios
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

```
