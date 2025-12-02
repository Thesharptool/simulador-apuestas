import streamlit as st
import random
import requests

# =========================================================
# CONFIG GENERAL
# =========================================================
st.set_page_config(page_title="Simulador de Apuestas 🏈🏀🏒", layout="wide")

st.title("Simulador de Apuestas 🏈🏀🏒")
st.markdown("🧠 Modelo ponderado activo (multi-liga)")
st.markdown(
    "🟦 = cálculo con promedios GLOBAL  \n"
    "🟩 = cálculo con promedios CASA/VISITA (solo NFL)  \n"
    "Si llenas casa/visita te muestra las dos proyecciones."
)

liga = st.radio("¿Qué quieres simular?", ["NFL", "NBA", "NHL"], horizontal=True)

# =========================================================
# KEYS, SEASON Y ENDPOINTS
# =========================================================

# 👇 KEYS
API_NBA_SCORES_KEY = "0d1d5d0c77a74544b94b4284cd4b29da"        # <<--- pega aquí tu key nueva de v3 NBA scores
API_NFL_KEY = "cbec1d58513c4c658168cedce52a8a08"   # NFL Odds Season Pass (la que ya usas)

NFL_SEASON_LABEL = "2025REG"
NBA_SEASON_YEAR = "2025"

# NFL Team stats (ODDS)
NFL_TEAMSEASON_URL = "https://api.sportsdata.io/api/nfl/odds/json/TeamSeasonStats/2025REG"

# NFL Odds por semana (ODDS)
NFL_GAMEODDS_WEEK_BASE = "https://api.sportsdata.io/api/nfl/odds/json/GameOddsByWeek"

# NBA Standings (SCORES v3 – NUEVO ENDPOINT)
NBA_STANDINGS_URL = "https://api.sportsdata.io/v3/nba/scores/json/Standings/2025"

# =========================================================
# HELPERS GENERALES
# =========================================================

def normalize_team_code(name: str) -> str:
    """Normaliza el nombre/código de equipo a algo tipo 'DAL', 'NYG', sin espacios."""
    if not name:
        return ""
    return name.strip().upper().replace(" ", "")

# =========================================================
# NFL: CÁLCULO DE PUNTOS POR JUEGO DESDE TeamSeasonStats (ODDS)
# =========================================================

def get_nfl_points_pg_v2(obj: dict):
    """
    Usa los campos que aparecen en TeamSeasonStats (ODDS):

      - Score / PointsFor       -> puntos a favor total
      - OpponentScore / PointsAgainst -> puntos en contra total
      - Wins / Losses / Ties o Games -> número de partidos
    """
    score = obj.get("PointsFor")
    opp_score = obj.get("PointsAgainst")

    if score is None:
        score = obj.get("Score")
    if opp_score is None:
        opp_score = obj.get("OpponentScore")

    total_score = obj.get("TotalScore")
    if score is None and total_score is not None and opp_score is not None:
        score = total_score - opp_score
    if opp_score is None and total_score is not None and score is not None:
        opp_score = total_score - score

    if score is None:
        score = 0.0
    if opp_score is None:
        opp_score = 0.0

    wins = obj.get("Wins") or 0
    losses = obj.get("Losses") or 0
    ties = obj.get("Ties") or 0

    games = obj.get("Games")
    if games is None or games == 0:
        games = wins + losses + ties
    if games == 0:
        games = 1

    pf_pg = score / games
    pa_pg = opp_score / games
    return round(pf_pg, 2), round(pa_pg, 2)

# =========================================================
# CARGA DESDE API NFL (ODDS: TeamSeasonStats)
# =========================================================

