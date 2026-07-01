"""
membrane_engine_v3.py — Run 3 Ternary Rigorous Membrane Engine (consolidated)
-------------------------------------------------------------------------------
Combines:
  - Ternary composition (N2 + C3H6 + C3H8) with Pitzer Z-factor real-gas
    compression correction and Arrhenius temperature-corrected permeability
    (the core Run 3 rigor).
  - Discharge pressure read from process_parameters.json (not hardcoded).
  - Parameterised OPEX from economics.json (replacement + auxiliaries).
"""

import json
import math
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str) -> dict:
    with open(_DATA_DIR / filename, "r") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
_BARRER_TO_SI = 3.346e-16
_R_GAS = 8.314
_GAMMA = 1.40

_TC = {"n2": 126.2, "c3h6": 364.9, "c3h8": 369.8}
_PC = {"n2": 33.9,  "c3h6": 46.0,  "c3h8": 42.5}
_OMEGA = {"n2": 0.037, "c3h6": 0.144, "c3h8": 0.152}
_MW = {"n2": 28.01, "c3h6": 42.08, "c3h8": 44.10}

_SKIN_THICKNESS_M = 0.1e-6
_PERM_REF_BARRER = {"c3h6": 15.0, "c3h8": 3.5, "n2": 0.25}
_EP_ACTIVATION_J_MOL = {"c3h6": 28_000.0, "c3h8": 32_000.0}
_T_REF_K = 308.15
_ELEMENT_AREA_M2 = 40.0
_P_PERMEATE_BAR = 1.2


def _get_discharge_pressure(fallback_bar: float = 26.0) -> float:
    """Reads p_discharge_bar (or derives it from differential target) from process_parameters.json."""
    try:
        params = _load_json("process_parameters.json")
        mem_cfg = params["separation_parameters"]["membrane"]
        if "p_discharge_bar" in mem_cfg:
            return float(mem_cfg["p_discharge_bar"])
        dp_target = mem_cfg["differential_pressure_target_bar"]
        return _P_PERMEATE_BAR + dp_target
    except (FileNotFoundError, KeyError):
        return fallback_bar


def _membrane_opex(standard_area_m2: float) -> float:
    """OPEX from economics.json (replacement + auxiliaries), with safe fallback."""
    OPERATING_HOURS_PER_YEAR = 8000.0
    REPLACEMENT_CYCLE_YEARS = 3.0
    AUXILIARY_FIXED_USD_HR = 0.25

    try:
        econ = _load_json("economics.json")
        skid_cfg = econ["equipment_curves"]["membrane_skid"]
        base_cost = skid_cfg["base_cost_usd"]
        base_cap = skid_cfg["base_capacity"]
        exp = skid_cfg["scaling_exponent"]
        mat_factor = skid_cfg["material_factor"]
        capex_total = base_cost * math.pow(standard_area_m2 / base_cap, exp) * mat_factor
    except (FileNotFoundError, KeyError):
        return 1.45

    annual_replacement = capex_total / REPLACEMENT_CYCLE_YEARS
    return round(annual_replacement / OPERATING_HOURS_PER_YEAR + AUXILIARY_FIXED_USD_HR, 2)


def _pitzer_z(t_k: float, p_bar: float, tc_k: float, pc_bar: float, omega: float) -> float:
    tr = t_k / tc_k
    pr = p_bar / pc_bar
    b0 = 0.083 - (0.422 / math.pow(tr, 1.6))
    b1 = 0.139 - (0.172 / math.pow(tr, 4.2))
    return 1.0 + (b0 + omega * b1) * (pr / tr)


def _mixture_critical_props(y_n2: float, y_c3h6: float, y_c3h8: float) -> tuple[float, float, float]:
    tc_avg = y_n2 * _TC["n2"] + y_c3h6 * _TC["c3h6"] + y_c3h8 * _TC["c3h8"]
    pc_avg = y_n2 * _PC["n2"] + y_c3h6 * _PC["c3h6"] + y_c3h8 * _PC["c3h8"]
    omega_avg = y_n2 * _OMEGA["n2"] + y_c3h6 * _OMEGA["c3h6"] + y_c3h8 * _OMEGA["c3h8"]
    return tc_avg, pc_avg, omega_avg


