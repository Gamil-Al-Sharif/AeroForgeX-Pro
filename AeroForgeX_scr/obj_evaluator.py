# ==============================================================================
# FILE: obj_evaluator.py
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
# DESCRIPTION: Core Objective Evaluator with High-Speed Vector Caching and
#              Integer-Mapped Optimization Routing.
# ==============================================================================
from colorama import Fore, Style, init
import os, copy, math, numpy as np
from collections import OrderedDict
from utils_logger import (
    my_stop,
    print_action,
    print_warning,
    print_colored,
    print_header,
    print_colored_r,
    print_note,
    COLOR_FEATURE,
    COLOR_PALE,
    COLOR_GOOD,
    Q_GOOD,
    commons,
)
from geom_core import AirfoilType, get_geometry, eval_deviation_at_side
from geom_builder import (
    create_airfoil_hicks_henne,
    create_airfoil_bezier,
    create_airfoil_camb_thick,
    create_airfoil_cst,
    get_ndv_of_flaps,
    get_flap_angles_optimized,
    get_shape_spec,
    set_shape_spec,
    get_seed_foil,
)
from solver_neuralfoil import run_op_points
from obj_utils import (
    GeoResultType,
    eval_curvature_violations,
    eval_geometry_violations,
    write_design_op_points_header,
    write_design_op_points_data,
    write_design_geo_targets_header,
    write_design_geo_targets_data,
    write_design_coord_header,
    write_design_coord_data,
    write_design_bezier_header,
    write_design_bezier_data,
    write_design_hh_header,
    write_design_hh_data,
    print_improvement,
    write_performance_summary,
)
from report_generator import generate_report

_OPT_TYPE_MAP = {
    "min-sink": 1,
    "max-glide": 2,
    "min-drag": 3,
    "max-lift": 4,
    "max-xtr": 5,
    "target-drag": 6,
    "target-glide": 7,
    "target-lift": 8,
    "target-moment": 9,
}

try:
    from obj_utils import violation_stats_print
except:
    violation_stats_print = lambda: None
try:
    from solver_xfoil import xfoil_stats_print
except:
    xfoil_stats_print = lambda: None

OBJ_XFOIL_FAIL, OBJ_GEO_FAIL, EPSILON = 55.55, 1000.0, 1.0e-10
OBJ_SURROGATE_REJECT = 33.33  # SAP filter sentinel: surrogate predicts poor performance

# High-Speed Integer Enum Mapping for Optimization Types
OPT_MIN_SINK = 1
OPT_MAX_GLIDE = 2
OPT_MIN_DRAG = 3
OPT_MAX_LIFT = 4
OPT_MAX_XTR = 5
OPT_TGT_DRAG = 6
OPT_TGT_GLIDE = 7
OPT_TGT_LIFT = 8
OPT_TGT_MOMENT = 9
GEO_THICKNESS = 1
GEO_CAMBER = 2
GEO_MATCH = 3

# Fast execution cache to prevent duplicate geometry creation and solver calls
# Uses OrderedDict for O(1) LRU eviction (popitem(last=False) removes oldest entry)
_eval_cache = OrderedDict()


# =============================================================================
# MASTER EVALUATION STATE
# =============================================================================
class EvalState:
    def __init__(self):
        self.op_points_spec, self.geo_targets = [], []
        self.geo_constraints, self.curv_constraints, self.panel_options = (
            None,
            None,
            None,
        )
        self.xfoil_options, self.dynamic_weighting_spec, self.match_foil_spec = (
            None,
            None,
            None,
        )
        self.best_objective, self.best_foil, self.best_op_points_result = (
            1.0,
            None,
            None,
        )
        self.best_dv = None  # Tracks the optimal vector to bypass regen in logging
        self.progression_enabled, self.initial_aero_objective = False, None
        self.sap_enabled = False  # Surrogate-Assisted Pre-Screening toggle
        self.best_aero_objective, self.seed_geo_values, self.original_geo_targets = (
            None,
            {},
            [],
        )


_evs = EvalState()


def _map_opt_type(s):
    return _OPT_TYPE_MAP.get(s.lower(), 0)


