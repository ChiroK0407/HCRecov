"""
2_PSA_Adsorption.py — Pressure Swing Adsorption technology page
"""
import streamlit as st
import pandas as pd
from sizing_engines.adsorption_engine_v2 import simulate_adsorption_rated as sim_v2, get_summary as summary_v2
from sizing_engines.adsorption_engine_v3 import simulate_adsorption_rated_ui as sim_v3, get_summary as summary_v3

from utils import get_selected_params
import json

with open("data/process_parameters.json") as f:
    params = json.load(f)

adsorbent_options = [m["name"] for m in params["separation_parameters"]["adsorption_psa"]["adsorbents"]]

# ── Ensure global session_state defaults exist, even if this page loads first ──
_GLOBAL_DEFAULTS = {
    "feed_mass_kg_hr": 650.0,
    "p_feed_bar": 1.2,
    "t_feed_c": 64.0,
    "y_hc_pct": 5.0,
    "y_c3h6_pct": 4.0,
    "y_c3h8_pct": 1.0,
    "engine_version": "v2",
}
for _key, _val in _GLOBAL_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

st.title("② Twin-Bed Pressure Swing Adsorption")

st.markdown(
    """
    **Separation Basis:** Cyclic adsorption–desorption using a competitive
    extended Langmuir isotherm on a molecular sieve adsorbent bed.

    **Driving Force:** Pressure swing — hydrocarbons adsorb preferentially
    onto the sieve at high pressure, then desorb during blowdown to low
    pressure, regenerating the bed for the next cycle.

    **Mechanism:** Twin beds alternate between adsorption and regeneration
    so the process runs continuously; bed sizing depends on cycle time,
    competitive loading capacity, and blowdown/purge losses.
    """
)

st.divider()

selected_adsorbent = st.selectbox("Choose adsorbent material", adsorbent_options)

chosen_params = get_selected_params("adsorption_psa", selected_adsorbent)
st.caption(f"Active adsorbent: **{selected_adsorbent}**")

# ── Initialize committed (last-run) values on first load ───────────────────
if "psa_committed" not in st.session_state:
    st.session_state["psa_committed"] = {
        "feed": st.session_state["feed_mass_kg_hr"],
        "p_feed": st.session_state["p_feed_bar"],
        "t_feed_c": st.session_state["t_feed_c"],
        "y_hc_pct": st.session_state["y_hc_pct"],
        "engine_version": st.session_state["engine_version"],
    }

col_flow, col_controls = st.columns([3, 2])

with col_flow:
    st.subheader("Process Flow")
    with st.container(border=True):
        st.image("assets/flowsheets/psa_flowsheet.png", width='stretch')
        # If no image yet, comment the line above and uncomment below:
        # st.markdown("*Insert PSA flowsheet at assets/flowsheets/psa_flowsheet.png*")

with col_controls:
    st.subheader("Feed Conditions")

    feed_input = st.slider(
        "Feed Flow (kg/hr)", 200.0, 1500.0,
        st.session_state["psa_committed"]["feed"], step=10.0, key="psa_feed_slider"
    )
    p_feed_input = st.slider(
        "Feed Pressure (bar a)", 0.5, 5.0,
        st.session_state["psa_committed"]["p_feed"], step=0.05, key="psa_p_slider"
    )
    t_feed_c_input = st.slider(
        "Feed Temperature (°C)", 20.0, 100.0,
        st.session_state["psa_committed"]["t_feed_c"], step=1.0, key="psa_t_slider"
    )
    y_hc_input = st.slider(
        "Monomer Conc. (mol% HC)", 1.0, 20.0,
        st.session_state["psa_committed"]["y_hc_pct"], step=0.5, key="psa_y_slider"
    )

    st.caption(f"Engine Version: **{st.session_state['engine_version'].upper()}** (set in sidebar)")

    run_clicked = st.button("▶️ Run Simulation", type="primary", width='stretch', key="psa_run_btn")

    if run_clicked:
        st.session_state["psa_committed"] = {
            "feed": feed_input,
            "p_feed": p_feed_input,
            "t_feed_c": t_feed_c_input,
            "y_hc_pct": y_hc_input,
            "engine_version": st.session_state["engine_version"],
        }
        st.session_state["feed_mass_kg_hr"] = feed_input
        st.session_state["p_feed_bar"] = p_feed_input
        st.session_state["t_feed_c"] = t_feed_c_input
        st.session_state["y_hc_pct"] = y_hc_input
        st.success("Simulation updated with current parameters.")

