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
# 2. CASA / VISITA (los dejas tú a mano)
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
# 5. PROYECCIONES
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
# 6. MONTE CARLO
# =========================================================
st.subheader("Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones", 1000, 50000, 10000, 1000)
spread_casa = st.number_input("Spread (línea del casino)", -50.0, 50.0, 0.0, 0.5)
total_casa = st.number_input("Total (O/U del casino)", 0.0, 300.0, 0.0, 0.5)

covers, overs = 0, 0
desv = max(5, total * 0.15)
for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local, desv))
    sim_v = max(0, random.gauss(pts_visita, desv))

    # cubrir spread de la casa (la casa está expresada como LOCAL)
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1

    # over
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover = covers / num_sims * 100          # prob de que gane el lado del LOCAL con esa línea
prob_over = overs / num_sims * 100
st.write(f"Prob. que {local or 'LOCAL'} cubra el spread: **{prob_cover:.1f}%**")
st.write(f"Prob. de OVER: **{prob_over:.1f}%**")

# =========================================================
# 7. APUESTA RECOMENDADA (lo que te faltaba)
# =========================================================
st.subheader("Apuesta recomendada 🟣")

# prob del otro lado del spread (la visita)
prob_cover_visita = 100 - prob_cover

# prob del under
prob_under = 100 - prob_over

opciones = [
    (f"Spread {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover),
    (f"Spread {visita or 'VISITA'} {-spread_casa:+.1f}", prob_cover_visita),
    (f"OVER {total_casa}", prob_over),
    (f"UNDER {total_casa}", prob_under),
]

mejor = max(opciones, key=lambda x: x[1])

st.success(f"📌 Apuesta con mayor % de pegar: **{mejor[0]}**")
st.write(f"Probabilidad estimada por la simulación: **{mejor[1]:.1f}%**")
st.caption("No está considerando cuotas, solo el % más alto.")
