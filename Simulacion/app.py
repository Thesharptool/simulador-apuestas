import streamlit as st
import random
import requests

# =========================================================
# CONFIG GENERAL
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas 🏈🏀", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (multi-liga)")
st.markdown(
    "🟦 = cálculo con promedios GLOBAL  \n"
    "🟩 = cálculo con promedios CASA/VISITA (solo NFL)  \n"
    "Si llenas casa/visita te muestra las dosproyecciones."
)

liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# =========================================================
# NFL: carga desde SportsDataIO
# =========================================================
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"  # tu llave
NFL_SEASON = "2025REG"


@st.cache_data(ttl=600)
def cargar_nfl_desde_api(api_key: str, season: str):
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {}, f"Error {resp.status_code} al conectar con SportsDataIO"
        data = resp.json()
    except Exception as e:
        return {}, f"Error de conexión: {e}"

    nfl_teams = {}
    for t in data:
        name = (t.get("Name") or "").lower()
        wins = t.get("Wins", 0) or 0
        losses = t.get("Losses", 0) or 0
        ties = t.get("Ties", 0) or 0
        pf = t.get("PointsFor", 0.0) or 0.0
        pa = t.get("PointsAgainst", 0.0) or 0.0

        played = wins + losses + ties
        games_raw = t.get("Games", 0) or 0
        games_played = played if played > 0 else games_raw if games_raw > 0 else 1

        nfl_teams[name] = {
            "pf_pg": round(pf / games_played, 2),
            "pa_pg": round(pa / games_played, 2),
        }
    return nfl_teams, ""


nfl_data = {}
if liga == "NFL":
    nfl_data, nfl_error = cargar_nfl_desde_api(SPORTSDATAIO_KEY, NFL_SEASON)
    if nfl_error:
        st.warning(f"⚠️ {nfl_error}")
    else:
        st.success(f"✅ Datos NFL cargados — {len(nfl_data)} equipos ({NFL_SEASON})")
else:
    st.info("📘 NBA: no hay carga automática, llena los campos manualmente.")

# =========================================================
# 1) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col_l, col_v = st.columns(2)

# ---- LOCAL ----
with col_l:
    local_name = st.text_input("Equipo LOCAL", key="local_name")
    if liga == "NFL":
        if st.button("Rellenar LOCAL desde NFL"):
            lookup = local_name.strip().lower()
            if lookup in nfl_data:
                st.session_state["l_anota_global"] = nfl_data[lookup]["pf_pg"]
                st.session_state["l_permite_global"] = nfl_data[lookup]["pa_pg"]
                st.success(f"LOCAL rellenado con datos reales de {local_name}")
            else:
                st.error("No encontré ese equipo en NFL")

    st.markdown("**Promedios GLOBAL del LOCAL**")
    l_anota_global = st.number_input(
        "Local: puntos que ANOTA (global)",
        value=st.session_state.get("l_anota_global", 0.0),
        step=0.1,
        key="l_anota_global",
    )
    l_permite_global = st.number_input(
        "Local: puntos que PERMITE (global)",
        value=st.session_state.get("l_permite_global", 0.0),
        step=0.1,
        key="l_permite_global",
    )

# ---- VISITA ----
with col_v:
    visita_name = st.text_input("Equipo VISITA", key="visita_name")
    if liga == "NFL":
        if st.button("Rellenar VISITA desde NFL"):
            lookup = visita_name.strip().lower()
            if lookup in nfl_data:
                st.session_state["v_anota_global"] = nfl_data[lookup]["pf_pg"]
                st.session_state["v_permite_global"] = nfl_data[lookup]["pa_pg"]
                st.success(f"VISITA rellenado con datos reales de {visita_name}")
            else:
                st.error("No encontré ese equipo en NFL")

    st.markdown("**Promedios GLOBAL del VISITA**")
    v_anota_global = st.number_input(
        "Visita: puntos que ANOTA (global)",
        value=st.session_state.get("v_anota_global", 0.0),
        step=0.1,
        key="v_anota_global",
    )
    v_permite_global = st.number_input(
        "Visita: puntos que PERMITE (global)",
        value=st.session_state.get("v_permite_global", 0.0),
        step=0.1,
        key="v_permite_global",
    )

