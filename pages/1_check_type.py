import streamlit as st
import requests
import time
from collections import Counter
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Unique States Scanner", page_icon="🔍", layout="wide")

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
.summary-box  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.5rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }
.summary-row  { display:flex; justify-content:space-between; align-items:center; padding:0.3rem 0; border-bottom:1px solid var(--border); }
.summary-row:last-child { border-bottom:none; }
.summary-label { color:var(--muted); font-size:0.75rem; }
.summary-value { font-weight:700; font-size:0.9rem; color:#e2e8f0; }
.warn-box { background:#2a1414; border:1px solid var(--red); border-radius:8px; padding:1rem 1.5rem; margin-top:0.6rem; font-family:'JetBrains Mono',monospace; color:var(--red); }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🔍 Unique States Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Escanea la API sin filtros y saca todos los valores reales de grade / kind / active?</div>', unsafe_allow_html=True)

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
    st.markdown("### 🔍 Scan settings")

    campus_id = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    scope = st.radio("Alcance", ["Solo este campus", "Todos los campus"], index=0)
    st.info(f"📍 **{campus_name}** (ID {campus_id})" if scope == "Solo este campus" else "🌍 Todos los campus")

    cursus_id = st.number_input("Cursus ID", value=21, min_value=1)
    max_pages = st.number_input("Páginas máx (100/pág)", 1, 1000, 200)
    debug     = st.checkbox("🐛 Debug (mostrar URLs)", value=False)

    scan_btn = st.button("🚀 Escanear estados únicos", type="primary", use_container_width=True)

# ── Known values that your app currently filters on ───────────────────────────
KEEP_GRADES = {"Cadet", "Outercore", "Transcender", "Alumni", "Blackholed"}

# ── Scan function with progress bar ────────────────────────────────────────────
def scan_unique_states(campus_id, scope, cursus_id, headers, max_pages, debug):
    grade_counter = Counter()
    kind_counter  = Counter()
    active_counter = Counter()
    end_bh_counter = Counter()
    empty_grade_examples = []

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
            grade_counter[raw_grade if raw_grade else "(vacío/null)"] += 1

            kind_counter[user.get("kind", "(sin kind)")] += 1
            active_counter[str(user.get("active?", "(sin campo)"))] += 1

            has_end = bool(cu.get("end_at"))
            has_bh  = bool(cu.get("blackholed_at"))
            end_bh_counter[f"end_at={has_end} / blackholed_at={has_bh}"] += 1

            if not raw_grade and len(empty_grade_examples) < 10:
                empty_grade_examples.append(user.get("login", "?"))

        status.text(f"📄 Página {page} · {total} registros escaneados")
        bar.progress(min(page / max_pages, 1.0), text=f"Página {page}/{max_pages} · {total} registros")

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()

    return {
        "total": total,
        "grade": grade_counter,
        "kind": kind_counter,
        "active": active_counter,
        "end_bh": end_bh_counter,
        "empty_grade_examples": empty_grade_examples,
    }

# ── Run scan ────────────────────────────────────────────────────────────────
if scan_btn:
    result = scan_unique_states(campus_id, scope, cursus_id, headers, max_pages, debug)
    st.session_state["scan_result"] = result
    st.session_state["scan_ts"] = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ Escaneo completo — {result['total']} registros analizados")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "scan_result" not in st.session_state:
    st.info("👆 Pulsa **Escanear estados únicos** en el sidebar para empezar.")
    st.stop()

result = st.session_state["scan_result"]
ts = st.session_state.get("scan_ts", "—")

st.markdown(f"<small style='color:var(--muted)'>Último escaneo: {ts} · {result['total']} registros</small>", unsafe_allow_html=True)

# ── Results: grade ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🎓 VALORES ÚNICOS DE "grade"</div>', unsafe_allow_html=True)
for val, count in result["grade"].most_common():
    st.markdown(
        f'<div class="summary-box"><div class="summary-row">'
        f'<span class="summary-label">{val}</span>'
        f'<span class="summary-value">{count:,}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

missing = set(result["grade"].keys()) - KEEP_GRADES - {"(vacío/null)"}
if missing:
    st.markdown(
        f'<div class="warn-box">🚨 Estos valores de grade existen en la API pero tu KEEP_GRADES actual '
        f'los está IGNORANDO: <b>{", ".join(sorted(missing))}</b></div>',
        unsafe_allow_html=True
    )
else:
    st.success("✅ No hay valores de grade fuera de tu KEEP_GRADES (aparte de vacíos).")

# ── Results: kind ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">👤 VALORES ÚNICOS DE "kind"</div>', unsafe_allow_html=True)
for val, count in result["kind"].most_common():
    st.markdown(
        f'<div class="summary-box"><div class="summary-row">'
        f'<span class="summary-label">{val}</span>'
        f'<span class="summary-value">{count:,}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

# ── Results: active? ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🟢 VALORES ÚNICOS DE "active?"</div>', unsafe_allow_html=True)
for val, count in result["active"].most_common():
    st.markdown(
        f'<div class="summary-box"><div class="summary-row">'
        f'<span class="summary-label">{val}</span>'
        f'<span class="summary-value">{count:,}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

# ── Results: end_at / blackholed_at ────────────────────────────────────────────
st.markdown('<div class="section-title">🕳️ COMBINACIONES end_at / blackholed_at</div>', unsafe_allow_html=True)
for val, count in result["end_bh"].most_common():
    st.markdown(
        f'<div class="summary-box"><div class="summary-row">'
        f'<span class="summary-label">{val}</span>'
        f'<span class="summary-value">{count:,}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

if result["empty_grade_examples"]:
    st.markdown(
        f"<br><small style='color:var(--muted)'>Ejemplos de logins con grade vacío: "
        f"{', '.join(result['empty_grade_examples'])}</small>",
        unsafe_allow_html=True
    )
