import streamlit as st
import random
import requests

# =========================================================
# CONFIGURACIÓN BÁSICA
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
# 0. SELECCIÓN DE LIGA
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# tu key actual
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"

# temporadas por defecto
SEASON_NFL = "2025REG"
SEASON_NBA = "2025"  # esta te la va a marcar 401 porque tu trial no trae NBA


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

        played = wins + losses + ties
        games_raw = t.get("Games", 0) or 0
        games_played = played if played > 0 else games_raw if games_raw > 0 else 1

        equipos[name] = {
            "pf_pg": round(pf / games_played, 2),
            "pa_pg": round(pa / games_played, 2),
        }
    return equipos, ""


@st.cache_data(ttl=600)
def cargar_nba(api_key: str, season: str):
    """
    Tu trial no trae este subfeed, así que devolvemos vacía + mensaje.
    Cuando lo actives, aquí pones el endpoint real de NBA y funcionará igual que NFL.
    """
    return {}, "NBA no habilitado en tu cuenta (401). Pídeles el subfeed de NBA."


# cargar según liga
if liga == "NFL":
    data_liga, err_liga = cargar_nfl(SPORTSDATAIO_KEY, SEASON_NFL)
else:
    data_liga, err_liga = cargar_nba(SPORTSDATAIO_KEY, SEASON_NBA)

# status bar
if err_liga:
    st.warning(err_liga)
else:
    st.success(f"✅ Datos {liga} cargados — {len(data_liga)} equipos")

# =========================================================
# 1) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "", key="local_name")

    # texto del botón según liga
    texto_local_btn = "Rellenar LOCAL desde NFL" if liga == "NFL" else "Rellenar LOCAL desde NBA"
    if st.button(texto_local_btn):
        lookup = local.strip().lower()
        if lookup in data_liga:
            st.session_state["l_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["l_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"LOCAL rellenado con datos reales de {local}")
        else:
            st.error(f"No encontré ese equipo en {liga}")

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

    texto_visita_btn = "Rellenar VISITA desde NFL" if liga == "NFL" else "Rellenar VISITA desde NBA"
    if st.button(texto_visita_btn):
        lookup = visita.strip().lower()
        if lookup in data_liga:
            st.session_state["v_anota_global"] = data_liga[lookup]["pf_pg"]
            st.session_state["v_permite_global"] = data_liga[lookup]["pa_pg"]
            st.success(f"VISITA rellenado con datos reales de {visita}")
        else:
            st.error(f"No encontré ese equipo en {liga}")

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
# 2) PROMEDIOS POR CONDICIÓN (manual)
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
# 3) AJUSTE POR LESIONES / FORMA / QB
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

colL, colV = st.columns(2)

opciones_forma = {
    "Healthy / completo": 1.00,
    "1-2 bajas importantes": 0.97,
    "Varias bajas ofensivas": 0.94,
    "En buen momento": 1.03,
}

with colL:
    estado_local = st.selectbox("Estado ofensivo LOCAL", list(opciones_forma.keys()), index=0)
    mult_local_forma = opciones_forma[estado_local]

    # solo NFL tiene sentido el ajuste directo de QB
    mult_local_qb = 1.0
    if liga == "NFL":
        qb_local_titular = st.checkbox("¿Juega QB titular (LOCAL)?", value=True)
        if not qb_local_titular:
            mult_local_qb = 0.88  # castigo típico por no QB titular

with colV:
    estado_visita = st.selectbox("Estado ofensivo VISITA", list(opciones_forma.keys()), index=0)
    mult_visita_forma = opciones_forma[estado_visita]

    mult_visita_qb = 1.0
    if liga == "NFL":
        qb_visita_titular = st.checkbox("¿Juega QB titular (VISITA)?", value=True)
        if not qb_visita_titular:
            mult_visita_qb = 0.88

st.caption("Estos multiplicadores afectan a los puntos proyectados. 1.00 = normal, <1 = un poco peor, >1 = mejor.")

# multiplicadores finales
mult_local_total = mult_local_forma * mult_local_qb
mult_visita_total = mult_visita_forma * mult_visita_qb

# =========================================================
# 4) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