# =========================================================
# 2) SEGÚN LIGA
# =========================================================
if liga == "NFL":
    st.subheader("2) Promedios por condición (opcional)")
    c1, c2 = st.columns(2)
    with c1:
        l_anota_casa = st.number_input(
            "Local: puntos que ANOTA en casa", value=0.0, step=0.1
        )
        l_permite_casa = st.number_input(
            "Local: puntos que PERMITE en casa", value=0.0, step=0.1
        )
    with c2:
        v_anota_visita = st.number_input(
            "Visita: puntos que ANOTA de visita", value=0.0, step=0.1
        )
        v_permite_visita = st.number_input(
            "Visita: puntos que PERMITE de visita", value=0.0, step=0.1
        )

    hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

else:  # NBA
    st.subheader("2) Factores avanzados NBA (últimos 5 partidos) 🏀")
    st.caption(
        "Llena estos datos para que el total de NBA se acerque más a las líneas reales."
    )
    nb1, nb2 = st.columns(2)

    with nb1:
        pace_local_5 = st.number_input(
            "PACE LOCAL (posesiones últimos 5)", value=0.0, step=0.1
        )
        off_local_5 = st.number_input(
            "Ofensiva LOCAL (pts/100 poss últimos 5)", value=0.0, step=0.1
        )
        def_local_5 = st.number_input(
            "Defensiva LOCAL (pts permitidos/100 poss últimos 5)",
            value=0.0,
            step=0.1,
        )
    with nb2:
        pace_visita_5 = st.number_input(
            "PACE VISITA (posesiones últimos 5)", value=0.0, step=0.1
        )
        off_visita_5 = st.number_input(
            "Ofensiva VISITA (pts/100 poss últimos 5)", value=0.0, step=0.1
        )
        def_visita_5 = st.number_input(
            "Defensiva VISITA (pts permitidos/100 poss últimos 5)",
            value=0.0,
            step=0.1,
        )

    pace_liga = st.number_input("Pace promedio liga (NBA)", value=99.0, step=0.1)

# =========================================================
# 3) AJUSTE POR LESIONES / FORMA
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

opt_estado = {
    "Healthy / completo": 1.00,
    "1 baja importante": 0.97,
    "Varias bajas / tocado": 0.93,
    "En buen momento": 1.03,
}

c3, c4 = st.columns(2)
with c3:
    estado_local = st.selectbox(
        f"Estado ofensivo LOCAL ({liga})",
        list(opt_estado.keys()),
        index=0,
        key="estado_local",
    )
with c4:
    estado_visita = st.selectbox(
        f"Estado ofensivo VISITA ({liga})",
        list(opt_estado.keys()),
        index=0,
        key="estado_visita",
    )

mult_local = opt_estado[estado_local]
mult_visita = opt_estado[estado_visita]
st.caption("Estos multiplicadores afectan a los puntos proyectados. 1.00 = normal.")

