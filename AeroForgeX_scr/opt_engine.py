# ==============================================================================
# FILE: opt_engine.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
from colorama import Fore, Style, init
import numpy as np, multiprocessing, os, time, psutil, math
from pymoo.core.problem import ElementwiseProblem, StarmapParallelization
from pymoo.core.callback import Callback
from pymoo.optimize import minimize
from pymoo.algorithms.soo.nonconvex.de import DE
from pymoo.algorithms.soo.nonconvex.nelder import NelderMead
from pymoo.termination.default import DefaultSingleObjectiveTermination

# --- Internal Core & Architecture ---
from utils_logger import (
    print_action,
    print_colored,
    COLOR_GOOD,
    COLOR_FEATURE,
    COLOR_PALE,
    COLOR_ERROR,
    COLOR_WARNING,
    commons,
)
from solver_xfoil import xfoil_cleanup
from geom_builder import (
    get_ndv_of_shape,
    get_ndv_of_flaps,
    get_dv0_of_shape,
    get_dv0_of_flaps,
    get_shape_spec,
)
from obj_evaluator import (
    set_eval_spec,
    eval_seed_scale_objectives,
    evaluate_design_pymoo,
    write_final_results,
    write_progress,
    initialize_worker_state,
)

# from obj_utils import generate_report
from opt_utils import stop_requested
from report_generator import generate_report

# =============================================================================
# OPTIMIZATION ARCHITECTURE CONSTANTS & CONFIG
# =============================================================================
PSO, GENETIC, SIMPLEX = 1, 2, 3


class OptimizeSpecType:
    def __init__(self):
        from opt_utils import PsoOptionsType, SimplexOptionsType

        self.type, self.cpu_threads = GENETIC, -1
        self.pso_options, self.sx_options = PsoOptionsType(), SimplexOptionsType()


# =============================================================================
# OS-LEVEL PROCESS MANAGEMENT
# =============================================================================
def worker_init(ev_sp, sf, shp_sp, c_dict):
    try:
        p = psutil.Process(os.getpid())
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 10)
    except:
        pass

    # Strictly lock Deep Learning threads to 1 per worker to prevent OS Thrashing
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"

    initialize_worker_state(ev_sp, sf, shp_sp, c_dict)
    from solver_neuralfoil import set_aero_solver

    solver_name = getattr(ev_sp, "aero_solver_name", "xfoil")
    set_aero_solver(solver_name)


