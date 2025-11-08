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
    # tu trial no lo trae, lo dejamos manual
    return {}, "Tu trial actual no tiene habilitado el feed de NBA. Pídeselo a SportsDataIO."

# =========================================================
# 1) CARGA SEGÚN LIGA
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
# 2) DATOS DEL PARTIDO
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
# 3) PROMEDIOS POR CONDICIÓN
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
# 4) AJUSTE POR LESIONES / FORMA (estilo book) + QB ON/OFF
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

opciones_estado = {
    "Healthy / completo": 1.00,
    "1-2 bajas (WR/RB/OL)": 0.98,
    "Varias bajas ofensivas": 0.95,
    "Ofensiva en buen momento": 1.03,
}

col_adj1, col_adj2 = st.columns(2)
with col_adj1:
    estado_local_txt = st.selectbox("Estado ofensivo LOCAL", list(opciones_estado.keys()), index=0)
    mult_estado_local = opciones_estado[estado_local_txt]
with col_adj2:
    estado_visita_txt = st.selectbox("Estado ofensivo VISITA", list(opciones_estado.keys()), index=0)
    mult_estado_visita = opciones_estado[estado_visita_txt]

st.caption("Esto es el ajuste general (bajas normales). Ahora viene el ajuste SOLO por QB.")

st.markdown("**¿Juega el QB titular / estrella?**")
qbcol1, qbcol2 = st.columns(2)
with qbcol1:
    qb_local_out = st.checkbox("No juega QB titular LOCAL", value=False)
with qbcol2:
    qb_visita_out = st.checkbox("No juega QB titular VISITA", value=False)

if liga == "NFL":
    qb_penal_local = -3.0 if qb_local_out else 0.0
    qb_penal_visita = -3.0 if qb_visita_out else 0.0
else:  # NBA
    qb_penal_local = -2.0 if qb_local_out else 0.0
    qb_penal_visita = -2.0 if qb_visita_out else 0.0

st.caption("Si marcas que no juega, el modelo le quita esos puntos directo (como hace el mercado).")

# =========================================================
# 5) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

def proyeccion_suavizada(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local and liga == "NFL":
        base += 1.5
    return base

pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, es_local=True) * mult_estado_local
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, es_local=False) * mult_estado_visita

pts_local_global = max(0.0, pts_local_global + qb_penal_local)
pts_visita_global = max(0.0, pts_visita_global + qb_penal_visita)

total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local_global:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita_global:.1f} pts**")
st.write(f"- Total modelo: **{total_global:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion_suavizada(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        es_local=True
    ) * mult_estado_local
    pts_visita_cv = proyeccion_suavizada(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        es_local=False
    ) * mult_estado_visita

    pts_local_cv = max(0.0, pts_local_cv + qb_penal_local)
    pts_visita_cv = max(0.0, pts_visita_cv + qb_penal_visita)

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f} pts**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f} pts**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 6) LÍNEA DEL CASINO Y DIFERENCIAS
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

# -------- alerta específica --------
motivos_alerta = []
if abs(dif_spread_global) >= 5:
    motivos_alerta.append("spread")
if abs(dif_total_global) >= 7:
    motivos_alerta.append("total")

if motivos_alerta:
    motivo_txt = " y ".join(motivos_alerta)
    st.error(f"⚠️ Línea muy diferente a tu modelo ({motivo_txt}). Puede ser trap line o info que tu modelo no trae.")
elif abs(dif_spread_global) >= 3:
    st.warning("⚠️ Tu modelo no coincide con la casa en el spread. Revísalo.")

# CASA/VISITA
if hay_cv:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.markdown("🔎 **Comparación de spreads (CASA/VISITA)**")
    st.write(f"- Modelo c/v (formato casa): **LOCAL {modelo_spread_cv_formato_casa:+.1f}**")
    st.write(f"- DIF. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.write(f"- DIF. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")

# =========================================================
# 5b) MONEYLINE
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

    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1
    if (sim_local + sim_visita) > total_casa:
        overs += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6b) SIMULACIÓN MONTE CARLO (CASA/VISITA)
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
# 7) APUESTAS RECOMENDADAS (≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

if prob_cover_local_global >= 55:
    recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_global))
else:
    prob_visita_spread_global = 100 - prob_cover_local_global
    if prob_visita_spread_global >= 55:
        visita_linea = -spread_casa
        recs.append((f"Spread GLOBAL: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

prob_under_global = 100 - prob_over_global
if prob_over_global >= 55:
    recs.append((f"Total GLOBAL: OVER {total_casa:.1f}", prob_over_global))
elif prob_under_global >= 55:
    recs.append((f"Total GLOBAL: UNDER {total_casa:.1f}", prob_under_global))

if hay_cv and prob_cover_local_cv is not None:
    if prob_cover_local_cv >= 55:
        recs.append((f"Spread CASA/VISITA: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_cv))
    else:
        prob_visita_spread_cv = 100 - prob_cover_local_cv
        if prob_visita_spread_cv >= 55:
            visita_linea = -spread_casa
            recs.append((f"Spread CASA/VISITA: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_cv))

if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= 55:
        recs.append((f"Total CASA/VISITA: OVER {total_casa:.1f}", prob_over_cv))
    elif prob_under_cv >= 55:
        recs.append((f"Total CASA/VISITA: UNDER {total_casa:.1f}", prob_under_cv))

if recs:
    for texto, p in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"📌 {texto} — **{p:.1f}%**")
else:
    st.info("No hay jugadas ≥ 55%. Llena líneas y ejecuta simulación.")

# =========================================================
# 8) EDGE DEL MODELO VS CASA
# =========================================================
st.subheader("8) Edge del modelo vs casa")
if prob_imp_local is not None and prob_imp_visita is not None:
    edge_local = prob_modelo_local - prob_imp_local
    edge_visita = prob_modelo_visita - prob_imp_visita

    if edge_local > 0.5:
        st.success(f"Edge LOCAL: +{edge_local:.1f}% (tu modelo ve más que la casa)")
    elif edge_local < -0.5:
        st.error(f"Edge LOCAL: {edge_local:.1f}% (la casa está más alta que tu modelo)")
    else:
        st.info(f"Edge LOCAL: {edge_local:.1f}% (muy parecido)")

    if edge_visita > 0.5:
        st.success(f"Edge VISITA: +{edge_visita:.1f}%")
    elif edge_visita < -0.5:
        st.error(f"Edge VISITA: {edge_visita:.1f}%")
    else:
        st.info(f"Edge VISITA: {edge_visita:.1f}%")
else:
    st.caption("Para ver el edge, mete los moneylines de la casa arriba ☝️.")