# =========================================================
# FUNCIÓN DE PROYECCIÓN NFL
# =========================================================
def proyeccion_nfl(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5
    return base


# =========================================================
# 4) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

if liga == "NFL":
    # GLOBAL
    pts_local_global = proyeccion_nfl(l_anota_global, v_permite_global, True) * mult_local
    pts_visita_global = (
        proyeccion_nfl(v_anota_global, l_permite_global, False) * mult_visita
    )
    total_global = pts_local_global + pts_visita_global
    spread_global = pts_local_global - pts_visita_global  # margen local – visita
    line_modelo = -spread_global  # formato casa (LOCAL favorito = negativo)

    st.markdown("🟦 **GLOBAL**")
    st.write(f"- {local_name or 'LOCAL'}: **{pts_local_global:.1f} pts**")
    st.write(f"- {visita_name or 'VISITA'}: **{pts_visita_global:.1f} pts**")
    st.write(f"- Total modelo: **{total_global:.1f}**")
    st.write(
        f"- Spread modelo (local – visita): **{spread_global:+.1f} pts** "
        f"→ línea modelo LOCAL **{line_modelo:+.1f}**"
    )

    # CASA / VISITA si hay
    if hay_cv:
        st.markdown("🟩 **CASA / VISITA**")
        pts_local_cv = proyeccion_nfl(l_anota_casa, v_permite_visita, True) * mult_local
        pts_visita_cv = (
            proyeccion_nfl(v_anota_visita, l_permite_casa, False) * mult_visita
        )
        total_cv = pts_local_cv + pts_visita_cv
        spread_cv = pts_local_cv - pts_visita_cv

        st.write(f"- {local_name or 'LOCAL'}: **{pts_local_cv:.1f} pts**")
        st.write(f"- {visita_name or 'VISITA'}: **{pts_visita_cv:.1f} pts**")
        st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
        st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
    else:
        total_cv = None
        spread_cv = None

else:
    # ================== NBA MODEL ==================
    # pace medio de los 2, si no hay usa liga
    if pace_local_5 > 0 and pace_visita_5 > 0:
        pace_med = (pace_local_5 + pace_visita_5) / 2
    else:
        pace_med = pace_liga

    # reciente LOCAL y VISITA -> 60% ataque + 40% defensa rival
    reciente_local = (0.6 * off_local_5 + 0.4 * def_visita_5) * (pace_med / 100.0)
    reciente_visita = (0.6 * off_visita_5 + 0.4 * def_local_5) * (pace_med / 100.0)

    # global: promedio simple vs rival
    global_local_part = 0.0
    global_visita_part = 0.0
    if l_anota_global or v_permite_global:
        global_local_part = (l_anota_global + v_permite_global) / 2.0
    if v_anota_global or l_permite_global:
        global_visita_part = (v_anota_global + l_permite_global) / 2.0

    # mezcla 65% reciente, 35% global
    pts_local_global = (0.65 * reciente_local + 0.35 * global_local_part) * mult_local
    pts_visita_global = (0.65 * reciente_visita + 0.35 * global_visita_part) * mult_visita

    total_global = pts_local_global + pts_visita_global
    spread_global = pts_local_global - pts_visita_global  # margen local – visita
    line_modelo = -spread_global  # formato casa

    st.markdown("🏀 usando últimos 5 + pace + global (65% / 35%)")
    st.write(f"- {local_name or 'LOCAL'}: **{pts_local_global:.1f} pts**")
    st.write(f"- {visita_name or 'VISITA'}: **{pts_visita_global:.1f} pts**")
    st.write(f"- Total modelo: **{total_global:.1f}**")
    st.write(
        f"- Spread modelo (local – visita): **{spread_global:+.1f} pts** "
        f"→ línea modelo LOCAL **{line_modelo:+.1f}**"
    )

    total_cv = None
    spread_cv = None

# =========================================================
# 5) LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")

col_spread, col_total = st.columns(2)
with col_spread:
    spread_casa = st.number_input(
        "Spread del casino (negativo si LOCAL favorito)",
        value=0.0,
        step=0.5,
    )
with col_total:
    total_casa = st.number_input("Total (O/U) del casino", value=0.0, step=0.5)

with st.expander("🔍 Comparación de spreads (GLOBAL)", expanded=True):
    st.write(f"- Modelo (formato casa): **LOCAL {line_modelo:+.1f}**")
    st.write(f"- Casa: **LOCAL {spread_casa:+.1f}**")
    # Usamos CASA - MODELO para que, si la casa es más agresiva con el favorito, el signo sea negativo
    dif_spread = spread_casa - line_modelo
    st.write(f"- **DIF. SPREAD (GLOBAL): {dif_spread:+.1f} pts**")

with st.expander("🔍 Comparación de totales (GLOBAL)", expanded=True):
    st.write(f"- Modelo: **{total_global:.1f}**")
    st.write(f"- Casa: **{total_casa:.1f}**")
    dif_total = total_global - total_casa
    st.write(f"- **DIF. TOTAL (GLOBAL): {dif_total:+.1f} pts**")

# alerta de trap line
trap_msgs = []
if abs(dif_spread) >= 5:
    trap_msgs.append("spread")
if abs(dif_total) >= 8:
    trap_msgs.append("total")

if trap_msgs:
    st.error(
        f"⚠️ Línea muy diferente a tu modelo ({', '.join(trap_msgs)}). "
        f"Puede ser trap line o info que no estás metiendo."
    )

# =========================================================
# 5b) MONEYLINE
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
c_ml1, c_ml2 = st.columns(2)
with c_ml1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with c_ml2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0, step=5)


