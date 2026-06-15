# ==============================================================================
# FILE: config_manager.py
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
# DESCRIPTION: Universal configuration parser. Capable of seamlessly digesting
#              legacy (v1/v2) and modern (v4) JSON/Namelist optimization matrices.
# ==============================================================================
import os, sys, re, json, argparse, numpy as np
from pathlib import Path
from utils_logger import (
    my_stop,
    filename_stem,
    print_header,
    print_action,
    print_warning,
    print_error,
    set_show_details,
    print_note,
    commons,
)
from obj_utils import (
    EvalSpecType,
    GeoTargetType,
    GeoConstraintsType,
    CurvConstraintsType,
)
from solver_xfoil import OpPointSpecType, FlapSpecType, ReType
from geom_core import PanelOptionsType
from geom_builder import ShapeSpecType, HICKS_HENNE, BEZIER, CAMB_THICK, CST
from opt_engine import OptimizeSpecType
from solver_neuralfoil import set_aero_solver

MAX_NOP, NOT_DEF_D = 45, -99999999.0


# =============================================================================
# UNIVERSAL PARSER ENGINE (JSON & Legacy Namelist)
# =============================================================================
class InputFileParser:
    def __init__(self, fn):
        if not fn or not os.path.exists(fn):
            print(
                f"\n\033[91m\033[1m[ FATAL ERROR ]\033[0m Configuration file not found: \033[93m'{fn}'\033[0m"
            )
            print(
                "                Please verify the file path, spelling, and directory.\n"
            )
            sys.exit(1)
        self.data = self._parse(fn)

    def _parse(self, fn):
        with open(fn, "r") as f:
            c = f.read().strip()
        if c.startswith("{"):
            try:
                return self._lower(json.loads(c))
            except json.JSONDecodeError as e:
                # Fault-Tolerant Auto-Fix for trailing commas before brackets
                c_clean = re.sub(r",\s*([}\]])", r"\1", c)
                try:
                    return self._lower(json.loads(c_clean))
                except json.JSONDecodeError:
                    print(
                        f"\n\033[91m\033[1m[ SYNTAX ERROR ]\033[0m Invalid formatting in config: '{fn}'\n                 \033[93m{str(e)}\033[0m\n                 Ensure lists/dicts have proper commas.\n"
                    )
                    sys.exit(1)

        d = {}
        [
            d.setdefault(g.lower(), {}).update({k.strip().lower(): self._pval(v.strip())})
            for g, b in re.findall(r"&(\w+)\s*(.*?)\s*/", re.sub(r"!.*", "", c), re.S)
            for assign in b.replace("\n", ";").replace(",", ";").split(";")
            if "=" in assign
            for k, v in [assign.split("=", 1)]
        ]
        return d

    def _lower(self, d):
        return (
            {k.lower(): self._lower(v) for k, v in d.items()}
            if isinstance(d, dict)
            else d
        )

    def _pval(self, v):
        v = v.strip()
        return (
            v[1:-1]
            if v.startswith(("'", '"'))
            else (
                True
                if v.lower() in [".true.", "t", "true"]
                else (
                    False
                    if v.lower() in [".false.", "f", "false"]
                    else (
                        float(v.lower().replace("d", "e"))
                        if "." in v or "e" in v.lower() or "d" in v.lower()
                        else (int(v) if v.isdigit() else v)
                    )
                )
            )
        )

    def get(self, groups, keys, default=None):
        """Dynamic Alias Resolver for scalar values."""
        if isinstance(groups, str):
            groups = (groups,)
        if isinstance(keys, str):
            keys = (keys,)
        for g in groups:
            if g in self.data:
                for k in keys:
                    if k in self.data[g]:
                        return self.data[g][k]
        return default

    def get_arr(self, groups, keys, L, default=None):
        """Universal Array Resolver: Seamlessly maps new arrays or old key(1) indexed formats."""
        if L == 0:
            return []
        if isinstance(groups, str):
            groups = (groups,)
        if isinstance(keys, str):
            keys = (keys,)

        # 1. Attempt to grab full array using modern syntax
        for g in groups:
            if g in self.data:
                for k in keys:
                    if k in self.data[g]:
                        v = self.data[g][k]
                        if isinstance(v, list):
                            return v[:L] + [default] * (L - len(v))
                        if isinstance(v, dict):
                            return [v.get(str(i), v.get(i, default)) for i in range(L)]
                        if v is not None:
                            return [v] * L

        # 2. Fallback to extracting Legacy indexed variables e.g., 'aero_target_mode(1)'
        arr = []
        for i in range(L):
            found = False
            for g in groups:
                if g in self.data:
                    for k in keys:
                        idx_k = f"{k}({i + 1})"
                        if idx_k in self.data[g]:
                            arr.append(self.data[g][idx_k])
                            found = True
                            break
                if found:
                    break
            if not found:
                arr.append(default)
        return arr


