import os
import math
import requests
import numpy as np
import pandas as pd
import streamlit as st

# -----------------------------------------------------------
# Utilidades generales
# -----------------------------------------------------------

st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

def implied_prob_from_american(odds):
    """Convierte momio americano a probabilidad implícita."""
    if odds is None:
        return None
    try:
        o = float(odds)
    except:
        return None
    if o == 0:
        return None
    if o > 0:
        return 100.0 / (o + 100.0)
    else:
        return -o / (-o + 100.0)


def monte_carlo_spread(total_local, total_visita, spread_casa, n=10000, sigma=13.0):
    """Monte Carlo simple para prob. de que el LOCAL cubra el spread."""
    media_dif = total_local - total_visita
    # simulamos margen real como normal(media_dif, sigma)
    difs = np.random.normal(loc=media_dif, scale=sigma, size=n)
    # spread del casino está en puntos para LOCAL (negativo si es favorito)
    # condición para cubrir: (puntos_local - puntos_visita) + spread_casa > 0
    cubre = difs + spread_casa > 0
    return cubre.mean() * 100.0


def monte_carlo_total(total_modelo, total_casino, n=10000, sigma=15.0, tipo="over"):
    """Monte Carlo para O/U."""
    puntos_totales = np.random.normal(loc=total_modelo, scale=sigma, size=n)
    if tipo == "over":
        prob = (puntos_totales > total_casino).mean()
    else:
        prob = (puntos_totales < total_casino).mean()
    return prob * 100.0


# -----------------------------------------------------------
# 0) Conexión NFL (SportsDataIO)
# -----------------------------------------------------------

def nfl_api_key_input():
    st.markdown("## 0) Conexión NFL (SportsDataIO)")

    # Intentar leer de st.secrets o variable de entorno
    default_key = ""
    try:
        default_key = st.secrets.get("SPORTSDATAIO_NFL_KEY", "")
    except Exception:
        default_key = ""
    if not default_key:
        default_key = os.getenv("SPORTSDATAIO_NFL_KEY", "")

    api_key = st.text_input(
        "SportsDataIO API Key (NFL)",
        value=default_key,
        type="password",
        help="Puedes guardarla en st.secrets['SPORTSDATAIO_NFL_KEY'], "
             "en la variable de entorno SPORTSDATAIO_NFL_KEY, o escribirla aquí.",
    )

    st.session_state["api_key_nfl"] = api_key

    if not api_key:
        st.warning("⚠️ Falta API Key NFL. Los botones de 'Rellenar desde NFL' no podrán llamar a la API.")
    else:
        st.success("✅ API Key NFL lista. Puedes usar 'Rellenar LOCAL/VISITA desde NFL'.")

    return api_key


@st.cache_data(show_spinner=False)
def cargar_stats_nfl(api_key, season):
    """
    Lee estadísticas de equipo por temporada desde SportsDataIO.
    Endpoint típico: TeamSeasonStats.
    Puedes ajustar el endpoint si tu cuenta usa uno distinto.
    """
    if not api_key:
        return None

    url = f"https://api.sportsdata.io/v3/nfl/stats/json/TeamSeasonStats/{season}"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data)

    # Campos típicos: 'Team', 'PointsFor', 'PointsAgainst', 'Games'
    if "Games" in df.columns and (df["Games"] > 0).any():
        df["PF_pg"] = df["PointsFor"] / df["Games"].replace(0, np.nan)
        df["PA_pg"] = df["PointsAgainst"] / df["Games"].replace(0, np.nan)
    else:
        df["PF_pg"] = np.nan
        df["PA_pg"] = np.nan

    return df[["Team", "PF_pg", "PA_pg"]].dropna(subset=["Team"])


def rellenar_desde_nfl(nombre_equipo, df_stats):
    """Devuelve (anota_pg, permite_pg) para el equipo indicado."""
    if df_stats is None or nombre_equipo is None or nombre_equipo == "":
        return 0.0, 0.0
    row = df_stats[df_stats["Team"] == nombre_equipo]
    if row.empty:
        return 0.0, 0.0
    r = row.iloc[0]
    return float(r["PF_pg"]), float(r["PA_pg"])


