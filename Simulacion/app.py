import streamlit as st
import random
import requests

# =========================================================
# CONFIGURACIÓN BÁSICA
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
# 0. ¿QUÉ LIGA VAS A SIMULAR?
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], index=0, horizontal=True)

# =========================================================
# 0.a CARGA NFL DESDE API (solo si es NFL)
# =========================================================
SPORTSDATAIO_NFL_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
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
    nfl_data, nfl_error = cargar_nfl_desde_api(SPORTSDATAIO_NFL_KEY, NFL_SEASON)
    if nfl_error:
        st.warning(f"⚠️ {nfl_error}")
    else:
        st.info(f"✅ Datos NFL cargados — {len(nfl_data)} equipos ({NFL_SEASON})")

# =========================================================
# 1. DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")
    if liga == "NFL":
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
    if liga == "NFL":
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
# (NUEVO) 1.b PARÁMETROS NBA (solo cuando eliges NBA)
# =========================================================
if liga == "NBA":
    st.subheader("Parámetros NBA (solo totals)")
    c_nba1, c_nba2, c_nba3 = st.columns(3)
    with c_nba1:
        nba_pace_local = st.number_input("Pace LOCAL", value=100.0, step=0.5)
    with c_nba2:
        nba_pace_visita = st.number_input("Pace VISITA", value=100.0, step=0.5)
    with c_nba3:
        nba_factor_ritmo = st.slider("Ajuste ritmo (0.9 lento – 1.1 rápido)", 0.9, 1.1, 1.0, 0.01)

    c_nba4, c_nba5 = st.columns(2)
    with c_nba4:
        nba_off_loc = st.number_input("OffRating LOCAL (pts por 100)", value=112.0, step=0.5)
        nba_def_loc = st.number_input("DefRating LOCAL (pts por 100)", value=112.0, step=0.5)
    with c_nba5:
        nba_off_vis = st.number_input("OffRating VISITA (pts por 100)", value=112.0, step=0.5)
        nba_def_vis = st.number_input("DefRating VISITA (pts por 100)", value=112.0, step=0.5)

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
# 3. AJUSTE POR LESIONES / QB
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

if liga == "NFL":
    c3, c4 = st.columns(2)
    with c3:
        estado_local = st.selectbox(
            "Estado ofensivo LOCAL",
            ["Healthy / completo", "1–2 bajas importantes", "QB titular NO juega"],
            index=0,
        )
    with c4:
        estado_visita = st.selectbox(
            "Estado ofensivo VISITA",
            ["Healthy / completo", "1–2 bajas importantes", "QB titular NO juega"],
            index=0,
        )

    def mult_desde_estado(estado: str):
        if estado == "Healthy / completo":
            return 1.0
        elif estado == "1–2 bajas importantes":
            return 0.97
        elif estado == "QB titular NO juega":
            return 0.88  # castigo más fuerte
        return 1.0

    mult_local = mult_desde_estado(estado_local)
    mult_visita = mult_desde_estado(estado_visita)

else:  # NBA
    c3, c4 = st.columns(2)
    with c3:
        estado_local = st.selectbox(
            "Estado ofensivo LOCAL (NBA)",
            ["Healthy / completo", "Falta un anotador", "Rotación corta"],
            index=0,
        )
    with c4:
        estado_visita = st.selectbox(
            "Estado ofensivo VISITA (NBA)",
            ["Healthy / completo", "Falta un anotador", "Rotación corta"],
            index=0,
        )

    def mult_nba(estado: str):
        if estado == "Healthy / completo":
            return 1.0
        elif estado == "Falta un anotador":
            return 0.97
        elif estado == "Rotación corta":
            return 0.95
        return 1.0

    mult_local = mult_nba(estado_local)
    mult_visita = mult_nba(estado_visita)

st.caption("Estos multiplicadores afectan los puntos proyectados. 1.00 = normal.")

# =========================================================
# 4. FUNCIÓN DEL MODELO (base)
# =========================================================
def proyeccion_suavizada(ofensiva_propia, defensa_rival, es_local=False):
    base = 0.55 * ofensiva_propia + 0.35 * defensa_rival
    if es_local:
        base += 1.5  # ventaja casa pensada para NFL
    return base

# =========================================================
# 4. PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

# ----- GLOBAL -----
st.markdown("🟦 **GLOBAL**")

