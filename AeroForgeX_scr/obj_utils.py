# ==============================================================================
# FILE: obj_utils.py
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
# DESCRIPTION: Core constraint evaluation, aerodynamic improvement tracking,
#              and comprehensive interactive dashboard generation.
# ==============================================================================
import os, copy, json, math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from numba import njit

from utils_logger import (
    COLOR_GOOD,
    COLOR_BAD,
    COLOR_NORMAL,
    COLOR_WARNING,
    COLOR_NOTE,
    COLOR_ERROR,
    COLOR_PALE,
    COLOR_FEATURE,
    Q_GOOD,
    Q_OK,
    Q_BAD,
    Q_PROBLEM,
    Q_NEW,
    NOT_DEF_D,
    print_colored,
    print_colored_i,
    print_colored_r,
    print_text,
    print_action,
    path_join,
    commons,
)
from geom_core import (
    AirfoilType,
    PanelOptionsType,
    airfoil_name_flapped,
    airfoil_write,
    print_airfoil_write,
    eval_thickness_camber_lines,
    get_geometry,
    normalize,
    split_foil_into_sides,
)
from solver_xfoil import (
    XfoilOptionsType,
    OpPointSpecType,
    ReType,
    OpPointResultType,
    FlapSpecType,
)
from math_accelerator import derivative1, count_reversals, find_reversals
from shape_functions_param import bezier_curvature


# =============================================================================
# NUMBA COMPILED CORE (DOUBLE PRECISION C-SPEED MATH ENGINE)
# =============================================================================
@njit(cache=True, fastmath=True)
def _get_le_angles(tx, ty, bx, by):
    """Calculates exactly the surface tangency at the leading edge."""
    if len(tx) < 2 or len(bx) < 2:
        return 90.0, 90.0
    return np.abs(np.degrees(np.arctan2(ty[1] - ty[0], tx[1] - tx[0]))), np.abs(
        np.degrees(np.arctan2(by[1] - by[0], bx[1] - bx[0]))
    )


@njit(cache=True, fastmath=True)
def _max_panels_angle(x, y):
    """Iterates through the geometry to find the maximum discontinuity angle."""
    n, m_ang = len(x), 0.0
    if n < 3:
        return 90.0
    for i in range(1, n - 1):
        dx1, dy1 = x[i] - x[i - 1], y[i] - y[i - 1]
        dx2, dy2 = x[i + 1] - x[i], y[i + 1] - y[i]
        ang = np.abs(
            np.degrees(np.arctan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2))
        )
        if ang > m_ang:
            m_ang = ang
    return m_ang


@njit(cache=True, fastmath=True)
def _min_te_angle(x, y):
    """Mathematically extracts the absolute trailing edge closure angle."""
    n = len(x)
    if n < 3:
        return 0.0
    max_s, min_s, idx_m, gap = -1e99, 1e99, 0, y[-1]

    # Forward scan for max slope
    for i in range(1, n - 1):
        dx = x[-1] - x[i]
        if dx <= 1e-10:
            continue
        slope = (y[i] - gap) / dx
        if slope > max_s:
            max_s, idx_m = slope, i
        else:
            break

    # Sub-scan for min slope from max location
    for i in range(idx_m, n - 1):
        dx = x[-1] - x[i]
        if dx > 1e-10 and (y[i] - gap) / dx < min_s:
            min_s = (y[i] - gap) / dx

    return np.degrees(np.arctan(min_s))


@njit(cache=True, fastmath=True)
def _max_te_curv(curv):
    """Analyzes the curvature gradient exactly at the trailing edge limit."""
    return np.max(np.abs(curv[-4:])) if len(curv) >= 4 else 0.0


# =============================================================================
# MASTER EVALUATION DATA STRUCTURES
# =============================================================================
class GeoTargetType:
    def __init__(self):
        self.type, self.target_string = "", ""
        self.preset_to_target, self.dynamic_weighting, self.extra_punch = (
            False,
            False,
            False,
        )
        self.target_value = self.seed_value = self.reference_value = 0.0
        self.scale_factor = self.weighting = self.weighting_user = 1.0
        self.weighting_user_cur = self.weighting_user_prv = 0.0