def _map_geo_type(s):
    m = {"thickness": 1, "camber": 2, "match-foil": 3}
    return m.get(s.lower(), 0)


def set_eval_spec(esp):
    _evs.op_points_spec, _evs.geo_targets, _evs.geo_constraints = (
        esp.op_points_spec,
        esp.geo_targets,
        esp.geo_constraints,
    )
    _evs.curv_constraints, _evs.xfoil_options, _evs.panel_options = (
        esp.curv_constraints,
        esp.xfoil_options,
        esp.panel_options,
    )
    _evs.match_foil_spec, _evs.dynamic_weighting_spec = (
        esp.match_foil_spec,
        esp.dynamic_weighting_spec,
    )
    _evs.progression_enabled = (
        getattr(esp, "progression_spec", None) and esp.progression_spec.active
    )

    # Pre-compute integer enums to bypass slow string comparisons inside core math engine
    for sp in _evs.op_points_spec:
        sp._tid = _map_opt_type(sp.optimization_type)
    for gt in _evs.geo_targets:
        gt._tid = _map_geo_type(gt.type)

    # Pre-build flap angle mask arrays ONCE so get_flap_angles() is purely NumPy
    _evs._flap_opt_mask = np.array([op.flap_optimize for op in _evs.op_points_spec], dtype=bool)
    _evs._flap_default_angles = np.array([op.flap_angle for op in _evs.op_points_spec], dtype=np.float64)
    _evs.sap_enabled = getattr(esp, 'sap_enabled', False)


def get_eval_state():
    return _evs


def initialize_worker_state(esp, sf, ssp, gd):
    set_eval_spec(esp)
    set_shape_spec(sf, ssp)
    commons.show_details = False
    if gd:
        [setattr(commons, k, v) for k, v in gd.items()]
    _eval_cache.clear()


# =============================================================================
# GEOMETRY SYNTHESIS & PENALTIES
# =============================================================================
def create_airfoil(dv):
    f, tp, dvs = (
        AirfoilType(),
        get_shape_spec().type,
        dv[: len(dv) - get_ndv_of_flaps()],
    )
    if tp == 3:
        create_airfoil_camb_thick(dvs, f)
    elif tp == 2:
        create_airfoil_bezier(dvs, f)
    elif tp == 1:
        create_airfoil_hicks_henne(dvs, f)
    elif tp == 4:
        from geom_builder import composite_cst_handler

        composite_cst_handler.gen_foil(dvs, f, 150)
    return f


def get_flap_angles(dv):
    # Vectorized: pre-built mask arrays avoid Python loop on every evaluation
    out = _evs._flap_default_angles.copy()
    if np.any(_evs._flap_opt_mask):
        out[_evs._flap_opt_mask] = get_flap_angles_optimized(dv)
    return out


def geo_penalty_function(f):
    # CHEAP FIRST: O(1) thickness/camber bounds check (no spline traversal)
    if (
        _evs.geo_constraints.check_geometry
        and eval_geometry_violations(f, _evs.geo_constraints)[0]
    ):
        return OBJ_GEO_FAIL
    # EXPENSIVE SECOND: curvature spline traversal (only reached if geometry passes)
    if (
        _evs.curv_constraints.check_curvature
        and eval_curvature_violations(f, _evs.curv_constraints)[0]
    ):
        return OBJ_GEO_FAIL
    return 0.0


def geo_objective_results(f):
    r = GeoResultType()
    if _evs.match_foil_spec.active:
        r.match_top_deviation = eval_deviation_at_side(
            f,
            "Top",
            _evs.match_foil_spec.target_top_x,
            _evs.match_foil_spec.target_top_y,
        )
        r.match_bot_deviation = eval_deviation_at_side(
            f,
            "Bot",
            _evs.match_foil_spec.target_bot_x,
            _evs.match_foil_spec.target_bot_y,
        )
        return r
    r.maxt, r.xmaxt, r.maxc, r.xmaxc = get_geometry(f)
    if f.is_bezier_based:
        from shape_functions_param import bezier_curvature

        r.top_curv_le, r.top_curv_te = (
            bezier_curvature(f.top_bezier, 0.0),
            bezier_curvature(f.top_bezier, 1.0),
        )
        r.bot_curv_le, r.bot_curv_te = (
            bezier_curvature(f.bot_bezier, 0.0),
            bezier_curvature(f.bot_bezier, 1.0),
        )
    elif getattr(f.top, "curvature", None) is not None and len(f.top.curvature):
        r.top_curv_le, r.top_curv_te = f.top.curvature[0], f.top.curvature[-1]
        r.bot_curv_le, r.bot_curv_te = f.bot.curvature[0], f.bot.curvature[-1]
    return r