# =============================================================================
# CLI HANDLERS & MASTER CONFIG EXTRACTOR
# =============================================================================
def parse_command_line():
    p = argparse.ArgumentParser(description="AeroForgeX Aerodynamic Setup")
    p.add_argument("-i", "--input", default="")
    p.add_argument("-o", "--output", default="")
    p.add_argument("-r", "--reynolds", type=float, default=0.0)
    p.add_argument("-a", "--airfoil", default="")
    return (
        argparse.Namespace(input=sys.argv[1], output="", reynolds=0.0, airfoil="")
        if len(sys.argv) == 2 and not sys.argv[1].startswith("-")
        else p.parse_known_args()[0]
    )


def run_mode_from_command_line():
    return (
        commons.MODE_AIRFOIL_OPTIMIZER
        if "-m" in sys.argv and sys.argv[sys.argv.index("-m") + 1] == "ao"
        else commons.MODE_NORMAL
    )


def print_usage():
    print(
        "Usage: AeroForgeX input_file [OPTIONS]\nOptions:\n  -i input_file\n  -o output_prefix\n  -r reynolds\n  -a airfoil_file"
    )


def read_inputs(inp_file):
    args = parse_command_line()
    inp, c_out, c_re, c_af = (
        inp_file or args.input,
        args.output,
        args.reynolds,
        args.airfoil,
    )
    if not inp:
        print(
            f"\n\033[91m\033[1m[ FATAL ERROR ]\033[0m No configuration file specified."
        )
        print_usage()
        sys.exit(1)

    nml, ev_sp, shp_sp, opt_opts = (
        InputFileParser(inp),
        EvalSpecType(),
        ShapeSpecType(),
        OptimizeSpecType(),
    )

    g = ("opt_opts", "optimization_options")
    af_json = nml.get(g, ("foil_file", "airfoil_file"), "")
    af = c_af or (os.path.join(*af_json) if isinstance(af_json, list) else af_json)

    # --- PRE-FLIGHT DIAGNOSTIC: Seed Airfoil Validation ---
    if not af or not os.path.exists(af):
        print(
            f"\n\033[91m\033[1m[ FATAL ERROR ]\033[0m Seed airfoil geometry not found: \033[93m'{af}'\033[0m"
        )
        print(
            f"                Check the 'foil_file' parameter inside \033[96m{inp}\033[0m.\n"
        )
        sys.exit(1)

    od = nml.get(g, ("out_dir", "output_directory"), "")
    ad = nml.get(g, ("auto_dir", "auto_output_dir"), False)
    bd = nml.get(g, ("base_dir", "base_output_folder"), "Outputs")
    opx = c_out or nml.get(g, ("out_prefix", "output_prefix"), filename_stem(inp))
    sf = nml.get(g, ("shape_func", "shape_functions"), "hicks-henne")
    asolv = nml.get(g, ("solver", "aero_solver"), "xfoil")

    # --- PRE-FLIGHT DIAGNOSTIC: Engine Validation ---
    shp_map = {
        "bezier": BEZIER,
        "hicks-henne": HICKS_HENNE,
        "camb-thick": CAMB_THICK,
        "cst": CST,
    }
    if sf.lower() not in shp_map:
        print(
            f"\n\033[91m\033[1m[ FATAL ERROR ]\033[0m Invalid shape parameterization engine requested: \033[93m'{sf}'\033[0m"
        )
        print(
            f"                Supported engines: \033[96m'cst', 'bezier', 'hicks-henne', 'camb-thick'\033[0m\n"
        )
        sys.exit(1)

    shp_sp.type, shp_sp.type_as_text = shp_map[sf.lower()], sf.lower()

    # ---------------------------------------------------------
    # DYNAMIC ALGORITHM ROUTING & FOLDER INJECTION
    # ---------------------------------------------------------
    algo_int = nml.get(
        ("optim_set", "optimizer_settings", "particle_swarm_options"), "type", 1
    )
    algo_str = {1: "DE", 2: "jDE", 3: "SHADE"}.get(algo_int, "DE")
    opt_opts.algorithm_name = algo_str

    commons.output_dir_final = (
        os.path.join(od or bd, opx, Path(af).stem, algo_str, sf, asolv) if ad else od
    )
    commons.output_prefix_base = opx
    set_aero_solver(asolv)
    ev_sp.aero_solver_name = asolv

    sh_dtl = nml.get(g, ("verbose", "show_details"), True)
    w_end = nml.get(g, ("wait", "wait_at_end"), False)
    opt_opts.cpu_threads = nml.get(g, ("threads", "cpu_threads"), -1)
    set_show_details(sh_dtl)

    if sh_dtl:
        print_header(f"Processing Config: {inp}")
        print_action(
            "Aero Engine",
            "NeuralFoil (AI)" if asolv.lower() == "neuralfoil" else "XFOIL",
        )
        print_action("Target Prefix", opx)
        print_action("Algorithm", algo_str)
    else:
        print_header("Processing   ", inp)

    _rd_bez(nml, shp_sp.bezier)
    _rd_hh(nml, shp_sp.hh)
    _rd_ct(nml, shp_sp.camb_thick)
    _rd_cst(nml, shp_sp.cst)
    _rd_op(nml, c_re, ev_sp, shp_sp.flap_spec)
    _rd_geo(nml, ev_sp.geo_targets)
    _rd_constr(nml, ev_sp.geo_constraints, shp_sp.flap_spec, ev_sp.curv_constraints)
    _rd_pso(nml, opt_opts.pso_options)
    _rd_pan(nml, ev_sp.panel_options)
    _rd_xfo(nml, ev_sp.xfoil_options)

    return af, opx, sh_dtl, w_end, ev_sp, shp_sp, opt_opts