class GeoResultType:
    def __init__(self):
        self.maxt = self.xmaxt = self.maxc = self.xmaxc = 0.0
        self.top_curv_le = self.top_curv_te = self.bot_curv_le = self.bot_curv_te = 0.0
        self.match_top_deviation = self.match_bot_deviation = 0.0


class DynamicWeightingSpecType:
    def __init__(self):
        self.active, self.min_weighting, self.max_weighting = False, 0.5, 4.0
        self.extra_punch, self.frequency, self.start_with_design = 1.2, 20, 10


class GeoConstraintsType:
    def __init__(self):
        self.check_geometry, self.symmetrical = True, False
        self.min_te_angle, self.min_thickness, self.max_thickness = (
            0.0,
            -99999.0,
            -99999.0,
        )
        self.min_camber, self.max_camber = -99999.0, -99999.0


class CurvSideConstraintsType:
    def __init__(self):
        self.check_curvature_bumps = self.check_le_curvature = True
        self.curv_threshold, self.spike_threshold, self.max_te_curvature = 0.1, 0.5, 5.0
        self.max_curv_reverse = self.max_spikes = 0
        self.nskip_LE = 1


class CurvConstraintsType:
    def __init__(self):
        self.check_curvature, self.auto_curvature, self.max_le_curvature_diff = (
            True,
            True,
            5.0,
        )
        self.top, self.bot = CurvSideConstraintsType(), CurvSideConstraintsType()


class MatchFoilSpecType:
    def __init__(self):
        self.active, self.filename, self.foil = False, "", AirfoilType()
        self.target_top_x = self.target_top_y = self.target_bot_x = (
            self.target_bot_y
        ) = np.array([], dtype=np.float64)


class EvalSpecType:
    def __init__(self):
        self.op_points_spec, self.geo_targets = [], []
        self.geo_constraints, self.curv_constraints = (
            GeoConstraintsType(),
            CurvConstraintsType(),
        )
        self.dynamic_weighting_spec = DynamicWeightingSpecType()
        self.panel_options, self.xfoil_options, self.match_foil_spec = (
            PanelOptionsType(),
            XfoilOptionsType(),
            MatchFoilSpecType(),
        )


# =============================================================================
# EXACT GEOMETRIC MATHEMATICS & CONSTRAINT ENGINE
# =============================================================================
NO_VIOLATION = 0
VIOL_LE_BLUNT = 1
VIOL_LE_SHARP = 2
VIOL_MIN_TE_ANGLE = 3
VIOL_MAX_PANEL_ANGLE = 4
VIOL_MAX_CAMBER = 5
VIOL_MIN_CAMBER = 6
VIOL_MAX_THICKNESS = 7
VIOL_MIN_THICKNESS = 8
VIOL_MAX_REVERSALS = 9
VIOL_MAX_SPIKES = 10
VIOL_TE_CURVATURE = 11
VIOL_MAX_LE_DIFF = 12
VIOL_LE_CURV_MONOTON = 13

_v_stats = np.zeros(14, dtype=int)
_v_map = {
    1: "LE Bluntness",
    2: "LE Sharpness",
    3: "Min TE Angle",
    4: "Max Panel Angle",
    5: "Max Camber",
    6: "Min Camber",
    7: "Max Thickness",
    8: "Min Thickness",
    9: "Macro Reversals",
    10: "Micro Spikes",
    11: "TE Curvature",
    12: "LE Curv Diff",
    13: "LE Non-Monotonicity",
}


def add_to_stats(vid):
    if 0 < vid <= 13:
        _v_stats[vid] += 1


def violation_stats_reset():
    _v_stats[:] = 0


def violation_stats_print(indent=10):
    if np.sum(_v_stats) == 0:
        return
    print_colored(COLOR_FEATURE, " [ SYSTEM ] Geometric Rejections : ", end="")
    print_colored(
        COLOR_WARNING,
        " | ".join(f"{_v_stats[i]} {_v_map[i]}" for i in range(1, 14) if _v_stats[i]),
    )
    print("\n")


def get_le_panel_angles(f):
    return _get_le_angles(
        np.array(f.top.x, dtype=np.float64),
        np.array(f.top.y, dtype=np.float64),
        np.array(f.bot.x, dtype=np.float64),
        np.array(f.bot.y, dtype=np.float64),
    )


