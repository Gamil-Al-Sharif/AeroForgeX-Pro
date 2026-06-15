# ==============================================================================
# FILE: solver_xfoil.py
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
import os, subprocess, numpy as np, uuid, re, platform, shutil, math, threading, time
from utils_logger import (
    delete_file,
    print_colored,
    COLOR_NOTE,
    COLOR_WARNING,
    COLOR_ERROR,
)
from geom_core import airfoil_write


# =============================================================================
# HIGH-FIDELITY DATA STRUCTURES (SOLVER DEFINITIONS & METRICS)
# =============================================================================
class ReType:
    def __init__(self, number=0.0, typ=1):
        self.number, self.type = number, typ


class BubbleType:
    def __init__(self):
        self.found, self.xstart, self.xend = False, 0.0, 0.0


class OpPointSpecType:
    def __init__(self):
        self.spec_cl, self.value, self.re, self.ma, self.ncrit = (
            False,
            0.0,
            ReType(),
            ReType(),
            9.0,
        )
        (
            self.flap_angle,
            self.flap_optimize,
            self.scale_factor,
            self.optimization_type,
        ) = 0.0, False, 1.0, "min-drag"
        (
            self.target_value,
            self.allow_improved_target,
            self.weighting,
            self.weighting_user,
        ) = 0.0, True, 1.0, 1.0
        (
            self.dynamic_weighting,
            self.extra_punch,
            self.weighting_user_cur,
            self.weighting_user_prv,
        ) = False, False, 0.0, 0.0


class FlapSpecType:
    def __init__(self):
        self.use_flap, self.x_flap, self.y_flap, self.y_flap_spec = (
            False,
            0.7,
            0.0,
            "y/c",
        )
        self.min_flap_angle, self.max_flap_angle, self.ndv, self.start_flap_angle = (
            0.0,
            0.0,
            0,
            np.array([], np.float64),
        )


class OpPointResultType:
    def __init__(self):
        self.converged, self.cl, self.alpha, self.cd, self.cm = (
            False,
            0.0,
            0.0,
            1.0,
            0.0,
        )
        self.xtrt, self.xtrb, self.bubblet, self.bubbleb = (
            0.0,
            0.0,
            BubbleType(),
            BubbleType(),
        )


class XfoilOptionsType:
    def __init__(self):
        self.ncrit, self.xtript, self.xtripb, self.viscous_mode, self.silent_mode = (
            9.0,
            1.0,
            1.0,
            True,
            True,
        )
        (
            self.show_details,
            self.maxit,
            self.vaccel,
            self.fix_unconverged,
            self.detect_outlier,
        ) = False, 100, 0.01, True, True
        (
            self.exit_if_unconverged,
            self.exit_if_clmax,
            self.exit_if_clmax_nops,
            self.reinitialize,
        ) = False, False, 3, False
        self.parallel_op = True


class XfoilStatistics:
    def __init__(self):
        (
            self.ncalc,
            self.ncalc_not_conv,
            self.nretry_ok,
            self.nretry_failed,
            self.noutlier,
        ) = 0, 0, 0, 0, 0


stats = XfoilStatistics()


def xfoil_init():
    pass


def xfoil_cleanup():
    pass


def xfoil_defaults(opt):
    pass


def xfoil_apply_flap_deflection(fsp, a):
    pass


def xfoil_set_airfoil(f):
    pass


def xfoil_init_BL(sd):
    pass


# =============================================================================
# SYSTEM INTROSPECTION & EXECUTION
# =============================================================================
def get_xfoil_path():
    exe = "xfoil.exe" if platform.system() == "Windows" else "xfoil"
    paths = [
        shutil.which(exe),
        os.path.join(os.getcwd(), exe),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), exe),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), exe),
    ]
    return next((p for p in paths if p and os.path.exists(p)), None)


def check_xfoil_executable():
    if not get_xfoil_path():
        print()
        print_colored(COLOR_ERROR, "CRITICAL ERROR: 'xfoil' binary not found.\n")
        raise RuntimeError("Fortran Executable Fault")


def get_unique_temp_filename():
    return f"_temp_foil_{os.getpid()}_{threading.get_ident()}_{str(time.time()).replace('.', '')}_{str(uuid.uuid4())[:8]}.dat"


def run_xfoil_process(cmds, timeout=30):
    xp = get_xfoil_path()
    if not xp:
        return "XFOIL EXECUTION ERROR: Binary missing"
    try:
        proc = subprocess.Popen(
            [xp],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
            if platform.system() == "Windows"
            else 0,
        )
        try:
            return proc.communicate(input="\n".join(cmds) + "\n", timeout=timeout)[0]
        except subprocess.TimeoutExpired:
            proc.kill()
            return "XFOIL TIMEOUT"
    except Exception as e:
        return f"XFOIL EXECUTION ERROR: {str(e)}"


