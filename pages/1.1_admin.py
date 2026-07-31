import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="42 Cursus Activo / Pendiente", page_icon="📅", layout="wide")

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

st.markdown('<div class="page-title">📅 Cursus 42 — Activo vs Pendiente</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Separa por begin_at: quién ya está activo en el cursus vs quién tiene fecha de inicio futura (aún no cuenta como estudiante)</div>', unsafe_allow_html=True)

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
    st.markdown("### 📅 Scan settings")

    campus_id   = st.session_state.get("campus_id", 46)
    campus_name = st.session_state.get("selected_campus", "Barcelona")
    scope = st.radio("Alcance", ["Solo este campus", "Todos los campus"], index=0)
    st.info(f"📍 **{campus_name}** (ID {campus_id})" if scope == "Solo este campus" else "🌍 Todos los campus")

    cursus_id = st.number_input("Cursus ID", value=21, min_value=1, help="21 = 42cursus (el principal)")
    max_pages = st.number_input("Páginas máx (100/pág)", 1, 1000, 20)
    debug     = st.checkbox("🐛 Debug (mostrar URLs)", value=False)

    scan_btn = st.button("🚀 Ver activo / pendiente", type="primary", use_container_width=True)

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

            begin_raw = cu.get("begin_at")
            begin_dt  = None
            if begin_raw:
                try:
                    begin_dt = datetime.fromisoformat(begin_raw.replace("Z", "+00:00"))
                except Exception:
                    pass

            if begin_dt is None:
                status_label = "❓ Sin begin_at"
                days_to_start = None
            elif begin_dt > now_utc:
                status_label = "🟡 Pendiente (aún no empieza)"
                days_to_start = (begin_dt - now_utc).days
            else:
                status_label = "🟢 Activo"
                days_to_start = None

            raw_grade = (cu.get("grade") or "").strip()
            bh_raw    = cu.get("blackholed_at")
            end_raw   = cu.get("end_at")
            # Blackholeado "de verdad" = end_at Y blackholed_at ambos presentes.
            # (blackholed_at solo, sin end_at, es alguien en cuenta atrás / aún no confirmado)
            es_blackholeado = bool(end_raw) and bool(bh_raw)

            rows.append({
                "Login":          user.get("login", ""),
                "Display Name":   user.get("displayname", ""),
                "Kind":           user.get("kind", ""),
                "Grade (raw)":    raw_grade if raw_grade else "(vacío/null)",
                "Estado cursus":  status_label,
                "Begin At":       begin_raw or "—",
                "Días para empezar": days_to_start,
                "Level":          round(float(cu.get("level", 0)), 2),
                "Eval Points":    int(user.get("correction_point", 0) or 0),
                "Blackholed At":  bh_raw or "—",
                "Blackholeado":   es_blackholeado,
                "Updated":        cu.get("updated_at", ""),
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
    st.session_state["cursus_status_rows"] = rows
    st.session_state["scan_ts"] = datetime.now().strftime("%H:%M:%S")
    st.success(f"✅ Escaneo completo — {len(rows)} registros")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "cursus_status_rows" not in st.session_state:
    st.info("👆 Pulsa **Ver activo / pendiente** en el sidebar para empezar.")
    st.stop()

rows = st.session_state["cursus_status_rows"]
ts = st.session_state.get("scan_ts", "—")

df = pd.DataFrame(rows)
st.markdown(f"<small style='color:var(--muted)'>Último escaneo: {ts} · {len(df)} registros</small>", unsafe_allow_html=True)

# ── Stats ─────────────────────────────────────────────────────────────────────
pendientes  = df[df["Estado cursus"] == "🟡 Pendiente (aún no empieza)"]
activos     = df[df["Estado cursus"] == "🟢 Activo"]
sin_begin   = df[df["Estado cursus"] == "❓ Sin begin_at"]
blackholeados = df[df["Blackholeado"] == True]
admins      = df[df["Kind"] == "admin"]

# Nota: el filtro real de "estudiantes válidos" (Alumni/Transcender/Cadet sin blackhole)
# se calcula más abajo, justo antes de las tablas de estadísticas.

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--green)">{len(activos)}</div><div class="stat-lbl">ACTIVOS</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--orange)">{len(pendientes)}</div><div class="stat-lbl">PENDIENTES (FUTURO)</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--muted)">{len(sin_begin)}</div><div class="stat-lbl">SIN begin_at</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--red)">{len(blackholeados)}</div><div class="stat-lbl">BLACKHOLEADOS</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ── Pendientes ────────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-title">🟡 PENDIENTES — empiezan en el futuro ({len(pendientes)})</div>', unsafe_allow_html=True)
if not pendientes.empty:
    st.dataframe(
        pendientes.sort_values("Begin At"),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Días para empezar": st.column_config.NumberColumn("Días para empezar", format="%d días"),
        }
    )
    csv_pend = pendientes.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (pendientes)", csv_pend, "pendientes_cursus42.csv", "text/csv")
