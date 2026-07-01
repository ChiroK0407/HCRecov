"""
absorption_engine_v2.py — Binary baseline (N2 + Propylene), with E-101 feed cooler
"""
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import load_params, load_components, dew_point_check


def simulate_absorption_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc, params: dict = None):
    comps = load_components()

    mw_n2 = comps["nitrogen"]["molecular_weight_g_mol"]
    mw_c3h6 = comps["propylene"]["molecular_weight_g_mol"]
    mw_avg = y_n2 * mw_n2 + y_hc * mw_c3h6
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    flow_hc_kg = total_kmol_hr * y_hc * mw_c3h6

    t_cooler_outlet_k = params["feed_cooler_outlet_temp_c"] + 273.15
    delta_t_cooling = t_feed_k - t_cooler_outlet_k
    cp_gas_kj_kmol_k = 30.0
    duty_kw = max((total_kmol_hr * cp_gas_kj_kmol_k * delta_t_cooling) / 3600.0, 0.0)
    u_w_m2_k = 50.0
    lmtd_k = max(delta_t_cooling / 2.0, 1.0)
    area_e101 = max((duty_kw * 1000.0) / (u_w_m2_k * lmtd_k), 1.0)
    capex_e101 = 12000.0 * math.pow(area_e101 / 5.0, 0.59) * 1.25
    opex_e101 = duty_kw * 0.015

    dew_notes = []
    for cname, y_i in [("propylene", y_hc), ("nitrogen", y_n2)]:
        result = dew_point_check(cname, comps[cname], y_i, p_feed_bar, t_cooler_outlet_k)
        dew_notes.append(result["note"])

    r_const = 0.08314
    vol_flow_m3_s = (total_kmol_hr * r_const * t_cooler_outlet_k) / (p_feed_bar * 3600.0)
    rho_g = (p_feed_bar * mw_avg) / (r_const * t_cooler_outlet_k)
    rho_l = params["solvent_density_kg_m3"]
    c_factor = params["souders_brown_c_factor"]
    derating = params["flooding_derating"]
    v_allowable = c_factor * math.sqrt((rho_l - rho_g) / rho_g) * derating

    ideal_area = vol_flow_m3_s / v_allowable
    ideal_dia_mm = math.sqrt(4.0 * ideal_area / math.pi) * 1000.0
    catalog_dia = [300, 400, 500, 600, 750, 900, 1000, 1200]
    selected_dia_mm = next((d for d in catalog_dia if d >= ideal_dia_mm), catalog_dia[-1])
    selected_dia_m = selected_dia_mm / 1000.0
    actual_area = (math.pi / 4.0) * selected_dia_m ** 2

    hc_params = params["henry_constants_bar_mole_fraction"]
    h_ref, t_ref_k, delta_h_k = hc_params["propylene"], hc_params["reference_temp_k"], hc_params["delta_h_sol_k"]
    h_at_cooler = h_ref * math.exp(delta_h_k * (1.0 / t_cooler_outlet_k - 1.0 / t_ref_k))

    m_c3h6 = h_at_cooler / p_feed_bar
    l_min_kmol_hr = 1.4 * total_kmol_hr * m_c3h6
    lean_oil_kmol_hr = l_min_kmol_hr * 1.5
    mw_solvent = 200.0
    lean_oil_rate_kg_hr = lean_oil_kmol_hr * mw_solvent
    absorption_factor = lean_oil_kmol_hr / (total_kmol_hr * m_c3h6)

    if absorption_factor > 1.0:
        ntu = 5.0
    elif absorption_factor > 0.5:
        ntu = 5.0 * absorption_factor
    else:
        ntu = 2.5 * absorption_factor
    true_efficiency = max(min(1.0 - math.exp(-ntu * (1.0 - 1.0 / max(absorption_factor, 0.01))), 0.98), 0.35)
    monomer_recovered_kg = flow_hc_kg * true_efficiency

    packing_height = 5.2
    column_volume = actual_area * packing_height
    capex_t101 = 135000.0 * math.pow(column_volume / 3.0, 0.62) * 1.5

    solvent_m3_hr = lean_oil_rate_kg_hr / (mw_solvent * 5.0)
    solvent_gpm = solvent_m3_hr / 0.2271
    capex_p101 = 18000.0 * math.pow(solvent_gpm / 50.0, 0.55) * 1.3
    head_m = (p_feed_bar * 1e5) / (rho_l * 9.81)
    pump_kw = (rho_l * 9.81 * solvent_m3_hr / 3600.0 * head_m) / (0.65 * 1000.0)
    opex_p101 = pump_kw * 0.08

    rows = [
        {
            "component": "E-101 Gas Feed Cooler",
            "rating": "TEMA BEM Fixed Tube-Sheet / CS Shell + SS Tubes",
            "max_capacity": f"{area_e101 * 1.2:.1f} m² ceiling",
            "used_capacity": f"{area_e101:.1f} m² required area",
            "flow_rate": round(feed_mass_kg_hr, 2),
            "monomer_conc": round(flow_hc_kg, 2),
            "capex": round(capex_e101, -2),
            "opex": round(opex_e101, 2),
            "efficiency": f"Cooling Duty: {duty_kw:.1f} kW | {t_feed_k-273.15:.0f}°C → {t_cooler_outlet_k-273.15:.0f}°C"
        },
        {
            "component": "T-101 Absorber Tower Packed Shell",
            "rating": "ASME Section VIII / ANSI 150# Low Press Casing",
            "max_capacity": f"{actual_area * v_allowable * rho_g * 3600.0:.1f} kg/hr hydraulic ceiling",
            "used_capacity": f"{feed_mass_kg_hr:.1f} kg/hr",
            "flow_rate": round(feed_mass_kg_hr, 2),
            "monomer_conc": round(flow_hc_kg, 2),
            "capex": round(capex_t101, -2),
            "opex": round(5.50 * (lean_oil_rate_kg_hr / 1000.0), 2),
            "efficiency": f"Recovery: {true_efficiency*100:.1f}% | A={absorption_factor:.2f}"
        },
        {
            "component": "P-101 A/B Solvent Circulation Pumps",
            "rating": "API 610 Centrifugal / Standard 7.5 kW Frame",
            "max_capacity": f"{solvent_gpm * 1.25:.1f} GPM",
            "used_capacity": f"{solvent_gpm:.1f} GPM",
            "flow_rate": round(lean_oil_rate_kg_hr + monomer_recovered_kg, 2),
            "monomer_conc": round(monomer_recovered_kg, 2),
            "capex": round(capex_p101, -2),
            "opex": round(opex_p101, 2),
            "efficiency": "Solvent Recirculation Loop Containment"
        }
    ]
    return rows, dew_notes


def get_summary(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc, params: dict):
    rows, _ = simulate_absorption_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc, params)

    mw_n2, mw_c3h6 = 28.013, 42.081
    mw_avg = y_n2 * mw_n2 + y_hc * mw_c3h6
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    total_hc_kg = total_kmol_hr * y_hc * mw_c3h6
    recovered_kg = rows[2]["monomer_conc"]
    efficiency = (recovered_kg / total_hc_kg * 100.0) if total_hc_kg > 0 else 0.0
    total_capex = sum(r["capex"] for r in rows)
    total_opex = sum(r["opex"] for r in rows)
    return efficiency, total_capex, total_opex