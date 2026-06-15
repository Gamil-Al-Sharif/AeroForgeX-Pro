#!/usr/bin/env python3
# ==============================================================================
# FILE: aeroforgex_cli.py
# PROJECT: AeroForgeX v4.0 Pro Master Orchestrator
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# Based on Xoptfoil2 by Jochen Guenzel (MIT License)
# ==============================================================================
import sys, os, argparse, multiprocessing, glob
from utils_logger import (
    make_directory,
    delete_file,
    set_my_stop_to_stderr,
    print_colored,
    print_header,
    print_note,
    set_show_details,
    COLOR_FEATURE,
    commons,
)
from config_manager import (
    read_inputs,
    run_mode_from_command_line,
    check_and_process_inputs,
)
from geom_builder import (
    prepare_seed_foil,
    prepare_match_foil,
    set_shape_spec,
    assess_shape,
    get_airfoil,
)

# Import all three optimization engines
import opt_engine
import opt_engine_jDE
import opt_engine_SHADE

from opt_utils import reset_run_control, delete_run_control
from geom_core import airfoil_write_with_shapes
from obj_utils import write_airfoil_flapped
from aero_polars import (
    match_bezier,
    generate_polars,
    repanel_normalize,
    set_flap,
    check_foil_curvature,
    check_input_file_action,
    set_geometry_value,
    blend_foils,
    generate_family,
    smooth_airfoil,
)
from report_generator import generate_worker_diagnostics
from solver_xfoil import xfoil_cleanup

PGM_NAME, PACKAGE_VERSION = " AeroForgeX ", "v4.0 Pro | Memetic AI | Surrogate CFD | HPC Parallel"


# =============================================================================
# OPTIMIZATION MODE ORCHESTRATOR
# =============================================================================
def run_optimization():
    multiprocessing.freeze_support()
    print_header("AeroForgeX Subsystem Initialized", PACKAGE_VERSION)
    commons.run_mode = run_mode_from_command_line()
    if commons.run_mode == commons.MODE_AIRFOIL_OPTIMIZER:
        set_my_stop_to_stderr(True)

    af_f, out_p, s_dtl, w_end, ev_sp, shp_sp, opt_opt = read_inputs("")
    check_and_process_inputs(ev_sp, shp_sp, opt_opt)
    commons.output_prefix, commons.show_details = out_p, s_dtl

    if getattr(commons, "output_dir_final", None):
        make_directory(commons.output_dir_final)
    commons.design_subdir = os.path.join(
        commons.output_dir_final or "", out_p + commons.DESIGN_SUBDIR_POSTFIX, ""
    )
    make_directory(commons.design_subdir)
    reset_run_control()

    print_header("Constructing Seed Geometry Profile")
    sf = prepare_seed_foil(af_f, ev_sp, shp_sp)
    if ev_sp.match_foil_spec.active:
        print_header("Preparing topological match bounds")
        prepare_match_foil(sf, ev_sp.match_foil_spec)

    print_header("Configuring Mathematical Parametric Engine")
    set_shape_spec(sf, shp_sp)
    assess_shape()
    [delete_file(out_p + ext) for ext in [".dat", ".hicks", ".bez"]]
    [os.remove(f) for f in glob.glob(out_p + "_f*.dat")]

    # ---------------------------------------------------------
    # DYNAMIC ALGORITHM ROUTING EXECUTION
    # ---------------------------------------------------------
    print_header(f"Engaging PyMoo Hybrid Optima Search [{opt_opt.algorithm_name}]")
    if opt_opt.algorithm_name == "SHADE":
        ff, f_angs = opt_engine_SHADE.optimize(sf, ev_sp, opt_opt)
    elif opt_opt.algorithm_name == "jDE":
        ff, f_angs = opt_engine_jDE.optimize(sf, ev_sp, opt_opt)
    else:
        ff, f_angs = opt_engine.optimize(sf, ev_sp, opt_opt)

    ff.name = out_p
    set_show_details(True)
    airfoil_write_with_shapes(ff, "", highlight=True)
    if shp_sp.flap_spec.use_flap:
        [os.remove(f) for f in glob.glob(out_p + "_f*.dat")]
        write_airfoil_flapped(ff, shp_sp.flap_spec, f_angs, True)

    delete_run_control()
    print()
    if w_end:
        print_note("Press Enter to finish ... ", 1, no_crlf=True)
        input()


# =============================================================================
# STANDALONE WORKER MODE ORCHESTRATOR
# =============================================================================
def _worker_task_wrapper(args_dict):
    import argparse
    a = argparse.Namespace(**args_dict)
    run_worker(a)