def implied_from_ml(ml):
    if ml == 0:
        return 0.0
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return -ml / (-ml + 100)


prob_impl_local = implied_from_ml(ml_local) * 100
prob_impl_visita = implied_from_ml(ml_visita) * 100

st.write(
    f"Prob. implícita LOCAL (casa): **{prob_impl_local:.1f}%**, "
    f"Prob. implícita VISITA (casa): **{prob_impl_visita:.1f}%**"
)

# =========================================================
# 5c) Comparativa de probabilidades (modelo vs casino)
# =========================================================
st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
# modelo: muy sencillo, si spread modelo > 0 => local favorito
p_local_modelo = 50 + (spread_global * 2)  # muy simple
p_local_modelo = max(1, min(99, p_local_modelo))
p_visita_modelo = 100 - p_local_modelo

st.write(f"{local_name or 'LOCAL'} (modelo): **{p_local_modelo:.1f}%**")
st.write(f"{visita_name or 'VISITA'} (modelo): **{p_visita_modelo:.1f}%**")
st.write(f"Prob. implícita LOCAL (casa): **{prob_impl_local:.1f}%**")
st.write(f"Prob. implícita VISITA (casa): **{prob_impl_visita:.1f}%**")

# =========================================================
# 6) MONTE CARLO
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)

covers, overs = 0, 0
# desviación fija por deporte (curva normal más realista)
if liga == "NBA":
    desv = 12.0
else:  # NFL
    desv = 13.0

for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local_global, desv))
    sim_v = max(0, random.gauss(pts_visita_global, desv))
    # spread: LOCAL + spread_casa debe ser >= visita
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover = covers / num_sims * 100
prob_over = overs / num_sims * 100

st.write(f"Prob. de que {local_name or 'LOCAL'} cubra (GLOBAL): **{prob_cover:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over:.1f}%**")

# =========================================================
# 7) Apuestas recomendadas (si ≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []
if prob_cover >= 55:
    recs.append(
        f"🟢 Spread GLOBAL: {local_name or 'LOCAL'} {spread_casa:+.1f} → {prob_cover:.1f}%"
    )
if prob_over >= 55:
    recs.append(
        f"🟢 Total GLOBAL: OVER {total_casa:.1f} → {prob_over:.1f}%"
    )

if recs:
    for r in recs:
        st.success(r)
else:
    st.info("Por ahora ninguna llega al 55%.")

# =========================================================
# 8) Edge del modelo vs casa
# =========================================================
st.subheader("8) Edge del modelo vs casa")

st.write(f"Línea MODELO (LOCAL): **{line_modelo:+.1f}**")
st.write(f"Línea CASA   (LOCAL): **{spread_casa:+.1f}**")

# Edge en puntos:
# edge_local > 0  → la línea de la casa es más suave con el favorito → valor en LOCAL
# edge_local < 0  → la casa es más agresiva con el favorito → valor en VISITA
edge_local = spread_casa - line_modelo
edge_visita = -edge_local

if edge_local > 0:
    st.success(
        f"Edge SPREAD LOCAL: **+{edge_local:.1f} pts** "
        f"(la línea de la casa es {edge_local:.1f} pts más suave que tu modelo → valor en el LOCAL)"
    )
else:
    st.error(
        f"Edge SPREAD LOCAL: **{edge_local:.1f} pts** "
        f"(la casa es más agresiva con el LOCAL → más valor en la VISITA)"
    )

if edge_visita > 0:
    st.success(
        f"Edge SPREAD VISITA: **+{edge_visita:.1f} pts** "
        f"(tu modelo ve {edge_visita:.1f} pts de valor en la VISITA)"
    )
else:
    st.error(
        f"Edge SPREAD VISITA: **{edge_visita:.1f} pts** "
        f"(hay poco o ningún valor en la VISITA según tu modelo)"
    )

st.caption("Pon los moneylines para calcular el edge de forma más fina.")