# =============================================================================
# HIGH-SPEED MATH OBJECTIVE FUNCTIONS
# =============================================================================
def _get_aero_cv(sp, op):
    # Pure Integer routing (Massively faster than string evaluation)
    tid = sp._tid
    if tid == OPT_MIN_SINK:
        return (op.cd / (op.cl**1.5)) if op.cl > 0 else 1e9
    if tid == OPT_MAX_GLIDE:
        return (op.cd / op.cl) if op.cl > 0 else 1e9
    if tid == OPT_MIN_DRAG:
        return op.cd
    if tid == OPT_MAX_LIFT:
        return 1.0 / op.cl if op.cl > 0 else 1e9
    if tid == OPT_MAX_XTR:
        return 1.0 / (0.5 * (op.xtrt + op.xtrb) + 0.1)

    cv = (
        op.cd
        if tid == OPT_TGT_DRAG
        else (
            (op.cl / op.cd if op.cd != 0 else 0)
            if tid == OPT_TGT_GLIDE
            else (op.cl if tid == OPT_TGT_LIFT else op.cm)
        )
    )
    d = (
        max(0.0, cv - sp.target_value)
        if (sp.allow_improved_target and tid == OPT_TGT_DRAG)
        else (
            max(0.0, sp.target_value - cv)
            if sp.allow_improved_target
            else abs(cv - sp.target_value)
        )
    )

    if not sp.allow_improved_target:
        if tid == OPT_TGT_DRAG and d < 0.000004:
            d = 0.0
        if tid == OPT_TGT_GLIDE and d < 0.01:
            d = 0.0
        if tid in (OPT_TGT_LIFT, OPT_TGT_MOMENT) and d < 0.001:
            d = 0.0

    return (
        sp.target_value + d
        if tid == OPT_TGT_DRAG
        else (
            sp.target_value + d * 0.7
            if tid == OPT_TGT_GLIDE
            else (1.0 + d * 0.8 if tid == OPT_TGT_LIFT else d + 0.05)
        )
    )


def _get_geo_cv(gs, gr):
    tid = gs._tid
    progression_enabled = _evs.progression_enabled
    if tid == GEO_THICKNESS:
        cv, cor = gr.maxt, 1.2
    elif tid == GEO_CAMBER:
        cv, cor = gr.maxc, 0.7
    else:
        cv, cor = gr.match_top_deviation + gr.match_bot_deviation, 1.0
    tgt = (
        getattr(gs, "current_target", gs.target_value)
        if (progression_enabled and (tid == GEO_THICKNESS or tid == GEO_CAMBER))
        else gs.target_value
    )
    return gs.reference_value + abs(tgt - cv) * cor


def aero_objective_function(ops_res, dyn=False):
    # Use sum with generator for high speed iteration
    return sum(
        sp.weighting * _get_aero_cv(sp, op) * sp.scale_factor
        for sp, op in zip(_evs.op_points_spec, ops_res)
        if not dyn or sp.dynamic_weighting
    )


def geo_objective_function(gr, dyn=False):
    if not _evs.geo_targets:
        return 0.0  # Fast bypass
    return sum(
        gs.weighting * _get_geo_cv(gs, gr) * gs.scale_factor
        for gs in _evs.geo_targets
        if not dyn or gs.dynamic_weighting
    )


def _surrogate_screen(f, xo):
    """Fast NeuralFoil pre-screen: returns estimated aero objective or -1.0 if unavailable."""
    try:
        from solver_router import run_neuralfoil_analysis, check_neuralfoil_available
        if not check_neuralfoil_available():
            return -1.0
        screen_res = run_neuralfoil_analysis(f, xo, _evs.op_points_spec)
        if any(not r.converged for r in screen_res):
            return OBJ_SURROGATE_REJECT
        return aero_objective_function(screen_res)
    except Exception:
        return -1.0