def max_le_panel_angle(f):
    return max(get_le_panel_angles(f))


def le_panels_angle(f):
    return abs(get_le_panel_angles(f)[1] - get_le_panel_angles(f)[0])


def max_panels_angle(f):
    return (
        _max_panels_angle(
            np.array(f.x, dtype=np.float64), np.array(f.y, dtype=np.float64)
        )
        if f.x is not None
        else 90.0
    )


def min_te_angle(t):
    return (
        _min_te_angle(np.array(t.x, dtype=np.float64), np.array(t.y, dtype=np.float64))
        if t.x is not None
        else 0.0
    )


def max_curvature_at_te(c):
    return _max_te_curv(np.array(c, dtype=np.float64)) if c is not None else 0.0


def eval_geometry_violations(f, c):
    # Compute LE panel angles ONCE — was previously called 3× redundantly
    ang_t, ang_b = get_le_panel_angles(f)
    max_ang = max(ang_t, ang_b)
    diff_ang = abs(ang_t - ang_b)

    if max_ang > 89.99:
        add_to_stats(VIOL_LE_BLUNT)
        return (True, VIOL_LE_BLUNT, f"LE Panel angle {max_ang:.2f} approaches vertical singularity (Bluntness).")
    if diff_ang > 20.0:
        add_to_stats(VIOL_LE_SHARP)
        return (True, VIOL_LE_SHARP, f"LE Panel angles {diff_ang:.2f}  highly divergent (Mesh Fold Sharpness).")

    t, cmb = eval_thickness_camber_lines(f)
    if min_te_angle(t) < c.min_te_angle:
        add_to_stats(VIOL_MIN_TE_ANGLE)
        return (True, VIOL_MIN_TE_ANGLE, f"Min TE Wedge Angle  {min_te_angle(t):.2f} < {c.min_te_angle:.2f} deg")
    if max_panels_angle(f) > 30.0:
        add_to_stats(VIOL_MAX_PANEL_ANGLE)
        return (True, VIOL_MAX_PANEL_ANGLE, f"Surface panel turning angle {max_panels_angle(f):.2f} exceeds stable fluid mesh limits.")

    mt, xmt, mc, xmc = get_geometry(f)
    if c.max_camber > -9000 and mc > c.max_camber:
        add_to_stats(VIOL_MAX_CAMBER)
        return True, VIOL_MAX_CAMBER, f"Camber {mc:.4f} > {c.max_camber:.4f}"
    if c.min_camber > -9000 and mc < c.min_camber:
        add_to_stats(VIOL_MIN_CAMBER)
        return True, VIOL_MIN_CAMBER, f"Camber {mc:.4f} < {c.min_camber:.4f}"
    if c.max_thickness > -9000 and mt > c.max_thickness:
        add_to_stats(VIOL_MAX_THICKNESS)
        return True, VIOL_MAX_THICKNESS, f"Thickness {mt:.4f}  > {c.max_thickness:.4f}"
    if c.min_thickness > -9000 and mt < c.min_thickness:
        add_to_stats(VIOL_MIN_THICKNESS)
        return True, VIOL_MIN_THICKNESS, f"Thickness {mt:.4f}  < {c.min_thickness:.4f}"

    return False, NO_VIOLATION, ""


