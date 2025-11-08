import streamlit as st
import random
import requests

# =========================================================
# CONFIGURACIÓN BÁSICA
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (v3)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA  
Si llenas casa/visita te muestra las dos proyecciones.
""")

# =========================================================
# 0. DATOS NFL DESDE SPORTSDATAIO
# =========================================================
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
SEASON = "2025REG"

@st.cache_data(ttl=600)
def cargar_nfl_desde_api(api_key: str, season: str):
    """Obtiene promedios reales por juego, usando solo los juegos jugados."""
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
# 1. DATOS DEL PARTIDO
# =========================================================
st.subheader("Datos del partido")
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
# 2. CASA / VISITA (los llenas tú)
# =========================================================
st.subheader("Promedios por condición (opcional)")
c1, c2 = st.columns(2)
with c1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", value=0.0, step=0.1)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", value=0.0, step=0.1)
with c2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", value=0.0, step=0.1)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", value=0.0, step=0.1)

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
# 4. FUNCIÓN MODELO
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
total = pts_local + pts_visita
spread = pts_local - pts_visita
st.write(
    f"{local or 'LOCAL'}: **{pts_local:.1f}** | "
    f"{visita or 'VISITA'}: **{pts_visita:.1f}** | "
    f"Total modelo: **{total:.1f}** | "
    f"Spread modelo (local - visita): **{spread:+.1f}**"
)

# =========================================================
# 5.b PROYECCIÓN CASA / VISITA
# =========================================================
st.subheader("🟩 Proyección del modelo (CASA / VISITA)")
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

    st.write(
        f"{local or 'LOCAL'} (casa): **{pts_local_cv:.1f}** | "
        f"{visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}** | "
        f"Total casa/visita: **{total_cv:.1f}** | "
        f"Spread casa/visita: **{spread_cv:+.1f}**"
    )
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 6. LÍNEA DEL CASINO
# =========================================================
st.subheader("Línea del casino")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread (línea del casino) — negativo si LOCAL es favorito", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U del casino)", 0.0, 300.0, 0.0, 0.5)

# =========================================================
# 6.b DIFERENCIAS VS LÍNEA (lo que pediste)
# =========================================================
st.subheader("Diferencias vs la línea del casino")

# GLOBAL
# modelo da spread = local - visita
# la casa da spread = “cuántos puntos le quitamos al LOCAL”
# para comparar: pasamos nuestro spread a formato casa:
modelo_spread_formato_casa = -spread
dif_spread_global = modelo_spread_formato_casa - spread_casa
st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")

# CASA / VISITA
if hay_cv:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    st.write(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")

# =========================================================
# 7. MONTE CARLO GLOBAL
# =========================================================
st.subheader("Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones", 1000, 50000, 10000, 1000)
covers, overs = 0, 0
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

st.write(f"Prob. que {local or 'LOCAL'} cubra el spread (GLOBAL): **{prob_cover:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over:.1f}%**")
st.write(f"Prob. de UNDER (GLOBAL): **{prob_under:.1f}%**")

# =========================================================
# 8. MONTE CARLO CASA / VISITA
# =========================================================
st.subheader("Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_cv = None
prob_over_cv = None

if hay_cv:
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

    st.write(f"Prob. que {local or 'LOCAL'} cubra (CASA/VISITA): **{prob_cover_cv:.1f}%**")
    st.write(f"Prob. de OVER (CASA/VISITA): **{prob_over_cv:.1f}%**")
    st.write(f"Prob. de UNDER (CASA/VISITA): **{prob_under_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 9. APUESTA RECOMENDADA
# =========================================================
st.subheader("Apuesta recomendada 🟣")

opciones = []

# spread global (local o visita)
prob_visita_spread = 100 - prob_cover
opciones.append((f"Spread {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover))
opciones.append((f"Spread {visita or 'VISITA'} {-spread_casa:+.1f}", prob_visita_spread))

# total global
opciones.append((f"OVER {total_casa}", prob_over))
opciones.append((f"UNDER {total_casa}", prob_under))

mejor = max(opciones, key=lambda x: x[1])
st.success(f"📌 Apuesta con mayor % de pegar: **{mejor[0]}**")
st.write(f"Probabilidad estimada: **{mejor[1]:.1f}%**")
st.caption("No está considerando cuotas, solo el % más alto.")
