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

SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
NFL_SEASON = "2025REG"
NBA_SEASON = "2025"   # tu trial no lo trae, pero dejamos el hook

# =========================================================
# HELPERS DE API
# =========================================================
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

    equipos = {}
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

        equipos[name] = {
            "pf_pg": round(pf / games, 2),
            "pa_pg": round(pa / games, 2),
        }
    return equipos, ""

@st.cache_data(ttl=600)
def cargar_nba(api_key: str, season: str):
    # tu trial actual no tiene habilitado el feed de NBA
    return {}, "NBA no está habilitado en tu cuenta de SportsDataIO."

# =========================================================
# 1) Cargar datos según liga
# =========================================================
if liga == "NFL":
    data_liga, liga_error = cargar_nfl(SPORTSDATAIO_KEY, NFL_SEASON)
    if liga_error:
        st.warning(liga_error)
    else:
        st.success(f"✅ Datos NFL cargados — {len(data_liga)} equipos ({NFL_SEASON})")
else:
    data_liga, liga_error = cargar_nba(SPORTSDATAIO_KEY, NBA_SEASON)
    if liga_error:
        st.warning(liga_error)

# =========================================================
# 2) Datos del partido
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", key="local_name")
    btn_local = st.button("Rellenar LOCAL desde NFL" if liga == "NFL" else "Rellenar LOCAL desde NBA")
    if btn_local:
        lookup = local.strip().lower()
        if lookup in data_liga:
            st.session_state["l_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"LOCAL rellenado con datos reales de {local}")
        else:
            st.error("No encontré ese equipo en la API.")

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
    btn_visita = st.button("Rellenar VISITA desde NFL" if liga == "NFL" else "Rellenar VISITA desde NBA")
    if btn_visita:
        lookup = visita.strip().lower()
        if lookup in data_liga:
            st.session_state["v_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"VISITA rellenado con datos reales de {visita}")
        else:
            st.error("No encontré ese equipo en la API.")

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
# 3) Promedios por condición
# =========================================================
st.subheader("2) Promedios por condición (opcional)")
cc1, cc2 = st.columns(2)
with cc1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", value=0.0, step=0.1)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", value=0.0, step=0.1)
with cc2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", value=0.0, step=0.1)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", value=0.0, step=0.1)

hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

# =========================================================
# 4) Ajuste por lesiones / forma + QB
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

opciones_forma = {
    "Healthy / completo": 1.00,
    "1-2 bajas ofensivas": 0.97,
    "Varias bajas ofensivas": 0.94,
    "Ofensiva en buen momento": 1.03,
}

a1, a2 = st.columns(2)
with a1:
    estado_local = st.selectbox("Estado ofensivo LOCAL", list(opciones_forma.keys()), index=0)
    mult_local_forma = opciones_forma[estado_local]

    mult_local_qb = 1.0
    if liga == "NFL":
        juega_qb_local = st.checkbox("¿Juega QB titular LOCAL?", value=True)
        if not juega_qb_local:
            mult_local_qb = 0.88  # castigo típico por QB fuera

with a2:
    estado_visita = st.selectbox("Estado ofensivo VISITA", list(opciones_forma.keys()), index=0)
    mult_visita_forma = opciones_forma[estado_visita]

    mult_visita_qb = 1.0
    if liga == "NFL":
        juega_qb_visita = st.checkbox("¿Juega QB titular VISITA?", value=True)
        if not juega_qb_visita:
            mult_visita_qb = 0.88

mult_local_total = mult_local_forma * mult_local_qb
mult_visita_total = mult_visita_forma * mult_visita_qb

st.caption("Esto imita lo que hace una casa: penalizaciones chicas por bajas normales y otra aparte si no juega el QB.")

# =========================================================
# 5) Proyección del modelo
# =========================================================
st.subheader("4) Proyección del modelo")

