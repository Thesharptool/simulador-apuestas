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
# 0. SELECCIÓN DE LIGA
# =========================================================
# Usamos la MISMA key para NFL y NBA (la que ya tienes activa)
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"

# Puedes cambiar las seasons si ves 404 en NBA
LEAGUES = {
    "NFL": {
        "season": "2025REG",
        "url": "https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}",
        "home_adv": 1.5,   # ventaja local usada en el modelo
    },
    "NBA": {
        # en SportsDataIO la NBA suele ir "2025" o "2024"
        "season": "2025",
        "url": "https://api.sportsdata.io/v3/nba/scores/json/Standings/{season}",
        "home_adv": 3.0,   # en NBA el local influye un poco más
    },
}

liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# si cambias de liga, limpiamos algunos valores
if "current_league" not in st.session_state:
    st.session_state["current_league"] = liga
elif st.session_state["current_league"] != liga:
    # reseteo rápido
    for k in [
        "l_anota_global", "l_permite_global",
        "v_anota_global", "v_permite_global",
    ]:
        st.session_state[k] = 0.0
    st.session_state["current_league"] = liga

# =========================================================
# 1. CARGA DE DATOS DESDE LA API (por liga)
# =========================================================
@st.cache_data(ttl=600)
def cargar_equipos_desde_api(api_key: str, liga_key: str):
    cfg = LEAGUES[liga_key]
    url = cfg["url"].format(season=cfg["season"])
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {}, f"Error {resp.status_code} al conectar con SportsDataIO ({liga_key})"
        data = resp.json()
    except Exception as e:
        return {}, f"Error de conexión: {e}"

    equipos = {}
    for t in data:
        name = (t.get("Name") or "").lower()

        # estas claves existen tanto en NFL como en NBA standings
        wins = t.get("Wins", 0) or 0
        losses = t.get("Losses", 0) or 0
        ties = t.get("Ties", 0) or 0  # en NBA casi nunca
        pf = t.get("PointsFor", 0.0) or 0.0
        pa = t.get("PointsAgainst", 0.0) or 0.0

        played = wins + losses + ties
        games_raw = t.get("Games", 0) or 0
        games_played = played if played > 0 else games_raw if games_raw > 0 else 1

        equipos[name] = {
            "pf_pg": round(pf / games_played, 2),
            "pa_pg": round(pa / games_played, 2),
        }

    return equipos, ""

datos_liga, err_liga = cargar_equipos_desde_api(SPORTSDATAIO_KEY, liga)
if err_liga:
    st.warning(f"⚠️ {err_liga}")
else:
    st.info(f"✅ {liga}: datos cargados, {len(datos_liga)} equipos ({LEAGUES[liga]['season']})")

# =========================================================
# 2. DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

