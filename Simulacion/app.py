import streamlit as st
import random
import requests

# =========================================================
# CONFIGURACIÓN
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
# 0) SELECCIONAR LIGA
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# tu misma key
API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"

NFL_SEASON = "2025REG"
NBA_SEASON = "2025"  # si tu cuenta no tiene NBA, te dará aviso

@st.cache_data(ttl=600)
def cargar_nfl(api_key: str, season: str):
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"Error {r.status_code} al conectar con SportsDataIO (NFL)"
        data = r.json()
    except Exception as e:
        return {}, f"Error de conexión NFL: {e}"

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

@st.cache_data(ttl=600)
def cargar_nba(api_key: str, season: str):
    url = f"https://api.sportsdata.io/v3/nba/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"Error {r.status_code} al conectar con SportsDataIO (NBA)"
        data = r.json()
    except Exception as e:
        return {}, f"Error de conexión NBA: {e}"

    equipos = {}
    for t in data:
        name = (t.get("Name") or "").lower()
        wins = t.get("Wins", 0) or 0
        losses = t.get("Losses", 0) or 0
        pf = t.get("PointsFor", 0.0) or 0.0
        pa = t.get("PointsAgainst", 0.0) or 0.0
        jugados = wins + losses if (wins + losses) > 0 else 1

        equipos[name] = {
            "pf_pg": round(pf / jugados, 2),
            "pa_pg": round(pa / jugados, 2),
        }
    return equipos, ""

# cargar según liga
if liga == "NFL":
    data_liga, err = cargar_nfl(API_KEY, NFL_SEASON)
else:
    data_liga, err = cargar_nba(API_KEY, NBA_SEASON)

if err:
    st.warning(f"⚠️ {err}")
else:
    st.info(f"✅ Datos {liga} cargados – {len(data_liga)} equipos")

