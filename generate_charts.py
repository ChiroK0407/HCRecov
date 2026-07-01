import matplotlib.pyplot as plt
import numpy as np

# Set standard crisp plotting aesthetics for engineering decks
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig_color_primary = '#1e3a8a'  # Industrial Dark Blue
fig_color_secondary = '#b91c1c' # Alert Red
fig_color_accent = '#047857'    # Success Emerald Green

def generate_performance_plots():
    technologies = ['Polymeric Membrane\n(Skid Package)', 'Pressure Swing Adsorption\n(Twin-Bed Sieve)', 'Heavy Gas Absorption\n(Recirculation Loop)']
    
    # 1. Real calculated separation efficiencies under low-pressure boundary penalties
    efficiencies = [95.8, 81.1, 98.0]
    
    plt.figure(figsize=(9, 5))
    bars = plt.bar(technologies, efficiencies, color=[fig_color_primary, fig_color_secondary, fig_color_accent], width=0.5, edgecolor='black', linewidth=1)
    
    # Draw strict industrial lower boundary target baseline (e.g., 90% expected threshold cut)
    plt.axhline(y=90.0, color='red', linestyle='--', linewidth=1.5, label='Minimum Plant Target Recovery (90%)')
    
    # Formatting details
    plt.title('Packaged Skid Net Separation Efficiency ($\eta_{global}$)\n[Feed Conditions: 1.20 bar(a) @ 64.0°C]', fontsize=12, fontweight='bold', pad=15)
    plt.ylabel('Monomer Recovery Efficiency (%)', fontsize=11, fontweight='bold')
    plt.ylim(0, 115)
    
    # Data label annotations loop
    for bar in bars:
        height = bar.get_height()
        label_text = f"{height:.1f}%"
        # Flag the adsorption shortfall visibly
        if height < 90.0:
            label_text += " ❌ [OVERLOAD]"
        plt.text(bar.get_x() + bar.get_width()/2.0, height + 2, label_text, ha='center', va='bottom', fontsize=10, fontweight='bold')
        
    plt.legend(loc='lower left')
    plt.tight_layout()
    plt.savefig('separation_efficiency.png', dpi=300)
    print("✅ Successfully generated and saved chart: 'separation_efficiency.png'")
    plt.close()

    # 2. Total Itemized Skid CAPEX (INR) comparison
    # Membrane: Compressor (₹14.4L) + Skid modules (₹50.5L) = ₹64.9L
    # PSA Adsorption: Guard filter (₹1.0L) + Vessels (₹10.1L) = ₹11.1L
    # Gas Absorption: Tower (₹10.8L) + Circulation Pumps (₹1.1L) = ₹11.9L
    capex_values = [777700.0 * 83.5, 133400.0 * 83.5, 143000.0 * 83.5]
    
    plt.figure(figsize=(9, 5))
    bars_capex = plt.bar(technologies, [val/1000 for val in capex_values], color=[fig_color_primary, fig_color_secondary, fig_color_accent], width=0.5, edgecolor='black', linewidth=1)
    
    plt.title('Total Package Installed Capital Expenditure (CAPEX)\n[Standard Catalog Snapped Equipment Assets]', fontsize=12, fontweight='bold', pad=15)
    plt.ylabel('Capital Expenditures (₹ Lakhs)', fontsize=11, fontweight='bold')
    plt.ylim(0, max(capex_values)/1000 * 1.2)
    
    for bar in bars_capex:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, height + 15, f"₹{height/100000:,.1f}L", ha='center', va='bottom', fontsize=10, fontweight='bold')
        
    plt.tight_layout()
    plt.savefig('skid_capex.png', dpi=300)
    print("✅ Successfully generated and saved chart: 'skid_capex.png'")
    plt.close()

if __name__ == "__main__":
    generate_performance_plots()