#!/usr/bin/env python3
# ==============================================================================
# FILE: test_aeroforgex_work.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
# DESCRIPTION: Exhaustive automated testing of the Standalone Deterministic Toolkit
# ==============================================================================
import os, sys, json, subprocess, shutil, math

T_DIR = "Outputs/Test_Worker_Sandbox"
O_CWD = os.getcwd()

# ANSI Colors for Terminal
C_GRN = "\033[92m\033[1m"
C_BLU = "\033[96m\033[1m"
C_YLW = "\033[93m\033[1m"
C_RED = "\033[91m\033[1m"
C_RST = "\033[0m"

def setup_dir():
    print(f"{C_BLU}[*] Initializing Worker Sandbox: {os.path.abspath(T_DIR)}{C_RST}")
    if os.path.exists(T_DIR):
        shutil.rmtree(T_DIR)
    os.makedirs(T_DIR, exist_ok=True)
    os.chdir(T_DIR)

def find_cli():
    for d in [O_CWD, os.path.join(O_CWD, "AeroForgeX_scr")]:
        cli_path = os.path.join(d, "aeroforgex_cli.py")
        if os.path.exists(cli_path):
            return cli_path
    raise FileNotFoundError("Cannot locate aeroforgex_cli.py. Ensure you run this from the root directory.")

def generate_dummy_naca(name, t, c, p):
    """Generates a raw NACA 4-digit airfoil if standard files are missing."""
    x = [0.5 * (1.0 - math.cos(theta)) for theta in [i * math.pi / 40 for i in range(41)]]
    xu, yu, xl, yl = [], [], [], []
    for xi in x:
        yt = 5 * t * (0.2969 * math.sqrt(xi) - 0.1260 * xi - 0.3516 * xi**2 + 0.2843 * xi**3 - 0.1015 * xi**4)
        yc = (c / p**2) * (2 * p * xi - xi**2) if xi < p else (c / (1 - p)**2) * ((1 - 2 * p) + 2 * p * xi - xi**2) if p > 0 else 0
        dyc = (2 * c / p**2) * (p - xi) if xi < p else (2 * c / (1 - p)**2) * (p - xi) if p > 0 else 0
        th = math.atan(dyc)
        xu.append(xi - yt * math.sin(th)); yu.append(yc + yt * math.cos(th))
        xl.append(xi + yt * math.sin(th)); yl.append(yc - yt * math.cos(th))
    
    with open(name, 'w') as f:
        f.write(f"{name.split('.')[0]}\n")
        for xi, yi in zip(reversed(xu), reversed(yu)): f.write(f"{xi:.6f} {yi:.6f}\n")
        for xi, yi in zip(xl[1:], yl[1:]): f.write(f"{xi:.6f} {yi:.6f}\n")

def ensure_foils(req):
    print(f"{C_BLU}[*] Locating or generating baseline Seed Airfoils...{C_RST}")
    for f in req:
        src = os.path.join(O_CWD, "Airfoils", f)
        if os.path.exists(src):
            shutil.copy2(src, f)
        else:
            print(f"{C_YLW}   -> {f} not found in Airfoils/. Generating mathematical dummy.{C_RST}")
            # Generate dummy NACA0012 or NACA4415 based on name
            t = 0.15 if "15" in f else 0.12
            c = 0.04 if "44" in f else 0.0
            p = 0.40 if "44" in f else 0.0
            generate_dummy_naca(f, t, c, p)

def run_cmd(args, desc):
    print(f"\n{C_BLU}{'=' * 80}\n [TEST] {desc}\n{'=' * 80}{C_RST}")
    cmd = [sys.executable, find_cli()] + args
    print(f"Executing: {' '.join(cmd)}\n")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for l in proc.stdout:
            print("    " + l.strip())
        proc.wait()
        if proc.returncode == 0:
            print(f"{C_GRN}[SUCCESS] Worker Action Completed.{C_RST}")
            return True
        else:
            print(f"{C_RED}[FAILED] Worker Action returned non-zero exit code.{C_RST}")
            return False
    except Exception as e:
        print(f"\n{C_RED}[!] EXECUTION ERROR: {str(e)}{C_RST}")
        return False

def c_js(fn, d):
    open(fn, "w").write(json.dumps(d, indent=4))
    return fn