# =========================================================
# 1) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")
    boton_local = "Rellenar LOCAL desde NFL" if liga == "NFL" else "Rellenar LOCAL desde NBA"
    if st.button(boton_local):
        lookup = local.strip().lower()
        if lookup in data_liga:
            st.session_state["l_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"LOCAL rellenado con datos reales de {local}")
        else:
            st.error("No encontré ese equipo en la API")

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
    boton_visita = "Rellenar VISITA desde NFL" if liga == "NFL" else "Rellenar VISITA desde NBA"
    if st.button(boton_visita):
        lookup = visita.strip().lower()
        if lookup in data_liga:
            st.session_state["v_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"VISITA rellenado con datos reales de {visita}")
        else:
            st.error("No encontré ese equipo en la API")

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
# 2) CASA / VISITA (manual)
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
# 3) AJUSTE POR LESIONES (con etiqueta visible)
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

aj1, aj2 = st.columns(2)
with aj1:
    af_local = st.checkbox("¿Afecta ofensiva LOCAL?", False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
    # etiqueta
    if mult_local == 1.0:
        st.caption("LOCAL: ✅ normal / healthy")
    elif mult_local < 1.0:
        st.caption("LOCAL: ❌ lesionado / bajas (anota menos)")
    else:
        st.caption("LOCAL: 🔥 en buen momento (anota más)")

with aj2:
    af_visita = st.checkbox("¿Afecta ofensiva VISITA?", False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)
    if mult_visita == 1.0:
        st.caption("VISITA: ✅ normal / healthy")
    elif mult_visita < 1.0:
        st.caption("VISITA: ❌ lesionado / bajas (anota menos)")
    else:
        st.caption("VISITA: 🔥 en buen momento (anota más)")

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# =========================================================
# 4) FUNCIÓN DEL MODELO
# =========================================================
def proyeccion(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local and liga == "NFL":
        base += 1.5
    return base

# =========================================================
# 4) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

# aplicamos multiplicadores ANTES
of_local_ajustada = l_anota_global * mult_local
of_visita_ajustada = v_anota_global * mult_visita

pts_local_global = proyeccion(of_local_ajustada, v_permite_global, es_local=True)
pts_visita_global = proyeccion(of_visita_ajustada, l_permite_global, es_local=False)
total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.markdown("🟦 **GLOBAL**")
# pintamos según si subiste/bajaste
if mult_local < 1.0:
    st.markdown(f"- {local or 'LOCAL'} : **{pts_local_global:.1f} pts** 🟥 (castigado por lesiones)")
elif mult_local > 1.0:
    st.markdown(f"- {local or 'LOCAL'} : **{pts_local_global:.1f} pts** 🟩 (mejorado)")
else:
    st.markdown(f"- {local or 'LOCAL'} : **{pts_local_global:.1f} pts**")

if mult_visita < 1.0:
    st.markdown(f"- {visita or 'VISITA'} : **{pts_visita_global:.1f} pts** 🟥 (castigado por lesiones)")
elif mult_visita > 1.0:
    st.markdown(f"- {visita or 'VISITA'} : **{pts_visita_global:.1f} pts** 🟩 (mejorado)")
else:
    st.markdown(f"- {visita or 'VISITA'} : **{pts_visita_global:.1f} pts**")

st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

# CASA / VISITA
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    of_local_cv = (l_anota_casa if l_anota_casa > 0 else l_anota_global) * mult_local
    of_visita_cv = (v_anota_visita if v_anota_visita > 0 else v_anota_global) * mult_visita
    def_local_cv = v_permite_visita if v_permite_visita > 0 else v_permite_global
    def_visita_cv = l_permite_casa if l_permite_casa > 0 else l_permite_global

    pts_local_cv = proyeccion(of_local_cv, def_local_cv, es_local=True)
    pts_visita_cv = proyeccion(of_visita_cv, def_visita_cv, es_local=False)
    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
else:
    total_cv = None
    spread_cv = None
    st.info("Si llenas los 4 campos de casa/visita te muestro también esa proyección.")

# =========================================================
# 5) LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 350.0, 0.0, 0.5)

modelo_spread_formato_casa = -spread_global
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total_global - total_casa

st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

if hay_cv:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.write(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.write(f"🟩 Dif. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")

# =========================================================
# 6) MONTE CARLO GLOBAL
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv_global = max(5, total_global * 0.15)

covers_g = 0
overs_g = 0
for _ in range(num_sims_global):
    sim_l = max(0, random.gauss(pts_local_global, desv_global))
    sim_v = max(0, random.gauss(pts_visita_global, desv_global))

    if (sim_l - sim_v) + spread_casa >= 0:
        covers_g += 1
    if (sim_l + sim_v) > total_casa:
        overs_g += 1

prob_cover_global = covers_g / num_sims_global * 100
prob_over_global = overs_g / num_sims_global * 100
prob_under_global = 100 - prob_over_global

st.write(f"Prob. de que {local or 'LOCAL'} cubra (GLOBAL): **{prob_cover_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 7) MONTE CARLO CASA / VISITA
# =========================================================
st.subheader("7) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_cv = None
prob_over_cv = None

if hay_cv and total_cv is not None:
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

    st.write(f"Prob. de que {local or 'LOCAL'} cubra (C/V): **{prob_cover_cv:.1f}%**")
    st.write(f"Prob. de OVER (C/V): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 8) APUESTAS RECOMENDADAS
# =========================================================
st.subheader("8) Apuestas recomendadas 🎯")
recs = []

# spread global
prob_visita_spread_global = 100 - prob_cover_global
if prob_cover_global >= prob_visita_spread_global and prob_cover_global >= 55:
    recs.append((f"Spread (GLOBAL): {local or 'LOCAL'} {spread_casa}", prob_cover_global))
elif prob_visita_spread_global > prob_cover_global and prob_visita_spread_global >= 55:
    visita_linea = -spread_casa
    recs.append((f"Spread (GLOBAL): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

# total global
if prob_over_global >= prob_under_global and prob_over_global >= 55:
    recs.append((f"Total (GLOBAL): OVER {total_casa}", prob_over_global))
elif prob_under_global >= 55:
    recs.append((f"Total (GLOBAL): UNDER {total_casa}", prob_under_global))

# spreads / totals de casa-visita
if hay_cv and prob_cover_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_cv
    if prob_cover_cv >= prob_visita_spread_cv and prob_cover_cv >= 55:
        recs.append((f"Spread (CASA/VISITA): {local or 'LOCAL'} {spread_casa}", prob_cover_cv))
    elif prob_visita_spread_cv >= 55:
        visita_linea = -spread_casa
        recs.append((f"Spread (CASA/VISITA): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_cv))

if hay_cv and prob_over_cv is not None:
    if prob_over_cv >= prob_under_cv and prob_over_cv >= 55:
        recs.append((f"Total (CASA/VISITA): OVER {total_casa}", prob_over_cv))
    elif prob_under_cv >= 55:
        recs.append((f"Total (CASA/VISITA): UNDER {total_casa}", prob_under_cv))

if recs:
    for txt, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"📌 {txt} → **{p:.1f}%**")
else:
    st.info("No hay apuestas ≥ 55% con los datos actuales.")
