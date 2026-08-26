import streamlit as st
import requests
import time
import json
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Raw — Correction Point Historics", page_icon="🔍", layout="wide")

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
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🔍 Raw — Correction Point Historics</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">GET /v2/users/:user_id/correction_point_historics — para inspeccionar el JSON tal cual lo devuelve la API</div>', unsafe_allow_html=True)

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

def api_get(url, headers, max_retries=3, timeout=30):
    """
    GET con reintentos ante timeout/errores de conexión (backoff 2,4,8s).
    Si el token caducó (401), lo renueva y reintenta.
    Devuelve None si se agotan los reintentos, en vez de lanzar la excepción.
    """
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            return None

        if resp.status_code == 401:
            headers = get_headers(force=True)
            if headers:
                try:
                    resp = requests.get(url, headers=headers, timeout=timeout)
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                    if attempt < max_retries - 1:
                        time.sleep(2 ** (attempt + 1))
                        continue
                    return None

        return resp

    return None

headers = get_headers()
if not headers:
    st.error("❌ No se pudo autenticar. Revisa los secrets.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Query settings")

    user_id_or_login = st.text_input("User ID o login", value="", placeholder="ej: 12345 o jdoe")

    sort_field = st.selectbox(
        "Sort",
        ["(sin ordenar)", "id", "user_id", "scale_team_id", "reason", "sum", "created_at", "updated_at", "total"],
        index=0,
    )
    sort_dir = st.radio("Dirección", ["asc", "desc"], horizontal=True, index=0)

    page_number = st.number_input("page[number]", min_value=1, value=1)
    page_size   = st.number_input("page[size]", min_value=1, max_value=100, value=30)

    st.markdown("---")
    fetch_all = st.checkbox("Traer todas las páginas y concatenar", value=False)
    max_pages = st.number_input("Páginas máx (si 'traer todas')", 1, 200, 20, disabled=not fetch_all)

    debug = st.checkbox("🐛 Mostrar URL exacta", value=True)
    invertir = st.checkbox("🔄 Últimas modificaciones primero (invertir orden)", value=True)

    fetch_btn = st.button("🚀 Fetch raw", type="primary", use_container_width=True)

# ── Build URL ─────────────────────────────────────────────────────────────────
def build_url(uid, page_num, size, sort_field, sort_dir):
    base = f"https://api.intra.42.fr/v2/users/{uid}/correction_point_historics"
    params = [f"page[number]={page_num}", f"page[size]={size}"]
    if sort_field != "(sin ordenar)":
        prefix = "-" if sort_dir == "desc" else ""
        params.append(f"sort={prefix}{sort_field}")
    return base + "?" + "&".join(params)

# ── Fetch ─────────────────────────────────────────────────────────────────────
if fetch_btn:
    if not user_id_or_login.strip():
        st.warning("⚠️ Introduce un user_id o login primero.")
        st.stop()

    uid = user_id_or_login.strip()

    if not fetch_all:
        url = build_url(uid, page_number, page_size, sort_field, sort_dir)
        if debug:
            st.code(url)

        resp = api_get(url, headers)

        if resp is None:
            st.error("❌ Timeout / error de red persistente. Inténtalo de nuevo.")
            st.stop()

        st.session_state["raw_status_code"] = resp.status_code
        st.session_state["raw_headers"]     = dict(resp.headers)
        st.session_state["raw_url"]         = url

        if resp.status_code == 200:
            try:
                st.session_state["raw_data"] = resp.json()
            except Exception:
                st.session_state["raw_data"] = None
                st.session_state["raw_text"] = resp.text
        else:
            st.session_state["raw_data"] = None
            st.session_state["raw_text"] = resp.text

    else:
        all_data = []
        page = 1
        bar    = st.progress(0, text="Escaneando páginas…")
        status = st.empty()
        last_status_code = None
        last_url = None
        last_headers = None

        while page <= max_pages:
            url = build_url(uid, page, page_size, sort_field, sort_dir)
            last_url = url
            if debug:
                st.code(url)

            resp = api_get(url, headers)

            if resp is None:
                status.error(f"❌ Timeout persistente en página {page}. Deteniendo con {len(all_data)} registros recogidos.")
                break

            last_status_code = resp.status_code
            last_headers = dict(resp.headers)

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                status.warning(f"⏳ Rate limit — esperando {wait}s…")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                status.error(f"❌ Error API {resp.status_code}: {resp.text[:300]}")
                break

            data = resp.json()
            if not data:
                break

            all_data.extend(data)
            status.text(f"📄 Página {page} · {len(all_data)} registros acumulados")
            bar.progress(min(page / max_pages, 1.0), text=f"Página {page}/{max_pages}")

            if len(data) < page_size:
                break
            page += 1

        bar.empty()
        status.empty()

        st.session_state["raw_status_code"] = last_status_code
        st.session_state["raw_headers"]     = last_headers
        st.session_state["raw_url"]         = last_url
        st.session_state["raw_data"]        = all_data
        st.session_state.pop("raw_text", None)

