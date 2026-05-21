import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timezone, date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="🏫 Campus Eval Points", page_icon="🏫", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
:root {
    --accent:#00d4ff; --green:#00ff88; --orange:#ff8c00;
    --surface:#161920; --border:#2a2f3d; --muted:#64748b;
}
.stApp { background:#0d0f14; }
.page-title { font-family:'JetBrains Mono',monospace; font-size:2rem; font-weight:700; color:var(--accent); }
.page-sub   { font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--muted); margin-bottom:1.5rem; }
.stat-card  { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem; text-align:center; font-family:'JetBrains Mono',monospace; }
.stat-val   { font-size:1.8rem; font-weight:700; color:var(--accent); }
.stat-val-green { font-size:1.8rem; font-weight:700; color:var(--green); }
.stat-val-red   { font-size:1.8rem; font-weight:700; color:#ff4444; }
.stat-lbl   { font-size:0.65rem; color:var(--muted); margin-top:2px; }
.summary-box { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:1rem 1.5rem; margin-top:0.4rem; font-family:'JetBrains Mono',monospace; }
.summary-row { display:flex; justify-content:space-between; align-items:center; padding:0.3rem 0; border-bottom:1px solid var(--border); }
.summary-row:last-child { border-bottom:none; }
.summary-label { color:var(--muted); font-size:0.75rem; }
.summary-value { font-weight:700; font-size:0.9rem; color:#e2e8f0; }
.hist-card {
    background:var(--surface); border:1px solid var(--border);
    border-left:4px solid var(--accent); border-radius:8px;
    padding:0.6rem 1.25rem; margin-bottom:0.3rem;
    font-family:'JetBrains Mono',monospace;
    display:flex; justify-content:space-between; align-items:center;
}
.hist-pos { color:var(--green); font-weight:700; }
.hist-neg { color:#ff4444; font-weight:700; }
.hist-zero { color:var(--muted); font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">🏫 Campus Eval Points</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Suma total de correction points del campus — comparativa entre fechas</div>', unsafe_allow_html=True)

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
    st.markdown("### 🏫 Campus Eval Points")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    st.info(f"📍 **{campus_name}** (ID {campus_id})")

    date1    = st.date_input("Fecha base", value=date(2026, 5, 13))
    date2    = st.date_input("Fecha comparación", value=date.today())
    max_pages = st.number_input("Páginas de estudiantes (100/pág)", 1, 200, 50)
    debug    = st.checkbox("🐛 Debug", value=False)

    st.markdown("---")
    st.markdown("""
    **⚠️ Nota:** Este análisis llama a la API de historial por cada estudiante.
    Con muchos usuarios puede tardar varios minutos.
    """)
    load_btn = st.button("🚀 Calcular", type="primary", use_container_width=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
KEEP_GRADES = {"Cadet", "Outercore", "Transcender", "Alumni", "Blackholed"}

def detect_grade(cu, now_utc):
    user   = cu.get("user", {})
    active = user.get("active?", True)
    bh     = cu.get("blackholed_at")
    raw    = (cu.get("grade") or "").strip()
    if not active and bh:
        return "Blackholed"
    if raw:
        return raw
    end = cu.get("end_at")
    if not end and not bh:
        return "Outercore"
    return "Sin grade"

def fetch_campus_students(campus_id, headers, max_pages, debug):
    """Devuelve lista de {user_id, login, grade, current_pts}"""
    results = []
    page    = 1
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    while page <= max_pages:
        url = (
            f"https://api.intra.42.fr/v2/cursus/21/cursus_users"
            f"?filter[campus_id]={campus_id}"
            f"&page[size]=100&page[number]={page}&sort=-updated_at"
        )
        resp = api_get(url, headers)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            break

        data = resp.json()
        if not data:
            break

        for cu in data:
            user  = cu.get("user", {})
            if not user:
                continue
            grade = detect_grade(cu, now_utc)
            if grade not in KEEP_GRADES:
                continue
            results.append({
                "user_id":     user.get("id"),
                "login":       user.get("login", ""),
                "grade":       grade,
                "current_pts": int(user.get("correction_point", 0) or 0),
            })

        if len(data) < 100:
            break
        page += 1

    return results

def get_pts_on_date(user_id, target_date, headers):
    """
    Devuelve los correction points de un usuario al final de target_date.
    Usa "total" (saldo acumulado) del registro más reciente <= fin del día.
    Devuelve None si no hay datos.
    """
    end_of_day = datetime(
        target_date.year, target_date.month, target_date.day, 23, 59, 59
    )
    page = 1
    while page <= 10:  # máx 1000 registros por usuario
        url = (
            f"https://api.intra.42.fr/v2/users/{user_id}/correction_point_historics"
            f"?page[size]=100&page[number]={page}&sort=-created_at"
        )
        resp = api_get(url, headers)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            return None

        records = resp.json()
        if not records:
            return None

        for rec in records:
            created_raw = rec.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(
                    created_raw.replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except Exception:
                continue

            if created_dt <= end_of_day:
                # Primer registro en orden desc que cae antes del fin del día
                total = rec.get("total")
                if total is not None:
                    return int(total)
                return None

        # Todos los registros de esta página son posteriores a end_of_day
        # Si el último de la página ya es anterior, habremos encontrado antes
        # Si no, buscar en la página siguiente
        last_raw = records[-1].get("created_at", "")
        try:
            last_dt = datetime.fromisoformat(
                last_raw.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except Exception:
            break

        if last_dt <= end_of_day:
            # Ya deberíamos haber encontrado algo en esta página, no hay datos
            return None

        page += 1

    return None

# ── Load ──────────────────────────────────────────────────────────────────────
if load_btn:
    # 1. Cargar lista de estudiantes
    with st.spinner("📋 Cargando lista de estudiantes del campus…"):
        students = fetch_campus_students(campus_id, headers, max_pages, debug)

    if not students:
        st.error("❌ No se pudieron cargar los estudiantes.")
        st.stop()

    st.info(f"👥 {len(students)} estudiantes encontrados. Calculando historial de puntos…")

    # 2. Para cada estudiante, obtener pts en date1 y date2
    results = []
    bar     = st.progress(0, text="Procesando usuarios…")
    status  = st.empty()
    total   = len(students)

    for i, s in enumerate(students):
        status.text(f"⏳ {i+1}/{total} — {s['login']}")
        bar.progress((i + 1) / total)

        pts1 = get_pts_on_date(s["user_id"], date1, headers)
        pts2 = get_pts_on_date(s["user_id"], date2, headers)

        results.append({
            "login":       s["login"],
            "grade":       s["grade"],
            "current_pts": s["current_pts"],
            "pts_date1":   pts1,   # None = sin historial en esa fecha
            "pts_date2":   pts2,
        })

    bar.empty()
    status.empty()

    df = pd.DataFrame(results)
    st.session_state["campus_eval_df"]    = df
    st.session_state["campus_eval_date1"] = date1
    st.session_state["campus_eval_date2"] = date2
    st.success(f"✅ Listo — {len(df)} usuarios procesados")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "campus_eval_df" not in st.session_state:
    st.info("👆 Configura las fechas y pulsa **Calcular** para empezar.")
    st.markdown("""
    **Qué hace esta página:**
    - Carga todos los estudiantes activos del campus
    - Para cada uno, busca su saldo de correction points en **Fecha base** y **Fecha comparación**
    - Muestra la suma total del campus en cada fecha y la variación
    """)
    st.stop()

df    = st.session_state["campus_eval_df"].copy()
date1 = st.session_state["campus_eval_date1"]
date2 = st.session_state["campus_eval_date2"]

# ── Calcular totales ──────────────────────────────────────────────────────────
# Usuarios con datos en ambas fechas (para comparativa justa)
df_both = df.dropna(subset=["pts_date1", "pts_date2"])
df_d1   = df.dropna(subset=["pts_date1"])
df_d2   = df.dropna(subset=["pts_date2"])

total_current = int(df["current_pts"].sum())
total_d1      = int(df_d1["pts_date1"].sum())
total_d2      = int(df_d2["pts_date2"].sum())
diff          = total_d2 - total_d1
diff_sign     = "+" if diff >= 0 else ""
diff_color    = "#00ff88" if diff >= 0 else "#ff4444"

# Usuarios sin historial (se incorporaron después o sin datos)
no_data_d1 = len(df) - len(df_d1)
no_data_d2 = len(df) - len(df_d2)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"### 📍 {st.session_state.get('selected_campus','Campus')} — Correction Points")

# ── Stats principales ─────────────────────────────────────────────────────────
cards = [
    (total_current,          "PUNTOS HOY (API)",          "var(--accent)"),
    (total_d1,               f"TOTAL {date1.strftime('%d/%m/%Y')}", "var(--accent)"),
    (total_d2,               f"TOTAL {date2.strftime('%d/%m/%Y')}", "var(--accent)"),
    (f"{diff_sign}{diff}",   "VARIACIÓN",                 diff_color),
    (len(df),                "USUARIOS",                  "var(--muted)"),
]
c1, c2, c3, c4, c5 = st.columns(5)
for col, (val, lbl, color) in zip([c1, c2, c3, c4, c5], cards):
    v = f"{val:,}" if isinstance(val, int) else str(val)
    col.markdown(
        f'<div class="stat-card"><div class="stat-val" style="color:{color}">{v}</div>'
        f'<div class="stat-lbl">{lbl}</div></div>',
        unsafe_allow_html=True
    )

st.markdown(
    f"<br><small style='color:var(--muted);font-family:JetBrains Mono,monospace'>"
    f"Sin historial en {date1.strftime('%d/%m')}: {no_data_d1} usuarios · "
    f"Sin historial en {date2.strftime('%d/%m')}: {no_data_d2} usuarios</small>",
    unsafe_allow_html=True
)

st.markdown("---")

# ── Por grade ─────────────────────────────────────────────────────────────────
st.markdown("### 📊 Por Grade")

grade_rows = []
for grade, gdf in df.groupby("grade"):
    g1 = int(gdf["pts_date1"].dropna().sum())
    g2 = int(gdf["pts_date2"].dropna().sum())
    gd = g2 - g1
    grade_rows.append({
        "Grade":   grade,
        "Usuarios": len(gdf),
        f"Total {date1.strftime('%d/%m')}": g1,
        f"Total {date2.strftime('%d/%m')}": g2,
        "Variación": gd,
    })

grade_df = pd.DataFrame(grade_rows).sort_values("Variación", ascending=False)

for _, row in grade_df.iterrows():
    vd   = row["Variación"]
    sign = "+" if vd >= 0 else ""
    col  = "#00ff88" if vd >= 0 else "#ff4444"
    lbl1 = f"Total {date1.strftime('%d/%m')}"
    lbl2 = f"Total {date2.strftime('%d/%m')}"
    v1   = f"{row[lbl1]:,}"
    v2   = f"{row[lbl2]:,}"
    d1s  = date1.strftime('%d/%m')
    d2s  = date2.strftime('%d/%m')
    st.markdown(f"""
    <div class="hist-card">
        <div>
            <span style="color:#e2e8f0;font-weight:700">{row['Grade']}</span>
            <span style="color:var(--muted);font-size:0.75rem"> · {row['Usuarios']} usuarios</span>
        </div>
        <div style="text-align:right;font-size:0.85rem">
            <span style="color:var(--muted)">{d1s}: <b style="color:#e2e8f0">{v1}</b></span>
            &nbsp;→&nbsp;
            <span style="color:var(--muted)">{d2s}: <b style="color:#e2e8f0">{v2}</b></span>
            &nbsp;&nbsp;
            <b style="color:{col}">{sign}{vd:,} pts</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Top movers ────────────────────────────────────────────────────────────────
st.markdown("### 🏆 Top movers (usuarios con mayor variación)")

df_both = df.dropna(subset=["pts_date1", "pts_date2"]).copy()
df_both["variacion"] = df_both["pts_date2"].astype(int) - df_both["pts_date1"].astype(int)

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**📈 Mayores ganancias**")
    top_gainers = df_both.nlargest(15, "variacion")
    for _, row in top_gainers.iterrows():
        v = int(row["variacion"])
        if v == 0:
            continue
        st.markdown(f"""
        <div class="hist-card">
            <div>
                <span style="color:#e2e8f0">{row['login']}</span>
                <span style="color:var(--muted);font-size:0.7rem"> · {row['grade']}</span>
            </div>
            <div class="hist-pos">+{v} pts</div>
        </div>
        """, unsafe_allow_html=True)

with col_b:
    st.markdown("**📉 Mayores pérdidas**")
    top_losers = df_both.nsmallest(15, "variacion")
    for _, row in top_losers.iterrows():
        v = int(row["variacion"])
        if v == 0:
            continue
        st.markdown(f"""
        <div class="hist-card">
            <div>
                <span style="color:#e2e8f0">{row['login']}</span>
                <span style="color:var(--muted);font-size:0.7rem"> · {row['grade']}</span>
            </div>
            <div class="hist-neg">{v} pts</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── Tabla completa ────────────────────────────────────────────────────────────
st.markdown("### 📋 Tabla completa")

df_show = df.copy()
df_show["variacion"] = (df_show["pts_date2"].fillna(0) - df_show["pts_date1"].fillna(0)).astype(int)
df_show = df_show.rename(columns={
    "login":       "Login",
    "grade":       "Grade",
    "current_pts": "Pts actuales",
    "pts_date1":   f"Pts {date1.strftime('%d/%m')}",
    "pts_date2":   f"Pts {date2.strftime('%d/%m')}",
    "variacion":   "Variación",
})
df_show = df_show.sort_values("Variación", ascending=False)

st.dataframe(
    df_show,
    use_container_width=True,
    hide_index=True,
    height=500,
)

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
csv = df_show.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV", csv, "campus_eval_points.csv", "text/csv")
