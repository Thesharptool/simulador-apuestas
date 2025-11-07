import streamlit as st
import random

st.title("Simulador de Apuestas 🏈🏀")

st.markdown("""
**Leyenda de colores**  
🟦 = modelo con promedios **GLOBAL**  
🟩 = modelo con promedios **CASA / VISITA**
""")

st.write("Llena los datos que tengas. Si llenas casa/visita, también te mostrará esa proyección aparte.")

# =============== 1. DATOS DEL PARTIDO ===============
st.subheader("Datos del partido")

col1, col2 = st.columns(2)

with col1:
    local = st.text_input("Equipo LOCAL", "")
    st.markdown("**Promedios GLOBAL del LOCAL**")
    l_anota_global = st.number_input("Local: puntos que ANOTA (global)", 0.0, 150.0, 0.0)
    l_permite_global = st.number_input("Local: puntos que PERMITE (global)", 0.0, 150.0, 0.0)

    st.markdown("**Promedios en CASA del LOCAL**")
    l_anota_casa = st.number_input("Local: puntos que ANOTA en casa", 0.0, 150.0, 0.0)
    l_permite_casa = st.number_input("Local: puntos que PERMITE en casa", 0.0, 150.0, 0.0)

with col2:
    visita = st.text_input("Equipo VISITA", "")
    st.markdown("**Promedios GLOBAL del VISITA**")
    v_anota_global = st.number_input("Visita: puntos que ANOTA (global)", 0.0, 150.0, 0.0)
    v_permite_global = st.number_input("Visita: puntos que PERMITE (global)", 0.0, 150.0, 0.0)

    st.markdown("**Promedios de VISITA del VISITA**")
    v_anota_visita = st.number_input("Visita: puntos que ANOTA de visita", 0.0, 150.0, 0.0)
    v_permite_visita = st.number_input("Visita: puntos que PERMITE de visita", 0.0, 150.0, 0.0)

st.caption("Si los de casa/visita están en 0, el modelo solo mostrará la parte global.")

# =============== 2. AJUSTE POR LESIONES ===============
st.subheader("Ajuste por lesiones / QB")
col3, col4 = st.columns(2)
with col3:
    afecta_local = st.checkbox("¿Afecta ofensiva LOCAL?", value=False)
    factor_local = st.slider("Multiplicador ofensivo LOCAL", 0.5, 1.1, 1.0, 0.05)
with col4:
    afecta_visita = st.checkbox("¿Afecta ofensiva VISITA?", value=False)
    factor_visita = st.slider("Multiplicador ofensivo VISITA", 0.5, 1.1, 1.0, 0.05)

if not afecta_local:
    factor_local = 1.0
if not afecta_visita:
    factor_visita = 1.0

# =============== 3. PROYECCIÓN GLOBAL ===============
st.subheader("🟦 Proyección del modelo (GLOBAL)")

proy_local_global = (l_anota_global + v_permite_global) / 2 if (l_anota_global or v_permite_global) else 0
proy_visita_global = (v_anota_global + l_permite_global) / 2 if (v_anota_global or l_permite_global) else 0

# ventaja de local
proy_local_global += 1.5
# lesiones
proy_local_global *= factor_local
proy_visita_global *= factor_visita

total_global = proy_local_global + proy_visita_global
spread_global = proy_local_global - proy_visita_global

if local and visita:
    st.write(f"Marcador GLOBAL: **{local} {proy_local_global:.1f} - {visita} {proy_visita_global:.1f}**")
st.write(f"Total GLOBAL: **{total_global:.1f}**")
st.write(f"Spread GLOBAL (Local - Visita): **{spread_global:+.1f}**")

# =============== 4. PROYECCIÓN CASA/VISITA ===============
st.subheader("🟩 Proyección del modelo (CASA / VISITA)")

hay_cv = (l_anota_casa > 0 or l_permite_casa > 0 or v_anota_visita > 0 or v_permite_visita > 0)

proy_local_cv = 0.0
proy_visita_cv = 0.0
total_cv = 0.0
spread_cv = 0.0

