import streamlit as st
import requests
import time
import json
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Buscar Usuario (Raw)", page_icon="🔎", layout="wide")

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

st.markdown('<div class="page-title">🔎 Buscar Usuario — Info Raw</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Escanea todos los cursus_users y luego busca uno por login para ver su JSON completo tal cual lo da la API</div>', unsafe_allow_html=True)

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
    st.markdown("### 🔎 Scan settings")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    scope = st.radio("Alcance", ["Solo este campus", "Todos los campus"], index=0)
    st.info(f"📍 **{campus_name}** (ID {campus_id})" if scope == "Solo este campus" else "🌍 Todos los campus")

    cursus_id = st.number_input("Cursus ID", value=21, min_value=1)
    max_pages = st.number_input("Páginas máx (100/pág)", 1, 1000, 20)
    debug     = st.checkbox("🐛 Debug (mostrar URLs)", value=False)

    scan_btn = st.button("🚀 Escanear usuarios", type="primary", use_container_width=True)

# ── Scan function with progress bar (idéntica al resto de tus scripts) ────────
def scan_all_raw(campus_id, scope, cursus_id, headers, max_pages, debug):
    raw_by_login = {}
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
            login = user.get("login")
            if not login:
                continue
            total += 1
            raw_by_login[login.lower()] = cu

        status.text(f"📄 Página {page} · {total} registros escaneados")
        bar.progress(min(page / max_pages, 1.0), text=f"Página {page}/{max_pages} · {total} registros")

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()

    return raw_by_login

# ── Run scan ────────────────────────────────────────────────────────────────
if scan_btn:
    raw_by_login = scan_all_raw(campus_id, scope, cursus_id, headers, max_pages, debug)
    st.session_state["raw_by_login"] = raw_by_login
    st.session_state["scan_ts"] = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ Escaneo completo — {len(raw_by_login)} usuarios indexados")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "raw_by_login" not in st.session_state:
    st.info("👆 Pulsa **Escanear usuarios** en el sidebar para empezar.")
    st.stop()

raw_by_login = st.session_state["raw_by_login"]
ts = st.session_state.get("scan_ts", "—")

st.markdown(f"<small style='color:var(--muted)'>Último escaneo: {ts} · {len(raw_by_login)} usuarios indexados</small>", unsafe_allow_html=True)
st.markdown("---")

# ── Búsqueda de usuario — este campo se queda siempre visible ────────────────
st.markdown('<div class="section-title">🔎 BUSCAR USUARIO</div>', unsafe_allow_html=True)
login_query = st.text_input("Login del estudiante", placeholder="ej: brivasqu", key="login_search")

if login_query:
    match = raw_by_login.get(login_query.strip().lower())
    if match:
        user = match.get("user") or {}
        st.success(f"✅ Encontrado: **{user.get('login', '?')}** — {user.get('displayname', '')}")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card" style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:0.9rem;text-align:center;font-family:JetBrains Mono,monospace"><div style="font-size:1.4rem;font-weight:700;color:var(--accent)">{match.get("grade") or "—"}</div><div style="font-size:0.6rem;color:var(--muted)">GRADE</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:0.9rem;text-align:center;font-family:JetBrains Mono,monospace"><div style="font-size:1.4rem;font-weight:700;color:var(--green)">{round(float(match.get("level", 0)), 2)}</div><div style="font-size:0.6rem;color:var(--muted)">LEVEL</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:0.9rem;text-align:center;font-family:JetBrains Mono,monospace"><div style="font-size:1.4rem;font-weight:700;color:var(--purple)">{user.get("correction_point", "—")}</div><div style="font-size:0.6rem;color:var(--muted)">EVAL POINTS</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card" style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:0.9rem;text-align:center;font-family:JetBrains Mono,monospace"><div style="font-size:1.4rem;font-weight:700;color:{"var(--red)" if user.get("active?") is False else "var(--green)"}">{user.get("active?")}</div><div style="font-size:0.6rem;color:var(--muted)">ACTIVE?</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-title">📄 JSON COMPLETO — cursus_user</div>', unsafe_allow_html=True)
        st.json(match)

        raw_str = json.dumps(match, indent=2, ensure_ascii=False)
        st.download_button("⬇️ Descargar JSON", raw_str, f"{login_query.strip().lower()}_raw.json", "application/json")
    else:
        st.warning(f"⚠️ No se encontró ningún usuario con login `{login_query}` en el escaneo actual. Revisa que esté escrito bien o que esté dentro del alcance/cursus escaneado.")
