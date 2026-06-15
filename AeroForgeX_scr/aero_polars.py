# ==============================================================================
# FILE: aero_polars.py
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
# DESCRIPTION:
#   Aerodynamic Sweep Engine & Standalone Worker Utilities.
#   Manages automated Angle-of-Attack (Alpha) sweeps for generating Drag Polars.
#   Also acts as the execution layer for the CLI's Worker Mode, providing
#   standalone access to the geometry engine (Blending, Bezier Matching,
#   Repaneling, and Topological Diagnostics) without running an optimization loop.
# ==============================================================================

import os, copy, numpy as np
from solver_neuralfoil import get_active_solver, set_aero_solver, run_op_points
from utils_logger import (
    print_action,
    print_text,
    print_colored,
    strf,
    COLOR_NORMAL,
    COLOR_NOTE,
    COLOR_FEATURE,
    COLOR_GOOD,
    commons,
    make_directory,
    my_stop,
)
from solver_xfoil import (
    OpPointSpecType,
    FlapSpecType,
    ReType,
    XfoilOptionsType,
    xfoil_set_airfoil,
    xfoil_apply_flap_deflection,
    xfoil_init_BL,
)
from geom_core import (
    AirfoilType,
    PanelOptionsType,
    is_normalized_coord,
    airfoil_write_with_shapes,
    split_foil_into_sides,
    build_from_sides,
    airfoil_write,
    repanel_and_normalize,
    repanel_bezier,
    get_geometry,
    te_gap,
    set_geometry,
    set_te_gap,
    normalize,
    print_coordinate_data,
)
from geom_builder import (
    transform_to_bezier_based,
    get_airfoil,
    check_airfoil_curvature,
    auto_curvature_constraints,
    get_flap_angles_optimized,
)
from config_manager import (
    InputFileParser,
    read_panel_options,
    read_bezier_inputs,
    read_xfoil_options,
)
from shape_functions_param import ShapeBezierType
from obj_utils import (
    CurvConstraintsType,
    CurvSideConstraintsType,
    write_airfoil_flapped,
)
from math_accelerator import interp_vector, count_reversals, spline_2D
from report_generator import (
    generate_worker_polar_dashboard,
    generate_worker_topology_report,
)
# =============================================================================
# DATA STRUCTURES
# =============================================================================


class PolarType:
    """
    Data structure defining a specific aerodynamic boundary condition sweep.
    Holds the resulting aerodynamic matrix across a range of Angles of Attack.
    """

    def __init__(self):
        self.name = ""
        self.re = 0.0  # Reynolds Number
        self.mach = 0.0  # Mach Number
        self.ncrit = 9.0  # Boundary Layer Transition Amplification Factor
        self.flap = 0.0  # Trailing Edge geometric deflection (Degrees)
        self.results = []  # List of OpPointResultType objects


# =============================================================================
# AERODYNAMIC POLAR SWEEP ENGINE
# =============================================================================


def initialize_polars(
    auto_range,
    spec_cl,
    op_range,
    type_polar,
    ncrit,
    polar_res,
    polar_machs,
    output_prefix,
    csv_format,
    polars_out,
    splitted,
):
    """
    Constructs the operational matrix for polar generation.
    Creates an independent PolarType instance for every requested pair of
    Reynolds and Mach numbers.
    """
    if not csv_format:
        polar_dir = output_prefix + "_polars"
        make_directory(polar_dir)
        print_text(f"Aerodynamic Polars will be compiled to: {polar_dir}")

    polars_out.clear()

    # Generate combinatorial matrix of physical conditions
    for re, mach in zip(polar_res, polar_machs):
        p = PolarType()
        p.re = re
        p.mach = mach
        p.ncrit = ncrit
        polars_out.append(p)