def objective_function(dv):
    f = create_airfoil(dv)
    gp = geo_penalty_function(f)
    if gp >= OBJ_GEO_FAIL:
        return gp  # Fatal geometry violation -> Hard exit

    # =================================================================
    # SURROGATE-ASSISTED PRE-SCREENING (SAP) FILTER
    # NeuralFoil screens candidates in <1ms. Only top shapes proceed to
    # slow XFOIL subprocess. Active only when solver is XFOIL and SAP enabled.
    # =================================================================
    sap_enabled = getattr(_evs, 'sap_enabled', False)
    if sap_enabled and _evs.best_objective < 1.0:
        xo_screen = _make_xfoil_options()
        sap_val = _surrogate_screen(f, xo_screen)
        # If surrogate predicts 2× worse than current best, soft-reject
        if 0 < sap_val < OBJ_SURROGATE_REJECT and sap_val > _evs.best_objective * 2.0:
            return OBJ_SURROGATE_REJECT

    shape_spec = get_shape_spec()
    op_res = run_op_points(
        f,
        _make_xfoil_options(),
        shape_spec.flap_spec,
        get_flap_angles(dv),
        _evs.op_points_spec,
    )
    if any(not r.converged for r in op_res):
        return OBJ_XFOIL_FAIL

    a = aero_objective_function(op_res)
    g = geo_objective_function(geo_objective_results(f))
    obj = a + g + gp

    if obj < _evs.best_objective:
        (
            _evs.best_objective,
            _evs.best_foil,
            _evs.best_op_points_result,
            _evs.best_dv,
        ) = obj, f, op_res, dv.copy()
        if _evs.progression_enabled and (
            _evs.best_aero_objective is None or a < _evs.best_aero_objective
        ):
            _evs.best_aero_objective = a
            _update_geometry_targets(a)
    return obj


def evaluate_design_pymoo(dv):
    # Vector-Hash Caching Protocol (Eliminates PyMoo Redundant Evaluations)
    prec = getattr(_evs.xfoil_options, "cache_prec", 6) if (_evs is not None and getattr(_evs, "xfoil_options", None) is not None) else 6
    h_key = np.round(dv, int(prec)).tobytes()
    cached = _eval_cache.get(h_key)
    if cached is not None:
        # Move to end to mark as recently used
        _eval_cache.move_to_end(h_key)
        return cached


    f_val = objective_function(dv)
    res = (f_val, 1.0 if f_val >= OBJ_XFOIL_FAIL else -1.0)

    # LRU eviction: drop oldest 10% instead of clearing entire cache
    # Prevents the cold-start penalty of a full cache wipe
    if len(_eval_cache) >= 50000:
        evict_count = 5000
        for _ in range(evict_count):
            _eval_cache.popitem(last=False)
    _eval_cache[h_key] = res
    return res