@st.cache_data(ttl=600)
def cargar_nfl_desde_api(api_key: str):
    """
    NFL TeamSeasonStats (ODDS, 2025REG).
    Indexa muchos campos de texto como posibles llaves de búsqueda.
    """
    url = f"{NFL_TEAMSEASON_URL}?key={api_key}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}, f"Error {resp.status_code} al conectar con TeamSeasonStats NFL (ODDS)"
        data = resp.json()
    except Exception as e:
        return {}, f"Error de conexión NFL: {e}"

    nfl_teams = {}

    for t in data:
        pf_pg, pa_pg = get_nfl_points_pg_v2(t)
        stats = {
            "pf_pg": pf_pg,
            "pa_pg": pa_pg,
        }

        # cualquier string del objeto será posible llave: 'DAL', 'Dallas', etc.
        for v in t.values():
            if isinstance(v, str):
                s = v.lower()
                keys = {s, s.replace(" ", "")}
                for k in keys:
                    if k:
                        nfl_teams[k] = stats

    return nfl_teams, ""

# =========================================================
# CARGA DESDE API NBA (SCORES v3: Standings)
# =========================================================

@st.cache_data(ttl=600)
def cargar_nba_desde_api(api_key: str):
    """
    NBA Standings (v3 scores, 2025).
    Usa PointsPerGame y OppPointsPerGame / OpponentPointsPerGame.
    """
    url = f"{NBA_STANDINGS_URL}?key={api_key}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}, f"Error {resp.status_code} al conectar con NBA Standings (scores v3)"
        data = resp.json()
    except Exception as e:
        return {}, f"Error de conexión NBA: {e}"

    nba_teams = {}

    for t in data:
        # diferentes versiones usan OppPointsPerGame u OpponentPointsPerGame
        pf = t.get("PointsPerGame", 0.0) or 0.0
        pa = (
            t.get("OppPointsPerGame")
            or t.get("OpponentPointsPerGame")
            or 0.0
        )

        stats = {
            "pf_pg": round(float(pf), 2),
            "pa_pg": round(float(pa), 2),
            "pace": 0.0,  # standings normalmente no traen pace; lo sigues llenando a mano
        }

        for v in t.values():
            if isinstance(v, str):
                s = v.lower()
                keys = {s, s.replace(" ", "")}
                for k in keys:
                    if k:
                        nba_teams[k] = stats

    return nba_teams, ""

# =========================================================
# CARGA DE ODDS POR SEMANA (NFL GameOddsByWeek)
# =========================================================

@st.cache_data(ttl=300)
def cargar_odds_semana_nfl(api_key: str, season_label: str, week: int):
    """
    Llama EXACTAMENTE al endpoint:
    https://api.sportsdata.io/api/nfl/odds/json/GameOddsByWeek/2025REG/13
    """
    url = f"{NFL_GAMEODDS_WEEK_BASE}/{season_label}/{week}?key={api_key}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return [], f"Error {resp.status_code} del endpoint GameOddsByWeek"
        return resp.json(), ""
    except Exception as e:
        return [], f"Error de conexión al traer odds de NFL: {e}"

def traer_odds_partido_nfl(api_key: str, season_label: str, week: int,
                           team_local: str, team_visita: str):
    """
    Busca en GameOddsByWeek/{season}/{week} el partido con esas dos franquicias.
    Devuelve spread (formato LOCAL de la app), total, ML local y ML visita.
    Usa HomePointSpread / AwayPointSpread del endpoint de odds.
    """
    data, err = cargar_odds_semana_nfl(api_key, season_label, week)
    if err:
        return {}, err
    if not data:
        return {}, "No se encontraron juegos para esa semana."

    code_local = normalize_team_code(team_local)
    code_visita = normalize_team_code(team_visita)

    if not code_local or not code_visita:
        return {}, "Escribe LOCAL y VISITA antes de traer los odds."

    cand_local = {code_local, code_local.replace(" ", "")}
    cand_visita = {code_visita, code_visita.replace(" ", "")}

    def norm(s: str) -> str:
        return normalize_team_code(s or "")

    for g in data:
        raw_home = g.get("HomeTeam") or g.get("HomeTeamName") or g.get("HomeTeamKey") or ""
        raw_away = g.get("AwayTeam") or g.get("AwayTeamName") or g.get("AwayTeamKey") or ""

        home_norm = norm(raw_home)
        away_norm = norm(raw_away)

        if not home_norm or not away_norm:
            continue

        juego_tiene_local = any(c and c in {home_norm, away_norm} for c in cand_local)
        juego_tiene_visita = any(c and c in {home_norm, away_norm} for c in cand_visita)

        if not (juego_tiene_local and juego_tiene_visita):
            continue
        if home_norm == away_norm:
            continue

        odds_list = g.get("PregameOdds") or g.get("GameOdds") or []
        if not odds_list:
            return {}, "No encontré bloque PregameOdds para ese juego."

        o = odds_list[0]

        spread_home = o.get("HomePointSpread")
        if spread_home is None:
            spread_home = o.get("PointSpread")

        total = o.get("OverUnder")

        ml_home = o.get("HomeMoneyLine") or o.get("HomeTeamMoneyLine")
        ml_away = o.get("AwayMoneyLine") or o.get("AwayTeamMoneyLine")

        if home_norm in cand_local:
            ml_local = ml_home
            ml_visita = ml_away
            spread_local = spread_home
        else:
            ml_local = ml_away
            ml_visita = ml_home
            spread_local = -spread_home if spread_home is not None else 0.0

        return {
            "spread": float(spread_local or 0.0),
            "total": float(total or 0.0),
            "ml_local": int(ml_local or 0),
            "ml_visita": int(ml_visita or 0),
        }, ""

    return {}, "No encontré ese matchup en los odds de esa semana."

