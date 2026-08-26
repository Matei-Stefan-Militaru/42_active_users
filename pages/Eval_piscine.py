import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MADRID_TZ = ZoneInfo("Europe/Madrid")

POOL_REASONS = {
    "Provided points to the pool.",
    "Provided points to the pool",
}
ROBIN_HOOD_REASONS = {
    "Roobin Hood",
    "Robin Hood",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Eval Piscine — Pool & Robin Hood", page_icon="🏊", layout="wide")

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

st.markdown('<div class="page-title">🏊 Eval Piscine — Pool & Robin Hood</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Escanea los usuarios de la piscine, descarga su historial de puntos de evaluación, y filtra los puntos perdidos (pool y Robin Hood)</div>', unsafe_allow_html=True)

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

def api_get(url, headers, max_retries=3, timeout=30):
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
    st.markdown("### 🏊 Scan settings")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    scope = st.radio("Alcance", ["Solo este campus", "Todos los campus"], index=0)
    st.info(f"📍 **{campus_name}** (ID {campus_id})" if scope == "Solo este campus" else "🌍 Todos los campus")

    cursus_id = st.number_input("Cursus ID (piscine)", value=9, min_value=1, help="9 = Piscine Common Core")
    max_pages = st.number_input("Páginas máx (100/pág)", 1, 1000, 40)
    debug     = st.checkbox("🐛 Debug (mostrar URLs)", value=False)

    scan_btn = st.button("🚀 Escanear piscine + historial", type="primary", use_container_width=True)

# ── Scan: get piscine users + their correction_point_historics ────────────────
def fetch_correction_history(user_id, headers, max_pages_hist=20):
    all_records = []
    page = 1
    while page <= max_pages_hist:
        url = f"https://api.intra.42.fr/v2/users/{user_id}/correction_point_historics?page[number]={page}&page[size]=100&sort=-created_at"
        resp = api_get(url, headers)
        if resp is None:
            break
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        all_records.extend(data)
        if len(data) < 100:
            break
        page += 1
    return all_records

def scan_piscine(campus_id, scope, cursus_id, headers, max_pages, debug):
    users = []
    total = 0
    page  = 1
    base  = f"https://api.intra.42.fr/v2/cursus/{cursus_id}/cursus_users"

    bar    = st.progress(0, text="Escaneando piscine...")
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
            status.warning(f"⏳ Rate limit — esperando {wait}s...")
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
            uid = user.get("id")
            if uid:
                users.append({
                    "user_id":     uid,
                    "Login":       user.get("login", ""),
                    "Display Name": user.get("displayname", ""),
                    "Kind":        user.get("kind", ""),
                    "Level":       round(float(cu.get("level", 0)), 2),
                    "Eval Points": int(user.get("correction_point", 0) or 0),
                })

        status.text(f"Pagina {page} · {total} usuarios escaneados")
        bar.progress(min(page / max_pages, 1.0), text=f"Pagina {page}/{max_pages} · {total} usuarios")

        if len(data) < 100:
            break
        page += 1

    bar.empty()
    status.empty()
    return users

# ── Run scan ────────────────────────────────────────────────────────────────
if scan_btn:
    users = scan_piscine(campus_id, scope, cursus_id, headers, max_pages, debug)
    st.session_state["piscine_users"] = users
    st.session_state["scan_ts"] = datetime.now().strftime("%H:%M:%S")

    if users:
        bar2 = st.progress(0, text="Descargando historiales de puntos...")
        status2 = st.empty()
        all_pool_records = []
        all_robin_records = []
        all_user_records = {}
        processed = 0

        for u in users:
            uid = u["user_id"]
            records = fetch_correction_history(uid, headers)
            processed += 1

            user_pool = []
            user_robin = []
            for r in records:
                reason = (r.get("reason") or "").strip()
                if reason in POOL_REASONS:
                    user_pool.append(r)
                elif reason in ROBIN_HOOD_REASONS:
                    user_robin.append(r)

            all_user_records[uid] = {
                "login": u["Login"],
                "pool_records": user_pool,
                "robin_records": user_robin,
                "pool_sum": sum(r.get("sum", 0) for r in user_pool),
                "robin_sum": sum(r.get("sum", 0) for r in user_robin),
                "total_lost": sum(r.get("sum", 0) for r in user_pool) + sum(r.get("sum", 0) for r in user_robin),
            }
            all_pool_records.extend(user_pool)
            all_robin_records.extend(user_robin)

            bar2.progress(min(processed / len(users), 1.0), text=f"Historial {processed}/{len(users)} usuarios")
            status2.text(f"{u['Login']} — pool: {len(user_pool)} | robin: {len(user_robin)}")

        bar2.empty()
        status2.empty()

        st.session_state["piscine_history"] = all_user_records
        st.session_state["all_pool_records"] = all_pool_records
        st.session_state["all_robin_records"] = all_robin_records
        st.success(f"✅ Listo — {len(users)} usuarios · {len(all_pool_records)} registros pool · {len(all_robin_records)} registros Robin Hood")
    else:
        st.warning("No se encontraron usuarios en la piscine.")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "piscine_users" not in st.session_state:
    st.info("👆 Pulsa **Escanear piscine + historial** en el sidebar para empezar.")
    st.stop()

users_list    = st.session_state["piscine_users"]
history_data  = st.session_state.get("piscine_history", {})
pool_records  = st.session_state.get("all_pool_records", [])
robin_records = st.session_state.get("all_robin_records", [])
ts = st.session_state.get("scan_ts", "—")

st.markdown(f"<small style='color:var(--muted)'>Ultimo escaneo: {ts} · {len(users_list)} usuarios</small>", unsafe_allow_html=True)

# ── Summary stat cards ───────────────────────────────────────────────────────
total_pool_sum  = sum(r.get("sum", 0) for r in pool_records)
total_robin_sum = sum(r.get("sum", 0) for r in robin_records)
total_lost      = total_pool_sum + total_robin_sum
n_users_with_lost = sum(1 for v in history_data.values() if v["total_lost"] < 0)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--red)">{total_lost}</div><div class="stat-lbl">PUNTOS PERDIDOS TOTALES</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--orange)">{total_pool_sum}</div><div class="stat-lbl">POOL (trabajo en equipo)</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--purple)">{total_robin_sum}</div><div class="stat-lbl">ROBIN HOOD</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{n_users_with_lost}</div><div class="stat-lbl">USUARIOS CON PUNTOS PERDIDOS</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ── Table: per-user summary ──────────────────────────────────────────────────
st.markdown(f'<div class="section-title">📋 RESUMEN POR USUARIO</div>', unsafe_allow_html=True)