def generate_polar_set(
    auto_range,
    output_prefix,
    csv_format,
    seed_foil,
    flap_spec,
    flap_angles,
    xfoil_options,
    polars,
    splitted,
):
    """
    Executes the highly intensive viscous flow sweep across the defined operational matrix.
    Forces XFOIL/NeuralFoil through a strict Alpha progression to map Drag, Lift, and Moment.
    """
    # Extract unique kinematic states
    unique_flaps = sorted(list(set(flap_angles)))
    if len(unique_flaps) == 0:
        unique_flaps = [0.0]
    active_engine = get_active_solver()
    if active_engine == "neuralfoil":
        print_colored(
            COLOR_FEATURE,
            "\n[ SYSTEM ] Routing Polar Sweep via Deep Learning Surrogate (NeuralFoil)\n",
        )
    else:
        print_colored(
            COLOR_NOTE,
            "\n[ SYSTEM ] Routing Polar Sweep via Fortran Subprocess (XFOIL)\n",
        )

    # Store the absolute path for the master CSV if generating one
    master_csv_path = f"{output_prefix}_polar_master.csv"
    if csv_format:
        # --- [FIX] Create missing directories before opening file ---
        csv_dir = os.path.dirname(master_csv_path)
        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)
            
        # Create/Clear the master CSV file and write the header
        with open(master_csv_path, "w") as f:
            f.write("Re; Mach; Flap; alpha; CL; CD; CM; XtrT; XtrB\n")

    for flap in unique_flaps:
        for p in polars:
            p.flap = flap

            # --- Establish Alpha Sweep Matrix ---
            # Evaluates the boundary layer from -5.0 to +15.0 degrees in 0.5-degree increments.
            # This captures the zero-lift angle, linear lift slope, and the onset of stall.
            alphas = np.arange(-5.0, 16.0, 0.5)

            op_specs = []
            for alpha in alphas:
                spec = OpPointSpecType()
                spec.spec_cl = False
                spec.value = alpha
                spec.re = ReType(p.re, 1)  # Type 1: Constant Reynolds
                spec.ma = ReType(p.mach, 1)  # Type 1: Constant Mach
                spec.ncrit = p.ncrit
                op_specs.append(spec)

            current_flap_angles = np.full(len(alphas), flap)

            print_action(
                f"Calculating Aerodynamic Polar: Re={p.re:.1e}, Mach={p.mach:.2f}, Flap={flap:.1f}"
            )

            # Sub-solver configuration overrides for systematic polar execution
            local_opts = copy.deepcopy(xfoil_options)
            local_opts.show_details = False
            local_opts.exit_if_unconverged = (
                False  # Must push through stall angles to complete graph
            )
            local_opts.reinitialize = (
                False  # Force fresh BL calculation at the start of the sweep
            )

            # --- DYNAMIC ROUTING ---
            results = run_op_points(
                seed_foil, local_opts, flap_spec, current_flap_angles, op_specs
            )

            p.results = results
            print_colored(COLOR_GOOD, "Done.")

            # Dump to file
            write_polar_file(p, output_prefix, csv_format, master_csv_path)

    # Automatically generate the HTML Dashboard if CSV mode was used
    if csv_format:
        print_action("Generating Interactive HTML Polar Dashboard...")
        target_dir = (
            os.path.dirname(output_prefix) if os.path.dirname(output_prefix) else ""
        )
        generate_worker_polar_dashboard(
            target_dir, os.path.basename(output_prefix), master_csv_path
        )


