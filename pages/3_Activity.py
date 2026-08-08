import streamlit as st
import requests
import time
import json
import sqlite3
import pandas as pd
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Inactividad", page_icon="⏳", layout="wide")

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
.note-box { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:0.9rem 1.2rem; font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--muted); margin-bottom:1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">⏳ Inactividad — Última Entrega</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Estudiantes agrupados por cuánto tiempo llevan sin actividad, con su media de eval points</div>', unsafe_allow_html=True)

# ── Caché local con SQLite ──────────────────────────────────────────────────
# NOTA sobre persistencia: en Streamlit Community Cloud el disco es efímero —
# sobrevive mientras la app esté "despierta", pero se borra si la app se
# duerme por inactividad o si haces un redeploy. Sirve para no re-escanear
# cada vez que cambias de página o recargas dentro de la misma sesión activa,
# pero no es una base de datos permanente entre despliegues. Si necesitas eso,
# lo ideal sería un Postgres/SQLite externo (ej. Supabase, Neon, Turso).
DB_PATH = "inactividad_cache.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            scan_key TEXT PRIMARY KEY,
            scanned_at TEXT,
            data_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_scan(scan_key, rows):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO scans (scan_key, scanned_at, data_json) VALUES (?, ?, ?)",
        (scan_key, datetime.now(timezone.utc).isoformat(), json.dumps(rows)),
    )
    conn.commit()
    conn.close()

def load_scan(scan_key, max_age_hours):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT scanned_at, data_json FROM scans WHERE scan_key = ?", (scan_key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None, None
    scanned_at_raw, data_json = row
    scanned_at = datetime.fromisoformat(scanned_at_raw)
    age_hours = (datetime.now(timezone.utc) - scanned_at).total_seconds() / 3600
    if age_hours > max_age_hours:
        return None, scanned_at
    return json.loads(data_json), scanned_at

init_db()

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
    st.markdown("### ⏳ Scan settings")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    scope = st.radio("Alcance", ["Solo este campus", "Todos los campus"], index=0)
    st.info(f"📍 **{campus_name}** (ID {campus_id})" if scope == "Solo este campus" else "🌍 Todos los campus")

    cursus_id = st.number_input("Cursus ID", value=21, min_value=1)
    max_pages = st.number_input("Páginas máx (100/pág)", 1, 1000, 20)
    solo_estudiantes_validos = st.checkbox(
        "Solo student · Alumni/Transcender/Cadet (sin blackhole)", value=True
    )
    debug = st.checkbox("🐛 Debug (mostrar URLs)", value=False)

    st.markdown("---")
    st.markdown("### 💾 Caché")
    usar_cache = st.checkbox("Usar caché si existe", value=True)
    cache_max_horas = st.number_input("Caché válida por (horas)", 1, 168, 12)

    scan_btn = st.button("🚀 Escanear inactividad", type="primary", use_container_width=True)
    forzar_btn = st.button("🔄 Forzar re-escaneo (ignorar caché)", use_container_width=True)

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
            is_active_field = user.get("active?", True)
            es_blackholeado = (is_active_field is False) and bool(bh_raw)

            updated_raw = cu.get("updated_at")
            updated_dt  = None
            dias_inactivo = None
            if updated_raw:
                try:
                    updated_dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
                    dias_inactivo = (now_utc - updated_dt).days
                except Exception:
                    pass

            rows.append({
                "Login":          user.get("login", ""),
                "Display Name":   user.get("displayname", ""),
                "Kind":           user.get("kind", ""),
                "Grade (raw)":    raw_grade if raw_grade else "(vacío/null)",
                "Blackholeado":   es_blackholeado,
                "Level":          round(float(cu.get("level", 0)), 2),
                "Eval Points":    int(user.get("correction_point", 0) or 0),
                "Updated At":     updated_raw or "—",
                "Días sin actividad": dias_inactivo,
            })

        status.text(f"📄 Página {page} · {total} registros escaneados")
        bar.progress(min(page / max_pages, 1.0), text=f"Página {page}/{max_pages} · {total} registros")

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()

    return rows

# ── Run scan (con caché) ────────────────────────────────────────────────────
scan_key = f"{scope}|{cursus_id}|{campus_id}|{max_pages}"

if forzar_btn:
    rows = scan_targets(campus_id, scope, cursus_id, headers, max_pages, debug)
    save_scan(scan_key, rows)
    st.session_state["inactividad_rows"] = rows
    st.session_state["scan_ts"] = datetime.now().strftime("%H:%M:%S")
    st.session_state["scan_source"] = "API (forzado)"
    st.success(f"✅ Escaneo completo (forzado) — {len(rows)} registros")

