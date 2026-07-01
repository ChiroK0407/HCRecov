from sizing_engines.membrane_engine import simulate_membrane_rated
from sizing_engines.adsorption_engine import simulate_adsorption_rated
from sizing_engines.absorption_engine import simulate_absorption_rated

def print_standard_ledger_table(tech_title: str, components_list: list):
    print(f"\n🚀 FIRST-PRINCIPLES PERFORMANCE LEDGER: {tech_title.upper()}")
    print("=" * 165)
    header_format = " | {:<38} | {:<32} | {:<28} | {:<28} | {:<12} | {:<12} | {:<12} | {:<10} |"
    row_format = " | {:<38} | {:<32} | {:<28} | {:<28} | {:<12,.2f} | {:<12,.2f} | ₹{:<11,.2f} | ₹{:<9,.2f} |"
    
    print(header_format.format(
        "Industrial Component Name", "Mechanical Rating Specification", 
        "Maximum Capacity Envelope", "Used Operating Metric", 
        "Flow (kg/hr)", "Monomer (kg)", "CAPEX (INR)", "OPEX (₹/hr)"
    ))
    print("-" * 165)
    
    for row in components_list:
        print(row_format.format(
            row["component"], row["rating"], row["max_capacity"], row["used_capacity"],
            row["flow_rate"], row["monomer_conc"], row["capex"], row["opex"]
        ))
        print(f"   -> Nozzle Transfer Vector Kinetics Tracking: {row['efficiency']}")
        print(" " + "-" * 161)
    print("=" * 165)

def main():
    # Exact raw plant input metrics provided by user
    feed_mass_kg_hr = 650.0    # 650 kg/hr mass flow profile
    p_feed_bar = 1.2           # 0.2 kg/cm2 (g) converted directly to bar absolute bounds
    t_feed_k = 337.15          # 64 °C converted to Kelvin temperature vector
    
    # Purge vent gas component properties fractions (95 mol% N2, 5 mol% Monomer)
    y_n2 = 0.95
    y_hc = 0.05

    print("=" * 165)
    print("      STEADY-STATE MATERIAL RATING LOG - ACTUAL FLUID SPECIES PROFILE RUN")
    print("=" * 165)
    print(f" Boundary Variables: Feed flowrate = {feed_mass_kg_hr:.1f} kg/hr | Pressure Envelope = {p_feed_bar:.2f} bar(a) | Temperature = {t_feed_k - 273.15:.1f} °C")
    
    # Execute non-ideal process evaluation passes
    membrane_rows = simulate_membrane_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc)
    print_standard_ledger_table("Hollow Fiber Polymeric Membrane Skid System", membrane_rows)
    
    adsorption_rows = simulate_adsorption_rated(feed_mass_kg_hr, p_feed_bar, y_n2, y_hc)
    print_standard_ledger_table("Twin-Bed Cyclic Pressure Swing Adsorption Skid", adsorption_rows)
    
    absorption_rows = simulate_absorption_rated(feed_mass_kg_hr, p_feed_bar, t_feed_k, y_n2, y_hc)
    print_standard_ledger_table("Heavy Hydrocarbon Gas Absorption Recirculation Loop", absorption_rows)

if __name__ == "__main__":
    main()