def run_single_op_point(foil, xo, fsp, a, sp):
    t_file = get_unique_temp_filename()
    try:
        airfoil_write(t_file, foil)
        cmds = ["PLOP", "G", "", f"LOAD {t_file}"]
        if fsp.use_flap and abs(a) > 1e-5:
            cmds.extend(
                [
                    "GDES",
                    "FLAP",
                    f"{fsp.x_flap}",
                    f"{fsp.y_flap}",
                    f"{a}",
                    "",
                    "PANE",
                    "",
                ]
            )
        else:
            cmds.append("PANE")
        cmds.append("OPER")
        if xo.viscous_mode:
            cmds.extend(
                [f"VISC {sp.re.number}", f"MACH {sp.ma.number}", f"ITER {xo.maxit}"]
            )
            if sp.ncrit > 0:
                cmds.extend(["VPAR", f"N {sp.ncrit}", ""])
            if xo.xtript != 1.0 or xo.xtripb != 1.0:
                cmds.extend(["VPAR", f"XTR {xo.xtript} {xo.xtripb}", ""])
        if xo.reinitialize:
            cmds.append("INIT")
        cmds.extend(
            [f"CL {sp.value}" if sp.spec_cl else f"ALFA {sp.value}", "", "QUIT"]
        )

        r = parse_xfoil_output(run_xfoil_process(cmds, timeout=12), sp)
        return r
    finally:
        delete_file(t_file) if os.path.exists(t_file) else None


