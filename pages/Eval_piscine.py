import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict

MADRID_TZ = ZoneInfo("Europe/Madrid")

POOL_REASONS = {
    "Provided points to the pool.",
    "Provided points to the pool",
}
ROBIN_HOOD_REASONS = {
    "Roobin Hood",
    "Robin Hood",
}
DEFENSE_REASONS = {
    "Defense plannification",
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
st.markdown('<div class="page-sub">Carga los usuarios desde General Data y descarga su historial de puntos para filtrar pool y Robin Hood</div>', unsafe_allow_html=True)

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

# ── Fetch correction point history ────────────────────────────────────────────
def fetch_correction_history(login, headers, since_dt=None, max_pages=20):
    all_records = []
    page = 1
    while page <= max_pages:
        url = f"https://api.intra.42.fr/v2/users/{login}/correction_point_historics?page[number]={page}&page[size]=100&sort=-created_at"
        if since_dt:
            iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            url += f"&range[created_at]={iso},2099-12-31T23:59:59Z"
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

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏊 Settings")
    debug = st.checkbox("🐛 Debug", value=False)

    st.markdown("---")
    filtrar_fecha = st.checkbox("📅 Filtrar por fecha", value=True)
    col_f, col_h = st.columns(2)
    with col_f:
        cutoff_date = st.date_input("Fecha desde", value=datetime(2026, 8, 26).date(), format="DD/MM/YYYY", disabled=not filtrar_fecha)
    with col_h:
        cutoff_time = st.time_input("Hora", value=datetime(2026, 8, 26, 15, 21).time(), disabled=not filtrar_fecha)
    st.caption("Hora local Europe/Madrid")

    max_pages = st.number_input("Páginas máx (100/pág)", 1, 20, 5, help="Máximo de páginas por usuario")

    scan_btn = st.button("🚀 Descargar historiales", type="primary", use_container_width=True)

# ── Check session ─────────────────────────────────────────────────────────────
users_from_session = st.session_state.get("general_data_users")
if not users_from_session:
    st.warning("⚠️ No hay usuarios en memoria. Primero ejecuta un escaneo en General Data.")
    st.stop()

ALLOWED_GRADES = {"Cadet", "Transcender", "Alumni"}

users_blackhole = [u for u in users_from_session if u.get("Blackholeado")]
users_valid     = [u for u in users_from_session if u.get("Grade") in ALLOWED_GRADES and not u.get("Blackholeado")]
users_others    = [u for u in users_from_session if u.get("Grade") not in ALLOWED_GRADES and not u.get("Blackholeado")]

all_groups = [
    ("🕳️ BLACKHOLEADOS", users_blackhole),
    ("🎓 CADET / TRANSCENDER / ALUMNI", users_valid),
    ("👥 RESTO", users_others),
]

st.markdown(f"<small style='color:var(--muted)'>General Data: {len(users_blackhole)} blackholeados · {len(users_valid)} Cadet/Transcender/Alumni · {len(users_others)} resto</small>", unsafe_allow_html=True)

# ── Run ───────────────────────────────────────────────────────────────────────
if scan_btn:
    since_dt = None
    if filtrar_fecha:
        cutoff_naive = datetime.combine(cutoff_date, cutoff_time)
        since_dt = cutoff_naive.replace(tzinfo=MADRID_TZ).astimezone(timezone.utc)

    all_user_records = {}
    all_pool_records = []
    all_robin_records = []
    all_defense_records = []
    processed = 0
    total_calls = 0

    bar = st.progress(0, text="Descargando historiales...")
    status = st.empty()

    for u in users_valid:
        login = u["Login"]
        records = fetch_correction_history(login, headers, since_dt=since_dt, max_pages=max_pages)
        processed += 1
        total_calls += 1

        user_pool = []
        user_robin = []
        user_defense = []
        for r in records:
            reason = (r.get("reason") or "").strip()
            if reason in POOL_REASONS:
                user_pool.append(r)
            elif reason in ROBIN_HOOD_REASONS:
                user_robin.append(r)
            elif reason in DEFENSE_REASONS:
                user_defense.append(r)

        all_user_records[login] = {
            "Grade": u.get("Grade", ""),
            "Blackholeado": u.get("Blackholeado", False),
            "pool_records": user_pool,
            "robin_records": user_robin,
            "defense_records": user_defense,
            "pool_sum": sum(r.get("sum", 0) for r in user_pool),
            "robin_sum": sum(r.get("sum", 0) for r in user_robin),
            "defense_sum": sum(r.get("sum", 0) for r in user_defense),
            "total_lost": sum(r.get("sum", 0) for r in user_pool) + sum(r.get("sum", 0) for r in user_robin),
        }
        all_pool_records.extend(user_pool)
        all_robin_records.extend(user_robin)
        for dr in user_defense:
            all_defense_records.append({"login": login, "record": dr})

        bar.progress(min(processed / len(users_valid), 1.0), text=f"Historial {processed}/{len(users_valid)}")
        status.text(f"{login} — pool: {len(user_pool)} | robin: {len(user_robin)}")

    bar.empty()
    status.empty()

    st.session_state["eval_history"] = all_user_records
    st.session_state["eval_pool_records"] = all_pool_records
    st.session_state["eval_robin_records"] = all_robin_records
    st.session_state["eval_defense_records"] = all_defense_records
    st.session_state["eval_ts"] = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ Listo — {len(users_valid)} usuarios · {len(all_pool_records)} pool · {len(all_robin_records)} Robin Hood · {len(all_defense_records)} defense plannification")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "eval_history" not in st.session_state:
    st.info("👆 Pulsa **Descargar historiales** en el sidebar para empezar.")
    st.stop()

history_data  = st.session_state["eval_history"]
pool_records  = st.session_state.get("eval_pool_records", [])
robin_records = st.session_state.get("eval_robin_records", [])
ts = st.session_state.get("eval_ts", "—")

st.markdown(f"<small style='color:var(--muted)'>Ultimo escaneo: {ts}</small>", unsafe_allow_html=True)

# ── Summary stat cards ───────────────────────────────────────────────────────
total_pool_sum  = sum(r.get("sum", 0) for r in pool_records)
total_robin_sum = sum(r.get("sum", 0) for r in robin_records)
total_lost      = total_pool_sum + total_robin_sum
n_users_with_lost = sum(1 for v in history_data.values() if v["total_lost"] < 0)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--red)">{total_lost}</div><div class="stat-lbl">PUNTOS PERDIDOS TOTALES</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--orange)">{total_pool_sum}</div><div class="stat-lbl">POOL (puntos donados)</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--purple)">{total_robin_sum}</div><div class="stat-lbl">ROBIN HOOD</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{n_users_with_lost}</div><div class="stat-lbl">USUARIOS CON PUNTOS PERDIDOS</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ── Helper: build summary DataFrame for a group of logins ────────────────────
def build_group_df(logins, history):
    rows = []
    for login in logins:
        v = history.get(login)
        if not v:
            continue
        rows.append({
            "Login": login,
            "Grade": v.get("Grade", ""),
            "Pool (puntos)": v["pool_sum"],
            "Pool (registros)": len(v["pool_records"]),
            "Robin Hood (puntos)": v["robin_sum"],
            "Robin Hood (registros)": len(v["robin_records"]),
            "Total perdidos": v["total_lost"],
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Total perdidos")
    return df

# ── Display each group ──────────────────────────────────────────────────────
group_logins = {
    "🎓 CADET / TRANSCENDER / ALUMNI": [u["Login"] for u in users_valid],
}

for group_name, logins in group_logins.items():
    df_group = build_group_df(logins, history_data)
    st.markdown(f'<div class="section-title">{group_name} — {len(df_group)} usuarios</div>', unsafe_allow_html=True)
    if not df_group.empty:
        st.dataframe(df_group, use_container_width=True, hide_index=True)
        csv = df_group.to_csv(index=False).encode("utf-8")
        st.download_button(f"⬇️ CSV ({group_name})", csv, f"eval_piscine_cadet_transcender_alumni.csv", "text/csv", key=f"dl_{group_name}")
    else:
        st.info(f"No hay datos para {group_name}.")
    st.markdown("---")

# ── Pool details ─────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-title">🏊 POOL — "Provided points to the pool." ({len(pool_records)} registros)</div>', unsafe_allow_html=True)
if pool_records:
    df_pool = pd.DataFrame([{
        "Login": (r.get("user_id") or ""),
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
        "Login": (r.get("user_id") or ""),
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

st.markdown("---")

# ── Team detection (Defense Plannification) ───────────────────────────────────
defense_records = st.session_state.get("eval_defense_records", [])

st.markdown(f'<div class="section-title">🛡️ TEAMS / DEFENSE PLANNIFICATION ({len(defense_records)} registros)</div>', unsafe_allow_html=True)

if defense_records:
    teams = defaultdict(list)
    for entry in defense_records:
        stid = entry["record"].get("scale_team_id")
        if stid:
            teams[stid].append(entry)

    team_rows = []
    for stid, members in sorted(teams.items(), key=lambda x: -abs(sum(m["record"].get("sum", 0) for m in x[1]))):
        member_logins = sorted({m["login"] for m in members})
        n_members = len(member_logins)
        total_sum = sum(m["record"].get("sum", 0) for m in members)
        n_records = len(members)

        team_rows.append({
            "Team ID": stid,
            "Miembros": ", ".join(member_logins),
            "N miembros": n_members,
            "Registros": n_records,
            "Sum total": total_sum,
        })

    df_teams = pd.DataFrame(team_rows)
    st.dataframe(df_teams, use_container_width=True, hide_index=True)
    csv_teams = df_teams.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (teams)", csv_teams, "eval_piscine_teams.csv", "text/csv")

    st.markdown("---")

    # Per-member breakdown within each team
    st.markdown(f'<div class="section-title">👥 DETALLE POR MIEMBRO (por team)</div>', unsafe_allow_html=True)
    for stid, members in sorted(teams.items(), key=lambda x: -abs(sum(m["record"].get("sum", 0) for m in x[1]))):
        member_logins = sorted({m["login"] for m in members})
        total_sum = sum(m["record"].get("sum", 0) for m in members)
        with st.expander(f"Team {stid} — {len(member_logins)} miembros — sum total: {total_sum}"):
            member_rows = []
            for login in member_logins:
                login_records = [m["record"] for m in members if m["login"] == login]
                login_sum = sum(r.get("sum", 0) for r in login_records)
                member_rows.append({
                    "Login": login,
                    "Registros": len(login_records),
                    "Sum": login_sum,
                })
            df_member = pd.DataFrame(member_rows)
            st.dataframe(df_member, use_container_width=True, hide_index=True)
else:
    st.info("No hay registros de Defense plannification.")
