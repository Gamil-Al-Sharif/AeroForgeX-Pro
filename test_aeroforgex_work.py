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
import os, sys, json, subprocess, shutil

T_DIR, O_CWD = "test_aeroforgex_work", os.getcwd()


def setup_dir():
    print(f"[*] Using worker sandbox: ./{T_DIR}/")
    os.makedirs(T_DIR, exist_ok=True)
    os.chdir(T_DIR)


def find_cli():
    for d in [O_CWD, os.path.join(O_CWD, ".."), os.path.join(O_CWD, "AeroForgeX_scr")]:
        if os.path.exists(os.path.join(d, "aeroforgex_cli.py")):
            return os.path.join(d, "aeroforgex_cli.py")
    raise FileNotFoundError("Cannot locate aeroforgex_cli.py")


def get_foils(req):
    m = [
        f
        for f in req
        if not os.path.exists(f)
        and not (
            os.path.exists(os.path.join(O_CWD, f))
            and shutil.copy2(os.path.join(O_CWD, f), f)
        )
    ]
    if m:
        sys.exit(print(f"[!] ERROR: Required foils missing: {m}"))


def run_cmd(args, desc):
    print(f"\n{'=' * 80}\n [+] EXECUTING: {desc}\n{'=' * 80}")
    cmd = [sys.executable, find_cli()] + args
    print(f"CMD: {' '.join(cmd)}\n")
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for l in proc.stdout:
            print("    " + l.strip())
        proc.wait()
        return proc.returncode == 0
    except Exception as e:
        print(f"\n[!] EXECUTION ERROR: {str(e)}")
        return False


def c_js(fn, d):
    open(fn, "w").write(json.dumps(d, indent=4))
    return fn


def main():
    print("=" * 80 + "\n   AeroForgeX v3.0 :: WORKER TOOL (-w) TEST SUITE\n" + "=" * 80)
    setup_dir()

    try:
        req = ["RG15.dat", "MH32.dat", "MH43.dat"]
        get_foils(req)

        c_js(
            "flap.json",
            {
                "operating_conditions": {
                    "x_flap": 0.75,
                    "flap_angle": [2.0, 4.0, 6.0, 8.0, 10.0],
                }
            },
        )
        c_js(
            "bez.json",
            {"bez_opts": {"ncp_t": 5, "ncp_b": 5}, "panel_opts": {"npt": 161}},
        )
        c_js(
            "px.json",
            {
                "polar_generation": {
                    "polar_reynolds": [5e4, 1e5],
                    "type_of_polar": 1,
                    "op_mode": "spec-al",
                    "op_point_range": [-2.0, 8.0, 0.5],
                },
                "op_conds": {"x_flap": 0.75, "flap_ang": [-1.0, 0.0, 2.0]},
            },
        )
        c_js(
            "pc.json",
            {
                "polar_generation": {
                    "polar_reynolds": [4e5, 8e5],
                    "polar_mach": [0.0, 0.2],
                    "op_mode": "spec-al",
                    "op_point_range": [-2.0, 8.0, 0.5],
                }
            },
        )
        c_js(
            "polars_neural.json",
            {
                "opt_opts": {"solver": "neuralfoil"},
                "polar_generation": {
                    "polar_reynolds": [4e5, 8e5],
                    "polar_mach": [0.0, 0.2],
                    "op_mode": "spec-al",
                    "op_point_range": [-2.0, 8.0, 0.5],
                },
            },
        )
        print("\n\n>>> SCENARIO 1: Batch Normalization")
        for f in req:
            out = f.replace(".dat", "_norm.dat")
            run_cmd(["-w", "norm", "-a", f, "-o", out], f"Normalizing {f}")
            if os.path.exists(out + ".dat"):
                shutil.move(out + ".dat", out)

        print("\n\n>>> SCENARIO 2: Multi-Angle Flap Generation")
        if not os.path.exists("RG15_norm.dat"):
            return print("[!] RG15_norm.dat missing.")
        run_cmd(
            ["-w", "flap", "-i", "flap.json", "-a", "RG15_norm.dat"],
            "Generating 5 flapped variants",
        )

        print("\n\n>>> SCENARIO 3: Direct Geometry Scaling")
        [
            shutil.copy("RG15_norm.dat", f"RG15_{s}.dat")
            for s in ["thick", "camber", "te"]
        ]
        run_cmd(
            ["-w", "set", "t=8.5", "-a", "RG15_thick.dat", "-o", "RG15_t8.5.dat"],
            "Scaling thickness",
        )
        run_cmd(
            ["-w", "set", "c=2.0", "-a", "RG15_camber.dat", "-o", "RG15_c2.0.dat"],
            "Scaling camber",
        )
        run_cmd(
            ["-w", "set", "te=0.5", "-a", "RG15_te.dat", "-o", "RG15_te0.5.dat"],
            "Scaling TE gap",
        )

        print("\n\n>>> SCENARIO 4: Bezier Matching")
        run_cmd(
            ["-w", "bezier", "-i", "bez.json", "-a", "MH32.dat", "-o", "MH32-bez.dat"],
            "Bezier match",
        )

        print("\n\n>>> SCENARIO 5: Curvature Diagnostics")
        run_cmd(
            ["-w", "check", "-a", "MH32-bez.dat"], "Checking Curvature"
        ) if os.path.exists("MH32-bez.dat") else None

        print("\n\n>>> SCENARIO 6: XFOIL Polar Matrix")
        os.makedirs("RG15_polars", exist_ok=True)
        run_cmd(
            ["-w", "polar", "-i", "px.json", "-a", "RG15_norm.dat"],
            "Generating .dat polars",
        )

        print("\n\n>>> SCENARIO 7: CSV Polar Matrix")
        run_cmd(
            ["-w", "polar-csv", "-i", "pc.json", "-a", "MH43.dat", "-o", "MH43_Xfoil"],
            "Generating .csv polars",
        )
        # -------------------------------------------------------------------------
        # TEST 8: AI SURROGATE POLAR GENERATION (-w polar-csv)
        # -------------------------------------------------------------------------
        print("\n\n>>> SCENARIO 8: High-Speed AI Surrogate Polar Matrix (NeuralFoil)")
        run_cmd(
            [
                "-w",
                "polar-csv",
                "-i",
                "polars_neural.json",
                "-a",
                "MH43.dat",
                "-o",
                "MH43_AI",
            ],
            "Generating massive 168-point matrix via NeuralFoil",
        )

        print(
            "\n"
            + "=" * 80
            + f"\n  WORKER TESTS COMPLETED.\n  All outputs in: {os.path.abspath(T_DIR)}\n"
            + "=" * 80
        )

    finally:
        os.chdir(O_CWD)


if __name__ == "__main__":
    main()