# =========================================================
# CARGA INICIAL SEGÚN LIGA
# =========================================================

nfl_data = {}
nba_data = {}

if liga == "NFL":
    nfl_data, nfl_error = cargar_nfl_desde_api(API_NFL_KEY)
    if nfl_error:
        st.warning(f"⚠️ {nfl_error}")
    else:
        st.success(f"✅ Datos NFL cargados — {len(nfl_data)} registros indexados ({NFL_SEASON_LABEL})")

elif liga == "NBA":
    nba_data, nba_error = cargar_nba_desde_api(API_NBA_SCORES_KEY)
    if nba_error:
        st.warning(f"⚠️ {nba_error}")
    else:
        st.success(f"✅ Datos NBA cargados — {len(nba_data)} registros indexados ({NBA_SEASON_YEAR})")

else:  # NHL
    st.info("🏒 NHL: no hay carga automática, llena los campos manualmente.")

# =========================================================
# 1) DATOS DEL PARTIDO
# =========================================================
st.subheader("1) Datos del partido")
col_l, col_v = st.columns(2)

# ---- LOCAL ----
with col_l:
    local_name = st.text_input("Equipo LOCAL", key="local_name")

    if liga == "NFL":
        if st.button("Rellenar LOCAL desde NFL"):
            lookup_raw = local_name.strip().lower()
            lookup_no_space = lookup_raw.replace(" ", "")
            candidatos = {lookup_raw, lookup_no_space}
            encontrado = False
            for key_try in candidatos:
                if key_try in nfl_data:
                    st.session_state["l_anota_global"] = nfl_data[key_try]["pf_pg"]
                    st.session_state["l_permite_global"] = nfl_data[key_try]["pa_pg"]
                    st.success(f"LOCAL rellenado con datos reales de {local_name}")
                    encontrado = True
                    st.caption(
                        f"PF/PG={nfl_data[key_try]['pf_pg']}  "
                        f"PA/PG={nfl_data[key_try]['pa_pg']}"
                    )
                    break
            if not encontrado:
                st.error("No encontré ese equipo en NFL")

    if liga == "NBA":
        if st.button("Rellenar LOCAL desde NBA"):
            lookup_raw = local_name.strip().lower()
            lookup_no_space = lookup_raw.replace(" ", "")
            candidatos = {lookup_raw, lookup_no_space}
            encontrado = False
            for key_try in candidatos:
                if key_try in nba_data:
                    st.session_state["l_anota_global"] = nba_data[key_try]["pf_pg"]
                    st.session_state["l_permite_global"] = nba_data[key_try]["pa_pg"]
                    st.success(f"LOCAL rellenado con datos reales de {local_name}")
                    encontrado = True
                    st.caption(
                        f"PF/PG={nba_data[key_try]['pf_pg']}  "
                        f"PA/PG={nba_data[key_try]['pa_pg']}"
                    )
                    break
            if not encontrado:
                st.error("No encontré ese equipo en NBA")

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

