# ==============================================================================
# FILE: opt_engine_SHADE.py
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

try:
    from scipy.stats import qmc

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

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
# TRUE SHADE ALGORITHM (Tanabe & Fukunaga, 2013)
# =============================================================================
class SHADE:
    def __init__(
        self,
        problem,
        pop_size,
        archive_size=None,
        memory_size=10,
        p_best=0.15,
        F_init=0.5,
        CR_init=0.5,
        seed=42,
        verbose=False,
        callback=None,
    ):
        self.problem, self.ps, self.arc_sz, self.H, self.pb, self.rng = (
            problem,
            pop_size,
            archive_size or pop_size,
            memory_size,
            p_best,
            np.random.RandomState(seed),
        )
        self.Fi, self.CRi, self.verbose, self.cb, self.n_gen = (
            F_init,
            CR_init,
            verbose,
            callback,
            0,
        )
        self.M_F, self.M_CR, self.m_idx = (
            [F_init] * memory_size,
            [CR_init] * memory_size,
            0,
        )
        self.best_x, self.best_f, self.best_g, self.history = None, np.inf, np.inf, []

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
                cand = (
                    qmc.LatinHypercube(d=nv, seed=self.rng.randint(0, 2**31)).random(
                        n=self.ps * 3
                    )
                    if HAS_SCIPY
                    else self.rng.uniform(0, 1, (self.ps * 3, nv))
                )
                _, gc = self._eval(cand)
                for idx in np.where(gc <= 0)[0]:
                    if len(pop) < self.ps:
                        pop.append(cand[idx])
                    else:
                        break
                att += 1
            while len(pop) < self.ps:
                pop.append(self.rng.uniform(0, 1, nv))

        self.pop, self.arc_np = np.array(pop[: self.ps]), np.zeros((self.arc_sz, nv))
        self.arc_cnt = 0
        self.F_obj, self.G_obj = self._eval(self.pop)
        self._update_best()
        print_action(f"Initial population ready. Feasible: {np.sum(self.G_obj <= 0)}/{self.ps}")

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

    def run(self, max_gen):
        if self.pop is None:
            self._init_pop()
        nv, self.history = self.problem.n_var, [self.best_f]

        for gen in range(max_gen):
            self.n_gen = gen + 1
            if self.n_gen == max_gen // 2 and self.best_g > 0:
                print_colored(
                    COLOR_WARNING,
                    "\n[ SHADE ] No feasible solution found. Restarting population around best infeasible.\n",
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
                self.arc_np = np.zeros((self.arc_sz, nv))
                self.arc_cnt = 0
                self.history.append(self.best_f)
                continue

            # 1. Parameter Adaptation Generation
            idx = self.rng.randint(0, self.H, self.ps)
            M_F_rand = np.array([self.M_F[i] for i in idx])
            M_CR_rand = np.array([self.M_CR[i] for i in idx])

            # Normal Distribution for CR
            CRa = np.clip(self.rng.normal(M_CR_rand, 0.1), 0.0, 1.0)

            # Strict Cauchy Resampling for F (Prevents 0.0 stagnation)
            Fa = np.zeros(self.ps)
            for i in range(self.ps):
                while True:
                    f_val = M_F_rand[i] + 0.1 * self.rng.standard_cauchy()
                    if f_val > 0.0:
                        Fa[i] = min(1.0, f_val)
                        break

            # 2. Pbest Selection
            pen = np.where(self.G_obj <= 0, self.F_obj, self.F_obj + 1e6)
            sidx = np.argsort(pen)
            pb_idx = sidx[self.rng.randint(0, max(1, int(self.ps * self.pb)), self.ps)]
            
            fs_idx = np.where(self.G_obj <= 0)[0]
            valid_cands = fs_idx if len(fs_idx) >= 3 else np.arange(self.ps)

            # 3. Exact Distinct Index Selection for P U A Archive
            r1 = np.zeros(self.ps, dtype=int)
            xa = np.zeros((self.ps, nv))

            for i in range(self.ps):
                # Sample r1
                while True:
                    c1 = valid_cands[self.rng.randint(0, len(valid_cands))]
                    if c1 != i:
                        r1[i] = c1
                        break
                
                # Sample r2 from Population Union Archive
                while True:
                    idx2 = self.rng.randint(0, len(valid_cands) + self.arc_cnt)
                    if idx2 < len(valid_cands):
                        c2 = valid_cands[idx2]
                        if c2 != i and c2 != r1[i]:
                            xa[i] = self.pop[c2]
                            break
                    else:
                        xa[i] = self.arc_np[idx2 - len(valid_cands)]
                        break

            # 4. Mutation & Crossover (DE/current-to-pbest/1/bin)
            mut = np.clip(
                self.pop
                + Fa[:, None] * (self.pop[pb_idx] - self.pop)
                + Fa[:, None] * (self.pop[r1] - xa),
                0.0,
                1.0,
            )
            
            cross_mask = self.rng.random((self.ps, nv)) < CRa[:, None]
            j_rand = self.rng.randint(0, nv, size=self.ps)
            cross_mask[np.arange(self.ps), j_rand] = True
            off = np.where(cross_mask, mut, self.pop)

            # 5. Evaluation
            Fo, Go = self._eval(off)
            pf, of = self.G_obj <= 0, Go <= 0
            
            # Strict Feasibility Selection
            rep = (
                (of & ~pf)
                | (of & pf & (Fo <= self.F_obj))
                | (~of & ~pf & (Go < self.G_obj))
            )
            replaced_idx = np.where(rep)[0]

            # 6. Memory and Archive Extraction
            if len(replaced_idx) > 0:
                # Calculate True Fitness Delta for Memory Weighting
                delta_f = np.zeros(len(replaced_idx))
                for k, i_rep in enumerate(replaced_idx):
                    if self.G_obj[i_rep] > 0 and Go[i_rep] <= 0:
                        delta_f[k] = 1.0  # Massive weight for finding feasible space
                    elif self.G_obj[i_rep] <= 0 and Go[i_rep] <= 0:
                        delta_f[k] = max(0.0, self.F_obj[i_rep] - Fo[i_rep])
                    else:
                        delta_f[k] = max(0.0, self.G_obj[i_rep] - Go[i_rep])

                # Normalize Weights
                sum_df = np.sum(delta_f)
                w = delta_f / sum_df if sum_df > 1e-10 else np.ones(len(delta_f)) / len(delta_f)

                sCR = CRa[rep]
                sF = Fa[rep]

                # Update Historical Memory (Weighted Arithmetic Mean for CR)
                self.M_CR[self.m_idx] = np.sum(w * sCR)

                # Update Historical Memory (Weighted Lehmer Mean for F)
                sum_wF = np.sum(w * sF)
                if sum_wF > 1e-10:
                    self.M_F[self.m_idx] = np.sum(w * sF**2) / sum_wF

                self.m_idx = (self.m_idx + 1) % self.H

                # Update Archive with replaced solutions
                for idx_rep in replaced_idx:
                    if self.arc_cnt < self.arc_sz:
                        self.arc_np[self.arc_cnt] = self.pop[idx_rep].copy()
                        self.arc_cnt += 1
                    else:
                        self.arc_np[self.rng.randint(0, self.arc_sz)] = self.pop[idx_rep].copy()

                # Execute Population Replacement
                self.pop[rep], self.F_obj[rep], self.G_obj[rep] = off[rep], Fo[rep], Go[rep]

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
                    f"SHADE Gen {self.n_gen:04d} | Best F: {self.best_f:.6e} | Feas: {np.sum(self.G_obj <= 0)}/{self.ps}"
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
# CORE MEMETIC ALGORITHM ORCHESTRATOR
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
    print_action(f"Stage 1: SHADE (Tanabe & Fukunaga, 2013) | Population: {ps}")
    print_action(
        "  - Smart Micro-Perturbation Seeding | Latin Hypercube centered on Seed"
    )

    # Create an evenly spaced matrix from 0.0 to 1.0
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

    shade = SHADE(
        problem=prob,
        pop_size=ps,
        F_init=0.5,
        CR_init=0.5,
        verbose=True,
        callback=ProgressCallback("SHADE"),
    )
    shade._init_pop(X0=X0_matrix)

    st_t = time.time()
    try:
        bx, bf, h_sh = shade.run(max_gen=opt_opts.pso_options.max_iterations)
    except KeyboardInterrupt:
        print_colored(COLOR_WARNING, "\n[ WARN ] Stage 1 interrupted.\n")
        bx, bf, h_sh = shade.best_x, shade.best_f, shade.history
    print("\n")
    print_colored(
        COLOR_GOOD, f"[ INFO ] SHADE completed in {time.time() - st_t:.2f} seconds.\n"
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
        if shade.best_g > 0:
            print_colored(
                COLOR_WARNING,
                f"Warning: Best SHADE solution infeasible (G={shade.best_g:.3f}). Proceeding.\n",
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
                h_sh.append(bf)
        except KeyboardInterrupt:
            print_colored(COLOR_WARNING, "\n[ WARN ] Stage 2 interrupted.\n")

    print()
    print_colored(
        COLOR_GOOD,
        f"[ SYSTEM ] Full Hybrid Optimization Executed in {time.time() - st_t:.2f} seconds\n",
    )
    ff, fa = write_final_results(bx, bf)
    print_action("Compiling Comprehensive Mathematical Convergence Report...")
    generate_report(commons.design_subdir, commons.output_prefix, s_foil, ff, h_sh)
    try:
        pool.close()
        pool.join()
    except:
        pass
    xfoil_cleanup()
    return ff, fa