# -----------------------------------------------------------
# UI: selección de liga
# -----------------------------------------------------------

st.title("Simulador de Apuestas 🏈🏀")

liga = st.radio("Liga", ["NFL", "NBA"], horizontal=True)

st.markdown(
    """
    🔴 Modelo ponderado activo (multi-liga)  
    🟦 = cálculo con promedios GLOBAL  
    🟩 = cálculo con promedios CASA/VISITA (manual)  
    Si llenas casa/visita te muestra ambas proyecciones.
    """
)

# ===========================================================
# MODO NFL
# ===========================================================
if liga == "NFL":
    api_key_nfl = nfl_api_key_input()

    # temporada (texto por si quieres cambiarla fácil)
    col_season1, col_season2 = st.columns([1, 3])
    with col_season1:
        season_nfl = st.text_input("Season NFL (ej. 2025REG)", value="2025REG")

    df_nfl_stats = None
    if api_key_nfl:
        try:
            # En este ejemplo sólo usamos año (2025) para TeamSeasonStats.
            # Si tu season tiene sufijo REG/POST, puedes recortarlo.
            year_str = "".join(ch for ch in season_nfl if ch.isdigit())
            if year_str:
                year_int = int(year_str[:4])
            else:
                year_int = 2025
            df_nfl_stats = cargar_stats_nfl(api_key_nfl, year_int)
            if df_nfl_stats is not None:
                st.success("✅ Datos NFL cargados (TeamSeasonStats).")
        except Exception as e:
            st.warning(f"No se pudieron cargar stats NFL automáticamente: {e}")

    # ---------------- 1) Datos del partido (NFL) ----------------
    st.markdown("### 1) Datos del partido (NFL)")
    col_local, col_visita = st.columns(2)

    equipos_disponibles = df_nfl_stats["Team"].tolist() if df_nfl_stats is not None else []

    with col_local:
        equipo_local = st.selectbox(
            "Equipo LOCAL",
            options=[""] + equipos_disponibles,
            index=0,
            key="equipo_local_nfl",
        )
        if st.button("Rellenar LOCAL desde NFL", disabled=not api_key_nfl):
            pf, pa = rellenar_desde_nfl(equipo_local, df_nfl_stats)
            st.session_state["nfl_local_anota"] = pf
            st.session_state["nfl_local_permite"] = pa
            st.success(f"LOCAL rellenado con datos reales de {equipo_local}.")

        local_anota = st.number_input(
            "Local: puntos que ANOTA (global)",
            value=float(st.session_state.get("nfl_local_anota", 0.0)),
            step=0.1,
        )
        local_permite = st.number_input(
            "Local: puntos que PERMITE (global)",
            value=float(st.session_state.get("nfl_local_permite", 0.0)),
            step=0.1,
        )

    with col_visita:
        equipo_visita = st.selectbox(
            "Equipo VISITA",
            options=[""] + equipos_disponibles,
            index=0,
            key="equipo_visita_nfl",
        )
        if st.button("Rellenar VISITA desde NFL", disabled=not api_key_nfl):
            pf, pa = rellenar_desde_nfl(equipo_visita, df_nfl_stats)
            st.session_state["nfl_visita_anota"] = pf
            st.session_state["nfl_visita_permite"] = pa
            st.success(f"VISITA rellenado con datos reales de {equipo_visita}.")

        visita_anota = st.number_input(
            "Visita: puntos que ANOTA (global)",
            value=float(st.session_state.get("nfl_visita_anota", 0.0)),
            step=0.1,
        )
        visita_permite = st.number_input(
            "Visita: puntos que PERMITE (global)",
            value=float(st.session_state.get("nfl_visita_permite", 0.0)),
            step=0.1,
        )

    # ---------------- 2) Promedios por condición (opcional) ----------------
    st.markdown("### 2) Promedios por condición (opcional)")
    col_local_casa, col_visita_fuera = st.columns(2)
    with col_local_casa:
        local_anota_casa = st.number_input(
            "Local: puntos que ANOTA en casa",
            value=0.0,
            step=0.1,
        )
        local_permite_casa = st.number_input(
            "Local: puntos que PERMITE en casa",
            value=0.0,
            step=0.1,
        )
    with col_visita_fuera:
        visita_anota_fuera = st.number_input(
            "Visita: puntos que ANOTA de visita",
            value=0.0,
            step=0.1,
        )
        visita_permite_fuera = st.number_input(
            "Visita: puntos que PERMITE de visita",
            value=0.0,
            step=0.1,
        )

    # ---------------- 3) Ajuste por lesiones / forma (NFL) ----------------
    st.markdown("### 3) Ajuste por lesiones / QB")

    opciones_estado = {
        "Healthy / completo": 1.00,
        "1-2 bajas importantes": 0.97,
        "Varias bajas (ofensiva tocada)": 0.94,
        "QB titular fuera": 0.88,
        "En gran momento ofensivo": 1.03,
    }

    col_estado_loc, col_estado_vis = st.columns(2)
    with col_estado_loc:
        estado_local = st.selectbox(
            "Estado ofensivo LOCAL (NFL)",
            list(opciones_estado.keys()),
            index=0,
        )
        mult_local = opciones_estado[estado_local]
        st.caption("Estos multiplicadores afectan a los puntos proyectados. 1.00 = normal.")
    with col_estado_vis:
        estado_visita = st.selectbox(
            "Estado ofensivo VISITA (NFL)",
            list(opciones_estado.keys()),
            index=0,
        )
        mult_visita = opciones_estado[estado_visita]

    # ---------------- 4) Proyección del modelo (NFL, GLOBAL) ----------------
    st.markdown("### 4) Proyección del modelo (GLOBAL)")

    # Modelo básico: promedio de ataque local vs defensa visita y viceversa
    puntos_local_base = (local_anota + visita_permite) / 2.0
    puntos_visita_base = (visita_anota + local_permite) / 2.0

    puntos_local_aj = puntos_local_base * mult_local
    puntos_visita_aj = puntos_visita_base * mult_visita

    total_modelo = puntos_local_aj + puntos_visita_aj
    spread_modelo = puntos_local_aj - puntos_visita_aj  # local - visita

    st.write(f"**LOCAL:** {puntos_local_aj:.1f} pts")
    st.write(f"**VISITA:** {puntos_visita_aj:.1f} pts")
    st.write(f"**Total modelo:** {total_modelo:.1f}")
    st.write(f"**Spread modelo (local − visita):** {spread_modelo:+.1f}")

    # ---------------- 5) Línea del casino y diferencias ----------------
    st.markdown("### 5) Línea del casino y diferencias")

    col_spread_casa, col_total_casa = st.columns(2)
    with col_spread_casa:
        spread_casino = st.number_input(
            "Spread del casino (negativo si LOCAL favorito)",
            value=0.0,
            step=0.5,
        )
    with col_total_casa:
        total_casino = st.number_input(
            "Total (O/U) del casino",
            value=0.0,
            step=0.5,
        )

    with st.expander("🔍 Comparación de spreads (GLOBAL)", expanded=True):
        st.write(f"- **Modelo (formato casa)**: LOCAL {spread_modelo:+.1f}")
        st.write(f"- **Casa**: LOCAL {spread_casino:+.1f}")
        dif_spread = spread_modelo - spread_casino
        st.write(f"- **DIF. SPREAD (GLOBAL)**: {dif_spread:+.1f} pts")

    with st.expander("🔍 Comparación de totales (GLOBAL)", expanded=False):
        st.write(f"- **Modelo:** {total_modelo:.1f}")
        st.write(f"- **Casa:** {total_casino:.1f}")
        dif_total = total_modelo - total_casino
        st.write(f"- **DIF. TOTAL (GLOBAL)**: {dif_total:+.1f} pts")

    # Alerta trap line si hay mucha diferencia
    if abs(dif_spread) >= 3 or abs(dif_total) >= 7:
        st.error(
            "⚠️ Línea muy diferente a tu modelo. Puede ser trap line o info que no estás metiendo."
        )

    # ---------------- 5b) Moneyline del sportsbook (opcional) ----------------
    st.markdown("### 5b) Moneyline del sportsbook (opcional)")
    col_ml_loc, col_ml_vis = st.columns(2)
    with col_ml_loc:
        ml_local = st.number_input("Moneyline LOCAL (americano)", value=0.0, step=5.0)
        prob_impl_local = implied_prob_from_american(ml_local)
        st.write(f"Prob. implícita LOCAL (casa): {prob_impl_local*100:.1f}%" if prob_impl_local is not None else "")
    with col_ml_vis:
        ml_visita = st.number_input("Moneyline VISITA (americano)", value=0.0, step=5.0)
        prob_impl_visita = implied_prob_from_american(ml_visita)
        st.write(f"Prob. implícita VISITA (casa): {prob_impl_visita*100:.1f}%" if prob_impl_visita is not None else "")

    # ---------------- 5c) Comparativa de probabilidades (modelo vs casino) ----
    st.markdown("### 5c) Comparativa de probabilidades (modelo vs casino)")
    # Aprox: si spread_modelo es negativo grande, modelo favorito local > 50%.
    # Aquí ponemos un proxy sencillo con distribución normal.
    prob_modelo_local = 50 + spread_modelo * 2  # súper simple
    prob_modelo_local = min(max(prob_modelo_local, 0), 100)
    prob_modelo_visita = 100 - prob_modelo_local

    col_mod, col_casa = st.columns(2)
    with col_mod:
        st.write(f"LOCAL (modelo): **{prob_modelo_local:.1f}%**")
        st.write(f"VISITA (modelo): **{prob_modelo_visita:.1f}%**")
    with col_casa:
        if prob_impl_local is not None:
            st.write(f"Prob. implícita LOCAL (casa): **{prob_impl_local*100:.1f}%**")
        if prob_impl_visita is not None:
            st.write(f"Prob. implícita VISITA (casa): **{prob_impl_visita*100:.1f}%**")

    # ---------------- 6) Simulación Monte Carlo (GLOBAL) ----------------
    st.markdown("### 6) Simulación Monte Carlo 🧊 (GLOBAL)")
    n_sims = st.slider("Número de simulaciones (GLOBAL)", 1000, 30000, 10000, step=1000)

    prob_cubre_local_mc = monte_carlo_spread(
        puntos_local_aj, puntos_visita_aj, spread_casino, n=n_sims
    )
    prob_over_mc = monte_carlo_total(
        total_modelo, total_casino, n=n_sims, sigma=15.0, tipo="over"
    )

    st.write(f"- Prob. de que **LOCAL cubra** (GLOBAL): **{prob_cubre_local_mc:.1f}%**")
    st.write(f"- Prob. de **OVER** (GLOBAL): **{prob_over_mc:.1f}%**")

    # ---------------- 7) Apuestas recomendadas (si ≥ 55%) ----------------
    st.markdown("### 7) Apuestas recomendadas (si ≥ 55%)")

    recomendaciones = []
    if prob_over_mc >= 55:
        recomendaciones.append(
            f"✅ Total GLOBAL: OVER {total_casino:.1f} → {prob_over_mc:.1f}%"
        )
    if prob_cubre_local_mc >= 55:
        recomendaciones.append(
            f"✅ Spread GLOBAL: LOCAL {spread_casino:+.1f} → {prob_cubre_local_mc:.1f}%"
        )

    if not recomendaciones:
        st.info("Ninguna apuesta pasa el umbral del 55%.")
    else:
        for r in recomendaciones:
            st.success(r)

    # ---------------- 8) Edge del modelo vs casa ----------------
    st.markdown("### 8) Edge del modelo vs casa")

    # EDGE SPREAD
    edge_spread_local = spread_modelo - spread_casino  # modelo - casa
    st.write(
        f"- **Edge SPREAD LOCAL (modelo − casa): {edge_spread_local:+.1f} pts**  "
        f"({'la casa está más alta que tu modelo' if edge_spread_local < 0 else 'tu modelo está más alto que la casa'})"
    )

    # EDGE TOTAL
    edge_total = total_modelo - total_casino
    st.write(
        f"- **Edge TOTAL (modelo − casa): {edge_total:+.1f} pts**  "
        f\"({'modelo más bajo que el O/U → sesgo a UNDER' if edge_total < 0 else 'modelo más alto que el O/U → sesgo a OVER'})\"
    )

    st.caption("Pon también los moneylines para evaluar valor en ML, no sólo en spread / total.")