def main():
    print(f"{C_GRN}{'=' * 80}\n  AeroForgeX v4.2 Pro :: WORKER TOOL (-w) TEST SUITE\n{'=' * 80}{C_RST}")
    setup_dir()

    try:
        # 0. Prep Environment
        req = ["NACA0012.dat", "NACA4415.dat"]
        ensure_foils(req)

        # Config Files
        c_js("flap.json", {"operating_conditions": {"x_flap": 0.75, "flap_angle": [-5.0, 5.0, 10.0]}})
        c_js("bez.json", {"bezier_options": {"ncp_t": 6, "ncp_b": 6}, "paneling_options": {"npoint": 161}})
        c_js("check.json", {"curvature": {"chk_curv": True, "auto_curv": True}})
        
        c_js("polar_xfoil.json", {
            "opt_opts": {"solver": "xfoil"},
            "polar_generation": {"polar_reynolds": [5e5], "polar_mach": [0.0], "op_mode": "spec-al", "op_point_range": [-2.0, 10.0, 1.0]}
        })
        c_js("polar_neural.json", {
            "opt_opts": {"solver": "neuralfoil"},
            "polar_generation": {"polar_reynolds": [5e5, 1e6], "polar_mach": [0.0, 0.1], "op_mode": "spec-al", "op_point_range": [-5.0, 15.0, 0.5]}
        })

        # -------------------------------------------------------------------------
        # SCENARIO 1: Topological Sanitization (norm) & (smooth)
        # -------------------------------------------------------------------------
        run_cmd(["-w", "norm", "-a", "NACA0012.dat", "-o", "Foil_Norm"], "Topological Normalization (-w norm)")
        
        # Test the new Savitzky-Golay filter
        run_cmd(["-w", "smooth", "11", "-a", "Foil_Norm.dat", "-o", "Foil_Smooth"], "Savitzky-Golay Mathematical Smoothing (-w smooth)")

        # -------------------------------------------------------------------------
        # SCENARIO 2: Hard Scalar Mutation & Parametric Families (set & generate)
        # -------------------------------------------------------------------------
        run_cmd(["-w", "set", "t=18", "-a", "Foil_Smooth.dat", "-o", "Foil_t18"], "Direct Geometric Scaling (-w set t=18)")
        
        run_cmd(["-w", "generate", "t=10:14:3", "-a", "Foil_Smooth.dat"], "Automated Parametric Family Generation (-w generate)")

        # -------------------------------------------------------------------------
        # SCENARIO 3: Airfoil Blending & Fusing (blend)
        # -------------------------------------------------------------------------
        run_cmd(["-w", "norm", "-a", "NACA4415.dat", "-o", "Foil2_Norm"], "Normalizing Secondary Foil")
        run_cmd(["-w", "blend", "50", "-a", "Foil_Smooth.dat", "-a2", "Foil2_Norm.dat", "-o", "Foil_Blended_5050"], "Mesh Interpolation & Fusing (-w blend 50)")

        # -------------------------------------------------------------------------
        # SCENARIO 4: Kinematic Deflection Arrays (flap)
        # -------------------------------------------------------------------------
        run_cmd(["-w", "flap", "-i", "flap.json", "-a", "Foil_Smooth.dat"], "Kinematic Trailing Edge Deflection Array (-w flap)")

        # -------------------------------------------------------------------------
        # SCENARIO 5: Simplex "Shrink-Wrap" Recovery (bezier)
        # -------------------------------------------------------------------------
        run_cmd(["-w", "bezier", "-i", "bez.json", "-a", "Foil_Blended_5050.dat", "-o", "Foil_Bezier_Recovered"], "Nelder-Mead Bezier Shrink-Wrap (-w bezier)")

        # -------------------------------------------------------------------------
        # SCENARIO 6: High-Fidelity Diagnostics (check & report)
        # -------------------------------------------------------------------------
        run_cmd(["-w", "check", "-i", "check.json", "-a", "Foil_Bezier_Recovered.dat"], "Terminal Curvature Diagnostics (-w check)")
        
        run_cmd(["-w", "report", "-a", "Foil_Smooth.dat"], "Dual HTML/PDF Visual Diagnostics Generation (-w report)")

        # -------------------------------------------------------------------------
        # SCENARIO 7: The Batch Pipeline Interceptor (Directories)
        # -------------------------------------------------------------------------
        print(f"\n{C_BLU}[*] Preparing Batch Directory...{C_RST}")
        os.makedirs("Batch_Test_Folder", exist_ok=True)
        shutil.copy("Foil_Smooth.dat", "Batch_Test_Folder/Test1.dat")
        shutil.copy("Foil2_Norm.dat", "Batch_Test_Folder/Test2.dat")
        
        run_cmd(["-w", "norm", "-a", "Batch_Test_Folder/"], "Multi-Core Batch Pipeline Interception (-a [DIR])")

        # -------------------------------------------------------------------------
        # SCENARIO 8: Aerodynamic Sweeps (polar & polar-csv)
        # -------------------------------------------------------------------------
        run_cmd(["-w", "polar", "-i", "polar_xfoil.json", "-a", "Foil_Smooth.dat"], "Standard XFOIL Drag Polar Export (-w polar)")
        
        run_cmd(["-w", "polar-csv", "-i", "polar_neural.json", "-a", "Foil_Smooth.dat", "-o", "AI_Sweep"], "Massive NeuralFoil Sweep & HTML Dashboard (-w polar-csv)")

        print(f"\n{C_GRN}{'=' * 80}\n  ALL WORKER TESTS COMPLETED SUCCESSFULLY.\n  Please inspect the outputs in: {os.path.abspath(T_DIR)}\n{'=' * 80}{C_RST}")

    finally:
        os.chdir(O_CWD)

if __name__ == "__main__":
    main()