elif scan_btn:
    cached_rows, cached_at = (None, None)
    if usar_cache:
        cached_rows, cached_at = load_scan(scan_key, cache_max_horas)

    if cached_rows is not None:
        rows = cached_rows
        st.session_state["inactividad_rows"] = rows
        st.session_state["scan_ts"] = cached_at.strftime("%H:%M:%S %d/%m")
        st.session_state["scan_source"] = "Caché"
        st.info(f"💾 Usando caché guardada a las {cached_at.strftime('%H:%M %d/%m')} ({len(rows)} registros). Pulsa 'Forzar re-escaneo' para actualizar.")
    else:
        rows = scan_targets(campus_id, scope, cursus_id, headers, max_pages, debug)
        save_scan(scan_key, rows)
        st.session_state["inactividad_rows"] = rows
        st.session_state["scan_ts"] = datetime.now().strftime("%H:%M:%S")
        st.session_state["scan_source"] = "API"
        st.success(f"✅ Escaneo completo — {len(rows)} registros (guardado en caché)")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "inactividad_rows" not in st.session_state:
    st.info("👆 Pulsa **Escanear inactividad** en el sidebar para empezar.")
    st.stop()

rows = st.session_state["inactividad_rows"]
ts = st.session_state.get("scan_ts", "—")

df = pd.DataFrame(rows)
df = df[df["Días sin actividad"].notna()]

if solo_estudiantes_validos:
    df = df[
        (df["Kind"] == "student")
        & (df["Grade (raw)"].isin(["Cadet", "Transcender", "Alumni"]))
        & (~df["Blackholeado"])
    ]

st.markdown(f"<small style='color:var(--muted)'>Último escaneo: {ts} · fuente: {st.session_state.get('scan_source', '—')} · {len(df)} estudiantes con fecha de actividad válida</small>", unsafe_allow_html=True)
st.markdown("---")

# ── Categorías de inactividad (umbral: "al menos X tiempo sin actividad") ────
CATEGORIAS = [
    ("1 mes",   30),
    ("2 meses", 60),
    ("3 meses", 90),
    ("4 meses", 120),
    ("5 meses", 150),
    ("6 meses", 180),
    ("1 año",   365),
    ("2 años",  365 * 2),
    ("3 años",  365 * 3),
    ("4 años",  365 * 4),
    ("5 años",  365 * 5),
]

stats_rows = []
for label, dias in CATEGORIAS:
    subset = df[df["Días sin actividad"] >= dias]
    stats_rows.append({
        "Categoría":            label,
        "Días (umbral)":        dias,
        "Nº Estudiantes":       len(subset),
        "Media Eval Points":    round(subset["Eval Points"].mean(), 3) if not subset.empty else 0,
        "Media Level":          round(subset["Level"].mean(), 2) if not subset.empty else 0,
    })

tabla_categorias = pd.DataFrame(stats_rows)

st.markdown('<div class="section-title">📊 ESTADÍSTICAS POR TIEMPO DE INACTIVIDAD</div>', unsafe_allow_html=True)
st.caption("Cada fila cuenta a todos los que llevan AL MENOS ese tiempo sin actividad (no son mutuamente excluyentes — alguien con 2 años sin actividad también está en la fila de 1 año, 6 meses, etc.)")

st.dataframe(
    tabla_categorias,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Nº Estudiantes": st.column_config.NumberColumn("Nº Estudiantes"),
        "Media Eval Points": st.column_config.NumberColumn("Media Eval Points", format="%.3f"),
        "Media Level": st.column_config.NumberColumn("Media Level", format="%.2f"),
    }
)

csv_cat = tabla_categorias.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV (estadísticas por categoría)", csv_cat, "inactividad_categorias.csv", "text/csv")

# ── Detalle opcional: ver quién cae en una categoría concreta ─────────────────
st.markdown("---")
st.markdown('<div class="section-title">🔍 VER ESTUDIANTES DE UNA CATEGORÍA</div>', unsafe_allow_html=True)
categoria_elegida = st.selectbox("Elige categoría", [c[0] for c in CATEGORIAS])
dias_elegidos = dict(CATEGORIAS)[categoria_elegida]

subset_detalle = df[df["Días sin actividad"] >= dias_elegidos][
    ["Login", "Display Name", "Grade (raw)", "Level", "Eval Points", "Días sin actividad", "Updated At"]
].sort_values("Días sin actividad", ascending=False)

st.dataframe(subset_detalle, use_container_width=True, hide_index=True)
csv_detalle = subset_detalle.to_csv(index=False).encode("utf-8")
st.download_button(f"⬇️ Exportar CSV ({categoria_elegida})", csv_detalle, f"inactivos_{categoria_elegida.replace(' ', '_')}.csv", "text/csv")
