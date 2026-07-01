import json
import math
import warnings
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str) -> dict:
    with open(_DATA_DIR / filename, "r") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# FIX 3 — Read cycle time from JSON; clamp to physically realistic range
# ---------------------------------------------------------------------------
# Propylene / C3 PSA literature: commercial cycles run 5–15 min.
# An 8-hour (480 min) value in the JSON is almost certainly a data-entry error
# (minutes confused with seconds, or a placeholder). We clamp at 15 min and
# emit a visible warning so the reviewer can correct the source file.
_CYCLE_TIME_MIN_FLOOR   =  5.0   # below this → too fast, bed not loaded
_CYCLE_TIME_MIN_CEILING = 15.0   # above this → unphysical for C3 PSA; clamp & warn

def _get_cycle_params() -> tuple[float, float]:
    """
    Returns (cycle_time_min, feed_step_fraction) read from process_parameters.json.

    cycle_time_min     — total PSA cycle duration (all steps), clamped to
                         [_CYCLE_TIME_MIN_FLOOR, _CYCLE_TIME_MIN_CEILING].
    feed_step_fraction — fraction of cycle time spent in the adsorption/feed
                         step.  Falls back to 0.40 if not present in JSON
                         (pressurisation ≈15%, feed ≈40%, blowdown ≈25%,
                          purge ≈20% is a representative 4-step split).
    """
    FALLBACK_CYCLE_MIN      = 10.0
    FALLBACK_FEED_FRACTION  =  0.40

    try:
        params   = _load_json("process_parameters.json")
        psa_cfg  = params["separation_parameters"]["adsorption_psa"]
        raw_cycle_min = float(psa_cfg["cycle_time_minutes"])
    except (FileNotFoundError, KeyError, TypeError):
        raw_cycle_min = FALLBACK_CYCLE_MIN

    # --- clamp and warn ---
    if raw_cycle_min > _CYCLE_TIME_MIN_CEILING:
        warnings.warn(
            f"[adsorption_engine] cycle_time_minutes = {raw_cycle_min:.0f} min read from "
            f"process_parameters.json exceeds the realistic ceiling of "
            f"{_CYCLE_TIME_MIN_CEILING:.0f} min for a propylene PSA.  "
            f"Value has been clamped to {_CYCLE_TIME_MIN_CEILING:.0f} min for sizing. "
            f"Please verify the source JSON (minutes vs seconds confusion is common).",
            UserWarning,
            stacklevel=3,
        )
        cycle_time_min = _CYCLE_TIME_MIN_CEILING
    elif raw_cycle_min < _CYCLE_TIME_MIN_FLOOR:
        warnings.warn(
            f"[adsorption_engine] cycle_time_minutes = {raw_cycle_min:.1f} min is below "
            f"the minimum floor of {_CYCLE_TIME_MIN_FLOOR:.0f} min. "
            f"Clamped to {_CYCLE_TIME_MIN_FLOOR:.0f} min.",
            UserWarning,
            stacklevel=3,
        )
        cycle_time_min = _CYCLE_TIME_MIN_FLOOR
    else:
        cycle_time_min = raw_cycle_min

    # FIX 1 — Read feed_step_fraction if present, otherwise use 4-step default
    try:
        feed_step_fraction = float(psa_cfg["feed_step_fraction"])
        feed_step_fraction = max(0.10, min(feed_step_fraction, 0.70))  # sanity bounds
    except (KeyError, NameError, TypeError):
        feed_step_fraction = FALLBACK_FEED_FRACTION

    return cycle_time_min, feed_step_fraction


# ---------------------------------------------------------------------------
# FIX 2 — Guard filter CAPEX sized on actual volumetric flow, not molar flow
# ---------------------------------------------------------------------------
# Cartridge-housing filters are selected by face velocity / volumetric throughput.
# A standard duplex housing handling ~500 m³/hr actual gas costs ~USD 18 000.
# We scale from that anchor with a 0.45 exponent (relatively flat — housings snap
# to discrete sizes and cost is dominated by the pressure-rated shell).
_FILTER_BASE_COST_USD  = 18_000.0   # anchor CAPEX
_FILTER_BASE_FLOW_M3HR =    500.0   # anchor volumetric flow at actual conditions
_FILTER_COST_EXPONENT  =      0.45  # cartridge housing cost exponent

def _guard_filter_capex(total_kmol_hr: float, p_feed_bar: float, t_feed_k: float,
                         mw_avg: float) -> float:
    """
    Size the Y-201 duplex cartridge guard filter by actual volumetric gas flow
    (m³/hr at feed conditions) rather than molar flow.

    Ideal gas:  V̇ = ṅ · R · T / P
    """
    R_BAR_M3_KMOL_K = 0.08314   # bar·m³/(kmol·K)
    vol_flow_m3_hr  = (total_kmol_hr * R_BAR_M3_KMOL_K * t_feed_k) / p_feed_bar

    capex = _FILTER_BASE_COST_USD * math.pow(
        vol_flow_m3_hr / _FILTER_BASE_FLOW_M3HR, _FILTER_COST_EXPONENT
    )
    return capex


