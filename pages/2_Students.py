import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="42 Students Directory",
    page_icon="🎓",
    layout="wide",
)

# ── Styles ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@400;600;700&display=swap');

:root {
    --bg: #0d0f14;
    --surface: #161920;
    --border: #2a2f3d;
    --accent: #00d4ff;
    --green: #00ff88;
    --orange: #ff8c00;
    --purple: #a855f7;
    --text: #e2e8f0;
    --muted: #64748b;
}

.stApp { background: var(--bg); }

.page-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -1px;
    margin-bottom: 0.25rem;
}
.page-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 2rem;
}

.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
}
.stat-val { font-size: 2rem; font-weight: 700; color: var(--accent); }
.stat-lbl { font-size: 0.7rem; color: var(--muted); margin-top: 2px; }

.grade-cadet   { background:#00ff8822; color:#00ff88; border:1px solid #00ff8855; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-family:'JetBrains Mono',monospace; }
.grade-member  { background:#00d4ff22; color:#00d4ff; border:1px solid #00d4ff55; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-family:'JetBrains Mono',monospace; }
.grade-alumni  { background:#a855f722; color:#a855f7; border:1px solid #a855f755; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-family:'JetBrains Mono',monospace; }
.grade-other   { background:#ff8c0022; color:#ff8c00; border:1px solid #ff8c0055; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-family:'JetBrains Mono',monospace; }

.loc-active { color: #00ff88; font-weight: 700; }
.loc-none   { color: var(--muted); }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">🎓 42 Students Directory</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">kind: student · grade: Cadet / Member / Alumni</div>', unsafe_allow_html=True)

# ── Auth check ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_token(client_id, client_secret):
    resp = requests.post("https://api.intra.42.fr/oauth/token", data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }, timeout=10)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None

def get_headers():
    """Get auth headers, reusing token from main app session if available."""
    # Try to reuse token from sidebar/session
    if "api_headers" in st.session_state:
        return st.session_state["api_headers"]
    # Otherwise build from secrets
    try:
        cid = st.secrets["api42"]["client_id"]
        csec = st.secrets["api42"]["client_secret"]
        token = get_token(cid, csec)
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            st.session_state["api_headers"] = headers
            return headers
    except Exception:
        pass
    return None

# ── API helpers ───────────────────────────────────────────────────────────────
VALID_GRADES = {"cadet", "member", "outercore", "alumni"}
CURSUS_42 = 21  # cursus_id for the main 42 cursus

def fetch_students(campus_id: int, headers: dict, max_pages: int, debug: bool):
    """Fetch all kind=student users from campus, filter by grade."""
    all_users = []
    page = 1
    bar = st.progress(0, text="Fetching students…")
    status = st.empty()

    while page <= max_pages:
        url = (
            f"https://api.intra.42.fr/v2/campus/{campus_id}/users"
            f"?filter[kind]=student"
            f"&page[size]=100&page[number]={page}"
            f"&sort=-updated_at"
        )
        if debug:
            st.code(url)

        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            status.warning(f"⏳ Rate limit — waiting {wait}s…")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            status.error(f"❌ API error {resp.status_code} on page {page}")
            break

        data = resp.json()
        if not data:
            break

        # Filter: must have a 42cursus entry with a valid grade
        for user in data:
            cursus_users = user.get("cursus_users", [])
            for cu in cursus_users:
                grade = (cu.get("grade") or "").lower()
                cid_check = cu.get("cursus_id")
                if cid_check == CURSUS_42 and grade in VALID_GRADES:
                    user["_grade"] = cu.get("grade", "")
                    user["_level"] = round(float(cu.get("level", 0)), 2)
                    user["_blackholed_at"] = cu.get("blackholed_at")
                    user["_begin_at"] = cu.get("begin_at")
                    all_users.append(user)
                    break  # only add once

        status.text(f"📄 Page {page} · {len(all_users)} students collected")
        bar.progress(min(page / max_pages, 1.0), text=f"Page {page}/{max_pages}")

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()
    return all_users

def build_df(users):
    rows = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for u in users:
        # Location
        loc = u.get("location") or ""
        loc_active = bool(loc and loc != "unavailable")

        # Black hole days remaining
        bh = u.get("_blackholed_at")
        bh_days = None
        if bh:
            try:
                bh_dt = datetime.fromisoformat(bh.replace("Z", "+00:00")).replace(tzinfo=None)
                bh_days = (bh_dt - now).days
            except Exception:
                pass

        rows.append({
            "Login":        u.get("login", ""),
            "Display Name": u.get("displayname", ""),
            "Grade":        u.get("_grade", ""),
            "Level":        u.get("_level", 0.0),
            "Location":     loc if loc_active else "—",
            "In Campus":    "🟢" if loc_active else "⚪",
            "Wallet":       u.get("wallet", 0),
            "Eval Points":  u.get("correction_point", 0),
            "Pool":         f"{u.get('pool_month','') or ''} {u.get('pool_year','') or ''}".strip(),
            "Black Hole":   bh_days,
            "Updated":      u.get("updated_at", ""),
            "_image":       (u.get("image") or {}).get("versions", {}).get("small", ""),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Updated"] = pd.to_datetime(df["Updated"], utc=True, errors="coerce").dt.tz_localize(None)
    return df

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎓 Students Filter")

    # Campus selector — reuse from session if available
    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")

    st.info(f"📍 Campus: **{campus_name}** (ID {campus_id})")

    grade_filter = st.multiselect(
        "Grade",
        ["Cadet", "Member", "Outercore", "Alumni"],
        default=["Cadet", "Member", "Outercore", "Alumni"],
    )

    in_campus_only = st.checkbox("🟢 In campus only", value=False)
    min_level = st.slider("Min level", 0.0, 21.0, 0.0, 0.5)

    max_pages = st.number_input("Max pages to fetch (100 users/page)", 1, 100, 20)

    search_q = st.text_input("🔍 Search login / name")

    debug = st.checkbox("🐛 Debug mode", value=False)

    load_btn = st.button("🚀 Load Students", type="primary", use_container_width=True)

# ── Main content ──────────────────────────────────────────────────────────────
headers = get_headers()

if not headers:
    st.error("❌ No auth headers found. Make sure your secrets or sidebar token is configured.")
    st.stop()

if load_btn or ("students_df" not in st.session_state):
    if load_btn:
        with st.spinner("Loading students from 42 API…"):
            raw = fetch_students(campus_id, headers, max_pages, debug)
            st.session_state["students_df"]  = build_df(raw)
            st.session_state["students_raw"] = raw
            st.session_state["students_ts"]  = datetime.now().strftime("%H:%M:%S")
        st.success(f"✅ {len(st.session_state['students_df'])} students loaded")

# Show data if available
if "students_df" in st.session_state:
    df: pd.DataFrame = st.session_state["students_df"].copy()
    ts = st.session_state.get("students_ts", "—")

    # ── Apply filters ─────────────────────────────────────────────────────
    if grade_filter:
        df = df[df["Grade"].isin(grade_filter)]
    if in_campus_only:
        df = df[df["In Campus"] == "🟢"]
    if min_level > 0:
        df = df[df["Level"] >= min_level]
    if search_q:
        q = search_q.lower()
        df = df[df["Login"].str.lower().str.contains(q) | df["Display Name"].str.lower().str.contains(q)]

    # ── Stats ─────────────────────────────────────────────────────────────
    total        = len(df)
    in_campus    = (df["In Campus"] == "🟢").sum()
    avg_level    = df["Level"].mean() if total else 0
    cadets       = (df["Grade"] == "Cadet").sum()
    members      = (df["Grade"] == "Member").sum()
    outercore    = (df["Grade"] == "Outercore").sum()
    alumni       = (df["Grade"] == "Alumni").sum()

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    for col, val, lbl in [
        (c1, total,           "TOTAL"),
        (c2, in_campus,       "IN CAMPUS"),
        (c3, f"{avg_level:.1f}", "AVG LEVEL"),
        (c4, cadets,          "CADETS"),
        (c5, members,         "MEMBERS"),
        (c6, outercore,       "OUTERCORE"),
        (c7, alumni,          "ALUMNI"),
    ]:
        col.markdown(f'<div class="stat-card"><div class="stat-val">{val}</div><div class="stat-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown(f"<br><small style='color:#64748b'>Last load: {ts} · {total} students shown</small>", unsafe_allow_html=True)
    st.markdown("---")

    # ── Sort ──────────────────────────────────────────────────────────────
    sort_col = st.selectbox("Sort by", ["Level", "Login", "Updated", "Eval Points", "Wallet"], index=0)
    sort_asc  = st.checkbox("Ascending", value=False)
    df = df.sort_values(sort_col, ascending=sort_asc, na_position="last")

    # ── Table ─────────────────────────────────────────────────────────────
    display_df = df[[
        "Login", "Display Name", "Grade", "Level",
        "In Campus", "Location", "Eval Points", "Wallet",
        "Pool", "Black Hole", "Updated"
    ]].copy()

    display_df["Updated"] = display_df["Updated"].dt.strftime("%Y-%m-%d %H:%M").fillna("—")
    display_df["Black Hole"] = display_df["Black Hole"].apply(
        lambda x: f"⚠️ {int(x)}d" if pd.notna(x) and x < 30 else (f"{int(x)}d" if pd.notna(x) else "—")
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Level":      st.column_config.ProgressColumn("Level", min_value=0, max_value=21, format="%.2f"),
            "Grade":      st.column_config.TextColumn("Grade", width="small"),
            "In Campus":  st.column_config.TextColumn("📍", width="small"),
            "Black Hole": st.column_config.TextColumn("⏳ BH", width="small"),
        },
        height=600,
    )

    # ── Export ────────────────────────────────────────────────────────────
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export CSV", csv, "42_students.csv", "text/csv")

else:
    st.info("👆 Click **Load Students** in the sidebar to fetch the directory.")
    st.markdown("""
    **What this page shows:**
    - All users with `kind = student`
    - Filtered to those enrolled in the **42 main cursus** (cursus_id 21)
    - With grade: **Cadet**, **Member**, **Outercore** or **Alumni**
    """)