# ── Guard ─────────────────────────────────────────────────────────────────────
if "raw_status_code" not in st.session_state:
    st.info("👆 Introduce un user_id/login y pulsa **Fetch raw** en el sidebar.")
    st.stop()

# ── Display ───────────────────────────────────────────────────────────────────
status_code = st.session_state.get("raw_status_code")
resp_headers = st.session_state.get("raw_headers", {})
url_used = st.session_state.get("raw_url", "")

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:{"var(--green)" if status_code == 200 else "var(--red)"}">{status_code}</div><div class="stat-lbl">STATUS CODE</div></div>', unsafe_allow_html=True)

raw_data = st.session_state.get("raw_data")
n_items = len(raw_data) if isinstance(raw_data, list) else (1 if raw_data else 0)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{n_items}</div><div class="stat-lbl">REGISTROS</div></div>', unsafe_allow_html=True)

total_field = resp_headers.get("X-Total", "—")
c3.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--orange)">{total_field}</div><div class="stat-lbl">X-TOTAL (header)</div></div>', unsafe_allow_html=True)

pages_field = resp_headers.get("X-Page", "—")
c4.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--purple)">{pages_field}</div><div class="stat-lbl">X-PAGE (header)</div></div>', unsafe_allow_html=True)

st.markdown("---")

if url_used:
    st.markdown('<div class="section-title">🔗 URL USADA</div>', unsafe_allow_html=True)
    st.code(url_used)

st.markdown('<div class="section-title">📋 RESPONSE HEADERS</div>', unsafe_allow_html=True)
with st.expander("Ver headers completos"):
    st.json(resp_headers)

orden_label = "🔄 más recientes primero" if (invertir and isinstance(raw_data, list)) else "orden original de la API"
st.markdown(f'<div class="section-title">🧾 RAW JSON ({orden_label})</div>', unsafe_allow_html=True)

if raw_data is not None:
    # Por defecto la API devuelve id/created_at ascendente (más antiguo primero).
    # Si "invertir" está marcado, mostramos la lista al revés → últimas modificaciones primero.
    raw_data_mostrado = list(reversed(raw_data)) if (invertir and isinstance(raw_data, list)) else raw_data

    st.json(raw_data_mostrado)

    raw_json_str = json.dumps(raw_data_mostrado, indent=2, ensure_ascii=False)
    st.download_button(
        "⬇️ Descargar raw JSON",
        raw_json_str.encode("utf-8"),
        "correction_point_historics_raw.json",
        "application/json",
    )
else:
    st.markdown('<div class="section-title">⚠️ RESPUESTA NO-JSON / ERROR</div>', unsafe_allow_html=True)
    st.code(st.session_state.get("raw_text", "(sin contenido)"))