# ---- LOCAL
with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")
    if st.button("Rellenar LOCAL desde API", key="btn_local"):
        lookup = local.strip().lower()
        if lookup in datos_liga:
            st.session_state["l_anota_global"] = datos_liga[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = datos_liga[lookup]["pa_pg"]
            st.success(f"{liga}: LOCAL rellenado con datos reales de {local}")
        else:
            st.error("No encontré ese equipo en la API para esta liga")

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

# ---- VISITA
with col2:
    visita = st.text_input("Equipo VISITA", "", key="visita_name")
    if st.button("Rellenar VISITA desde API", key="btn_visita"):
        lookup = visita.strip().lower()
        if lookup in datos_liga:
            st.session_state["v_anota_global"] = datos_liga[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = datos_liga[lookup]["pa_pg"]
            st.success(f"{liga}: VISITA rellenado con datos reales de {visita}")
        else:
            st.error("No encontré ese equipo en la API para esta liga")

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
# 3. PROMEDIOS POR CONDICIÓN (lo dejas tú manual)
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
# 4. AJUSTE POR LESIONES
# =========================================================
st.subheader("3) Ajuste por lesiones / QB")
aj1, aj2 = st.columns(2)
with aj1:
    af_local = st.checkbox("¿Afecta ofensiva LOCAL?", False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
with aj2:
    af_visita = st.checkbox("¿Afecta ofensiva VISITA?", False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# =========================================================
# 5. FUNCIÓN DEL MODELO
# =========================================================
def proyeccion(ofensiva, defensa, es_local=False, liga_key="NFL"):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += LEAGUES[liga_key]["home_adv"]
    return base

# =========================================================
# 6. PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

# GLOBAL
pts_local = proyeccion(l_anota_global, v_permite_global, True, liga) * mult_local
pts_visita = proyeccion(v_anota_global, l_permite_global, False, liga) * mult_visita
total_global = pts_local + pts_visita
spread_global = pts_local - pts_visita   # local - visita

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'} : **{pts_local:.1f} pts**")
st.write(f"- {visita or 'VISITA'} : **{pts_visita:.1f} pts**")
st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

# CASA / VISITA (solo si rellenaste algo)
if hay_cv:
    pts_local_cv = proyeccion(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        True,
        liga
    ) * mult_local
    pts_visita_cv = proyeccion(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        False,
        liga
    ) * mult_visita
    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.markdown("🟩 **CASA / VISITA**")
    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
else:
    total_cv = None
    spread_cv = None
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 7. LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
lc1, lc2 = st.columns(2)
with lc1:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with lc2:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 350.0, 0.0, 0.5)

st.markdown("**Diferencias vs línea (GLOBAL)**")
modelo_spread_formato_casa = -spread_global  # porque el casino usa vista=+, local=-
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total_global - total_casa
st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

if hay_cv:
    st.markdown("**Diferencias vs línea (CASA/VISITA)**")
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.write(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.write(f"🟩 Dif. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")

# =========================================================
# 8. MONTE CARLO GLOBAL
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv = max(5, total_global * 0.15)
covers, overs = 0, 0
for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local, desv))
    sim_v = max(0, random.gauss(pts_visita, desv))
    # cubrir spread de la casa
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    # over
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover_global = covers / num_sims * 100
prob_over_global = overs / num_sims * 100
prob_under_global = 100 - prob_over_global

st.write(f"Prob. que **{local or 'LOCAL'}** cubra el spread (GLOBAL): **{prob_cover_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 9. MONTE CARLO CASA/VISITA
# =========================================================
prob_cover_cv = None
prob_over_cv = None
if hay_cv:
    st.subheader("7) Simulación Monte Carlo 🟩 (CASA / VISITA)")
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="cv_sims")
    desv_cv = max(5, total_cv * 0.15)
    covers_cv, overs_cv = 0, 0
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

# =========================================================
# 10. APUESTAS RECOMENDADAS (todas las >55%)
# =========================================================
st.subheader("8) Apuestas recomendadas (si ≥ 55%)")
recs = []

# GLOBAL spread
prob_visita_cover_global = 100 - prob_cover_global
if prob_cover_global >= prob_visita_cover_global:
    if prob_cover_global >= 55:
        recs.append((f"Spread (GLOBAL): {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_global))
else:
    visita_linea = -spread_casa
    if prob_visita_cover_global >= 55:
        recs.append((f"Spread (GLOBAL): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_cover_global))

# GLOBAL total
if prob_over_global >= prob_under_global:
    if prob_over_global >= 55:
        recs.append((f"Total (GLOBAL): OVER {total_casa}", prob_over_global))
else:
    if prob_under_global >= 55:
        recs.append((f"Total (GLOBAL): UNDER {total_casa}", prob_under_global))

# CASA/VISITA spread
if hay_cv and prob_cover_cv is not None:
    prob_visita_cover_cv = 100 - prob_cover_cv
    if prob_cover_cv >= prob_visita_cover_cv:
        if prob_cover_cv >= 55:
            recs.append((f"Spread (CASA/VISITA): {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_cv))
    else:
        visita_linea = -spread_casa
        if prob_visita_cover_cv >= 55:
            recs.append((f"Spread (CASA/VISITA): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_cover_cv))

# CASA/VISITA total
if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= prob_under_cv:
        if prob_over_cv >= 55:
            recs.append((f"Total (CASA/VISITA): OVER {total_casa}", prob_over_cv))
    else:
        if prob_under_cv >= 55:
            recs.append((f"Total (CASA/VISITA): UNDER {total_casa}", prob_under_cv))

if recs:
    for txt, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"{txt} → **{p:.1f}%**")
else:
    st.info("Ninguna apuesta superó el 55%.")
