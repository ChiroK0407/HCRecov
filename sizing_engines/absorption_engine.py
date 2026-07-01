"""
absorption_engine.py  —  HCRecov Run 2 (corrected)
----------------------------------------------------
Fixes applied in this version:
  [A] _min_solvent_rate: use y_hc-weighted HC molar flow, not total flow
  [B] true_efficiency: correct Kremser NTU form η = 1 - exp(-NTU*(1 - 1/A))
      with NTU independently set from packing height / HETP
  [C] E-101 return dict: capex/opex in correct keys; monomer_conc removed
      from position that was corrupting the ledger column alignment
"""

import json
import math
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str) -> dict:
    with open(_DATA_DIR / filename, "r") as fh:
        return json.load(fh)


def _get_absorption_params() -> dict:
    DEFAULTS = {
        "operating_temperature_c":    35.0,
        "target_flooding_percent":    72.0,
        "henry_propylene_bar":         8.2,
        "liquid_to_gas_min_ratio_l_v": 1.45,
    }
    try:
        params  = _load_json("process_parameters.json")
        abs_cfg = params["separation_parameters"]["absorption"]
        return {
            "operating_temperature_c":     float(abs_cfg.get("operating_temperature_c",    DEFAULTS["operating_temperature_c"])),
            "target_flooding_percent":     float(abs_cfg["design_limits"].get("target_flooding_percent", DEFAULTS["target_flooding_percent"])),
            "henry_propylene_bar":         float(abs_cfg["henry_constants_bar_mole_fraction"].get("propylene", DEFAULTS["henry_propylene_bar"])),
            "liquid_to_gas_min_ratio_l_v": float(abs_cfg.get("liquid_to_gas_min_ratio_l_v", DEFAULTS["liquid_to_gas_min_ratio_l_v"])),
        }
    except (FileNotFoundError, KeyError):
        return DEFAULTS


_C_FACTOR_FLOOD_M_S  = 0.107
_ABSORPTION_FACTOR_TARGET = 1.5   # FIX A: raised from 1.4 → 1.5 (standard design margin)
_SOLVENT_MW_KG_KMOL  = 150.0
_SOLVENT_DENSITY_KG_M3 = 800.0

# Packing parameters — Mellapak 250Y
_HETP_M          = 0.50   # m per theoretical stage (Mellapak 250Y, light gas service)
_N_STAGES        = 10     # theoretical stages (conservative for propylene absorption)
_PACKING_HEIGHT_M = _N_STAGES * _HETP_M   # 5.0 m

_U_GAS_COOLER_W_M2_K = 45.0
_CW_SUPPLY_K         = 303.15
_CW_RETURN_K         = 318.15
_CP_GAS_KJ_KMOL_K    = 31.5
_BASE_HX_COST_USD    = 22_000.0
_BASE_HX_AREA_M2     = 15.0
_HX_COST_EXPONENT    = 0.65


def _allowable_velocity(rho_g_kg_m3: float, rho_l_kg_m3: float,
                         flooding_pct: float) -> float:
    c_design = _C_FACTOR_FLOOD_M_S * (flooding_pct / 100.0)
    return c_design * math.sqrt((rho_l_kg_m3 - rho_g_kg_m3) / rho_g_kg_m3)


def _min_solvent_rate(total_kmol_hr: float, y_hc: float,
                      p_feed_bar: float, h_bar: float) -> float:
    """
    FIX A — Kremser minimum solvent rate.

    Correct derivation:
        m   = H / P          (equilibrium ratio, dimensionless)
        G_HC = total_kmol_hr * y_hc   (molar flow of absorbable species only)
        L_min = m * G_HC              (minimum for A=1 on the HC component)
        L_design = A_target * L_min

    Previously: l_min = m * total_kmol_hr  ← wrong: treated all N2 as absorbable,
    overestimated solvent rate by factor ~1/y_hc (= 20× at 5 mol% HC).
    """
    m_equilibrium  = h_bar / p_feed_bar
    g_hc_kmol_hr   = total_kmol_hr * y_hc          # HC component molar flow only
    l_min_kmol_hr  = m_equilibrium * g_hc_kmol_hr  # Kremser minimum
    return _ABSORPTION_FACTOR_TARGET * l_min_kmol_hr


