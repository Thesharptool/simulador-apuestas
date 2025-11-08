import streamlit as st
import random
import requests
import math

# =========================================================
# CONFIGURACIÓN
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (multi-liga) + opción neuronal + ML")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA (manual)  
Ahora: convierte el spread del modelo a probabilidad de ganar (sin simulación).
""")

# =========================================================
# 0) SELECCIONAR LIGA Y MODELO
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)
tipo_modelo = st.radio("¿Con qué modelo quieres proyectar?", ["Monte Carlo / clásico", "Neuronal (demo)"])

API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
NFL_SEASON = "2025REG"
NBA_SEASON = "2025"

# =========================================================
# CARGA DE DATOS
# =========================================================
@st.cache_data(ttl=600)
def cargar_nfl(api_key: str, season: str):
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}, f"Error {r.status_code} (NFL)"
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
            return {}, f"Error {r.status_code} (NBA)"
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
# 2) CASA / VISITA
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
# 3) AJUSTE POR LESIONES
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")
aj1, aj2 = st.columns(2)
with aj1:
    af_local = st.checkbox("¿Afecta ofensiva LOCAL?", False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
    if mult_local == 1.0:
        st.caption("LOCAL: ✅ normal")
    elif mult_local < 1.0:
        st.caption("LOCAL: ❌ bajas")
    else:
        st.caption("LOCAL: 🔥 en racha")
with aj2:
    af_visita = st.checkbox("¿Afecta ofensiva VISITA?", False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)
    if mult_visita == 1.0:
        st.caption("VISITA: ✅ normal")
    elif mult_visita < 1.0:
        st.caption("VISITA: ❌ bajas")
    else:
        st.caption("VISITA: 🔥 en racha")

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# =========================================================
# 4) MODELOS
# =========================================================
def modelo_clasico(of_local, def_visita, of_visita, def_local):
    pts_local = 0.55 * of_local + 0.35 * def_visita
    pts_visita = 0.55 * of_visita + 0.35 * def_local
    if liga == "NFL":
        pts_local += 1.5
    return pts_local, pts_visita

def modelo_neuronal_demo(of_local, def_visita, of_visita, def_local, extra_cv=False):
    h1 = 0.6 * of_local + 0.25 * def_visita - 0.1 * def_local
    h2 = 0.6 * of_visita + 0.25 * def_local - 0.1 * def_visita
    h1 = max(0, h1)
    h2 = max(0, h2)
    pts_local = 0.7 * h1 + 0.15 * def_visita
    pts_visita = 0.7 * h2 + 0.15 * def_local
    if liga == "NFL":
        pts_local += 1.2
    if extra_cv:
        pts_local += 0.3
    return pts_local, pts_visita

# conversión spread -> prob (nuevo)
def prob_desde_spread(spread, deporte="NFL"):
    """
    Convierte spread del modelo a probabilidad de ganar.
    Usamos una logística suave; para NBA hacemos un poco más sensible.
    """
    if deporte == "NBA":
        k = 0.45  # más puntos en NBA
    else:
        k = 0.55  # NFL
    # prob = 1 / (1 + e^(-k*spread))
    p = 1 / (1 + math.exp(-k * spread))
    return p * 100

# =========================================================
# 4) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

of_local_ajustada = l_anota_global * mult_local
of_visita_ajustada = v_anota_global * mult_visita

if tipo_modelo == "Monte Carlo / clásico":
    pts_local_global, pts_visita_global = modelo_clasico(
        of_local_ajustada, v_permite_global, of_visita_ajustada, l_permite_global
    )
else:
    pts_local_global, pts_visita_global = modelo_neuronal_demo(
        of_local_ajustada, v_permite_global, of_visita_ajustada, l_permite_global
    )

total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'} : **{pts_local_global:.1f} pts**")
st.write(f"- {visita or 'VISITA'} : **{pts_visita_global:.1f} pts**")
st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

# probabilidad a partir del spread del modelo (nuevo)
prob_local_spread = prob_desde_spread(spread_global, deporte=liga)
st.write(f"🧮 Prob. de victoria (solo por spread del modelo): **{prob_local_spread:.1f}%** para {local or 'LOCAL'}")
st.write(f"🧮 Prob. de victoria (solo por spread del modelo): **{100 - prob_local_spread:.1f}%** para {visita or 'VISITA'}")

# CASA / VISITA
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    of_local_cv = (l_anota_casa if l_anota_casa > 0 else l_anota_global) * mult_local
    of_visita_cv = (v_anota_visita if v_anota_visita > 0 else v_anota_global) * mult_visita
    def_local_cv = v_permite_visita if v_permite_visita > 0 else v_permite_global
    def_visita_cv = l_permite_casa if l_permite_casa > 0 else l_permite_global

    if tipo_modelo == "Monte Carlo / clásico":
        pts_local_cv, pts_visita_cv = modelo_clasico(of_local_cv, def_local_cv, of_visita_cv, def_visita_cv)
    else:
        pts_local_cv, pts_visita_cv = modelo_neuronal_demo(of_local_cv, def_local_cv, of_visita_cv, def_visita_cv, extra_cv=True)

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")

    # prob desde spread c/v
    prob_local_spread_cv = prob_desde_spread(spread_cv, deporte=liga)
    st.write(f"🧮 Prob. de victoria (c/v): **{prob_local_spread_cv:.1f}%** {local or 'LOCAL'}")
else:
    total_cv = None
    spread_cv = None
    st.info("Si llenas los 4 campos de casa/visita te muestro también esa proyección.")

# =========================================================
# 5) LÍNEA DEL CASINO Y TRAP
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
st.write(f"🟦 Dif. TOTAL  (GLOBAL): **{dif_total_global:+.1f} pts**")

if abs(dif_spread_global) >= 8:
    st.error("🚨 Posible TRAP LINE (GLOBAL): el modelo está ≥ 8 pts de la línea.")
elif abs(dif_spread_global) >= 5:
    st.warning("⚠️ El modelo y la línea difieren ≥ 5 pts (GLOBAL).")

if hay_cv and total_cv is not None:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.write(f"🟩 Dif. SPREAD (C/V): **{dif_spread_cv:+.1f} pts**")
    st.write(f"🟩 Dif. TOTAL  (C/V): **{dif_total_cv:+.1f} pts**")
    if abs(dif_spread_cv) >= 8:
        st.error("🚨 Posible TRAP LINE (C/V): el modelo está ≥ 8 pts.")
    elif abs(dif_spread_cv) >= 5:
        st.warning("⚠️ El modelo y la línea difieren ≥ 5 pts (C/V).")

# =========================================================
# 5b) MONEYLINE
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")

def implied_prob_from_american(odds):
    if odds == 0:
        return 0.0
    if odds > 0:
        return 100 / (odds + 100) * 100
    else:
        return (-odds) / ((-odds) + 100) * 100

ml1, ml2 = st.columns(2)
with ml1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", -2000, 2000, 0)
with ml2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", -2000, 2000, 0)

imp_local = implied_prob_from_american(ml_local) if ml_local != 0 else 0.0
imp_visita = implied_prob_from_american(ml_visita) if ml_visita != 0 else 0.0
if ml_local != 0 or ml_visita != 0:
    st.caption(f"Prob. implícita LOCAL: **{imp_local:.1f}%** | Prob. implícita VISITA: **{imp_visita:.1f}%**")

# =========================================================
# 6) MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv_global = max(5, total_global * 0.15)

covers_g = 0
overs_g = 0
wins_local = 0
for _ in range(num_sims_global):
    sim_l = max(0, random.gauss(pts_local_global, desv_global))
    sim_v = max(0, random.gauss(pts_visita_global, desv_global))

    if (sim_l - sim_v) + spread_casa >= 0:
        covers_g += 1
    if (sim_l + sim_v) > total_casa:
        overs_g += 1
    if sim_l > sim_v:
        wins_local += 1

prob_cover_global = covers_g / num_sims_global * 100
prob_over_global = overs_g / num_sims_global * 100
prob_win_modelo_local_mc = wins_local / num_sims_global * 100
prob_win_modelo_visita_mc = 100 - prob_win_modelo_local_mc

st.write(f"Prob. de que {local or 'LOCAL'} cubra (GLOBAL): **{prob_cover_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")
st.write(f"Prob. de victoria (Monte Carlo): **{prob_win_modelo_local_mc:.1f}%** {local or 'LOCAL'}")

# comparar MC vs ML
if ml_local != 0:
    edge_local = prob_win_modelo_local_mc - imp_local
    st.write(f"🟣 Edge ML LOCAL (MC - casa): **{edge_local:+.1f} pts %**")
if ml_visita != 0:
    edge_visita = prob_win_modelo_visita_mc - imp_visita
    st.write(f"🟣 Edge ML VISITA (MC - casa): **{edge_visita:+.1f} pts %**")

# =========================================================
# 7) MONTE CARLO CASA/VISITA
# =========================================================
st.subheader("7) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_cv = None
prob_over_cv = None
if hay_cv and total_cv is not None:
    num_sims_cv = st.slider("Número de simulaciones (C/V)", 1000, 50000, 10000, 1000, key="cv_sims")
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
elif prob_visita_spread_global >= 55:
    visita_linea = -spread_casa
    recs.append((f"Spread (GLOBAL): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= prob_under_global and prob_over_global >= 55:
    recs.append((f"Total (GLOBAL): OVER {total_casa}", prob_over_global))
elif prob_under_global >= 55:
    recs.append((f"Total (GLOBAL): UNDER {total_casa}", prob_under_global))

# casa/visita
if hay_cv and prob_cover_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_cv
    if prob_cover_cv >= prob_visita_spread_cv and prob_cover_cv >= 55:
        recs.append((f"Spread (C/V): {local or 'LOCAL'} {spread_casa}", prob_cover_cv))
    elif prob_visita_spread_cv >= 55:
        visita_linea = -spread_casa
        recs.append((f"Spread (C/V): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_cv))

if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= prob_under_cv and prob_over_cv >= 55:
        recs.append((f"Total (C/V): OVER {total_casa}", prob_over_cv))
    elif prob_under_cv >= 55:
        recs.append((f"Total (C/V): UNDER {total_casa}", prob_under_cv))

if recs:
    for txt, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"📌 {txt} → **{p:.1f}%**")
else:
    st.info("No hay apuestas ≥ 55% con los datos actuales.")
