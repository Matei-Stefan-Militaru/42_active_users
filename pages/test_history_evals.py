import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="💰 Eval Points History", page_icon="💰", layout="wide")

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
.stat-card  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem; text-align:center; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:1.8rem; font-weight:700; color:var(--accent); }
.stat-lbl   { font-size:0.65rem; color:var(--muted); margin-top:2px; }
.hist-card  {
    background:var(--surface); border:1px solid var(--border);
    border-left:4px solid var(--accent); border-radius:8px;
    padding:0.75rem 1.25rem; margin-bottom:0.4rem;
    font-family:'JetBrains Mono',monospace;
    display:flex; justify-content:space-between; align-items:center;
}
.hist-reason { font-size:0.8rem; color:#e2e8f0; }
.hist-date   { font-size:0.7rem; color:var(--muted); margin-top:2px; }
.hist-pts-pos { font-size:1.1rem; font-weight:700; color:var(--green); }
.hist-pts-neg { font-size:1.1rem; font-weight:700; color:#ff4444; }
.hist-total   { font-size:0.75rem; color:var(--muted); text-align:right; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">💰 Eval Points History</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Historial de correction points por usuario</div>', unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
def get_token():
    try:
        cid  = st.secrets["api42"]["client_id"]
        csec = st.secrets["api42"]["client_secret"]
        resp = requests.post("https://api.intra.42.fr/oauth/token", data={
            "grant_type":    "client_credentials",
            "client_id":     cid,
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

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💰 Eval Points History")

    login    = st.text_input("Login del usuario", value="smilitar")
    date1    = st.date_input("Fecha 1", value=date(2026, 5, 13))
    date2    = st.date_input("Fecha 2", value=date(2026, 5, 20))
    debug    = st.checkbox("🐛 Debug", value=False)
    load_btn = st.button("🔍 Consultar", type="primary", use_container_width=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_user_id(login, headers):
    resp = api_get(f"https://api.intra.42.fr/v2/users/{login}", headers)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("id"), data.get("correction_point", 0), data.get("displayname", login)
    return None, None, login

def fetch_history(user_id, headers, debug):
    """Fetch all correction_point_historics for a user."""
    all_records = []
    page = 1

    while True:
        url = (
            f"https://api.intra.42.fr/v2/users/{user_id}/correction_point_historics"
            f"?page[size]=100&page[number]={page}&sort=-created_at"
        )
        if debug:
            st.code(url)

        resp = api_get(url, headers)

        if resp.status_code == 429:
            import time
            wait = int(resp.headers.get("Retry-After", 5))
            st.warning(f"⏳ Rate limit — esperando {wait}s…")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            st.error(f"❌ Error API {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        if not data:
            break

        all_records.extend(data)

        if len(data) < 100:
            break
        page += 1

    return all_records

def points_on_date(records_df, target_date):
    """
    Calcula los puntos acumulados al final del día target_date.
    Suma todos los registros hasta ese día inclusive.
    """
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    mask = records_df["created_at_dt"] <= end_of_day
    filtered = records_df[mask]
    if filtered.empty:
        return None
    # El registro más reciente antes o en ese día tiene el total acumulado
    # Usar el campo "sum" si existe, si no reconstruir
    latest = filtered.iloc[0]  # ya ordenado desc
    return int(latest.get("sum", 0)) if "sum" in filtered.columns else None

# ── Load ──────────────────────────────────────────────────────────────────────
if load_btn and login:
    with st.spinner(f"Cargando historial de {login}…"):

        # 1. Obtener user info
        user_id, current_pts, display_name = get_user_id(login.strip(), headers)

        if not user_id:
            st.error(f"❌ Usuario '{login}' no encontrado.")
            st.stop()

        if debug:
            st.write(f"User ID: {user_id} | Nombre: {display_name} | Pts actuales: {current_pts}")

        # 2. Fetch historial completo
        records = fetch_history(user_id, headers, debug)

        if not records:
            st.warning("No se encontró historial de correction points.")
            st.stop()

        # 3. Construir DataFrame
        df = pd.DataFrame(records)

        if debug:
            st.write("Columnas disponibles:", df.columns.tolist())
            st.write("Primeros registros:", df.head(3).to_dict())

        # Parsear fechas
        date_col = "created_at" if "created_at" in df.columns else "updated_at"
        df["created_at_dt"] = pd.to_datetime(df[date_col], utc=True, errors="coerce").dt.tz_localize(None)
        df = df.sort_values("created_at_dt", ascending=False).reset_index(drop=True)
        df["delta"] = df["sum"] - df["sum"].shift(-1)

        st.session_state["hist_df"]       = df
        st.session_state["hist_login"]    = login
        st.session_state["hist_name"]     = display_name
        st.session_state["hist_cur_pts"]  = current_pts
        st.session_state["hist_user_id"]  = user_id
        st.session_state["hist_date1"]    = date1
        st.session_state["hist_date2"]    = date2

    st.success(f"✅ {len(df)} registros cargados para {display_name}")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "hist_df" not in st.session_state:
    st.info("👆 Introduce un login y pulsa **Consultar** para ver el historial.")
    st.markdown("""
    **Qué muestra esta página:**
    - Puntos de evaluación en una fecha concreta
    - Historial completo de cambios
    - Comparativa entre dos fechas
    """)
    st.stop()

df          = st.session_state["hist_df"].copy()
disp_name   = st.session_state["hist_name"]
cur_pts     = st.session_state["hist_cur_pts"]
d1          = st.session_state["hist_date1"]
d2          = st.session_state["hist_date2"]
hist_login  = st.session_state["hist_login"]

# ── Calcular puntos en cada fecha ─────────────────────────────────────────────
def get_pts_on(df, target_date):
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    filtered = df[df["created_at_dt"] <= end_of_day]
    if filtered.empty:
        return "Sin datos antes de esa fecha"
    # El primer registro (ordenado desc) es el más reciente antes de ese día
    row = filtered.iloc[0]
    if "sum" in .columns and pd.notna(row.get("sum")):
        return int(row["sum"])
    return "N/A"

pts_d1 = get_pts_on(, d1)
pts_d2 = get_pts_on(, d2)

# ── Header usuario ────────────────────────────────────────────────────────────
st.markdown(f"### 👤 {disp_name} &nbsp;<small style='color:var(--muted);font-size:0.9rem'>({hist_login})</small>", unsafe_allow_html=True)

# ── Stats ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
for col, (val, lbl) in zip(
    [c1, c2, c3, c4],
    [
        (cur_pts,         "PUNTOS ACTUALES"),
        (pts_d1,          f"PUNTOS {d1.strftime('%d/%m/%Y')}"),
        (pts_d2,          f"PUNTOS {d2.strftime('%d/%m/%Y')}"),
        (len(df),         "TOTAL EVENTOS"),
    ]
):
    col.markdown(
        f'<div class="stat-card"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

# Diferencia entre fechas
if isinstance(pts_d1, int) and isinstance(pts_d2, int):
    diff = pts_d2 - pts_d1
    sign = "+" if diff >= 0 else ""
    color = "#00ff88" if diff >= 0 else "#ff4444"
    st.markdown(
        f"<br><div style='font-family:JetBrains Mono,monospace;font-size:0.85rem;color:var(--muted)'>"
        f"Variación entre {d1.strftime('%d/%m')} → {d2.strftime('%d/%m')}: "
        f"<b style='color:{color};font-size:1.1rem'>{sign}{diff} pts</b></div>",
        unsafe_allow_html=True
    )

st.markdown("---")

# ── Historial completo ────────────────────────────────────────────────────────
st.markdown("### 📋 Historial de eventos")

# Mostrar columnas relevantes
show_cols = [c for c in ["created_at_dt", "reason", "point", "sum", "updated_at"] if c in df.columns]
display_df = df[show_cols].copy()
display_df["created_at_dt"] = display_df["created_at_dt"].dt.strftime("%Y-%m-%d %H:%M")

# Cards para los primeros 50
for _, row in df.head(50).iterrows():
    point  = row.get("point", 0) or 0
    reason = row.get("reason", "—") or "—"
    total  = row.get("sum", "")
    date_s = row["created_at_dt"].strftime("%Y-%m-%d %H:%M") if pd.notna(row["created_at_dt"]) else "—"

    pts_class = "hist-pts-pos" if point >= 0 else "hist-pts-neg"
    sign      = "+" if point > 0 else ""
    total_str = f"Total: {int(total)}" if total != "" and pd.notna(total) else ""

    st.markdown(f"""
    <div class="hist-card">
        <div>
            <div class="hist-reason">{reason}</div>
            <div class="hist-date">{date_s}</div>
        </div>
        <div style="text-align:right">
            <div class="{pts_class}">{sign}{int(point)} pts</div>
            <div class="hist-total">{total_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if len(df) > 50:
    st.caption(f"Mostrando 50 de {len(df)} eventos. Descarga el CSV para verlos todos.")

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
display_df["created_at_dt"] = df["created_at_dt"].dt.strftime("%Y-%m-%d %H:%M")
csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV", csv, f"eval_points_{hist_login}.csv", "text/csv")
