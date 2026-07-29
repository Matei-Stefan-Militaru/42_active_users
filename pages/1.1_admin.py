import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Grade Vacío / Admins", page_icon="🕵️", layout="wide")

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
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🕵️ Grade vacío / Admins</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Lista quién exactamente cae en (vacío/null) de grade y quién es admin</div>', unsafe_allow_html=True)

# ── Auth (idéntico a tu app) ───────────────────────────────────────────────────
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
    st.markdown("### 🕵️ Scan settings")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    scope = st.radio("Alcance", ["Solo este campus", "Todos los campus"], index=0)
    st.info(f"📍 **{campus_name}** (ID {campus_id})" if scope == "Solo este campus" else "🌍 Todos los campus")

    cursus_id = st.number_input("Cursus ID", value=21, min_value=1)
    max_pages = st.number_input("Páginas máx (100/pág)", 1, 1000, 20)
    debug     = st.checkbox("🐛 Debug (mostrar URLs)", value=False)

    scan_btn = st.button("🚀 Buscar grade vacío / admins", type="primary", use_container_width=True)

# ── Scan function with progress bar ────────────────────────────────────────────
def scan_targets(campus_id, scope, cursus_id, headers, max_pages, debug):
    empty_grade_rows = []
    admin_rows       = []

    total = 0
    page  = 1
    base  = f"https://api.intra.42.fr/v2/cursus/{cursus_id}/cursus_users"

    bar    = st.progress(0, text="Escaneando…")
    status = st.empty()

    while page <= max_pages:
        if scope == "Solo este campus":
            url = f"{base}?filter[campus_id]={campus_id}&page[size]=100&page[number]={page}&sort=-updated_at"
        else:
            url = f"{base}?page[size]=100&page[number]={page}&sort=-updated_at"

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
            user = cu.get("user") or {}
            if not user:
                continue
            total += 1

            raw_grade = (cu.get("grade") or "").strip()
            kind      = user.get("kind", "")

            row = {
                "Login":        user.get("login", ""),
                "Display Name": user.get("displayname", ""),
                "Kind":         kind,
                "Grade (raw)":  raw_grade if raw_grade else "(vacío/null)",
                "Level":        round(float(cu.get("level", 0)), 2),
                "End At":       cu.get("end_at") or "—",
                "Blackholed At": cu.get("blackholed_at") or "—",
                "Updated":      cu.get("updated_at", ""),
            }

            if not raw_grade:
                empty_grade_rows.append(row)

            if kind == "admin":
                admin_rows.append(row)

        status.text(f"📄 Página {page} · {total} registros escaneados")
        bar.progress(min(page / max_pages, 1.0), text=f"Página {page}/{max_pages} · {total} registros")

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()

    return empty_grade_rows, admin_rows

# ── Run scan ────────────────────────────────────────────────────────────────
if scan_btn:
    empty_rows, admin_rows = scan_targets(campus_id, scope, cursus_id, headers, max_pages, debug)
    st.session_state["empty_grade_rows"] = empty_rows
    st.session_state["admin_rows"]       = admin_rows
    st.session_state["scan_ts"]          = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ Escaneo completo — {len(empty_rows)} con grade vacío · {len(admin_rows)} admins")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "empty_grade_rows" not in st.session_state:
    st.info("👆 Pulsa **Buscar grade vacío / admins** en el sidebar para empezar.")
    st.stop()

empty_rows = st.session_state["empty_grade_rows"]
admin_rows = st.session_state["admin_rows"]
ts = st.session_state.get("scan_ts", "—")

st.markdown(f"<small style='color:var(--muted)'>Último escaneo: {ts}</small>", unsafe_allow_html=True)

# ── Grade vacío ─────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-title">🈳 GRADE VACÍO — {len(empty_rows)}</div>', unsafe_allow_html=True)
if empty_rows:
    df_empty = pd.DataFrame(empty_rows)
    st.dataframe(df_empty, use_container_width=True, hide_index=True)
    csv_empty = df_empty.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (grade vacío)", csv_empty, "grade_vacio.csv", "text/csv")
else:
    st.info("No hay registros con grade vacío en este escaneo.")

st.markdown("---")

# ── Admins ────────────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-title">🛡️ ADMINS — {len(admin_rows)}</div>', unsafe_allow_html=True)
if admin_rows:
    df_admin = pd.DataFrame(admin_rows)
    st.dataframe(df_admin, use_container_width=True, hide_index=True)
    csv_admin = df_admin.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (admins)", csv_admin, "admins.csv", "text/csv")
else:
    st.info("No hay admins en este escaneo.")