else:
    st.info("No hay nadie con fecha de inicio futura en este escaneo.")

st.markdown("---")

# ── Activos ───────────────────────────────────────────────────────────────────
activos_tabla = activos[(~activos["Blackholeado"]) & (activos["Grade (raw)"] != "(vacío/null)")]

st.markdown(f'<div class="section-title">🟢 ACTIVOS ({len(activos_tabla)})</div>', unsafe_allow_html=True)
if not activos_tabla.empty:
    st.dataframe(activos_tabla.sort_values("Begin At"), use_container_width=True, hide_index=True)
    csv_act = activos_tabla.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (activos)", csv_act, "activos_cursus42.csv", "text/csv")
else:
    st.info("No hay activos en este escaneo.")

# ── Sin begin_at (por si acaso) ─────────────────────────────────────────────────
if not sin_begin.empty:
    st.markdown("---")
    st.markdown(f'<div class="section-title">❓ SIN begin_at ({len(sin_begin)})</div>', unsafe_allow_html=True)
    st.dataframe(sin_begin, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Blackholeados ───────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-title">🕳️ BLACKHOLEADOS ({len(blackholeados)})</div>', unsafe_allow_html=True)
if not blackholeados.empty:
    tabla_bh = blackholeados[["Login", "Display Name", "Kind", "Grade (raw)", "Level", "Eval Points", "Blackholed At"]].sort_values("Blackholed At", ascending=False)
    st.dataframe(tabla_bh, use_container_width=True, hide_index=True)
    csv_bh = tabla_bh.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV (blackholeados)", csv_bh, "blackholeados.csv", "text/csv")
else:
    st.info("No hay blackholeados en este escaneo.")

st.markdown("---")

# ── Filtro base: kind=student, y de los Cadets se excluyen los blackholeados ──
# (Transcender y Alumni ya pasaron esa etapa, así que no se filtran por blackhole aquí)
es_cadet_valido = (df["Grade (raw)"] == "Cadet") & (~df["Blackholeado"])
es_transcender   = df["Grade (raw)"] == "Transcender"
es_alumni        = df["Grade (raw)"] == "Alumni"

estudiantes_validos = df[(df["Kind"] == "student") & (es_cadet_valido | es_transcender | es_alumni)]

activos_validos     = estudiantes_validos[estudiantes_validos["Estado cursus"] == "🟢 Activo"]
pendientes_validos  = estudiantes_validos[estudiantes_validos["Estado cursus"] == "🟡 Pendiente (aún no empieza)"]

def tabla_estadisticas(data, group_col="Grade (raw)"):
    """Devuelve un DataFrame de estadísticas agregadas (conteo, media, total) por grupo."""
    if data.empty:
        return pd.DataFrame(columns=[group_col, "Estudiantes", "Media Eval Points", "Total Eval Points"])
    stats = (
        data.groupby(group_col)["Eval Points"]
        .agg(Estudiantes="count", **{"Media Eval Points": "mean", "Total Eval Points": "sum"})
        .reset_index()
        .sort_values("Estudiantes", ascending=False)
    )
    stats["Media Eval Points"] = stats["Media Eval Points"].round(1)
    return stats

st.markdown("---")

# ── Tabla A: estadísticas — solo alumnos activos ───────────────────────────────
st.markdown('<div class="section-title">📊 ESTADÍSTICAS — SOLO ACTIVOS (student · Alumni/Transcender/Cadet sin blackhole)</div>', unsafe_allow_html=True)
avg_a = activos_validos["Eval Points"].mean() if not activos_validos.empty else 0
mas_de_5_a = (activos_validos["Eval Points"] > 5).sum()
avg_a_capped = activos_validos["Eval Points"].clip(upper=5).mean() if not activos_validos.empty else 0
total_capped = activos_validos["Eval Points"].clip(upper=5).sum() if not activos_validos.empty else 0
puntos_a_bajar_3 = total_capped - (3 * len(activos_validos))

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--green)">{len(activos_validos)}</div><div class="stat-lbl">TOTAL ESTUDIANTES</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{avg_a:.1f}</div><div class="stat-lbl">MEDIA EVAL POINTS</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--purple)">{mas_de_5_a}</div><div class="stat-lbl">CON MÁS DE 5 PUNTOS</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--orange)">{avg_a_capped:.1f}</div><div class="stat-lbl">MEDIA SI TOPAMOS EN 5</div></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--red)">-{puntos_a_bajar_3:.0f}</div><div class="stat-lbl">EVAL POINTS A BAJAR PARA MEDIA=3</div></div>', unsafe_allow_html=True)