def write_polar_file(polar, prefix, csv, master_csv_path):
    """
    Translates raw aerodynamic solver memory objects into standard formatted ASCII files.
    Supports comma-separated values (CSV) for Pandas/Python parsing, or standard
    XFOIL space-delimited .dat format for traditional engineering software.
    """
    re_str = f"{int(polar.re / 1000)}k"
    flap_str = f"_f{polar.flap:.1f}" if polar.flap != 0 else ""

    if csv:
        # Append to the master CSV file
        with open(master_csv_path, "a") as f:
            for r in polar.results:
                if r.converged:
                    f.write(
                        f"{polar.re};{polar.mach};{polar.flap};{r.alpha:.3f};{r.cl:.4f};{r.cd:.5f};{r.cm:.4f};{r.xtrt:.4f};{r.xtrb:.4f}\n"
                    )
    else:
        # Write individual XFOIL-formatted .dat files
        dir_name = prefix + "_polars"
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True) 
        
        fname = os.path.join(dir_name, f"polar_Re{re_str}{flap_str}.dat")
        with open(fname, "w") as f:
            f.write(
                f"Polar for {prefix}, Re={polar.re}, Mach={polar.mach}, Ncrit={polar.ncrit}, Flap={polar.flap}\n"
            )
            f.write(f"  alpha      CL      CD      CM     XtrT     XtrB\n")
            for r in polar.results:
                if r.converged:
                    f.write(
                        f"{r.alpha:7.3f}  {r.cl:8.4f}  {r.cd:8.5f}  {r.cm:8.4f}  {r.xtrt:8.4f}  {r.xtrb:8.4f}\n"
                    )
        print_text(f"Compiled polar matrix to  -> Saved: {fname}")


# =============================================================================
# STANDALONE WORKER UTILITIES (CLI EXECUTION LAYER)
# =============================================================================


