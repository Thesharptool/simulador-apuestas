import streamlit as st
import random
import requests

# =========================================================
# CONFIG INICIAL
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
# 0) ¿QUÉ QUIERES SIMULAR?
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# =========================================================
# 0.a) NFL: cargar standings de SportsDataIO
# =========================================================
NFL_API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"   # la tuya
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

# =========================================================
# 0.b) NBA: cargar ratings de Basketball Reference
# =========================================================
@st.cache_data(ttl=600)
def cargar_nba_ratings(season_year: int = 2025):
    """
    Trae la tabla de https://www.basketball-reference.com/leagues/NBA_2025_ratings.html
    y la convierte en dict {team_lower: {pace, ortg, drtg}}.
    Si falla, regresa {} y un mensaje.
    """
    import pandas as pd

    url = f"https://www.basketball-reference.com/leagues/NBA_{season_year}_ratings.html"
    try:
        tables = pd.read_html(url)
        df = tables[0]
    except Exception as e:
        return {}, f"No se pudo leer Basketball Reference: {e}"

    # columnas típicas: 'Team', 'Pace', 'ORtg', 'DRtg'
    ratings = {}
    for _, row in df.iterrows():
        team = str(row.get("Team", "")).lower()
        if team and team != "league average":
            pace = float(row.get("Pace", 100))
            ortg = float(row.get("ORtg", 110))
            drtg = float(row.get("DRtg", 110))
            # estimación súper simple de puntos por partido:
            # ppp = pace * ortg / 100
            pf_pg = round(pace * ortg / 100, 1)
            pa_pg = round(pace * drtg / 100, 1)
            ratings[team] = {
                "pace": pace,
                "ortg": ortg,
                "drtg": drtg,
                "pf_pg": pf_pg,
                "pa_pg": pa_pg,
            }
    return ratings, ""

# =========================================================
# CARGAS SEGÚN LIGA
# =========================================================
nfl_data = {}
nfl_error = ""
nba_data = {}
nba_error = ""

if liga == "NFL":
    nfl_data, nfl_error = cargar_nfl_desde_api(NFL_API_KEY, NFL_SEASON)
    if nfl_error:
        st.warning(f"⚠️ {nfl_error}")
    else:
        st.success(f"✅ Datos NFL cargados — {len(nfl_data)} equipos ({NFL_SEASON})")
else:
    nba_data, nba_error = cargar_nba_ratings(2025)
    if nba_error:
        st.warning(f"⚠️ {nba_error}")
    else:
        st.success(f"✅ Ratings NBA cargados automáticamente (Basketball Reference) — {len(nba_data)} equipos")


# =========================================================
# 1) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")

    # botón según liga
    if liga == "NFL":
        if st.button("Rellenar LOCAL desde NFL"):
            lookup = local.strip().lower()
            if lookup in nfl_data:
                st.session_state["l_anota_global"] = nfl_data[lookup]["pf_pg"]
                st.session_state["l_permite_global"] = nfl_data[lookup]["pa_pg"]
                st.success(f"LOCAL rellenado con datos reales de {local}")
            else:
                st.error("No encontré ese equipo en NFL")
    else:
        if st.button("Rellenar LOCAL desde NBA"):
            lookup = local.strip().lower()
            if lookup in nba_data:
                st.session_state["l_anota_global"] = nba_data[lookup]["pf_pg"]
                st.session_state["l_permite_global"] = nba_data[lookup]["pa_pg"]
                st.success(f"LOCAL rellenado con ratings de {local}")
            else:
                st.error("No encontré ese equipo en NBA (revisa el nombre tal cual sale en Basketball Reference)")

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

    if liga == "NFL":
        if st.button("Rellenar VISITA desde NFL"):
            lookup = visita.strip().lower()
            if lookup in nfl_data:
                st.session_state["v_anota_global"] = nfl_data[lookup]["pf_pg"]
                st.session_state["v_permite_global"] = nfl_data[lookup]["pa_pg"]
                st.success(f"VISITA rellenado con datos reales de {visita}")
            else:
                st.error("No encontré ese equipo en NFL")
    else:
        if st.button("Rellenar VISITA desde NBA"):
            lookup = visita.strip().lower()
            if lookup in nba_data:
                st.session_state["v_anota_global"] = nba_data[lookup]["pf_pg"]
                st.session_state["v_permite_global"] = nba_data[lookup]["pa_pg"]
                st.success(f"VISITA rellenado con ratings de {visita}")
            else:
                st.error("No encontré ese equipo en NBA")

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
# 2) CASA / VISITA (manual, lo dejamos en blanco)
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
# 3) AJUSTE POR LESIONES / FORMA
# NFL: toggle de QB titular
# NBA: lo dejamos como “estado ofensivo” nada más
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