# ---------------------------------------------------------------------------
# Main engine entry point
# ---------------------------------------------------------------------------
def simulate_adsorption_rated(feed_mass_kg_hr: float, p_feed_bar: float,
                               y_n2: float, y_hc: float,
                               t_feed_k: float = 337.15) -> list:
    """
    t_feed_k is needed for volumetric flow in the guard filter sizing.
    Defaults to 337.15 K (64 °C) — the plant design point — so existing
    callers that don't pass temperature remain backward-compatible.
    """
    mw_n2, mw_propylene = 28.01, 42.08
    mw_avg        = (y_n2 * mw_n2) + (y_hc * mw_propylene)
    total_kmol_hr = feed_mass_kg_hr / mw_avg
    flow_hc_kg    = total_kmol_hr * y_hc * mw_propylene

    # ------------------------------------------------------------------
    # FIX 3 + FIX 1 — Cycle time (clamped) and feed-step fraction (from JSON)
    # ------------------------------------------------------------------
    cycle_time_min, feed_step_fraction = _get_cycle_params()
    cycle_time_hr = cycle_time_min / 60.0

    # ------------------------------------------------------------------
    # Extended Langmuir competitive isotherm
    # ------------------------------------------------------------------
    p_partial_hc    = p_feed_bar * y_hc
    bed_loading_mol_kg = (4.65 * 2.25 * p_partial_hc) / (
        1.0 + 2.25 * p_partial_hc + 0.045 * (p_feed_bar * y_n2)
    )
    bed_loading_mol_kg = max(bed_loading_mol_kg, 0.05)

    # ------------------------------------------------------------------
    # FIX 1 — Replace hardcoded 0.5 with feed_step_fraction read from JSON
    #
    # moles_captured_per_cycle = molar HC flow × feed step duration (hr)
    #   feed step duration = cycle_time_hr × feed_step_fraction
    # × 1000 converts kmol → mol to match bed_loading_mol_kg units
    # ------------------------------------------------------------------
    feed_step_hr            = cycle_time_hr * feed_step_fraction
    moles_captured_per_cycle = (total_kmol_hr * y_hc * feed_step_hr) * 1000.0
    ideal_adsorbent_mass_kg = moles_captured_per_cycle / bed_loading_mol_kg

    # Standard catalog vessel matching (unchanged logic)
    vessel_vol           = (ideal_adsorbent_mass_kg / 510.0) * 2.0
    actual_cross_section = vessel_vol / 3.2
    ideal_dia_mm         = math.sqrt((4.0 * actual_cross_section) / math.pi) * 1000.0

    selected_dia_mm = 600 if ideal_dia_mm <= 600 else 900 if ideal_dia_mm <= 900 else 1200
    selected_dia_m  = selected_dia_mm / 1000.0
    actual_area     = (math.pi / 4.0) * math.pow(selected_dia_m, 2)

    standard_volume          = actual_area * 3.2
    standard_mass_capacity_kg = (standard_volume / 2.0) * 510.0

    net_recovery_factor  = min(0.94 * (standard_mass_capacity_kg / ideal_adsorbent_mass_kg), 0.985)
    monomer_adsorbed_kg  = flow_hc_kg * net_recovery_factor

    # ------------------------------------------------------------------
    # FIX 2 — Guard filter CAPEX from volumetric flow, not molar flow
    # ------------------------------------------------------------------
    capex_y201 = _guard_filter_capex(total_kmol_hr, p_feed_bar, t_feed_k, mw_avg)
    capex_v201 = 92000.0 * math.pow((standard_volume / 4.0), 0.58) * 1.4

    # Volumetric flow for display in the filter rating string
    R_BAR    = 0.08314
    vol_flow = (total_kmol_hr * R_BAR * t_feed_k) / p_feed_bar   # m³/hr actual

    return [
        {
            "component": "Y-201 Duplex Guard Cartridge Element",
            "rating": "ASME Housing / 0.5 Micron Particulate Strainer",
            "max_capacity": f"{vol_flow * 1.4:.1f} m3/hr hydraulic ceiling",
            "used_capacity": f"{vol_flow:.1f} m3/hr actual volumetric flow",
            "flow_rate":    round(feed_mass_kg_hr, 2),
            "monomer_conc": round(flow_hc_kg, 2),
            "capex":  round(capex_y201, -2),
            "opex":   0.45,
            "efficiency": "99.95% Resin Fines Separation Guard"
        },
        {
            "component": "V-201 A/B Twin Swing Adsorber Steel Shells",
            "rating": "ASME Section VIII / ANSI 150# Rating Vessel Frame",
            "max_capacity": f"{standard_mass_capacity_kg:.1f} kg standard loading frame",
            "used_capacity": f"{ideal_adsorbent_mass_kg:.1f} kg required sieve mass",
            "flow_rate":    round(monomer_adsorbed_kg, 2),
            "monomer_conc": round(monomer_adsorbed_kg, 2),
            "capex":  round(capex_v201, -2),
            "opex":   3.50,
            "efficiency": (
                f"Langmuir Pore Vapor Equilibrium Affinity: {net_recovery_factor * 100:.1f}%  |  "
                f"Cycle: {cycle_time_min:.0f} min total / feed step {feed_step_fraction * 100:.0f}% "
                f"({feed_step_hr * 60:.1f} min)"
            )
        }
    ]