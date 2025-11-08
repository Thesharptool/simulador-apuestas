import streamlit as st
import random
import requests

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.caption("Modelo ponderado v3.2 • NFL API + Monte Carlo")

# =========================
# 0. DATOS NFL
# =========================
API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
SEASON = "2025REG"

@st.cache_data(ttl=600)
def cargar_nfl(api_key, season):
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"Error {r.status_code}"
        data = r.json()
    except Exception as e:
        return {}, f"Error: {e}"

    equipos = {}
    for t in data:
        name = (t.get("Name") or "").lower()
        wins = t.get("Wins", 0) or 0
        losses = t.get("Losses", 0) or 0
        ties = t.get("Ties", 0) or 0
        pf = t.get("PointsFor", 0.0) or 0.0
        pa = t.get("PointsAgainst", 0.0) or 0.0

        jugados = wins + losses + ties
        games = jugados if jugados > 0 else (t.get("Games", 0) or 1)

        equipos[name] = {
            "pf_pg": round(pf / games, 2),
            "pa_pg": round(pa / games, 2),
        }
    return equipos, ""

nfl_data, nfl_err = cargar_nfl(API_KEY, SEASON)
if nfl_err:
    st.warning(f"⚠️ {nfl_err}")
else:
    st.info(f"✅ NFL {SEASON} cargada ({len(nfl_data)} equipos)", icon="✅")

# =========================
# 1. ENTRADA DE PARTIDO
# =========================
st.subheader("1) Datos del partido")

c_local, c_visita = st.columns(2)

with c_local:
    local = st.text_input("Equipo LOCAL", "", key="local_name")
    if st.button("Rellenar LOCAL desde NFL"):
        k = local.strip().lower()
        if k in nfl_data:
            st.session_state["l_anota_global"] = nfl_data[k]["pf_pg"]
            st.session_state["l_permite_global"] = nfl_data[k]["pa_pg"]
            st.success(f"Local rellenado: {local}")
        else:
            st.error("No encontré ese equipo.")

    l_anota_global = st.number_input(
        "Local anota (global)",
        value=st.session_state.get("l_anota_global", 0.0),
        step=0.1,
        key="l_anota_global",
    )
    l_permite_global = st.number_input(
        "Local permite (global)",
        value=st.session_state.get("l_permite_global", 0.0),
        step=0.1,
        key="l_permite_global",
    )

with c_visita:
    visita = st.text_input("Equipo VISITA", "", key="visita_name")
    if st.button("Rellenar VISITA desde NFL"):
        k = visita.strip().lower()
        if k in nfl_data:
            st.session_state["v_anota_global"] = nfl_data[k]["pf_pg"]
            st.session_state["v_permite_global"] = nfl_data[k]["pa_pg"]
            st.success(f"Visita rellenado: {visita}")
        else:
            st.error("No encontré ese equipo.")

    v_anota_global = st.number_input(
        "Visita anota (global)",
        value=st.session_state.get("v_anota_global", 0.0),
        step=0.1,
        key="v_anota_global",
    )
    v_permite_global = st.number_input(
        "Visita permite (global)",
        value=st.session_state.get("v_permite_global", 0.0),
        step=0.1,
        key="v_permite_global",
    )

# =========================
# 2. CASA / VISITA
# =========================
with st.expander("2) Promedios por condición (opcional)", expanded=False):
    cc1, cc2 = st.columns(2)
    with cc1:
        l_anota_casa = st.number_input("Local anota en casa", value=0.0, step=0.1)
        l_permite_casa = st.number_input("Local permite en casa", value=0.0, step=0.1)
    with cc2:
        v_anota_visita = st.number_input("Visita anota de visita", value=0.0, step=0.1)
        v_permite_visita = st.number_input("Visita permite de visita", value=0.0, step=0.1)

hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

# =========================
# 3. AJUSTE
# =========================
with st.expander("3) Ajuste por lesiones / QB", expanded=False):
    aj1, aj2 = st.columns(2)
    with aj1:
        af_local = st.checkbox("¿Afecta LOCAL?", False)
        mult_local = st.slider("Multiplicador LOCAL", 0.5, 1.1, 1.0, 0.05)
    with aj2:
        af_visita = st.checkbox("¿Afecta VISITA?", False)
        mult_visita = st.slider("Multiplicador VISITA", 0.5, 1.1, 1.0, 0.05)

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# =========================
# 4. FUNCIÓN MODELO
# =========================
def proyeccion(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5
    return base

# =========================
# 5. PROYECCIONES (ahora vertical)
# =========================
st.subheader("4) Proyección del modelo")

# GLOBAL
pts_local = proyeccion(l_anota_global, v_permite_global, True) * mult_local
pts_visita = proyeccion(v_anota_global, l_permite_global, False) * mult_visita
total = pts_local + pts_visita
spread = pts_local - pts_visita

st.markdown("**🟦 GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita:.1f} pts**")
st.write(f"- Total modelo: **{total:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread:+.1f}**")

# CASA / VISITA
if hay_cv:
    pts_local_cv = proyeccion(l_anota_casa or l_anota_global,
                              v_permite_visita or v_permite_global,
                              True) * mult_local
    pts_visita_cv = proyeccion(v_anota_visita or v_anota_global,
                               l_permite_casa or l_permite_global,
                               False) * mult_visita
    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.markdown("**🟩 CASA / VISITA**")
    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total casa/visita: **{total_cv:.1f}**")
    st.write(f"- Spread casa/visita: **{spread_cv:+.1f}**")
else:
    total_cv, spread_cv = None, None

# =========================
# 6. LÍNEA DEL CASINO Y DIFERENCIAS
# =========================
st.subheader("5) Línea del casino y diferencias")
lc1, lc2 = st.columns(2)
with lc1:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with lc2:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 0.0, 0.5)

modelo_spread_formato_casa = -spread
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total - total_casa

st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

if hay_cv and total_cv is not None:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.write(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.write(f"🟩 Dif. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")

# =========================
# 7. MONTE CARLO (GLOBAL)
# =========================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Simulaciones", 1000, 50000, 10000, 1000)
covers = 0
overs = 0
desv = max(5, total * 0.15)

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

st.write(f"- Prob. cubrir spread (LOCAL): **{prob_cover:.1f}%**")
st.write(f"- Prob. OVER: **{prob_over:.1f}%**")
st.write(f"- Prob. UNDER: **{prob_under:.1f}%**")

# =========================
# 8. APUESTAS RECOMENDADAS (≥55%)
# =========================
st.subheader("7) Apuestas recomendadas (solo ≥55%)")

recomendaciones = []

# spread local y visita
if prob_cover >= 55:
    recomendaciones.append((f"Spread {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover))

if (100 - prob_cover) >= 55:
    recomendaciones.append((f"Spread {visita or 'VISITA'} {-spread_casa:+.1f}", 100 - prob_cover))

# totales
if prob_over >= 55:
    recomendaciones.append((f"OVER {total_casa}", prob_over))

if prob_under >= 55:
    recomendaciones.append((f"UNDER {total_casa}", prob_under))

if recomendaciones:
    for ap, pr in recomendaciones:
        st.success(f"📌 {ap} — **{pr:.1f}%**")
else:
    st.warning("Ninguna opción pasa el 55%. Cambia datos o línea del casino.")

st.caption("Solo muestra las que tienen buena probabilidad. No calcula valor por cuota.")