# =============================================================================
# SEED CALIBRATION & PROGRESSION ENGINE
# =============================================================================
def eval_seed_scale_objectives(sf):
    print_action(
        "Calibrating absolute evaluation matrix; scaling Seed Objective Function to 1.0"
    )
    op_res = run_op_points(
        sf,
        type("opts", (), {**_evs.xfoil_options.__dict__, "show_details": False})(),
        get_shape_spec().flap_spec,
        np.array([op.flap_angle for op in _evs.op_points_spec]),
        _evs.op_points_spec,
    )
    gr = geo_objective_results(sf)
    _evs.seed_geo_values.clear()

    for gs in _evs.geo_targets:
        v = (
            gr.maxt
            if gs.type == "thickness"
            else (
                gr.maxc
                if gs.type == "camber"
                else gr.match_top_deviation + gr.match_bot_deviation
            )
        )
        gs.seed_value, gs.reference_value = v, (0.0 if gs.type == "match-foil" else v)
        if _evs.progression_enabled and gs.type in ["thickness", "camber"]:
            if not hasattr(gs, "original_target"):
                gs.original_target = gs.target_value
            gs.current_target = v
        if gs.target_value < 0.0:
            gs.target_value = v * abs(gs.target_value)
            if _evs.progression_enabled:
                gs.original_target = gs.target_value

        cor = 1.2 if gs.type == "thickness" else (0.7 if gs.type == "camber" else 1.0)
        den = gs.reference_value + abs(gs.target_value - v) * cor
        gs.scale_factor = 1.0 / den if den != 0.0 else 1.0
        if den == 0.0:
            print_warning(
                f"Zero denominator for target '{gs.type}'. Scale factor set to 1.0."
            )

    if _evs.progression_enabled:
        _evs.best_aero_objective = _evs.initial_aero_objective = (
            aero_objective_function(op_res)
        )

    for i, (sp, op) in enumerate(zip(_evs.op_points_spec, op_res)):
        if not op.converged:
            if sp.ma.number > 0.0 and not sp.spec_cl:
                print_note(
                    "High Alpha + Mach > 0.0 destabilizes initial XFOIL boundary layers.",
                    7,
                )
            my_stop(
                f"Seed evaluation failed: XFOIL cannot converge operating point {i + 1}."
            )
        if op.cl <= 0.0 and sp.optimization_type in ["min-sink", "max-glide"]:
            my_stop(
                f"OP {i + 1} has Negative Lift. Cannot execute {sp.optimization_type}."
            )
        if sp.optimization_type.startswith("target") and sp.target_value < 0.0:
            cv = (
                op.cd
                if sp.optimization_type == "target-drag"
                else (
                    op.cl / op.cd
                    if op.optimization_type == "target-glide"
                    else (op.cl if sp.optimization_type == "target-lift" else op.cm)
                )
            )
            sp.target_value = cv * abs(sp.target_value)
        sp.scale_factor = 1.0 / _get_aero_cv(sp, op)


def _update_geometry_targets(bst_a):
    if not _evs.progression_enabled or _evs.initial_aero_objective is None:
        return
    imp = (
        min(
            1.0,
            max(
                0.0, (_evs.initial_aero_objective - bst_a) / _evs.initial_aero_objective
            ),
        )
        if _evs.initial_aero_objective != 0
        else 0.0
    )
    for g in _evs.geo_targets:
        if g.type in ["thickness", "camber"]:
            g.current_target = g.seed_value + (g.original_target - g.seed_value) * imp
    if commons.show_details and imp > 0.0:
        print_note(
            f"Gradual Progression Triggered: Aero Improved {imp * 100:.1f}%. Morphing geometric bounds."
        )