def proyeccion(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5  # ventaja de local
    return base

# GLOBAL
pts_local_glob = proyeccion(l_anota_global, v_permite_global, True) * mult_local_total
pts_visita_glob = proyeccion(v_anota_global, l_permite_global, False) * mult_visita_total
total_modelo_glob = pts_local_glob + pts_visita_glob
spread_modelo_glob = pts_local_glob - pts_visita_glob  # + = local arriba

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local_glob:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita_glob:.1f} pts**")
st.write(f"- Total modelo: **{total_modelo_glob:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_modelo_glob:+.1f}**")

# CASA / VISITA
st.markdown("🟩 **CASA / VISITA**")
if hay_cv:
    pts_local_cv = proyeccion(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        True,
    ) * mult_local_total

    pts_visita_cv = proyeccion(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        False,
    ) * mult_visita_total

    total_modelo_cv = pts_local_cv + pts_visita_cv
    spread_modelo_cv = pts_local_cv - pts_visita_cv
    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f}**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}**")
    st.write(f"- Total modelo (c/v): **{total_modelo_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_modelo_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

# =========================================================
# 5) LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")
c_spread, c_total = st.columns(2)
with c_spread:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", -50.0, 50.0, 0.0, 0.5)
with c_total:
    total_casa = st.number_input("Total (O/U) del casino", 0.0, 300.0, 0.0, 0.5)

st.markdown("🔎 **Comparación de spreads (GLOBAL)**")
modelo_formato_casa = -spread_modelo_glob  # convertimos nuestro spread a formato casino
st.write(f"- Modelo (formato casa): LOCAL {modelo_formato_casa:+.1f}")
st.write(f"- Casa: LOCAL {spread_casa:+.1f}")
dif_spread_glob = modelo_formato_casa - spread_casa
st.write(f"- DIF. SPREAD (GLOBAL): **{dif_spread_glob:+.1f} pts**")

st.markdown("🔎 **Comparación de totales (GLOBAL)**")
st.write(f"- Modelo: {total_modelo_glob:.1f}")
st.write(f"- Casa: {total_casa:.1f}")
dif_total_glob = total_modelo_glob - total_casa
st.write(f"- DIF. TOTAL (GLOBAL): **{dif_total_glob:+.1f} pts**")

# alerta trap line
alertas = []
if abs(dif_spread_glob) >= 5:
    alertas.append(f"Spread muy diferente (modelo vs casa): {dif_spread_glob:+.1f} pts.")
if abs(dif_total_glob) >= 8:
    alertas.append(f"Total muy diferente (modelo vs casa): {dif_total_glob:+.1f} pts.")

if alertas:
    st.error("⚠️ Línea muy diferente a tu modelo. Puede ser trap line o info que tu modelo no trae:\n- " + "\n- ".join(alertas))

# =========================================================
# 5b) MONEYLINE DEL SPORTSBOOK (opcional)
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
c_ml1, c_ml2 = st.columns(2)
with c_ml1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with c_ml2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0, step=5)

def americano_a_prob(ml):
    if ml == 0:
        return None
    if ml > 0:
        return 100 / (ml + 100) * 100
    else:
        return (-ml) / (-ml + 100) * 100

prob_imp_local_casa = americano_a_prob(ml_local)
prob_imp_visita_casa = americano_a_prob(ml_visita)

st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
# modelo: usamos una probabilidad simple: quien anota más en el modelo
prob_modelo_local = 50.0
prob_modelo_visita = 50.0
if pts_local_glob + pts_visita_glob > 0:
    prob_modelo_local = pts_local_glob / (pts_local_glob + pts_visita_glob) * 100
    prob_modelo_visita = 100 - prob_modelo_local

st.write(f"{local or 'LOCAL'} (modelo): **{prob_modelo_local:.1f}%**")
st.write(f"{visita or 'VISITA'} (modelo): **{prob_modelo_visita:.1f}%**")
if prob_imp_local_casa is not None:
    st.write(f"Prob. implícita LOCAL (casa): **{prob_imp_local_casa:.1f}%**")
if prob_imp_visita_casa is not None:
    st.write(f"Prob. implícita VISITA (casa): **{prob_imp_visita_casa:.1f}%**")

# =========================================================
# 6) SIMULACIÓN MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)

desv_global = max(5, total_modelo_glob * 0.15)
covers = 0
overs = 0