def run_worker(a):
    set_show_details(True)
    inp, out, act, af, af2, rd, ar, val = (
        a.input,
        a.output,
        a.action.lower(),
        a.airfoil,
        a.airfoil2,
        a.reynolds,
        getattr(a, "alpha_range", ""),
        getattr(a, "value_argument", ""),
    )

    if act == "check-input" and not inp:
        sys.exit(print("Error: Must specify input file with -i", file=sys.stderr))
    elif act != "check-input" and not af:
        sys.exit(print("Error: Must specify airfoil file with -a", file=sys.stderr))
        
# [BATCH INTERCEPTOR]
    if af and os.path.isdir(af):
        import copy
        print_colored(COLOR_FEATURE, f"\n[ BATCH PIPELINE ENGAGED ] Target Directory: {af}")
        files = glob.glob(os.path.join(af, "*.dat")) + glob.glob(os.path.join(af, "*.bez"))
        if not files:
            sys.exit(print(f"Error: No .dat or .bez files found in {af}", file=sys.stderr))
        
        # --- [FIX] Route Batch outputs to the GUI's assigned output path ---
        base_out = os.path.dirname(out) if out else os.path.join(af, "Worker_Batch_Output")
        if not base_out: base_out = "Outputs/Batch_Run"
        batch_out_dir = os.path.join(base_out, "Batch_Results")
        os.makedirs(batch_out_dir, exist_ok=True)
        
        args_list = []
        for f in files:
            a_copy = copy.deepcopy(a)
            a_copy.airfoil = f
            a_copy.output = os.path.join(batch_out_dir, os.path.basename(f).rsplit('.', 1)[0])
            args_list.append(vars(a_copy))
            
        env_workers = int(os.environ.get("AERO_NUM_WORKERS", 0))
        nt = env_workers if env_workers > 0 else multiprocessing.cpu_count()
        pool_sz = min(nt, len(args_list))
        print_colored(COLOR_FEATURE, f"Dispatching {len(args_list)} jobs across {pool_sz} parallel workers...")
        
        with multiprocessing.Pool(pool_sz) as pool:
            pool.map(_worker_task_wrapper, args_list)
            
        print_colored(COLOR_FEATURE, f"[ BATCH COMPLETE ] Check {batch_out_dir} for results.\n")
        return

    if inp and not os.path.exists(inp):
        sys.exit(print(f"Error: Input file '{inp}' not found", file=sys.stderr))
    if af and not os.path.exists(af):
        sys.exit(print(f"Error: Airfoil file '{af}' not found", file=sys.stderr))

    print()
    print_colored(COLOR_FEATURE, "Worker")
    print(f" - {act} {inp if act == 'check-input' else af}")

    o_auto = False
    if not out:
        out, o_auto = os.path.splitext(os.path.basename(af))[0], True
    f = None if act == "check-input" else get_airfoil(af, silent_mode=True)

    if act == "bezier":
        match_bezier(inp, o_auto, out, f)
    elif act == "polar":
        generate_polars(inp, False, out, rd, ar, f)
    elif act == "polar-csv":
        generate_polars(inp, True, out, rd, ar, f)
    elif act == "norm":
        repanel_normalize(inp, o_auto, out, f)
    elif act == "flap":
        set_flap(inp, o_auto, out, f)
    elif act == "check":
        check_foil_curvature(inp, out, f)  # [FIX] Added 'out' to the arguments
    elif act == "check-input":
        check_input_file_action(inp)
    elif act == "set":
        sys.exit(
            print("Error: Missing argument for set (e.g. t=0.12)", file=sys.stderr)
        ) if not val else set_geometry_value(inp, o_auto, out, f, val)
    elif act == "generate":
        sys.exit(
            print("Error: Missing argument for generate (e.g. t=8:15:5)", file=sys.stderr)
        ) if not val else generate_family(inp, o_auto, out, f, val)
    elif act == "smooth":
        smooth_airfoil(inp, o_auto, out, f, val)
    elif act == "report":
        generate_worker_diagnostics(f, out)
    elif act == "blend":
        sys.exit(
            print("Error: Must specify -a2 and blend value", file=sys.stderr)
        ) if not af2 or not val else blend_foils(
            inp, o_auto, out, f, get_airfoil(af2, silent_mode=True), val
        )
    else:
        print(f"Error: Unknown action '{act}'", file=sys.stderr)
        print_worker_usage()
        sys.exit(1)

    print()
    xfoil_cleanup()


def print_worker_usage():
    print(
        f"\n{Fore.CYAN} {PGM_NAME} Worker | {PACKAGE_VERSION}{Style.RESET_ALL}\nUsage: python aeroforgex_cli.py -w <action> [Options]"
    )
    print(
        "Actions: polar, polar-csv, norm, flap, bezier, check, set <arg>, blend <val>, check-input"
    )
    print("Options: -i <file>, -o <prefix>, -r <re>, -a <file>, -a2 <file>\n")


