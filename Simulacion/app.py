import streamlit as st
import random

# ------------------------------------------------
# CONFIG BÁSICA
# ------------------------------------------------
st.set_page_config(page_title="Simulador de Apuestas", layout="wide")

# CSS simple para cel
st.markdown(
    """
    <style>
    .block-container {max-width: 1100px; margin: 0 auto; padding-top: 0.8rem;}
    @media (max-width: 768px){
        .block-container {padding-left: 0.6rem; padding-right: 0.6rem;}
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Simulador de Apuestas 🏈🏀")
st.markdown("""
🟦 = modelo con promedios GLOBAL  
🟩 = modelo con promedios CASA/VISITA  
Este modelo ya está **suavizado** para no disparar diferencias absurdas.
""")

# ------------------------------------------------
# 1. DATOS DEL PARTIDO
# ------------------------------------------------
st.subheader("Datos del partido")

col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "Panthers")
    st.markdown("**Promedios GLOBAL del LOCAL**")
    l_anota_global = st.number_input("Local: puntos que ANOTA (global)", 0.0, 150.0, 18.9)
    l_permite_global = st.number_input("Local: puntos que PERMITE (global)", 0.0, 150.0, 22.8)
with col2:
    visita = st.text_input("Equipo VISITA", "Saints")
    st.markdown("**Promedios GLOBAL del VISITA**")
    v_anota_global = st.number_input("Visita: puntos que ANOTA (global)", 0.0, 150.0, 15.3)
    v_permite_global = st.number_input("Visita: puntos que PERMITE (global)", 0.0, 150.0, 27.0)

st.caption("Si más abajo llenas CASA/VISITA, te mostrará también esa proyección aparte.")

# ------------------------------------------------
# 2. DATOS CASA / VISITA (opcional)
# ------------------------------------------------
st.subheader("Promedios por condición (opcional)")

c1, c2 = st.columns(2)
with c1:
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", 0.0, 150.0, 0.0)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", 0.0, 150.0, 0.0)
with c2:
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", 0.0, 150.0, 0.0)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", 0.0, 150.0, 0.0)

hay_cv = any([
    l_anota_casa > 0, l_permite_casa > 0, v_anota_visita > 0, v_permite_visita > 0
])

# ------------------------------------------------
# 3. AJUSTE POR LESIONES
# ------------------------------------------------
st.subheader("Ajuste por lesiones / QB (opcional)")
c3, c4 = st.columns(2)
with c3:
    afecta_local = st.checkbox("¿Afecta ofensiva LOCAL?", value=False)
    mult_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
with c4:
    afecta_visita = st.checkbox("¿Afecta ofensiva VISITA?", value=False)
    mult_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)

if not afecta_local:
    mult_local = 1.0
if not afecta_visita:
    mult_visita = 1.0

# ------------------------------------------------
# 4. FUNCIÓN DE PROYECCIÓN (NUEVA)
# ------------------------------------------------
def proyeccion_suavizada(ofensiva_propia, defensa_rival, es_local=False):
    """
    ofensiva_propia: puntos que anota ese equipo
    defensa_rival: puntos que permite el rival
    es_local: bool
    fórmula: 55% ofensiva + 35% defensa rival + 10% localía
    """
    base = (0.55 * ofensiva_propia) + (0.35 * defensa_rival)
    if es_local:
        base += 1.5   # pequeña ventaja por jugar en casa
    return base

# ------------------------------------------------
# 5. PROYECCIÓN GLOBAL (con nueva fórmula)
# ------------------------------------------------
st.subheader("🟦 Proyección del modelo (GLOBAL)")

# puntos esperados con la nueva fórmula
pts_local_global = proyeccion_suavizada(l_anota_global, v_permite_global, es_local=True) * mult_local
pts_visita_global = proyeccion_suavizada(v_anota_global, l_permite_global, es_local=False) * mult_visita

total_global = pts_local_global + pts_visita_global
spread_global = pts_local_global - pts_visita_global  # local - visita

st.write(f"Puntos esperados {local}: **{pts_local_global:.1f}**")
st.write(f"Puntos esperados {visita}: **{pts_visita_global:.1f}**")
st.write(f"Total GLOBAL del modelo: **{total_global:.1f}**")
st.write(f"Spread GLOBAL del modelo (Local - Visita): **{spread_global:+.1f}**")

# ------------------------------------------------
# 6. PROYECCIÓN CASA / VISITA
# ------------------------------------------------
st.subheader("🟩 Proyección del modelo (CASA / VISITA)")

if hay_cv:
    pts_local_cv = proyeccion_suavizada(
        l_anota_casa if l_anota_casa > 0 else l_anota_global,
        v_permite_visita if v_permite_visita > 0 else v_permite_global,
        es_local=True
    ) * mult_local

    pts_visita_cv = proyeccion_suavizada(
        v_anota_visita if v_anota_visita > 0 else v_anota_global,
        l_permite_casa if l_permite_casa > 0 else l_permite_global,
        es_local=False
    ) * mult_visita

    total_cv = pts_local_cv + pts_visita_cv
    spread_cv = pts_local_cv - pts_visita_cv

    st.write(f"Puntos esperados {local} (casa): **{pts_local_cv:.1f}**")
    st.write(f"Puntos esperados {visita} (visita): **{pts_visita_cv:.1f}**")
    st.write(f"Total CASA/VISITA del modelo: **{total_cv:.1f}**")
    st.write(f"Spread CASA/VISITA del modelo: **{spread_cv:+.1f}**")
else:
    st.info("Si llenas los campos de casa/visita te mostrará esta proyección también.")

# ------------------------------------------------
# 7. LÍNEA REAL
# ------------------------------------------------
st.subheader("Línea real del sportsbook")

c5, c6 = st.columns(2)
with c5:
    spread_casa = st.number_input("Spread de la casa (negativo si LOCAL es favorito)", -50.0, 50.0, -5.5, 0.5)
with c6:
    total_casa = st.number_input("Total (O/U) de la casa", 0.0, 300.0, 42.0, 0.5)

# ------------------------------------------------
# 8. DIFERENCIAS VS LÍNEA REAL (ahora más claras)
# ------------------------------------------------
st.subheader("Diferencias vs línea real")

dif_spread_global = spread_global - spread_casa
dif_total_global = total_global - total_casa

st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

if abs(dif_spread_global) >= 8:
    st.error("⚠️ El spread del modelo está MUY lejos de la línea. Revisa datos o hay posible value.")
elif abs(dif_spread_global) >= 5:
    st.warning("⚠️ El spread del modelo está bastante distinto a la línea.")

if abs(dif_total_global) >= 6:
    st.warning("⚠️ El total del modelo está muy distinto al de la casa.")

if hay_cv:
    dif_spread_cv = spread_cv - spread_casa
    dif_total_cv = total_cv - total_casa

    st.write(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.write(f"🟩 Dif. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")

# ------------------------------------------------
# 9. MONTE CARLO GLOBAL
# ------------------------------------------------
st.subheader("Simulación Monte Carlo 🟦 (GLOBAL)")
num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)
desv_global = max(5, total_global * 0.15)

covers = 0
overs = 0

for _ in range(num_sims_global):
    sim_local = max(0, random.gauss(pts_local_global, desv_global))
    sim_visita = max(0, random.gauss(pts_visita_global, desv_global))

    # spread: local - visita + spread_casa >= 0 significa que el local cubre
    if (sim_local - sim_visita) + spread_casa >= 0:
        covers += 1
    if (sim_local + sim_visita) > total_casa:
        overs += 1

st.write(f"Prob. de que **{local}** cubra el spread (GLOBAL): **{covers/num_sims_global*100:.1f}%**")
st.write(f"Prob. de OVER (GLOBAL): **{overs/num_sims_global*100:.1f}%**")

# ------------------------------------------------
# 10. MONTE CARLO CASA / VISITA
# ------------------------------------------------
st.subheader("Simulación Monte Carlo 🟩 (CASA / VISITA)")
if hay_cv:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="cv_slider")
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

    st.write(f"Prob. de que **{local}** cubra (CASA/VISITA): **{covers_cv/num_sims_cv*100:.1f}%**")
    st.write(f"Prob. de OVER (CASA/VISITA): **{overs_cv/num_sims_cv*100:.1f}%**")
else:
    st.info("Para correr la simulación de CASA/VISITA llena los campos de casa/visita.")
