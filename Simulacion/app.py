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

# Llave API SportsDataIO
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"

NFL_SEASON = "2025REG"
NBA_SEASON = "2025"

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
# 2) PROMEDIOS POR CONDICIÓN
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
opciones_estado = {
    "Healthy / completo": 1.00,
    "1-2 bajas importantes": 0.975,
    "Varias bajas / QB tocado": 0.95,
    "En buen momento / ofensiva 🔥": 1.03,
}
c3, c4 = st.columns(2)
with c3:
    estado_local_txt = st.selectbox("Estado ofensivo LOCAL", list(opciones_estado.keys()), index=0)
    mult_estado_local = opciones_estado[estado_local_txt]
with c4:
    estado_visita_txt = st.selectbox("Estado ofensivo VISITA", list(opciones_estado.keys()), index=0)
    mult_estado_visita = opciones_estado[estado_visita_txt]
st.caption("Estos multiplicadores afectan los puntos proyectados: 1.00 = normal, 0.975 = leve bajón, 1.03 = mejora leve.")

# =========================================================
# 4) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")
def proyeccion_suavizada(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local and liga == "NFL":
        base += 1.5
    return base

pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, es_local=True) * mult_estado_local
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, es_local=False) * mult_estado_visita
total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local_global:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita_global:.1f} pts**")
st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

# =========================================================
# 5) LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 0.0, 0.5)

modelo_spread_formato_casa = -spread_global
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

if abs(dif_spread_global) >= 3 or abs(dif_total_global) >= 5:
    st.error("⚠️ Línea muy diferente a tu modelo. Puede ser un trap line o info que no estás considerando (lesiones, clima, descanso).")

# =========================================================
# 5b) MONEYLINE Y COMPARATIVA
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

def prob_ganar_desde_spread(spread_lv):
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
# 6) SIMULACIÓN MONTE CARLO
# =========================================================
st.subheader("6) Simulación Monte Carlo (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones", 1000, 50000, 10000, 1000)
desv_global = max(5, total_global * 0.15)
covers, overs = 0, 0

for _ in range(num_sims_global):
    sim_local = max(0, random.gauss(pts_local_global, desv_global))
    sim_visita = max(0, random.gauss(pts_visita_global, desv_global))
    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1
    if (sim_local + sim_visita) > total_casa:
        overs += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100
st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 7) APUESTAS RECOMENDADAS (≥55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []
if prob_cover_local_global >= 55:
    recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_global))
else:
    prob_visita = 100 - prob_cover_local_global
    if prob_visita >= 55:
        recs.append((f"Spread GLOBAL: {visita or 'VISITA'} {-spread_casa:+.1f}", prob_visita))
prob_under = 100 - prob_over_global
if prob_over_global >= 55:
    recs.append((f"Total GLOBAL: OVER {total_casa}", prob_over_global))
elif prob_under >= 55:
    recs.append((f"Total GLOBAL: UNDER {total_casa}", prob_under))

if recs:
    for texto, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"📌 {texto} — **{p:.1f}%**")
else:
    st.info("No hay jugadas ≥ 55% con los datos actuales.")