# =============================================================================
# EXACT MATHEMATICAL PROBLEM DEFINITION
# =============================================================================
class AirfoilProblem(ElementwiseProblem):
    def __init__(self, ndv, **kwargs):
        super().__init__(
            n_var=ndv,
            n_obj=1,
            n_ieq_constr=1,
            xl=np.zeros(ndv, dtype=float),
            xu=np.ones(ndv, dtype=float),
            **kwargs,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        f, g = evaluate_design_pymoo(x)
        out["F"], out["G"] = f, g


# =============================================================================
# STATE TRACKER & ASYNCHRONOUS I/O MANAGER
# =============================================================================
class ProgressCallback(Callback):
    def __init__(self, prefix="", gen_offset=0):
        super().__init__()
        self.best_f, self.prefix, self.history = float("inf"), prefix, []
        self.gen_offset = gen_offset

    def notify(self, algo):
        if stop_requested():
            print_colored(COLOR_ERROR, "\n[ FATAL ] Physical halt triggered.\n")
            if hasattr(algo, "termination"):
                setattr(algo.termination, "force_termination", True)
            return
        
        _local_g = getattr(algo, "n_gen", getattr(algo, "n_iter", 0))
        g = _local_g + self.gen_offset
        improved = False
        
        if hasattr(algo, "best_f"):
            is_f, c_f = True, algo.best_f
            if c_f < self.best_f:
                self.best_f = c_f
                improved = True
                if hasattr(algo, "best_x"): write_progress(algo.best_x, g)
        else:
            if algo.pop is None: return
            f_pop = algo.pop[algo.pop.get("G")[:, 0] <= 0] if algo.pop.has("G") else algo.pop
            is_f = len(f_pop) > 0
            b_ind = f_pop[np.argmin(f_pop.get("F"))] if is_f else (algo.pop[np.argmin(algo.pop.get("G")[:, 0])] if algo.pop.has("G") else algo.pop[0])
            c_f = b_ind.F[0]
            
            if is_f and c_f < self.best_f:
                self.best_f = c_f
                improved = True
                write_progress(b_ind.X, g)

        # CRITICAL FIX: To prevent 33.33 spikes in plots/CSV, we ONLY append the best known objective.
        # This keeps the convergence line perfectly flat during stalled generations.
        _local_g = getattr(algo, "n_gen", getattr(algo, "n_iter", 0))
        if _local_g == 0 and self.gen_offset > 0:
            pass
        else:
            history_val = self.best_f if self.best_f != float("inf") else c_f
            if not self.history or history_val != self.history[-1]:
                self.history.append(history_val)

        imp_p = (1.0 - self.best_f) * 100.0 if math.isfinite(self.best_f) else 0.0
        
        if improved:
            print_colored(COLOR_FEATURE, f"\n{'=' * 105}\n")
            print_colored(COLOR_GOOD, " [ OPTIMA ] NEW BASELINE DISCOVERED ")
            print_colored(COLOR_PALE, f"| Gen: {g:04d} | Feas: {'PASS' if is_f else 'FAIL'} | Obj: {self.best_f:.6f} | Improv: {imp_p:+.2f}%\n")
            print_colored(COLOR_FEATURE, f"{'=' * 105}\n")
        elif g % 10 == 0:
            print_colored(COLOR_PALE, f" [ SWARM ] {self.prefix} Gen {g:04d} | Searching... Best Improv: {imp_p:+.2f}%\n")




# =============================================================================
# CORE MEMETIC ALGORITHM (HYBRID DE + SIMPLEX)
# =============================================================================
from geom_builder import (
    get_dv_initial_perturb_of_shape,
    get_dv_initial_perturb_of_flaps,
)


# =============================================================================
# CORE MEMETIC ALGORITHM ORCHESTRATOR (PyMoo Standard DE)
# =============================================================================
def optimize(s_foil, ev_sp, opt_opts):
    set_eval_spec(ev_sp)
    eval_seed_scale_objectives(s_foil)
    ndvs, ndvf = get_ndv_of_shape(), get_ndv_of_flaps()
    ndv = ndvs + ndvf
    print_action(f"Rigorous Setup Complete: Enforcing {ndv} Exact Continuous Variables")

    # 1. Extract Seed Coordinates AND Smart Perturbation Bounds
    dv_0 = np.zeros(ndv, dtype=float)
    pert = np.zeros(ndv, dtype=float)

    if ndvs > 0:
        dv_0[:ndvs] = get_dv0_of_shape()
        pert[:ndvs] = get_dv_initial_perturb_of_shape()
    if ndvf > 0:
        dv_0[ndvs:] = get_dv0_of_flaps()
        pert[ndvs:] = get_dv_initial_perturb_of_flaps()

    write_progress(dv_0, 0)
    env_workers = int(os.environ.get("AERO_NUM_WORKERS", 0))
    nt = (
        opt_opts.cpu_threads
        if opt_opts.cpu_threads > 0
        else (env_workers if env_workers > 0 else multiprocessing.cpu_count())
    )
    print_action(f"Engaging Parallel Evaluation Pool across {nt} cores")

    pool = multiprocessing.Pool(
        processes=nt,
        initializer=worker_init,
        initargs=(
            ev_sp,
            s_foil,
            get_shape_spec(),
            {
                "design_subdir": commons.design_subdir,
                "output_prefix": commons.output_prefix,
                "show_details": False,
            },
        ),
    )
    prob = AirfoilProblem(ndv, elementwise_runner=StarmapParallelization(pool.starmap))
    ps = max(opt_opts.pso_options.pop, ndv * 10)

    # =================================================================
    # SMART LATIN HYPERCUBE SEEDING (Dimensionality Curse Fix)
    # =================================================================
    algo_name = getattr(opt_opts.pso_options, "algo", "lshade").lower()
    
    if algo_name != "nm-only":
        print_action(
            f"Stage 1: Global Search ({algo_name.upper()}) | Pop: {ps}"
        )
        print_action(
            "  - Smart Micro-Perturbation Seeding | Latin Hypercube centered on Seed"
        )
    
        try:
            from scipy.stats import qmc
            lhs = qmc.LatinHypercube(d=ndv, seed=42).random(n=ps - 1)
        except:
            np.random.seed(42)
            lhs = np.random.rand(ps - 1, ndv)
    
        # Shift LHS space to [-1.0, 1.0] and mathematically scale it by the JSON init_pert
        smart_pop = np.clip(dv_0 + ((lhs * 2.0) - 1.0) * pert, 0.0, 1.0)
        X0_matrix = np.vstack([dv_0, smart_pop])
        # =================================================================
    
        # Algorithm Selection
        if algo_name == "lshade":
            algo_de = DE(
                pop_size=ps,
                sampling=X0_matrix,
                variant="DE/best/1/bin",
                CR=0.9,
                F=0.7,
                dither="scalar",
                jitter=True,
            )
        elif algo_name == "shade":
            algo_de = DE(
                pop_size=ps,
                sampling=X0_matrix,
                variant="DE/best/1/bin",
                CR=0.9,
                F=0.5,
                dither="vector",
                jitter=True,
            )
        elif algo_name == "jde":
            algo_de = DE(
                pop_size=ps,
                sampling=X0_matrix,
                variant="DE/rand/1/bin",
                CR=0.9,
                F=0.5,
                dither="vector",
                jitter=False,
            )
        else:
            algo_de = DE(
                pop_size=ps,
                sampling=X0_matrix,
                variant="DE/best/1/bin",
                CR=0.85,
                F=0.5,
                dither="vector",
                jitter=False,
            )

        term_g = DefaultSingleObjectiveTermination(
            xtol=1e-8,
            cvtol=1e-6,
            ftol=1e-5,
            period=250,
            n_max_gen=opt_opts.pso_options.max_iterations,
        )
    
        cb_de = ProgressCallback("DE")
        st_t = time.time()
        try:
            res_g = minimize(
                prob,
                algo_de,
                term_g,
                seed=42,
                callback=cb_de,
                verbose=False,
                save_history=False,
            )
        except KeyboardInterrupt:
            print_colored(
                COLOR_WARNING,
                "\n[ WARN ] Stage 1 Interrupted. Proceeding to Local Refinement.\n",
            )
        print("\n")
        print_colored(COLOR_GOOD, "[ INFO ]   Global Search Stage Converged.\n")
    
        bx, bf = dv_0, float("inf")
        if "res_g" in locals() and res_g and res_g.X is not None:
            bx, bf = (
                (res_g.X, res_g.F[0])
                if res_g.G is None or res_g.G[0] <= 0
                else (res_g.X, bf)
            )
    
        hf = cb_de.history.copy()
    else:
        print_action("Stage 1: Global Search Skipped (Nelder-Mead Only selected)")
        st_t = time.time()
        bx, bf = dv_0, float("inf")
        hf = []

    # STAGE 2: EXACT NELDER-MEAD SIMPLEX REFINEMENT
    if stop_requested():
        print_colored(
            COLOR_WARNING,
            "[ WARN ] Optimization halted via run_control. Skipping Stage 2.\n",
        )
    else:
        print_action("Stage 2: Nelder-Mead Simplex (Exact Topological Refinement)")
        cb_nm = ProgressCallback("NM")
        cb_nm.best_f = bf

        try:
            res_l = minimize(
                prob,
                NelderMead(x0=bx, max_restarts=1),
                DefaultSingleObjectiveTermination(
                    xtol=1e-8, ftol=1e-8, n_max_evals=int(ps * 7)
                ),
                verbose=False,
                callback=cb_nm,
            )
            if (
                res_l
                and res_l.X is not None
                and res_l.F[0] < bf
                and (res_l.G is None or res_l.G[0] <= 0)
            ):
                print_colored(
                    COLOR_GOOD,
                    f"[ INFO ]   Nelder-Mead cleanly extracted further precision: {bf:.8f} -> {res_l.F[0]:.8f}\n",
                )
                bx, bf = res_l.X, res_l.F[0]
                hf.extend(cb_nm.history)

        except KeyboardInterrupt:
            print_colored(COLOR_WARNING, "\n[ WARN ] Stage 2 Interrupted.\n")

    # FINALIZATION & EXPORT
    print(
        f"\n{Fore.GREEN}[ SYSTEM ] Full Hybrid Optimization Executed in {time.time() - st_t:.2f} seconds{Style.RESET_ALL}\n"
    )
    ff, fa = write_final_results(bx, bf)

    print_action("Compiling Comprehensive Mathematical Convergence Report...")
    generate_report(commons.design_subdir, commons.output_prefix, s_foil, ff, hf)

    try:
        pool.close()
        pool.join()
    except:
        pass
    xfoil_cleanup()
    return ff, fa