st.dataframe(tabla_estadisticas(activos_validos), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Tabla A2: estadísticas — solo activos, Transcender/Cadet (sin Alumni) ─────
activos_sin_alumni = activos_validos[activos_validos["Grade (raw)"] != "Alumni"]
avg_a2 = activos_sin_alumni["Eval Points"].mean() if not activos_sin_alumni.empty else 0

st.markdown('<div class="section-title">📊 ESTADÍSTICAS — SOLO ACTIVOS (student · Transcender/Cadet sin blackhole)</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--green)">{len(activos_sin_alumni)}</div><div class="stat-lbl">TOTAL ESTUDIANTES</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{avg_a2:.1f}</div><div class="stat-lbl">MEDIA EVAL POINTS</div></div>', unsafe_allow_html=True)

st.dataframe(tabla_estadisticas(activos_sin_alumni), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Tabla B: estadísticas — activos + futuros (pendientes) ────────────────────
activos_y_futuros = pd.concat([activos_validos, pendientes_validos], ignore_index=True)
avg_b = activos_y_futuros["Eval Points"].mean() if not activos_y_futuros.empty else 0
diff_b = avg_b - avg_a

st.markdown('<div class="section-title">📊 ESTADÍSTICAS — ACTIVOS + FUTUROS</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--orange)">{len(activos_y_futuros)}</div><div class="stat-lbl">TOTAL ESTUDIANTES</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{avg_b:.1f}</div><div class="stat-lbl">MEDIA EVAL POINTS</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-card"><div class="stat-val" style="color:{"var(--red)" if diff_b < 0 else "var(--green)"}">{diff_b:+.1f}</div><div class="stat-lbl">DIFERENCIA vs SOLO ACTIVOS</div></div>', unsafe_allow_html=True)

st.dataframe(tabla_estadisticas(activos_y_futuros), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Tabla C: estadísticas — activos + futuros + admins ─────────────────────────
# Los admins no tienen "Grade (raw)" útil, así que se agrupan aparte con su propia etiqueta
admins_para_stats = admins.copy()
admins_para_stats["Grade (raw)"] = "Admin"
activos_futuros_admins = pd.concat([activos_validos, pendientes_validos, admins_para_stats], ignore_index=True)
avg_c = activos_futuros_admins["Eval Points"].mean() if not activos_futuros_admins.empty else 0
diff_c = avg_c - avg_a

st.markdown('<div class="section-title">📊 ESTADÍSTICAS — ACTIVOS + FUTUROS + ADMINS</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--purple)">{len(activos_futuros_admins)}</div><div class="stat-lbl">TOTAL PERSONAS</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-val" style="color:var(--accent)">{avg_c:.1f}</div><div class="stat-lbl">MEDIA EVAL POINTS</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-card"><div class="stat-val" style="color:{"var(--red)" if diff_c < 0 else "var(--green)"}">{diff_c:+.1f}</div><div class="stat-lbl">DIFERENCIA vs SOLO ACTIVOS</div></div>', unsafe_allow_html=True)

st.dataframe(tabla_estadisticas(activos_futuros_admins), use_container_width=True, hide_index=True)