for _ in range(num_sims_global):
    sim_local = max(0, random.gauss(pts_local_glob, desv_global))
    sim_visita = max(0, random.gauss(pts_visita_glob, desv_global))

    # cubrir spread de la casa
    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1

    if (sim_local + sim_visita) > total_casa:
        overs += 1

prob_cover_local_global = covers / num_sims_global * 100
prob_over_global = overs / num_sims_global * 100

st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_local_global:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =========================================================
# 6c) EDGE EN SPREAD (modelo vs cuota estándar)
# =========================================================
st.subheader("6c) Edge en spread (modelo vs cuota estándar)")

prob_implicita_110 = 52.38  # porcentaje típico -110
edge_spread_local = prob_cover_local_global - prob_implicita_110
edge_spread_visita = (100 - prob_cover_local_global) - prob_implicita_110

if edge_spread_local > 0:
    st.success(f"Edge en spread para **{local or 'LOCAL'}**: +{edge_spread_local:.1f}% (modelo ve más valor que -110)")
else:
    st.warning(f"Edge en spread para **{local or 'LOCAL'}**: {edge_spread_local:.1f}% (por debajo de -110)")

if edge_spread_visita > 0:
    st.success(f"Edge en spread para **{visita or 'VISITA'}**: +{edge_spread_visita:.1f}%")
else:
    st.warning(f"Edge en spread para **{visita or 'VISITA'}**: {edge_spread_visita:.1f}%")

# =========================================================
# 6b) SIMULACIÓN MONTE CARLO (CASA / VISITA)
# =========================================================
st.subheader("6b) Simulación Monte Carlo 🟩 (CASA / VISITA)")
prob_cover_local_cv = None
prob_over_cv = None
if hay_cv:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000)
    desv_cv = max(5, total_modelo_cv * 0.15)
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
# 7) APUESTAS RECOMENDADAS (si ≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []

# spread global: local o visita
prob_visita_spread_global = 100 - prob_cover_local_global
if prob_cover_local_global >= prob_visita_spread_global:
    if prob_cover_local_global >= 55:
        recs.append((f"Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_global))
else:
    visita_linea = -spread_casa
    if prob_visita_spread_global >= 55:
        recs.append((f"Spread GLOBAL: {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

# total global
prob_under_global = 100 - prob_over_global
if prob_over_global >= prob_under_global:
    if prob_over_global >= 55:
        recs.append((f"Total GLOBAL: OVER {total_casa:.1f}", prob_over_global))
else:
    if prob_under_global >= 55:
        recs.append((f"Total GLOBAL: UNDER {total_casa:.1f}", prob_under_global))

# casa/visita si hay
if hay_cv and prob_cover_local_cv is not None:
    prob_visita_spread_cv = 100 - prob_cover_local_cv
    if prob_cover_local_cv >= prob_visita_spread_cv:
        if prob_cover_local_cv >= 55:
            recs.append((f"Spread C/V: {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_cv))
    else:
        visita_linea = -spread_casa
        if prob_visita_spread_cv >= 55:
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
    for r in sorted(recs, key=lambda x: x[1], reverse=True):
        st.success(f"{r[0]} — {r[1]:.1f}%")
else:
    st.info("Aún no hay apuestas ≥ 55% según tu simulación.")

# =========================================================
# 8) EDGE DEL MODELO VS CASA (el que ya tenías)
# =========================================================
st.subheader("8) Edge del modelo vs casa")

# edge en spread: cuánto más arriba/abajo está tu spread del spread casa, en %
if total_casa > 0:
    pass  # aquí no necesitamos nada más

# lo dejamos como resumen en texto
if dif_spread_glob > 0:
    st.warning(f"Edge LOCAL: +{dif_spread_glob:.1f} pts (tu modelo es más alto que la casa)")
else:
    st.warning(f"Edge VISITA: {dif_spread_glob:.1f} pts (tu modelo favorece más a la visita)")

if dif_total_glob > 0:
    st.info(f"Edge TOTAL hacia OVER: +{dif_total_glob:.1f} pts")
elif dif_total_glob < 0:
    st.info(f"Edge TOTAL hacia UNDER: {dif_total_glob:.1f} pts")
else:
    st.info("Tu total es igual al de la casa.")