def proyeccion_suavizada(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local and liga == "NFL":
        base += 1.5
    return base

# GLOBAL
pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, es_local=True) * mult_local_total
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, es_local=False) * mult_visita_total
total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local_global:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita_global:.1f} pts**")
st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

# CASA / VISITA
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion_suavizada(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        es_local=True
    ) * mult_local_total

    pts_visita_cv = proyeccion_suavizada(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        es_local=False
    ) * mult_visita_total

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 6) Línea del casino y diferencias
# =========================================================
st.subheader("5) Línea del casino y diferencias")
lc1, lc2 = st.columns(2)
with lc1:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with lc2:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 0.0, 0.5)

# comparación
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

# alerta especificando dónde
motivos_alerta = []
if abs(dif_spread_global) >= 5:
    motivos_alerta.append("spread")
if abs(dif_total_global) >= 7:
    motivos_alerta.append("total")
if motivos_alerta:
    st.error(f"⚠️ Línea muy diferente a tu modelo ({' y '.join(motivos_alerta)}). Puede ser trap line o info que no estás metiendo.")
elif abs(dif_spread_global) >= 3:
    st.warning("⚠️ Tu modelo no coincide con la casa en el spread. Revísalo.")

# si hay casa/visita también mostramos
if hay_cv:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.markdown("🔎 **Comparación CASA/VISITA**")
    st.write(f"- DIF. SPREAD (c/v): **{dif_spread_cv:+.1f} pts**")
    st.write(f"- DIF. TOTAL (c/v): **{dif_total_cv:+.1f} pts**")

# =========================================================
# 5b) Moneyline opcional
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
ml1, ml2 = st.columns(2)
with ml1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with ml2:
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

# para el ML usamos una conversión desde el spread del modelo (más real que repartir puntos)
def prob_ganar_desde_spread(spread_lv):
    # fórmula logística aproximada
    return 1 / (1 + 10 ** (-(spread_lv) / 6.5)) * 100

prob_modelo_local = prob_ganar_desde_spread(spread_global)
prob_modelo_visita = 100 - prob_modelo_local

if prob_imp_local is not None and prob_imp_visita is not None:
    st.subheader("5c) Comparativa de probabilidades (modelo vs casa)")
    st.write(f"{local or 'LOCAL'} — modelo: **{prob_modelo_local:.1f}%** vs casa: **{prob_imp_local:.1f}%**")
    st.write(f"{visita or 'VISITA'} — modelo: **{prob_modelo_visita:.1f}%** vs casa: **{prob_imp_visita:.1f}%**")

# =========================================================
# 6) Monte Carlo GLOBAL
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv_global = max(5, total_global * 0.15)

covers = 0
overs = 0
for _ in range(num_sims_global):
    sim_l = max(0, random.gauss(pts_local_global, desv_global))
    sim_v = max(0, random.gauss(pts_visita_global, desv_global))

    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6c) Edge en spread (modelo vs cuota -110)
# =========================================================
st.subheader("6c) Edge en spread (modelo vs cuota -110)")

prob_implicita_110 = 52.38
edge_spread_local = prob_cover_local_global - prob_implicita_110
edge_spread_visita = (100 - prob_cover_local_global) - prob_implicita_110

if edge_spread_local > 0:
    st.success(f"Edge en spread para {local or 'LOCAL'}: +{edge_spread_local:.1f}%")
else:
    st.warning(f"Edge en spread para {local or 'LOCAL'}: {edge_spread_local:.1f}%")

if edge_spread_visita > 0:
    st.success(f"Edge en spread para {visita or 'VISITA'}: +{edge_spread_visita:.1f}%")
else:
    st.warning(f"Edge en spread para {visita or 'VISITA'}: {edge_spread_visita:.1f}%")

with st.expander("❓ ¿Qué significa este edge en spread?"):
    st.markdown("""
- Aquí estoy comparando **tu probabilidad de cubrir** (la que salió de la simulación) contra la probabilidad que te **cobra el casino** cuando la línea es -110 (≈ 52.4%).
- Si tu modelo dice **más de 52.4%**, hay **value** → por eso lo ves en verde.
- Si dice **menos de 52.4%**, no alcanza para ganarle al juice → por eso lo ves en amarillo.
- Esto es solo para el **spread**, no para el moneyline.
    """)