# ---- VISITA ----
with col_v:
    visita_name = st.text_input("Equipo VISITA", key="visita_name")

    if liga == "NFL":
        if st.button("Rellenar VISITA desde NFL"):
            lookup_raw = visita_name.strip().lower()
            lookup_no_space = lookup_raw.replace(" ", "")
            candidatos = {lookup_raw, lookup_no_space}
            encontrado = False
            for key_try in candidatos:
                if key_try in nfl_data:
                    st.session_state["v_anota_global"] = nfl_data[key_try]["pf_pg"]
                    st.session_state["v_permite_global"] = nfl_data[key_try]["pa_pg"]
                    st.success(f"VISITA rellenado con datos reales de {visita_name}")
                    encontrado = True
                    st.caption(
                        f"PF/PG={nfl_data[key_try]['pf_pg']}  "
                        f"PA/PG={nfl_data[key_try]['pa_pg']}"
                    )
                    break
            if not encontrado:
                st.error("No encontré ese equipo en NFL")

    if liga == "NBA":
        if st.button("Rellenar VISITA desde NBA"):
            lookup_raw = visita_name.strip().lower()
            lookup_no_space = lookup_raw.replace(" ", "")
            candidatos = {lookup_raw, lookup_no_space}
            encontrado = False
            for key_try in candidatos:
                if key_try in nba_data:
                    st.session_state["v_anota_global"] = nba_data[key_try]["pf_pg"]
                    st.session_state["v_permite_global"] = nba_data[key_try]["pa_pg"]
                    st.success(f"VISITA rellenado con datos reales de {visita_name}")
                    encontrado = True
                    st.caption(
                        f"PF/PG={nba_data[key_try]['pf_pg']}  "
                        f"PA/PG={nba_data[key_try]['pa_pg']}"
                    )
                    break
            if not encontrado:
                st.error("No encontré ese equipo en NBA")

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
# 2) SEGÚN LIGA
# =========================================================
if liga == "NFL":
    st.subheader("2) Promedios por condición (opcional)")
    c1, c2 = st.columns(2)
    with c1:
        l_anota_casa = st.number_input(
            "Local: puntos que ANOTA en casa", value=0.0, step=0.1
        )
        l_permite_casa = st.number_input(
            "Local: puntos que PERMITE en casa", value=0.0, step=0.1
        )
    with c2:
        v_anota_visita = st.number_input(
            "Visita: puntos que ANOTA de visita", value=0.0, step=0.1
        )
        v_permite_visita = st.number_input(
            "Visita: puntos que PERMITE de visita", value=0.0, step=0.1
        )

    hay_cv = any([l_anota_casa, l_permite_casa, v_anota_visita, v_permite_visita])

elif liga == "NBA":
    st.subheader("2) Factores avanzados NBA (últimos 5 partidos) 🏀")
    st.caption(
        "Llena estos datos para que el total de NBA se acerque más a las líneas reales. "
        "Por ahora, estos se llenan manualmente."
    )
    nb1, nb2 = st.columns(2)

    with nb1:
        pace_local_5 = st.number_input(
            "PACE LOCAL (posesiones últimos 5)", value=0.0, step=0.1
        )
        off_local_5 = st.number_input(
            "Ofensiva LOCAL (pts/100 poss últimos 5)", value=0.0, step=0.1
        )
        def_local_5 = st.number_input(
            "Defensiva LOCAL (pts permitidos/100 poss últimos 5)",
            value=0.0,
            step=0.1,
        )
    with nb2:
        pace_visita_5 = st.number_input(
            "PACE VISITA (posesiones últimos 5)", value=0.0, step=0.1
        )
        off_visita_5 = st.number_input(
            "Ofensiva VISITA (pts/100 poss últimos 5)", value=0.0, step=0.1
        )
        def_visita_5 = st.number_input(
            "Defensiva VISITA (pts permitidos/100 poss últimos 5)",
            value=0.0,
            step=0.1,
        )

    pace_liga = st.number_input("Pace promedio liga (NBA)", value=99.0, step=0.1)
    hay_cv = False