# =============================================================================
# DATA LOGGING & PROGRESS TRACKING
# =============================================================================
def write_progress(dv, cnt):
    if cnt == 0:
        print_action("Generating baseline CSV logs in " + commons.design_subdir)
    elif commons.show_details:
        print()

    shape_spec = get_shape_spec()
    tp = shape_spec.type

    # Determine the foil and flap angles
    if cnt == 0:
        f = get_seed_foil()
        # For generation 0, flap angles are the default values from each operating point
        fa = np.array([op.flap_angle for op in _evs.op_points_spec], dtype=np.float64)
    else:
        f = create_airfoil(dv)
        fa = get_flap_angles(dv)
        f.name = commons.output_prefix

    # Prepare XFOIL/NeuralFoil options
    xo = type(
        "opts",
        (),
        {
            **_evs.xfoil_options.__dict__,
            "show_details": False,
            "exit_if_unconverged": False,
            "reinitialize": _evs.xfoil_options.reinitialize if cnt > 0 else False,
        },
    )()

    # Run solver (use cached results if available for best design)
    if (
        cnt > 0
        and _evs.best_op_points_result is not None
        and np.allclose(dv, _evs.best_dv, atol=1e-10)
    ):
        op_res = _evs.best_op_points_result
    else:
        op_res = run_op_points(f, xo, shape_spec.flap_spec, fa, _evs.op_points_spec)

    # CSV file paths
    fs = {
        "op": os.path.join(commons.design_subdir, "Design_OpPoints.csv"),
        "bez": os.path.join(commons.design_subdir, "Design_Beziers.csv"),
        "hh": os.path.join(commons.design_subdir, "Design_Hicks.csv"),
        "coord": os.path.join(commons.design_subdir, "Design_Coordinates.csv"),
        "geo": os.path.join(commons.design_subdir, "Design_GeoTargets.csv"),
    }

    # Write headers on first call
    if cnt == 0:
        write_design_op_points_header(fs["op"])
        if len(_evs.geo_targets):
            write_design_geo_targets_header(fs["geo"])
        write_design_coord_header(fs["coord"], f)
        if tp == 2:
            write_design_bezier_header(fs["bez"], f)
        elif tp == 1:
            write_design_hh_header(fs["hh"], f, shape_spec.hh)

    # Write operating point data (includes CM and flap)
    write_design_op_points_data(fs["op"], cnt, _evs.op_points_spec, op_res, fa)

    # Write geometry target data
    gr = geo_objective_results(f)
    if len(_evs.geo_targets):
        write_design_geo_targets_data(fs["geo"], cnt, _evs.geo_targets, gr)

    # Write coordinates – always write for every generation
    write_design_coord_data(fs["coord"], cnt, f)

    # Write shape‑specific data
    if tp == 2:
        write_design_bezier_data(fs["bez"], cnt, f)
    elif tp == 1:
        write_design_hh_data(fs["hh"], cnt, f)

    # Progression and dynamic weighting (unchanged)
    if _evs.progression_enabled and cnt > 0:
        a = aero_objective_function(op_res)
        if _evs.best_aero_objective is None or a < _evs.best_aero_objective:
            _evs.best_aero_objective = a
            _update_geometry_targets(a)

    dd = (
        do_dynamic_weighting(cnt, _evs.dynamic_weighting_spec, op_res, gr)
        if _evs.dynamic_weighting_spec.active
        else False
    )

    if commons.show_details and cnt > 0:
        print_improvement(
            _evs.op_points_spec,
            _evs.geo_targets,
            op_res,
            gr,
            shape_spec.flap_spec.use_flap,
            fa,
            dd,
        )
        violation_stats_print()
        xfoil_stats_print()
        print()


def write_final_results(dv, fmin):
    print(
        f"\n{Fore.MAGENTA}{Style.BRIGHT}[ SYSTEM ]{Style.RESET_ALL} Global Optimization Matrix Converged. Final Objective Improvement: ",
        end="",
    )
    print_colored_r(8, '(F7.4,"%")', Q_GOOD, (1.0 - fmin) * 100.0)
    print()
    ff, fa = create_airfoil(dv), get_flap_angles(dv)
    print_improvement(
        _evs.op_points_spec,
        _evs.geo_targets,
        run_op_points(
            ff, _evs.xfoil_options, get_shape_spec().flap_spec, fa, _evs.op_points_spec
        ),
        geo_objective_results(ff),
        get_shape_spec().flap_spec.use_flap,
        fa,
        False,
    )
    print()
    return ff, fa