c3, c4 = st.columns(2)

if liga == "NFL":
    with c3:
        qb_juega = st.checkbox("¿Juega el QB titular del LOCAL?", value=True)
        estado_local = st.selectbox(
            "Estado ofensivo LOCAL",
            ["Healthy / completo", "1–2 bajas importantes", "Varias bajas"],
            index=0,
        )
    with c4:
        qb_juega_v = st.checkbox("¿Juega el QB titular del VISITA?", value=True)
        estado_visita = st.selectbox(
            "Estado ofensivo VISITA",
            ["Healthy / completo", "1–2 bajas importantes", "Varias bajas"],
            index=0,
            key="estado_visita",
        )

    def mult_desde_estado(estado, qb_ok=True):
        base = 1.0
        if estado == "1–2 bajas importantes":
            base -= 0.03
        elif estado == "Varias bajas":
            base -= 0.06
        # impacto de QB
        if not qb_ok:
            base -= 0.10   # -10% si no juega el QB titular
        return max(0.7, base)

    mult_local = mult_desde_estado(estado_local, qb_ok=qb_juega)
    mult_visita = mult_desde_estado(estado_visita, qb_ok=qb_juega_v)

else:
    # NBA: ajuste simple
    with c3:
        estado_local = st.selectbox(
            "Estado ofensivo LOCAL (NBA)",
            ["Normal", "Sin una estrella", "Back-to-back / cansados"],
            index=0,
        )
    with c4:
        estado_visita = st.selectbox(
            "Estado ofensivo VISITA (NBA)",
            ["Normal", "Sin una estrella", "Back-to-back / cansados"],
            index=0,
            key="estado_visita_nba",
        )

    def mult_nba(estado):
        if estado == "Normal":
            return 1.0
        elif estado == "Sin una estrella":
            return 0.94
        else:
            return 0.97

    mult_local = mult_nba(estado_local)
    mult_visita = mult_nba(estado_visita)

st.caption("Estos multiplicadores afectan a los puntos proyectados. 1.00 = normal.")

# =========================================================
# 4) FUNCIÓN DEL MODELO
# =========================================================
def proyeccion(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5  # pequeña ventaja local
    return base

# =========================================================
# 4) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

# GLOBAL
pts_local = proyeccion(l_anota_global, v_permite_global, True) * mult_local
pts_visita = proyeccion(v_anota_global, l_permite_global, False) * mult_visita
total_modelo = pts_local + pts_visita
spread_modelo = pts_local - pts_visita  # positivo = local mejor

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita:.1f} pts**")
st.write(f"- Total modelo: **{total_modelo:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_modelo:+.1f}**")

# CASA / VISITA si hay datos
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

    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f}**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}**")
    st.write(f"- Total (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread (c/v): **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 5) LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 0.0, 0.5)

st.markdown("🔍 **Comparación de spreads (GLOBAL)**")
modelo_spread_formato_casa = -spread_modelo
st.write(f"- Modelo (formato casa): **LOCAL {modelo_spread_formato_casa:+.1f}**")
st.write(f"- Casa: **LOCAL {spread_casa:+.1f}**")
dif_spread_global = modelo_spread_formato_casa - spread_casa
st.write(f"- **DIF. SPREAD (GLOBAL): {dif_spread_global:+.1f} pts**")

st.markdown("🔍 **Comparación de totales (GLOBAL)**")
st.write(f"- Modelo: **{total_modelo:.1f}**")
st.write(f"- Casa: **{total_casa:.1f}**")
dif_total_global = total_modelo - total_casa
st.write(f"- **DIF. TOTAL (GLOBAL): {dif_total_global:+.1f} pts**")

# alerta específica
if abs(dif_spread_global) >= 3 and abs(dif_total_global) >= 10:
    st.error("⚠️ Línea muy diferente a tu modelo (spread y total). Puede ser trap line o te falta info.")
else:
    if abs(dif_spread_global) >= 3:
        st.error("⚠️ Línea muy diferente a tu modelo **en el spread**. Puede ser trap line o te falta info.")
    elif abs(dif_total_global) >= (12 if liga == "NBA" else 8):
        st.error("⚠️ Línea muy diferente a tu modelo **en el total**. Puede ser trap line o te falta info.")

# =========================================================
# 5b) MONEYLINE DEL SPORTSBOOK (opcional)
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
c7, c8 = st.columns(2)
with c7:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0.0, step=5.0)
with c8:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0.0, step=5.0)

