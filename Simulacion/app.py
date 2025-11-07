import streamlit as st
import random
import requests

# ------------------------------------------------
# CONFIG
# ------------------------------------------------
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("🧠 Modelo ponderado activo (v2)")
st.markdown("""
🟦 = cálculo con promedios GLOBAL  
🟩 = cálculo con promedios CASA/VISITA  
Si llenas casa/visita te muestra las dos proyecciones.
""")

# ------------------------------------------------
# 0. CONEXIÓN A SPORTSDATA.IO (NFL)
# ------------------------------------------------
API_KEY = "9a0c57c7cd90446f9b836247b5cf5c34"
NFL_URLS = [
    "https://api.sportsdata.io/v3/nfl/scores/json/Standings/2025REG",
    "https://api.sportsdata.io/v3/nfl/scores/json/Standings/2024REG"
]

@st.cache_data(ttl=3600)
def cargar_equipos_nfl():
    headers = {"Ocp-Apim-Subscription-Key": API_KEY}
    for url in NFL_URLS:
        try:
            st.info(f"📡 Conectando con SportsDataIO → {url.split('/')[-1]}", icon="⚙️")
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, list):
                st.warning(f"⚠️ Respuesta inesperada de {url}: {data}")
                continue

            por_nombre, por_key = {}, {}
            for t in data:
                nombre = t.get("Name", "").lower()
                key = t.get("Key", "").lower()
                por_nombre[nombre] = t
                por_key[key] = t

            st.success(f"✅ Datos NFL cargados: {len(por_key)} equipos ({url.split('/')[-1]})")
            return por_nombre, por_key
        except requests.exceptions.HTTPError as e:
            st.warning(f"❌ Error HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            st.warning(f"No pude traer datos desde {url} → {e}")

    st.error("No se pudieron cargar standings de NFL (verifica tu API key o plan).")
    return {}, {}

equipos_por_nombre, equipos_por_key = cargar_equipos_nfl()

# ------------------------------------------------
# 1. DATOS DE ENTRADA (en blanco)
# ------------------------------------------------
st.subheader("Datos del partido")

col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "")
    auto_local = st.button("Rellenar LOCAL desde NFL")
    st.markdown("**Promedios GLOBAL del LOCAL**")

    if "l_anota_global" not in st.session_state:
        st.session_state.l_anota_global = 0.0
    if "l_permite_global" not in st.session_state:
        st.session_state.l_permite_global = 0.0

    if auto_local and local:
        nombre_buscar = local.lower().strip()
        team = equipos_por_nombre.get(nombre_buscar) or equipos_por_key.get(nombre_buscar)
        if team:
            games = team.get("Games", 17) or 17
            st.session_state.l_anota_global = team.get("PointsFor", 0) / games
            st.session_state.l_permite_global = team.get("PointsAgainst", 0) / games
            st.success(f"LOCAL rellenado con datos reales de {team['Name']}")
        else:
            st.error("No encontré ese equipo en la NFL. Prueba con abreviaciones (ej. DAL, SF, KC).")

    l_anota_global = st.number_input(
        "Local: puntos que ANOTA (global)",
        value=st.session_state.l_anota_global,
        step=0.1,
        key="input_l_anota"
    )
    l_permite_global = st.number_input(
        "Local: puntos que PERMITE (global)",
        value=st.session_state.l_permite_global,
        step=0.1,
        key="input_l_permite"
    )

with col2:
    visita = st.text_input("Equipo VISITA", "")
    auto_visita = st.button("Rellenar VISITA desde NFL")
    st.markdown("**Promedios GLOBAL del VISITA**")

    if "v_anota_global" not in st.session_state:
        st.session_state.v_anota_global = 0.0
    if "v_permite_global" not in st.session_state:
        st.session_state.v_permite_global = 0.0

    if auto_visita and visita:
        nombre_buscar = visita.lower().strip()
        team = equipos_por_nombre.get(nombre_buscar) or equipos_por_key.get(nombre_buscar)
        if team:
            games = team.get("Games", 17) or 17
            st.session_state.v_anota_global = team.get("PointsFor", 0) / games
            st.session_state.v_permite_global = team.get("PointsAgainst", 0) / games
            st.success(f"VISITA rellenado con datos reales de {team['Name']}")
        else:
            st.error("No encontré ese equipo en la NFL. Prueba con abreviaciones (ej. DAL, SF, KC).")

    v_anota_global = st.number_input(
        "Visita: puntos que ANOTA (global)",
        value=st.session_state.v_anota_global,
        step=0.1,
        key="input_v_anota"
    )
    v_permite_global = st.number_input(
        "Visita: puntos que PERMITE (global)",
        value=st.session_state.v_permite_global,
        step=0.1,
        key="input_v_permite"
    )

# ------------------------------------------------
# 2. OPCIONAL: CASA / VISITA
# ------------------------------------------------
st.subheader("Promedios por condición (opcional)")

c1, c2 = st.columns(2)
with c1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", value=0.0, step=0.1)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", value=0.0, step=0.1)
with c2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", value=0.0, step=0.1)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", value=0.0, step=0.1)

hay_cv = any([
    l_anota_casa > 0,
    l_permite_casa > 0,
    v_anota_visita > 0,
    v_permite_visita > 0
])

# ------------------------------------------------
# 3. AJUSTE POR LESIONES / QB
# ------------------------------------------------
st.subheader("Ajuste por lesiones / QB")
c3, c4 = st.columns(2)
with c3:
    af_local = st.checkbox("¿Afecta ofensiva LOCAL?", value=False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
with c4:
    af_visita = st.checkbox("¿Afecta ofensiva VISITA?", value=False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)

if not af_local:
    mult_local = 1.0
if not af_visita:
    mult_visita = 1.0

# ------------------------------------------------
# 4. FUNCIÓN DEL MODELO
# ------------------------------------------------
def proyeccion_suavizada(ofensiva_propia, defensa_rival, es_local=False):
    base = 0.55 * ofensiva_propia + 0.35 * defensa_rival
    if es_local:
        base += 1.5
    return base

# ------------------------------------------------
# 5. PROYECCIÓN GLOBAL
# ------------------------------------------------
st.subheader("🟦 Proyección del modelo (GLOBAL)")

pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, es_local=True) * mult_local
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, es_local=False) * mult_visita

total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global

st.write(f"Puntos esperados {local or 'LOCAL'}: **{pts_local_global:.1f}**")
st.write(f"Puntos esperados {visita or 'VISITA'}: **{pts_visita_global:.1f}**")
st.write(f"Total GLOBAL del modelo: **{total_global:.1f}**")
st.write(f"Spread GLOBAL del modelo (local - visita): **{spread_global:+.1f}**")

# ------------------------------------------------
# ... (resto del código igual que antes)
# ------------------------------------------------