# =============================================================================
# SUBSYSTEM CONFIGURATION READERS (Alias Mapped)
# =============================================================================
def _rd_op(n, re_cli, ev, fsp):
    g = ("op_conds", "operating_conditions")
    nop = n.get(g, ("num_pts", "num_operating_points", "noppoint"), 0)
    if nop > MAX_NOP:
        my_stop(f"Max OP points exceeded: {MAX_NOP}")

    rd = re_cli if re_cli > 0 else n.get(g, ("re_def", "re_default"), 400000.0)
    md = n.get(g, ("ma_def", "mach_default"), 0.0)

    mds = n.get_arr(g, ("mode", "aero_target_mode", "op_mode"), nop, "spec-cl")
    pts = n.get_arr(g, ("val", "aero_target_value", "op_point"), nop, 0.0)
    ncs = n.get_arr(g, ("ncrit", "ncrit_pt"), nop, -1.0)
    oty = n.get_arr(g, ("opt_type", "optimization_type"), nop, "target-drag")
    tgt = n.get_arr(g, ("tgt_val", "target_value"), nop, NOT_DEF_D)
    wt = n.get_arr(g, ("weight", "weighting"), nop, 1.0)
    re = n.get_arr(g, ("re", "reynolds"), nop, NOT_DEF_D)
    ma = n.get_arr(g, ("ma", "mach"), nop, NOT_DEF_D)

    uf = fsp.use_flap = n.get(g, "use_flap", False)
    fsp.x_flap = n.get(g, "x_flap", 0.75)
    fsp.y_flap = n.get(g, "y_flap", 0.0)
    fsp.y_flap_spec = n.get(g, "y_flap_spec", "y/c")

    fd = n.get(g, ("flap_def", "flap_angle_default"), 0.0)
    fa = n.get_arr(g, ("flap_ang", "flap_angle"), nop, NOT_DEF_D)
    fo = n.get_arr(g, ("flap_opt", "flap_optimize"), nop, False)

    ev.dynamic_weighting_spec.active = n.get(
        g, ("dyn_weight", "dynamic_weighting"), True
    )
    ds = n.get(g, ("dyn_spec", "dynamic_weighting_spec"), {})
    ev.dynamic_weighting_spec.min_weighting = ds.get(
        "min_w", ds.get("min_weighting", 0.6)
    )
    ev.dynamic_weighting_spec.max_weighting = ds.get(
        "max_w", ds.get("max_weighting", 1.4)
    )
    ev.dynamic_weighting_spec.extra_punch = ds.get("extra_punch", 1.2)
    ev.dynamic_weighting_spec.frequency = ds.get("frequency", 20)
    ev.dynamic_weighting_spec.start_with_design = ds.get("start_with_design", 10)

    ops, starts = [], []
    for i in range(nop):
        s = OpPointSpecType()
        s.spec_cl = str(mds[i]).lower() == "spec-cl"
        s.value, s.optimization_type, s.target_value, s.weighting_user, s.ncrit = (
            pts[i],
            str(oty[i]),
            tgt[i],
            wt[i],
            ncs[i],
        )
        s.re, s.ma = (
            ReType(re[i] if re[i] != NOT_DEF_D else rd, 1),
            ReType(ma[i] if ma[i] != NOT_DEF_D else md, 1),
        )
        s.flap_optimize, s.flap_angle = (
            (fo[i], fa[i] if fa[i] != NOT_DEF_D else fd) if uf else (False, 0.0)
        )
        if s.flap_optimize:
            starts.append(s.flap_angle)
        ops.append(s)
    ev.op_points_spec, fsp.ndv, fsp.start_flap_angle = (
        ops,
        len(starts),
        np.array(starts),
    )


