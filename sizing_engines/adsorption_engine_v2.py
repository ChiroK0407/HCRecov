"""
adsorption_engine_v2.py — Binary baseline (N2 + Propylene)
"""
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_params, load_components, dew_point_check


def simulate_adsorption_rated(feed_mass_kg_hr, p_feed_bar, y_n2, y_hc, t_feed_k=337.15, params: dict = None):
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

    # Now params is the chosen adsorbent dict
    iso_c3h6 = params["extended_langmuir_isotherm"]["propylene"]
    iso_n2   = params["extended_langmuir_isotherm"]["nitrogen"]
    qm_c3h6, b_c3h6, b_n2 = iso_c3h6["qm_mol_kg"], iso_c3h6["b_bar_inv"], iso_n2["b_bar_inv"]

    p_partial_hc = p_feed_bar * y_hc
    p_partial_n2 = p_feed_bar * y_n2

    bed_loading_mol_kg = max(
        (qm_c3h6 * b_c3h6 * p_partial_hc) / (1.0 + b_c3h6 * p_partial_hc + b_n2 * p_partial_n2),
        0.05
    )

    cycle_time_hr = params["cycle_time_minutes"] / 60.0
    moles_per_half_cycle = (total_kmol_hr * y_hc * cycle_time_hr * 0.5) * 1000.0
    ideal_adsorbent_mass_kg = moles_per_half_cycle / bed_loading_mol_kg

    rho_bed = params["bed_bulk_density_kg_m3"]
    bed_l_d = 3.2
    vessel_vol = (ideal_adsorbent_mass_kg / rho_bed) * 2.0
    cross_section = vessel_vol / bed_l_d
    ideal_dia_mm = math.sqrt(4.0 * cross_section / math.pi) * 1000.0

    catalog_dia = [400, 600, 900, 1200, 1500]
    selected_dia_mm = next((d for d in catalog_dia if d >= ideal_dia_mm), catalog_dia[-1])
    selected_dia_m = selected_dia_mm / 1000.0
    actual_area = (math.pi / 4.0) * selected_dia_m ** 2
    standard_volume = actual_area * bed_l_d
    standard_mass_capacity_kg = (standard_volume / 2.0) * rho_bed

    net_recovery_factor = min(0.94 * (standard_mass_capacity_kg / ideal_adsorbent_mass_kg), 0.985)
    monomer_adsorbed_kg = flow_hc_kg * net_recovery_factor

    capex_y201 = 18000.0 * math.pow(total_kmol_hr / 50.0, 0.52)
    capex_v201 = 92000.0 * math.pow(standard_volume / 4.0, 0.58) * 1.4

    rows = [
        {
            "component": "Y-201 Duplex Guard Cartridge Element",
            "rating": "ASME Housing / 0.5 Micron Particulate Strainer",
            "max_capacity": f"{total_kmol_hr * 1.4:.2f} kmol/hr limit",
            "used_capacity": f"{total_kmol_hr:.2f} kmol/hr line entry load",
            "flow_rate": round(feed_mass_kg_hr, 2),
            "monomer_conc": round(flow_hc_kg, 2),
            "capex": round(capex_y201, -2),
            "opex": 0.45,
            "efficiency": "99.95% Resin Fines Separation Guard"
        },
        {
            "component": "V-201 A/B Twin Swing Adsorber Steel Shells",
            "rating": "ASME Section VIII / ANSI 150# Rating Vessel Frame",
            "max_capacity": f"{standard_mass_capacity_kg:.1f} kg standard loading frame",
            "used_capacity": f"{ideal_adsorbent_mass_kg:.1f} kg required sieve mass",
            "flow_rate": round(monomer_adsorbed_kg, 2),
            "monomer_conc": round(monomer_adsorbed_kg, 2),
            "capex": round(capex_v201, -2),
            "opex": 3.50,
            "efficiency": f"Langmuir Equilibrium Affinity: {net_recovery_factor*100:.1f}% | Cycle={params['cycle_time_minutes']:.0f} min"
        }
    ]
    return rows, dew_notes


def get_summary(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc, params: dict):
    rows, _ = simulate_adsorption_rated(feed_mass_kg_hr, p_feed_bar, y_n2, y_hc, t_feed_k, params)
    mw_n2, mw_c3h6 = 28.013, 42.081
    mw_avg = y_n2 * mw_n2 + y_hc * mw_c3h6
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    total_hc_kg = total_kmol_hr * y_hc * mw_c3h6
    recovered_kg = rows[1]["monomer_conc"]
    efficiency = (recovered_kg / total_hc_kg * 100.0) if total_hc_kg > 0 else 0.0
    total_capex = sum(r["capex"] for r in rows)
    total_opex = sum(r["opex"] for r in rows)
    return efficiency, total_capex, total_opex