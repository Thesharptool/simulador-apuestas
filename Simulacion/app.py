
    st.write(f"- Modelo (formato casa): **LOCAL {spread_global:+.1f}**")
    st.write(f"- Casa: **LOCAL {spread_casa:+.1f}**")
    dif_spread = spread_global - spread_casa
    st.write(f"- **DIF. SPREAD (GLOBAL): {dif_spread:+.1f} pts**")

with st.expander("🔍 Comparación de totales (GLOBAL)", expanded=True):
    st.write(f"- Modelo: **{total_global:.1f}**")
    st.write(f"- Casa: **{total_casa:.1f}**")
    dif_total = total_global - total_casa
    st.write(f"- **DIF. TOTAL (GLOBAL): {dif_total:+.1f} pts**")

# alerta de trap line
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
    ml_local = st.number_input("Moneyline LOCAL (americano)", value=0, step=5)
with c_ml2:
    ml_visita = st.number_input("Moneyline VISITA (americano)", value=0, step=5)


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
# modelo: muy sencillo, si spread modelo > 0 => local favorito
p_local_modelo = 50 + (spread_global * 2)  # muy simple
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
# desviación distinta para NFL/NBA
if liga == "NBA":
    desv = max(6, total_global * 0.12)
else:
    desv = max(5, total_global * 0.15)

for _ in range(num_sims):
    sim_l = max(0, random.gauss(pts_local_global, desv))
    sim_v = max(0, random.gauss(pts_visita_global, desv))
    # spread: LOCAL + spread_casa debe ser >= visita
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
recs = []
if prob_cover >= 55:
    recs.append(f"🟢 Spread GLOBAL: {local_name or 'LOCAL'} {spread_casa:+.1f} → {prob_cover:.1f}%")
if prob_over >= 55:
    recs.append(f"🟢 Total GLOBAL: OVER {total_casa:.1f} → {prob_over:.1f}%")

if recs:
    for r in recs:
        st.success(r)
else:
    st.info("Por ahora ninguna llega al 55%.")

# =========================================================
# 8) Edge del modelo vs casa
# =========================================================
st.subheader("8) Edge del modelo vs casa")
# spread: si modelo dice LOCAL -3 y casa dice LOCAL -5 → modelo +2 pts a favor del local
edge_local = -(spread_casa) + spread_global  # lo que gana LOCAL
edge_visita = -edge_local

if edge_local >= 0:
    st.success(f"Edge LOCAL: +{edge_local:.1f} pts (la casa está más alta que tu modelo)")
else:
    st.error(f"Edge LOCAL: {edge_local:.1f} pts (tu modelo está más alto que la casa)")

if edge_visita >= 0:
    st.success(f"Edge VISITA: +{edge_visita:.1f} pts")
else:
    st.error(f"Edge VISITA: {edge_visita:.1f} pts")

st.caption("Pon los moneylines para calcular el edge de forma más fina.")
