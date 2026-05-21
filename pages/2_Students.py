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
.summary-box  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.5rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }
.summary-row  { display:flex; justify-content:space-between; align-items:center; padding:0.3rem 0; border-bottom:1px solid var(--border); }
.summary-row:last-child { border-bottom:none; }
.summary-label { color:var(--muted); font-size:0.75rem; }
.summary-value { font-weight:700; font-size:0.9rem; color:#e2e8f0; }
.summary-total { color:var(--green); font-size:1.1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🎓 42 Students Directory</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Cadets · Outercore · Transcender · Alumni · Blackholed — cursus 21</div>', unsafe_allow_html=True)

# ── Auth con auto-renovación ──────────────────────────────────────────────────
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
    expired  = not token_ts or (now - token_ts).total_seconds() > 5400  # 90 min

    if force or expired or "api_headers" not in st.session_state:
        token = get_token()
        if not token:
            return None
        st.session_state["api_headers"] = {"Authorization": f"Bearer {token}"}
        st.session_state["token_ts"]    = now

    return st.session_state["api_headers"]

def api_get(url, headers):
    """GET con re-intento automático si el token expiró."""
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code == 401:
        headers = get_headers(force=True)
        if headers:
            resp = requests.get(url, headers=headers, timeout=20)
    return resp

headers = get_headers()
if not headers:
    st.error("❌ No se pudo autenticar con la API de 42. Revisa los secrets.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎓 Students Filter")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    st.info(f"📍 **{campus_name}** (ID {campus_id})")

    grade_filter = st.multiselect(
        "Grade",
        ["Cadet", "Outercore", "Transcender", "Alumni", "Blackholed"],
        default=["Cadet", "Outercore", "Transcender", "Alumni", "Blackholed"]
    )
    kind_filter = st.multiselect(
        "Kind",
        ["student", "admin", "external"],
        default=["student", "admin", "external"]
    )
    in_campus_only = st.checkbox("🟢 Solo en campus ahora", value=False)
    min_level      = st.slider("Nivel mínimo", 0.0, 21.0, 0.0, 0.5)
    max_pages      = st.number_input("Páginas máx (100/pág)", 1, 100, 20)
    search_q       = st.text_input("🔍 Buscar login / nombre")
    debug          = st.checkbox("🐛 Debug", value=False)
    load_btn       = st.button("🚀 Cargar estudiantes", type="primary", use_container_width=True)

# ── Grade detection ───────────────────────────────────────────────────────────
def detect_grade(cu: dict, now_utc: datetime) -> str:
    raw = (cu.get("grade") or "").strip()
    bh  = cu.get("blackholed_at")

    # Si tiene blackholed_at en el pasado → Blackholed, independientemente del grade
    if bh:
        try:
            bh_dt = datetime.fromisoformat(bh.replace("Z", "+00:00")).replace(tzinfo=None)
            if bh_dt < now_utc:
                return "Blackholed"
        except Exception:
            pass

    if raw:
        return raw  # Cadet, Transcender, Alumni

    end = cu.get("end_at")
    if not end and not bh:
        return "Outercore"

    return "Sin grade"

# ── Fetch ─────────────────────────────────────────────────────────────────────
KEEP_GRADES = {"Cadet", "Outercore", "Transcender", "Alumni", "Blackholed"}

def fetch_students(campus_id, headers, max_pages, debug):
    results = []
    bar     = st.progress(0, text="Cargando…")
    status  = st.empty()
    page    = 1
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    while page <= max_pages:
        url = (
            f"https://api.intra.42.fr/v2/cursus/21/cursus_users"
            f"?filter[campus_id]={campus_id}"
            f"&page[size]=100&page[number]={page}"
            f"&sort=-updated_at"
        )

        if debug:
            st.code(url)

        resp = api_get(url, headers)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            status.warning(f"⏳ Rate limit — esperando {wait}s…")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            status.error(f"❌ Error API {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        if not data:
            break

        for cu in data:
            user = cu.get("user", {})
            if not user:
                continue

            grade = detect_grade(cu, now_utc)

            if grade not in KEEP_GRADES:
                continue

            loc        = user.get("location") or ""
            loc_active = bool(loc and loc != "unavailable")

            bh = cu.get("blackholed_at")
            bh_days = None
            if bh:
                try:
                    bh_dt   = datetime.fromisoformat(bh.replace("Z", "+00:00")).replace(tzinfo=None)
                    bh_days = (bh_dt - now_utc).days
                except Exception:
                    pass

            results.append({
                "Login":        user.get("login", ""),
                "Display Name": user.get("displayname", ""),
                "Kind":         user.get("kind", ""),
                "Grade":        grade,
                "Level":        round(float(cu.get("level", 0)), 2),
                "In Campus":    "🟢" if loc_active else "⚪",
                "Location":     loc if loc_active else "—",
                "Eval Points":  int(user.get("correction_point", 0) or 0),
                "Wallet":       int(user.get("wallet", 0) or 0),
                "Pool":         f"{user.get('pool_month','') or ''} {user.get('pool_year','') or ''}".strip(),
                "Black Hole":   bh_days,
                "Updated":      cu.get("updated_at", ""),
            })

        status.text(f"📄 Página {page} · {len(results)} registros")
        bar.progress(min(page / max_pages, 1.0))

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()
    return results

# ── Load ──────────────────────────────────────────────────────────────────────
if load_btn:
    with st.spinner("Cargando…"):
        rows = fetch_students(campus_id, headers, max_pages, debug)

    if not rows:
        st.warning("⚠️ No se encontraron estudiantes. Revisa el debug para más info.")
        st.stop()

    df = pd.DataFrame(rows)
    df["Updated"] = pd.to_datetime(df["Updated"], utc=True, errors="coerce").dt.tz_localize(None)
    st.session_state["students_df"] = df
    st.session_state["students_ts"] = datetime.now().strftime("%H:%M:%S")

    if debug:
        st.write("**Grades:**", df["Grade"].value_counts().to_dict())
        st.write("**Kinds:**",  df["Kind"].value_counts().to_dict())

    st.success(f"✅ {len(df)} registros cargados")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "students_df" not in st.session_state or st.session_state["students_df"].empty:
    st.info("👆 Pulsa **Cargar estudiantes** en el sidebar para empezar.")
    st.stop()

df = st.session_state["students_df"].copy()
ts = st.session_state.get("students_ts", "—")

# ── Apply filters ─────────────────────────────────────────────────────────────
if grade_filter:
    df = df[df["Grade"].isin(grade_filter)]
if kind_filter:
    df = df[df["Kind"].isin(kind_filter)]
if in_campus_only:
    df = df[df["In Campus"] == "🟢"]
if min_level > 0:
    df = df[df["Level"] >= min_level]
if search_q:
    q = search_q.lower()
    df = df[
        df["Login"].str.lower().str.contains(q, na=False) |
        df["Display Name"].str.lower().str.contains(q, na=False)
    ]

if df.empty:
    st.warning("No hay registros que coincidan con los filtros.")
    st.stop()

gc = df["Grade"].value_counts()
kc = df["Kind"].value_counts()

# ── Stats por grade ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 POR GRADE</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
for col, (val, lbl) in zip(
    [c1, c2, c3, c4, c5, c6, c7, c8],
    [
        (len(df),                      "TOTAL"),
        ((df["In Campus"]=="🟢").sum(),"EN CAMPUS"),
        (f"{df['Level'].mean():.1f}",  "NIVEL ⌀"),
        (gc.get("Cadet", 0),           "CADETS"),
        (gc.get("Outercore", 0),       "OUTERCORE"),
        (gc.get("Transcender", 0),     "TRANSCENDER"),
        (gc.get("Alumni", 0),          "ALUMNI"),
        (gc.get("Blackholed", 0),      "BLACKHOLED"),
    ]
):
    col.markdown(
        f'<div class="stat-card"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

# ── Stats por kind ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">👤 POR KIND</div>', unsafe_allow_html=True)
kind_cols = st.columns(max(len(kc), 1))
colors = {"student": "#00ff88", "admin": "#ff8c00", "external": "#a855f7"}
for col, (k, v) in zip(kind_cols, kc.items()):
    color = colors.get(k, "#00d4ff")
    col.markdown(
        f'<div class="stat-card"><div class="stat-val" style="color:{color}">{v}</div>'
        f'<div class="stat-lbl">{k.upper()}</div></div>',
        unsafe_allow_html=True
    )

st.markdown(
    f"<br><small style='color:var(--muted)'>Última carga: {ts} · {len(df)} registros mostrados</small>",
    unsafe_allow_html=True
)
st.markdown("---")

# ── Table ─────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
sort_col = c1.selectbox("Ordenar por", ["Level", "Login", "Grade", "Kind", "Eval Points", "Wallet", "Updated"])
sort_asc = c2.checkbox("Ascendente", value=False)

df_sorted  = df.sort_values(sort_col, ascending=sort_asc, na_position="last")
display_df = df_sorted[[
    "Login", "Display Name", "Kind", "Grade", "Level",
    "In Campus", "Location", "Eval Points", "Wallet",
    "Pool", "Black Hole", "Updated"
]].copy()

display_df["Updated"] = display_df["Updated"].dt.strftime("%Y-%m-%d %H:%M").fillna("—")
display_df["Black Hole"] = display_df["Black Hole"].apply(
    lambda x: f"⚠️ {int(x)}d" if pd.notna(x) and x < 30
    else (f"{int(x)}d" if pd.notna(x) else "—")
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=600,
    column_config={
        "Level":      st.column_config.ProgressColumn("Level", min_value=0, max_value=21, format="%.2f"),
        "In Campus":  st.column_config.TextColumn("📍", width="small"),
        "Black Hole": st.column_config.TextColumn("⏳ BH", width="small"),
        "Grade":      st.column_config.TextColumn("Grade", width="small"),
        "Kind":       st.column_config.TextColumn("Kind",  width="small"),
    }
)

# ── Eval Points Summary ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">💰 EVALUATION POINTS</div>', unsafe_allow_html=True)

total_eval = int(df["Eval Points"].sum())
avg_eval   = df["Eval Points"].mean()
max_eval   = int(df["Eval Points"].max())
min_eval   = int(df["Eval Points"].min())
top_user   = df.loc[df["Eval Points"].idxmax(), "Login"]

st.markdown(f"""
<div class="summary-box">
  <div class="summary-row">
    <span class="summary-label">TOTAL PUNTOS</span>
    <span class="summary-value summary-total">{total_eval:,}</span>
  </div>
  <div class="summary-row">
    <span class="summary-label">MEDIA POR ESTUDIANTE</span>
    <span class="summary-value">{avg_eval:.1f} pts</span>
  </div>
  <div class="summary-row">
    <span class="summary-label">MÁXIMO</span>
    <span class="summary-value">{max_eval} pts — {top_user}</span>
  </div>
  <div class="summary-row">
    <span class="summary-label">MÍNIMO</span>
    <span class="summary-value">{min_eval} pts</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Por grade
st.markdown("<br><b style='color:#e2e8f0;font-family:JetBrains Mono,monospace;font-size:0.8rem'>POR GRADE</b>", unsafe_allow_html=True)
for _, row in df.groupby("Grade")["Eval Points"].agg(["sum","mean","count"]).reset_index().sort_values("sum", ascending=False).iterrows():
    st.markdown(
        f'<div class="summary-box"><div class="summary-row">'
        f'<span class="summary-label">{row["Grade"]} &nbsp;·&nbsp; {int(row["count"])} est.</span>'
        f'<span class="summary-value">Total: {int(row["sum"]):,} pts &nbsp;·&nbsp; Media: {row["mean"]:.1f} pts</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

# Por kind
st.markdown("<br><b style='color:#e2e8f0;font-family:JetBrains Mono,monospace;font-size:0.8rem'>POR KIND</b>", unsafe_allow_html=True)
for _, row in df.groupby("Kind")["Eval Points"].agg(["sum","mean","count"]).reset_index().sort_values("sum", ascending=False).iterrows():
    k     = row["Kind"]
    color = colors.get(k, "#00d4ff")
    st.markdown(
        f'<div class="summary-box"><div class="summary-row">'
        f'<span class="summary-label" style="color:{color}">{k} &nbsp;·&nbsp; {int(row["count"])} est.</span>'
        f'<span class="summary-value">Total: {int(row["sum"]):,} pts &nbsp;·&nbsp; Media: {row["mean"]:.1f} pts</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV", csv, "42_students.csv", "text/csv")