# =============================================================================
# MASTER ASYNCHRONOUS KERNEL DISPATCHER
# =============================================================================
def run_op_points(foil, xo, fsp, fa, ops_spec, ops_res_out=None):
    check_xfoil_executable()
    res = []
    
    use_parallel = getattr(xo, "parallel_op", True) and len(ops_spec) > 1
    
    if use_parallel:
        from concurrent.futures import ThreadPoolExecutor
        
        def task(args):
            i, sp, a = args
            r = run_single_op_point(foil, xo, fsp, a, sp)
            return i, r

        import os as _os
        _total_cpus = _os.cpu_count() or 4
        _num_workers = int(_os.environ.get('AERO_NUM_WORKERS', '1'))
        _threads_per_worker = max(1, _total_cpus // _num_workers)
        _max_threads = min(_threads_per_worker, len(ops_spec), 8)
        with ThreadPoolExecutor(max_workers=_max_threads) as executor:
            tasks = list(executor.map(task, [(i, sp, a) for i, (sp, a) in enumerate(zip(ops_spec, fa))]))
            
        tasks.sort(key=lambda x: x[0])
        res = [r for i, r in tasks]
        
        for r in res:
            stats.ncalc += 1
            if not r.converged:
                stats.ncalc_not_conv += 1
                (print_colored(COLOR_WARNING, "x") if xo.show_details else None)
            elif xo.show_details:
                print_colored(COLOR_NOTE, ".")
                
        if xo.exit_if_unconverged:
            first_fail_idx = -1
            for idx, r in enumerate(res):
                if not r.converged:
                    first_fail_idx = idx
                    break
            if first_fail_idx != -1:
                for idx in range(first_fail_idx + 1, len(res)):
                    res[idx] = OpPointResultType()
                    res[idx].cd = 1.0
                    
    else:
        t_file = get_unique_temp_filename()
        try:
            airfoil_write(t_file, foil)
            for i, (sp, a) in enumerate(zip(ops_spec, fa)):
                cmds = ["PLOP", "G", "", f"LOAD {t_file}"]
                if fsp.use_flap and abs(a) > 1e-5:
                    cmds.extend(
                        [
                            "GDES",
                            "FLAP",
                            f"{fsp.x_flap}",
                            f"{fsp.y_flap}",
                            f"{a}",
                            "",
                            "PANE",
                            "",
                        ]
                    )
                else:
                    cmds.append("PANE")
                cmds.append("OPER")
                if xo.viscous_mode:
                    cmds.extend(
                        [f"VISC {sp.re.number}", f"MACH {sp.ma.number}", f"ITER {xo.maxit}"]
                    )
                    if sp.ncrit > 0:
                        cmds.extend(["VPAR", f"N {sp.ncrit}", ""])
                    if xo.xtript != 1.0 or xo.xtripb != 1.0:
                        cmds.extend(["VPAR", f"XTR {xo.xtript} {xo.xtripb}", ""])
                if xo.reinitialize:
                    cmds.append("INIT")
                cmds.extend(
                    [f"CL {sp.value}" if sp.spec_cl else f"ALFA {sp.value}", "", "QUIT"]
                )

                r = parse_xfoil_output(run_xfoil_process(cmds, timeout=12), sp)
                stats.ncalc += 1
                if not r.converged:
                    stats.ncalc_not_conv += 1
                    (print_colored(COLOR_WARNING, "x") if xo.show_details else None)
                elif xo.show_details:
                    print_colored(COLOR_NOTE, ".")
                res.append(r)

                if not r.converged and xo.exit_if_unconverged:
                    for _ in range(len(ops_spec) - 1 - i):
                        d = OpPointResultType()
                        d.cd = 1.0
                        res.append(d)
                    break
        finally:
            delete_file(t_file) if os.path.exists(t_file) else None
            
    if ops_res_out is not None:
        ops_res_out[:] = res
    return res


# =============================================================================
# SCIENTIFIC OUTPUT PARSING & PHYSICS VALIDATION
# =============================================================================
def validate_aerodynamic_physics(cl, cd, alpha, mach):
    if (
        math.isnan(cl)
        or math.isnan(cd)
        or math.isinf(cl)
        or math.isinf(cd)
        or cd <= 0.0
        or mach >= 1.0
    ):
        return False
    if abs(cl) > 0.01:
        if cd < 1e-6 or (cd < 1e-4 and abs(cl) > 0.05):
            return False
        if cd < 3e-3:
            if abs(cl / cd) > 350.0 or (mach > 0.4 and cd < 0.0025):
                return False
    return True


def parse_xfoil_output(out, sp):
    r = OpPointResultType()
    r.converged, r.cd = False, 1.0
    if any(
        t in out
        for t in [
            "VISCAL:  Convergence failed",
            "XFOIL TIMEOUT",
            "EXECUTION ERROR",
            "Paneling failed",
        ]
    ):
        return r

    lns, fd, ta, tcl, tcd, tcm = out.split("\n"), False, None, None, None, None
    f_rx = r"([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)"
    a_rx = re.compile(
        rf"(?:a|alpha)\s*=\s*{f_rx}.*?CL\s*=\s*{f_rx}.*?CD\s*=\s*{f_rx}.*?Cm\s*=\s*{f_rx}",
        re.I,
    )

    for l in reversed(lns):
        l = l.strip()
        m = a_rx.search(l)
        if m:
            ta, tcl, tcd, tcm = map(float, m.groups())
        else:
            if "CD =" in l:
                mcd, mcm = (
                    re.search(rf"CD\s*=\s*{f_rx}", l, re.I),
                    re.search(rf"Cm\s*=\s*{f_rx}", l, re.I),
                )
                if mcd:
                    tcd = float(mcd.group(1))
                if mcm:
                    tcm = float(mcm.group(1))
            if "CL =" in l:
                mcl, ma = (
                    re.search(rf"CL\s*=\s*{f_rx}", l, re.I),
                    re.search(rf"(?:a|alpha)\s*=\s*{f_rx}", l, re.I),
                )
                if mcl:
                    tcl = float(mcl.group(1))
                if ma:
                    ta = float(ma.group(1))

        if ta is not None and tcl is not None and tcd is not None:
            if validate_aerodynamic_physics(tcl, tcd, ta, sp.ma.number):
                r.alpha, r.cl, r.cd, r.converged = ta, tcl, tcd, True
                if tcm is not None:
                    r.cm = tcm
            fd = True
            break

    if not fd:
        if sp.spec_cl:
            r.cl = sp.value
        else:
            r.alpha = sp.value

    for l in lns:
        if "Top side transition at x/c =" in l:
            try:
                r.xtrt = float(l.split("=")[1].strip())
            except:
                pass
        elif "Bot side transition at x/c =" in l:
            try:
                r.xtrb = float(l.split("=")[1].strip())
            except:
                pass
        elif "Top side  separation bubble" in l:
            r.bubblet.found = True
        elif "Bot side  separation bubble" in l:
            r.bubbleb.found = True

    return r


def xfoil_stats_print(ind=10):
    if stats.ncalc == 0:
        return
    print_colored(
        COLOR_NOTE,
        f"{' ' * ind}XFOIL Fortran Execution Matrix: {stats.ncalc} Validated"
        + (
            f", {stats.ncalc_not_conv} Iteration Divergences"
            if stats.ncalc_not_conv > 0
            else ""
        )
        + "\n",
    )