def eval_side_curvature_violations(s, c):
    if s.curvature is None or len(s.curvature) == 0:
        return True, VIOL_MAX_REVERSALS, "Invalid Curvature Spline"

    n_rev = count_reversals(c.nskip_LE, len(s.x), s.curvature, c.curv_threshold)
    if n_rev > c.max_curv_reverse:
        add_to_stats(VIOL_MAX_REVERSALS)
        return (
            True,
            VIOL_MAX_REVERSALS,
            f"{s.name}: Reversals {n_rev} > {c.max_curv_reverse}",
        )

    if c.check_curvature_bumps:
        if (
            nspikes := count_reversals(
                c.nskip_LE, len(s.x), derivative1(s.x, s.curvature), c.spike_threshold
            )
        ) > c.max_spikes:
            add_to_stats(VIOL_MAX_SPIKES)
            return (
                True,
                VIOL_MAX_SPIKES,
                f"{s.name}: Micro Spikes {nspikes} > {c.max_spikes}",
            )

    if (te_curv := max_curvature_at_te(s.curvature)) > c.max_te_curvature:
        add_to_stats(VIOL_TE_CURVATURE)
        return (
            True,
            VIOL_TE_CURVATURE,
            f"{s.name}: TE Curvature {te_curv:.1f} > {c.max_te_curvature:.1f}",
        )

    if c.check_le_curvature:
        # Vectorized: single NumPy operation replaces Python loop over 10 elements
        n_check = min(10, len(s.curvature) - 1)
        if n_check > 0:
            curv_le = np.abs(s.curvature[:n_check])
            curv_next = np.abs(s.curvature[1:n_check + 1])
            if np.any(curv_le < curv_next / 1.05):
                add_to_stats(VIOL_LE_CURV_MONOTON)
                return True, VIOL_LE_CURV_MONOTON, f"{s.name}: LE Curv not monotonic."

    return False, NO_VIOLATION, ""


def eval_curvature_violations(f, c):
    has, vid, info = eval_side_curvature_violations(f.top, c.top)
    if has:
        return has, vid, info

    if not f.symmetrical:
        has, vid, info = eval_side_curvature_violations(f.bot, c.bot)
        if has:
            return has, vid, info

    if (
        f.is_bezier_based
        and (
            diff := abs(
                bezier_curvature(f.top_bezier, 0.0)
                - bezier_curvature(f.bot_bezier, 0.0)
            )
        )
        > c.max_le_curvature_diff
    ):
        add_to_stats(VIOL_MAX_LE_DIFF)
        return (
            True,
            VIOL_MAX_LE_DIFF,
            f"Bezier LE Curvature Discontinuity {diff:.1f} > {c.max_le_curvature_diff:.1f}",
        )

    return False, NO_VIOLATION, ""


def assess_surface(s, dtl, skp, ie, i_spk, c_th, s_th):
    if s.curvature is None or len(s.curvature) == 0:
        return Q_PROBLEM
    n_spk = find_reversals(skp, i_spk, s_th, derivative1(s.x, s.curvature), "s", True)[
        0
    ]
    n_rev = find_reversals(skp, ie, c_th, s.curvature, "R", True)[0]
    return max(
        2 if n_spk >= 6 else (1 if n_spk >= 2 else 0),
        2 if n_rev >= 3 else (1 if n_rev >= 2 else 0),
    )


# =============================================================================
# CSV EXPORT ENGINES & INTERACTIVE HTML DASHBOARD
# =============================================================================
# class NumpyJSONEncoder(json.JSONEncoder):
# """Safely and recursively converts NumPy numerical types for HTML/Javascript."""
# def default(self, obj):
# if isinstance(obj, np.integer): return int(obj)
# elif isinstance(obj, np.floating):
# if np.isnan(obj) or np.isinf(obj): return 0.0
# return float(obj)
# elif isinstance(obj, np.ndarray): return obj.tolist()
# return super(NumpyJSONEncoder, self).default(obj)


# from report_generator import (
# generate_report,
# generate_worker_topology_report,
# generate_worker_polar_dashboard
# )
# =============================================================================
# DATA FORMATTERS & CONSOLE LOGGERS (unchanged from Version 2)
# =============================================================================
def write_design_op_points_header(fn):
    with open(fn, "w") as f:
        f.write(
            "  No; iOp;      alpha;         cl;         cd;         cm;       xtrt;       xtrb;     dist;      dev;     flap;   weight\n"
        )