def generate_polars(input_file, csv_format, output_prefix, re_default_cl, alpha_range_str, foil):
    """
    Worker Entry Point: Configures and executes an entire polar sweep based
    strictly on settings extracted from an input JSON/Namelist file, OR from direct CLI arguments.
    """
    xfoil_options = XfoilOptionsType()
    panel_options = PanelOptionsType()
    nml = None

    if os.path.exists(input_file):
        nml = InputFileParser(input_file)
        read_xfoil_options(nml, xfoil_options)

        # Read the solver preference from the JSON and lock it!
        
        aero_solver = nml.get("opt_opts", ("solver", "aero_solver", "asolv"), "xfoil")
        set_aero_solver(aero_solver)

        if "paneling_options" in nml.data:
            read_panel_options(nml, panel_options)
            do_repanel = True
        else:
            do_repanel = False

        # Kinematics Setup
        flap_spec = FlapSpecType()
        grp = "operating_conditions"
        flap_spec.x_flap = nml.get(grp, "x_flap", 0.75)
        flap_spec.y_flap = nml.get(grp, "y_flap", 0.0)
        flap_spec.y_flap_spec = nml.get(grp, "y_flap_spec", "y/c")

        raw_angles = nml.get(grp, "flap_angle")
        flap_angles = []
        if isinstance(raw_angles, dict):
            sorted_idx = sorted([int(k) for k in raw_angles.keys()])
            for idx in sorted_idx:
                flap_angles.append(raw_angles[str(idx)])
        elif isinstance(raw_angles, list):
            flap_angles = raw_angles
        elif raw_angles is not None:
            flap_angles.append(raw_angles)
        else:
            flap_angles = [0.0]

    else:
        # No input file — only valid when alpha_range_str CLI override is provided
        if not alpha_range_str:
            my_stop(
                f"Fatal: Valid input configuration {input_file} required to orchestrate a polar generation sweep."
            )
        # Apply minimal defaults so the sweep can proceed
        xfoil_options = XfoilOptionsType()
        panel_options = PanelOptionsType()
        do_repanel = False
        flap_spec = FlapSpecType()
        flap_angles = [0.0]

    grp = "polar_generation"
    gen_polar = nml.get(grp, "generate_polar", True) if nml is not None else True
    type_polar = nml.get(grp, "type_of_polar", 1) if nml is not None else 1

    polar_res, polar_machs = [], []

    # Extrapolate Reynolds Arrays
    p_re = nml.get(grp, "polar_reynolds") if nml is not None else None
    if isinstance(p_re, dict):
        for k in sorted([int(x) for x in p_re.keys()]):
            polar_res.append(p_re[str(k)])
    elif isinstance(p_re, list):
        polar_res = p_re
    elif p_re is not None:
        polar_res.append(p_re)

    # Extrapolate Mach Arrays
    p_ma = nml.get(grp, "polar_mach") if nml is not None else None
    if isinstance(p_ma, dict):
        for k in sorted([int(x) for x in p_ma.keys()]):
            polar_machs.append(p_ma[str(k)])
    elif isinstance(p_ma, list):
        polar_machs = p_ma
    elif p_ma is not None:
        polar_machs.append(p_ma)
    else:
        polar_machs = [0.0] * len(polar_res)

    op_mode = nml.get(grp, "op_mode", "spec-al") if nml is not None else "spec-al"
    spec_cl = op_mode == "spec-cl"
    auto_range = nml.get(grp, "auto_range", False) if nml is not None else False

    raw_range = nml.get(grp, "op_point_range") if nml is not None and os.path.exists(input_file) else None
    op_range = np.zeros(3)
    if isinstance(raw_range, list) and len(raw_range) >= 3:
        op_range = np.array(raw_range[:3])
    elif isinstance(raw_range, dict):
        op_range[0], op_range[1], op_range[2] = (
            raw_range.get("0", 0.0),
            raw_range.get("1", 0.0),
            raw_range.get("2", 0.0),
        )

    # CLI Override — always applied when provided
    if alpha_range_str:
        parts = alpha_range_str.split(":")
        if len(parts) >= 3:
            try:
                op_range[0], op_range[1], op_range[2] = float(parts[0]), float(parts[1]), float(parts[2])
                auto_range = False  # explicit range disables auto-range
            except ValueError:
                print(f"Error parsing alpha range: {alpha_range_str}. Expected format min:max:step")
        else:
            print(f"Error: Alpha range must have 3 parts separated by colons (e.g. -5:15:0.5)")

    if len(polar_res) == 0:
        polar_res.append(re_default_cl if re_default_cl > 0 else 100000.0)
        polar_machs.append(0.0)

    if not gen_polar:
        my_stop("Polar generation explicitly disabled in configuration file.")

    polars = []
    initialize_polars(
        auto_range,
        spec_cl,
        op_range,
        type_polar,
        xfoil_options.ncrit,
        polar_res,
        polar_machs,
        output_prefix,
        csv_format,
        polars,
        False,
    )

    if len(polars) > 0:
        seed_foil = AirfoilType()
        if do_repanel:
            if foil.is_bezier_based:
                repanel_bezier(foil, seed_foil, panel_options)
            elif foil.is_hh_based:
                seed_foil = copy.deepcopy(foil)
            else:
                repanel_and_normalize(foil, seed_foil, panel_options)
        else:
            seed_foil = copy.deepcopy(foil)

        print("\n")
        generate_polar_set(
            auto_range,
            output_prefix,
            csv_format,
            seed_foil,
            flap_spec,
            np.array(flap_angles),
            xfoil_options,
            polars,
            False,
        )


def match_bezier(input_file, outname_auto, output_prefix, seed_foil):
    """
    Worker Action: Forces the Nelder-Mead Simplex engine to fit a pure analytical
    Bezier curve onto the discrete coordinates of the provided seed airfoil.
    """
    print_action("Executing topological curve-fitting (Simplex -> Bezier)")

    panel_options = PanelOptionsType()
    shape_bezier = ShapeBezierType()

    if os.path.exists(input_file):
        nml = InputFileParser(input_file)
        read_panel_options(nml, panel_options)
        read_bezier_inputs(nml, shape_bezier)

    foil = AirfoilType()
    print()

    if not is_normalized_coord(seed_foil):
        repanel_and_normalize(seed_foil, foil, panel_options)
    else:
        foil = copy.deepcopy(seed_foil)

    foil.name = output_prefix + "-bezier" if outname_auto else output_prefix

    commons.show_details = True
    transform_to_bezier_based(shape_bezier, panel_options, foil)
    airfoil_write_with_shapes(foil, "")