def _rd_geo(n, gl):
    g = ("geo_tgts", "geometry_targets")
    nt = n.get(g, ("num_tgts", "num_geometry_targets", "ngeo_targets"), 0)

    t = n.get_arr(g, ("type", "target_type"), nt, "")
    v = n.get_arr(g, ("val", "target_value"), nt, 0.0)
    w = n.get_arr(g, ("weight", "weighting"), nt, 1.0)
    s = n.get_arr(g, ("str", "target_string"), nt, "")
    p = n.get_arr(g, ("preset", "preset_to_target"), nt, False)

    for i in range(nt):
        tgt = GeoTargetType()
        (
            tgt.type,
            tgt.target_value,
            tgt.weighting_user,
            tgt.target_string,
            tgt.preset_to_target,
        ) = str(t[i]).lower(), v[i], w[i], str(s[i]), p[i]
        gl.append(tgt)


def _rd_constr(n, gc, fsp, cc):
    g = ("constr", "constraints")
    gc.check_geometry = n.get(g, ("chk_geo", "check_geometry"), True)
    gc.symmetrical = n.get(g, ("sym", "symmetrical"), False)
    gc.min_te_angle = n.get(g, ("min_te_ang", "min_te_angle"), 2.0)
    gc.min_thickness = n.get(g, ("min_t", "min_thickness"), NOT_DEF_D)
    gc.max_thickness = n.get(g, ("max_t", "max_thickness"), NOT_DEF_D)
    gc.min_camber = n.get(g, ("min_c", "min_camber"), NOT_DEF_D)
    gc.max_camber = n.get(g, ("max_c", "max_camber"), NOT_DEF_D)
    fsp.min_flap_angle = n.get(g, ("min_flap", "min_flap_angle"), -5.0)
    fsp.max_flap_angle = n.get(g, ("max_flap", "max_flap_angle"), 15.0)
    _rd_curv(n, cc)


