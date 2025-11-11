import streamlit as st
import random
import requests

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (multi-liga)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA (manual)  
Si llenas casa/visita te muestra las dos proyecciones.
""")

# =========================================================
# 0. ELEGIR DEPORTE
# =========================================================
deporte = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# =========================================================
# 0b. CARGA NFL DESDE SPORTSDATAIO (solo si NFL)
# =========================================================
NFL_API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
NFL_SEASON = "2025REG"   # lo estabas usando así

@st.cache_data(ttl=600)
def cargar_nfl_desde_api(api_key: str, season: str):
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"Error {r.status_code} al conectar con SportsDataIO"
        data = r.json()
    except Exception as e:
        return {}, f"Error de conexión: {e}"

    equipos = {}
    for t in data:
        name = (t.get("Name") or "").lower()
        wins = t.get("Wins", 0) or 0
        losses = t.get("Losses", 0) or 0
        ties = t.get("Ties", 0) or 0
        pf = t.get("PointsFor", 0.0) or 0.0
        pa = t.get("PointsAgainst", 0.0) or 0.0

        jugados = wins + losses + ties
        games_raw = t.get("Games", 0) or 0
        games_played = jugados if jugados > 0 else (games_raw if games_raw > 0 else 1)

        equipos[name] = {
            "pf_pg": round(pf / games_played, 2),
            "pa_pg": round(pa / games_played, 2),
        }
    return equipos, ""

nfl_data = {}
if deporte == "NFL":
    nfl_data, nfl_err = cargar_nfl_desde_api(NFL_API_KEY, NFL_SEASON)
    if nfl_err:
        st.warning(f"⚠️ {nfl_err}")
    else:
        st.success(f"✅ Datos NFL cargados — {len(nfl_data)} equipos ({NFL_SEASON})")
else:
    st.info("📘 NBA: no hay carga automática, llena los promedios manualmente.")

# =========================================================
# 1. DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", key="local_name")
    if deporte == "NFL":
        if st.button("Rellenar LOCAL desde NFL"):
            key = local.strip().lower()
            if key in nfl_data:
                st.session_state["l_anota_global"] = nfl_data[key]["pf_pg"]
                st.session_state["l_permite_global"] = nfl_data[key]["pa_pg"]
                st.success(f"LOCAL rellenado con datos reales de {local}")
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

with col2:
    visita = st.text_input("Equipo VISITA", key="visita_name")
    if deporte == "NFL":
        if st.button("Rellenar VISITA desde NFL"):
            key = visita.strip().lower()
            if key in nfl_data:
                st.session_state["v_anota_global"] = nfl_data[key]["pf_pg"]
                st.session_state["v_permite_global"] = nfl_data[key]["pa_pg"]
                st.success(f"VISITA rellenado con datos reales de {visita}")
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
# 2. CASA / VISITA (manual)
# =========================================================
st.subheader("2) Promedios por condición (opcional)")
c1, c2 = st.columns(2)
with c1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", value=0.0, step=0.1)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", value=0.0, step=0.1)
with c2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", value=0.0, step=0.1)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", value=0.0, step=0.1)

hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

# =========================================================
# 2b. FACTORES AVANZADOS NBA (nuevo)
# =========================================================
if deporte == "NBA":
    st.subheader("2b) Factores avanzados NBA (pace / eficiencia)")
    st.markdown("Llena estos datos para que el total de NBA se acerque más a las líneas reales.")

    colA, colB, colC = st.columns(3)
    with colA:
        pace_local = st.number_input("Pace LOCAL (posesiones)", value=98.0, step=0.1)
    with colB:
        pace_visita = st.number_input("Pace VISITA", value=98.0, step=0.1)
    with colC:
        pace_liga = st.number_input("Pace promedio liga", value=99.0, step=0.1)

    colO, colD = st.columns(2)
    with colO:
        off_eff_local = st.number_input("Ofensiva LOCAL (pts/100 poss)", value=112.0, step=0.1)
    with colD:
        def_eff_visita = st.number_input("Defensiva VISITA (pts permitidos/100 poss)", value=112.0, step=0.1)

# =========================================================
# 3. AJUSTE POR LESIONES / FORMA / QB
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

if deporte == "NFL":
    colL, colV = st.columns(2)
    with colL:
        qb_local_fuera = st.checkbox("¿QB titular LOCAL no juega?", value=False)
    with colV:
        qb_visita_fuera = st.checkbox("¿QB titular VISITA no juega?", value=False)
    # multiplicadores NFL
    mult_local = 1.0 - (0.12 if qb_local_fuera else 0.0)
    mult_visita = 1.0 - (0.12 if qb_visita_fuera else 0.0)
else:
    # NBA: solo forma general
    colL, colV = st.columns(2)
    with colL:
        estado_local = st.selectbox("Estado ofensivo LOCAL (NBA)", ["Normal", "Ligera baja", "Muy tocado"], index=0)
    with colV:
        estado_visita = st.selectbox("Estado ofensivo VISITA (NBA)", ["Normal", "Ligera baja", "Muy tocado"], index=0)

    def mult_nba(estado):
        if estado == "Normal":
            return 1.0
        elif estado == "Ligera baja":
            return 0.97
        else:
            return 0.93

    mult_local = mult_nba(estado_local)
    mult_visita = mult_nba(estado_visita)

st.caption("Estos multiplicadores afectan a los puntos proyectados.")

# =========================================================
# 4. FUNCIÓN DE PROYECCIÓN
# =========================================================
def proyeccion(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5 if deporte == "NFL" else 1.0
    return base

# =========================================================
# 4. PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

# GLOBAL
pts_local_global = proyeccion(l_anota_global, v_permite_global, True) * mult_local
pts_visita_global = proyeccion(v_anota_global, l_permite_global, False) * mult_visita
total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global  # + = gana LOCAL

# ajuste NBA por pace (suave)
if deporte == "NBA":
    try:
        pace_factor = (pace_local + pace_visita) / 2 / pace_liga
        total_global = total_global * pace_factor
    except Exception:
        pass

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'} : **{pts_local_global:.1f} pts**")
st.write(f"- {visita or 'VISITA'} : **{pts_visita_global:.1f} pts**")
st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

# CASA / VISITA
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        True
    ) * mult_local
    pts_visita_cv = proyeccion(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        False
    ) * mult_visita
    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"- {local or 'LOCAL'} (c/v): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (c/v): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread (c/v): **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 5. LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", value=0.0, step=0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", value=0.0, step=0.5)

with st.expander("🔍 Comparación de spreads (GLOBAL)", expanded=True):
    modelo_formato_casa = -spread_global
    st.write(f"- Modelo (formato casa): **LOCAL {modelo_formato_casa:+.1f}**")
    st.write(f"- Casa: **LOCAL {spread_casa:+.1f}**")
    dif_spread_global = modelo_formato_casa - spread_casa
    st.write(f"- **DIF. SPREAD (GLOBAL): {dif_spread_global:+.1f} pts**")

with st.expander("🔍 Comparación de totales (GLOBAL)", expanded=True):
    st.write(f"- Modelo: **{total_global:.1f}**")
    st.write(f"- Casa: **{total_casa:.1f}**")
    dif_total_global = total_global - total_casa
    st.write(f"- **DIF. TOTAL (GLOBAL): {dif_total_global:+.1f} pts**")

alertas = []
if abs(dif_spread_global) >= 3.0:
    alertas.append("spread")
if abs(dif_total_global) >= 12.0 and deporte == "NBA":
    alertas.append("total")
if abs(dif_total_global) >= 8.0 and deporte == "NFL":
    alertas.append("total")

if alertas:
    txt = " y ".join(alertas)
    st.error(f"⚠️ Línea muy diferente a tu modelo ({txt}). Puede ser trap line o info que no estás metiendo.")

# =========================================================
# 5b. MONEYLINE (opcional)
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
cML1, cML2 = st.columns(2)
with cML1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0)
with cML2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0)

def american_to_prob(ml):
    if ml == 0:
        return 0.0
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return -ml / (-ml + 100)

imp_local = american_to_prob(ml_local) * 100
imp_visita = american_to_prob(ml_visita) * 100
st.write(f"Prob. implícita LOCAL: **{imp_local:.1f}%**, Prob. implícita VISITA: **{imp_visita:.1f}%**")

# =========================================================
# 5c. COMPARATIVA MODELO vs CASINO (solo con ML)
# =========================================================
st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
# prob modelo por puntos: si el modelo da más puntos al local, le damos prob alta
if pts_local_global + 0.01 > pts_visita_global:
    prob_modelo_local = 60.0
    prob_modelo_visita = 40.0
else:
    prob_modelo_local = 40.0
    prob_modelo_visita = 60.0

colM1, colM2 = st.columns(2)
with colM1:
    st.write(f"{local or 'LOCAL'} (modelo): **{prob_modelo_local:.1f}%**")
    st.write(f"{visita or 'VISITA'} (modelo): **{prob_modelo_visita:.1f}%**")
with colM2:
    st.write(f"Prob. implícita LOCAL (casa): **{imp_local:.1f}%**")
    st.write(f"Prob. implícita VISITA (casa): **{imp_visita:.1f}%**")

# =========================================================
# 6. MONTE CARLO GLOBAL
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)

covers = 0
overs = 0
desv_global = max(5, total_global * 0.15)

for _ in range(num_sims_global):
    sim_l = max(0, random.gauss(pts_local_global, desv_global))
    sim_v = max(0, random.gauss(pts_visita_global, desv_global))
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6b. MONTE CARLO CASA/VISITA
# =========================================================
st.subheader("6b) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_cv = None
prob_over_cv = None
if hay_cv:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="sims_cv")
    desv_cv = max(5, total_cv * 0.15)
    covers_cv = 0
    overs_cv = 0
    for _ in range(num_sims_cv):
        sim_l = max(0, random.gauss(pts_local_cv, desv_cv))
        sim_v = max(0, random.gauss(pts_visita_cv, desv_cv))
        if (sim_l - sim_v) + spread_casa >= 0:
            covers_cv += 1
        if (sim_l + sim_v) > total_casa:
            overs_cv += 1
    prob_cover_cv = covers_cv / num_sims_cv * 100
    prob_over_cv = overs_cv / num_sims_cv * 100

    st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (c/v): **{prob_cover_cv:.1f}%**")
    st.write(f"Prob. de OVER (c/v): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 7. APUESTAS RECOMENDADAS
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

if prob_cover_global >= 55:
    recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_global))

if prob_over_global >= 55:
    recs.append((f"Total GLOBAL: OVER {total_casa:.1f}", prob_over_global))

if hay_cv and prob_cover_cv is not None and prob_cover_cv >= 55:
    recs.append((f"Spread CASA/VISITA: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_cv))

if hay_cv and prob_over_cv is not None and prob_over_cv >= 55:
    recs.append((f"Total CASA/VISITA: OVER {total_casa:.1f}", prob_over_cv))

if recs:
    for txt, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"✅ {txt} — **{p:.1f}%**")
else:
    st.info("Ninguna apuesta pasa el 55% según la simulación.")

# =========================================================
# 8. EDGE DEL MODELO vs CASA (con ML)
# =========================================================
st.subheader("8) Edge del modelo vs casa")
if ml_local != 0 and ml_visita != 0:
    edge_local = prob_modelo_local - imp_local
    edge_visita = prob_modelo_visita - imp_visita

    if edge_local >= 0:
        st.success(f"Edge LOCAL: **{edge_local:+.1f}%** (modelo ve más valor que la casa)")
    else:
        st.error(f"Edge LOCAL: **{edge_local:+.1f}%** (la casa está más alta)")

    if edge_visita >= 0:
        st.success(f"Edge VISITA: **{edge_visita:+.1f}%**")
    else:
        st.error(f"Edge VISITA: **{edge_visita:+.1f}%**")
else:
    st.caption("Pon los moneylines para calcular el edge.")
