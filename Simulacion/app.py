import streamlit as st
import random
import requests

# =========================================================
# 0. CONFIGURACIÓN BÁSICA
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (v3.3)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA  
Si llenas casa/visita te muestra las dos proyecciones.
""")

# =========================================================
# 1. DATOS NFL DESDE SPORTSDATAIO
# =========================================================
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"  # tu llave
SEASON = "2025REG"  # la que usaste

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

nfl_data, nfl_error = cargar_nfl_desde_api(SPORTSDATAIO_KEY, SEASON)
if nfl_error:
    st.warning(f"⚠️ {nfl_error}")
else:
    st.info(f"✅ Datos NFL cargados ({SEASON}) – {len(nfl_data)} equipos")

# =========================================================
# 2. DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")
    if st.button("Rellenar LOCAL desde NFL"):
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
    visita = st.text_input("Equipo VISITA", "", key="visita_name")
    if st.button("Rellenar VISITA desde NFL"):
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
# 3. PROMEDIOS POR CONDICIÓN (LOS DEJAMOS EN BLANCO)
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
# 4. AJUSTE POR LESIONES / QB
# =========================================================
st.subheader("3) Ajuste por lesiones / QB")
c3, c4 = st.columns(2)
with c3:
    af_local = st.checkbox("¿Afecta ofensiva LOCAL?", False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
with c4:
    af_visita = st.checkbox("¿Afecta ofensiva VISITA?", False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# =========================================================
# 5. FUNCIÓN DEL MODELO
# =========================================================
def proyeccion(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5
    return base

# =========================================================
# 6. PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

# GLOBAL
pts_local = proyeccion(l_anota_global, v_permite_global, True) * mult_local
pts_visita = proyeccion(v_anota_global, l_permite_global, False) * mult_visita
total = pts_local + pts_visita
spread = pts_local - pts_visita

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'} : **{pts_local:.1f} pts**")
st.write(f"- {visita or 'VISITA'} : **{pts_visita:.1f} pts**")
st.write(f"- Total modelo: **{total:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread:+.1f}**")

# CASA / VISITA (solo si llenaste algo)
pts_local_cv = pts_visita_cv = total_cv = spread_cv = None
if hay_cv:
    pts_local_cv = proyeccion(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        True,
    ) * mult_local
    pts_visita_cv = proyeccion(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        False,
    ) * mult_visita
    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.markdown("🟩 **CASA / VISITA**")
    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, también te muestro esa proyección.")

# =========================================================
# 7. LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 0.0, 0.5)

# modelo usa local-visita, pero la casa usa "para local" (negativo favorito)
modelo_spread_formato_casa = -spread  # para compararlo con el casino
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total - total_casa

st.markdown("🟦 Dif. SPREAD (GLOBAL): **{:+.1f} pts**".format(dif_spread_global))
st.markdown("🟦 Dif. TOTAL (GLOBAL): **{:+.1f} pts**".format(dif_total_global))

dif_spread_cv = dif_total_cv = None
if hay_cv and spread_cv is not None:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.markdown("🟩 Dif. SPREAD (CASA/VISITA): **{:+.1f} pts**".format(dif_spread_cv))
    st.markdown("🟩 Dif. TOTAL (CASA/VISITA): **{:+.1f} pts**".format(dif_total_cv))

# =========================================================
# 7.b SEMÁFORO DE ALERTA (esto es lo nuevo)
# =========================================================
st.subheader("Semáforo de lectura de línea")

# de momento no sabemos si el mercado se mueve, así que solo avisamos por magnitud
# guardaremos mensajes y los mostramos
alertas = []

# GLOBAL spread
if abs(dif_spread_global) >= 4:
    alertas.append(("warning",
                    "Spread GLOBAL del modelo está ≥ 4 pts de la línea. Puede ser línea trampa o info que no tenemos."))
elif 2 <= abs(dif_spread_global) < 4:
    # todavía no sabemos la prob aquí, la traemos abajo después de Monte Carlo
    alertas.append(("info",
                    "Hay una separación moderada en el spread GLOBAL (2–4 pts). Si la simulación da ≥55% puede ser valor."))

# GLOBAL total
if abs(dif_total_global) >= 2:
    alertas.append(("info",
                    "El TOTAL del modelo difiere ≥ 2 pts del O/U. Revisa si la simulación de OVER/UNDER te da ≥55%."))

# CASA/VISITA
if dif_spread_cv is not None:
    if abs(dif_spread_cv) >= 4:
        alertas.append(("warning",
                        "Spread CASA/VISITA está ≥ 4 pts de la línea. Revísalo, puede ser exceso del modelo."))
    elif 2 <= abs(dif_spread_cv) < 4:
        alertas.append(("info",
                        "Spread CASA/VISITA separado 2–4 pts. Si Monte Carlo c/v te da ≥55% puede ser valor."))

for tipo, msg in alertas:
    if tipo == "warning":
        st.warning(msg)
    elif tipo == "info":
        st.info(msg)
    else:
        st.success(msg)

# =========================================================
# 8. SIMULACIÓN MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
covers, overs = 0, 0
desv = max(5, total * 0.15)

for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local, desv))
    sim_v = max(0, random.gauss(pts_visita, desv))

    # para cubrir spread de la casa: (local - visita) + spread_casa >= 0
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1

    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover_global = covers / num_sims * 100
prob_over_global = overs / num_sims * 100
prob_under_global = 100 - prob_over_global

st.write(f"Prob. que **{local or 'LOCAL'}** cubra el spread (GLOBAL): **{prob_cover_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 9. SIMULACIÓN MONTE CARLO (CASA / VISITA)
# =========================================================
st.subheader("7) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_cv = prob_over_cv = prob_under_cv = None

if hay_cv and pts_local_cv is not None:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="cv_sims")
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
    prob_under_cv = 100 - prob_over_cv

    st.write(f"Prob. que **{local or 'LOCAL'}** cubra (CASA/VISITA): **{prob_cover_cv:.1f}%**")
    st.write(f"Prob. de OVER (CASA/VISITA): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 10. AJUSTE DE SEMÁFORO CON PROBABILIDADES (ya tenemos probs)
# =========================================================
# si había una separación moderada y además la prob es >=55, lo decimos
if 2 <= abs(dif_spread_global) < 4 and prob_cover_global >= 55:
    st.success("💰 Valor detectado en SPREAD GLOBAL (modelo y Monte Carlo de acuerdo ≥55%).")

if abs(dif_total_global) >= 2 and max(prob_over_global, prob_under_global) >= 55:
    st.success("💰 Valor detectado en TOTAL GLOBAL (modelo y Monte Carlo de acuerdo ≥55%).")

if dif_spread_cv is not None and 2 <= abs(dif_spread_cv) < 4 and prob_cover_cv is not None and prob_cover_cv >= 55:
    st.success("💰 Valor detectado en SPREAD CASA/VISITA (modelo y Monte Carlo ≥55%).")

if dif_total_cv is not None and abs(dif_total_cv) >= 2 and prob_over_cv is not None and max(prob_over_cv, prob_under_cv) >= 55:
    st.success("💰 Valor detectado en TOTAL CASA/VISITA (modelo y Monte Carlo ≥55%).")

# =========================================================
# 11. APUESTAS RECOMENDADAS (ambas si ≥55%)
# =========================================================
st.subheader("8) Apuestas recomendadas")

recs = []

# spread global (local o visita)
prob_visita_spread_global = 100 - prob_cover_global
if prob_cover_global >= prob_visita_spread_global and prob_cover_global >= 55:
    recs.append(f"Spread GLOBAL → {local or 'LOCAL'} {spread_casa}  (**{prob_cover_global:.1f}%**)")
elif prob_visita_spread_global > prob_cover_global and prob_visita_spread_global >= 55:
    visita_linea = -spread_casa
    recs.append(f"Spread GLOBAL → {visita or 'VISITA'} {visita_linea:+.1f}  (**{prob_visita_spread_global:.1f}%**)")

# total global
if prob_over_global >= 55:
    recs.append(f"Total GLOBAL → OVER {total_casa}  (**{prob_over_global:.1f}%**)")
elif prob_under_global >= 55:
    recs.append(f"Total GLOBAL → UNDER {total_casa}  (**{prob_under_global:.1f}%**)")

# spreads y totals de casa/visita si los tienes
if hay_cv and prob_cover_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_cv
    if prob_cover_cv >= prob_visita_spread_cv and prob_cover_cv >= 55:
        recs.append(f"Spread C/V → {local or 'LOCAL'} {spread_casa}  (**{prob_cover_cv:.1f}%**)")
    elif prob_visita_spread_cv > prob_cover_cv and prob_visita_spread_cv >= 55:
        visita_linea = -spread_casa
        recs.append(f"Spread C/V → {visita or 'VISITA'} {visita_linea:+.1f}  (**{prob_visita_spread_cv:.1f}%**)")

if hay_cv and prob_over_cv is not None:
    if prob_over_cv >= 55:
        recs.append(f"Total C/V → OVER {total_casa}  (**{prob_over_cv:.1f}%**)")
    elif prob_under_cv >= 55:
        recs.append(f"Total C/V → UNDER {total_casa}  (**{prob_under_cv:.1f}%**)")

if recs:
    for r in recs:
        st.success(r)
else:
    st.info("No hay apuestas ≥55% en este escenario. Ajusta datos o revisa lesiones/clima.")