else:  # NHL
    st.subheader("2) Factores avanzados NHL (últimos 5 + xG + goalie) 🎯")
    st.caption("Usa GF/GA, xG, Corsi% y Save% para acercarte a las líneas reales.")
    nhl1, nhl2 = st.columns(2)

    with nhl1:
        gf_local_5 = st.number_input("GF LOCAL (goles a favor últimos 5)", value=0.0, step=0.1)
        ga_local_5 = st.number_input("GA LOCAL (goles en contra últimos 5)", value=0.0, step=0.1)
        xgf_local_5 = st.number_input("xGF LOCAL (goles esperados a favor últimos 5)", value=0.0, step=0.1)
        xga_local_5 = st.number_input("xGA LOCAL (goles esperados en contra últimos 5)", value=0.0, step=0.1)
        corsi_local_5 = st.number_input("Corsi% LOCAL (últimos 5)", value=50.0, step=0.1)
        sv_goalie_local_5 = st.number_input("Save% GOALIE LOCAL (últimos 5)", value=0.910, step=0.001)

    with nhl2:
        gf_visita_5 = st.number_input("GF VISITA (goles a favor últimos 5)", value=0.0, step=0.1)
        ga_visita_5 = st.number_input("GA VISITA (goles en contra últimos 5)", value=0.0, step=0.1)
        xgf_visita_5 = st.number_input("xGF VISITA (goles esperados a favor últimos 5)", value=0.0, step=0.1)
        xga_visita_5 = st.number_input("xGA VISITA (goles esperados en contra últimos 5)", value=0.0, step=0.1)
        corsi_visita_5 = st.number_input("Corsi% VISITA (últimos 5)", value=50.0, step=0.1)
        sv_goalie_visita_5 = st.number_input("Save% GOALIE VISITA (últimos 5)", value=0.910, step=0.001)

    goles_liga = st.number_input("Promedio goles totales liga (NHL)", value=6.20, step=0.1)
    hay_cv = False

# =========================================================
# 3) AJUSTE POR LESIONES / FORMA
# =========================================================
st.subheader("3) Ajuste por lesiones / forma")

opt_estado = {
    "Healthy / completo": 1.00,
    "1 baja importante": 0.97,
    "Varias bajas / tocado": 0.93,
    "En buen momento": 1.03,
}

c3, c4 = st.columns(2)
with c3:
    estado_local = st.selectbox(
        f"Estado ofensivo LOCAL ({liga})",
        list(opt_estado.keys()),
        index=0,
        key="estado_local",
    )
with c4:
    estado_visita = st.selectbox(
        f"Estado ofensivo VISITA ({liga})",
        list(opt_estado.keys()),
        index=0,
        key="estado_visita",
    )

mult_local = opt_estado[estado_local]
mult_visita = opt_estado[estado_visita]
st.caption("Estos multiplicadores afectan a los puntos proyectados. 1.00 = normal.")

# =========================================================
# FUNCIÓN DE PROYECCIÓN NFL
# =========================================================
def proyeccion_nfl(ofensiva, defensa, es_local=False):
    base = 0.55 * ofensiva + 0.35 * defensa
    if es_local:
        base += 1.5
    return base

# =========================================================
# 4) PROYECCIÓN DEL MODELO
# =========================================================
st.subheader("4) Proyección del modelo")

