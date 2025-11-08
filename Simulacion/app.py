import streamlit as st
import requests
import random

# ======================================================
# CONFIGURACIÓN INICIAL
# ======================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🔴 **Modelo ponderado activo (v3.1)**")
st.markdown(
    """
🟦 = cálculo con promedios **GLOBAL**  
🟩 = cálculo con promedios **CASA/VISITA**  
Si llenas casa/visita te muestra las dos proyecciones.
"""
)

# ======================================================
# 0. DESCARGAR DATOS NFL (GLOBAL) DESDE SPORTSDATA.IO
# ======================================================
API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"  # la que salió en tu captura
SEASON = "2025REG"  # así venía en tu panel

nfl_equipos = {}
status_msg = st.empty()

try:
    status_msg.info(f"🔄 Conectando con SportsDataIO → {SEASON}")
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{SEASON}?key={API_KEY}"
    resp = requests.get(url, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        for team in data:
            nombre = team.get("Name", "").strip()
            games = team.get("Games", 0) or 0
            pf = team.get("PointsFor", 0) or 0
            pa = team.get("PointsAgainst", 0) or 0

            if games > 0:
                pf_pg = round(pf / games, 2)
                pa_pg = round(pa / games, 2)
            else:
                pf_pg = 0.0
                pa_pg = 0.0

            nfl_equipos[nombre.lower()] = {
                "name": nombre,
                "pf_pg": pf_pg,
                "pa_pg": pa_pg,
            }
        status_msg.success(f"✅ Datos NFL cargados, {len(nfl_equipos)} equipos ({SEASON})")
    else:
        status_msg.warning(f"⚠️ No pude traer datos NFL: {resp.status_code}")
except Exception as e:
    status_msg.error(f"⚠️ Error conectando a SportsDataIO: {e}")

# ======================================================
# 1. DATOS DEL PARTIDO
# ======================================================
st.subheader("Datos del partido")
col1, col2 = st.columns(2)

# Para poder rellenar los number_input con botones, usamos session_state
if "l_anota_global" not in st.session_state:
    st.session_state["l_anota_global"] = 0.0
if "l_permite_global" not in st.session_state:
    st.session_state["l_permite_global"] = 0.0
if "v_anota_global" not in st.session_state:
    st.session_state["v_anota_global"] = 0.0
if "v_permite_global" not in st.session_state:
    st.session_state["v_permite_global"] = 0.0

with col1:
    local = st.text_input("Equipo LOCAL", value=st.session_state.get("local_name", ""))
    if st.button("Rellenar LOCAL desde NFL"):
        key = local.strip().lower()
        if key in nfl_equipos:
            datos = nfl_equipos[key]
            st.session_state["l_anota_global"] = datos["pf_pg"]
            st.session_state["l_permite_global"] = datos["pa_pg"]
            st.session_state["local_name"] = datos["name"]
            st.success(f"LOCAL rellenado con datos reales de {datos['name']}")
        else:
            st.warning("No encontré ese equipo en los datos NFL.")

    st.markdown("**Promedios GLOBAL del LOCAL**")
    l_anota_global = st.number_input(
        "Local: puntos que ANOTA (global)",
        value=st.session_state["l_anota_global"],
        step=0.1,
        key="l_anota_global_input",
    )
    # sincronizamos
    st.session_state["l_anota_global"] = l_anota_global

    l_permite_global = st.number_input(
        "Local: puntos que PERMITE (global)",
        value=st.session_state["l_permite_global"],
        step=0.1,
        key="l_permite_global_input",
    )
    st.session_state["l_permite_global"] = l_permite_global

with col2:
    visita = st.text_input("Equipo VISITA", value=st.session_state.get("visita_name", ""))
    if st.button("Rellenar VISITA desde NFL"):
        key = visita.strip().lower()
        if key in nfl_equipos:
            datos = nfl_equipos[key]
            st.session_state["v_anota_global"] = datos["pf_pg"]
            st.session_state["v_permite_global"] = datos["pa_pg"]
            st.session_state["visita_name"] = datos["name"]
            st.success(f"VISITA rellenado con datos reales de {datos['name']}")
        else:
            st.warning("No encontré ese equipo en los datos NFL.")

    st.markdown("**Promedios GLOBAL del VISITA**")
    v_anota_global = st.number_input(
        "Visita: puntos que ANOTA (global)",
        value=st.session_state["v_anota_global"],
        step=0.1,
        key="v_anota_global_input",
    )
    st.session_state["v_anota_global"] = v_anota_global

    v_permite_global = st.number_input(
        "Visita: puntos que PERMITE (global)",
        value=st.session_state["v_permite_global"],
        step=0.1,
        key="v_permite_global_input",
    )
    st.session_state["v_permite_global"] = v_permite_global

# ======================================================
# 2. PROMEDIOS POR CONDICIÓN (los dejamos EN BLANCO)
# ======================================================
st.subheader("Promedios por condición (opcional)")
c1, c2 = st.columns(2)
with c1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", value=0.0, step=0.1)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", value=0.0, step=0.1)
with c2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", value=0.0, step=0.1)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", value=0.0, step=0.1)