def get_op_improvement(sp, op):
    tp, d, dev, g = sp.optimization_type, 0.0, 0.0, 0
    if tp.startswith("target"):
        if tp == "target-drag":
            d = op.cd - sp.target_value
            dev = (d / sp.target_value) * 100 if sp.target_value else 0
        elif tp == "target-glide":
            gld = op.cl / op.cd if op.cd else 0
            d = gld - sp.target_value
            dev = (d / sp.target_value) * 100 if sp.target_value else 0
        elif tp == "target-lift":
            d = op.cl - sp.target_value
            dev = (d / (1.0 + sp.target_value)) * 100
        elif tp == "target-moment":
            d = op.cm - sp.target_value
            dev = (d / (sp.target_value + 0.1)) * 100
        g = (
            Q_GOOD
            if sp.allow_improved_target
            and ((tp == "target-drag" and dev < 0) or (tp != "target-drag" and dev > 0))
            else (2 if abs(dev) >= 10.0 else (1 if abs(dev) >= 2.0 else 0))
        )
    else:
        sc, imp = sp.scale_factor, 0.0
        if tp == "min-sink":
            v = (op.cl**1.5) / op.cd if op.cd else 0
            d, imp = v - sc, ((v - sc) / sc * 100) if sc else 0
        elif tp == "max-glide":
            v = op.cl / op.cd if op.cd else 0
            d, imp = v - sc, ((v - sc) / sc * 100) if sc else 0
        elif tp == "min-drag":
            d, imp = op.cd - (1.0 / sc), -(op.cd - (1.0 / sc)) * sc * 100
        elif tp == "max-lift":
            d, imp = op.cl - sc, ((op.cl - sc) / sc) * 100
        elif tp == "max-xtr":
            v = 0.5 * (op.xtrt + op.xtrb) + 0.1
            d, imp = v - sc, ((v - sc) / sc) * 100
        g, dev = 2 if imp <= 0.0 else (1 if imp < 2.0 else 0), imp
    return d, dev, g


def write_design_op_points_data(fn, d, sps, ops, f_angs):
    with open(fn, "w" if d == 0 else "a") as f:
        for i, (sp, op, a) in enumerate(zip(sps, ops, f_angs)):
            dst, dev, _ = get_op_improvement(sp, op)
            f.write(
                f"{d:5d};{i + 1:4d};{op.alpha:11.6f};{op.cl:11.6f};{op.cd:11.6f};"
                f"{op.cm:11.6f};{op.xtrt:11.6f};{op.xtrb:11.6f};{dst:11.6f};"
                f"{dev:9.4f};{a:9.4f};{sp.weighting_user_cur or sp.weighting_user:5.2f}\n"
            )


def write_design_geo_targets_header(fn):
    with open(fn, "w") as f:
        f.write(
            "  No; iGeo;         type;         val;        dist;         dev;      weight\n"
        )


def get_geo_improvement_info(g_sp, g_res):
    v = g_res.maxt if g_sp.type == "thickness" else g_res.maxc
    d, dev = (
        v - g_sp.target_value,
        ((v - g_sp.target_value) / g_sp.target_value) * 100 if g_sp.target_value else 0,
    )
    return d, dev, 2 if abs(dev) >= 10.0 else (1 if abs(dev) >= 2.0 else 0)


def write_design_geo_targets_data(fn, d, tgts, res):
    with open(fn, "w" if d == 0 else "a") as f:
        for i, g in enumerate(tgts):
            v, (dst, dev, _) = (
                res.maxt if g.type == "thickness" else res.maxc,
                get_geo_improvement_info(g, res),
            )
            f.write(
                f"{d:5d};{i + 1:4d};{g.type:>12s};{v:11.6f};{dst:11.6f};{dev:11.6f};{g.weighting_user_cur or g.weighting_user:11.6f}\n"
            )


def write_design_coord_header(fn, foil):
    with open(fn, "w") as f:
        f.write(
            "  No;           Name; Coord"
            + "".join(f";{i + 1:10d}" for i in range(len(foil.x)))
            + "\n"
        )


def write_design_coord_data(fn, d, foil):
    nm = foil.name if d == 0 else f"{foil.name[:15]}~{d}"
    with open(fn, "w" if d == 0 else "a") as f:
        f.write(
            f"{d:5d};{nm};    x"
            + "".join(f";{x:10.7f}" for x in foil.x)
            + f"\n{d:5d};{nm};    y"
            + "".join(f";{y:10.7f}" for y in foil.y)
            + "\n"
        )


def write_design_bezier_header(fn, foil):
    with open(fn, "w") as f:
        f.write(
            "  No;           Name; Side"
            + "".join(
                f";       p{i}x;       p{i}y"
                for i in range(
                    1, max(len(foil.top_bezier.px), len(foil.bot_bezier.px)) + 1
                )
            )
            + "\n"
        )