if liga == "NFL":
    pts_local_global = proyeccion_nfl(l_anota_global, v_permite_global, True) * mult_local
    pts_visita_global = proyeccion_nfl(v_anota_global, l_permite_global, False) * mult_visita
    total_global = pts_local_global + pts_visita_global
    spread_global = pts_local_global - pts_visita_global
    line_modelo = -spread_global

    st.markdown("🟦 **GLOBAL**")
    st.write(f"- {local_name or 'LOCAL'}: **{pts_local_global:.1f} pts**")
    st.write(f"- {visita_name or 'VISITA'}: **{pts_visita_global:.1f} pts**")
    st.write(f"- Total modelo: **{total_global:.1f}**")
    st.write(
        f"- Spread modelo (local – visita): **{spread_global:+.1f} pts** "
        f"→ línea modelo LOCAL **{line_modelo:+.1f}**"
    )

    if hay_cv:
        st.markdown("🟩 **CASA / VISITA**")
        pts_local_cv = proyeccion_nfl(l_anota_casa, v_permite_visita, True) * mult_local
        pts_visita_cv = proyeccion_nfl(v_anota_visita, l_permite_casa, False) * mult_visita
        total_cv = pts_local_cv + pts_visita_cv
        spread_cv = pts_local_cv - pts_visita_cv

        st.write(f"- {local_name or 'LOCAL'}: **{pts_local_cv:.1f} pts**")
        st.write(f"- {visita_name or 'VISITA'}: **{pts_visita_cv:.1f} pts**")
        st.write(f"- Total modelo (c/v): **{total_cv:.1f}**")
        st.write(f"- Spread modelo (c/v): **{spread_cv:+.1f}**")
    else:
        total_cv = None
        spread_cv = None

elif liga == "NBA":
    if 'pace_local_5' in locals() and pace_local_5 > 0 and pace_visita_5 > 0:
        pace_med = (pace_local_5 + pace_visita_5) / 2
    else:
        pace_med = pace_liga

    reciente_local = (0.6 * off_local_5 + 0.4 * def_visita_5) * (pace_med / 100.0)
    reciente_visita = (0.6 * off_visita_5 + 0.4 * def_local_5) * (pace_med / 100.0)

    global_local_part = 0.0
    global_visita_part = 0.0
    if l_anota_global or v_permite_global:
        global_local_part = (l_anota_global + v_permite_global) / 2.0
    if v_anota_global or l_permite_global:
        global_visita_part = (v_anota_global + l_permite_global) / 2.0

    pts_local_global = (0.65 * reciente_local + 0.35 * global_local_part) * mult_local
    pts_visita_global = (0.65 * reciente_visita + 0.35 * global_visita_part) * mult_visita

    total_global = pts_local_global + pts_visita_global
    spread_global = pts_local_global - pts_visita_global
    line_modelo = -spread_global

    st.markdown("🏀 usando últimos 5 + pace + global (65% / 35%)")
    st.write(f"- {local_name or 'LOCAL'}: **{pts_local_global:.1f} pts**")
    st.write(f"- {visita_name or 'VISITA'}: **{pts_visita_global:.1f} pts**")
    st.write(f"- Total modelo: **{total_global:.1f}**")
    st.write(
        f"- Spread modelo (local – visita): **{spread_global:+.1f} pts** "
        f"→ línea modelo LOCAL **{line_modelo:+.1f}**"
    )

    total_cv = None
    spread_cv = None

else:  # NHL
    base_team = goles_liga / 2.0

    atk_local = 0.5 * gf_local_5 + 0.3 * xgf_local_5 + 0.2 * (corsi_local_5 - 50) / 5
    def_visita = 0.5 * ga_visita_5 + 0.3 * xga_visita_5 - 0.2 * (sv_goalie_visita_5 - 0.910) * 10

    atk_visita = 0.5 * gf_visita_5 + 0.3 * xgf_visita_5 + 0.2 * (corsi_visita_5 - 50) / 5
    def_local = 0.5 * ga_local_5 + 0.3 * xga_local_5 - 0.2 * (sv_goalie_local_5 - 0.910) * 10

    exp_local = base_team + 0.5 * (atk_local - base_team) - 0.5 * (def_visita - base_team)
    exp_visita = base_team + 0.5 * (atk_visita - base_team) - 0.5 * (def_local - base_team)

    pts_local_global = max(0.5, exp_local) * mult_local
    pts_visita_global = max(0.5, exp_visita) * mult_visita

    total_global = pts_local_global + pts_visita_global
    spread_global = pts_local_global - pts_visita_global
    line_modelo = -spread_global

    st.markdown("🏒 usando GF/GA + xG + Corsi% + Save% (NHL)")
    st.write(f"- {local_name or 'LOCAL'}: **{pts_local_global:.2f} goles**")
    st.write(f"- {visita_name or 'VISITA'}: **{pts_visita_global:.2f} goles**")
    st.write(f"- Total modelo: **{total_global:.2f} goles**")
    st.write(
        f"- Spread modelo (local – visita): **{spread_global:+.2f}** "
        f"→ línea modelo LOCAL **{line_modelo:+.2f}**"
    )

    total_cv = None
    spread_cv = None

