import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone, date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="🏫 Campus Eval Points", page_icon="🏫", layout="wide")

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
.summary-box  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.5rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }
.summary-row  { display:flex; justify-content:space-between; align-items:center; padding:0.3rem 0; border-bottom:1px solid var(--border); }
.summary-row:last-child { border-bottom:none; }
.summary-label { color:var(--muted); font-size:0.75rem; }
.summary-value { font-weight:700; font-size:0.9rem; color:#e2e8f0; }
.summary-total { color:var(--green); font-size:1.1rem; }
.section-title { font-family:'JetBrains Mono',monospace; font-size:0.9rem; font-weight:700;
                 color:var(--accent); margin:1.25rem 0 0.6rem 0; letter-spacing:1px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🏫 Campus Eval Points</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Comparativa de correction points — solo students</div>', unsafe_allow_html=True)

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

# ── Require students_df from directory page ───────────────────────────────────
if "students_df" not in st.session_state or st.session_state["students_df"].empty:
    st.warning("⚠️ Ve primero a **Students Directory** y pulsa **Cargar estudiantes**.")
    st.stop()

# Solo kind=student
src_df = st.session_state["students_df"].copy()
src_df = src_df[src_df["Kind"] == "student"].reset_index(drop=True)

st.info(f"✅ {len(src_df)} students cargados desde Students Directory")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏫 Campus Eval Points")
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    st.info(f"📍 **{campus_name}** · {len(src_df)} students")

    date_base = st.date_input("Fecha base (pasado)", value=date(2026, 5, 13))
    debug     = st.checkbox("🐛 Debug", value=False)

    st.markdown("---")
    st.markdown(f"""
    **Fecha base:** {date_base.strftime('%d/%m/%Y')}  
    **Fecha actual:** puntos en API (ahora)  
    Llamará a la API de historial de los **{len(src_df)} students**.  
    ⏱️ Puede tardar varios minutos.
    """)
    calc_btn = st.button("🚀 Calcular comparativa", type="primary", use_container_width=True)

# ── Helper: puntos en fecha ───────────────────────────────────────────────────
def get_pts_on_date(user_id, target_date, headers):
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    page = 1
    while page <= 15:
        url = (
            f"https://api.intra.42.fr/v2/users/{user_id}/correction_point_historics"
            f"?page[size]=100&page[number]={page}&sort=-created_at"
        )
        resp = api_get(url, headers)
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", 5)))
            continue
        if resp.status_code != 200:
            return None
        records = resp.json()
        if not records:
            return None
        for rec in records:
            try:
                dt = datetime.fromisoformat(rec["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            if dt <= end_of_day:
                total = rec.get("total")
                return int(total) if total is not None else None
        try:
            last_dt = datetime.fromisoformat(
                records[-1]["created_at"].replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except Exception:
            break
        if last_dt <= end_of_day or len(records) < 100:
            break
        page += 1
    return None

# ── Render summary (same style as students directory) ─────────────────────────
def render_summary(df, title):
    total = int(df["Eval Points"].sum())
    avg   = df["Eval Points"].mean()
    mx    = int(df["Eval Points"].max())
    mn    = int(df["Eval Points"].min())
    top   = df.loc[df["Eval Points"].idxmax(), "Login"]

    st.markdown(f'<div class="section-title">💰 {title}</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="summary-box">
      <div class="summary-row">
        <span class="summary-label">TOTAL PUNTOS</span>
        <span class="summary-value summary-total">{total:,}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">MEDIA POR ESTUDIANTE</span>
        <span class="summary-value">{avg:.1f} pts</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">MÁXIMO</span>
        <span class="summary-value">{mx} pts — {top}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">MÍNIMO</span>
        <span class="summary-value">{mn} pts</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><b style='color:#e2e8f0;font-family:JetBrains Mono,monospace;font-size:0.8rem'>POR GRADE</b>", unsafe_allow_html=True)
    for _, row in (
        df.groupby("Grade")["Eval Points"]
        .agg(["sum", "mean", "count"])
        .reset_index()
        .sort_values("sum", ascending=False)
        .iterrows()
    ):
        st.markdown(
            f'<div class="summary-box"><div class="summary-row">'
            f'<span class="summary-label">{row["Grade"]} &nbsp;·&nbsp; {int(row["count"])} est.</span>'
            f'<span class="summary-value">Total: {int(row["sum"]):,} pts &nbsp;·&nbsp; Media: {row["mean"]:.1f} pts</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

# ── Calculate ─────────────────────────────────────────────────────────────────
if calc_btn:
    bar    = st.progress(0, text="Procesando usuarios…")
    status = st.empty()
    total  = len(src_df)
    pts_base = {}

    for i, row in src_df.iterrows():
        login   = row["Login"]
        # We need user_id — fetch from API using login
        status.text(f"⏳ {i+1}/{total} — {login}")
        bar.progress((i + 1) / total)

        # Get user_id
        resp = api_get(f"https://api.intra.42.fr/v2/users/{login}", headers)
        if resp.status_code != 200:
            pts_base[login] = None
            continue
        user_id = resp.json().get("id")
        if not user_id:
            pts_base[login] = None
            continue

        pts_base[login] = get_pts_on_date(user_id, date_base, headers)

    bar.empty()
    status.empty()

    src_df["pts_base"] = src_df["Login"].map(pts_base)

    st.session_state["cep_df"]        = src_df
    st.session_state["cep_date_base"] = date_base
    st.success(f"✅ Listo — {len(src_df)} usuarios procesados")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "cep_df" not in st.session_state:
    st.info("👆 Selecciona la fecha base y pulsa **Calcular comparativa**.")
    st.stop()

df        = st.session_state["cep_df"].copy()
date_base = st.session_state["cep_date_base"]

# ── HOY — puntos actuales (ya en src_df como "Eval Points") ──────────────────
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    render_summary(df, f"HOY — EVALUATION POINTS")

# ── FECHA BASE — construir df equivalente con pts_base ───────────────────────
df_base = df.dropna(subset=["pts_base"]).copy()
df_base["Eval Points"] = df_base["pts_base"].astype(int)
no_data = len(df) - len(df_base)

with col2:
    if df_base.empty:
        st.warning("Sin datos históricos para esa fecha.")
    else:
        render_summary(df_base, f"{date_base.strftime('%d/%m/%Y')} — EVALUATION POINTS")
        if no_data > 0:
            st.caption(f"ℹ️ {no_data} usuarios sin historial en esa fecha (no incluidos en la columna base)")

# ── Variación ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">📈 VARIACIÓN</div>', unsafe_allow_html=True)

df_both = df.dropna(subset=["pts_base"]).copy()
df_both["variacion"] = df_both["Eval Points"] - df_both["pts_base"].astype(int)

total_now  = int(df["Eval Points"].sum())
total_base = int(df_both["pts_base"].sum())
diff       = total_now - total_base
sign       = "+" if diff >= 0 else ""
color      = "#00ff88" if diff >= 0 else "#ff4444"

c1, c2, c3, c4 = st.columns(4)
for col, (val, lbl, clr) in zip([c1, c2, c3, c4], [
    (f"{total_base:,}", f"TOTAL {date_base.strftime('%d/%m/%Y')}", "var(--accent)"),
    (f"{total_now:,}",  "TOTAL HOY",                               "var(--accent)"),
    (f"{sign}{diff:,}", "VARIACIÓN",                               color),
    (len(df_both),      "USUARIOS CON DATOS",                      "var(--muted)"),
]):
    col.markdown(
        f'<div class="stat-card"><div class="stat-val" style="color:{clr}">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

# Top movers
st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**📈 Mayores ganancias**")
    for _, row in df_both.nlargest(10, "variacion").iterrows():
        v = int(row["variacion"])
        if v <= 0:
            continue
        st.markdown(
            f'<div class="summary-box"><div class="summary-row">'
            f'<span class="summary-label">{row["Login"]} · {row["Grade"]}</span>'
            f'<span class="summary-value" style="color:#00ff88">+{v} pts</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

with col_b:
    st.markdown("**📉 Mayores pérdidas**")
    for _, row in df_both.nsmallest(10, "variacion").iterrows():
        v = int(row["variacion"])
        if v >= 0:
            continue
        st.markdown(
            f'<div class="summary-box"><div class="summary-row">'
            f'<span class="summary-label">{row["Login"]} · {row["Grade"]}</span>'
            f'<span class="summary-value" style="color:#ff4444">{v} pts</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
export = df_both[["Login", "Grade", "Eval Points", "pts_base", "variacion"]].rename(columns={
    "Eval Points": "Pts hoy",
    "pts_base":    f"Pts {date_base.strftime('%d/%m/%Y')}",
    "variacion":   "Variación",
})
csv = export.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV", csv, "campus_eval_points.csv", "text/csv")