def set_geometry_value(
    input_file, outname_auto, output_prefix, seed_foil, value_argument
):
    """
    Worker Action: Exerts raw scalar transformations (Scale Max Thickness,
    Scale Camber) to morph a seed airfoil's baseline dimensions.
    """
    if "=" not in value_argument:
        my_stop(
            f"Syntax Error: Argument '{value_argument}' invalid. Expected format: 't=12.0'"
        )

    val_type, val_str = value_argument.split("=")
    val_type, val_str = val_type.strip(), val_str.strip()

    try:
        val_number = float(val_str) / 100.0
    except ValueError:
        my_stop(f"Syntax Error: Cannot parse numeric value from '{val_str}'")

    panel_options = PanelOptionsType()
    if os.path.exists(input_file):
        nml = InputFileParser(input_file)
        read_panel_options(nml, panel_options)

    foil = copy.deepcopy(seed_foil)

    if not is_normalized_coord(foil):
        print_action("Executing absolute coordinate normalization to (0,0)->(1,0)")
        normalize(foil, basic=True)

    if val_type == "t":
        print_action("Morphing geometric thickness to", f"{val_str}%")
        set_geometry(foil, maxt=val_number)
    elif val_type == "xt":
        print_action("Shifting maximum thickness spatial location to", f"{val_str}%")
        set_geometry(foil, xmaxt=val_number)
    elif val_type == "c":
        print_action("Morphing geometric camber scale to", f"{val_str}%")
        set_geometry(foil, maxc=val_number)
    elif val_type == "xc":
        print_action("Shifting maximum camber spatial location to", f"{val_str}%")
        set_geometry(foil, xmaxc=val_number)
    elif val_type == "te":
        print_action("Scaling Trailing Edge thickness gap to", f"{val_str}%")
        set_te_gap(foil, val_number)
    else:
        my_stop(f"Fatal: Unknown geometric scalar target '{val_type}'")

    foil.name = (
        f"{output_prefix}_{val_type}={val_str}" if outname_auto else output_prefix
    )
    airfoil_write_with_shapes(foil, "")


def generate_family(
    input_file, outname_auto, output_prefix, seed_foil, value_argument
):
    """
    Worker Action: Generates a parametric family of airfoils scaling a geometric property.
    Format: t=8:15:5 (Thickness from 8% to 15% in 5 steps)
    """
    if "=" not in value_argument or ":" not in value_argument:
        my_stop("Syntax Error: Expected format e.g. 't=8:15:5'")
    val_type, val_str = value_argument.split("=")
    val_type = val_type.strip()
    parts = val_str.split(":")
    if len(parts) != 3:
        my_stop("Syntax Error: Range must be min:max:steps")
    
    vmin, vmax, steps = float(parts[0]), float(parts[1]), int(parts[2])
    
    if not is_normalized_coord(seed_foil):
        normalize(seed_foil, basic=True)
        
    out_folder = output_prefix + "_Family"
    make_directory(out_folder)
    print_action(f"Generating Parametric Family: {val_type} from {vmin}% to {vmax}% ({steps} steps)")
    
    for i, val in enumerate(np.linspace(vmin, vmax, steps)):
        foil = copy.deepcopy(seed_foil)
        val_number = val / 100.0
        if val_type == "t": set_geometry(foil, maxt=val_number)
        elif val_type == "xt": set_geometry(foil, xmaxt=val_number)
        elif val_type == "c": set_geometry(foil, maxc=val_number)
        elif val_type == "xc": set_geometry(foil, xmaxc=val_number)
        elif val_type == "te": set_te_gap(foil, val_number)
        else: my_stop(f"Unknown scalar '{val_type}'")
        
        stem = os.path.basename(output_prefix)
        foil.name = os.path.join(out_folder, f"{stem}_{val_type}={val:.2f}")
        airfoil_write_with_shapes(foil, "")


