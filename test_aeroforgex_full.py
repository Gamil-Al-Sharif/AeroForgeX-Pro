#!/usr/bin/env python3
# ==============================================================================
# FILE: test_aeroforgex_full.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
import os
import sys
import json
import subprocess
import platform
import shutil

T_DIR = "test_aeroforgex_full_output"


def setup_dir():
    print(f"[*] Preparing clean test sandbox: ./{T_DIR}/")
    shutil.rmtree(T_DIR, ignore_errors=True)
    os.makedirs(T_DIR)


def get_p(fn):
    return os.path.join(T_DIR, fn)


def c_js(fn, d):
    fp = get_p(fn)
    open(fp, "w").write(json.dumps(d, indent=4))
    return fp


def find_exe(exe):
    for d in [os.getcwd(), "..", "AeroForgeX_scr", "src", "source", "bin"]:
        if os.path.exists(os.path.join(d, exe)):
            return os.path.join(d, exe)
    return shutil.which(exe)


def gen_naca4(n, n_pts=160):
    import numpy as np

    m, p, t = int(n[0]) / 100.0, int(n[1]) / 10.0, int(n[2:]) / 100.0
    x = (1.0 - np.cos(np.linspace(0, np.pi, (n_pts // 2) + 1))) / 2.0
    yt = (
        5
        * t
        * (0.2969 * x**0.5 - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    )
    xu, yu, xd, yd = [], [], [], []
    for i, xi in enumerate(x):
        # Fixed: Corrected the grouping of the tuples to short-circuit if p == 0 avoiding ZeroDivisionError
        yc, dy = (
            (0.0, 0.0)
            if p == 0
            else (
                ((m / p**2) * (2 * p * xi - xi**2), (2 * m / p**2) * (p - xi))
                if xi < p
                else (
                    (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * xi - xi**2),
                    (2 * m / (1 - p) ** 2) * (p - xi),
                )
            )
        )

        th = np.arctan(dy)
        xu.append(xi - yt[i] * np.sin(th))
        yu.append(yc + yt[i] * np.cos(th))
        xd.append(xi + yt[i] * np.sin(th))
        yd.append(yc - yt[i] * np.cos(th))
    fp = get_p(f"NACA{n}.dat")
    with open(fp, "w") as f:
        f.write(
            f"NACA {n}\n"
            + "".join(
                f"{xi:.7f}  {yi:.7f}\n"
                for xi, yi in zip(xu[::-1] + xd[1:], yu[::-1] + yd[1:])
            )
        )
    return fp


def run_cmd(args, desc):
    print(f"\n{'=' * 80}\n [+] EXECUTING: {desc}\n{'=' * 80}")
    cp = find_exe("aeroforgex_cli.py")
    if not cp:
        print("[!] ERROR: Cannot locate CLI script.")
        sys.exit(1)
    cmd = [sys.executable, cp] + args
    print(f"CMD: {' '.join(cmd)}\n")
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for l in proc.stdout:
            print("    " + l.strip())
        proc.wait()
        if proc.returncode != 0:
            print(f"\n[!] FAILED with exit code {proc.returncode}")
            return False
        return True
    except Exception as e:
        print(f"\n[!] EXECUTION ERROR: {str(e)}")
        return False


def main():
    print("=" * 80 + "\n  AeroForgeX v3.0 Master Test Suite (Numba/PyMoo)\n" + "=" * 80)
    setup_dir()
    xf = find_exe("xfoil.exe" if platform.system() == "Windows" else "xfoil")
    print(
        f"[*] XFOIL found at: {xf}"
        if xf
        else "[!] WARNING: XFOIL missing. Tests may fail."
    )

    s_0, s_4, w_cfg = (
        gen_naca4("0012"),
        gen_naca4("4412"),
        c_js(
            "tw.json",
            {
                "op_conds": {"x_flap": 0.75, "flap_ang": 5.0},
                "polar_generation": {
                    "generate_polar": True,
                    "polar_reynolds": [5e5],
                    "op_point_range": [-5.0, 15.0, 0.5],
                },
            },
        ),
    )
    n_pfx, n_f = get_p("NACA_0012_Norm"), get_p("NACA_0012_Norm.dat")

    run_cmd(["-w", "check-input", "-i", w_cfg], "WORKER: Check Config")
    run_cmd(["-w", "norm", "-a", s_0, "-o", n_pfx], "WORKER: Normalize")
    run_cmd(["-w", "check", "-i", w_cfg, "-a", n_f], "WORKER: Curvature Diagnostics")
    run_cmd(
        ["-w", "set", "t=15", "-a", n_f, "-o", get_p("NACA_0015_Scl")],
        "WORKER: Set Thickness",
    )
    run_cmd(
        ["-w", "set", "c=5", "-a", n_f, "-o", get_p("NACA_5012_Scl")],
        "WORKER: Set Camber",
    )
    run_cmd(
        ["-w", "blend", "50", "-a", n_f, "-a2", s_4, "-o", get_p("NACA_Bld")],
        "WORKER: Blend Mesh",
    )
    run_cmd(
        ["-w", "flap", "-i", w_cfg, "-a", n_f, "-o", get_p("NACA_Flp")], "WORKER: Flap"
    )
    run_cmd(["-w", "bezier", "-a", n_f, "-o", get_p("NACA_Bez")], "WORKER: Bezier Fit")
    run_cmd(
        ["-w", "polar-csv", "-i", w_cfg, "-a", n_f, "-o", get_p("Polar")],
        "WORKER: Polar CSV",
    )

    print(
        "\n\n"
        + "#" * 80
        + "\n INITIATING MEMETIC OPTIMIZATION ENGINE (Generations=2-5)\n"
        + "#" * 80
    )

    c_cst = c_js(
        "t_cst.json",
        {
            "opt_opts": {"solver": "xfoil", "shape_func": "cst", "verbose": True},
            "optim_set": {"pop": 10, "gen": 3},
            "op_conds": {
                "num_pts": 2,
                "re_def": 5e5,
                "dyn_weight": True,
                "mode": ["spec-cl", "spec-al"],
                "val": [0.5, 2.0],
                "opt_type": ["min-drag", "max-glide"],
                "weight": [1.0, 1.0],
            },
            "constr": {"chk_geo": True, "min_t": 0.10, "max_t": 0.14},
            "cst_opts": {"n_t": 4, "n_b": 4},
        },
    )
    run_cmd(
        ["-i", c_cst, "-a", n_f, "-o", get_p("Opt_CST")],
        "OPTIMIZER: CST + Dynamic Weighting",
    )

    c_bez = c_js(
        "t_bez.json",
        {
            "opt_opts": {"solver": "xfoil", "shape_func": "bezier", "verbose": True},
            "optim_set": {"pop": 10, "gen": 2},
            "op_conds": {
                "num_pts": 1,
                "re_def": 5e5,
                "mode": ["spec-al"],
                "val": [5],
                "opt_type": ["max-lift"],
                "use_flap": True,
                "flap_opt": [True],
                "x_flap": 0.75,
            },
            "constr": {"min_flap": 0.0, "max_flap": 10.0},
            "bez_opts": {"ncp_t": 5, "ncp_b": 5},
        },
    )
    run_cmd(
        ["-i", c_bez, "-a", n_f, "-o", get_p("Opt_Bez")], "OPTIMIZER: Bezier + Flaps"
    )

    c_hh = c_js(
        "t_hh.json",
        {
            "opt_opts": {
                "solver": "xfoil",
                "shape_func": "hicks-henne",
                "verbose": True,
            },
            "optim_set": {"pop": 10, "gen": 2},
            "op_conds": {
                "num_pts": 1,
                "re_def": 5e5,
                "mode": ["spec-cl"],
                "val": [0.4],
                "opt_type": ["min-drag"],
            },
            "curv": {"chk_curv": True, "auto_curv": True},
            "hh_opts": {"n_t": 3, "n_b": 3},
        },
    )
    run_cmd(
        ["-i", c_hh, "-a", s_4, "-o", get_p("Opt_HH")],
        "OPTIMIZER: Hicks-Henne + Auto Curvature",
    )

    c_mat = c_js(
        "t_mat.json",
        {
            "opt_opts": {
                "solver": "xfoil",
                "shape_func": "camb-thick",
                "verbose": True,
            },
            "optim_set": {"pop": 50, "gen": 50},
            "geo_tgts": {"num_tgts": 1, "type": ["match-foil"], "str": [s_4]},
            "ct_opts": {"thk": True, "cmb": True},
        },
    )
    run_cmd(
        ["-i", c_mat, "-a", n_f, "-o", get_p("Opt_Mat")],
        "OPTIMIZER: Camb-Thick Match Foil",
    )

    print("\n" + "=" * 80 + "\n  ALL TESTS COMPLETED\n" + "=" * 80)


if __name__ == "__main__":
    try:
        import numpy
    except:
        sys.exit(print("[!] ERROR: numpy required."))
    main()
