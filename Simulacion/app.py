import streamlit as st
import random
import requests

st.set_page_config(page_title="Simulador de Apuestas", layout="wide")
st.title("Simulador de Apuestas 🏈🏀")

# ===========================
# Selector de liga
# ===========================
liga = st.radio("Liga", ["NFL", "NBA"], horizontal=True)

# ============================================================
# =========================== NFL ============================
# ============================================================
if liga == "NFL":
    st.markdown("🧠 Modelo ponderado (NFL)")
    st.markdown("""
    🟦 = cálculo con promedios GLOBAL  
    🟩 = cálculo con promedios CASA/VISITA  
    Si llenas casa/visita te muestra las dos proyecciones.
    """)

    # ---------- 0. DATOS NFL DESDE SPORTSDATAIO ----------
    st.subheader("0) Conexión NFL (SportsDataIO)")
    col_api = st.columns(2)
    with col_api[0]:
        api_key_nfl = st.text_input("SportsDataIO API Key (NFL)", value=st.session_state.get("SPORTSDATAIO_KEY", ""), type="password")
        st.session_state["SPORTSDATAIO_KEY"] = api_key_nfl
    with col_api[1]:
        season_nfl = st.text_input("Season (por ej. 2025REG)", value=st.session_state.get("SEASON_NFL", "2025REG"))
        st.session_state["SEASON_NFL"] = season_nfl

    @st.cache_data(ttl=600)
    def cargar_nfl_desde_api(api_key: str, season: str):
        if not api_key:
            return {}, "Falta API Key NFL"
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

    nfl_data, nfl_error = cargar_nfl_desde_api(api_key_nfl, season_nfl)
    if nfl_error:
        st.warning(f"⚠️ {nfl_error}")
    else:
        st.info(f"✅ Datos NFL cargados ({season_nfl}) – {len(nfl_data)} equipos")

    # ---------- 1. DATOS DEL PARTIDO ----------
    st.subheader("1) Datos del partido (NFL)")
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Equipo LOCAL", value=st.session_state.get("nfl_local", ""))
        st.session_state["nfl_local"] = local
        if st.button("Rellenar LOCAL desde NFL"):
            lookup = local.strip().lower()
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

    with col2:
        visita = st.text_input("Equipo VISITA", value=st.session_state.get("nfl_visita", ""))
        st.session_state["nfl_visita"] = visita
        if st.button("Rellenar VISITA desde NFL"):
            lookup = visita.strip().lower()
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

    # ---------- 2. CASA / VISITA ----------
    st.subheader("2) Promedios por condición (opcional)")
    c1, c2 = st.columns(2)
    with c1:
        l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", value=0.0, step=0.1)
        l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", value=0.0, step=0.1)
    with c2:
        v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", value=0.0, step=0.1)
        v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", value=0.0, step=0.1)

    hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

    # ---------- 3. AJUSTE LESIONES ----------
    st.subheader("3) Ajuste por lesiones / QB")
    c3, c4 = st.columns(2)
    with c3:
        af_local = st.checkbox("¿Afecta ofensiva LOCAL?", False)
        mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
    with c4:
        af_visita = st.checkbox("¿Afecta ofensiva VISITA?", False)
        mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)
    if not af_local: mult_local = 1.0
    if not af_visita: mult_visita = 1.0

    # ---------- 4. FUNCIÓN MODELO ----------
    def proyeccion(ofensiva, defensa, es_local=False):
        base = 0.55 * ofensiva + 0.35 * defensa
        if es_local: base += 1.5
        return base

    # ---------- 5. PROYECCIONES ----------
    st.subheader("4) Proyección del modelo (GLOBAL)")
    pts_local = proyeccion(l_anota_global, v_permite_global, True) * mult_local
    pts_visita = proyeccion(v_anota_global, l_permite_global, False) * mult_visita
    total = pts_local + pts_visita
    spread = pts_local - pts_visita
    st.write(f"{local or 'LOCAL'}: **{pts_local:.1f}** | {visita or 'VISITA'}: **{pts_visita:.1f}** | Total: **{total:.1f}** | Spread: **{spread:+.1f}**")

    st.subheader("5) Proyección del modelo (CASA / VISITA)")
    if hay_cv:
        pts_local_cv = proyeccion(
            l_anota_casa if l_anota_casa > 0 else l_anota_global,
            v_permite_visita if v_permite_visita > 0 else v_permite_global,
            True
        ) * mult_local
        pts_visita_cv = proyeccion(
            v_anota_visita if v_anota_visita > 0 else v_anota_global,
            l_permite_casa if l_permite_casa > 0 else l_permite_global,
            False
        ) * mult_visita
        total_cv = pts_local_cv + pts_visita_cv
        spread_cv = pts_local_cv - pts_visita_cv
        st.write(f"{local or 'LOCAL'} (casa): **{pts_local_cv:.1f}** | {visita or 'VISITA'} (visita): **{pts_visita_cv:.1f}** | Total: **{total_cv:.1f}** | Spread: **{spread_cv:+.1f}**")
    else:
        st.info("Si llenas los 4 campos de casa/visita, te muestro también esa proyección.")

    # ---------- 6. LÍNEA DEL CASINO ----------
    st.subheader("6) Línea real del sportsbook")
    c5, c6 = st.columns(2)
    with c5:
        spread_casa = st.number_input("Spread de la casa (negativo si LOCAL es favorito)", -50.0, 50.0, 0.0, 0.5)
    with c6:
        total_casa = st.number_input("Total (O/U) de la casa", 0.0, 300.0, 0.0, 0.5)

    # ---------- 7. DIFERENCIAS ----------
    st.subheader("7) Diferencias vs línea real (GLOBAL y CASA/VISITA)")
    # formato Vegas para comparación (invertir signo del spread modelo local-visit)
    modelo_spread_formato_casa = -spread
    dif_spread_global = modelo_spread_formato_casa - spread_casa
    dif_total_global = total - total_casa
    st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
    st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

    # alertas
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

    # ---------- 8. MONTE CARLO (GLOBAL) ----------
    st.subheader("8) Simulación Monte Carlo 🟦 (GLOBAL)")
    num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
    desv_global = max(5, total * 0.15)
    covers = 0
    overs = 0
    for _ in range(num_sims_global):
        sim_local = max(0, random.gauss(pts_local, desv_global))
        sim_visita = max(0, random.gauss(pts_visita, desv_global))
        if (sim_local - sim_visita) + spread_casa >= 0:
            covers += 1
        if (sim_local + sim_visita) > total_casa:
            overs += 1
    prob_cover_local_global = covers / num_sims_global * 100
    prob_over_global = overs / num_sims_global * 100
    st.write(f"Prob. de que **{local or 'LOCAL'}** cubra (GLOBAL): **{prob_cover_local_global:.1f}%**")
    st.write(f"Prob. de OVER (GLOBAL): **{prob_over_global:.1f}%**")

    # ---------- 9. MONTE CARLO (CASA/VISITA) ----------
    st.subheader("9) Simulación Monte Carlo 🟩 (CASA / VISITA)")
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

    # ---------- 10. APUESTA RECOMENDADA ----------
    st.subheader("10) Apuesta recomendada 🟣 (≥55%)")
    opciones = []
    prob_visita_spread_global = 100 - prob_cover_local_global
    if prob_cover_local_global >= prob_visita_spread_global:
        if prob_cover_local_global >= 55:
            opciones.append((f"Spread (GLOBAL): {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_global))
    else:
        visita_linea = -spread_casa
        if prob_visita_spread_global >= 55:
            opciones.append((f"Spread (GLOBAL): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_global))

    prob_under_global = 100 - prob_over_global
    if prob_over_global >= prob_under_global and prob_over_global >= 55:
        opciones.append((f"Total (GLOBAL): OVER {total_casa:.1f}", prob_over_global))
    elif prob_under_global >= 55:
        opciones.append((f"Total (GLOBAL): UNDER {total_casa:.1f}", prob_under_global))

    if hay_cv and prob_cover_local_cv is not None:
        prob_visita_spread_cv = 100 - prob_cover_local_cv
        if prob_cover_local_cv >= prob_visita_spread_cv and prob_cover_local_cv >= 55:
            opciones.append((f"Spread (CASA/VISITA): {local or 'LOCAL'} {spread_casa:+.1f}", prob_cover_local_cv))
        elif prob_visita_spread_cv >= 55:
            visita_linea = -spread_casa
            opciones.append((f"Spread (CASA/VISITA): {visita or 'VISITA'} {visita_linea:+.1f}", prob_visita_spread_cv))

    if hay_cv and prob_over_cv is not None:
        prob_under_cv = 100 - prob_over_cv
        if prob_over_cv >= prob_under_cv and prob_over_cv >= 55:
            opciones.append((f"Total (CASA/VISITA): OVER {total_casa:.1f}", prob_over_cv))
        elif prob_under_cv >= 55:
            opciones.append((f"Total (CASA/VISITA): UNDER {total_casa:.1f}", prob_under_cv))

    if opciones:
        mejor = max(opciones, key=lambda x: x[1])
        st.success(f"📌 Apuesta sugerida: **{mejor[0]}**")
        st.write(f"Probabilidad estimada por el modelo: **{mejor[1]:.1f}%**")
        st.caption("Nota: es solo la apuesta con mayor probabilidad, no está midiendo valor/cuota.")
    else:
        st.info("Llena los datos del partido y las líneas para ver una recomendación (≥55%).")


# ============================================================
# =========================== NBA ============================
# ============================================================
else:
    st.subheader("🏀 NBA — Versión avanzada (global + últimos 5 + pace)")
    # ---------- 1) GLOBAL ----------
    c1, c2 = st.columns(2)
    with c1:
        local_name = st.text_input("Equipo LOCAL (NBA)", value=st.session_state.get("nba_local", "Celtics"))
        st.session_state["nba_local"] = local_name
        l_anota_global = st.number_input("LOCAL: puntos que ANOTA (global)", value=118.0, step=0.1)
        l_permite_global = st.number_input("LOCAL: puntos que PERMITE (global)", value=111.9, step=0.1)
    with c2:
        visita_name = st.text_input("Equipo VISITA (NBA)", value=st.session_state.get("nba_visita", "Grizzlies"))
        st.session_state["nba_visita"] = visita_name
        v_anota_global = st.number_input("VISITA: puntos que ANOTA (global)", value=113.7, step=0.1)
        v_permite_global = st.number_input("VISITA: puntos que PERMITE (global)", value=118.6, step=0.1)

    # ---------- 2) Últimos 5 + Pace ----------
    st.markdown("### 2) Últimos 5 + Pace (per 100 poss)")
    c3, c4 = st.columns(2)
    with c3:
        pace_local_5 = st.number_input("PACE LOCAL (últ 5)", value=96.8, step=0.1)
        off_local_5  = st.number_input("Ofensiva LOCAL (pts/100 poss, últ 5)", value=115.9, step=0.1)
        def_local_5  = st.number_input("Defensiva LOCAL (pts permitidos/100 poss, últ 5)", value=112.2, step=0.1)
    with c4:
        pace_visita_5 = st.number_input("PACE VISITA (últ 5)", value=102.8, step=0.1)
        off_visita_5  = st.number_input("Ofensiva VISITA (pts/100 poss, últ 5)", value=107.6, step=0.1)
        def_visita_5  = st.number_input("Defensiva VISITA (pts/100 poss, últ 5)", value=114.6, step=0.1)

    pace_liga = st.number_input("PACE promedio liga (NBA)", value=99.0, step=0.1)
    peso_recent, peso_global = 0.65, 0.35

    # ---------- 3) Lesiones / forma (selector simple) ----------
    st.markdown("### 3) Lesiones / forma (selector simple, suma/resta puntos)")
    ajustes = {
        "Healthy (0)": 0.0,
        "Menor ausencia (−1)": -1.0,
        "Playmaker fuera (−2)": -2.0,
        "Estrella fuera (−3)": -3.0,
        "Dos+ titulares (−4)": -4.0,
        "En racha (+1)": 1.0,
        "Back-to-back (−0.5)": -0.5,
    }
    c5, c6 = st.columns(2)
    with c5:
        estado_local = st.selectbox("LOCAL — estado", list(ajustes.keys()), index=0, key="nba_estado_local")
    with c6:
        estado_visita = st.selectbox("VISITA — estado", list(ajustes.keys()), index=0, key="nba_estado_visita")
    adj_local = ajustes[estado_local]
    adj_visita = ajustes[estado_visita]

    # ---------- 4) Línea del casino ----------
    st.markdown("### 4) Línea del casino (formato Vegas)")
    c7, c8 = st.columns(2)
    with c7:
        spread_casa_local = st.number_input("Spread de la casa (negativo si LOCAL es favorito)", value=-6.5, step=0.5)
    with c8:
        total_casa = st.number_input("Total (O/U) de la casa", value=234.0, step=0.5)

    # ---------- 5) Proyección final automática ----------
    st.markdown("### 5) Proyección final del modelo (automática)")
    pace_med = (pace_local_5 + pace_visita_5) / 2.0 if (pace_local_5 > 0 and pace_visita_5 > 0) else pace_liga
    rec_l_pg  = (0.6 * off_local_5  + 0.4 * def_visita_5) * (pace_med / 100.0)
    rec_v_pg  = (0.6 * off_visita_5 + 0.4 * def_local_5 ) * (pace_med / 100.0)
    glob_l_pg = (l_anota_global + v_permite_global) / 2.0
    glob_v_pg = (v_anota_global + l_permite_global) / 2.0
    pts_local_model  = (peso_recent * rec_l_pg  + peso_global * glob_l_pg) + adj_local
    pts_visita_model = (peso_recent * rec_v_pg  + peso_global * glob_v_pg) + adj_visita
    total_modelo = pts_local_model + pts_visita_model
    margin_local = pts_local_model - pts_visita_model
    spread_model_local = -margin_local
    spread_model_visita = -spread_model_local
    st.write(f"**{local_name or 'LOCAL'}**: {pts_local_model:.1f}  |  **{visita_name or 'VISITA'}**: {pts_visita_model:.1f}")
    st.write(f"**Total modelo:** {total_modelo:.1f}  |  **Spread modelo (Vegas): LOCAL {spread_model_local:+.1f}**")

    # ---------- 6) Diferencias vs línea + alertas ----------
    st.markdown("### 6) Diferencias vs línea + alertas")
    # Trabajar en márgenes para que los signos de DIF sean intuitivos por lado
    house_margin_local  = -spread_casa_local
    model_margin_local  = -spread_model_local
    dif_spread_local    = model_margin_local - house_margin_local  # ej: 5.1 - 6.5 = -1.4
    house_margin_visita = -house_margin_local
    model_margin_visita = -model_margin_local
    dif_spread_visita   = model_margin_visita - house_margin_visita # ej: -5.1 - (-6.5) = +1.4
    dif_total = total_modelo - total_casa

    def tag_spread(x):
        ax = abs(x)
        if ax >= 4: return "🚨 Fuerte"
        if ax >= 3: return "⚠️ Precaución"
        if ax >= 2: return "ℹ️ Diferencia"
        return "—"

    def tag_total(x):
        ax = abs(x)
        if ax >= 10:  return "🚨 Fuerte"
        if ax >= 8:   return "⚠️ Precaución"
        if ax >= 6:   return "ℹ️ Diferencia"
        return "—"

    c9, c10 = st.columns(2)
    with c9:
        st.write(f"**DIF SPREAD LOCAL (modelo − casa):** {dif_spread_local:+.1f}  {tag_spread(dif_spread_local)}")
        st.write(f"**DIF SPREAD VISITA (modelo − casa):** {dif_spread_visita:+.1f}  {tag_spread(dif_spread_visita)}")
    with c10:
        st.write(f"**DIF TOTAL (modelo − casa):** {dif_total:+.1f}  {tag_total(dif_total)}")

    # ---------- 7) Monte Carlo ----------
    st.markdown("### 7) Simulación Monte Carlo")
    num_sims = st.slider("Nº simulaciones", 1000, 50000, 10000, 1000)
    covers, overs = 0, 0
    desv = max(6.0, total_modelo * 0.12)
    for _ in range(num_sims):
        sim_l = max(0, random.gauss(pts_local_model, desv))
        sim_v = max(0, random.gauss(pts_visita_model, desv))
        # cubrir spread de la casa (formato Vegas local)
        if (sim_l - sim_v) + spread_casa_local >= 0:
            covers += 1
        if (sim_l + sim_v) > total_casa:
            overs += 1
    prob_cover_local = covers / num_sims * 100.0
    prob_over = overs / num_sims * 100.0
    prob_under = 100.0 - prob_over
    st.write(f"Prob. que **{local_name or 'LOCAL'}** cubra {spread_casa_local:+.1f}: **{prob_cover_local:.1f}%**")
    st.write(f"Prob. **OVER {total_casa:.1f}**: {prob_over:.1f}%  |  **UNDER**: {prob_under:.1f}%")

    # ---------- 8) Edge (modelo − casa) — por lado ----------
    st.markdown("### 8) Edge (modelo − casa) — por lado")
    spread_casa_visita = -spread_casa_local
    st.write(f"- **LOCAL ({local_name or 'LOCAL'})** — Modelo: {spread_model_local:+.1f}  |  Casa: {spread_casa_local:+.1f}  |  **DIF:** {dif_spread_local:+.1f}")
    st.write(f"- **VISITA ({visita_name or 'VISITA'})** — Modelo: {spread_model_visita:+.1f}  |  Casa: {spread_casa_visita:+.1f}  |  **DIF:** {dif_spread_visita:+.1f}")
    st.write(f"- **TOTAL** — Modelo: {total_modelo:.1f}  |  Casa: {total_casa:.1f}  |  **DIF:** {dif_total:+.1f}")

    # ---------- 9) Apuestas recomendadas (≥55% y edge alineado) ----------
    st.markdown("### 9) Apuestas recomendadas (requiere prob ≥55% y edge alineado)")
    recs = []
    prob_cover_visita = 100.0 - prob_cover_local

    # Spread: exigir probabilidad y edge del mismo lado
    if prob_cover_local >= 55 and dif_spread_local > 0:
        recs.append(f"🟢 Spread — {local_name or 'LOCAL'} {spread_casa_local:+.1f}  ({prob_cover_local:.1f}%, DIF {dif_spread_local:+.1f})")
    if prob_cover_visita >= 55 and dif_spread_visita > 0:
        recs.append(f"🟢 Spread — {visita_name or 'VISITA'} {(-spread_casa_local):+.1f}  ({prob_cover_visita:.1f}%, DIF {dif_spread_visita:+.1f})")

    # Totales: OVER si Prob≥55 y DIF total > 0; UNDER si Prob≥55 y DIF total < 0
    if prob_over >= 55 and dif_total > 0:
        recs.append(f"🟢 OVER {total_casa:.1f}  ({prob_over:.1f}%, DIF {dif_total:+.1f})")
    if prob_under >= 55 and dif_total < 0:
        recs.append(f"🟢 UNDER {total_casa:.1f}  ({prob_under:.1f}%, DIF {dif_total:+.1f})")

    if recs:
        for r in recs:
            st.success(r)
    else:
        st.info("Sin pick: falta que probabilidad ≥55% y edge estén alineados. Revisa número o espera mejor línea.")