def smooth_airfoil(input_file, outname_auto, output_prefix, seed_foil, value_argument):
    """
    Worker Action: Applies Savitzky-Golay mathematical filter to eliminate coordinate noise.
    """
    from scipy.signal import savgol_filter
    print_action("Initializing Mathematical Smoothing Filter (Savitzky-Golay)")
    
    if not is_normalized_coord(seed_foil):
        normalize(seed_foil, basic=True)
        
    try:
        window_size = int(value_argument) if value_argument else 11
    except ValueError:
        window_size = 11

    if window_size % 2 == 0:
        window_size += 1 
    poly_order = min(3, window_size - 1)
    
    foil = copy.deepcopy(seed_foil)
    
    # Split into Top/Bottom arrays using y >= 0 heuristic, sorting by x
    top_idx = foil.y >= -1e-6
    bot_idx = foil.y < 1e-6
    
    x_t, y_t = foil.x[top_idx], foil.y[top_idx]
    x_b, y_b = foil.x[bot_idx], foil.y[bot_idx]
    
    sort_t = np.argsort(x_t)
    sort_b = np.argsort(x_b)
    
    x_t, y_t = x_t[sort_t], y_t[sort_t]
    x_b, y_b = x_b[sort_b], y_b[sort_b]
    
    if len(y_t) > window_size:
        y_t_smooth = savgol_filter(y_t, window_size, poly_order)
        # Restore original order
        for i, org_idx in enumerate(sort_t):
            foil.y[np.where(top_idx)[0][org_idx]] = y_t_smooth[i]
            
    if len(y_b) > window_size:
        y_b_smooth = savgol_filter(y_b, window_size, poly_order)
        for i, org_idx in enumerate(sort_b):
            foil.y[np.where(bot_idx)[0][org_idx]] = y_b_smooth[i]
            
    # Lock LE to exactly zero
    le_idx = np.argmin(foil.x)
    foil.y[le_idx] = 0.0
    
    foil.name = f"{output_prefix}_smooth" if outname_auto else output_prefix
    airfoil_write_with_shapes(foil, "")


def blend_foils(
    input_file, outname_auto, output_prefix, seed_foil, blend_foil, value_argument
):
    """
    Worker Action: Interpolates the mesh of two independent airfoils and
    blends them together based on a user-defined percentage weighting.
    """
    print_action("Initializing Parametric Morphing Engine (Airfoil Blending)")

    try:
        blend_factor = float(value_argument)
    except ValueError:
        my_stop(
            f"Syntax Error: Cannot parse numeric blend factor from '{value_argument}'"
        )

    if blend_factor > 1.0:
        blend_factor /= 100.0
    if not (0.0 <= blend_factor <= 1.0):
        my_stop(
            "Math Error: Blend factor percentage must resolve strictly between 0.0 and 1.0"
        )

    panel_options = PanelOptionsType()
    if os.path.exists(input_file):
        nml = InputFileParser(input_file)
        read_panel_options(nml, panel_options)

    print()

    # Base Mesh Extraction
    in_foil = AirfoilType()
    if is_normalized_coord(seed_foil):
        in_foil = copy.deepcopy(seed_foil)
        split_foil_into_sides(in_foil)
        print_text(
            f"- Verified: Airfoil {in_foil.name} complies with normalization standards."
        )
    else:
        repanel_and_normalize(seed_foil, in_foil, panel_options)

    # Target Mesh Extraction
    b_foil = AirfoilType()
    if is_normalized_coord(blend_foil):
        b_foil = copy.deepcopy(blend_foil)
        split_foil_into_sides(b_foil)
        print_text(
            f"- Verified: Airfoil {b_foil.name} complies with normalization standards."
        )
    else:
        repanel_and_normalize(blend_foil, b_foil, panel_options)

    # --- 1D Spline Interpolation ---
    # To mathematically blend two shapes, they must share identical X-coordinates.
    # We map the Target Foil (b_foil) onto the Base Foil (in_foil) X-distribution.
    yttmp = interp_vector(b_foil.top.x, b_foil.top.y, in_foil.top.x)
    ybtmp = interp_vector(b_foil.bot.x, b_foil.bot.y, in_foil.bot.x)

    print_action(
        f"Fusing boundaries of {seed_foil.name} & {blend_foil.name} at a weighting ratio of {int(blend_factor * 100)}%"
    )

    # Exact Linear Morphing Algorithm
    yt_blended = (1.0 - blend_factor) * in_foil.top.y + blend_factor * yttmp
    yb_blended = (1.0 - blend_factor) * in_foil.bot.y + blend_factor * ybtmp

    blended_foil = AirfoilType()
    blended_foil.top.x, blended_foil.top.y = in_foil.top.x, yt_blended
    blended_foil.bot.x, blended_foil.bot.y = in_foil.bot.x, yb_blended

    build_from_sides(blended_foil)
    blended_foil.name = output_prefix + "-blend" if outname_auto else output_prefix
    airfoil_write_with_shapes(blended_foil, "")


