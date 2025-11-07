import streamlit as st
import random
import requests

# =========================================
# CONFIGURACIÓN
# =========================================
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 **Modelo ponderado activo (v2)**")
st.markdown(
    """
🟦 = cálculo con promedios **GLOBAL**  
🟩 = cálculo con promedios **CASA/VISITA**  
Si llenas casa/visita te muestra las dos proyecciones.
"""
)

# =========================================
# 0. SESIÓN / ESTADO INICIAL
# =========================================
defaults = {
    "local_name": "",
    "visita_name": "",
    "l_anota_global": 0.0,
    "l_permite_global": 0.0,
    "v_anota_global": 0.0,
    "v_permite_global": 0.0,
    "l_anota_casa": 0.0,
    "l_permite_casa": 0.0,
    "v_anota_visita": 0.0,
    "v_permite_visita": 0.0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================================
# 1. CARGAR DATOS DE NFL DESDE SPORTSDATA.IO
# =========================================
API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"  # ✅ llave activa
SEASON = "2025REG"

equipos_por_nombre = {}
equipos_por_key = {}
api_ok = False

if API_KEY:
    st.info(f"🔵 Conectando con SportsDataIO ➜ {SEASON}")
    url = f"https://api.sportsdata.io/v3/nfl/scores/json/Standings/{SEASON}"
    headers = {"Ocp-Apim-Subscription-Key": API_KEY}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for team in data:
                nombre = (team.get("Name") or "").lower()
                abre = (team.get("Team") or team.get("Key") or "").lower()
                if nombre:
                    equipos_por_nombre[nombre] = team
                if abre:
                    equipos_por_key[abre] = team
            api_ok = True
            st.success(f"🟩 Datos NFL cargados. {len(data)} equipos ({SEASON})")
        else:
            st.warning("⚠️ No pude traer datos de NFL: respuesta no 200.")
    except Exception as e:
        st.warning(f"⚠️ No pude traer datos de NFL: {e}")
else:
    st.warning("⚠️ No hay API key configurada.")


# =========================================
# 2. DATOS DEL PARTIDO
# =========================================
st.subheader("Datos del partido")

col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", st.session_state["local_name"], key="local_name")
    btn_local = st.button("Rellenar LOCAL desde NFL")

with col2:
    visita = st.text_input("Equipo VISITA", st.session_state["visita_name"], key="visita_name")
    btn_visita = st.button("Rellenar VISITA desde NFL")


# =========================================
# 2.a RELLENAR LOCAL DESDE NFL
# =========================================
if btn_local and api_ok and local:
    nombre = local.lower().strip()
    team = equipos_por_nombre.get(nombre) or equipos_por_key.get(nombre)
    if team:
        games = team.get("Games", 17) or 17
        anota = (team.get("PointsFor", 0) or 0) / games
        permite = (team.get("PointsAgainst", 0) or 0) / games

        st.session_state.update({
            "l_anota_global": round(anota, 2),
            "l_permite_global": round(permite, 2),
            "local_name": local
        })

        st.success(f"LOCAL rellenado con datos reales de {team.get('Name', 'equipo')}")
        st.experimental_rerun()
    else:
        st.error("No encontré ese equipo en la NFL. Prueba con 'den', 'dal', 'kc', etc.")

# =========================================
# 2.b RELLENAR VISITA DESDE NFL
# =========================================
if btn_visita and api_ok and visita:
    nombre = visita.lower().strip()
    team = equipos_por_nombre.get(nombre) or equipos_por_key.get(nombre)
    if team:
        games = team.get("Games", 17) or 17
        anota = (team.get("PointsFor", 0) or 0) / games
        permite = (team.get("PointsAgainst", 0) or 0) / games

        st.session_state.update({
            "v_anota_global": round(anota, 2),
            "v_permite_global": round(permite, 2),
            "visita_name": visita
        })

        st.success(f"VISITA rellenado con datos reales de {team.get('Name', 'equipo')}")
        st.experimental_rerun()
    else:
        st.error("No encontré ese equipo en la NFL.")


# =========================================
# 3. PROMEDIOS GLOBAL
# =========================================
colg1, colg2 = st.columns(2)
with colg1:
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

with colg2:
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


# =========================================
# 4. CASA / VISITA OPCIONAL
# =========================================
st.subheader("Promedios por condición (opcional)")
cv1, cv2 = st.columns(2)
with cv1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", 0.0, step=0.1)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", 0.0, step=0.1)
with cv2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", 0.0, step=0.1)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", 0.0, step=0.1)

hay_cv = any([l_anota_casa > 0, l_permite_casa > 0, v_anota_visita > 0, v_permite_visita > 0])

# =========================================
# 5. AJUSTE POR LESIONES / QB
# =========================================
st.subheader("Ajuste por lesiones / QB")
aj1, aj2 = st.columns(2)
with aj1:
    af_local = st.checkbox("¿Afecta ofensiva LOCAL?", value=False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
with aj2:
    af_visita = st.checkbox("¿Afecta ofensiva VISITA?", value=False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# =========================================
# 6. FUNCIÓN DEL MODELO
# =========================================
def proyeccion_suavizada(ofensiva_propia, defensa_rival, es_local=False):
    base = 0.55 * ofensiva_propia + 0.35 * defensa_rival
    if es_local:
        base += 1.5
    return base

# =========================================
# 7. PROYECCIÓN GLOBAL
# =========================================
st.subheader("🟦 Proyección del modelo (GLOBAL)")
pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, True) * mult_local
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, False) * mult_visita
total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.write(f"Puntos esperados {local or 'LOCAL'}: **{pts_local_global:.1f}**")
st.write(f"Puntos esperados {visita or 'VISITA'}: **{pts_visita_global:.1f}**")
st.write(f"Total GLOBAL: **{total_global:.1f}** — Spread: **{spread_global:+.1f}**")

# =========================================
# 8. SIMULACIÓN MONTE CARLO
# =========================================
st.subheader("Simulación Monte Carlo 🧮")
num_sims = st.slider("Número de simulaciones", 1000, 50000, 10000, 1000)
desv = max(5, total_global * 0.15)

covers, overs = 0, 0
spread_casa = st.number_input("Spread de la casa (negativo si LOCAL es favorito)", -50.0, 50.0, 0.0, 0.5)
total_casa = st.number_input("Total (O/U) de la casa", 0.0, 300.0, 0.0, 0.5)

for _ in range(num_sims):
    sim_local = max(0, random.gauss(pts_local_global, desv))
    sim_visita = max(0, random.gauss(pts_visita_global, desv))
    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1
    if (sim_local + sim_visita) > total_casa:
        overs += 1

prob_cover = covers / num_sims * 100
prob_over = overs / num_sims * 100
st.write(f"Prob. de cubrir spread: **{prob_cover:.1f}%**")
st.write(f"Prob. de OVER: **{prob_over:.1f}%**")
