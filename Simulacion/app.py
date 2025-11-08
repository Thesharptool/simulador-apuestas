import streamlit as st
import requests
import random
import math

# =========================================================
# 0) CONFIG GENERAL
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (multi-liga)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA (manual)  
Si llenas casa/visita te muestro las dos proyecciones.
""")

# NFL / NBA switch
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# tu key
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
NFL_SEASON = "2025REG"
NBA_SEASON = "2025"   # tu trial no la tiene abierta, pero dejamos el hook


# =========================================================
# helpers de API
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
        games_played = jugados if jugados > 0 else games_raw if games_raw > 0 else 1

        equipos[name] = {
            "pf_pg": round(pf / games_played, 2),
            "pa_pg": round(pa / games_played, 2),
        }
    return equipos, ""


@st.cache_data(ttl=600)
def cargar_nba(api_key: str, season: str):
    # En tu cuenta trial no está habilitado, devolvemos vacío
    return {}, "NBA no está habilitado en tu trial. Usa datos manuales."


# =========================================================
# 1) CARGA DE DATOS SEGÚN LIGA
# =========================================================
if liga == "NFL":
    liga_data, liga_error = cargar_nfl(SPORTSDATAIO_KEY, NFL_SEASON)
    if liga_error:
        st.warning(f"⚠️ {liga_error}")
    else:
        st.info(f"✅ Datos NFL cargados — {len(liga_data)} equipos ({NFL_SEASON})")
else:
    liga_data, liga_error = cargar_nba(SPORTSDATAIO_KEY, NBA_SEASON)
    if liga_error:
        st.warning(f"⚠️ {liga_error}")


# =========================================================
# 2) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

# asegurar llaves
for key in ["l_anota_global", "l_permite_global", "v_anota_global", "v_permite_global"]:
    st.session_state.setdefault(key, 0.0)

with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")

    if liga == "NFL":
        btn_local = st.button("Rellenar LOCAL desde NFL")
    else:
        btn_local = st.button("Rellenar LOCAL desde NBA")

    if btn_local:
        lookup = local.strip().lower()
        if lookup in liga_data:
            st.session_state["l_anota_global"] = liga_data[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = liga_data[lookup]["pa_pg"]
            st.success(f"LOCAL rellenado con datos reales de {local}")
        else:
            st.error("No encontré ese equipo en la API, llénalo manualmente.")

    st.markdown("**Promedios GLOBAL del LOCAL**")
    l_anota_global = st.number_input(
        "Local: puntos que ANOTA (global)",
        value=st.session_state["l_anota_global"],
        step=0.1,
        key="l_anota_global"
    )
    l_permite_global = st.number_input(
        "Local: puntos que PERMITE (global)",
        value=st.session_state["l_permite_global"],
        step=0.1,
        key="l_permite_global"
    )

with col2:
    visita = st.text_input("Equipo VISITA", "", key="visita_name")

    if liga == "NFL":
        btn_visita = st.button("Rellenar VISITA desde NFL")
    else:
        btn_visita = st.button("Rellenar VISITA desde NBA")

    if btn_visita:
        lookup = visita.strip().lower()
        if lookup in liga_data:
            st.session_state["v_anota_global"] = liga_data[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = liga_data[lookup]["pa_pg"]
            st.success(f"VISITA rellenado con datos reales de {visita}")
        else:
            st.error("No encontré ese equipo en la API, llénalo manualmente.")

    st.markdown("**Promedios GLOBAL del VISITA**")
    v_anota_global = st.number_input(
        "Visita: puntos que ANOTA (global)",
        value=st.session_state["v_anota_global"],
        step=0.1,
        key="v_anota_global"
    )
    v_permite_global = st.number_input(
        "Visita: puntos que PERMITE (global)",
        value=st.session_state["v_permite_global"],
        step=0.1,
        key="v_permite_global"
    )

# =========================================================
# 3) PROMEDIOS POR CONDICIÓN (MANUAL)
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
# 4) AJUSTE POR LESIONES / FORMA (más realista)
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

def option_to_multiplier(opt: str) -> float:
    # valores más parecidos a cómo se “raspa” una ofensiva en libros
    if "Seleccionado" in opt:
        # por si se te va una tilde 😅
        return 0.97
    if "Lesión ligera" in opt:
        return 0.97          # -3%
    if "Baja importante" in opt:
        return 0.93          # -7%
    if "Varias bajas" in opt:
        return 0.88          # -12%
    if "En buen momento" in opt:
        return 1.04          # +4%
    return 1.00              # healthy

col_adj1, col_adj2 = st.columns(2)
with col_adj1:
    opt_local = st.selectbox(
        "Estado ofensivo LOCAL",
        [
            "Healthy / sin reporte (1.00)",
            "Lesión ligera / 1 baja no clave (-3%)",
            "Baja importante (QB, WR1, LT) (-7%)",
            "Varias bajas ofensivas (-12%)",
            "En buen momento (+4%)",
        ],
        index=0
    )
    mult_local = option_to_multiplier(opt_local)

with col_adj2:
    opt_visita = st.selectbox(
        "Estado ofensivo VISITA",
        [
            "Healthy / sin reporte (1.00)",
            "Lesión ligera / 1 baja no clave (-3%)",
            "Baja importante (QB, WR1, LT) (-7%)",
            "Varias bajas ofensivas (-12%)",
            "En buen momento (+4%)",
        ],
        index=0
    )
    mult_visita = option_to_multiplier(opt_visita)

# =========================================================
# 5) FUNCIÓN DEL MODELO
# =========================================================
def proyeccion_suavizada(ofensiva_propia, defensa_rival, es_local=False, liga="NFL"):
    base = 0.55 * ofensiva_propia + 0.35 * defensa_rival
    if es_local:
        base += 1.5 if liga == "NFL" else 1.0
    return base

# =========================================================
# 6) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, True, liga) * mult_local
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, False, liga) * mult_visita

total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.markdown("🟦 **GLOBAL**")
st.markdown(f"- {local or 'LOCAL'} : **{pts_local_global:.1f} pts**")
st.markdown(f"- {visita or 'VISITA'} : **{pts_visita_global:.1f} pts**")
st.markdown(f"- Total modelo: **{total_global:.1f}**")
st.markdown(f"- Spread modelo (local - visita): **{spread_global:+.1f}**")

st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion_suavizada(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        True,
        liga
    ) * mult_local
    pts_visita_cv = proyeccion_suavizada(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        False,
        liga
    ) * mult_visita

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.markdown(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f}**")
    st.markdown(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}**")
    st.markdown(f"- Total casa/visita: **{total_cv:.1f}**")
    st.markdown(f"- Spread casa/visita: **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 7) LÍNEA DEL CASINO
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 0.0, 0.5)

# diferencias GLOBAL
modelo_spread_formato_casa = -spread_global
dif_spread_global = modelo_spread_formato_casa - spread_casa
dif_total_global = total_global - total_casa

st.markdown(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
st.markdown(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

# detector de TRAP
if abs(dif_spread_global) >= 8:
    st.error("🚨 Posible TRAP / o datos mal cargados: tu modelo está ≥ 8 pts del spread real.")
elif abs(dif_spread_global) >= 5:
    st.warning("⚠️ Línea sospechosa: tu modelo está ≥ 5 pts del spread real. Revísalo.")

# diferencias CASA/VISITA
if hay_cv:
    modelo_spread_cv_formato_casa = -spread_cv
    dif_spread_cv = modelo_spread_cv_formato_casa - spread_casa
    dif_total_cv = total_cv - total_casa
    st.markdown(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.markdown(f"🟩 Dif. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")
    if abs(dif_spread_cv) >= 8:
        st.error("🚨 (CV) Posible TRAP en la proyección casa/visita.")
    elif abs(dif_spread_cv) >= 5:
        st.warning("⚠️ (CV) Línea sospechosa en casa/visita.")

# =========================================================
# 7b) Moneyline opcional
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
cml1, cml2 = st.columns(2)
ml_local = cml1.number_input("Moneyline LOCAL (americano)", value=0, step=5)
ml_visita = cml2.number_input("Moneyline VISITA (americano)", value=0, step=5)

def prob_desde_ml(ml):
    if ml == 0:
        return None
    if ml > 0:
        return 100 / (ml + 100) * 100
    else:
        return (-ml) / ((-ml) + 100) * 100

prob_ml_local = prob_desde_ml(ml_local)
prob_ml_visita = prob_desde_ml(ml_visita)
if prob_ml_local is not None and prob_ml_visita is not None:
    st.caption(f"Prob. implícita LOCAL: {prob_ml_local:.1f}%, Prob. implícita VISITA: {prob_ml_visita:.1f}%")

# =========================================================
# 8) COMPARATIVA DE PROBABILIDADES POR SPREAD
# =========================================================
st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
def prob_desde_spread(spread_modelo, deporte="NFL"):
    k = 0.40 if deporte == "NFL" else 0.35
    p = 1 / (1 + math.exp(-k * spread_modelo))
    return p * 100

prob_local_modelo = prob_desde_spread(spread_global, liga)
colp1, colp2 = st.columns(2)
colp1.metric(f"{local or 'LOCAL'} (modelo)", f"{prob_local_modelo:.1f}%")
colp2.metric(f"{visita or 'VISITA'} (modelo)", f"{100 - prob_local_modelo:.1f}%")

# =========================================================
# 9) MONTE CARLO GLOBAL
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
# 10) MONTE CARLO CASA/VISITA
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
# 11) APUESTAS RECOMENDADAS (≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

# spread global
prob_visita_spread_global = 100 - prob_cover_local_global
if prob_cover_local_global >= prob_visita_spread_global:
    if prob_cover_local_global >= 55:
        recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa}", prob_cover_local_global))
else:
    visita_linea = -spread_casa
    if prob_visita_spread_global >= 55:
        recs.append((f"Spread GLOBAL: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= prob_under_global:
    if prob_over_global >= 55:
        recs.append((f"TOTAL GLOBAL: OVER {total_casa}", prob_over_global))
else:
    if prob_under_global >= 55:
        recs.append((f"TOTAL GLOBAL: UNDER {total_casa}", prob_under_global))

# casa/visita
if hay_cv and prob_cover_local_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_local_cv
    if prob_cover_local_cv >= prob_visita_spread_cv:
        if prob_cover_local_cv >= 55:
            recs.append((f"Spread CASA/VISITA: {local or 'LOCAL'} {spread_casa}", prob_cover_local_cv))
    else:
        visita_linea = -spread_casa
        if prob_visita_spread_cv >= 55:
            recs.append((f"Spread CASA/VISITA: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_cv))

if hay_cv and prob_over_cv is not None:
    prob_under_cv = 100 - prob_over_cv
    if prob_over_cv >= prob_under_cv:
        if prob_over_cv >= 55:
            recs.append((f"TOTAL CASA/VISITA: OVER {total_casa}", prob_over_cv))
    else:
        if prob_under_cv >= 55:
            recs.append((f"TOTAL CASA/VISITA: UNDER {total_casa}", prob_under_cv))

if recs:
    for texto, prob in recs:
        st.success(f"📌 {texto} — {prob:.1f}%")
else:
    st.info("No hay ninguna apuesta con probabilidad ≥ 55% según el modelo.")