def set_flap(input_file, outname_auto, output_prefix, seed_foil):
    """
    Worker Action: Exerts raw kinematic transformations to deflect a trailing
    edge element geometrically.
    """
    panel_options = PanelOptionsType()
    flap_spec = FlapSpecType()
    flap_angles = []

    if os.path.exists(input_file):
        nml = InputFileParser(input_file)
        read_panel_options(nml, panel_options)

        grp = "operating_conditions"
        flap_spec.x_flap = nml.get(grp, "x_flap", 0.75)
        flap_spec.y_flap = nml.get(grp, "y_flap", 0.0)
        flap_spec.y_flap_spec = nml.get(grp, "y_flap_spec", "y/c")

        raw = nml.get(grp, "flap_angle")
        if isinstance(raw, dict):
            keys = sorted(raw.keys(), key=lambda x: int(x) if x.isdigit() else x)
            for k in keys:
                flap_angles.append(raw[k])
        elif isinstance(raw, list):
            flap_angles = raw
        elif raw is not None:
            flap_angles.append(raw)
        else:
            flap_angles = [0.0]

    if not flap_angles:
        flap_angles = [5.0]  # sensible default when no config file is provided

    if len(flap_angles) == 1 and flap_angles[0] == 0.0:
        my_stop("Fatal: No kinematic deflections specified in the configuration file.")
    elif len(flap_angles) == 1:
        print_colored(COLOR_NORMAL, "Processing single geometric deflection state")
    else:
        print_colored(
            COLOR_NORMAL,
            f"Processing multi-state kinematic array ({len(flap_angles)} angles)",
        )

    print(
        f" (Hinge Origin: X={int(flap_spec.x_flap * 100)}%, {flap_spec.y_flap_spec}={flap_spec.y_flap})\n"
    )

    foil = copy.deepcopy(seed_foil)
    if not is_normalized_coord(foil):
        normalize(foil, basic=True)
        print_action("Executing absolute coordinate normalization to (0,0)->(1,0)")
    from utils_logger import filename_stem

    if not outname_auto:
        foil.name = output_prefix
    write_airfoil_flapped(foil, flap_spec, np.array(flap_angles), outname_auto)


def repanel_normalize(input_file, outname_auto, output_prefix, seed_foil):
    """
    Worker Action: Executes X-axis cosine clustering to push dense resolution
    into regions of massive aerodynamic pressure gradients (LE and TE).
    """
    print_action("Initiating mesh repaneling and absolute boundary normalization.")

    panel_options = PanelOptionsType()
    if os.path.exists(input_file):
        nml = InputFileParser(input_file)
        read_panel_options(nml, panel_options)

    foil = AirfoilType()
    print()
    repanel_and_normalize(seed_foil, foil, panel_options)

    if not outname_auto:
        foil.name = output_prefix
    airfoil_write_with_shapes(foil, "")


