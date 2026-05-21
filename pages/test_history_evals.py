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
    border-radius:8px; padding:0.75rem 1.25rem; margin-bottom:0.4rem;
    font-family:'JetBrains Mono',monospace;
    display:flex; justify-content:space-between; align-items:center;
}
.hist-reason { font-size:0.8rem; color:#e2e8f0; }
.hist-date   { font-size:0.7rem; color:var(--muted); margin-top:2px; }
.hist-pts-pos { font-size:1.1rem; font-weight:700; color:var(--green); }
.hist-pts-neg { font-size:1.1rem; font-weight:700; color:#ff4444; }
.hist-pts-zer { font-size:1.1rem; font-weight:700; color:var(--muted); }
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
    login  = st.text_input("Login del usuario", value="smilitar")
    date1  = st.date_input("Fecha 1", value=date(2026, 5, 13))
    date2  = st.date_input("Fecha 2", value=date(2026, 5, 20))
    debug  = st.checkbox("🐛 Debug", value=False)
    load_btn = st.button("🔍 Consultar", type="primary", use_container_width=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_user_info(login, headers):
    resp = api_get(f"https://api.intra.42.fr/v2/users/{login}", headers)
    if resp.status_code == 200:
        d = resp.json()
        return d.get("id"), d.get("correction_point", 0), d.get("displayname", login)
    return None, None, login

def fetch_history(user_id, headers, debug):
    all_records = []
    page = 1
    import time
    while True:
        url = (
            f"https://api.intra.42.fr/v2/users/{user_id}/correction_point_historics"
            f"?page[size]=100&page[number]={page}&sort=-created_at"
        )
        if debug:
            st.code(url)

        resp = api_get(url, headers)

        if resp.status_code == 429:
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

def get_pts_on(df, target_date):
    """
    Devuelve el total de puntos al final del día target_date.
    Usa el campo 'sum' del registro más reciente <= ese día.
    Si no hay registros ese día, coge el último anterior.
    """
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    filtered = df[df["created_at_dt"] <= end_of_day]
    if filtered.empty:
        return None
    row = filtered.iloc[0]  # más reciente (df ordenado desc)
    val = row.get("sum")
    if val is not None and pd.notna(val):
        return int(val)
    return None

# ── Load ──────────────────────────────────────────────────────────────────────
if load_btn and login:
    with st.spinner(f"Cargando historial de {login}…"):
        user_id, current_pts, display_name = get_user_info(login.strip(), headers)

        if not user_id:
            st.error(f"❌ Usuario '{login}' no encontrado.")
            st.stop()

        records = fetch_history(user_id, headers, debug)

        if not records:
            st.warning("No se encontró historial de correction points.")
            st.stop()

        df = pd.DataFrame(records)

        if debug:
            st.write("Columnas:", df.columns.tolist())
            st.write("Muestra:", df.head(3).to_dict())

        # Parsear fecha
        date_col = "created_at" if "created_at" in df.columns else "updated_at"
        df["created_at_dt"] = pd.to_datetime(df[date_col], utc=True, errors="coerce").dt.tz_localize(None)
        df = df.sort_values("created_at_dt", ascending=False).reset_index(drop=True)

        # Calcular delta real entre registros consecutivos
        # df ordenado desc → shift(-1) es el registro anterior (más antiguo)
        if "sum" in df.columns:
            df["delta"] = df["sum"] - df["sum"].shift(-1)
            # El último registro no tiene anterior → delta = sum (primer evento)
            df["delta"] = df["delta"].fillna(df["sum"])
            df["delta"] = df["delta"].astype(int)

        st.session_state["hist_df"]      = df
        st.session_state["hist_login"]   = login.strip()
        st.session_state["hist_name"]    = display_name
        st.session_state["hist_cur_pts"] = current_pts
        st.session_state["hist_date1"]   = date1
        st.session_state["hist_date2"]   = date2

    st.success(f"✅ {len(df)} registros cargados para {display_name}")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "hist_df" not in st.session_state:
    st.info("👆 Introduce un login y pulsa **Consultar**.")
    st.stop()

df         = st.session_state["hist_df"].copy()
disp_name  = st.session_state["hist_name"]
cur_pts    = st.session_state["hist_cur_pts"]
d1         = st.session_state["hist_date1"]
d2         = st.session_state["hist_date2"]
hist_login = st.session_state["hist_login"]

pts_d1 = get_pts_on(df, d1)
pts_d2 = get_pts_on(df, d2)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"### 👤 {disp_name} &nbsp;<small style='color:var(--muted);font-size:0.9rem'>({hist_login})</small>",
    unsafe_allow_html=True
)

# ── Stats ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
for col, (val, lbl) in zip(
    [c1, c2, c3, c4],
    [
        (cur_pts,                          "PUNTOS ACTUALES"),
        (pts_d1 if pts_d1 is not None else "Sin datos", f"PUNTOS {d1.strftime('%d/%m/%Y')}"),
        (pts_d2 if pts_d2 is not None else "Sin datos", f"PUNTOS {d2.strftime('%d/%m/%Y')}"),
        (len(df),                          "TOTAL EVENTOS"),
    ]
):
    col.markdown(
        f'<div class="stat-card"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

# Variación entre fechas
if isinstance(pts_d1, int) and isinstance(pts_d2, int):
    diff  = pts_d2 - pts_d1
    sign  = "+" if diff >= 0 else ""
    color = "#00ff88" if diff >= 0 else "#ff4444"
    st.markdown(
        f"<br><div style='font-family:JetBrains Mono,monospace;font-size:0.85rem;color:var(--muted)'>"
        f"Variación {d1.strftime('%d/%m')} → {d2.strftime('%d/%m')}: "
        f"<b style='color:{color};font-size:1.1rem'>{sign}{diff} pts</b></div>",
        unsafe_allow_html=True
    )

st.markdown("---")

# ── Historial ─────────────────────────────────────────────────────────────────
st.markdown("### 📋 Historial de eventos")

has_delta = "delta" in df.columns
has_sum   = "sum" in df.columns

for _, row in df.head(100).iterrows():
    delta  = int(row["delta"]) if has_delta and pd.notna(row.get("delta")) else 0
    total  = int(row["sum"])   if has_sum   and pd.notna(row.get("sum"))   else None
    reason = row.get("reason", "—") or "—"
    date_s = row["created_at_dt"].strftime("%Y-%m-%d %H:%M") if pd.notna(row["created_at_dt"]) else "—"

    if delta > 0:
        pts_class = "hist-pts-pos"
        sign      = "+"
        border    = "#00ff8855"
    elif delta < 0:
        pts_class = "hist-pts-neg"
        sign      = ""
        border    = "#ff444455"
    else:
        pts_class = "hist-pts-zer"
        sign      = ""
        border    = "var(--border)"

    total_str = f"Total: {total}" if total is not None else ""

    st.markdown(f"""
    <div class="hist-card" style="border-left:4px solid {border}">
        <div>
            <div class="hist-reason">{reason}</div>
            <div class="hist-date">{date_s}</div>
        </div>
        <div style="text-align:right">
            <div class="{pts_class}">{sign}{delta} pts</div>
            <div class="hist-total">{total_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if len(df) > 100:
    st.caption(f"Mostrando 100 de {len(df)} eventos. Exporta CSV para verlos todos.")

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
export_df = df.copy()
export_df["created_at_dt"] = export_df["created_at_dt"].dt.strftime("%Y-%m-%d %H:%M")
csv = export_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV", csv, f"eval_points_{hist_login}.csv", "text/csv")
