import streamlit as st
import random
import requests

# =========================================================
# CONFIG GENERAL
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (multi-liga)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA (manual, solo NFL).  
Si llenas casa/visita te muestra las dos proyecciones.
""")

# =========================================================
# 0. SELECTOR DE LIGA
# =========================================================
liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA"], horizontal=True)

# =========================================================
# KEYS
# =========================================================
SPORTSDATAIO_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
NFL_SEASON = "2025REG"

# =========================================================
# 0a. CARGA NFL (solo si toca)
# =========================================================
@st.cache_data(ttl=600)
def cargar_nfl_desde_api(api_key: str, season: str):
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

if liga == "NFL":
    nfl_data, nfl_error = cargar_nfl_desde_api(SPORTSDATAIO_KEY, NFL_SEASON)
    if nfl_error:
        st.warning(f"⚠️ {nfl_error}")
    else:
        st.info(f"✅ Datos NFL cargados, {len(nfl_data)} equipos ({NFL_SEASON})")
else:
    nfl_data, nfl_error = {}, ""
    st.warning("🟡 NBA no hay carga automática, llena los promedios manualmente.")

# =========================================================
# 1. DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
c1, c2 = st.columns(2)

with c1:
    local = st.text_input("Equipo LOCAL", "").strip()
    if liga == "NFL":
        if st.button("Rellenar LOCAL desde NFL"):
            lookup = local.lower()
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

with c2:
    visita = st.text_input("Equipo VISITA", "").strip()
    if liga == "NFL":
        if st.button("Rellenar VISITA desde NFL"):
            lookup = visita.lower()
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
# 2) BLOQUE DIFERENTE POR LIGA
# =========================================================
if liga == "NFL":
    st.subheader("2) Promedios por condición (opcional)")
    c3, c4 = st.columns(2)
    with c3:
        l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", value=0.0, step=0.1)
        l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", value=0.0, step=0.1)
    with c4:
        v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", value=0.0, step=0.1)
        v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", value=0.0, step=0.1)
    hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])
else:
    st.subheader("2) Factores avanzados NBA (pace / eficiencia) 🏀")
    st.caption("Llena estos datos para que el total de NBA se acerque más a las líneas reales.")
    colL, colR = st.columns(2)
    with colL:
        pace_local = st.number_input("Pace LOCAL (posesiones)", value=99.0, step=0.5)
        off_local_100 = st.number_input("Ofensiva LOCAL (pts/100 poss)", value=112.0, step=0.5)
        def_local_100 = st.number_input("Defensiva LOCAL (pts permitidos/100 poss)", value=113.0, step=0.5)
    with colR:
        pace_visita = st.number_input("Pace VISITA (posesiones)", value=99.0, step=0.5)
        off_visita_100 = st.number_input("Ofensiva VISITA (pts/100 poss)", value=112.0, step=0.5)
        def_visita_100 = st.number_input("Defensiva VISITA (pts permitidos/100 poss)", value=113.0, step=0.5)
    pace_liga = st.number_input("Pace promedio liga", value=99.0, step=0.5)
    hay_cv = False  # para que no dispare la de casa/visita luego

# =========================================================
# 3. AJUSTE POR LESIONES / FORMA
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

ajustes_map = {
    "Normal": 1.00,
    "1-2 bajas importantes": 0.97,
    "Varias bajas / descanso pesado": 0.94,
    "Equipo en buen momento": 1.03,
}

c7, c8 = st.columns(2)
with c7:
    estado_local = st.selectbox(
        "Estado ofensivo LOCAL",
        list(ajustes_map.keys()),
        index=0,
        key="estado_local",
    )
with c8:
    estado_visita = st.selectbox(
        "Estado ofensivo VISITA",
        list(ajustes_map.keys()),
        index=0,
        key="estado_visita",
    )

mult_local = ajustes_map[estado_local]
mult_visita = ajustes_map[estado_visita]

# extra para NFL: QB titular
qb_penalizacion = 3.0  # pts
if liga == "NFL":
    cqb1, cqb2 = st.columns(2)
    with cqb1:
        qb_local_juega = st.checkbox("¿Juega QB titular LOCAL?", True)
    with cqb2:
        qb_visita_juega = st.checkbox("¿Juega QB titular VISITA?", True)
else:
    qb_local_juega = True
    qb_visita_juega = True

st.caption("Estos multiplicadores afectan a los puntos proyectados. 1.00 = normal.")

# =========================================================
# 4. FUNCIONES DE PROYECCIÓN
# =========================================================
def proyeccion_nfl(ofensiva, defensa_rival, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa_rival
    if es_local:
        base += 1.5
    return base

def proyeccion_nba(
    pace_local,
    pace_visita,
    off_local_100,
    off_visita_100,
    def_local_100,
    def_visita_100,
    pace_liga,
):
    pace_combinado = (pace_local + pace_visita) / 2
    pace_final = 0.7 * pace_combinado + 0.3 * pace_liga
    fac_def_visita = 100.0 / def_visita_100 if def_visita_100 > 0 else 1.0
    fac_def_local = 100.0 / def_local_100 if def_local_100 > 0 else 1.0
    off_local_aj = off_local_100 * fac_def_visita
    off_visita_aj = off_visita_100 * fac_def_local
    pts_local = off_local_aj * (pace_final / 100.0)
    pts_visita = off_visita_aj * (pace_final / 100.0)
    return pts_local, pts_visita

# =========================================================
# 4. PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

if liga == "NFL":
    pts_local_modelo = proyeccion_nfl(l_anota_global, v_permite_global, es_local=True) * mult_local
    pts_visita_modelo = proyeccion_nfl(v_anota_global, l_permite_global, es_local=False) * mult_visita

    if not qb_local_juega:
        pts_local_modelo -= qb_penalizacion
    if not qb_visita_juega:
        pts_visita_modelo -= qb_penalizacion
else:
    pts_local_modelo, pts_visita_modelo = proyeccion_nba(
        pace_local,
        pace_visita,
        off_local_100,
        off_visita_100,
        def_local_100,
        def_visita_100,
        pace_liga,
    )
    pts_local_modelo *= mult_local
    pts_visita_modelo *= mult_visita

total_modelo = pts_local_modelo + pts_visita_modelo
spread_modelo = pts_local_modelo - pts_visita_modelo

st.markdown("🟦 **GLOBAL**")
st.write(f"- {local or 'LOCAL'}: **{pts_local_modelo:.1f} pts**")
st.write(f"- {visita or 'VISITA'}: **{pts_visita_modelo:.1f} pts**")
st.write(f"- Total modelo: **{total_modelo:.1f}**")
st.write(f"- Spread modelo (local - visita): **{spread_modelo:+.1f}**")

# proyección casa/visita solo NFL
if liga == "NFL" and hay_cv:
    st.markdown("🟩 **CASA / VISITA**")
    pts_local_cv = proyeccion_nfl(l_anota_casa or l_anota_global,
                                  v_permite_visita or v_permite_global,
                                  es_local=True) * mult_local
    pts_visita_cv = proyeccion_nfl(v_anota_visita or v_anota_global,
                                   l_permite_casa or l_permite_global,
                                   es_local=False) * mult_visita
    if not qb_local_juega:
        pts_local_cv -= qb_penalizacion
    if not qb_visita_juega:
        pts_visita_cv -= qb_penalizacion
    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv
    st.write(f"- {local or 'LOCAL'} (casa): **{pts_local_cv:.1f}**")
    st.write(f"- {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}**")
    st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
    st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los 4 campos de casa/visita (solo NFL), te muestro también esa proyección.")

# =========================================================
# 5. LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")

c_lin1, c_lin2 = st.columns(2)
with c_lin1:
    spread_casa = st.number_input("Spread del casino (negativo si LOCAL favorito)", value=0.0, step=0.5)
with c_lin2:
    total_casa = st.number_input("Total (O/U) del casino", value=0.0, step=0.5)

with st.expander("🔎 Comparación de spreads (GLOBAL)", expanded=True):
    st.write(f"- Modelo (formato casa): **LOCAL {spread_modelo:+.1f}**")
    if spread_casa != 0:
        st.write(f"- Casa: **LOCAL {(-spread_casa):+.1f}**")
    else:
        st.write(f"- Casa: **LOCAL +0.0**")
    dif_spread = spread_modelo - (-spread_casa)
    st.write(f"- **DIF. SPREAD (GLOBAL)**: **{dif_spread:+.1f} pts**")

with st.expander("🔎 Comparación de totales (GLOBAL)", expanded=True):
    st.write(f"- Modelo: **{total_modelo:.1f}**")
    st.write(f"- Casa: **{total_casa:.1f}**")
    dif_total = total_modelo - total_casa
    st.write(f"- **DIF. TOTAL (GLOBAL)**: **{dif_total:+.1f} pts**")

if abs(dif_spread) >= 3.0 or abs(dif_total) >= 12.0:
    tipo = "spread" if abs(dif_spread) >= 3.0 else "total"
    st.error(f"⚠️ Línea muy diferente a tu modelo (**{tipo}**). Puede ser trap line o info que no estás metiendo.")

# =========================================================
# 5b. MONEYLINE
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
m1, m2 = st.columns(2)
with m1:
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with m2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0, step=5)

def ml_to_prob(ml):
    if ml == 0:
        return 0.0
    if ml > 0:
        return 100.0 / (ml + 100.0) * 100.0
    else:
        return (-ml) / ((-ml) + 100.0) * 100.0

prob_imp_local = ml_to_prob(ml_local)
prob_imp_visita = ml_to_prob(ml_visita)

c_imp1, c_imp2 = st.columns(2)
with c_imp1:
    st.write(f"Prob. implícita LOCAL: **{prob_imp_local:.1f}%**")
with c_imp2:
    st.write(f"Prob. implícita VISITA: **{prob_imp_visita:.1f}%**")

# =========================================================
# 5c. COMPARATIVA DE PROBABILIDADES
# =========================================================
st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")

def spread_to_winprob(spread):
    return 50 + (spread * 3.5)

prob_modelo_local = max(1.0, min(99.0, spread_to_winprob(spread_modelo)))
prob_modelo_visita = 100.0 - prob_modelo_local

c_prob1, c_prob2 = st.columns(2)
with c_prob1:
    st.write(f"{local or 'LOCAL'} (modelo): **{prob_modelo_local:.1f}%**")
    st.write(f"Prob. implícita LOCAL (casa): **{prob_imp_local:.1f}%**")
with c_prob2:
    st.write(f"{visita or 'VISITA'} (modelo): **{prob_modelo_visita:.1f}%**")
    st.write(f"Prob. implícita VISITA (casa): **{prob_imp_visita:.1f}%**")

# =========================================================
# 6. MONTE CARLO (GLOBAL)
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones (GLOBAL)", 1000, 20000, 10000, 1000)

covers, overs = 0, 0
desv = max(5, total_modelo * 0.15)

for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local_modelo, desv))
    sim_v = max(0, random.gauss(pts_visita_modelo, desv))
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover = covers / num_sims * 100
prob_over = overs / num_sims * 100
st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover:.1f}%**")
st.write(f"Prob. de **OVER** (GLOBAL): **{prob_over:.1f}%**")

# =========================================================
# 6b. MONTE CARLO CASA/VISITA (solo NFL)
# =========================================================
st.subheader("6b) Simulación Monte Carlo 🟩 (CASA / VISITA) ↩︎")
if liga == "NFL" and hay_cv:
    covers_cv, overs_cv = 0, 0
    for _ in range(num_sims):
        sim_l = max(0, random.gauss(pts_local_cv, desv))
        sim_v = max(0, random.gauss(pts_visita_cv, desv))
        if (sim_l - sim_v) + spread_casa >= 0:
            covers_cv += 1
        if (sim_l + sim_v) > total_casa:
            overs_cv += 1
    prob_cover_cv = covers_cv / num_sims * 100
    prob_over_cv = overs_cv / num_sims * 100
    st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (c/v): **{prob_cover_cv:.1f}%**")
    st.write(f"Prob. de **OVER** (c/v): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr esta simulación llena los campos de casa/visita (solo NFL).")

# =========================================================
# 7. APUESTAS RECOMENDADAS
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")
recs = []
if prob_cover >= 55:
    recs.append(f"🟢 Spread GLOBAL: {local or 'LOCAL'} {spread_casa:+.1f} → **{prob_cover:.1f}%**")
if prob_over >= 55:
    recs.append(f"🟢 Total GLOBAL: {'OVER' if total_modelo > total_casa else 'UNDER'} {total_casa:.1f} → **{prob_over:.1f}%**")

if liga == "NFL" and hay_cv:
    # en este caso sí tenemos prob_cover_cv y prob_over_cv
    if 'prob_cover_cv' in locals() and prob_cover_cv >= 55:
        recs.append(f"🟢 Spread C/V: {local or 'LOCAL'} {spread_casa:+.1f} → **{prob_cover_cv:.1f}%**")
    if 'prob_over_cv' in locals() and prob_over_cv >= 55:
        recs.append(f"🟢 Total C/V: {'OVER' if total_cv > total_casa else 'UNDER'} {total_casa:.1f} → **{prob_over_cv:.1f}%**")

if recs:
    for r in recs:
        st.success(r)
else:
    st.info("Ninguna apuesta supera el 55% con los datos actuales.")

# =========================================================
# 8. EDGE DEL MODELO VS CASA
# =========================================================
st.subheader("8) Edge del modelo vs casa")

edge_local = prob_cover - prob_imp_local if ml_local != 0 else prob_cover - 50
edge_visita = (100 - prob_cover) - prob_imp_visita if ml_visita != 0 else (100 - prob_cover) - 50

if edge_local >= 0:
    st.success(f"Edge LOCAL: **{edge_local:.1f}%** (tu modelo ve más valor en local)")
else:
    st.error(f"Edge LOCAL: **{edge_local:.1f}%** (la casa está más alta que tu modelo)")

if edge_visita >= 0:
    st.success(f"Edge VISITA: **{edge_visita:.1f}%** (tu modelo ve más valor en visita)")
else:
    st.error(f"Edge VISITA: **{edge_visita:.1f}%** (la casa está más alta que tu modelo)")
