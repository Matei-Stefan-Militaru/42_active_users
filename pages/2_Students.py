import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Students Directory", page_icon="🎓", layout="wide")

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
:root { --accent:#00d4ff; --green:#00ff88; --surface:#161920; --border:#2a2f3d; --muted:#64748b; }
.stApp { background:#0d0f14; }
.page-title { font-family:'JetBrains Mono',monospace; font-size:2rem; font-weight:700; color:var(--accent); }
.page-sub   { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--muted); margin-bottom:1.5rem; }
.stat-card  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem; text-align:center; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:1.8rem; font-weight:700; color:var(--accent); }
.stat-lbl   { font-size:0.65rem; color:var(--muted); margin-top:2px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🎓 42 Students Directory</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">kind: student · cursus 21 · grade: Cadet / Member / Outercore / Alumni</div>', unsafe_allow_html=True)

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

    grade_filter    = st.multiselect("Grade", ["Cadet", "Member", "Outercore", "Alumni"],
                                     default=["Cadet", "Member", "Outercore", "Alumni"])
    in_campus_only  = st.checkbox("🟢 Solo en campus ahora", value=False)
    min_level       = st.slider("Nivel mínimo", 0.0, 21.0, 0.0, 0.5)
    max_pages       = st.number_input("Páginas máx (100 users/página)", 1, 100, 20)
    search_q        = st.text_input("🔍 Buscar login / nombre")
    debug           = st.checkbox("🐛 Debug", value=False)
    load_btn        = st.button("🚀 Cargar estudiantes", type="primary", use_container_width=True)

# ── Fetch ─────────────────────────────────────────────────────────────────────
VALID_GRADES = {"cadet", "member", "outercore", "alumni"}
CURSUS_42    = 21

def fetch_students(campus_id, headers, max_pages, debug):
    """
    Usa /v2/cursus/21/cursus_users?filter[campus_id]=X
    que devuelve cursus_users con grade incluido directamente.
    """
    results = []
    bar     = st.progress(0, text="Cargando…")
    status  = st.empty()
    page    = 1

    while page <= max_pages:
        url = (
            f"https://api.intra.42.fr/v2/cursus/{CURSUS_42}/cursus_users"
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
            grade = (cu.get("grade") or "").lower()
            if grade not in VALID_GRADES:
                continue

            user = cu.get("user", {})
            if not user:
                continue

            # kind check
            if user.get("kind") != "student":
                continue

            loc = user.get("location") or ""
            loc_active = bool(loc and loc != "unavailable")

            # Black hole
            bh = cu.get("blackholed_at")
            bh_days = None
            if bh:
                try:
                    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                    bh_dt   = datetime.fromisoformat(bh.replace("Z", "+00:00")).replace(tzinfo=None)
                    bh_days = (bh_dt - now_utc).days
                except Exception:
                    pass

            results.append({
                "Login":        user.get("login", ""),
                "Display Name": user.get("displayname", ""),
                "Grade":        cu.get("grade", ""),
                "Level":        round(float(cu.get("level", 0)), 2),
                "In Campus":    "🟢" if loc_active else "⚪",
                "Location":     loc if loc_active else "—",
                "Eval Points":  user.get("correction_point", 0),
                "Wallet":       user.get("wallet", 0),
                "Pool":         f"{user.get('pool_month','') or ''} {user.get('pool_year','') or ''}".strip(),
                "Black Hole":   bh_days,
                "Updated":      cu.get("updated_at", ""),
            })

        status.text(f"📄 Página {page} · {len(results)} estudiantes encontrados")
        bar.progress(min(page / max_pages, 1.0))

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()
    return results

# ── Load data ─────────────────────────────────────────────────────────────────
if load_btn:
    with st.spinner("Cargando estudiantes…"):
        rows = fetch_students(campus_id, headers, max_pages, debug)

    if not rows:
        st.warning("⚠️ No se encontraron estudiantes. Prueba aumentar las páginas o revisa el campus ID.")
        st.stop()

    df = pd.DataFrame(rows)
    df["Updated"] = pd.to_datetime(df["Updated"], utc=True, errors="coerce").dt.tz_localize(None)
    st.session_state["students_df"] = df
    st.session_state["students_ts"] = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ {len(df)} estudiantes cargados")

# ── Display ───────────────────────────────────────────────────────────────────
if "students_df" not in st.session_state or st.session_state["students_df"].empty:
    st.info("👆 Pulsa **Cargar estudiantes** en el sidebar para empezar.")
    st.stop()

df  = st.session_state["students_df"].copy()
ts  = st.session_state.get("students_ts", "—")

# ── Filters ───────────────────────────────────────────────────────────────────
if grade_filter:
    df = df[df["Grade"].isin(grade_filter)]
if in_campus_only:
    df = df[df["In Campus"] == "🟢"]
if min_level > 0:
    df = df[df["Level"] >= min_level]
if search_q:
    q  = search_q.lower()
    df = df[
        df["Login"].str.lower().str.contains(q, na=False) |
        df["Display Name"].str.lower().str.contains(q, na=False)
    ]

if df.empty:
    st.warning("No hay estudiantes que coincidan con los filtros seleccionados.")
    st.stop()

# ── Stats ─────────────────────────────────────────────────────────────────────
cols = st.columns(7)
stats = [
    (len(df),                        "TOTAL"),
    ((df["In Campus"] == "🟢").sum(), "EN CAMPUS"),
    (f"{df['Level'].mean():.1f}",    "NIVEL ⌀"),
    ((df["Grade"] == "Cadet").sum(), "CADETS"),
    ((df["Grade"] == "Member").sum(),"MEMBERS"),
    ((df["Grade"] == "Outercore").sum(), "OUTERCORE"),
    ((df["Grade"] == "Alumni").sum(),"ALUMNI"),
]
for col, (val, lbl) in zip(cols, stats):
    col.markdown(
        f'<div class="stat-card"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

st.markdown(f"<br><small style='color:#64748b'>Última carga: {ts} · {len(df)} estudiantes</small>", unsafe_allow_html=True)
st.markdown("---")

# ── Sort + Table ──────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 1])
sort_col = c1.selectbox("Ordenar por", ["Level", "Login", "Updated", "Eval Points", "Wallet"])
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
    }
)

# ── Export ────────────────────────────────────────────────────────────────────
csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV", csv, "42_students.csv", "text/csv")