def write_design_bezier_data(fn, d, foil):
    nm = foil.name if d == 0 else f"{foil.name[:15]}~{d}"
    with open(fn, "w" if d == 0 else "a") as f:
        f.write(
            f"{d:5d};{nm};  Top"
            + "".join(
                f";{x:10.7f};{y:10.7f}"
                for x, y in zip(foil.top_bezier.px, foil.top_bezier.py)
            )
            + f"\n{d:5d};{nm};  Bot"
            + "".join(
                f";{x:10.7f};{y:10.7f}"
                for x, y in zip(foil.bot_bezier.px, foil.bot_bezier.py)
            )
            + "\n"
        )


def write_design_hh_header(fn, f, hh):
    with open(fn, "w") as o:
        o.write(
            "  No;           Name; Side"
            + "".join(
                f";   hh{i}_str;   hh{i}_loc;   hh{i}_wid"
                for i in range(1, max(hh.nfunctions_top, hh.nfunctions_bot) + 1)
            )
            + "\n"
        )


def write_design_hh_data(fn, d, foil):
    if d == 0:
        return
    with open(fn, "a") as f:
        f.write(
            f"{d:5d};{foil.name[:15]}~{d};  Top"
            + "".join(
                f";{h.strength:10.7f};{h.location:10.7f};{h.width:10.7f}"
                for h in foil.top_hh.hhs
            )
            + f"\n{d:5d};{foil.name[:15]}~{d};  Bot"
            + "".join(
                f";{h.strength:10.7f};{h.location:10.7f};{h.width:10.7f}"
                for h in foil.bot_hh.hhs
            )
            + "\n"
        )


def get_status_color(g):
    return (
        (COLOR_GOOD, " PASS ")
        if g == Q_GOOD
        else (
            (COLOR_NORMAL, " OK   ")
            if g == Q_OK
            else ((COLOR_WARNING, " WARN ") if g == Q_BAD else (COLOR_ERROR, " FAIL "))
        )
    )


def print_improvement(ops, geots, oprs, g_res, u_flap, f_angs, dyn_done):
    if len(oprs):
        print_colored(COLOR_FEATURE, "\n" + "-" * 105 + "\n")
        print_colored(
            COLOR_FEATURE,
            " OP | MODE | ALPHA  |   CL   |    CD    |   L/D   "
            + ("| FLAP  " if u_flap else "")
            + "|| OBJECTIVE    |   DELTA   | IMPROVEMENT | STAT \n"
            + "-" * 105
            + "\n",
        )
    for i, (sp, op, ang) in enumerate(zip(ops, oprs, f_angs)):
        print_colored(
            COLOR_PALE, f" {i + 1:02d} | {' CL ' if sp.spec_cl else 'ALFA'} | "
        )
        print_colored(COLOR_NORMAL, f"{op.alpha:6.2f} | {op.cl:6.3f} | {op.cd:8.5f} | ")
        print_colored(
            COLOR_NORMAL if op.cl > 0.05 and op.cd > 0 else COLOR_PALE,
            f"{op.cl / op.cd:7.2f} "
            if op.cl > 0.05 and op.cd > 0 and op.cl / op.cd <= 999.9
            else (
                f"{op.cl / op.cd:7.1f} " if op.cl > 0.05 and op.cd > 0 else "  ---   "
            ),
        )
        if u_flap:
            print_colored(COLOR_NORMAL, f"| {ang:5.1f} ")
        print_colored(COLOR_FEATURE, "|| ")
        d, dev, g = get_op_improvement(sp, op)
        c_id, s_txt = get_status_color(g)
        obj = (
            sp.optimization_type.replace("target-", "TARG ")
            .replace("min-", "MIN ")
            .replace("max-", "MAX ")
            .replace("xtr", "XTR")
            .upper()
            .ljust(12)
        )
        print_colored(COLOR_PALE, f"{obj} | {d:+9.4f} | ")
        print_colored(
            c_id, f"{dev:+10.1f}% | " if abs(dev) < 99.9 else f"{dev:+10.0f}% | "
        )
        print_colored(c_id, s_txt + "\n")
    if len(geots):
        print_colored(COLOR_FEATURE, "-" * 105 + "\n")
        for i, g_s in enumerate(geots):
            val, (d, dev, g) = (
                g_res.maxt if g_s.type == "thickness" else g_res.maxc,
                get_geo_improvement_info(g_s, g_res),
            )
            print_colored(
                COLOR_PALE, f" G{i + 1:d} | {g_s.type.upper()[:10].ljust(10)} | "
            )
            print_colored(COLOR_NORMAL, f"{val:6.4f} (y/c)".ljust(35))
            print_colored(COLOR_FEATURE, "|| ")
            print_colored(COLOR_PALE, f"TARGET       | {d:+9.5f} | ")
            c_id, s_txt = get_status_color(g)
            if g == Q_GOOD and abs(dev) < 0.1:
                print_colored(c_id, "  LOCKED   ".ljust(13) + "| ")
            else:
                print_colored(
                    c_id,
                    f"{dev:+10.1f}% | " if abs(dev) < 99.9 else f"{dev:+10.0f}% | ",
                )
            print_colored(c_id, s_txt + "\n")
    print_colored(COLOR_FEATURE, "=" * 105 + "\n")