if hay_cv:
    if (l_anota_casa > 0 or v_permite_visita > 0):
        proy_local_cv = (l_anota_casa + v_permite_visita) / 2
    if (v_anota_visita > 0 or l_permite_casa > 0):
        proy_visita_cv = (v_anota_visita + l_permite_casa) / 2

    # misma ventaja y lesiones
    proy_local_cv += 1.5
    proy_local_cv *= factor_local
    proy_visita_cv *= factor_visita

    total_cv = proy_local_cv + proy_visita_cv
    spread_cv = proy_local_cv - proy_visita_cv

    if local and visita:
        st.write(f"Marcador CASA/VISITA: **{local} {proy_local_cv:.1f} - {visita} {proy_visita_cv:.1f}**")
    st.write(f"Total CASA/VISITA: **{total_cv:.1f}**")
    st.write(f"Spread CASA/VISITA: **{spread_cv:+.1f}**")
else:
    st.info("Para ver esta proyección llena los campos de casa/visita.")

# =============== 5. LÍNEA REAL Y ML ===============
st.subheader("Línea real del sportsbook")

col5, col6 = st.columns(2)
with col5:
    spread_casa = st.number_input("Spread de la casa (negativo si LOCAL es favorito)", -50.0, 50.0, 0.0, 0.5)
with col6:
    total_casa = st.number_input("Total (O/U) de la casa", 0.0, 300.0, 0.0, 0.5)

st.markdown("**Moneyline (opcional)**")
col7, col8 = st.columns(2)
with col7:
    ml_local = st.number_input(f"ML {local or 'Local'}", value=0)
with col8:
    ml_visita = st.number_input(f"ML {visita or 'Visita'}", value=0)

def american_odds_to_prob(odds):
    if odds == 0:
        return 0
    return (-odds / ((-odds) + 100)) if odds < 0 else (100 / (odds + 100))

prob_local_casa = american_odds_to_prob(ml_local)
prob_visita_casa = american_odds_to_prob(ml_visita)

if ml_local != 0 or ml_visita != 0:
    st.write(f"Probabilidad implícita **{local or 'Local'}**: {prob_local_casa*100:.2f}%")
    st.write(f"Probabilidad implícita **{visita or 'Visita'}**: {prob_visita_casa*100:.2f}%")

# =============== 6. DIFERENCIAS VS LÍNEA ===============
st.subheader("Diferencias vs línea real")

# GLOBAL
dif_spread_global = spread_global - spread_casa
dif_total_global = total_global - total_casa

st.write(f"🟦 Dif. SPREAD (GLOBAL): **{dif_spread_global:+.1f} pts**")
st.write(f"🟦 Dif. TOTAL (GLOBAL): **{dif_total_global:+.1f} pts**")

if abs(dif_spread_global) >= 10:
    st.error("⚠️ El SPREAD GLOBAL está MUY lejos de la línea. Revisa datos o hay posible value grande.")
elif abs(dif_spread_global) >= 5:
    st.warning("⚠️ El SPREAD GLOBAL está bastante distinto a la línea.")

if abs(dif_total_global) >= 6:
    st.warning("⚠️ El TOTAL GLOBAL está muy distinto al de la casa.")

# CASA / VISITA
if hay_cv:
    dif_spread_cv = spread_cv - spread_casa
    dif_total_cv = total_cv - total_casa

    st.write(f"🟩 Dif. SPREAD (CASA/VISITA): **{dif_spread_cv:+.1f} pts**")
    st.write(f"🟩 Dif. TOTAL (CASA/VISITA): **{dif_total_cv:+.1f} pts**")

    if abs(dif_spread_cv) >= 10:
        st.error("🚨 El SPREAD CASA/VISITA está MUY lejos de la línea.")
    elif abs(dif_spread_cv) >= 5:
        st.warning("⚠️ El SPREAD CASA/VISITA está bastante distinto a la línea.")

    if abs(dif_total_cv) >= 6:
        st.warning("⚠️ El TOTAL CASA/VISITA está muy distinto al de la casa.")

