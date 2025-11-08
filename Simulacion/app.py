import streamlit as st
import random
import requests
from collections import defaultdict

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (v3.1)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA  
Si llenas casa/visita te muestra las dos proyecciones.
""")

# tu llave real
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
SEASON = "2025REG"  # la misma que estabas usando

# =========================================================
# 0. CARGA DE DATOS NFL
# =========================================================
@st.cache_data(ttl=600)
def get_standings(api_key, season):
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"Standings: error {r.status_code}"
        data = r.json()
    except Exception as e:
        return {}, f"Standings: {e}"

    teams = {}
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

        teams[name] = {
            "pf_pg": round(pf / games_played, 2),
            "pa_pg": round(pa / games_played, 2),
        }
    return teams, ""

@st.cache_data(ttl=600)
def get_team_game_stats(api_key, season):
    """
    Intenta traer TODOS los juegos de la temporada y arma promedios
    casa/visita por equipo.
    """
    url = f"https://api.sportsdata.io/v3/nfl/stats/json/TeamGameStats/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"TeamGameStats: error {r.status_code}"
        games = r.json()
    except Exception as e:
        return {}, f"TeamGameStats: {e}"

    # estructuras para acumular
    acc = defaultdict(lambda: {
        "home_pf_sum": 0.0,
        "home_pa_sum": 0.0,
        "home_games": 0,
        "away_pf_sum": 0.0,
        "away_pa_sum": 0.0,
        "away_games": 0,
    })

    for g in games:
        team_name = (g.get("Name") or "").lower()
        # el endpoint marca si el equipo fue home o away
        is_home = g.get("HomeOrAway", "").upper() == "HOME"
        pf = g.get("Score", 0.0) or 0.0
        pa = g.get("OpponentScore", 0.0) or 0.0

        if is_home:
            acc[team_name]["home_pf_sum"] += pf
            acc[team_name]["home_pa_sum"] += pa
            acc[team_name]["home_games"] += 1
        else:
            acc[team_name]["away_pf_sum"] += pf
            acc[team_name]["away_pa_sum"] += pa
            acc[team_name]["away_games"] += 1

    # convertir a promedios
    final = {}
    for team, vals in acc.items():
        home_g = vals["home_games"] if vals["home_games"] > 0 else 1
        away_g = vals["away_games"] if vals["away_games"] > 0 else 1
        final[team] = {
            "home_pf_pg": round(vals["home_pf_sum"] / home_g, 2),
            "home_pa_pg": round(vals["home_pa_sum"] / home_g, 2),
            "away_pf_pg": round(vals["away_pf_sum"] / away_g, 2),
            "away_pa_pg": round(vals["away_pa_sum"] / away_g, 2),
        }
    return final, ""

standings_data, standings_err = get_standings(SPORTSDATAIO_KEY, SEASON)
team_cv_data, team_cv_err = get_team_game_stats(SPORTSDATAIO_KEY, SEASON)

if standings_err:
    st.warning(f"⚠️ {standings_err}")
else:
    st.info(f"✅ Datos NFL (global) cargados, {len(standings_data)} equipos ({SEASON})")

if team_cv_err:
    st.warning(f"⚠️ No pude traer casa/visita real: {team_cv_err}")

# =========================================================
# 1. DATOS DEL PARTIDO
# =========================================================
st.subheader("Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")
    if st.button("Rellenar LOCAL desde NFL"):
        lookup = local.strip().lower()
        if lookup in standings_data:
            st.session_state["l_anota_global"] = standings_data[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = standings_data[lookup]["pa_pg"]
        if lookup in team_cv_data:
            st.session_state["l_anota_casa"] = team_cv_data[lookup]["home_pf_pg"]
            st.session_state["l_permite_casa"] = team_cv_data[lookup]["home_pa_pg"]
        st.success(f"LOCAL rellenado con datos de {local}")

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
        if lookup in standings_data:
            st.session_state["v_anota_global"] = standings_data[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = standings_data[lookup]["pa_pg"]
        if lookup in team_cv_data:
            st.session_state["v_anota_visita"] = team_cv_data[lookup]["away_pf_pg"]
            st.session_state["v_permite_visita"] = team_cv_data[lookup]["away_pa_pg"]
        st.success(f"VISITA rellenado con datos de {visita}")

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
# 2. PROMEDIOS POR CONDICIÓN (ahora también se rellenan)
# =========================================================
st.subheader("Promedios por condición (opcional)")
c1, c2 = st.columns(2)
with c1:
    l_anota_casa = st.number_input(
        "Local: puntos que ANOTA en casa",
        value=st.session_state.get("l_anota_casa", 0.0),
        step=0.1,
        key="l_anota_casa",
    )
    l_permite_casa = st.number_input(
        "Local: puntos que PERMITE en casa",
        value=st.session_state.get("l_permite_casa", 0.0),
        step=0.1,
        key="l_permite_casa",
    )

with c2:
    v_anota_visita = st.number_input(
        "Visita: puntos que ANOTA de visita",
        value=st.session_state.get("v_anota_visita", 0.0),
        step=0.1,
        key="v_anota_visita",
    )
    v_permite_visita = st.number_input(
        "Visita: puntos que PERMITE de visita",
        value=st.session_state.get("v_permite_visita", 0.0),
        step=0.1,
        key="v_permite_visita",
    )

hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

# =========================================================
# 3. AJUSTE LESIONES
# =========================================================
st.subheader("Ajuste por lesiones / QB")
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
# 4. FUNCIÓN DEL MODELO
# =========================================================
def proyeccion(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5
    return base

# =========================================================
# 5. PROYECCIÓN GLOBAL
# =========================================================
st.subheader("🟦 Proyección del modelo (GLOBAL)")
pts_local = proyeccion(l_anota_global, v_permite_global, True) * mult_local
pts_visita = proyeccion(v_anota_global, l_permite_global, False) * mult_visita
total_modelo = pts_local + pts_visita
spread_modelo = pts_local - pts_visita

st.write(f"Puntos esperados {local or 'LOCAL'}: **{pts_local:.1f}**")
st.write(f"Puntos esperados {visita or 'VISITA'}: **{pts_visita:.1f}**")
st.write(f"Total GLOBAL del modelo: **{total_modelo:.1f}**")
st.write(f"Spread del modelo (local - visita): **{spread_modelo:+.1f}**")

# =========================================================
# 6. LÍNEA DEL CASINO
# =========================================================
st.subheader("Línea real del sportsbook")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread de la casa (negativo si LOCAL es favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) de la casa", 0.0, 300.0, 0.0, 0.5)

# =========================================================
# 7. DIFERENCIAS VS LÍNEA
# =========================================================
st.subheader("Diferencias vs línea real")
modelo_spread_formato_casa = -spread_modelo
dif_spread = modelo_spread_formato_casa - spread_casa
dif_total = total_modelo - total_casa

st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread:+.1f} pts**")
st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total:+.1f} pts**")

if abs(dif_spread) >= 8:
    st.error("⚠️ El spread del modelo está MUY lejos de la línea. Revisa datos o puede haber value.")
elif abs(dif_spread) >= 5:
    st.warning("⚠️ El spread del modelo está algo lejos de la línea, revísalo.")

# =========================================================
# 8. MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones", 1000, 50000, 10000, 1000)

covers = 0
overs = 0
desv = max(5, total_modelo * 0.15)

for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local, desv))
    sim_v = max(0, random.gauss(pts_visita, desv))

    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover = covers / num_sims * 100
prob_over = overs / num_sims * 100
prob_under = 100 - prob_over

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra el spread: **{prob_cover:.1f}%**")
st.write(f"Prob. de OVER: **{prob_over:.1f}%**")
st.write(f"Prob. de UNDER: **{prob_under:.1f}%**")

# =========================================================
# 9. APUESTA RECOMENDADA
# =========================================================
st.subheader("Apuesta recomendada 🎯")
opciones = []

# spread local vs visita
prob_visita_spread = 100 - prob_cover
if prob_cover >= prob_visita_spread:
    opciones.append((f"Spread: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover))
else:
    visita_linea = -spread_casa
    opciones.append((f"Spread: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread))

# total over/under
if prob_over >= prob_under:
    opciones.append((f"Total: OVER {total_casa}", prob_over))
else:
    opciones.append((f"Total: UNDER {total_casa}", prob_under))

mejor = max(opciones, key=lambda x: x[1]) if opciones else None
if mejor:
    st.success(f"📌 Apuesta sugerida: **{mejor[0]}**")
    st.write(f"Probabilidad estimada: **{mejor[1]:.1f}%**")
else:
    st.info("Llena datos, líneas y corre la simulación para ver una recomendación.")