committed = st.session_state["psa_committed"]
feed = committed["feed"]
p_feed = committed["p_feed"]
t_feed_k = committed["t_feed_c"] + 273.15
y_hc = committed["y_hc_pct"] / 100.0
y_n2 = 1.0 - y_hc
engine_version = committed["engine_version"]

if (feed_input, p_feed_input, t_feed_c_input, y_hc_input) != (committed["feed"], committed["p_feed"], committed["t_feed_c"], committed["y_hc_pct"]):
    st.info("⚠️ Sliders have changed since the last run. Click **Run Simulation** to update results below.")

st.divider()

if engine_version == "v2":
    rows, dew_notes = sim_v2(feed, p_feed, y_n2, y_hc, t_feed_k, chosen_params)
    efficiency, total_capex, total_opex = summary_v2(feed, p_feed, t_feed_k, y_n2, y_hc, chosen_params)
else:
    rows, dew_notes = sim_v3(feed, p_feed, t_feed_k, y_n2, y_hc, chosen_params)
    efficiency, total_capex, total_opex = summary_v3(feed, p_feed, t_feed_k, y_n2, y_hc, chosen_params)

st.subheader(f"Equipment Ledger ({'Run 2 — Binary' if engine_version == 'v2' else 'Run 3 — Ternary'})")

df = pd.DataFrame(rows)[["component", "rating", "max_capacity", "used_capacity", "flow_rate", "monomer_conc", "capex", "opex", "efficiency"]]
df.columns = ["Component", "Rating", "Max Capacity", "Used Capacity", "Flow (kg/hr)", "Monomer (kg)", "CAPEX (USD)", "OPEX ($/hr)", "Notes"]

# Cast everything to string BEFORE transposing — avoids mixed-dtype columns
# that pyarrow can't serialize (numeric CAPEX/OPEX mixed with text Rating/Notes
# in the same column after pivot).
df_display = df.copy()
df_display["CAPEX (USD)"] = df_display["CAPEX (USD)"].apply(lambda v: f"${v:,.0f}")
df_display["OPEX ($/hr)"] = df_display["OPEX ($/hr)"].apply(lambda v: f"${v:,.2f}")
df_display["Flow (kg/hr)"] = df_display["Flow (kg/hr)"].apply(lambda v: f"{v:,.2f}")
df_display["Monomer (kg)"] = df_display["Monomer (kg)"].apply(lambda v: f"{v:,.2f}")

df_transposed = df_display.set_index("Component").T.astype(str)
st.dataframe(df_transposed, width='stretch')

if dew_notes:
    with st.expander("🌡 Antoine Dew-Point Check"):
        for note in dew_notes:
            st.write(note)

st.divider()

st.subheader("Recovery Performance")
g1, g2, g3 = st.columns(3)
with g1:
    delta_color = "normal" if efficiency >= 90.0 else "inverse"
    st.metric("Net Recovery Efficiency", f"{efficiency:.1f}%", delta=f"{efficiency - 90.0:+.1f} pp vs target", delta_color=delta_color)
    st.progress(min(efficiency / 100.0, 1.0))
    if efficiency >= 90.0:
        st.success("✅ Meets 90% recovery target")
    else:
        st.warning("⚠️ Below 90% recovery target")
with g2:
    st.metric("Total Package CAPEX", f"${total_capex:,.0f}")
with g3:
    st.metric("Total OPEX", f"${total_opex:,.2f}/hr")