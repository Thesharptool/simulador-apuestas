import streamlit as st
import random
import requests
import math

# =========================================================
# CONFIG GENERAL
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (multi-liga)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA (manual)  
Si llenas casa/visita te muestro las dos proyecciones.
""")

# =========================================================
# 0) ¿QUÉ LIGA QUIERES?
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# tu key REAL de SportsDataIO (sirve para NFL; NBA en tu cuenta está cerrada)
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
NFL_SEASON = "2025REG"

# =========================================================
# FUNCIONES DE APOYO
# =========================================================
@st.cache_data(ttl=600)
def cargar_nfl_desde_api(api_key: str, season: str):
    """Trae standings de NFL y los pasa a pts a favor / pts en contra por partido."""
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"Error {r.status_code} al conectar con SportsDataIO (NFL)"
        data = r.json()
    except Exception as e:
        return {}, f"Error de conexión: {e}"

    equipos = {}
    for t in data:
        name = (t.get("Name") or "").lower()
        wins = t.get("Wins", 0) or 0
        losses = t.get("Losses", 0) or 0
        ties = t.get("Ties", 0) or 0
        pf = float(t.get("PointsFor", 0) or 0)
        pa = float(t.get("PointsAgainst", 0) or 0)
        jugados = wins + losses + ties
        games_raw = t.get("Games", 0) or 0
        jugados = jugados if jugados > 0 else games_raw if games_raw > 0 else 1
        equipos[name] = {
            "pf_pg": round(pf / jugados, 2),
            "pa_pg": round(pa / jugados, 2),
        }
    return equipos, ""

def proyeccion_puntos(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local and liga == "NFL":
        base += 1.5
    return base

def prob_desde_moneyline(ml: float) -> float:
    if ml is None or ml == 0:
        return 0.0
    if ml > 0:
        return 100 / (ml + 100) * 100
    else:
        return (-ml) / (-ml + 100) * 100

def config_desviacion_por_liga(liga: str, total_modelo: float) -> float:
    if liga == "NFL":
        return max(6.0, total_modelo * 0.12)
    else:
        return max(10.0, total_modelo * 0.08)

# =========================================================
# INICIALIZAR SESSION_STATE PARA LOS CAMPOS QUE RELLENAMOS
# =========================================================
for key in [
    "l_anota_global", "l_permite_global",
    "v_anota_global", "v_permite_global"
]:
    if key not in st.session_state:
        st.session_state[key] = 0.0

# =========================================================
# 1) CARGA DATA NFL
# =========================================================
nfl_data = {}
if liga == "NFL":
    nfl_data, nfl_error = cargar_nfl_desde_api(SPORTSDATAIO_KEY, NFL_SEASON)
    if nfl_error:
        st.warning(nfl_error)
    else:
        st.success(f"✅ Datos NFL cargados — {len(nfl_data)} equipos ({NFL_SEASON})")
else:
    st.info("NBA: tu plan actual de SportsDataIO no trae stats de equipo, así que esta parte es manual.")

# =========================================================
# 2) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", key="local_name")
    if liga == "NFL" and st.button("Rellenar LOCAL desde NFL"):
        lookup = local.strip().lower()
        if lookup in nfl_data:
            st.session_state["l_anota_global"] = nfl_data[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = nfl_data[lookup]["pa_pg"]
            st.success(f"LOCAL rellenado con datos reales de {local}")
        else:
            st.error("No encontré ese equipo en NFL")

    st.markdown("**Promedios GLOBAL del LOCAL**")
    l_anota_global = st.number_input(
        "Local: puntos que ANOTA (global)",
        value=st.session_state["l_anota_global"],
        step=0.1,
        key="l_anota_global"
    )
    l_permite_global = st.number_input(
        "Local: puntos que PERMITE (global)",
        value=st.session_state["l_permite_global"],
        step=0.1,
        key="l_permite_global"
    )

with col2:
    visita = st.text_input("Equipo VISITA", key="visita_name")
    if liga == "NFL" and st.button("Rellenar VISITA desde NFL"):
        lookup = visita.strip().lower()
        if lookup in nfl_data:
            st.session_state["v_anota_global"] = nfl_data[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = nfl_data[lookup]["pa_pg"]
            st.success(f"VISITA rellenado con datos reales de {visita}")
        else:
            st.error("No encontré ese equipo en NFL")

    st.markdown("**Promedios GLOBAL del VISITA**")
    v_anota_global = st.number_input(
        "Visita: puntos que ANOTA (global)",
        value=st.session_state["v_anota_global"],
        step=0.1,
        key="v_anota_global"
    )
    v_permite_global = st.number_input(
        "Visita: puntos que PERMITE (global)",
        value=st.session_state["v_permite_global"],
        step=0.1,
        key="v_permite_global"
    )

# =========================================================
# 3) PROMEDIOS POR CONDICIÓN (manual)
# =========================================================
st.subheader("2) Promedios por condición (opcional)")
c1, c2 = st.columns(2)
with c1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", 0.0, step=0.1)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", 0.0, step=0.1)
with c2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", 0.0, step=0.1)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", 0.0, step=0.1)

hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

# =========================================================
# 4) AJUSTE POR LESIONES / FORMA
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

perfil_opciones = {
    "Healthy / completo": 1.00,
    "1–2 bajas importantes": 0.95,
    "Varias bajas / QB tocado": 0.90,
    "En buen momento ofensivo": 1.05,
}

c3, c4 = st.columns(2)
with c3:
    perfil_local = st.selectbox("Estado ofensivo LOCAL", list(perfil_opciones.keys()), index=0)
    mult_local = perfil_opciones[perfil_local]
with c4:
    perfil_visita = st.selectbox("Estado ofensivo VISITA", list(perfil_opciones.keys()), index=0)
    mult_visita = perfil_opciones[perfil_visita]

st.caption("Estos multiplicadores afectan los puntos proyectados. 1.00 = normal, 0.95 = un poco peor, 1.05 = mejor.")

# =========================================================
# 5) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

# GLOBAL
pts_local_global = proyeccion_puntos(l_anota_global, v_permite_global, es_local=True) * mult_local
pts_visita_global = proyeccion_puntos(v_anota_global, l_permite_global, es_local=False) * mult_visita
total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.markdown("🟦 **GLOBAL**")
st.write(f"• {local or 'LOCAL'} : **{pts_local_global:.1f} pts**")
st.write(f"• {visita or 'VISITA'} : **{pts_visita_global:.1f} pts**")
st.write(f"• Total modelo: **{total_global:.1f}**")
st.write(f"• Spread modelo (local - visita): **{spread_global:+.1f}**")

# CASA / VISITA
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion_puntos(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        es_local=True
    ) * mult_local
    pts_visita_cv = proyeccion_puntos(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        es_local=False
    ) * mult_visita
    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv
    st.write(f"• {local or 'LOCAL'} (casa): **{pts_local_cv:.1f}**")
    st.write(f"• {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}**")
    st.write(f"• Total CASA/VISITA: **{total_cv:.1f}**")
    st.write(f"• Spread CASA/VISITA: **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 6) LÍNEA DEL CASINO + ALERTA
# =========================================================
st.subheader("5) Línea del casino y diferencias")

c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -60.0, 60.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 350.0, 0.0, 0.5)

modelo_spread_formato_casa = -spread_global
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total_global - total_casa

st.write(f"🟦 **DIF. SPREAD (GLOBAL):** {dif_spread_global:+.1f} pts")
st.write(f"🟦 **DIF. TOTAL (GLOBAL):** {dif_total_global:+.1f} pts")

if abs(dif_spread_global) >= 5:
    st.error("⚠️ Posible trap line: modelo y casa están muy lejos. Revisa lesiones/noticias.")
elif abs(dif_spread_global) >= 3:
    st.warning("⚠️ Modelo y casa no coinciden mucho. Puede ser oportunidad o info faltante.")

if hay_cv:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.write(f"🟩 **DIF. SPREAD (CASA/VISITA):** {dif_spread_cv:+.1f} pts")
    st.write(f"🟩 **DIF. TOTAL (CASA/VISITA):** {dif_total_cv:+.1f} pts")

# =========================================================
# 5b) MONEYLINE
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
c_ml1, c_ml2 = st.columns(2)
with c_ml1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with c_ml2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0, step=5)

prob_imp_local = prob_desde_moneyline(ml_local)
prob_imp_visita = prob_desde_moneyline(ml_visita)

if ml_local != 0 and ml_visita != 0:
    st.write(f"Prob. implícita LOCAL: **{prob_imp_local:.1f}%**, Prob. implícita VISITA: **{prob_imp_visita:.1f}%**")

# =========================================================
# 6) MONTE CARLO GLOBAL
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv_global = config_desviacion_por_liga(liga, total_global)

covers = 0
overs = 0
wins_local = 0

for _ in range(num_sims_global):
    sim_local = max(0, random.gauss(pts_local_global, desv_global))
    sim_visita = max(0, random.gauss(pts_visita_global, desv_global))

    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1
    if (sim_local + sim_visita) > total_casa:
        overs += 1
    if sim_local > sim_visita:
        wins_local += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100
prob_win_local_model = wins_local / num_sims_global * 100
prob_win_visita_model = 100 - prob_win_local_model

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra el spread (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6b) MONTE CARLO CASA/VISITA
# =========================================================
st.subheader("6b) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_local_cv = None
prob_over_cv = None

if hay_cv:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="cv_sims_slider")
    desv_cv = config_desviacion_por_liga(liga, total_cv)
    covers_cv = 0
    overs_cv = 0
    for _ in range(num_sims_cv):
        sim_l = max(0, random.gauss(pts_local_cv, desv_cv))
        sim_v = max(0, random.gauss(pts_visita_cv, desv_cv))
        if (sim_l - sim_v) + spread_casa >= 0:
            covers_cv += 1
        if (sim_l + sim_v) > total_casa:
            overs_cv += 1
    prob_cover_local_cv = covers_cv / num_sims_cv * 100
    prob_over_cv = overs_cv / num_sims_cv * 100
    st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (CASA/VISITA): **{prob_cover_local_cv:.1f}%**")
    st.write(f"Prob. de OVER (CASA/VISITA): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 5c) COMPARATIVA MODELO VS CASINO
# =========================================================
st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
col_cm1, col_cm2 = st.columns(2)
with col_cm1:
    st.write(f"{local or 'LOCAL'} (modelo): **{prob_win_local_model:.1f}%**")
with col_cm2:
    st.write(f"{visita or 'VISITA'} (modelo): **{prob_win_visita_model:.1f}%**")

if ml_local != 0 and ml_visita != 0:
    value_msgs = []
    if prob_win_local_model > prob_imp_local + 5:
        value_msgs.append(f"✅ Posible value en **{local or 'LOCAL'} ML** (modelo {prob_win_local_model:.1f}% vs casa {prob_imp_local:.1f}%)")
    if prob_win_visita_model > prob_imp_visita + 5:
        value_msgs.append(f"✅ Posible value en **{visita or 'VISITA'} ML** (modelo {prob_win_visita_model:.1f}% vs casa {prob_imp_visita:.1f}%)")
    if value_msgs:
        for m in value_msgs:
            st.success(m)
    else:
        st.info("No se detectó value claro en moneylines.")
else:
    st.caption("Si metes moneylines aquí te digo si tu modelo ve más probabilidad que la casa.")

# =========================================================
# 7) APUESTAS RECOMENDADAS
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

# spread global
if prob_cover_local_global >= 55:
    recs.append(f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f} — {prob_cover_local_global:.1f}%")
elif (100 - prob_cover_local_global) >= 55:
    visita_linea = -spread_casa
    recs.append(f"Spread GLOBAL: {visita or 'VISITA'} {visita_linea:+.1f} — {100 - prob_cover_local_global:.1f}%")

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= 55:
    recs.append(f"Total GLOBAL: OVER {total_casa:.1f} — {prob_over_global:.1f}%")
elif prob_under_global >= 55:
    recs.append(f"Total GLOBAL: UNDER {total_casa:.1f} — {prob_under_global:.1f}%")

# casa/visita
if hay_cv and prob_cover_local_cv is not None:
    if prob_cover_local_cv >= 55:
        recs.append(f"Spread CASA/VISITA: {local or 'LOCAL'} {spread_casa:+.1f} — {prob_cover_local_cv:.1f}%")
    elif (100 - prob_cover_local_cv) >= 55:
        visita_linea = -spread_casa
        recs.append(f"Spread CASA/VISITA: {visita or 'VISITA'} {visita_linea:+.1f} — {100 - prob_cover_local_cv:.1f}%")

if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= 55:
        recs.append(f"Total CASA/VISITA: OVER {total_casa:.1f} — {prob_over_cv:.1f}%")
    elif prob_under_cv >= 55:
        recs.append(f"Total CASA/VISITA: UNDER {total_casa:.1f} — {prob_under_cv:.1f}%")

if recs:
    for r in recs:
        st.success("📌 " + r)
else:
    st.info("Aún no hay apuestas ≥ 55%. Llena líneas y ejecuta simulación.")
