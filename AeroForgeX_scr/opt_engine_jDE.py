# ==============================================================================
# FILE: opt_engine_jDE.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
import numpy as np, multiprocessing, os, time, psutil, math
from typing import List, Tuple, Optional
from pymoo.core.problem import Problem, ElementwiseProblem, StarmapParallelization
from pymoo.core.callback import Callback
from pymoo.algorithms.soo.nonconvex.nelder import NelderMead
from pymoo.termination.default import DefaultSingleObjectiveTermination
from pymoo.optimize import minimize

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

PSO, GENETIC, SIMPLEX = 1, 2, 3


class OptimizeSpecType:
    def __init__(self):
        from opt_utils import PsoOptionsType, SimplexOptionsType

        self.type, self.cpu_threads = GENETIC, -1
        self.pso_options, self.sx_options = PsoOptionsType(), SimplexOptionsType()


# =============================================================================
# OS-LEVEL PROCESS MANAGEMENT & VECTORIZED PROBLEM
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

    # Retrieve the solver name we parsed from the JSON (defaults to 'xfoil' if missing)
    solver_name = getattr(ev_sp, "aero_solver_name", "xfoil")
    set_aero_solver(solver_name)


class AirfoilProblem(Problem):
    def __init__(self, ndv, pool=None, **kwargs):
        self.pool = pool
        super().__init__(
            n_var=ndv,
            n_obj=1,
            n_ieq_constr=1,
            xl=np.zeros(ndv, dtype=float),
            xu=np.ones(ndv, dtype=float),
            **kwargs,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        res = (
            self.pool.starmap(evaluate_design_pymoo, [(r,) for r in x])
            if self.pool
            else [evaluate_design_pymoo(r) for r in x]
        )
        out["F"], out["G"] = (
            np.array([r[0] for r in res], dtype=float),
            np.array([r[1] for r in res], dtype=float),
        )


class NMSimplexProblem(ElementwiseProblem):
    def __init__(self, ndv, **kwargs):
        super().__init__(
            n_var=ndv,
            n_obj=1,
            n_ieq_constr=1,
            xl=np.zeros(ndv),
            xu=np.ones(ndv),
            **kwargs,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"], out["G"] = evaluate_design_pymoo(x)


# =============================================================================
# CALLBACK TRACKER
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
# jDE ALGORITHM (Brest et al., 2006)
# =============================================================================
class jDE:
    def __init__(
        self,
        problem,
        pop_size,
        tau=0.1,
        F_low=0.1,
        F_high=1.0,
        CR_low=0.1,
        CR_high=1.0,
        seed=42,
        verbose=False,
        callback=None,
    ):
        self.problem, self.ps, self.tau, self.Fl, self.Fh, self.CRl, self.CRh = (
            problem,
            pop_size,
            tau,
            F_low,
            F_high,
            CR_low,
            CR_high,
        )
        self.rng, self.verbose, self.cb, self.n_gen = (
            np.random.RandomState(seed),
            verbose,
            callback,
            0,
        )
        self.pop, self.best_x, self.best_f, self.best_g, self.history = (
            None,
            None,
            np.inf,
            np.inf,
            [],
        )

    def _eval(self, X):
        out = {}
        self.problem._evaluate(X, out)
        return out.get("F", np.full(len(X), np.inf)).flatten(), out.get(
            "G", np.zeros(len(X))
        ).flatten()

    def _init_pop(self, X0=None):
        print_action("Synthesizing initial population (feasibility-guided) ...")
        pop, nv = [], self.problem.n_var
        if X0 is not None and len(X0) >= self.ps:
            cand = X0[: self.ps].copy()
            fc, gc = self._eval(cand)
            for i, x in enumerate(cand):
                if gc[i] <= 0:
                    pop.append(x)
                else:
                    rep = False
                    for _ in range(50):
                        xn = np.clip(x + self.rng.normal(0, 0.02, nv), 0.0, 1.0)
                        _, gn = self._eval(np.array([xn]))
                        if gn[0] <= 0:
                            pop.append(xn)
                            rep = True
                            break
                    if not rep:
                        pop.append(x)
        else:
            att = 0
            while len(pop) < self.ps and att < 100:
                cand = self.rng.uniform(0, 1, (self.ps * 2, nv))
                _, gc = self._eval(cand)
                for idx in np.where(gc <= 0)[0]:
                    if len(pop) < self.ps:
                        pop.append(cand[idx])
                    else:
                        break
                att += 1
            while len(pop) < self.ps:
                pop.append(self.rng.uniform(0, 1, nv))

        self.pop, self.F_pop, self.CR_pop = (
            np.array(pop[: self.ps]),
            self.rng.uniform(self.Fl, self.Fh, self.ps),
            self.rng.uniform(self.CRl, self.CRh, self.ps),
        )
        self.F_obj, self.G_obj = self._eval(self.pop)
        self._update_best()
        print_action(
            f"Initial population ready. Feasible: {np.sum(self.G_obj <= 0)}/{self.ps}"
        )

    def _update_best(self):
        fs = self.G_obj <= 0
        if np.any(fs):
            i = np.where(fs)[0][np.argmin(self.F_obj[fs])]
            if self.F_obj[i] < self.best_f:
                self.best_f, self.best_x, self.best_g = (
                    self.F_obj[i],
                    self.pop[i].copy(),
                    self.G_obj[i],
                )
        else:
            i = np.argmin(self.G_obj)
            if self.G_obj[i] < self.best_g:
                self.best_g, self.best_x, self.best_f = (
                    self.G_obj[i],
                    self.pop[i].copy(),
                    self.F_obj[i],
                )

    # def _adapt_params(self):
        # # FIXED: Mathematically strict, shared probability mask 'tau'
        # mask = self.rng.random(self.ps) < self.tau
        # self.F_pop[mask] = self.rng.uniform(self.Fl, self.Fh, np.sum(mask))
        # self.CR_pop[mask] = self.rng.uniform(self.CRl, self.CRh, np.sum(mask))

    def run(self, max_gen):
        if self.pop is None:
            self._init_pop()
        nv, self.history = self.problem.n_var, [self.best_f]

        for gen in range(max_gen):
            self.n_gen = gen + 1
            if self.n_gen == max_gen // 2 and self.best_g > 0:
                print_colored(
                    COLOR_WARNING,
                    "\n[ jDE ] No feasible solution found. Restarting population around best infeasible.\n",
                )
                self.pop = np.vstack(
                    [
                        self.best_x,
                        np.clip(
                            self.best_x + self.rng.normal(0, 0.05, (self.ps - 1, nv)),
                            0.0,
                            1.0,
                        ),
                    ]
                )
                self.F_obj, self.G_obj = self._eval(self.pop)
                self._update_best()
                self.F_pop, self.CR_pop = (
                    self.rng.uniform(self.Fl, self.Fh, self.ps),
                    self.rng.uniform(self.CRl, self.CRh, self.ps),
                )
                self.history.append(self.best_f)
                continue

            fs_idx = np.where(self.G_obj <= 0)[0]
            valid_cands = fs_idx if len(fs_idx) >= 3 else np.arange(self.ps)

            # Fast Vectorized Distinct Index Selection
            r1 = np.zeros(self.ps, dtype=int)
            r2 = np.zeros(self.ps, dtype=int)
            for i in range(self.ps):
                avail = valid_cands[valid_cands != i] if len(valid_cands) > 2 else np.delete(np.arange(self.ps), i)
                if len(avail) >= 2:
                    c = self.rng.choice(avail, 2, replace=False)
                    r1[i], r2[i] = c[0], c[1]
                else:
                    r1[i], r2[i] = avail[0], avail[0]

            # Generate trial parameters (jDE Self-Adaptation Engine)
            F_trial = np.where(self.rng.random(self.ps) < self.tau, 
                               self.rng.uniform(self.Fl, self.Fh, self.ps), 
                               self.F_pop)
            CR_trial = np.where(self.rng.random(self.ps) < self.tau, 
                                self.rng.uniform(self.CRl, self.CRh, self.ps), 
                                self.CR_pop)

            # DE/current-to-best/1/bin Mutation 
            # Blends the speed of DE/best/1 with the exploration of DE/rand/1
            mut = np.clip(
                self.pop + F_trial[:, None] * (self.best_x - self.pop) + F_trial[:, None] * (self.pop[r1] - self.pop[r2]),
                0.0,
                1.0,
            )
            
            # Crossover logic
            cross_mask = self.rng.random((self.ps, nv)) < CR_trial[:, None]
            j_rand = self.rng.randint(0, nv, size=self.ps)
            cross_mask[np.arange(self.ps), j_rand] = True
            off = np.where(cross_mask, mut, self.pop)

            # Evaluate Offspring
            Fo, Go = self._eval(off)
            pf, of = self.G_obj <= 0, Go <= 0
            
            # Strict Feasibility Selection Criteria
            rep = (
                (of & ~pf)
                | (of & pf & (Fo <= self.F_obj))
                | (~of & ~pf & (Go < self.G_obj))
            )
            
            # Replace Population 
            self.pop[rep], self.F_obj[rep], self.G_obj[rep] = off[rep], Fo[rep], Go[rep]
            
            # Retain successful F and CR parameters into next generation
            self.F_pop[rep] = F_trial[rep]
            self.CR_pop[rep] = CR_trial[rep]

            self._update_best()
            self.history.append(self.best_f)

            if self.cb:
                d = type(
                    "Dummy",
                    (),
                    {
                        "n_gen": self.n_gen,
                        "best_f": self.best_f,
                        "best_g": self.best_g,
                        "best_x": self.best_x,
                        "termination": type("T", (), {"force_termination": False})(),
                    },
                )()
                self.cb.notify(d)
                if d.termination.force_termination:
                    break
            if self.verbose and (self.n_gen % 10 == 0 or self.n_gen == 1):
                print(
                    f"jDE Gen {self.n_gen:04d} | Best F: {self.best_f:.6e} | Feas: {np.sum(self.G_obj <= 0)}/{self.ps}"
                )

        return self.best_x, self.best_f, self.history



# =============================================================================
# CORE MEMETIC ALGORITHM ORCHESTRATOR
# =============================================================================
from geom_builder import (
    get_dv_initial_perturb_of_shape,
    get_dv_initial_perturb_of_flaps,
)


# =============================================================================
# CORE MEMETIC ALGORITHM ORCHESTRATOR (jDE)
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
    prob = AirfoilProblem(ndv, pool=pool)
    ps = max(opt_opts.pso_options.pop, ndv * 10)

    # =================================================================
    # SMART LATIN HYPERCUBE SEEDING (Dimensionality Curse Fix)
    # =================================================================
    print_action(f"Stage 1: jDE (Brest et al., 2006) | Population: {ps}")
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

    jde = jDE(problem=prob, pop_size=ps, verbose=True, callback=ProgressCallback("jDE"))
    jde._init_pop(X0=X0_matrix)

    st_t = time.time()
    try:
        bx, bf, h_jd = jde.run(max_gen=opt_opts.pso_options.max_iterations)
    except KeyboardInterrupt:
        print_colored(COLOR_WARNING, "\n[ WARN ] Stage 1 interrupted.\n")
        bx, bf, h_jd = jde.best_x, jde.best_f, jde.history
    print("\n")
    print_colored(
        COLOR_GOOD, f"[ INFO ] jDE completed in {time.time() - st_t:.2f} seconds.\n"
    )

    # STAGE 2: NELDER-MEAD LOCAL REFINEMENT
    if stop_requested():
        print_colored(
            COLOR_WARNING,
            "[ WARN ] Optimization halted via run_control. Skipping Stage 2.\n",
        )
    else:
        print_action("Stage 2: Nelder-Mead Simplex (Local Refinement)")
        prob_nm = NMSimplexProblem(
            ndv, elementwise_runner=StarmapParallelization(pool.starmap)
        )
        if jde.best_g > 0:
            print_colored(
                COLOR_WARNING,
                f"Warning: Best jDE solution infeasible (G={jde.best_g:.3f}). Proceeding.\n",
            )
        try:
            res_l = minimize(
                prob_nm,
                NelderMead(x0=bx, max_restarts=1),
                DefaultSingleObjectiveTermination(
                    xtol=1e-8, ftol=1e-8, n_max_evals=int(ps * 7)
                ),
                verbose=False,
                callback=ProgressCallback("NM"),
            )
            if (
                res_l
                and res_l.X is not None
                and res_l.F[0] < bf
                and (res_l.G is None or res_l.G[0] <= 0)
            ):
                print_colored(
                    COLOR_GOOD,
                    f"[ INFO ] Nelder-Mead improved precision: {bf:.8f} -> {res_l.F[0]:.8f}\n",
                )
                bx, bf = res_l.X, res_l.F[0]
                h_jd.append(bf)
        except KeyboardInterrupt:
            print_colored(COLOR_WARNING, "\n[ WARN ] Stage 2 interrupted.\n")

    print()
    print_colored(
        COLOR_GOOD,
        f"[ SYSTEM ] Full Hybrid Optimization Executed in {time.time() - st_t:.2f} seconds\n",
    )
    ff, fa = write_final_results(bx, bf)
    print_action("Compiling Comprehensive Mathematical Convergence Report...")
    generate_report(commons.design_subdir, commons.output_prefix, s_foil, ff, h_jd)
    try:
        pool.close()
        pool.join()
    except:
        pass
    xfoil_cleanup()
    return ff, fa