hay_cv = any([
    l_anota_casa > 0,
    l_permite_casa > 0,
    v_anota_visita > 0,
    v_permite_visita > 0,
])

# ======================================================
# 3. AJUSTE POR LESIONES / QB
# ======================================================
st.subheader("Ajuste por lesiones / QB")
c3, c4 = st.columns(2)
with c3:
    af_local = st.checkbox("¿Afecta ofensiva LOCAL?", value=False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
with c4:
    af_visita = st.checkbox("¿Afecta ofensiva VISITA?", value=False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# ======================================================
# 4. FUNCIÓN DEL MODELO
# ======================================================
def proyeccion_suavizada(ofensiva_propia, defensa_rival, es_local=False):
    base = 0.55 * ofensiva_propia + 0.35 * defensa_rival
    if es_local:
        base += 1.5
    return base

# ======================================================
# 5. PROYECCIÓN DEL MODELO (GLOBAL)
# ======================================================
st.subheader("🟦 Proyección del modelo (GLOBAL)")

pts_local_global = proyeccion_suavizada(
    st.session_state["l_anota_global"],
    st.session_state["v_permite_global"],
    es_local=True
) * mult_local

pts_visita_global = proyeccion_suavizada(
    st.session_state["v_anota_global"],
    st.session_state["l_permite_global"],
    es_local=False
) * mult_visita

total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global  # positivo: LOCAL mejor

st.write(f"Puntos esperados {local or 'LOCAL'}: **{pts_local_global:.1f}**")
st.write(f"Puntos esperados {visita or 'VISITA'}: **{pts_visita_global:.1f}**")
st.write(f"Total GLOBAL del modelo: **{total_global:.1f}**")
st.write(f"Spread GLOBAL del modelo (local - visita): **{spread_global:+.1f}**")

# ======================================================
# 6. PROYECCIÓN CASA / VISITA (solo si tú llenas)
# ======================================================
st.subheader("🟩 Proyección del modelo (CASA / VISITA)")
if hay_cv:
    pts_local_cv = proyeccion_suavizada(
        l_anota_casa if l_anota_casa > 0 else st.session_state["l_anota_global"],
        v_permite_visita if v_permite_visita > 0 else st.session_state["v_permite_global"],
        es_local=True
    ) * mult_local

    pts_visita_cv = proyeccion_suavizada(
        v_anota_visita if v_anota_visita > 0 else st.session_state["v_anota_global"],
        l_permite_casa if l_permite_casa > 0 else st.session_state["l_permite_global"],
        es_local=False
    ) * mult_visita

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"Puntos esperados {local or 'LOCAL'} (casa): **{pts_local_cv:.1f}**")
    st.write(f"Puntos esperados {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}**")
    st.write(f"Total CASA/VISITA del modelo: **{total_cv:.1f}**")
    st.write(f"Spread CASA/VISITA del modelo: **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# ======================================================
# 7. LÍNEA REAL DEL SPORTSBOOK
# ======================================================
st.subheader("Línea real del sportsbook")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread de la casa (negativo si LOCAL es favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) de la casa", 0.0, 300.0, 0.0, 0.5)

# ======================================================
# 8. DIFERENCIAS vs LÍNEA
# ======================================================
st.subheader("Diferencias vs línea real")

modelo_spread_formato_casa = -spread_global
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total_global - total_casa

st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

if abs(dif_spread_global) >= 8:
    st.error("⚠️ El spread del modelo está MUY lejos de la línea. Revisa datos o hay posible value.")
elif abs(dif_spread_global) >= 5:
    st.warning("⚠️ El spread del modelo está distinto a la línea, revísalo.")

if hay_cv:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa

    st.write(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.write(f"🟩 Dif. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")

# ======================================================
# 9. SIMULACIÓN MONTE CARLO (GLOBAL)
# ======================================================
st.subheader("Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)

desv_global = max(5, total_global * 0.15)
covers = 0
overs = 0

for _ in range(num_sims_global):
    sim_local = max(0, random.gauss(pts_local_global, desv_global))
    sim_visita = max(0, random.gauss(pts_visita_global, desv_global))

    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1

    if (sim_local + sim_visita) > total_casa:
        overs += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra el spread (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# ======================================================
# 10. SIMULACIÓN MONTE CARLO (CASA/VISITA)
# ======================================================
st.subheader("Simulación Monte Carlo 🟩 (CASA / VISITA)")
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

# ======================================================
# 11. APUESTA RECOMENDADA
# ======================================================
st.subheader("Apuesta recomendada 🟣")

opciones = []

# spread global (local o visita)
prob_visita_spread_global = 100 - prob_cover_local_global
if prob_cover_local_global >= prob_visita_spread_global:
    opciones.append((
        f"Spread (GLOBAL): {local or 'LOCAL'} {spread_casa}",
        prob_cover_local_global
    ))
else:
    visita_linea = -spread_casa
    opciones.append((
        f"Spread (GLOBAL): {visita or 'VISITA'} {visita_linea:+.1f}",
        prob_visita_spread_global
    ))

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= prob_under_global:
    opciones.append((
        f"Total (GLOBAL): OVER {total_casa}",
        prob_over_global
    ))
else:
    opciones.append((
        f"Total (GLOBAL): UNDER {total_casa}",
        prob_under_global
    ))

# si hay casa/visita, también las metemos
if hay_cv and prob_cover_local_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_local_cv
    if prob_cover_local_cv >= prob_visita_spread_cv:
        opciones.append((
            f"Spread (CASA/VISITA): {local or 'LOCAL'} {spread_casa}",
            prob_cover_local_cv
        ))
    else:
        visita_linea = -spread_casa
        opciones.append((
            f"Spread (CASA/VISITA): {visita or 'VISITA'} {visita_linea:+.1f}",
            prob_visita_spread_cv
        ))

if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= prob_under_cv:
        opciones.append((
            f"Total (CASA/VISITA): OVER {total_casa}",
            prob_over_cv
        ))
    else:
        opciones.append((
            f"Total (CASA/VISITA): UNDER {total_casa}",
            prob_under_cv
        ))

if opciones:
    mejor = max(opciones, key=lambda x: x[1])
    st.success(f"📌 Apuesta sugerida: **{mejor[0]}**")
    st.write(f"Probabilidad estimada por el modelo: **{mejor[1]:.1f}%**")
    st.caption("Nota: es solo la apuesta con mayor probabilidad, no está midiendo valor/cuota.")
else:
    st.info("Llena los datos del partido y las líneas para ver una recomendación.")