# =============================================================================
# CLI PARSERS & ENTRY POINT
# =============================================================================
def parse_worker_args():
    p = argparse.ArgumentParser()
    p.add_argument("-w", "--action", required=True)
    p.add_argument("-i", "--input", default="")
    p.add_argument("-o", "--output", default="")
    p.add_argument("-r", "--reynolds", type=float, default=0.0)
    p.add_argument("-a", "--airfoil", default="")
    p.add_argument("-a2", "--airfoil2", default="")
    p.add_argument("-ar", "--alpha_range", default="", help="Format min:max:step e.g. -5:15:0.5")
    p.add_argument("value_argument", nargs="?", default="")
    return p.parse_args()


def main():
    raw_logo = r"""
   █████╗ ███████╗██████╗  ██████╗ ███████╗ ██████╗ ██████╗  ██████╗ ███████╗██╗  ██╗
  ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝╚██╗██╔╝
  ███████║█████╗  ██████╔╝██║   ██║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗   ╚███╔╝ 
  ██╔══██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝   ██╔██╗ 
  ██║  ██║███████╗██║  ██║╚██████╔╝██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗██╔╝ ██╗
  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝"""

    try:
        import os

        # Enable virtual terminal processing for Windows to ensure Truecolor RGB works
        os.system("")
        from colorama import init, Fore, Style

        init(autoreset=True)

        # ====================================================================
        # 2D RGB PALETTES (Uncomment the one you want to use!)
        # Format: (R, G, B) tuples. The engine mathematically blends them.
        # ====================================================================
        # ====================================================================
        # PROFESSIONAL ENGINEERING 2D RGB PALETTES
        # (Uncomment the one you want to use)
        # ====================================================================

        # 1. "AeroForge Signature CFD" (Your favorite: Aero Blue -> Forge Heat)
        palette = [(0, 191, 255), (0, 255, 128), (255, 255, 0), (255, 100, 0)]


        # ====================================================================

        # 2D Gradient Engine
        def blend_color(c1, c2, factor):
            """Linearly interpolates between two RGB colors."""
            return (
                int(c1[0] + (c2[0] - c1[0]) * factor),
                int(c1[1] + (c2[1] - c1[1]) * factor),
                int(c1[2] + (c2[2] - c1[2]) * factor),
            )

        lines = raw_logo.strip("\n").split("\n")
        max_y = len(lines) - 1
        max_x = max(len(l) for l in lines) - 1
        num_segments = len(palette) - 1

        gradient_logo = ""
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                if char == " ":
                    gradient_logo += char
                    continue

                # Calculate 2D Factor (Diagonal Gradient: Top-Left to Bottom-Right)
                # t ranges from 0.0 to 1.0 across both dimensions
                t_x = x / max_x if max_x > 0 else 0
                t_y = y / max_y if max_y > 0 else 0
                t = (t_x + t_y) / 2.0

                # Map 't' to the correct segment in our palette array
                scaled_t = t * num_segments
                segment_idx = min(int(scaled_t), num_segments - 1)
                local_t = scaled_t - segment_idx

                # Blend the two colors for this specific (x, y) coordinate
                r, g, b = blend_color(
                    palette[segment_idx], palette[segment_idx + 1], local_t
                )

                # Append Truecolor ANSI escape code
                gradient_logo += f"\033[38;2;{r};{g};{b}m{char}"
            gradient_logo += "\n"

        # Apply standard colorama coloring for text and borders to keep it readable
        border = Fore.LIGHTBLACK_EX
        t_title = Fore.WHITE + Style.BRIGHT
        t_sub = Fore.WHITE
        reset = "\033[0m"

        print(
            f"{border}{'=' * 88}\n{reset}"
            f"{gradient_logo}{reset}"
            f"{border}{'=' * 88}\n"
            f"{t_title}                          AeroForgeX v4.0 Pro | Memetic AI | Surrogate CFD | HPC Parallel\n"
            f"{t_sub}                        Advanced Airfoil Optimization Suite | v4.0 Numba/PyMoo\n"
            f"{t_sub}                         DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir\n"
            f"{t_sub}                               Contact: mely104haja@gmail.com\n"
            f"{border}{'=' * 88}{reset}"
        )

    except UnicodeEncodeError:
        # Fallback to simple ASCII banner
        print("=" * 80)
        print("                      AeroForgeX v4.0 Pro | Memetic AI | Surrogate CFD | HPC Parallel")
        print("                    Advanced Airfoil Optimization Suite | v4.0 Numba/PyMoo")
        print("           DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir")
        print("                     Contact: mely104haja@gmail.com")
        print("=" * 80)
        print()
    # Detect mode

    except Exception as e:
        # Fallback if anything goes wrong
        print(
            f"{'=' * 88}\n{raw_logo}\n{'=' * 88}\n"
            f"                          AeroForgeX v4.0 Pro | Memetic AI | Surrogate CFD | HPC Parallel\n"
            f"                        Advanced Airfoil Optimization Suite | v4.0 Numba/PyMoo\n"
            f"                         DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir\n"
            f"                               Contact: mely104haja@gmail.com\n"
            f"{'=' * 88}"
        )
    def print_professional_help():
        from colorama import Fore, Style
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}================================================================================{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Style.BRIGHT}  AeroForgeX v4.0 Pro Command Line Interface (CLI){Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}================================================================================{Style.RESET_ALL}\n")
        
        print(f"{Fore.YELLOW}{Style.BRIGHT}DESCRIPTION:{Style.RESET_ALL}")
        print("  AeroForgeX is an advanced aerodynamic design and optimization suite.")
        print("  It operates in two primary modes: [Optimization Mode] and [Worker Utility Mode].\n")
        
        print(f"{Fore.GREEN}{Style.BRIGHT}1. OPTIMIZATION MODE (Default){Style.RESET_ALL}")
        print(f"   Executes large-scale evolutionary aerodynamic optimizations using | Memetic AI | Surrogate CFD | HPC Parallel.")
        print(f"\n   {Fore.WHITE}Usage:{Style.RESET_ALL} python aeroforgex_cli.py [Options]")
        print(f"   {Fore.WHITE}Options:{Style.RESET_ALL}")
        print(f"     -i, --input    <file>     Specify the JSON/NML configuration input file.")
        print(f"     -o, --output   <prefix>   Set the global output prefix for generated designs.")
        print(f"     -r, --reynolds <value>    Set the Reynolds number for aerodynamic evaluation.")
        print(f"     -a, --airfoil  <file>     Specify the baseline seed airfoil coordinates.\n")
        
        print(f"{Fore.GREEN}{Style.BRIGHT}2. WORKER UTILITY MODE{Style.RESET_ALL}")
        print(f"   Executes precise standalone aerodynamic and geometric transformations.")
        print(f"\n   {Fore.WHITE}Usage:{Style.RESET_ALL} python aeroforgex_cli.py -w <action> [Options]")
        print(f"   {Fore.WHITE}Available Actions (-w):{Style.RESET_ALL}")
        print(f"     {Fore.CYAN}polar{Style.RESET_ALL}        Generate XFOIL aerodynamic polar sweeps.")
        print(f"     {Fore.CYAN}polar-csv{Style.RESET_ALL}    Export generated polars directly to CSV.")
        print(f"     {Fore.CYAN}norm{Style.RESET_ALL}         Normalize airfoil geometry to unit chord [0,1].")
        print(f"     {Fore.CYAN}flap{Style.RESET_ALL}         Apply kinematic flap deflections to geometry.")
        print(f"     {Fore.CYAN}bezier{Style.RESET_ALL}       Fit CST/Bezier polynomials to discrete coordinates.")
        print(f"     {Fore.CYAN}check{Style.RESET_ALL}        Run topological diagnostics and curvature checks.")
        print(f"     {Fore.CYAN}check-input{Style.RESET_ALL}  Validate optimization JSON configuration parameters.")
        print(f"     {Fore.CYAN}blend <val>{Style.RESET_ALL}  Morph/Blend two distinct airfoils at ratio <val>.")
        print(f"     {Fore.CYAN}set <param>{Style.RESET_ALL}  Force a specific geometric parameter (e.g. thickness).")
        print(f"     {Fore.CYAN}generate{Style.RESET_ALL}     Generate an automated parametric airfoil family.")
        print(f"     {Fore.CYAN}smooth{Style.RESET_ALL}       Apply Savitzky-Golay mathematical smoothing filter.")
        print(f"     {Fore.CYAN}report{Style.RESET_ALL}       Generate Professional Dual HTML/PDF Diagnostics Report.")
        
        print(f"\n   {Fore.WHITE}Worker Options:{Style.RESET_ALL}")
        print(f"     -a,  --airfoil    <file>   Target airfoil file.")
        print(f"     -a2, --airfoil2   <file>   Secondary target airfoil (for blending).")
        print(f"     -o,  --output     <file>   Custom output path.")
        print(f"     -ar, --alpha_range <str>   Alpha sweep bounds (e.g., -5:15:0.5).")
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}================================================================================{Style.RESET_ALL}\n")

    # Command Line Execution Routing
    if "-h" in sys.argv or "--help" in sys.argv:
        print_professional_help()
        sys.exit(0)
    elif "-w" in sys.argv:
        run_worker(parse_worker_args())
    elif len(sys.argv) == 1:
        print_professional_help()
        sys.exit(0)
    else:
        run_optimization()

if __name__ == "__main__":
    main()