# =============================================================================
# DYNAMIC WEIGHTING ENGINE
# =============================================================================
def do_dynamic_weighting(cnt, dw_spec, ops_res, gr):
    if (
        cnt < dw_spec.start_with_design
        or (cnt - dw_spec.start_with_design) % dw_spec.frequency != 0
    ):
        return False
    dyn_tgts = [s for s in _evs.op_points_spec if s.dynamic_weighting] + [
        g for g in _evs.geo_targets if g.dynamic_weighting
    ]
    if not dyn_tgts:
        return False

    for sp, op in zip(_evs.op_points_spec, ops_res):
        sp.new_weighting = sp.weighting
        if sp.dynamic_weighting and op.converged:
            tp, cv = (
                sp.optimization_type,
                op.cd
                if sp.optimization_type == "target-drag"
                else (
                    (op.cl / op.cd if op.cd != 0 else 0)
                    if sp.optimization_type == "target-glide"
                    else (op.cl if sp.optimization_type == "target-lift" else op.cm)
                ),
            )
            d = (
                max(0.0, cv - sp.target_value)
                if (sp.allow_improved_target and tp == "target-drag")
                else (
                    max(0.0, sp.target_value - cv)
                    if sp.allow_improved_target
                    else abs(cv - sp.target_value)
                )
            )
            if not sp.allow_improved_target:
                if tp == "target-drag" and d < 0.000004:
                    d = 0.0
                if tp == "target-glide" and d < 0.01:
                    d = 0.0
                if tp in ["target-lift", "target-moment"] and d < 0.001:
                    d = 0.0
            denom = (
                sp.target_value
                if tp in ["target-drag", "target-glide"]
                else (
                    1.0 + sp.target_value
                    if tp == "target-lift"
                    else 0.05 + sp.target_value
                )
            )
            sp.dev = (d / denom) * 100.0 if denom != 0 else 0.0
        else:
            sp.dev = 0.0

    for gs in _evs.geo_targets:
        gs.new_weighting = gs.weighting
        if gs.dynamic_weighting:
            cv = gr.maxt if gs.type == "thickness" else gr.maxc
            gs.dev = (
                ((cv - gs.target_value) / gs.target_value) * 100.0
                if gs.target_value != 0
                else 0.0
            )
        else:
            gs.dev = 0.0

    devs = [abs(t.dev) for t in dyn_tgts]
    avg_d, med_d = np.mean(devs), np.median(devs)
    print()
    print_colored(
        COLOR_FEATURE, " - Triggering Dynamic Weighting Restructure: ", end=""
    )
    print_colored(
        COLOR_PALE,
        f"Tracking {len(dyn_tgts)} targets. System Average Deviation: {avg_d:.1f}%. Median: {med_d:.1f}%\n\n",
    )
    if cnt == 0:
        return True

    for t in dyn_tgts:
        t.new_weighting = abs(t.dev) / avg_d if avg_d > 0 else 0.0
    mn_w, mx_w = (
        min(t.new_weighting for t in dyn_tgts),
        max(t.new_weighting for t in dyn_tgts),
    )
    if mx_w == mn_w:
        mx_w = mn_w + 1.0

    wd = (dw_spec.max_weighting - dw_spec.min_weighting) / (
        (1.3**2) if avg_d < 0.1 else (1.3 if avg_d < 0.5 else 1.0)
    )
    mw = dw_spec.min_weighting + wd

    for t in dyn_tgts:
        t.new_weighting = dw_spec.min_weighting + (t.new_weighting - mn_w) * (
            wd / (mx_w - mn_w)
        )
        ep = False
        if hasattr(t, "optimization_type"):
            if abs(t.dev) > avg_d * 3.0 and avg_d > 0.3:
                t.new_weighting *= dw_spec.extra_punch**2
                ep = True
            elif abs(t.dev) > avg_d * 1.5 and avg_d > 0.1:
                t.new_weighting *= dw_spec.extra_punch
                ep = True
            elif getattr(t, "extra_punch", False):
                t.new_weighting = max(t.new_weighting, mw * 0.9)
        else:
            if abs(t.dev) > med_d * 1.5 and avg_d > 0.2:
                t.new_weighting *= dw_spec.extra_punch
                ep = True
            elif getattr(t, "extra_punch", False):
                t.new_weighting = max(
                    t.new_weighting, (mw + dw_spec.min_weighting) / 2.0
                )
        t.extra_punch, t.new_weighting = (
            ep,
            t.new_weighting * getattr(t, "weighting_user", 1.0),
        )

    sf = (
        aero_objective_function(ops_res, True) + geo_objective_function(gr, True)
    ) / sum(
        t.new_weighting
        * (
            _get_aero_cv(t, o) * t.scale_factor
            if hasattr(t, "optimization_type")
            else _get_geo_cv(t, gr) * t.scale_factor
        )
        for t, o in zip(dyn_tgts, ops_res + [None] * len(_evs.geo_targets))
    )
    for t in dyn_tgts:
        t.weighting = t.new_weighting * sf
    return True





def _make_xfoil_options():
    opts = _evs.xfoil_options.__dict__.copy()
    opts["show_details"] = False
    opts["exit_if_unconverged"] = True
    return type("opts", (), opts)()