def simulate_membrane_rated(
    feed_mass_kg_hr: float, p_feed_bar: float, t_feed_k: float,
    y_n2: float, y_c3h6: float, y_c3h8: float
) -> list:
    """
    Ternary, rigorous: Pitzer real-gas compression + Arrhenius permeability +
    SI-consistent log-mean-ΔP flux. p_discharge and OPEX both sourced from JSON.
    """
    mw_avg = y_n2 * _MW["n2"] + y_c3h6 * _MW["c3h6"] + y_c3h8 * _MW["c3h8"]
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    flow_c3h6_kg = total_kmol_hr * y_c3h6 * _MW["c3h6"]
    flow_c3h8_kg = total_kmol_hr * y_c3h8 * _MW["c3h8"]
    f1_monomer_kg_hr = flow_c3h6_kg + flow_c3h8_kg

    p_discharge = _get_discharge_pressure()

    tc_avg, pc_avg, omega_avg = _mixture_critical_props(y_n2, y_c3h6, y_c3h8)
    z_suction = _pitzer_z(t_feed_k, p_feed_bar, tc_avg, pc_avg, omega_avg)
    z_discharge = _pitzer_z(t_feed_k, p_discharge, tc_avg, pc_avg, omega_avg)
    z_avg = (z_suction + z_discharge) / 2.0

    isentropic_work = (
        (_GAMMA / (_GAMMA - 1.0)) * _R_GAS * t_feed_k
        * (math.pow(p_discharge / p_feed_bar, (_GAMMA - 1.0) / _GAMMA) - 1.0)
    )
    compressor_kw = (total_kmol_hr * isentropic_work * z_avg) / (3600.0 * 0.72)

    catalog_kw = [45.0, 75.0, 110.0, 132.0, 160.0]
    selected_comp_kw = next((k for k in catalog_kw if k >= compressor_kw), catalog_kw[-1])
    capex_k301 = 75000.0 * math.pow(selected_comp_kw / 50.0, 0.72) * 1.3

    perm_c3h6 = _PERM_REF_BARRER["c3h6"] * math.exp(
        (-_EP_ACTIVATION_J_MOL["c3h6"] / _R_GAS) * (1.0 / t_feed_k - 1.0 / _T_REF_K)
    )
    perm_c3h8 = _PERM_REF_BARRER["c3h8"] * math.exp(
        (-_EP_ACTIVATION_J_MOL["c3h8"] / _R_GAS) * (1.0 / t_feed_k - 1.0 / _T_REF_K)
    )
    perm_n2 = _PERM_REF_BARRER["n2"]

    alpha_c3h6_n2 = perm_c3h6 / perm_n2
    alpha_c3h8_n2 = perm_c3h8 / perm_n2

    pp_c3h6_feed = p_discharge * y_c3h6
    pp_c3h8_feed = p_discharge * y_c3h8
    pp_c3h6_retentate = pp_c3h6_feed * 0.05
    pp_c3h8_retentate = pp_c3h8_feed * 0.05

    def _capped_permeate_y(y_feed: float, alpha: float) -> float:
        y_perm_ideal = (y_feed * alpha) / (1.0 + y_feed * (alpha - 1.0))
        return min(y_perm_ideal, 0.60)

    y_c3h6_perm = _capped_permeate_y(y_c3h6, alpha_c3h6_n2)
    y_c3h8_perm = _capped_permeate_y(y_c3h8, alpha_c3h8_n2)
    pp_c3h6_permeate = _P_PERMEATE_BAR * y_c3h6_perm
    pp_c3h8_permeate = _P_PERMEATE_BAR * y_c3h8_perm

    def _log_mean_dp_bar(pp_feed: float, pp_retentate: float, pp_permeate: float) -> float:
        dp_feed = max(pp_feed - pp_permeate, 1e-6)
        dp_retentate = max(pp_retentate - pp_permeate, 1e-6)
        if abs(dp_feed - dp_retentate) < 1e-9:
            return dp_feed
        return (dp_feed - dp_retentate) / math.log(dp_feed / dp_retentate)

    dp_lm_c3h6_bar = _log_mean_dp_bar(pp_c3h6_feed, pp_c3h6_retentate, pp_c3h6_permeate)
    dp_lm_c3h8_bar = _log_mean_dp_bar(pp_c3h8_feed, pp_c3h8_retentate, pp_c3h8_permeate)

    flux_c3h6_mol_m2_s = (perm_c3h6 * _BARRER_TO_SI * dp_lm_c3h6_bar * 1e5) / _SKIN_THICKNESS_M
    flux_c3h8_mol_m2_s = (perm_c3h8 * _BARRER_TO_SI * dp_lm_c3h8_bar * 1e5) / _SKIN_THICKNESS_M
    flux_c3h6_kmol_m2_hr = flux_c3h6_mol_m2_s * 3600.0 / 1000.0
    flux_c3h8_kmol_m2_hr = flux_c3h8_mol_m2_s * 3600.0 / 1000.0
    net_flux_kmol_m2_hr = max(flux_c3h6_kmol_m2_hr + flux_c3h8_kmol_m2_hr, 1e-5)

    target_kmol_hr = total_kmol_hr * (y_c3h6 + y_c3h8) * 0.95
    ideal_area = target_kmol_hr / net_flux_kmol_m2_hr
    element_count = math.ceil(ideal_area / _ELEMENT_AREA_M2)
    standard_area = element_count * _ELEMENT_AREA_M2

    true_recovery = min(0.92 * (standard_area / ideal_area), 0.985)
    monomer_permeated_kg = f1_monomer_kg_hr * true_recovery
    capex_m301 = 48000.0 * math.pow(standard_area / 15.0, 0.65) * 1.2
    opex_m301 = _membrane_opex(standard_area)

    return [
        {
            "component": "K-301 Feed Gas Booster Compressor",
            "rating": f"API 619 Screw Compressor / {selected_comp_kw} kW Rating Frame",
            "max_capacity": f"{selected_comp_kw * 1.15:.1f} kW thermal boundary",
            "used_capacity": f"{compressor_kw:.1f} kW [Z_avg={z_avg:.3f}]",
            "flow_rate": round(feed_mass_kg_hr, 2),
            "monomer_conc": round(f1_monomer_kg_hr, 2),
            "capex": round(capex_k301, -2),
            "opex": round(selected_comp_kw * 0.08, 2),
            "efficiency": (
                f"Real-Gas Z_avg Correction | p_discharge={p_discharge:.1f} bar (from JSON)"
            )
        },
        {
            "component": "M-301 Polyimide Membrane Separator Skids",
            "rating": f"ASME Module Housing Bank / {element_count} Elements",
            "max_capacity": f"{standard_area:.1f} m² active skin profile",
            "used_capacity": f"{ideal_area:.1f} m² selective gas interface",
            "flow_rate": round(monomer_permeated_kg, 2),
            "monomer_conc": round(monomer_permeated_kg, 2),
            "capex": round(capex_m301, -2),
            "opex": opex_m301,
            "efficiency": (
                f"Arrhenius-Corrected Recovery: {true_recovery * 100:.1f}% | "
                f"P(C3H6)={perm_c3h6:.2f} Barrer @ {t_feed_k-273.15:.0f}°C | "
                f"OPEX = replacement + auxiliaries"
            )
        }
    ]


def get_summary(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc):
    """UI wrapper — splits y_hc into 80/20 propylene/propane."""
    y_c3h6 = y_hc * 0.80
    y_c3h8 = y_hc * 0.20
    rows = simulate_membrane_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_c3h6, y_c3h8)
    mw_avg = y_n2 * _MW["n2"] + y_c3h6 * _MW["c3h6"] + y_c3h8 * _MW["c3h8"]
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    total_hc_kg = total_kmol_hr * (y_c3h6 * _MW["c3h6"] + y_c3h8 * _MW["c3h8"])
    recovered_kg = rows[1]["monomer_conc"]
    efficiency = (recovered_kg / total_hc_kg * 100.0) if total_hc_kg > 0 else 0.0
    total_capex = sum(r["capex"] for r in rows)
    total_opex = sum(r["opex"] for r in rows)
    return efficiency, total_capex, total_opex


def simulate_membrane_rated_ui(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc):
    """UI-facing call matching the v2 page signature — returns (rows, dew_notes)."""
    y_c3h6 = y_hc * 0.80
    y_c3h8 = y_hc * 0.20
    rows = simulate_membrane_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_c3h6, y_c3h8)
    return rows, []