# =========================================================
# 5) LÍNEA DEL CASINO Y DIFERENCIAS
# =========================================================
st.subheader("5) Línea del casino y diferencias")

if liga == "NFL":
    st.markdown("#### Automatizar odds NFL desde SportsDataIO")
    semana_nfl = st.number_input(
        "Semana NFL (para GameOddsByWeek)",
        min_value=1, max_value=25, value=13, step=1
    )
    if st.button("Traer odds NFL desde SportsDataIO"):
        odds, err = traer_odds_partido_nfl(
            API_NFL_KEY,
            NFL_SEASON_LABEL,
            int(semana_nfl),
            local_name,
            visita_name,
        )
        if err:
            st.warning(f"⚠️ {err}")
        else:
            st.session_state["spread_casa"] = odds["spread"]
            st.session_state["total_casa"] = odds["total"]
            st.session_state["ml_local"] = odds["ml_local"]
            st.session_state["ml_visita"] = odds["ml_visita"]
            st.success(
                f"Odds cargados: spread={odds['spread']:+.1f}, total={odds['total']:.1f}, "
                f"ML local={odds['ml_local']}, ML visita={odds['ml_visita']}"
            )

col_spread, col_total = st.columns(2)
with col_spread:
    spread_casa = st.number_input(
        "Spread del casino (negativo si LOCAL favorito)",
        value=float(st.session_state.get("spread_casa", 0.0)),
        step=0.5,
    )
with col_total:
    total_casa = st.number_input(
        "Total (O/U) del casino",
        value=float(st.session_state.get("total_casa", 0.0)),
        step=0.5,
    )

with st.expander("🔍 Comparación de spreads (GLOBAL)", expanded=True):
    st.write(f"- Modelo (formato casa): **LOCAL {line_modelo:+.1f}**")
    st.write(f"- Casa: **LOCAL {spread_casa:+.1f}**")
    dif_spread = spread_casa - line_modelo
    st.write(f"- **DIF. SPREAD (GLOBAL): {dif_spread:+.1f} pts**")

with st.expander("🔍 Comparación de totales (GLOBAL)", expanded=True):
    st.write(f"- Modelo: **{total_global:.1f}**")
    st.write(f"- Casa: **{total_casa:.1f}**")
    dif_total = total_global - total_casa
    st.write(f"- **DIF. TOTAL (GLOBAL): {dif_total:+.1f} pts**")

trap_msgs = []
if abs(dif_spread) >= 5:
    trap_msgs.append("spread")
if abs(dif_total) >= 8:
    trap_msgs.append("total")

if trap_msgs:
    st.error(
        f"⚠️ Línea muy diferente a tu modelo ({', '.join(trap_msgs)}). "
        f"Puede ser trap line o info que no estás metiendo."
    )

# =========================================================
# 5b) MONEYLINE
# =========================================================
st.subheader("5b) Moneyline del sportsbook (opcional)")
c_ml1, c_ml2 = st.columns(2)
with c_ml1:
    ml_local = st.number_input(
        "Moneyline LOCAL (americano)",
        value=int(st.session_state.get("ml_local", 0)),
        step=5,
    )
with c_ml2:
    ml_visita = st.number_input(
        "Moneyline VISITA (americano)",
        value=int(st.session_state.get("ml_visita", 0)),
        step=5,
    )

def implied_from_ml(ml):
    if ml == 0:
        return 0.0
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return -ml / (-ml + 100)

prob_impl_local = implied_from_ml(ml_local) * 100
prob_impl_visita = implied_from_ml(ml_visita) * 100

st.write(
    f"Prob. implícita LOCAL (casa): **{prob_impl_local:.1f}%**, "
    f"Prob. implícita VISITA (casa): **{prob_impl_visita:.1f}%**"
)