def _rd_curv(n, cc):
    g = ("curv", "curvature")
    cc.check_curvature = n.get(g, ("chk_curv", "check_curvature"), True)
    cc.auto_curvature = n.get(g, ("auto_curv", "auto_curvature"), True)
    cc.max_le_curvature_diff = n.get(g, ("max_le_diff", "max_le_curvature_diff"), 5.0)

    dt = n.get(g, ("curv_thr", "curv_threshold"), 0.1)
    ds = n.get(g, ("spike_thr", "spike_threshold"), 0.5)
    dte = n.get(g, ("max_te_c", "max_te_curvature"), 4.9999)

    cc.top.curv_threshold = cc.bot.curv_threshold = dt
    cc.top.spike_threshold = cc.bot.spike_threshold = ds
    cc.top.max_te_curvature = cc.bot.max_te_curvature = dte

    cc.top.max_curv_reverse = n.get(g, ("max_rev_t", "max_curv_reverse_top"), 0)
    cc.bot.max_curv_reverse = n.get(g, ("max_rev_b", "max_curv_reverse_bot"), 0)
    cc.top.max_spikes = n.get(g, ("max_spk_t", "max_spikes_top"), 0)
    cc.bot.max_spikes = n.get(g, ("max_spk_b", "max_spikes_bot"), 0)


def _rd_pso(n, p):
    g = ("optim_set", "optimizer_settings", "particle_swarm_options")
    p.algo = n.get(g, ("algo", "algorithm"), "lshade")
    p.pop = n.get(g, ("pop", "population_size"), 30)
    p.min_radius = n.get(g, ("min_r", "min_radius"), 0.001)
    p.max_iterations = n.get(g, ("gen", "max_generations", "max_iterations"), 500)
    p.max_speed = n.get(g, ("speed", "max_speed"), 0.1)
    p.init_attempts = n.get(g, ("init_att", "init_attempts"), 1000)
    p.convergence_profile = n.get(g, ("conv_prof", "convergence_profile"), "exhaustive")
    p.max_retries = n.get(g, ("retry", "max_retries"), 3)
    p.rescue_particle = n.get(g, ("rescue", "rescue_particles"), True)


def _rd_pan(n, p):
    g = ("panel_opts", "paneling_options")
    p.npoint = n.get(g, ("npt", "npoint"), 161)
    p.le_bunch = n.get(g, ("le_clust", "le_clustering", "le_bunch"), 0.86)
    p.te_bunch = n.get(g, ("te_clust", "te_clustering", "te_bunch"), 0.6)


def _rd_xfo(n, x):
    g = ("xfoil_opts", "xfoil_run_options")
    x.ncrit = n.get(g, "ncrit", 9.0)
    x.xtript = n.get(g, ("trip_t", "trip_loc_top", "xtript"), 1.0)
    x.xtripb = n.get(g, ("trip_b", "trip_loc_bot", "xtripb"), 1.0)
    x.viscous_mode = n.get(g, ("visc", "viscous_mode"), True)
    x.maxit = n.get(g, ("iter", "max_iterations", "bl_maxit"), 50)
    x.vaccel = n.get(g, ("vaccel", "convergence_acceleration"), 0.005)
    x.fix_unconverged = n.get(g, ("fix_unc", "fix_unconverged"), True)
    x.reinitialize = n.get(g, ("reinit", "reinitialize"), False)
    x.parallel_op = n.get(g, ("parallel_op", "parallel_op"), True)
    x.cache_prec = n.get(g, ("cache_prec", "cache_prec"), 6)
    x.nf_conf_threshold = n.get(g, ("nf_conf_threshold", "nf_conf_threshold"), 0.5)
    x.sap_enabled = n.get(g, ("sap_enabled", "sap_enabled"), True)