# ===========================================================
# MODO NBA
# (Aquí dejamos la versión avanzada que ya teníamos con últimos 5 + pace + global + edge)
# ===========================================================
else:
    st.markdown("## NBA (modelo avanzado: global + últimos 5 + pace + edge)")

    # --- 1) Datos globales (manual) ---
    st.markdown("### 1) Datos GLOBAL del partido (NBA)")
    col_loc, col_vis = st.columns(2)
    with col_loc:
        equipo_local_nba = st.text_input("Equipo LOCAL (NBA)", value="")
        local_anota_global = st.number_input("LOCAL puntos que ANOTA (global)", 0.0, 200.0, 110.0, 0.1)
        local_permite_global = st.number_input("LOCAL puntos que PERMITE (global)", 0.0, 200.0, 112.0, 0.1)
    with col_vis:
        equipo_visita_nba = st.text_input("Equipo VISITA (NBA)", value="")
        visita_anota_global = st.number_input("VISITA puntos que ANOTA (global)", 0.0, 200.0, 108.0, 0.1)
        visita_permite_global = st.number_input("VISITA puntos que PERMITE (global)", 0.0, 200.0, 114.0, 0.1)

    # --- 2) Últimos 5 + pace ---
    st.markdown("### 2) Últimos 5 partidos + pace (NBA)")

    col_l5_loc, col_l5_vis = st.columns(2)
    with col_l5_loc:
        pace_local_5 = st.number_input("PACE LOCAL (posesiones últimos 5)", 80.0, 115.0, 99.0, 0.1)
        off_local_5 = st.number_input("Ofensiva LOCAL (pts/100 poss últimos 5)", 80.0, 140.0, 115.0, 0.1)
        def_local_5 = st.number_input("Defensiva LOCAL (pts permitidos/100 poss últimos 5)", 80.0, 140.0, 112.0, 0.1)
    with col_l5_vis:
        pace_visita_5 = st.number_input("PACE VISITA (posesiones últimos 5)", 80.0, 115.0, 102.0, 0.1)
        off_visita_5 = st.number_input("Ofensiva VISITA (pts/100 poss últimos 5)", 80.0, 140.0, 108.0, 0.1)
        def_visita_5 = st.number_input("Defensiva VISITA (pts permitidos/100 poss últimos 5)", 80.0, 140.0, 114.0, 0.1)

    pace_prom_liga = st.number_input("Pace promedio liga (NBA)", 80.0, 115.0, 99.0, 0.1)

    # --- 3) Ajuste por lesiones/forma --- 
    st.markdown("### 3) Ajuste por lesiones / forma (NBA)")

    opciones_estado_nba = {
        "Healthy / completo": 1.00,
        "Falta 1 jugador importante": 0.97,
        "Faltan 2+ titulares": 0.94,
        "En racha ofensiva": 1.03,
    }

    col_est_loc, col_est_vis = st.columns(2)
    with col_est_loc:
        estado_loc_nba = st.selectbox("Estado ofensivo LOCAL (NBA)", list(opciones_estado_nba.keys()), index=0)
        mult_loc_nba = opciones_estado_nba[estado_loc_nba]
    with col_est_vis:
        estado_vis_nba = st.selectbox("Estado ofensivo VISITA (NBA)", list(opciones_estado_nba.keys()), index=0)
        mult_vis_nba = opciones_estado_nba[estado_vis_nba]

    st.caption("Estos multiplicadores afectan directamente los puntos esperados y el spread.")

    # --- 4) Proyección del modelo (NBA: global + últimos 5 + pace) ---
    st.markdown("### 4) Proyección del modelo (últ. 5 + pace ajustado + global 65/35)")

    # Pace medio del partido
    pace_medio = (pace_local_5 + pace_visita_5) / 2.0
    pace_factor = pace_medio / pace_prom_liga if pace_prom_liga > 0 else 1.0

    # Puntos por 100 poss usando ofensiva vs defensa rival (últimos 5)
    # luego se pasa a puntos por partido ajustando por pace
    pts_loc_l5 = (0.6 * off_local_5 + 0.4 * def_visita_5) * pace_factor / 100.0
    pts_vis_l5 = (0.6 * off_visita_5 + 0.4 * def_local_5) * pace_factor / 100.0

    # Versión global simple
    pts_loc_global = (local_anota_global + visita_permite_global) / 2.0
    pts_vis_global = (visita_anota_global + local_permite_global) / 2.0

    # Combinación 65% últimos 5, 35% global
    peso_l5 = 0.65
    peso_glob = 0.35

    pts_loc_modelo = (peso_l5 * pts_loc_l5 + peso_glob * pts_loc_global) * mult_loc_nba
    pts_vis_modelo = (peso_l5 * pts_vis_l5 + peso_glob * pts_vis_global) * mult_vis_nba

    total_nba = pts_loc_modelo + pts_vis_modelo
    spread_nba = pts_loc_modelo - pts_vis_modelo  # local - visita

    st.write(f"**{equipo_local_nba or 'LOCAL'}:** {pts_loc_modelo:.1f} pts")
    st.write(f"**{equipo_visita_nba or 'VISITA'}:** {pts_vis_modelo:.1f} pts")
    st.write(f"**Total modelo:** {total_nba:.1f}")
    st.write(f"**Spread modelo (local − visita):** {spread_nba:+.1f}")

    # --- 5) Línea del casino y diferencias ---
    st.markdown("### 5) Línea del casino y diferencias")

    col_sp_cas, col_tot_cas = st.columns(2)
    with col_sp_cas:
        spread_cas_nba = st.number_input("Spread del casino (negativo si LOCAL favorito)", value=-6.5, step=0.5)
    with col_tot_cas:
        total_cas_nba = st.number_input("Total (O/U) del casino", value=229.5, step=0.5)

    with st.expander("🔍 Comparación de spreads (GLOBAL)", expanded=True):
        st.write(f"- Modelo (formato casa): LOCAL {spread_nba:+.1f}")
        st.write(f"- Casa: LOCAL {spread_cas_nba:+.1f}")
        dif_spread_nba = spread_nba - spread_cas_nba
        st.write(f"- **DIF. SPREAD (modelo − casa): {dif_spread_nba:+.1f} pts**")

    with st.expander("🔍 Comparación de totales (GLOBAL)", expanded=False):
        st.write(f"- Modelo: {total_nba:.1f}")
        st.write(f"- Casa: {total_cas_nba:.1f}")
        dif_total_nba = total_nba - total_cas_nba
        st.write(f"- **DIF. TOTAL (modelo − casa): {dif_total_nba:+.1f} pts**")

    # Trap line alert
    if abs(dif_spread_nba) >= 3 or abs(dif_total_nba) >= 7:
        st.error("⚠️ Línea muy diferente a tu modelo. Puede ser trap line o info que no estás metiendo.")

    # --- 5b) Moneyline sportsbook (NBA) ---
    st.markdown("### 5b) Moneyline del sportsbook (opcional)")
    col_ml_loc_nba, col_ml_vis_nba = st.columns(2)
    with col_ml_loc_nba:
        ml_loc_nba = st.number_input("Moneyline LOCAL (americano)", value=-250.0, step=5.0)
        prob_ml_loc_nba = implied_prob_from_american(ml_loc_nba)
        st.write(f"Prob. implícita LOCAL (casa): {prob_ml_loc_nba*100:.1f}%" if prob_ml_loc_nba is not None else "")
    with col_ml_vis_nba:
        ml_vis_nba = st.number_input("Moneyline VISITA (americano)", value=+200.0, step=5.0)
        prob_ml_vis_nba = implied_prob_from_american(ml_vis_nba)
        st.write(f"Prob. implícita VISITA (casa): {prob_ml_vis_nba*100:.1f}%" if prob_ml_vis_nba is not None else "")

    # --- 5c) Probabilidades modelo vs casa ---
    st.markdown("### 5c) Comparativa de probabilidades (modelo vs casino)")
    prob_mod_loc_nba = 50 + spread_nba * 2
    prob_mod_loc_nba = min(max(prob_mod_loc_nba, 0), 100)
    prob_mod_vis_nba = 100 - prob_mod_loc_nba

    col_mod_nba, col_cas_nba = st.columns(2)
    with col_mod_nba:
        st.write(f"{equipo_local_nba or 'LOCAL'} (modelo): **{prob_mod_loc_nba:.1f}%**")
        st.write(f"{equipo_visita_nba or 'VISITA'} (modelo): **{prob_mod_vis_nba:.1f}%**")
    with col_cas_nba:
        if prob_ml_loc_nba is not None:
            st.write(f"Prob. implícita LOCAL (casa): **{prob_ml_loc_nba*100:.1f}%**")
        if prob_ml_vis_nba is not None:
            st.write(f"Prob. implícita VISITA (casa): **{prob_ml_vis_nba*100:.1f}%**")

    # --- 6) Monte Carlo NBA ---
    st.markdown("### 6) Simulación Monte Carlo 🧊 (NBA)")
    n_sims_nba = st.slider("Número de simulaciones (NBA)", 1000, 30000, 10000, step=1000)

    prob_cubre_loc_nba_mc = monte_carlo_spread(
        pts_loc_modelo, pts_vis_modelo, spread_cas_nba, n=n_sims_nba, sigma=13.0
    )
    prob_over_nba_mc = monte_carlo_total(
        total_nba, total_cas_nba, n=n_sims_nba, sigma=15.0, tipo="over"
    )

    st.write(f"- Prob. de que **{equipo_local_nba or 'LOCAL'} cubra**: **{prob_cubre_loc_nba_mc:.1f}%**")
    st.write(f"- Prob. de **OVER**: **{prob_over_nba_mc:.1f}%**")

    # --- 7) Apuestas recomendadas ---
    st.markdown("### 7) Apuestas recomendadas (si ≥ 55%)")
    recs_nba = []
    if prob_over_nba_mc >= 55:
        recs_nba.append(f"✅ UNDER/OVER recomendado según modelo y Monte Carlo (p.ej. UNDER si tu modelo es más bajo). Prob ≈ {prob_over_nba_mc:.1f}% para OVER.")
    if prob_cubre_loc_nba_mc >= 55:
        recs_nba.append(f"✅ Spread {equipo_local_nba or 'LOCAL'} {spread_cas_nba:+.1f} → {prob_cubre_loc_nba_mc:.1f}%")

    if not recs_nba:
        st.info("Ninguna apuesta pasa el umbral del 55%.")
    else:
        for r in recs_nba:
            st.success(r)

    # --- 8) Edge modelo vs casa (NBA) ---
    st.markdown("### 8) Edge del modelo vs casa")

    edge_spread_loc_nba = spread_nba - spread_cas_nba
    edge_spread_vis_nba = -edge_spread_loc_nba

    st.write(
        f"- **Edge SPREAD LOCAL (modelo − casa): {edge_spread_loc_nba:+.1f} pts**  "
        f\"({'casa un poco más alta que tu modelo' if edge_spread_loc_nba < 0 else 'tu modelo un poco más alto que la casa'})\"
    )
    st.write(
        f"- **Edge SPREAD VISITA (modelo − casa): {edge_spread_vis_nba:+.1f} pts**"
    )

    edge_total_nba = total_nba - total_cas_nba
    st.write(
        f"- **Edge TOTAL (modelo − casa): {edge_total_nba:+.1f} pts**  "
        f\"({'modelo más bajo que el O/U → sesgo a UNDER' if edge_total_nba < 0 else 'modelo más alto que el O/U → sesgo a OVER'})\"