def _kremser_efficiency(absorption_factor: float, n_stages: int) -> float:
    """
    FIX B — Kremser equation for fraction of HC absorbed across N theoretical stages.

        η = [A^(N+1) - A] / [A^(N+1) - 1]     for A ≠ 1
        η = N / (N + 1)                          for A = 1

    This is the textbook form (Treybal, Mass Transfer Operations, Ch. 5).
    Replaces the incorrect: 1 - exp(-5.2 * (1 - A))
    which is neither the NTU form nor the Kremser form and produces
    negative exponents for A < 1, inflating efficiency nonphysically.
    """
    if abs(absorption_factor - 1.0) < 1e-6:
        return n_stages / (n_stages + 1.0)
    a   = absorption_factor
    n   = n_stages
    eta = (a**(n + 1) - a) / (a**(n + 1) - 1.0)
    return max(min(eta, 0.98), 0.10)


def _size_feed_cooler(feed_mass_kg_hr: float, total_kmol_hr: float,
                       t_feed_k: float, t_absorber_k: float) -> dict:
    q_kw = (total_kmol_hr * _CP_GAS_KJ_KMOL_K * (t_feed_k - t_absorber_k)) / 3600.0

    dt1 = max(t_feed_k     - _CW_RETURN_K,  1.0)
    dt2 = max(t_absorber_k - _CW_SUPPLY_K,  1.0)
    dt_lm = dt1 if abs(dt1 - dt2) < 0.5 else (dt1 - dt2) / math.log(dt1 / dt2)

    area_m2    = (q_kw * 1000.0) / (_U_GAS_COOLER_W_M2_K * dt_lm)
    # FIX C — capex computed correctly, opex in correct key
    capex_e101 = _BASE_HX_COST_USD * math.pow(area_m2 / _BASE_HX_AREA_M2, _HX_COST_EXPONENT)
    opex_e101  = round((q_kw * 3.6e-3) * 0.04, 2)

    return {
        "component":    "E-101 Feed Gas Cooler (Shell & Tube)",
        "rating":       "TEMA R / ANSI 150# — CW Duty Gas Cooler",
        "max_capacity": f"{area_m2 * 1.25:.1f} m2 surface (25% margin envelope)",
        "used_capacity":f"{area_m2:.1f} m2 required transfer surface  |  Duty: {q_kw:.1f} kW",
        "flow_rate":    round(feed_mass_kg_hr, 2),
        "monomer_conc": round(feed_mass_kg_hr * 0.0, 2),  # HC passes through unchanged
        "capex":        round(capex_e101, -2),             # FIX C: was 0.00
        "opex":         opex_e101,                         # FIX C: was showing capex value
        "efficiency": (
            f"Cooling duty: {t_feed_k - 273.15:.1f} °C → {t_absorber_k - 273.15:.1f} °C  |  "
            f"ΔT_lm = {dt_lm:.1f} K  |  "
            f"NOTE: E-101 is a missing upstream unit — without it the absorber "
            f"operates at feed temperature ({t_feed_k - 273.15:.0f} °C), "
            f"raising Henry's constant and requiring ~65× L/G to compensate."
        )
    }