def _rd_bez(n, b):
    g = ("bez_opts", "bezier_options")
    b.ncp_top = n.get(g, ("ncp_t", "ncp_top"), 5)
    b.ncp_bot = n.get(g, ("ncp_b", "ncp_bot"), 5)
    b.initial_perturb = n.get(g, ("init_pert", "initial_perturb"), 0.1)


def _rd_cst(n, c):
    g = ("cst_opts", "cst_options")
    c.n_weights_top = n.get(g, ("n_t", "n_weights_top"), 6)
    c.n_weights_bot = n.get(g, ("n_b", "n_weights_bot"), 6)
    c.N1_top = n.get(g, ("n1_t", "n1_top"), 0.5)
    c.N2_top = n.get(g, ("n2_t", "n2_top"), 1.0)
    c.N1_bot = n.get(g, ("n1_b", "n1_bot"), 0.5)
    c.N2_bot = n.get(g, ("n2_b", "n2_bot"), 1.0)
    c.initial_perturb = n.get(g, ("init_pert", "initial_perturb"), 0.1)


def _rd_hh(n, h):
    g = ("hh_opts", "hicks_henne_options")
    h.nfunctions_top = n.get(g, ("n_t", "nfunctions_top"), 3)
    h.nfunctions_bot = n.get(g, ("n_b", "nfunctions_bot"), 3)
    h.initial_perturb = n.get(g, ("init_pert", "initial_perturb"), 0.1)
    h.smooth_seed = n.get(g, ("smooth", "smooth_seed"), False)


def _rd_ct(n, c):
    g = ("ct_opts", "camb_thick_options")
    c.thickness = n.get(g, ("thk", "thickness"), True)
    c.thickness_pos = n.get(g, ("thk_pos", "thickness_pos"), True)
    c.camber = n.get(g, ("cmb", "camber"), True)
    c.camber_pos = n.get(g, ("cmb_pos", "camber_pos"), True)
    c.le_radius = n.get(g, ("le_r", "le_radius"), True)
    c.le_radius_blend = n.get(g, ("le_b", "le_radius_blend"), True)
    c.initial_perturb = n.get(g, ("init_pert", "initial_perturb"), 0.1)
    c.ndv = sum(
        [
            c.thickness,
            c.thickness_pos,
            c.camber,
            c.camber_pos,
            c.le_radius,
            c.le_radius_blend,
        ]
    )


