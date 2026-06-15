# ==============================================================================
# FILE: solver_neuralfoil.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
import copy, numpy as np
import solver_xfoil as xfoil_driver
import solver_router as neural_driver
from utils_logger import print_colored, COLOR_WARNING

# =============================================================================
# SOLVER STATE & ROUTING
# =============================================================================
_active_solver = "xfoil"


def set_aero_solver(solver_name):
    global _active_solver
    if (
        solver_name.lower() == "neuralfoil"
        and neural_driver.check_neuralfoil_available()
    ):
        _active_solver = "neuralfoil"
    elif solver_name.lower() == "neuralfoil":
        print_colored(
            COLOR_WARNING,
            "WARNING: NeuralFoil engine missing. Falling back to XFOIL subprocess.\n",
        )
        _active_solver = "xfoil"
    else:
        _active_solver = "xfoil"


def get_active_solver():
    return _active_solver


# =============================================================================
# PYTHON-NATIVE KINEMATIC GEOMETRY ENGINE & DISPATCHER
# =============================================================================
def _apply_geometric_flap(foil, fsp, a):
    """Replicates XFOIL's internal GDES FLAP routine purely in Python arrays."""
    nf, rad = copy.deepcopy(foil), np.radians(a)
    c, s, m = np.cos(rad), np.sin(rad), foil.x >= fsp.x_flap
    dx, dy = nf.x[m] - fsp.x_flap, nf.y[m] - fsp.y_flap
    nf.x[m], nf.y[m] = fsp.x_flap + dx * c + dy * s, fsp.y_flap - dx * s + dy * c
    return nf


def run_op_points(foil, x_opt, fsp, f_angs, ops_spec):
    """The Unified Aerodynamic Entry Point routing to XFOIL or AI Surrogate."""
    # print(f"\n[ TRAFFIC CONTROLLER ] Active Solver is currently set to: {_active_solver}\n")
    if _active_solver == "neuralfoil":
        if fsp.use_flap and any(abs(a) > 0.001 for a in f_angs):
            return [
                neural_driver.run_neuralfoil_analysis(
                    _apply_geometric_flap(foil, fsp, f_angs[i])
                    if abs(f_angs[i]) > 0.001
                    else foil,
                    x_opt,
                    [sp],
                )[0]
                for i, sp in enumerate(ops_spec)
            ]
        return neural_driver.run_neuralfoil_analysis(foil, x_opt, ops_spec)
    return xfoil_driver.run_op_points(foil, x_opt, fsp, f_angs, ops_spec)