def ml_to_prob(ml):
    if ml == 0:
        return None
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return -ml / (-ml + 100)

prob_imp_local = ml_to_prob(ml_local)
prob_imp_visita = ml_to_prob(ml_visita)

st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
# prob de victoria del modelo -> lo saco del spread del modelo con una sigmoide suave
import math
def prob_from_spread(spread_points):
    # spread_points positivo = local mejor
    # 6 pts ~ 70%, 3 pts ~ 60%
    return 1 / (1 + math.exp(-0.35 * spread_points))

prob_modelo_local = prob_from_spread(spread_modelo) * 100
prob_modelo_visita = 100 - prob_modelo_local

st.write(f"{local or 'LOCAL'} (modelo): **{prob_modelo_local:.1f}%**")
st.write(f"{visita or 'VISITA'} (modelo): **{prob_modelo_visita:.1f}%**")
if prob_imp_local is not None:
    st.write(f"Prob. implícita LOCAL (casa): **{prob_imp_local*100:.1f}%**")
if prob_imp_visita is not None:
    st.write(f"Prob. implícita VISITA (casa): **{prob_imp_visita*100:.1f}%**")

# =========================================================
# 6) SIMULACIÓN MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv = max(5, total_modelo * 0.15)
covers, overs = 0, 0
for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local, desv))
    sim_v = max(0, random.gauss(pts_visita, desv))
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover_global = covers / num_sims * 100
prob_over_global = overs / num_sims * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6b) SIMULACIÓN MONTE CARLO (CASA / VISITA)
# =========================================================
st.subheader("6b) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_cv = None
prob_over_cv = None

if hay_cv:
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
    st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (CASA/VISITA): **{prob_cover_cv:.1f}%**")
    st.write(f"Prob. de OVER (CASA/VISITA): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 7) APUESTAS RECOMENDADAS (si ≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

# spread global
prob_visita_spread_global = 100 - prob_cover_global
if prob_cover_global >= 55:
    recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_global))
elif prob_visita_spread_global >= 55:
    recs.append((f"Spread GLOBAL: {visita or 'VISITA'} {-spread_casa:+.1f}", prob_visita_spread_global))

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= 55:
    recs.append((f"Total GLOBAL: OVER {total_casa:.1f}", prob_over_global))
elif prob_under_global >= 55:
    recs.append((f"Total GLOBAL: UNDER {total_casa:.1f}", prob_under_global))

# casa/visita si hay
if hay_cv and prob_cover_cv is not None:
    p_visit_cv = 100 - prob_cover_cv
    if prob_cover_cv >= 55:
        recs.append((f"Spread C/V: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_cv))
    elif p_visit_cv >= 55:
        recs.append((f"Spread C/V: {visita or 'VISITA'} {-spread_casa:+.1f}", p_visit_cv))

if hay_cv and prob_over_cv is not None:
    p_under_cv = 100 - prob_over_cv
    if prob_over_cv >= 55:
        recs.append((f"Total C/V: OVER {total_casa:.1f}", prob_over_cv))
    elif p_under_cv >= 55:
        recs.append((f"Total C/V: UNDER {total_casa:.1f}", p_under_cv))

if recs:
    for txt, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"✅ {txt} — **{p:.1f}%**")
else:
    st.info("Ninguna apuesta pasó el 55% en la simulación.")

# =========================================================
# 8) EDGE DEL MODELO VS CASA (spread)
# =========================================================
st.subheader("8) Edge del modelo vs casa")

# edge spread local = prob_modelo_local - prob_implicita_local
edge_local = None
edge_visita = None

if prob_imp_local is not None:
    edge_local = prob_modelo_local - (prob_imp_local * 100)
if prob_imp_visita is not None:
    edge_visita = prob_modelo_visita - (prob_imp_visita * 100)

if edge_local is not None:
    if edge_local >= 5:
        st.success(f"Edge LOCAL: +{edge_local:.1f}% (el modelo ve más valor que la casa)")
    elif edge_local <= -5:
        st.error(f"Edge LOCAL: {edge_local:.1f}% (la casa lo trae más alto; cuidado)")
    else:
        st.write(f"Edge LOCAL: {edge_local:.1f}%")

if edge_visita is not None:
    if edge_visita >= 5:
        st.success(f"Edge VISITA: +{edge_visita:.1f}% (el modelo ve más valor que la casa)")
    elif edge_visita <= -5:
        st.error(f"Edge VISITA: {edge_visita:.1f}% (la casa lo trae más alto; cuidado)")
    else:
        st.write(f"Edge VISITA: {edge_visita:.1f}%")