# =============================================================================
# SANITY & PHYSICS CHECKERS
# =============================================================================
def check_and_process_inputs(ev_sp, shp_sp, opt_opts):
    print_action("Sanitizing input parameters and enforcing mathematical consistency")
    dw, d_on = ev_sp.dynamic_weighting_spec, ev_sp.dynamic_weighting_spec.active

    # Weight Normalization
    for o in ev_sp.op_points_spec + ev_sp.geo_targets:
        if getattr(o, "weighting_user", 1.0) < 0:
            o.dynamic_weighting, o.weighting_user = (
                False,
                -getattr(o, "weighting_user", 1.0),
            )
        else:
            o.dynamic_weighting = d_on
    if not any(o.dynamic_weighting for o in ev_sp.op_points_spec):
        dw.active = False
    sm = sum(
        getattr(o, "weighting_user", 1.0)
        for o in ev_sp.op_points_spec + ev_sp.geo_targets
    )
    for o in ev_sp.op_points_spec + ev_sp.geo_targets:
        o.weighting = getattr(o, "weighting_user", 1.0) / sm if sm > 0 else 0.0
    if dw.active and (
        sum(1 for o in ev_sp.op_points_spec + ev_sp.geo_targets if o.dynamic_weighting)
        < 3
        or sum(
            1
            for o in ev_sp.op_points_spec + ev_sp.geo_targets
            if o.dynamic_weighting and getattr(o, "weighting_user", 1.0) == 1.0
        )
        < 3
    ):
        print_note("Dynamic weighting deactivated (Math constraint)")
        dw.active = False

    # Re Type & Trip Checks
    for op in ev_sp.op_points_spec:
        if op.re.type == 2 and op.spec_cl and op.value < 0:
            op.re.type, op.re.number = 1, op.re.number / (abs(op.value) ** 0.5)
            print_note(
                f"CL={op.value} reverted to Type 1 Re to prevent imaginary root error."
            )
    if sum(
        1 for op in ev_sp.op_points_spec if op.optimization_type == "max-xtr"
    ) > 0 and (ev_sp.xfoil_options.xtript < 1.0 or ev_sp.xfoil_options.xtripb < 1.0):
        my_stop(
            "max-xtr requested but XTRIP constraints force early turbulent transition."
        )

    # Match Foil Bypass
    if any(g.type == "match-foil" for g in ev_sp.geo_targets):
        print_note("Activating 'match-foil' protocol: Aero matrix bypassed.")
        ev_sp.op_points_spec, ev_sp.match_foil_spec.active = [], True
        ev_sp.match_foil_spec.filename = next(
            g.target_string for g in ev_sp.geo_targets if g.type == "match-foil"
        )

    # Flap Bounds
    if shp_sp.flap_spec.use_flap:
        starts = []
        for i, op in enumerate(ev_sp.op_points_spec):
            if op.flap_angle < shp_sp.flap_spec.min_flap_angle:
                print_warning(f"Flap viol OP {i + 1}. Confining to min bound.", 5)
                op.flap_angle = shp_sp.flap_spec.min_flap_angle
            if op.flap_angle > shp_sp.flap_spec.max_flap_angle:
                print_warning(f"Flap viol OP {i + 1}. Confining to max bound.", 5)
                op.flap_angle = shp_sp.flap_spec.max_flap_angle
            if op.flap_optimize:
                starts.append(op.flap_angle)
        shp_sp.flap_spec.ndv, shp_sp.flap_spec.start_flap_angle = (
            len(starts),
            np.array(starts),
        )

    # Curvature Adaptations
    if shp_sp.type == CAMB_THICK and ev_sp.curv_constraints.check_curvature:
        print_note("Curvature safely disabled for scalar scaling.")
        (
            ev_sp.curv_constraints.check_curvature,
            ev_sp.curv_constraints.auto_curvature,
        ) = False, False
    elif shp_sp.type == BEZIER:
        ev_sp.curv_constraints.top.check_curvature_bumps = (
            ev_sp.curv_constraints.bot.check_curvature_bumps
        ) = False
    elif shp_sp.type == HICKS_HENNE and not ev_sp.curv_constraints.check_curvature:
        print_warning("Curvature validation recommended for Hicks-Henne.", 5)

    if ev_sp.curv_constraints.check_curvature:
        rt, rb = (
            ev_sp.curv_constraints.top.max_curv_reverse,
            ev_sp.curv_constraints.bot.max_curv_reverse,
        )
        if rt > 1:
            print_warning(f"Multiple reversals ({rt}) requested for Upper Surface.", 5)
        if rb > 1:
            print_warning(f"Multiple reversals ({rb}) requested for Lower Surface.", 5)
        shp_sp.camber_type = (
            "reflexed"
            if rt == 1 and rb == 0
            else ("rear-loading" if rb == 1 and rt == 0 else "")
        )

    if shp_sp.type == CAMB_THICK:
        opt_opts.pso_options.convergence_profile, opt_opts.pso_options.max_retries = (
            "quick_camb_thick",
            0,
        )
        print_note("Adapting topological convergence for 'camb-thick'.")
    if ev_sp.xfoil_options.vaccel > 0.01:
        print_note(
            f"VACCEL is {ev_sp.xfoil_options.vaccel:.4f}. Values > 0.01 destabilize BL convergence."
        )


read_panel_options, read_bezier_inputs, read_xfoil_options, read_curvature_inputs = (
    _rd_pan,
    _rd_bez,
    _rd_xfo,
    _rd_curv,
)