# =========================================================
# 6b) Monte Carlo CASA/VISITA
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
        sim_l = max(0, random.gauss(pts_local_cv, desv_cv))
        sim_v = max(0, random.gauss(pts_visita_cv, desv_cv))

        if (sim_l - sim_v) + spread_casa >= 0:
            covers_cv += 1
        if (sim_l + sim_v) > total_casa:
            overs_cv += 1

    prob_cover_local_cv = covers_cv / num_sims_cv * 100
    prob_over_cv = overs_cv / num_sims_cv * 100

    st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (CASA/VISITA): **{prob_cover_local_cv:.1f}%**")
    st.write(f"Prob. de OVER (CASA/VISITA): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita.")

# =========================================================
# 7) Apuestas recomendadas
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

# spread global
prob_visita_spread_global = 100 - prob_cover_local_global
if prob_cover_local_global >= prob_visita_spread_global:
    if prob_cover_local_global >= 55:
        recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_global))
else:
    if prob_visita_spread_global >= 55:
        visita_linea = -spread_casa
        recs.append((f"Spread GLOBAL: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= prob_under_global:
    if prob_over_global >= 55:
        recs.append((f"Total GLOBAL: OVER {total_casa:.1f}", prob_over_global))
else:
    if prob_under_global >= 55:
        recs.append((f"Total GLOBAL: UNDER {total_casa:.1f}", prob_under_global))

# casa/visita
if hay_cv and prob_cover_local_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_local_cv
    if prob_cover_local_cv >= prob_visita_spread_cv:
        if prob_cover_local_cv >= 55:
            recs.append((f"Spread C/V: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_cv))
    else:
        if prob_visita_spread_cv >= 55:
            visita_linea = -spread_casa
            recs.append((f"Spread C/V: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_cv))

if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= prob_under_cv:
        if prob_over_cv >= 55:
            recs.append((f"Total C/V: OVER {total_casa:.1f}", prob_over_cv))
    else:
        if prob_under_cv >= 55:
            recs.append((f"Total C/V: UNDER {total_casa:.1f}", prob_under_cv))

if recs:
    for texto, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"📌 {texto} — **{p:.1f}%**")
else:
    st.info("No hay jugadas ≥ 55% con los datos actuales.")

# =========================================================
# 8) Edge del modelo vs casa (Moneyline)
# =========================================================
st.subheader("8) Edge del modelo vs casa (Moneyline)")
if prob_imp_local is not None and prob_imp_visita is not None:
    edge_local_ml = prob_modelo_local - prob_imp_local
    edge_visita_ml = prob_modelo_visita - prob_imp_visita

    if edge_local_ml > 0.5:
        st.success(f"Edge LOCAL (ML): +{edge_local_ml:.1f}% — tu modelo ve más que la casa para {local or 'LOCAL'}")
    elif edge_local_ml < -0.5:
        st.error(f"Edge LOCAL (ML): {edge_local_ml:.1f}% — la casa valora más al local que tu modelo")
    else:
        st.info(f"Edge LOCAL (ML): {edge_local_ml:.1f}% — casi igual")

    if edge_visita_ml > 0.5:
        st.success(f"Edge VISITA (ML): +{edge_visita_ml:.1f}% — tu modelo ve más que la casa para {visita or 'VISITA'}")
    elif edge_visita_ml < -0.5:
        st.error(f"Edge VISITA (ML): {edge_visita_ml:.1f}% — la casa valora más a la visita que tu modelo")
    else:
        st.info(f"Edge VISITA (ML): {edge_visita_ml:.1f}% — casi igual")
else:
    st.caption("Para ver el edge de ML, ingresa los moneylines arriba ☝️.")