# =============== 7. SIMULACIÓN MONTE CARLO (GLOBAL) ===============
st.subheader("Simulación Monte Carlo 🟦 (GLOBAL)")

num_sims_global = st.slider("Número de simulaciones (GLOBAL)", 1000, 50000, 10000, 1000)

desviacion_global = max(5, total_global * 0.15)

covers_local_global = 0
overs_global = 0

for _ in range(num_sims_global):
    sim_local = random.gauss(proy_local_global, desviacion_global)
    sim_visita = random.gauss(proy_visita_global, desviacion_global)
    sim_local = max(0, sim_local)
    sim_visita = max(0, sim_visita)

    if (sim_local - sim_visita) + spread_casa >= 0:
        covers_local_global += 1
    if (sim_local + sim_visita) > total_casa:
        overs_global += 1

prob_cubre_local_global = covers_local_global / num_sims_global * 100
prob_over_global = overs_global / num_sims_global * 100

st.write(f"Probabilidad de que **{local or 'Local'}** cubra el spread (GLOBAL): **{prob_cubre_local_global:.1f}%**")
st.write(f"Probabilidad de OVER (GLOBAL): **{prob_over_global:.1f}%**")

# =============== 8. SIMULACIÓN MONTE CARLO (CASA/VISITA) ===============
st.subheader("Simulación Monte Carlo 🟩 (CASA / VISITA)")

if hay_cv:
    num_sims_cv = st.slider("Número de simulaciones (CASA/VISITA)", 1000, 50000, 10000, 1000, key="cv_slider")

    desviacion_cv = max(5, total_cv * 0.15)

    covers_local_cv = 0
    overs_cv = 0

    for _ in range(num_sims_cv):
        sim_local = random.gauss(proy_local_cv, desviacion_cv)
        sim_visita = random.gauss(proy_visita_cv, desviacion_cv)
        sim_local = max(0, sim_local)
        sim_visita = max(0, sim_visita)

        if (sim_local - sim_visita) + spread_casa >= 0:
            covers_local_cv += 1
        if (sim_local + sim_visita) > total_casa:
            overs_cv += 1

    prob_cubre_local_cv = covers_local_cv / num_sims_cv * 100
    prob_over_cv = overs_cv / num_sims_cv * 100

    st.write(f"Probabilidad de que **{local or 'Local'}** cubra el spread (CASA/VISITA): **{prob_cubre_local_cv:.1f}%**")
    st.write(f"Probabilidad de OVER (CASA/VISITA): **{prob_over_cv:.1f}%**")
else:
    st.info("Para correr la simulación de CASA/VISITA llena los campos de casa/visita.")

# =============== 9. COMPARACIÓN FINAL ===============
st.subheader("📊 Comparación final de modelos")

# valor absoluto de la diferencia de spread
global_edge = abs(dif_spread_global)
cv_edge = abs(dif_spread_cv) if hay_cv else 0

texto = ""
if hay_cv:
    if cv_edge > global_edge:
        texto = "👉 El modelo 🟩 CASA/VISITA ve MÁS diferencia que el modelo 🟦 GLOBAL. Revisa ese modelo primero."
    elif cv_edge < global_edge:
        texto = "👉 El modelo 🟦 GLOBAL ve más diferencia que el modelo 🟩 CASA/VISITA."
    else:
        texto = "👉 Ambos modelos ven una diferencia similar."
else:
    texto = "Solo hay modelo GLOBAL disponible (no llenaste casa/visita)."

st.write(texto)

# también podemos mostrar cuál se acerca más al total
global_total_edge = abs(dif_total_global)
cv_total_edge = abs(dif_total_cv) if hay_cv else 0

if hay_cv:
    if cv_total_edge > global_total_edge:
        st.write("En TOTAL también el modelo 🟩 CASA/VISITA está más lejos de la línea.")
    elif cv_total_edge < global_total_edge:
        st.write("En TOTAL el modelo 🟦 GLOBAL está más lejos de la línea.")
    else:
        st.write("En TOTAL ambos modelos están igual de cerca/lejos.")