if liga == "NBA":
    # cálculo NBA con pace/ratings
    pace_prom = ((nba_pace_local + nba_pace_visita) / 2.0) * nba_factor_ritmo
    # pts = rating_ofensivo_propio + rating_defensivo_rival / 2 * pace/100
    pts_local_global = ((nba_off_loc + nba_def_vis) / 2.0) * (pace_prom / 100.0) * mult_local
    pts_visita_global = ((nba_off_vis + nba_def_loc) / 2.0) * (pace_prom / 100.0) * mult_visita
else:
    # cálculo NFL igual que antes
    pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, es_local=True) * mult_local
    pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, es_local=False) * mult_visita

total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global  # local - visita

st.write(f"* {local or 'LOCAL'} : **{pts_local_global:.1f} pts**")
st.write(f"* {visita or 'VISITA'} : **{pts_visita_global:.1f} pts**")
st.write(f"* Total modelo: **{total_global:.1f}**")
st.write(f"* Spread modelo (local - visita): **{spread_global:+.1f}**")

# ----- CASA / VISITA -----
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion_suavizada(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        es_local=True
    ) * mult_local

    pts_visita_cv = proyeccion_suavizada(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        es_local=False
    ) * mult_visita

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"* {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"* {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"* Total (casa/visita): **{total_cv:.1f}**")
    st.write(f"* Spread (casa/visita): **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 5. LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 400.0, 0.0, 0.5)

st.markdown("🔍 **Comparación de spreads (GLOBAL)**")
modelo_spread_formato_casa = -spread_global  # pasamos modelo al mismo formato que la casa
st.write(f"* Modelo (formato casa): **LOCAL {modelo_spread_formato_casa:+.1f}**")
st.write(f"* Casa: **LOCAL {spread_casa:+.1f}**")
dif_spread_global = modelo_spread_formato_casa - spread_casa
st.write(f"* DIF. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")

st.markdown("🔍 **Comparación de totales (GLOBAL)**")
st.write(f"* Modelo: **{total_global:.1f}**")
st.write(f"* Casa: **{total_casa:.1f}**")
dif_total_global = total_global - total_casa
st.write(f"* DIF. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

# alerta trap line más específica
if abs(dif_spread_global) >= 5 and abs(dif_total_global) >= 5:
    st.error("⚠️ Línea muy diferente a tu modelo en spread **y** total. Puede ser trap line o info que no estás metiendo.")
else:
    if abs(dif_spread_global) >= 5:
        st.error("⚠️ Línea muy diferente en **spread**. Revisa lesiones/QB/descanso.")
    if abs(dif_total_global) >= 8:  # en NBA los totales se mueven más
        st.error("⚠️ Línea muy diferente en **total**. Puede ser ritmo, back-to-back o bajas ofensivas.")

# =========================================================
# 5b. MONEYLINE (opcional)
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
cml1, cml2 = st.columns(2)
with cml1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with cml2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0, step=5)

def prob_implicita_from_ml(ml):
    if ml == 0:
        return 0.0
    if ml > 0:
        return 100 / (ml + 100) * 100
    else:
        return (-ml) / (-ml + 100) * 100

prob_imp_local_casa = prob_implicita_from_ml(ml_local)
prob_imp_visita_casa = prob_implicita_from_ml(ml_visita)

# prob del modelo (muy simple: puntos del modelo como %)
modelo_local_win = 0.5
if pts_local_global + pts_visita_global > 0:
    modelo_local_win = pts_local_global / (pts_local_global + pts_visita_global)
prob_modelo_local = modelo_local_win * 100
prob_modelo_visita = 100 - prob_modelo_local

st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
st.write(f"{local or 'LOCAL'} (modelo): **{prob_modelo_local:.1f}%**")
st.write(f"{visita or 'VISITA'} (modelo): **{prob_modelo_visita:.1f}%**")
if ml_local != 0:
    st.write(f"Prob. implícita LOCAL (casa): **{prob_imp_local_casa:.1f}%**")
if ml_visita != 0:
    st.write(f"Prob. implícita VISITA (casa): **{prob_imp_visita_casa:.1f}%**")

# =========================================================
# 6. MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv_global = max(5, total_global * 0.15)  # dispersión
covers = 0
overs = 0
for _ in range(num_sims_global):
    sim_local = max(0, random.gauss(pts_local_global, desv_global))
    sim_visita = max(0, random.gauss(pts_visita_global, desv_global))
    # spread: (local - visita) + línea >= 0 -> cubre LOCAL
    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1
    if (sim_local + sim_visita) > total_casa:
        overs += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6b. MONTE CARLO (CASA/VISITA)
# =========================================================
st.subheader("6b) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_local_cv = None
prob_over_cv = None
if hay_cv:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="cv_sims")
    desv_cv = max(5, total_cv * 0.15)
    covers_cv = 0
    overs_cv = 0
    for _ in range(num_sims_cv):
        sim_local = max(0, random.gauss(pts_local_cv, desv_cv))
        sim_visita = max(0, random.gauss(pts_visita_cv, desv_cv))
        if (sim_local - sim_visita) + spread_casa >= 0:
            covers_cv += 1
        if (sim_local + sim_visita) > total_casa:
            overs_cv += 1
    prob_cover_local_cv = covers_cv / num_sims_cv * 100
    prob_over_cv = overs_cv / num_sims_cv * 100
    st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (CASA/VISITA): **{prob_cover_local_cv:.1f}%**")
    st.write(f"Prob. de OVER (CASA/VISITA): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 7. APUESTAS RECOMENDADAS (si ≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

# spread global
mejor_lado_spread = local or "LOCAL"
prob_mejor_spread = prob_cover_local_global
linea_mejor_spread = spread_casa  # local con ese spread
# visita spread
prob_visita_spread = 100 - prob_cover_local_global
if prob_visita_spread > prob_mejor_spread:
    mejor_lado_spread = visita or "VISITA"
    linea_mejor_spread = -spread_casa
    prob_mejor_spread = prob_visita_spread

if prob_mejor_spread >= 55:
    recs.append(f"Spread GLOBAL: {mejor_lado_spread} {linea_mejor_spread:+.1f} — {prob_mejor_spread:.1f}%")

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= prob_under_global:
    if prob_over_global >= 55:
        recs.append(f"Total GLOBAL: OVER {total_casa:.1f} — {prob_over_global:.1f}%")
else:
    if prob_under_global >= 55:
        recs.append(f"Total GLOBAL: UNDER {total_casa:.1f} — {prob_under_global:.1f}%")

if hay_cv and prob_cover_local_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_local_cv
    mejor_cv = local or "LOCAL"
    mejor_cv_linea = spread_casa
    mejor_cv_prob = prob_cover_local_cv
    if prob_visita_spread_cv > mejor_cv_prob:
        mejor_cv = visita or "VISITA"
        mejor_cv_linea = -spread_casa
        mejor_cv_prob = prob_visita_spread_cv
    if mejor_cv_prob >= 55:
        recs.append(f"Spread CASA/VISITA: {mejor_cv} {mejor_cv_linea:+.1f} — {mejor_cv_prob:.1f}%")

    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= prob_under_cv:
        if prob_over_cv >= 55:
            recs.append(f"Total CASA/VISITA: OVER {total_casa:.1f} — {prob_over_cv:.1f}%")
    else:
        if prob_under_cv >= 55:
            recs.append(f"Total CASA/VISITA: UNDER {total_casa:.1f} — {prob_under_cv:.1f}%")

if recs:
    for r in recs:
        st.success(r)
else:
    st.info("No hay apuesta ≥ 55% según la simulación.")

# =========================================================
# 8. EDGE DEL MODELO VS CASA
# =========================================================
st.subheader("8) Edge del modelo vs casa")

# edge por spread: cuánto se aleja tu % de cubrir del 50% teórico
edge_local_spread = prob_cover_local_global - 50
edge_visita_spread = (100 - prob_cover_local_global) - 50

if edge_local_spread >= 0:
    st.success(f"Edge LOCAL (spread): +{edge_local_spread:.1f} pts de % sobre 50%.")
else:
    st.error(f"Edge LOCAL (spread): {edge_local_spread:.1f} pts por debajo de 50%.")

if edge_visita_spread >= 0:
    st.success(f"Edge VISITA (spread): +{edge_visita_spread:.1f} pts de % sobre 50%.")
else:
    st.error(f"Edge VISITA (spread): {edge_visita_spread:.1f} pts por debajo de 50%.")
