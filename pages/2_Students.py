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
:root { --accent:#00d4ff; --green:#00ff88; --orange:#ff8c00; --purple:#a855f7; --surface:#161920; --border:#2a2f3d; --muted:#64748b; }
.stApp { background:#0d0f14; }
.page-title { font-family:'JetBrains Mono',monospace; font-size:2rem; font-weight:700; color:var(--accent); }
.page-sub   { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--muted); margin-bottom:1.5rem; }
.stat-card  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem; text-align:center; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:1.8rem; font-weight:700; color:var(--accent); }
.stat-lbl   { font-size:0.65rem; color:var(--muted); margin-top:2px; }
.summary-box { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:1.5rem 2rem; margin-top:0.75rem; font-family:'JetBrains Mono',monospace; }
.summary-title { font-size:1rem; font-weight:700; color:var(--accent); margin-bottom:1rem; }
.summary-row { display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0; border-bottom:1px solid var(--border); }
.summary-row:last-child { border-bottom:none; }
.summary-label { color:var(--muted); font-size:0.8rem; }
.summary-value { font-weight:700; font-size:1rem; color:#e2e8f0; }
.summary-total { color:var(--green); font-size:1.3rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🎓 42 Students Directory</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Cadets · Outercore · Transcender · Alumni — cursus 21</div>', unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
def get_headers():
    if "api_headers" in st.session_state:
        return st.session_state["api_headers"]
    try:
        cid  = st.secrets["api42"]["client_id"]
        csec = st.secrets["api42"]["client_secret"]
        resp = requests.post("https://api.intra.42.fr/oauth/token", data={
            "grant_type":    "client_credentials",
            "client_id":     cid,
            "client_secret": csec,
        }, timeout=10)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            st.session_state["api_headers"] = headers
            return headers
    except Exception as e:
        st.error(f"Auth error: {e}")
    return None

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

    in_campus_only = st.checkbox("🟢 Solo en campus ahora", value=False)
    min_level      = st.slider("Nivel mínimo", 0.0, 21.0, 0.0, 0.5)
    max_pages      = st.number_input("Páginas máx (100 users/página)", 1, 100, 20)
    search_q       = st.text_input("🔍 Buscar login / nombre")
    grade_filter   = st.multiselect(
        "Filtrar por grade",
        ["Cadet", "Outercore", "Transcender", "Alumni"],
        default=["Cadet", "Outercore", "Transcender", "Alumni"]
    )
    debug    = st.checkbox("🐛 Debug", value=False)
    load_btn = st.button("🚀 Cargar estudiantes", type="primary", use_container_width=True)

# ── Grade detection ───────────────────────────────────────────────────────────
def detect_grade(cu: dict) -> str:
    raw_grade = (cu.get("grade") or "").strip()
    if raw_grade:
        return raw_grade  # Cadet, Transcender, Alumni, etc.

    bh  = cu.get("blackholed_at")
    end = cu.get("end_at")

    if not end and not bh:
        return "Outercore"
    if bh:
        return "Blackholed"
    return "Sin grade"

# ── Fetch ─────────────────────────────────────────────────────────────────────
KEEP_GRADES = {"Cadet", "Outercore", "Transcender", "Alumni"}

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

        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            status.warning(f"⏳ Rate limit — esperando {wait}s…")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            status.error(f"❌ Error API {resp.status_code} en página {page}")
            if debug:
                st.write(resp.text)
            break

        data = resp.json()
        if not data:
            break

        for cu in data:
            user = cu.get("user", {})
            if not user:
                continue

            grade = detect_grade(cu)
            if debug:
                st.write(f"{user.get('login')} | kind: {user.get('kind')} | grade: {grade} | bh: {cu.get('blackholed_at')}")
            # Cadet: descartar solo si el blackhole ya ocurrió (fecha pasada)
            if grade == "Cadet" and cu.get("blackholed_at"):
                try:
                    bh_dt = datetime.fromisoformat(
                        cu["blackholed_at"].replace("Z", "+00:00")
                    ).replace(tzinfo=None)
                    if bh_dt < now_utc:
                        continue  # blackhole ya pasó → fuera
                except Exception:
                    pass

            # Solo los grades que nos interesan
            if grade not in KEEP_GRADES:
                continue

            loc        = user.get("location") or ""
            loc_active = bool(loc and loc != "unavailable")

            # Black hole días restantes
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

        status.text(f"📄 Página {page} · {len(results)} estudiantes")
        bar.progress(min(page / max_pages, 1.0))

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()
    return results

# ── Load ──────────────────────────────────────────────────────────────────────
if load_btn:
    with st.spinner("Cargando estudiantes…"):
        rows = fetch_students(campus_id, headers, max_pages, debug)

    if not rows:
        st.warning("⚠️ No se encontraron estudiantes.")
        st.stop()

    df = pd.DataFrame(rows)
    df["Updated"] = pd.to_datetime(df["Updated"], utc=True, errors="coerce").dt.tz_localize(None)
    st.session_state["students_df"] = df
    st.session_state["students_ts"] = datetime.now().strftime("%H:%M:%S")

    if debug:
        st.write("**Grades únicos detectados:**", df["Grade"].value_counts().to_dict())

    st.success(f"✅ {len(df)} estudiantes cargados")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "students_df" not in st.session_state or st.session_state["students_df"].empty:
    st.info("👆 Pulsa **Cargar estudiantes** en el sidebar para empezar.")
    st.stop()

df = st.session_state["students_df"].copy()
ts = st.session_state.get("students_ts", "—")

# ── Filters ───────────────────────────────────────────────────────────────────
if grade_filter:
    df = df[df["Grade"].isin(grade_filter)]
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
    st.warning("No hay estudiantes que coincidan con los filtros.")
    st.stop()

# ── Stats ─────────────────────────────────────────────────────────────────────
grade_counts = df["Grade"].value_counts()

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
for col, (val, lbl) in zip(
    [c1, c2, c3, c4, c5, c6, c7],
    [
        (len(df),                              "TOTAL"),
        ((df["In Campus"] == "🟢").sum(),      "EN CAMPUS"),
        (f"{df['Level'].mean():.1f}",          "NIVEL ⌀"),
        (grade_counts.get("Cadet", 0),         "CADETS"),
        (grade_counts.get("Outercore", 0),     "OUTERCORE"),
        (grade_counts.get("Transcender", 0),   "TRANSCENDER"),
        (grade_counts.get("Alumni", 0),        "ALUMNI"),
    ]
):
    col.markdown(
        f'<div class="stat-card"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

st.markdown(f"<br><small style='color:#64748b'>Última carga: {ts} · {len(df)} estudiantes</small>", unsafe_allow_html=True)
st.markdown("---")

# ── Sort + Table ──────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
sort_col = c1.selectbox("Ordenar por", ["Level", "Login", "Grade", "Eval Points", "Wallet", "Updated"])
sort_asc = c2.checkbox("Ascendente", value=False)
df = df.sort_values(sort_col, ascending=sort_asc, na_position="last")

display_df = df[[
    "Login", "Display Name", "Grade", "Level",
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
    }
)

# ── Eval Points Summary ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Resumen de Evaluation Points")

total_eval = int(df["Eval Points"].sum())
avg_eval   = df["Eval Points"].mean()
max_eval   = int(df["Eval Points"].max())
min_eval   = int(df["Eval Points"].min())
top_user   = df.loc[df["Eval Points"].idxmax(), "Login"] if not df.empty else "—"

st.markdown(f"""
<div class="summary-box">
  <div class="summary-title">💰 Evaluation Points — {len(df)} estudiantes filtrados</div>
  <div class="summary-row">
    <span class="summary-label">TOTAL PUNTOS</span>
    <span class="summary-value summary-total">{total_eval:,}</span>
  </div>
  <div class="summary-row">
    <span class="summary-label">MEDIA POR ESTUDIANTE</span>
    <span class="summary-value">{avg_eval:.1f}</span>
  </div>
  <div class="summary-row">
    <span class="summary-label">MÁXIMO (1 estudiante)</span>
    <span class="summary-value">{max_eval} pts — {top_user}</span>
  </div>
  <div class="summary-row">
    <span class="summary-label">MÍNIMO</span>
    <span class="summary-value">{min_eval} pts</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Desglose por grade
st.markdown("<br>**Desglose por grade:**", unsafe_allow_html=True)
eval_by_grade = df.groupby("Grade")["Eval Points"].agg(["sum", "mean", "count"]).reset_index()
eval_by_grade = eval_by_grade.sort_values("sum", ascending=False)

for _, row in eval_by_grade.iterrows():
    g     = row["Grade"]
    total = int(row["sum"])
    avg   = row["mean"]
    count = int(row["count"])
    st.markdown(
        f'<div class="summary-box">'
        f'<div class="summary-row">'
        f'<span class="summary-label">{g} ({count} estudiantes)</span>'
        f'<span class="summary-value">Total: {total:,} pts &nbsp;·&nbsp; Media: {avg:.1f} pts</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV", csv, "42_students.csv", "text/csv")
