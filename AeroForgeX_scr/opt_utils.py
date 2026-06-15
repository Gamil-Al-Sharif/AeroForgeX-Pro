# ==============================================================================
# FILE: opt_utils.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# Based on Xoptfoil2 by Jochen Guenzel (MIT License)
# ==============================================================================
import os, numpy as np
from utils_logger import print_error


# =============================================================================
# NELDER-MEAD SIMPLEX SEARCH ENGINE (Local Topological Refinement)
# =============================================================================
class SimplexOptionsType:
    def __init__(self):
        self.min_radius, self.initial_step, self.max_iterations = 1e-5, 0.02, 1000


def design_radius(dv):
    """Calculates the spatial volume (radius) of the Simplex hyperspace."""
    cen = np.mean(dv, axis=1)
    return np.max([np.linalg.norm(dv[:, i] - cen) for i in range(dv.shape[1])])


def simplexsearch(objfunc, x0_in, opt, f0_ref=None):
    """
    Executes a Nelder-Mead topological search strictly within [0.0, 1.0].
    Used analytically to morph Bezier control points to target coordinates.
    """
    rho, xi, gam, sigma, step = 1.0, 2.0, 0.5, 0.5, opt.initial_step
    x0, nvars = np.clip(np.array(x0_in, dtype=float), 0.0, 1.0), len(x0_in)
    dv, objvals, fevals, steps = np.zeros((nvars, nvars + 1)), np.zeros(nvars + 1), 0, 0

    # 1. Initialize the N-Dimensional Simplex Geometry
    f0 = f0_ref if f0_ref is not None else objfunc(x0)
    if f0_ref is None:
        fevals += 1

    for j in range(nvars):
        v = x0.copy()
        v[j] = (
            step if v[j] == 0.0 else (v[j] - step if v[j] + step > 1.0 else v[j] + step)
        )
        dv[:, j] = v
        objvals[j] = 9999.0 if np.any(v > 1.0) or np.any(v < 0.0) else objfunc(v)
        if objvals[j] != 9999.0:
            fevals += 1

    dv[:, nvars], objvals[nvars] = x0, f0
    idx = np.argsort(objvals)
    dv, objvals = dv[:, idx], objvals[idx]

    # 2. Core Simplex Evolution Loop
    while design_radius(dv) >= opt.min_radius and steps < opt.max_iterations:
        steps += 1
        xcen = np.mean(dv[:, :-1], axis=1)

        # Reflection
        xr = (1.0 + rho) * xcen - rho * dv[:, -1]
        fr = 9999.0 if np.any(xr > 1.0) or np.any(xr < 0.0) else objfunc(xr)
        if fr != 9999.0:
            fevals += 1

        if objvals[0] <= fr < objvals[-2]:
            dv[:, -1], objvals[-1] = xr, fr
        elif fr < objvals[0]:
            # Expansion
            xe = (1.0 + rho * xi) * xcen - rho * xi * dv[:, -1]
            fe = 9999.0 if np.any(xe > 1.0) or np.any(xe < 0.0) else objfunc(xe)
            if fe != 9999.0:
                fevals += 1
            dv[:, -1], objvals[-1] = (xe, fe) if fe < fr else (xr, fr)
        else:
            # Contraction
            if fr < objvals[-1]:  # Outside
                xc = (1.0 + rho * gam) * xcen - rho * gam * dv[:, -1]
                fc = 9999.0 if np.any(xc > 1.0) or np.any(xc < 0.0) else objfunc(xc)
                if fc != 9999.0:
                    fevals += 1
                if fc < fr:
                    dv[:, -1], objvals[-1], shrink = xc, fc, False
                else:
                    shrink = True
            else:  # Inside
                xc = (1.0 - gam) * xcen + gam * dv[:, -1]
                fc = 9999.0 if np.any(xc > 1.0) or np.any(xc < 0.0) else objfunc(xc)
                if fc != 9999.0:
                    fevals += 1
                if fc < objvals[-1]:
                    dv[:, -1], objvals[-1], shrink = xc, fc, False
                else:
                    shrink = True

            # Shrink
            if shrink:
                xb = dv[:, 0]
                for i in range(1, nvars + 1):
                    dv[:, i] = xb + sigma * (dv[:, i] - xb)
                    objvals[i] = (
                        9999.0
                        if np.any(dv[:, i] > 1.0) or np.any(dv[:, i] < 0.0)
                        else objfunc(dv[:, i])
                    )
                    if objvals[i] != 9999.0:
                        fevals += 1

        idx = np.argsort(objvals)
        dv, objvals = dv[:, idx], objvals[idx]

    return dv[:, 0], objvals[0], steps, fevals


# =============================================================================
# PARTICLE SWARM CONFIGURATION (Legacy Mapping)
# =============================================================================
class PsoOptionsType:
    def __init__(self):
        self.pop, self.min_radius, self.max_speed, self.max_iterations = (
            30,
            0.001,
            0.1,
            500,
        )
        self.init_attempts, self.convergence_profile, self.max_retries = (
            1000,
            "exhaustive",
            3,
        )
        self.auto_frequency, self.rescue_particle, self.stucked_threshold = (
            100,
            True,
            15,
        )
        self.rescue_frequency, self.dump_dv = 20, False


# =============================================================================
# OS-LEVEL INTERRUPTS
# =============================================================================
def reset_run_control():
    open("run_control", "w").close()


def update_run_control(it, dcnt, fmin):
    with open("run_control", "w") as f:
        f.write(f"!stop\n!run-info; step: {it}; design: {dcnt}; fmin: {fmin:.7f}\n")


def delete_run_control():
    if os.path.exists("run_control"):
        os.remove("run_control")


def stop_requested():
    if not os.path.exists("run_control"):
        return False
    try:
        with open("run_control", "r") as f:
            return any(line.strip().lower() == "stop" for line in f)
    except Exception:
        return False
