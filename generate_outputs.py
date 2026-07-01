import subprocess
import os
import sys  # <--- Make sure this is imported

def build_entire_project():
    # Use sys.executable instead of the literal string "python"
    current_interpreter = sys.executable 

    print("🚀 Step 1: Running Industrial Thermodynamic & Sizing Math Engines...")
    subprocess.run([current_interpreter, "generate_report_data.py"], check=True)
    
    print("\n📊 Step 2: Extracting Calculations into PDF Report Asset...")
    if os.path.exists("generate_pdf.py"):
        # This forces the script to run using your exact same virtual environment context
        subprocess.run([current_interpreter, "generate_pdf.py"], check=True)
        print("➡️ [SUCCESS] PDF Report generated inside outputs/ folder.")
    else:
        print("⚠️ generate_pdf.py script not found.")

    print("\n🖥️ Step 3: Pushing Parameters to Node.js Presentation Engine...")
    try:
        subprocess.run(["node", "generate_ppt.js"], check=True)
        print("➡️ [SUCCESS] PowerPoint Slides generated inside outputs/ folder.")
    except Exception as e:
        print("⚠️ Node.js presentation builder encountered an error.")

if __name__ == "__main__":
    build_entire_project()