user_summary = []
for uid, v in history_data.items():
    user_summary.append({
        "Login": v["login"],
        "Pool (puntos)": v["pool_sum"],
        "Pool (registros)": len(v["pool_records"]),
        "Robin Hood (puntos)": v["robin_sum"],
        "Robin Hood (registros)": len(v["robin_records"]),
        "Total perdidos": v["total_lost"],
    })

df_summary = pd.DataFrame(user_summary)
if not df_summary.empty:
    df_summary = df_summary.sort_values("Total perdidos")
    st.dataframe(df_summary, use_container_width=True, hide_index=True)
    csv = df_summary.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (resumen usuarios)", csv, "eval_piscine_resumen.csv", "text/csv")
else:
    st.info("No hay datos de puntos perdidos.")

st.markdown("---")

# ── Pool details ─────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-title">🏊 POOL — "Provided points to the pool." ({len(pool_records)} registros)</div>', unsafe_allow_html=True)
if pool_records:
    df_pool = pd.DataFrame([{
        "Login": history_data.get(r.get("user_id"), {}).get("login", str(r.get("user_id", ""))),
        "Sum": r.get("sum", 0),
        "Total": r.get("total", 0),
        "Reason": r.get("reason", ""),
        "Created At": r.get("created_at", ""),
    } for r in pool_records])
    st.dataframe(df_pool, use_container_width=True, hide_index=True)
    csv_pool = df_pool.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (pool)", csv_pool, "eval_piscine_pool.csv", "text/csv")
else:
    st.info("No hay registros de pool.")

st.markdown("---")

# ── Robin Hood details ───────────────────────────────────────────────────────
st.markdown(f'<div class="section-title">🏹 ROBIN HOOD ({len(robin_records)} registros)</div>', unsafe_allow_html=True)
if robin_records:
    df_robin = pd.DataFrame([{
        "Login": history_data.get(r.get("user_id"), {}).get("login", str(r.get("user_id", ""))),
        "Sum": r.get("sum", 0),
        "Total": r.get("total", 0),
        "Reason": r.get("reason", ""),
        "Created At": r.get("created_at", ""),
    } for r in robin_records])
    st.dataframe(df_robin, use_container_width=True, hide_index=True)
    csv_robin = df_robin.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (Robin Hood)", csv_robin, "eval_piscine_robin_hood.csv", "text/csv")
else:
    st.info("No hay registros de Robin Hood.")
