# ==============================================================================
# FILE: solver_router.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
import numpy as np

try:
    import neuralfoil
except ImportError:
    neuralfoil = None
from solver_xfoil import OpPointResultType
from utils_logger import print_colored, COLOR_ERROR


# =============================================================================
# ENVIRONMENT VALIDATION
# =============================================================================
def check_neuralfoil_available():
    return neuralfoil is not None


def get_dummy_result():
    res = OpPointResultType()
    res.converged, res.cd = False, 1.0
    return res


# =============================================================================
# SURROGATE INFERENCE ENGINE
# =============================================================================
def run_neuralfoil_analysis(foil, xo, op_points_spec, conf_threshold=None):
    """
    Executes high-speed aerodynamic inference using the Deep Learning Surrogate.
    Updated to utilize full Batched Tensor Operations for massive speed-ups.
    CL-targeting now uses 2-pass secant interpolation (was 3-pass) for ~33% speedup.
    """
    if not neuralfoil:
        print_colored(
            COLOR_ERROR,
            "CRITICAL: 'neuralfoil' missing. Install via: pip install neuralfoil",
        )
        return [get_dummy_result() for _ in op_points_spec]

    # Resolve confidence threshold — from options, or default 0.5
    if conf_threshold is None:
        conf_threshold = getattr(xo, 'nf_conf_threshold', 0.5)

    # Format and strictly compress mesh array for the CNN Convolutional limits
    c = np.column_stack((foil.x, foil.y))
    if len(c) > 200:
        c = c[np.linspace(0, len(c) - 1, 160, dtype=int)]

    res_list = [OpPointResultType() for _ in range(len(op_points_spec))]
    idx_cl = [i for i, op in enumerate(op_points_spec) if op.spec_cl]
    idx_al = [i for i, op in enumerate(op_points_spec) if not op.spec_cl]

    # 1. BATCHED ALPHA-TARGETING (DIRECT INFERENCE)
    if idx_al:
        alphas = np.array([op_points_spec[i].value for i in idx_al])
        res_arr = np.array([op_points_spec[i].re.number for i in idx_al])
        re_in = res_arr[0] if np.all(res_arr == res_arr[0]) else res_arr
        try:
            vals = neuralfoil.get_aero_from_coordinates(
                c, alpha=alphas, Re=re_in, model_size="xxxlarge"
            )
            conf = vals.get("analysis_confidence", np.ones(len(alphas)))
            for k, i in enumerate(idx_al):
                if conf[k] > conf_threshold:
                    r = res_list[i]
                    r.converged, r.alpha, r.cl, r.cd, r.cm = (
                        True,
                        float(alphas[k]),
                        float(vals["CL"][k]),
                        float(vals["CD"][k]),
                        float(vals["CM"][k]),
                    )
                    r.xtrt, r.xtrb = 1.0, 1.0
                else:
                    res_list[i].converged, res_list[i].cd = False, 1.0
        except Exception as e:
            print(f"\n[ NEURALFOIL ERROR ] Surrogate Batch Inference crash: {str(e)}")
            for i in idx_al:
                res_list[i].converged, res_list[i].cd = False, 1.0

    # 2. BATCHED SECANT SOLVER (CL-TARGETING) — 2-Pass Interpolation (was 3-pass)
    if idx_cl:
        tgt_cls = np.array([op_points_spec[i].value for i in idx_cl])
        res_arr = np.array([op_points_spec[i].re.number for i in idx_cl])
        re_in = res_arr[0] if np.all(res_arr == res_arr[0]) else res_arr
        ag1 = (tgt_cls - 0.1) * 10.0
        ag2 = ag1 + 1.0

        try:
            vals1 = neuralfoil.get_aero_from_coordinates(
                c, alpha=ag1, Re=re_in, model_size="xxxlarge"
            )
            vals2 = neuralfoil.get_aero_from_coordinates(
                c, alpha=ag2, Re=re_in, model_size="xxxlarge"
            )

            cl1, cl2 = vals1["CL"], vals2["CL"]
            dcl = cl2 - cl1
            # Secant interpolation fraction — clipped to [0, 2] to prevent extrapolation blowup
            t = np.where(np.abs(dcl) > 1e-4, (tgt_cls - cl1) / dcl, 0.0)
            t = np.clip(t, 0.0, 2.0)

            # Interpolate all aerodynamic quantities directly — NO 3rd inference pass
            af = ag1 + t * (ag2 - ag1)
            cl_f = cl1 + t * dcl
            cd_f = vals1["CD"] + t * (vals2["CD"] - vals1["CD"])
            cm_f = vals1["CM"] + t * (vals2["CM"] - vals1["CM"])
            # Use minimum confidence of both bracket points (conservative)
            c1 = vals1.get("analysis_confidence", np.ones(len(ag1)))
            c2 = vals2.get("analysis_confidence", np.ones(len(ag2)))
            conf = np.minimum(c1, c2)

            for k, i in enumerate(idx_cl):
                if conf[k] > conf_threshold:
                    r = res_list[i]
                    r.converged, r.alpha, r.cl, r.cd, r.cm = (
                        True,
                        float(af[k]),
                        float(cl_f[k]),
                        float(cd_f[k]),
                        float(cm_f[k]),
                    )
                    r.xtrt, r.xtrb = 1.0, 1.0
                else:
                    res_list[i].converged, res_list[i].cd = False, 1.0
        except Exception as e:
            print(f"\n[ NEURALFOIL ERROR ] Surrogate Batch Secant crash: {str(e)}")
            for i in idx_cl:
                res_list[i].converged, res_list[i].cd = False, 1.0

    return res_list