# =========================================================
# 5c) Comparativa de probabilidades (modelo vs casino)
# =========================================================
st.subheader("5c) Comparativa de probabilidades (modelo vs casino)")
p_local_modelo = 50 + (spread_global * 2)
p_local_modelo = max(1, min(99, p_local_modelo))
p_visita_modelo = 100 - p_local_modelo

st.write(f"{local_name or 'LOCAL'} (modelo): **{p_local_modelo:.1f}%**")
st.write(f"{visita_name or 'VISITA'} (modelo): **{p_visita_modelo:.1f}%**")
st.write(f"Prob. implícita LOCAL (casa): **{prob_impl_local:.1f}%**")
st.write(f"Prob. implícita VISITA (casa): **{prob_impl_visita:.1f}%**")

# =========================================================
# 6) MONTE CARLO
# =========================================================
st.subheader("6) Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)

covers, overs = 0, 0
if liga == "NBA":
    desv = 12.0
elif liga == "NFL":
    desv = 13.0
else:  # NHL
    desv = 1.2

for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local_global, desv))
    sim_v = max(0, random.gauss(pts_visita_global, desv))
    if (sim_l - sim_v) + spread_casa >= 0:
        covers += 1
    if (sim_l + sim_v) > total_casa:
        overs += 1

prob_cover = covers / num_sims * 100
prob_over = overs / num_sims * 100

st.write(f"Prob. de que {local_name or 'LOCAL'} cubra (GLOBAL): **{prob_cover:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{prob_over:.1f}%**")

# =========================================================
# 7) Apuestas recomendadas (si ≥ 55%)
# =========================================================
st.subheader("7) Apuestas recomendadas (si ≥ 55%)")

umbral = 55.0
recs = []

prob_cover_local = prob_cover
prob_cover_visita = 100.0 - prob_cover

if prob_cover_local >= umbral:
    recs.append(
        f"🟢 Spread GLOBAL: {local_name or 'LOCAL'} {spread_casa:+.1f} → {prob_cover_local:.1f}%"
    )

if prob_cover_visita >= umbral:
    spread_visita_line = -spread_casa
    recs.append(
        f"🟢 Spread GLOBAL: {visita_name or 'VISITA'} {spread_visita_line:+.1f} → {prob_cover_visita:.1f}%"
    )

prob_over_val = prob_over
prob_under_val = 100.0 - prob_over_val

if prob_over_val >= umbral:
    recs.append(
        f"🟢 Total GLOBAL: OVER {total_casa:.1f} → {prob_over_val:.1f}%"
    )
elif prob_under_val >= umbral:
    recs.append(
        f"🟢 Total GLOBAL: UNDER {total_casa:.1f} → {prob_under_val:.1f}%"
    )

if recs:
    for r in recs:
        st.success(r)
else:
    st.info("Por ahora ninguna llega al 55%.")

# =========================================================
# 8) Edge del modelo vs casa
# =========================================================
st.subheader("8) Edge del modelo vs casa")

st.write(f"Línea MODELO (LOCAL): **{line_modelo:+.1f}**")
st.write(f"Línea CASA   (LOCAL): **{spread_casa:+.1f}**")

edge_local_pts = spread_casa - line_modelo
edge_visita_pts = -edge_local_pts

if edge_local_pts > 0:
    st.success(
        f"Edge SPREAD LOCAL: **+{edge_local_pts:.1f} pts** "
        f"(la línea de la casa es {edge_local_pts:.1f} pts más suave que tu modelo → valor en el LOCAL)"
    )
else:
    st.error(
        f"Edge SPREAD LOCAL: **{edge_local_pts:.1f} pts** "
        f"(la casa es más agresiva con el LOCAL → más valor en la VISITA)"
    )

if edge_visita_pts > 0:
    st.success(
        f"Edge SPREAD VISITA: **+{edge_visita_pts:.1f} pts** "
        f"(tu modelo ve {edge_visita_pts:.1f} pts de valor en la VISITA)"
    )
else:
    st.error(
        f"Edge SPREAD VISITA: **{edge_visita_pts:.1f} pts** "
        f"(hay poco o ningún valor en la VISITA según tu modelo)"
    )

st.caption("Pon los moneylines para calcular el edge de forma más fina.")
