import streamlit as st
import random
import requests

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (multi-liga)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA (manual)  
Si llenas casa/visita te muestro las dos proyecciones.
""")

# =========================================================
# 0) ELECCIÓN DE LIGA
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# tus llaves (la misma para las dos porque tu cuenta es así)
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"

NFL_SEASON = "2025REG"   # lo que ya te funcionó
NBA_SEASON = "2025"      # pero tu trial no lo tiene habilitado

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
        return {}, f"Error de conexión (NFL): {e}"

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
        games = played if played > 0 else games_raw if games_raw > 0 else 1

        teams[name] = {
            "pf_pg": round(pf / games, 2),
            "pa_pg": round(pa / games, 2),
        }
    return teams, ""

@st.cache_data(ttl=600)
def cargar_nba(api_key: str, season: str):
    # tu trial no lo trae, así que devolvemos vacío y aviso
    return {}, "Tu trial actual no tiene habilitado el feed de NBA. Pídeselo a SportsDataIO."

if liga == "NFL":
    nfl_data, nfl_error = cargar_nfl(SPORTSDATAIO_KEY, NFL_SEASON)
    if nfl_error:
        st.warning(nfl_error)
    else:
        st.success(f"✅ Datos NFL cargados — {len(nfl_data)} equipos ({NFL_SEASON})")
    data_liga = nfl_data
else:
    nba_data, nba_error = cargar_nba(SPORTSDATAIO_KEY, NBA_SEASON)
    if nba_error:
        st.warning(nba_error)
    data_liga = nba_data

# =========================================================
# 1) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", key="local_name")

    # botón de rellenar, cambia el texto si es NFL o NBA
    label_local_btn = "Rellenar LOCAL desde NFL" if liga == "NFL" else "Rellenar LOCAL desde NBA"
    if st.button(label_local_btn, key="btn_local_fill"):
        lookup = local.strip().lower()
        if lookup in data_liga:
            st.session_state["l_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"LOCAL rellenado con datos reales de {local}")
        else:
            st.error("No encontré ese equipo en la API de esta liga.")

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
    visita = st.text_input("Equipo VISITA", key="visita_name")

    label_visita_btn = "Rellenar VISITA desde NFL" if liga == "NFL" else "Rellenar VISITA desde NBA"
    if st.button(label_visita_btn, key="btn_visita_fill"):
        lookup = visita.strip().lower()
        if lookup in data_liga:
            st.session_state["v_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"VISITA rellenado con datos reales de {visita}")
        else:
            st.error("No encontré ese equipo en la API de esta liga.")

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
# 2) PROMEDIOS POR CONDICIÓN (los dejamos en blanco)
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
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

# ajustes suaves, estilo book
opciones_estado = {
    "Healthy / completo": 1.00,
    "1-2 bajas importantes": 0.975,   # -2.5%
    "Varias bajas / QB tocado": 0.95,  # -5%
    "En buen momento / ofensiva 🔥": 1.03,  # +3%
}

c3, c4 = st.columns(2)
with c3:
    estado_local_txt = st.selectbox("Estado ofensivo LOCAL", list(opciones_estado.keys()), index=0)
    mult_estado_local = opciones_estado[estado_local_txt]
with c4:
    estado_visita_txt = st.selectbox("Estado ofensivo VISITA", list(opciones_estado.keys()), index=0, key="estado_visita")
    mult_estado_visita = opciones_estado[estado_visita_txt]

st.caption("Estos multiplicadores afectan los puntos proyectados: 1.00 = normal, 0.975 = un poco peor, 1.03 = un poco mejor.")

# =========================================================
# 4) FUNCIÓN DEL MODELO Y PROYECCIÓN
# =========================================================
def proyeccion_suavizada(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local and liga == "NFL":
        base += 1.5     # dejas tu ventaja de campo
    return base

st.subheader("4) Proyección del modelo")

# GLOBAL
pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, es_local=True) * mult_estado_local
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, es_local=False) * mult_estado_visita
total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global   # positivo = local mejor

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local_global:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita_global:.1f} pts**")
st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

# CASA / VISITA (solo si llenó)
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion_suavizada(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        es_local=True,
    ) * mult_estado_local

    pts_visita_cv = proyeccion_suavizada(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        es_local=False,
    ) * mult_estado_visita

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
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
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 49.5, 0.5)

# aquí viene lo que querías ver claro:
modelo_spread_formato_casa = -spread_global   # paso de (local-visita) a cómo lo publicaría la casa
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total_global - total_casa

st.markdown("🔎 **Comparación de spreads (GLOBAL)**")
st.write(f"- Modelo (formato casa): **LOCAL {modelo_spread_formato_casa:+.1f}**")
st.write(f"- Casa: **LOCAL {spread_casa:+.1f}**")
st.write(f"- DIF. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")

st.markdown("🔎 **Comparación de totales (GLOBAL)**")
st.write(f"- Modelo: **{total_global:.1f}**")
st.write(f"- Casa: **{total_casa:.1f}**")
st.write(f"- DIF. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

# alerta de posible trap / número raro
if abs(dif_spread_global) >= 3 or abs(dif_total_global) >= 5:
    st.error("⚠️ Línea muy diferente a tu modelo. Puede ser info que no estás metiendo (lesiones, clima, descanso) o simple ajuste del book.")

# =========================================================
# 5b) MONEYLINE (opcional)
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
cml1, cml2 = st.columns(2)
with cml1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with cml2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0, step=5)

def americano_a_prob(ml):
    if ml == 0:
        return None
    if ml > 0:
        return 100 / (ml + 100) * 100
    else:
        return -ml / (-ml + 100) * 100

prob_imp_local = americano_a_prob(ml_local)
prob_imp_visita = americano_a_prob(ml_visita)

# una prob de victoria muy simple desde el spread del modelo (te dije que era una aproximación)
def prob_ganar_desde_spread(spread_lv):
    # spread_lv = local - visita
    # si local es mejor, spread_lv > 0
    return 1 / (1 + 10 ** (-(spread_lv) / 6.5)) * 100

prob_modelo_local = prob_ganar_desde_spread(spread_global)
prob_modelo_visita = 100 - prob_modelo_local

if prob_imp_local is not None and prob_imp_visita is not None:
    st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
    st.write(f"**{local or 'LOCAL'} (modelo): {prob_modelo_local:.1f}%**")
    st.write(f"**{visita or 'VISITA'} (modelo): {prob_modelo_visita:.1f}%**")
    st.write(f"Prob. implícita LOCAL (casa): {prob_imp_local:.1f}%")
    st.write(f"Prob. implícita VISITA (casa): {prob_imp_visita:.1f}%")

# =========================================================
# 6) SIMULACIÓN MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)

desv_global = max(5, total_global * 0.15)
covers = 0
overs = 0

for _ in range(num_sims_global):
    sim_local = max(0, random.gauss(pts_local_global, desv_global))
    sim_visita = max(0, random.gauss(pts_visita_global, desv_global))

    # cubrir spread de la casa (recuerda que spread_casa es desde el local)
    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1

    if (sim_local + sim_visita) > total_casa:
        overs += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6b) SIMULACIÓN MONTE CARLO (CASA / VISITA)
# =========================================================
st.subheader("6b) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_local_cv = None
prob_over_cv = None

if hay_cv:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="sims_cv")
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
# 7) APUESTAS RECOMENDADAS (≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

# SPREAD GLOBAL
if prob_cover_local_global >= 55:
    recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_global))
else:
    # prob visita = 100 - prob local
    prob_visita_spread_global = 100 - prob_cover_local_global
    if prob_visita_spread_global >= 55:
        visita_linea = -spread_casa
        recs.append((f"Spread GLOBAL: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

# TOTAL GLOBAL
prob_under_global = 100 - prob_over_global
if prob_over_global >= 55:
    recs.append((f"Total GLOBAL: OVER {total_casa}", prob_over_global))
elif prob_under_global >= 55:
    recs.append((f"Total GLOBAL: UNDER {total_casa}", prob_under_global))

# SPREAD CV
if hay_cv and prob_cover_local_cv is not None:
    if prob_cover_local_cv >= 55:
        recs.append((f"Spread CASA/VISITA: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_cv))
    else:
        prob_visita_spread_cv = 100 - prob_cover_local_cv
        if prob_visita_spread_cv >= 55:
            visita_linea = -spread_casa
            recs.append((f"Spread CASA/VISITA: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_cv))

# TOTAL CV
if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= 55:
        recs.append((f"Total CASA/VISITA: OVER {total_casa}", prob_over_cv))
    elif prob_under_cv >= 55:
        recs.append((f"Total CASA/VISITA: UNDER {total_casa}", prob_under_cv))

if recs:
    for texto, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"📌 {texto} — **{p:.1f}%**")
else:
    st.info("No hay jugadas ≥ 55% con los datos actuales.")
