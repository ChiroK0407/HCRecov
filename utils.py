"""
utils.py — Shared thermodynamic helpers for HCRecov Streamlit App
---------------------------------------------------------------------
Provides:
  - load_params()        : load process_parameters.json once
  - load_components()    : load components.json once
  - antoine_p_sat_bar()  : Antoine vapour-pressure (log10 form, result in bar)
  - dew_point_check()    : checks whether a component condenses at given T, P, y
  - get_selected_params(): fetch parameters for chosen material/adsorbent/solvent
"""

import json
import math
from pathlib import Path

# Data directory — keep JSON files in ./data/
_DATA_DIR = Path(__file__).parent / "data"


def load_params() -> dict:
    """Load separation parameters JSON."""
    with open(_DATA_DIR / "process_parameters.json") as f:
        return json.load(f)["separation_parameters"]


def load_components() -> dict:
    """Load components JSON."""
    with open(_DATA_DIR / "components.json") as f:
        return json.load(f)["components"]


def antoine_p_sat_bar(component_data: dict, t_k: float) -> float | None:
    """Antoine vapour-pressure (log10 form, result in bar)."""
    a = component_data["antoine_coefficients"]
    t_min = a["temp_min_k"]
    t_max = a["temp_max_k"]
    tc = component_data.get("critical_temperature_k", float("inf"))

    if not (t_min <= t_k <= t_max) or (tc - t_k) < 5.0:
        return None

    t_c = t_k - 273.15
    denominator = t_c + a["C"]
    if abs(denominator) < 1e-9:
        return None
    log_p_mmhg = a["A"] - a["B"] / denominator
    p_mmhg = 10.0 ** log_p_mmhg
    return p_mmhg * 133.322e-6  # convert mmHg → bar


def dew_point_check(
    component_name: str,
    component_data: dict,
    y_i: float,
    p_total_bar: float,
    t_k: float
) -> dict:
    """Check whether a component condenses at given T, P, y."""
    p_partial = y_i * p_total_bar
    nbp_k = component_data.get("normal_boiling_point_k", 0.0)
    tc_k = component_data.get("critical_temperature_k", float("inf"))

    if t_k >= tc_k:
        note = (
            f"✅ {component_name}: T={t_k-273.15:.1f}°C ≥ Tc={tc_k-273.15:.1f}°C — "
            f"supercritical, no condensation possible."
        )
        return {"p_partial_bar": p_partial, "p_sat_bar": None, "condenses": False, "note": note}

    if nbp_k > 0 and t_k > (nbp_k + 20.0):
        note = (
            f"✅ {component_name}: T={t_k-273.15:.1f}°C >> NBP={nbp_k-273.15:.1f}°C — "
            f"superheated vapour at stream pressure, no condensation risk."
        )
        return {"p_partial_bar": p_partial, "p_sat_bar": None, "condenses": False, "note": note}

    p_sat = antoine_p_sat_bar(component_data, t_k)

    if p_sat is None:
        note = (
            f"ℹ️  {component_name}: Antoine equation out of calibrated range at "
            f"T={t_k-273.15:.1f}°C — vapour assumed."
        )
        return {"p_partial_bar": p_partial, "p_sat_bar": None, "condenses": False, "note": note}

    condenses = p_partial >= p_sat
    margin = p_sat - p_partial
    if condenses:
        note = (
            f"⚠️  {component_name} CONDENSATION RISK: "
            f"P_partial={p_partial:.4f} bar ≥ P_sat={p_sat:.4f} bar at {t_k-273.15:.1f}°C."
        )
    else:
        note = (
            f"✅ {component_name}: remains vapour at {t_k-273.15:.1f}°C. "
            f"Safety margin = {margin:.4f} bar."
        )
    return {"p_partial_bar": p_partial, "p_sat_bar": p_sat, "condenses": condenses, "note": note}


def get_selected_params(section: str, key: str) -> dict:
    """
    Return the chosen material/adsorbent/solvent parameter dict from
    process_parameters.json.

    Args:
        section : "membrane" | "adsorption_psa" | "absorption"
        key     : the name string matching the "name" field in the JSON list

    Returns:
        dict of parameters for the selected option.

    Raises:
        ValueError : if section is unrecognised
        StopIteration : if no item matches key (name mismatch)
    """
    params = load_params()   # already returns separation_parameters dict

    list_key_map = {
        "membrane":       "materials",
        "adsorption_psa": "adsorbents",
        "absorption":     "solvents",
    }
    if section not in list_key_map:
        raise ValueError(f"Unknown section: '{section}'. Expected one of {list(list_key_map)}")

    options = params[section][list_key_map[section]]
    chosen = next((item for item in options if item["name"] == key), None)

    if chosen is None:
        available = [item["name"] for item in options]
        raise ValueError(f"Material '{key}' not found in '{section}'. Available: {available}")

    return chosen