def check_foil_curvature(input_file, output_prefix, seed_foil): 
    """
    Worker Action: Dissects the exact topological math of a coordinate array...
    """
    """
    Worker Action: Dissects the exact topological math of a coordinate array
    to locate mathematical bumps and inflection points that trigger flow separation.
    """
    print_action("Initiating High-Fidelity Topological & Curvature Diagnostics.")

    panel_options = PanelOptionsType()
    curv_constraints = CurvConstraintsType()
    curv_constraints.top = CurvSideConstraintsType()
    curv_constraints.bot = CurvSideConstraintsType()

    if os.path.exists(input_file):
        nml = InputFileParser(input_file)
        read_panel_options(nml, panel_options)
        from config_manager import read_curvature_inputs

        read_curvature_inputs(nml, curv_constraints)

    tmp_foil = copy.deepcopy(seed_foil)
    norm_foil = AirfoilType()

    commons.show_details = True
    print()
    repanel_and_normalize(tmp_foil, norm_foil, panel_options)

    maxt, xmaxt, maxc, xmaxc = get_geometry(norm_foil)
    print()
    print_colored(COLOR_NOTE, f"     Physical Geometry Metrics: ")
    print_colored(COLOR_NOTE, f"Thickness {maxt * 100:.2f}% at {xmaxt * 100:.2f}% | ")
    print_colored(COLOR_NOTE, f"Camber {maxc * 100:.2f}% at {xmaxc * 100:.2f}% | ")
    print_colored(COLOR_NOTE, f"TE gap {te_gap(seed_foil) * 100:.2f}%\n\n")

    tmp_foil.spl = spline_2D(tmp_foil.x, tmp_foil.y)
    norm_foil.spl = spline_2D(norm_foil.x, norm_foil.y)

    tmp_foil.name, norm_foil.name = "original", "normalized"
    print_coordinate_data(tmp_foil, norm_foil, indent=5)
    print()

    print_action(
        "Executing boundary layer surface assessment (Spike / Reversal Detection)."
    )
    print()
    qual = check_airfoil_curvature(curv_constraints, norm_foil)
    print()

    print_action(
        "Calibrating optimized mathematical tolerance limits for normalization."
    )
    print()

    # Upper Surface Tolerances
    is_skip = curv_constraints.top.nskip_LE + 1
    ie = len(norm_foil.top.x)
    nrev = count_reversals(
        is_skip, ie, norm_foil.top.curvature, curv_constraints.top.curv_threshold
    )
    curv_constraints.top.max_curv_reverse = nrev
    auto_curvature_constraints(norm_foil.top, curv_constraints.top)

    # Lower Surface Tolerances
    if not norm_foil.symmetrical:
        is_skip = curv_constraints.bot.nskip_LE + 1
        ie = len(norm_foil.bot.x)
        nrev = count_reversals(
            is_skip, ie, norm_foil.bot.curvature, curv_constraints.bot.curv_threshold
        )
        curv_constraints.bot.max_curv_reverse = nrev
        auto_curvature_constraints(norm_foil.bot, curv_constraints.bot)
# Automatically generate the HTML Topology Report
    print_action("Generating Interactive HTML Topology Dashboard...")
    
    # --- [FIX] Route the HTML report to the correct Sandbox output directory ---
    target_dir = os.path.dirname(output_prefix) if os.path.dirname(output_prefix) else ""
    prefix = os.path.basename(output_prefix)
    
    # Ensure the directory exists before saving
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        
    generate_worker_topology_report(target_dir, prefix, norm_foil, curv_constraints)


def check_input_file_action(input_file):
    """Worker Action: Verifies configuration file syntax and structure."""
    from config_manager import read_inputs

    print()
    read_inputs(input_file)
    print()
    print_colored(
        COLOR_FEATURE,
        "SYSTEM DIAGNOSTIC: Configuration Matrix parsed successfully without strict syntax faults.\n",
    )