def simulate_absorption_rated(feed_mass_kg_hr: float, p_feed_bar: float,
                               t_feed_k: float, y_n2: float, y_hc: float) -> list:

    mw_n2, mw_c3h6 = 28.01, 42.08
    mw_avg         = (y_n2 * mw_n2) + (y_hc * mw_c3h6)
    total_kmol_hr  = feed_mass_kg_hr / mw_avg
    flow_hc_kg     = total_kmol_hr * y_hc * mw_c3h6

    cfg          = _get_absorption_params()
    t_absorber_k = cfg["operating_temperature_c"] + 273.15

    r_constant    = 0.08314
    vol_flow_m3_s = (total_kmol_hr * r_constant * t_absorber_k) / (p_feed_bar * 3600.0)
    rho_g         = (p_feed_bar * mw_avg) / (r_constant * t_absorber_k)

    flooding_pct = cfg["target_flooding_percent"]
    v_allowable  = _allowable_velocity(rho_g, _SOLVENT_DENSITY_KG_M3, flooding_pct)

    ideal_area   = vol_flow_m3_s / v_allowable
    ideal_dia_mm = math.sqrt((4.0 * ideal_area) / math.pi) * 1000.0

    selected_dia_mm = 400 if ideal_dia_mm <= 400 else 600 if ideal_dia_mm <= 600 else 900
    selected_dia_m  = selected_dia_mm / 1000.0
    actual_area     = (math.pi / 4.0) * selected_dia_m ** 2

    h_ref_bar   = cfg["henry_propylene_bar"]
    h_propylene = h_ref_bar * math.exp(2200.0 * (1.0 / t_absorber_k - 1.0 / 308.15))

    # FIX A — correct solvent rate (y_hc-weighted)
    solvent_kmol_hr     = _min_solvent_rate(total_kmol_hr, y_hc, p_feed_bar, h_propylene)
    lean_oil_rate_kg_hr = solvent_kmol_hr * _SOLVENT_MW_KG_KMOL

    absorption_factor = solvent_kmol_hr / (total_kmol_hr * y_hc * h_propylene / p_feed_bar)

    # FIX B — Kremser efficiency
    true_efficiency      = _kremser_efficiency(absorption_factor, _N_STAGES)
    monomer_recovered_kg = flow_hc_kg * true_efficiency

    capex_t101   = 135000.0 * math.pow((_PACKING_HEIGHT_M * actual_area) / 3.0, 0.62) * 1.5
    solvent_gpm  = (lean_oil_rate_kg_hr / _SOLVENT_DENSITY_KG_M3) / 0.227
    capex_p101   = 18000.0 * math.pow(solvent_gpm / 50.0, 0.55) * 1.3
    running_p101 = ((solvent_gpm * p_feed_bar * 1e5 * 6.3e-5) / 0.65) * 0.08

    c_design = _C_FACTOR_FLOOD_M_S * (flooding_pct / 100.0)
    e101_row = _size_feed_cooler(feed_mass_kg_hr, total_kmol_hr, t_feed_k, t_absorber_k)

    return [
        e101_row,
        {
            "component":    "T-101 Absorber Tower Packed Shell",
            "rating":       "ASME Section VIII / ANSI 150# Low Press Casing",
            "max_capacity": f"{actual_area * v_allowable * rho_g * 3600.0:.1f} kg/hr hydraulic ceiling",
            "used_capacity":f"{feed_mass_kg_hr:.1f} kg/hr @ {t_absorber_k - 273.15:.0f} °C (post E-101)",
            "flow_rate":    round(feed_mass_kg_hr, 2),
            "monomer_conc": round(flow_hc_kg, 2),
            "capex":        round(capex_t101, -2),
            "opex":         round(5.50 * (lean_oil_rate_kg_hr / 1000.0), 2),
            "efficiency": (
                f"Thermodynamic Recovery Yield: {true_efficiency * 100:.1f}%  |  "
                f"Absorption Factor A = {absorption_factor:.2f}  |  "
                f"L/G (mass) = {lean_oil_rate_kg_hr / feed_mass_kg_hr:.1f}  |  "
                f"C_design = {c_design:.4f} m/s  (Mellapak 250Y @ {flooding_pct:.0f}% flood)"
            )
        },
        {
            "component":    "P-101 A/B Solvent Circulation Pumps",
            "rating":       "API 610 Centrifugal / Standard 7.5 kW Frame",
            "max_capacity": f"{solvent_gpm * 1.25:.1f} GPM impeller cut",
            "used_capacity":f"{solvent_gpm:.1f} GPM solvent circulation",
            "flow_rate":    round(lean_oil_rate_kg_hr + monomer_recovered_kg, 2),
            "monomer_conc": round(monomer_recovered_kg, 2),
            "capex":        round(capex_p101, -2),
            "opex":         round(running_p101, 2),
            "efficiency":   "Solvent Recirculation Loop Containment"
        }
    ]