import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="🕳️ Blackholed", page_icon="🕳️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
:root {
    --accent:#00d4ff; --red:#ff4444; --surface:#161920;
    --border:#2a2f3d; --muted:#64748b;
}
.stApp { background:#0d0f14; }
.page-title { font-family:'JetBrains Mono',monospace; font-size:2rem; font-weight:700; color:var(--red); }
.page-sub   { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--muted); margin-bottom:1.5rem; }
.bh-card {
    background:var(--surface);
    border:1px solid #ff444433;
    border-left: 4px solid var(--red);
    border-radius:8px;
    padding:1rem 1.5rem;
    margin-bottom:0.6rem;
    font-family:'JetBrains Mono',monospace;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.bh-login  { font-size:1.1rem; font-weight:700; color:#e2e8f0; }
.bh-name   { font-size:0.75rem; color:var(--muted); margin-top:2px; }
.bh-days   { font-size:2rem; font-weight:700; color:var(--red); text-align:right; }
.bh-days-lbl { font-size:0.65rem; color:var(--muted); text-align:right; }
.bh-date   { font-size:0.75rem; color:#ff8c00; margin-top:4px; text-align:right; }
.stat-card { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem; text-align:center; font-family:'JetBrains Mono',monospace; }
.stat-val  { font-size:1.8rem; font-weight:700; color:var(--red); }
.stat-lbl  { font-size:0.65rem; color:var(--muted); margin-top:2px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🕳️ Blackhole Watch</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Últimos estudiantes que cayeron en el blackhole — cursus 21</div>', unsafe_allow_html=True)

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
    st.markdown("### 🕳️ Blackhole Watch")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    st.info(f"📍 **{campus_name}** (ID {campus_id})")

    top_n    = st.number_input("Mostrar últimos N blackholed", 1, 50, 10)
    max_pages = st.number_input("Páginas máx a escanear", 1, 200, 50)
    debug    = st.checkbox("🐛 Debug", value=False)
    load_btn = st.button("🚀 Cargar blackholed", type="primary", use_container_width=True)

# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_blackholed(campus_id, headers, max_pages, debug):
    results = []
    bar     = st.progress(0, text="Escaneando…")
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
            bh = cu.get("blackholed_at")
            if not bh:
                continue

            try:
                bh_dt = datetime.fromisoformat(bh.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue

            # Solo los que ya cayeron (blackhole en el pasado)
            if bh_dt >= now_utc:
                continue

            user = cu.get("user", {})
            if user.get("active?", True):  # si sigue activo → ignorar
                continue

            days_ago = (now_utc - bh_dt).days

            results.append({
                "Login":        user.get("login", ""),
                "Display Name": user.get("displayname", ""),
                "Kind":         user.get("kind", ""),
                "Level":        round(float(cu.get("level", 0)), 2),
                "Blackholed At": bh_dt,
                "Days Ago":     days_ago,
                "Eval Points":  int(user.get("correction_point", 0) or 0),
                "Wallet":       int(user.get("wallet", 0) or 0),
                "Pool":         f"{user.get('pool_month','') or ''} {user.get('pool_year','') or ''}".strip(),
            })

        status.text(f"📄 Página {page} · {len(results)} blackholed encontrados")
        bar.progress(min(page / max_pages, 1.0))

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()
    return results

# ── Load ──────────────────────────────────────────────────────────────────────
if load_btn:
    with st.spinner("Escaneando blackholed…"):
        rows = fetch_blackholed(campus_id, headers, max_pages, debug)

    if not rows:
        st.warning("⚠️ No se encontraron blackholed.")
        st.stop()

    df = pd.DataFrame(rows)
    df = df.sort_values("Blackholed At", ascending=False)
    st.session_state["bh_df"] = df
    st.session_state["bh_ts"] = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ {len(df)} blackholed encontrados en total")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "bh_df" not in st.session_state or st.session_state["bh_df"].empty:
    st.info("👆 Pulsa **Cargar blackholed** en el sidebar para empezar.")
    st.stop()

df  = st.session_state["bh_df"].copy()
ts  = st.session_state.get("bh_ts", "—")
now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

# Recalcular days_ago en tiempo real
df["Days Ago"] = df["Blackholed At"].apply(lambda x: (now_utc - x).days)

top_df = df.head(top_n)

# ── Stats ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
for col, (val, lbl) in zip(
    [c1, c2, c3, c4],
    [
        (len(df),                                "TOTAL BLACKHOLED"),
        (int(df["Days Ago"].min()),              "DÍAS (MÁS RECIENTE)"),
        (int(df["Days Ago"].max()),              "DÍAS (MÁS ANTIGUO)"),
        (round(df["Level"].mean(), 1),           "NIVEL ⌀"),
    ]
):
    col.markdown(
        f'<div class="stat-card"><div class="stat-val">{val}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

st.markdown(
    f"<br><small style='color:var(--muted)'>Última carga: {ts} · mostrando últimos {top_n} de {len(df)}</small>",
    unsafe_allow_html=True
)
st.markdown("---")

# ── Cards ─────────────────────────────────────────────────────────────────────
st.markdown(f'<div style="font-family:JetBrains Mono,monospace;color:var(--muted);font-size:0.75rem;margin-bottom:0.75rem;">ÚLTIMOS {top_n} BLACKHOLED</div>', unsafe_allow_html=True)

for _, row in top_df.iterrows():
    bh_date_str = row["Blackholed At"].strftime("%Y-%m-%d %H:%M")
    days        = int(row["Days Ago"])
    level       = row["Level"]
    pool        = row["Pool"] or "—"

    st.markdown(f"""
    <div class="bh-card">
        <div>
            <div class="bh-login">{row['Login']}</div>
            <div class="bh-name">{row['Display Name']}</div>
            <div class="bh-name" style="margin-top:6px">
                Nivel: <b style="color:#e2e8f0">{level}</b>
                &nbsp;·&nbsp; Pool: <b style="color:#e2e8f0">{pool}</b>
                &nbsp;·&nbsp; Eval pts: <b style="color:#e2e8f0">{row['Eval Points']}</b>
            </div>
        </div>
        <div>
            <div class="bh-days">{days}</div>
            <div class="bh-days-lbl">días</div>
            <div class="bh-date">{bh_date_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Full table ────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📋 Ver tabla completa"):
    display_df = df.copy()
    display_df["Blackholed At"] = display_df["Blackholed At"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(
        display_df[[
            "Login", "Display Name", "Kind", "Level",
            "Blackholed At", "Days Ago", "Eval Points", "Wallet", "Pool"
        ]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Level":    st.column_config.ProgressColumn("Level", min_value=0, max_value=21, format="%.2f"),
            "Days Ago": st.column_config.NumberColumn("Días", format="%d días"),
        }
    )

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv, "blackholed.csv", "text/csv")
