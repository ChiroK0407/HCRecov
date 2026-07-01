"""
membrane_engine_v2.py — Binary baseline (N2 + Propylene)
"""
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_components, dew_point_check


def simulate_membrane_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc, params: dict):
    """
    Run membrane simulation for the selected material parameters.

    Args:
        feed_mass_kg_hr (float): Feed flow in kg/hr
        p_feed_bar (float): Feed pressure in bar
        t_feed_k (float): Feed temperature in Kelvin
        y_n2 (float): Mole fraction of nitrogen
        y_hc (float): Mole fraction of propylene
        params (dict): Selected membrane material parameters from JSON

    Returns:
        rows (list[dict]): Equipment ledger rows
        dew_notes (list[str]): Dew point check notes
    """
    comps = load_components()

    mw_n2 = comps["nitrogen"]["molecular_weight_g_mol"]
    mw_c3h6 = comps["propylene"]["molecular_weight_g_mol"]
    mw_avg = y_n2 * mw_n2 + y_hc * mw_c3h6
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    flow_hc_kg = total_kmol_hr * y_hc * mw_c3h6

    dew_notes = []
    for cname, y_i in [("propylene", y_hc), ("nitrogen", y_n2)]:
        result = dew_point_check(cname, comps[cname], y_i, p_feed_bar, t_feed_k)
        dew_notes.append(result["note"])

    # Use selected material parameters
    p_discharge = params["p_discharge_bar"]
    p_permeate = params["permeate_pressure_bar"]
    gamma = 1.40
    compression_ratio = p_discharge / p_feed_bar
    isentropic_work = (
        (gamma / (gamma - 1.0)) * 8.314 * t_feed_k
        * (compression_ratio ** ((gamma - 1.0) / gamma) - 1.0)
    )
    compressor_kw = (total_kmol_hr * isentropic_work) / (3600.0 * 0.72)

    catalog_kw = [15, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160]
    selected_comp_kw = next((k for k in catalog_kw if k >= compressor_kw), catalog_kw[-1])
    capex_k301 = 75000.0 * math.pow(selected_comp_kw / 50.0, 0.72) * 1.3

    perm_n2 = params["component_permeabilities_barrer"]["nitrogen"]
    perm_c3h6 = params["component_permeabilities_barrer"]["propylene"]
    l_m = params["skin_thickness_microns"] * 1e-6
    barrer_to_si = 3.346e-16

    pp_hc_feed = p_discharge * y_hc
    pp_hc_retentate = pp_hc_feed * 0.05

    alpha_c3h6_n2 = perm_c3h6 / perm_n2
    y_hc_perm = min((y_hc * alpha_c3h6_n2) / (1.0 + y_hc * (alpha_c3h6_n2 - 1.0)), 0.60)
    pp_hc_permeate = p_permeate * y_hc_perm

    if pp_hc_feed > pp_hc_permeate and pp_hc_retentate > pp_hc_permeate:
        dp_feed = pp_hc_feed - pp_hc_permeate
        dp_retentate = pp_hc_retentate - pp_hc_permeate
        delta_p_lm_bar = dp_feed if abs(dp_feed - dp_retentate) < 1e-9 else (dp_feed - dp_retentate) / math.log(dp_feed / dp_retentate)
    else:
        delta_p_lm_bar = max(pp_hc_feed - pp_hc_permeate, 1e-6)

    flux_mol_m2_s = (perm_c3h6 * barrer_to_si * delta_p_lm_bar * 1e5) / l_m
    flux_kmol_m2_hr = max(flux_mol_m2_s * 3600.0 / 1000.0, 0.002)

    target_kmol_hr = total_kmol_hr * y_hc * 0.95
    ideal_area_m2 = target_kmol_hr / flux_kmol_m2_hr
    element_area = params.get("element_area_m2", 40.0)
    element_count = math.ceil(ideal_area_m2 / element_area)
    standard_area = element_count * element_area

    net_recovery = min(0.92 * (standard_area / ideal_area_m2), 0.99)
    monomer_permeated_kg = flow_hc_kg * net_recovery
    capex_m301 = 48000.0 * math.pow(standard_area / 15.0, 0.65) * 1.2

    rows = [
        {
            "component": "K-301 Feed Gas Booster Compressor",
            "rating": f"API 619 Screw Machine / {selected_comp_kw} kW Motor Enclosure",
            "max_capacity": f"{selected_comp_kw * 1.15:.1f} kW thermal limit",
            "used_capacity": f"{compressor_kw:.1f} kW compression work",
            "flow_rate": round(feed_mass_kg_hr, 2),
            "monomer_conc": round(flow_hc_kg, 2),
            "capex": round(capex_k301, -2),
            "opex": round(selected_comp_kw * 0.08, 2),
            "efficiency": f"Isentropic Compression Ratio: {compression_ratio:.1f}:1 | ΔP_lm = {delta_p_lm_bar:.2f} bar"
        },
        {
            "component": "M-301 Membrane Separator Skids",
            "rating": f"ASME Rated Bank housing {element_count} Standard Elements",
            "max_capacity": f"{standard_area:.1f} m² active area",
            "used_capacity": f"{ideal_area_m2:.1f} m² selective flux interface",
            "flow_rate": round(monomer_permeated_kg, 2),
            "monomer_conc": round(monomer_permeated_kg, 2),
            "capex": round(capex_m301, -2),
            "opex": 1.45,
            "efficiency": f"Log-Mean ΔP Corrected Recovery: {net_recovery * 100:.1f}% | α(C3H6/N2)={alpha_c3h6_n2:.1f}"
        }
    ]
    return rows, dew_notes


def get_summary(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc, params: dict):
    """Returns (net_efficiency_pct, total_capex, total_opex) for the gauge widget."""
    rows, _ = simulate_membrane_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc, params)
    mw_n2, mw_c3h6 = 28.013, 42.081
    mw_avg = y_n2 * mw_n2 + y_hc * mw_c3h6
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    total_hc_kg = total_kmol_hr * y_hc * mw_c3h6
    recovered_kg = rows[1]["monomer_conc"]
    efficiency = (recovered_kg / total_hc_kg * 100.0) if total_hc_kg > 0 else 0.0
    total_capex = sum(r["capex"] for r in rows)
    total_opex = sum(r["opex"] for r in rows)
    return efficiency, total_capex, total_opex