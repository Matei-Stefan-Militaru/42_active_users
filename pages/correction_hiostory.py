import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone, date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="📥 Generador por Fechas Independientes", page_icon="🏫", layout="wide")

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
.section-title { font-family:'JetBrains Mono',monospace; font-size:0.9rem; font-weight:700; color:var(--accent); margin:1.25rem 0 0.6rem 0; letter-spacing:1px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">📥 Generador por Fechas Independientes</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Carga optimizada paso a paso para mitigar el límite de llamadas a la API (Rate Limit)</div>', unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
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

# ── Funciones de descarga de historial ────────────────────────────────────────
def fetch_full_history(user_id, headers):
    all_records = []
    page = 1
    while True:
        url = (
            f"https://api.intra.42.fr/v2/users/{user_id}/correction_point_historics"
            f"?page[size]=100&page[number]={page}&sort=-created_at"
        )
        resp = api_get(url, headers)
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", 5)))
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
    df["created_at_dt"] = pd.to_datetime(
        df.get("created_at", df.get("updated_at")),
        utc=True, errors="coerce"
    ).dt.tz_localize(None)
    df = df.sort_values("created_at_dt", ascending=False).reset_index(drop=True)
    return df

def pts_on_date(hist_df, target_date):
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    before = hist_df[hist_df["created_at_dt"] <= end_of_day]

    if not before.empty:
        row = before.iloc[0]
        total = row.get("total")
        return int(total) if total is not None and pd.notna(total) else None

    oldest = hist_df.iloc[-1]
    total_oldest = oldest.get("total")
    sum_oldest   = oldest.get("sum", 0)

    if total_oldest is None or pd.isna(total_oldest):
        return None

    pre_balance = int(total_oldest) - int(sum_oldest or 0)
    return max(pre_balance, 0)

# ── Bloque 1: Recogida y asignación de Archivos TXT ───────────────────────────
st.markdown('### 📂 1. Cargar archivos de estudiantes')
col_files_left, col_files_right = st.columns(2)

with col_files_left:
    file_19 = st.file_uploader("Subir archivo de estudiantes del 19.02 (`logins_activos_al_19_02_2025.txt`)", type=["txt"])

with col_files_right:
    file_hoy = st.file_uploader("Subir archivo de estudiantes de Hoy (`logins_cursus_activo_20260521.txt`)", type=["txt"])

# Helper para convertir el TXT en una lista limpia de Logins
def load_logins_from_txt(uploaded_file):
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8")
        logins = [line.strip() for line in content.splitlines() if line.strip()]
        return logins
    return []

logins_19_02 = load_logins_from_txt(file_19)
logins_hoy = load_logins_from_txt(file_hoy)

# Mostrar estados de carga
if file_19:
    st.caption(f"✅ Archivo del 19.02 cargado: {len(logins_19_02)} estudiantes encontrados.")
if file_hoy:
    st.caption(f"✅ Archivo de hoy cargado: {len(logins_hoy)} estudiantes encontrados.")

st.markdown("---")

# ── Bloque 2: Selección del Día a procesar ────────────────────────────────────
st.markdown('### 🗓️ 2. Seleccionar el día que deseas generar')
st.info("Para cuidar tus cuotas de API por hora, selecciona y procesa **solo un día a la vez**.")

opcion_dia = st.selectbox(
    "¿De qué fecha quieres generar los datos y la tabla?",
    [
        "Selecciona una opción...",
        "19/02 (Usa archivo 19.02)",
        "25/02 (Usa archivo 19.02)",
        "17/05 (Usa archivo de Hoy)",
        "Hoy (Usa archivo de Hoy)"
    ]
)

# Mapeo de fechas reales y asignación del set de estudiantes correspondiente
target_date = None
selected_logins = []
nombre_columna_puntos = ""

if opcion_dia == "19/02 (Usa archivo 19.02)":
    target_date = date(2026, 2, 19)
    selected_logins = logins_19_02
    nombre_columna_puntos = "Puntos al 19/02/2026"
elif opcion_dia == "25/02 (Usa archivo 19.02)":
    target_date = date(2026, 2, 25)
    selected_logins = logins_19_02
    nombre_columna_puntos = "Puntos al 25/02/2026"
elif opcion_dia == "17/05 (Usa archivo de Hoy)":
    target_date = date(2026, 5, 17)
    selected_logins = logins_hoy
    nombre_columna_puntos = "Puntos al 17/05/2026"
elif opcion_dia == "Hoy (Usa archivo de Hoy)":
    target_date = date.today()
    selected_logins = logins_hoy
    nombre_columna_puntos = "Puntos Hoy"

# ── Bloque 3: Procesamiento y Descarga ────────────────────────────────────────
if target_date is not None:
    if not selected_logins:
        st.warning(f"⚠️ Has seleccionado una opción que requiere un archivo que aún no has subido. Por favor, súbelo arriba.")
    else:
        st.success(f"Listo para procesar **{len(selected_logins)} estudiantes** para la fecha seleccionada.")
        
        # Guardamos en session_state para que la tabla no desaparezca al dar clic en descargar
        btn_procesar = st.button(f"🚀 Generar Tabla para {opcion_dia.split(' ')[0]}", type="primary")

        if btn_procesar:
            # Inicializar barra de progreso
            progress_bar = st.progress(0, text="Llamando a la API de 42...")
            status_text = st.empty()
            
            resultados = []
            total_estudiantes = len(selected_logins)

            for idx, login in enumerate(selected_logins):
                status_text.text(f"⏳ {idx+1}/{total_estudiantes} — Procesando: {login}")
                progress_bar.progress((idx + 1) / total_estudiantes)

                # 1. Obtener el ID numérico del usuario
                resp_user = api_get(f"https://api.intra.42.fr/v2/users/{login}", headers)
                if resp_user.status_code != 200:
                    resultados.append({"Login": login, nombre_columna_puntos: None, "Estatus": "No encontrado en API"})
                    continue
                
                user_data = resp_user.json()
                user_id = user_data.get("id")
                
                if not user_id:
                    resultados.append({"Login": login, nombre_columna_puntos: None, "Estatus": "Sin ID válido"})
                    continue

                # 2. Si el día solicitado es "Hoy", podemos extraer el dato directamente sin procesar todo el historial histórico
                if target_date == date.today():
                    puntos_hoy = user_data.get("correction_point")
                    resultados.append({"Login": login, nombre_columna_puntos: puntos_hoy, "Estatus": "OK"})
                else:
                    # 3. Si es fecha pasada, bajamos historial completo
                    hist_df = fetch_full_history(user_id, headers)
                    if hist_df is None:
                        resultados.append({"Login": login, nombre_columna_puntos: 0, "Estatus": "Sin historial"})
                    else:
                        puntos_pasados = pts_on_date(hist_df, target_date)
                        resultados.append({"Login": login, nombre_columna_puntos: puntos_pasados, "Estatus": "OK"})

            progress_bar.empty()
            status_text.empty()

            # Guardar el DataFrame resultante en caché de sesión
            df_resultado = pd.DataFrame(resultados)
            st.session_state["tabla_independiente"] = df_resultado
            st.session_state["fecha_procesada_label"] = opcion_dia.split(" ")[0].replace("/", "_")

        # Verificar si hay una tabla lista para renderizar y descargar
        if "tabla_independiente" in st.session_state:
            df_render = st.session_state["tabla_independiente"]
            label_fecha = st.session_state["fecha_procesada_label"]
            
            st.markdown('### 📋 Tabla Generada')
            st.dataframe(df_render, use_container_width=True, hide_index=True, height=400)
            
            # Botón de descarga dedicado
            csv_data = df_render.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"⬇️ Descargar Tabla ({label_fecha}).csv",
                data=csv_data,
                file_name=f"eval_points_{label_fecha}.csv",
                mime="text/csv",
                use_container_width=True
            )
