import streamlit as st
import requests
import time
import math
import pandas as pd
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Cadets por Nivel", page_icon="🪜", layout="wide")

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

st.markdown('<div class="page-title">🪜 Cadets por Nivel</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Solo Cadets activos (sin futuros, sin blackhole), agrupados en brackets de nivel de 2 en 2</div>', unsafe_allow_html=True)

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
    st.markdown("### 🪜 Scan settings")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    scope = st.radio("Alcance", ["Solo este campus", "Todos los campus"], index=0)
    st.info(f"📍 **{campus_name}** (ID {campus_id})" if scope == "Solo este campus" else "🌍 Todos los campus")

    cursus_id = st.number_input("Cursus ID", value=21, min_value=1)
    max_pages = st.number_input("Páginas máx (100/pág)", 1, 1000, 20)
    debug     = st.checkbox("🐛 Debug (mostrar URLs)", value=False)

    scan_btn = st.button("🚀 Escanear cadets", type="primary", use_container_width=True)

# ── Scan function with progress bar ────────────────────────────────────────────
def scan_targets(campus_id, scope, cursus_id, headers, max_pages, debug):
    rows = []
    total = 0
    page  = 1
    base  = f"https://api.intra.42.fr/v2/cursus/{cursus_id}/cursus_users"
    now_utc = datetime.now(timezone.utc)

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
            bh_raw    = cu.get("blackholed_at")
            end_raw   = cu.get("end_at")
            es_blackholeado = bool(end_raw) and bool(bh_raw)

            begin_raw = cu.get("begin_at")
            begin_dt  = None
            if begin_raw:
                try:
                    begin_dt = datetime.fromisoformat(begin_raw.replace("Z", "+00:00"))
                except Exception:
                    pass
            es_futuro = begin_dt is not None and begin_dt > now_utc

            rows.append({
                "Login":         user.get("login", ""),
                "Display Name":  user.get("displayname", ""),
                "Kind":          user.get("kind", ""),
                "Grade (raw)":   raw_grade if raw_grade else "(vacío/null)",
                "Level":         round(float(cu.get("level", 0)), 2),
                "Eval Points":   int(user.get("correction_point", 0) or 0),
                "Es Futuro":     es_futuro,
                "Blackholeado":  es_blackholeado,
                "Updated":       cu.get("updated_at", ""),
            })

        status.text(f"📄 Página {page} · {total} registros escaneados")
        bar.progress(min(page / max_pages, 1.0), text=f"Página {page}/{max_pages} · {total} registros")

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()

    return rows

# ── Run scan ────────────────────────────────────────────────────────────────
if scan_btn:
    rows = scan_targets(campus_id, scope, cursus_id, headers, max_pages, debug)
    st.session_state["cadets_nivel_rows"] = rows
    st.session_state["scan_ts"] = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ Escaneo completo — {len(rows)} registros")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "cadets_nivel_rows" not in st.session_state:
    st.info("👆 Pulsa **Escanear cadets** en el sidebar para empezar.")
    st.stop()

rows = st.session_state["cadets_nivel_rows"]
ts = st.session_state.get("scan_ts", "—")

df = pd.DataFrame(rows)

# ── Filtro: solo Cadets, kind=student, sin futuros, sin blackhole ────────────
cadets = df[
    (df["Kind"] == "student")
    & (df["Grade (raw)"] == "Cadet")
    & (~df["Es Futuro"])
    & (~df["Blackholeado"])
].copy()

# ── Bracket de nivel, de 2 en 2, tope en nivel 12 (0-1.99, 2-3.99, ..., 12+) ──
STEP      = 2
MAX_LEVEL = 12

def bracket_de_nivel(level, step=STEP, max_level=MAX_LEVEL):
    if level >= max_level:
        return f"{max_level}+"
    inicio = math.floor(level / step) * step
    fin = inicio + step
    return f"{inicio}-{fin - 0.01:.2f}"

def bracket_orden(level, step=STEP, max_level=MAX_LEVEL):
    return min(math.floor(level / step) * step, max_level)

cadets["Nivel (bracket)"] = cadets["Level"].apply(bracket_de_nivel)
cadets["_bracket_orden"]  = cadets["Level"].apply(bracket_orden)

st.markdown(f"<small style='color:var(--muted)'>Último escaneo: {ts} · {len(cadets)} cadets activos (sin futuros, sin blackhole)</small>", unsafe_allow_html=True)
st.markdown("---")

# ── Tabla de estadísticas por bracket ─────────────────────────────────────────
st.markdown('<div class="section-title">📊 ESTADÍSTICAS POR BRACKET DE NIVEL (de 2 en 2, hasta 12)</div>', unsafe_allow_html=True)

stats = (
    cadets.groupby(["_bracket_orden", "Nivel (bracket)"], as_index=False)
    .agg(
        **{
            "Nº Estudiantes": ("Login", "count"),
            "Media Level":    ("Level", "mean"),
            "Media Puntos":   ("Eval Points", "mean"),
        }
    )
    .sort_values("_bracket_orden")
    .drop(columns="_bracket_orden")
    .rename(columns={"Nivel (bracket)": "Bracket de Nivel"})
)

stats["Media Level"]  = stats["Media Level"].round(2)
stats["Media Puntos"] = stats["Media Puntos"].round(2)

# Añadir fila de totales
total_row = pd.DataFrame([{
    "Bracket de Nivel": "TOTAL",
    "Nº Estudiantes":   cadets.shape[0],
    "Media Level":      round(cadets["Level"].mean(), 2) if not cadets.empty else 0,
    "Media Puntos":     round(cadets["Eval Points"].mean(), 2) if not cadets.empty else 0,
}])
stats_con_total = pd.concat([stats, total_row], ignore_index=True)

st.dataframe(
    stats_con_total,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Nº Estudiantes": st.column_config.NumberColumn("Nº Estudiantes"),
        "Media Level":    st.column_config.NumberColumn("Media Level", format="%.2f"),
        "Media Puntos":   st.column_config.NumberColumn("Media Puntos", format="%.2f"),
    }
)

csv_stats = stats.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV (estadísticas por bracket)", csv_stats, "estadisticas_por_bracket.csv", "text/csv")

# ── Detalle completo (opcional, plegado) ──────────────────────────────────────
with st.expander("🪜 Ver detalle de cadets por nivel (tabla completa)"):
    tabla_final = cadets[
        ["Nivel (bracket)", "Login", "Display Name", "Level", "Eval Points", "Updated", "_bracket_orden"]
    ].sort_values(["_bracket_orden", "Level"], ascending=[True, False]).drop(columns="_bracket_orden")

    st.dataframe(
        tabla_final,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Level": st.column_config.ProgressColumn("Level", min_value=0, max_value=21, format="%.2f"),
        }
    )

    csv = tabla_final.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (cadets por nivel, detalle)", csv, "cadets_por_nivel.csv", "text/csv")