def write_airfoil_flapped(f, fsp, f_angs, auto):
    from geom_core import airfoil_read
    from solver_xfoil import run_xfoil_process, get_unique_temp_filename
    from utils_logger import filename_stem
    import os

    for a_raw in set(f_angs):
        # --- [FIX 1] Round to 4 decimals to prevent Fortran buffer overflows ---
        a = round(float(a_raw), 4) 
        
        if abs(a) > 0.0001:
            base_tmp = get_unique_temp_filename().replace(".dat", "")
            tin = f"{base_tmp}_in_{a}.dat"
            tout = f"{base_tmp}_out_{a}.dat"
            
            airfoil_write(tin, f)
            run_xfoil_process(
                [
                    f"LOAD {tin}",
                    "GDES",
                    "FLAP",
                    f"{fsp.x_flap:.4f}",
                    f"{fsp.y_flap:.4f}",
                    f"{a:.4f}",
                    "exec",  # Ensure XFOIL executes the flap before paneling
                    "",
                    "PANE",
                    f"SAVE {tout}",
                    "QUIT",
                ]
            )
            try:
                # --- [FIX 2] Prevent 'my_stop' crash if Fortran failed to save ---
                if not os.path.exists(tout):
                    continue 
                    
                nm, x, y = airfoil_read(tout)
                f_flp = copy.deepcopy(f)
                f_flp.x, f_flp.y, f_flp.name = (
                    x,
                    y,
                    airfoil_name_flapped(f, a) if auto else f.name,
                )
                tdir = (
                    commons.output_dir_final
                    if hasattr(commons, "output_dir_final") and commons.output_dir_final
                    else ""
                )
                cn = filename_stem(f_flp.name)
                fp = os.path.join(tdir, cn + ".dat") if tdir else f_flp.name + ".dat"
                print_airfoil_write(tdir, cn + ".dat", "dat", True)
                airfoil_write(fp, f_flp)
            except Exception as e:
                pass
            finally:
                if os.path.exists(tin):
                    os.remove(tin)
                if os.path.exists(tout):
                    os.remove(tout)


def write_performance_summary(sps, xfo, oprs, f_angs):
    with open(path_join(commons.design_subdir, "Performance_Summary.dat"), "w") as f:
        f.write(
            " Optimal airfoil performance summary\n\n i   alpha     CL        CD       Cm    Top Xtr Bot Xtr   Re      Mach    ncrit     flap\n -- ------- -------- --------- -------- ------- ------- ------- -------- ------- -----------\n"
        )
        for i, (s, op, a) in enumerate(zip(sps, oprs, f_angs)):
            f.write(
                f"{i + 1:2d}   {op.alpha:8.3f}   {op.cl:9.4f}    {op.cd:10.5f} {op.cm:9.4f}   {op.xtrt:8.4f}   {op.xtrb:8.4f} {s.re.number:9.2E}     {s.ma.number:8.3f}     {s.ncrit if s.ncrit != -1 else xfo.ncrit:7.1f}   {f'{a:6.2f} opt' if s.flap_optimize else (f'{a:6.2f} fix' if a != 0 else '   -')}\n"
            )
