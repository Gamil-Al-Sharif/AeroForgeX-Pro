# ==============================================================================
# FILE: geom_builder.py
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
import os, copy, numpy as np
from scipy.special import comb
from geom_core import (
    AirfoilType,
    is_dat_file,
    is_normalized_coord,
    split_foil_into_sides,
    make_symmetrical,
    airfoil_write_with_shapes,
    build_from_sides,
    normalize,
    repanel_bezier,
    repanel_and_normalize,
    te_gap,
    set_geometry,
    set_te_gap,
    set_geometry_by_scale,
)
from utils_logger import (
    commons,
    my_stop,
    i_quality,
    r_quality,
    Q_OK,
    Q_BAD,
    Q_PROBLEM,
    Q_GOOD,
    COLOR_NOTE,
    COLOR_WARNING,
    COLOR_GOOD,
    COLOR_ERROR,
    COLOR_NORMAL,
    COLOR_FEATURE,
    print_action,
    print_note,
    print_warning,
    print_colored,
    print_colored_i,
    print_colored_r,
    print_text,
    stri,
)
from obj_utils import (
    eval_geometry_violations,
    eval_curvature_violations,
    assess_surface,
    VIOL_LE_CURV_MONOTON,
    max_curvature_at_te,
)
from math_accelerator import (
    find_closest_index,
    count_reversals,
    min_threshold_for_reversals,
    derivative1,
    spline_2D,
)
from opt_utils import simplexsearch, SimplexOptionsType
from shape_functions_param import (
    is_bezier_file,
    load_bezier_airfoil,
    ncp_to_ndv,
    bezier_curvature,
    get_initial_bezier,
    bezier_create_airfoil,
    ncp_to_ndv_side,
    ShapeBezierType,
    BezierSpecType,
    map_dv_to_bezier,
    bezier_get_dv0,
    bezier_get_dv_inital_perturb,
    print_bezier_spec,
    bezier_eval_y_on_x,
    ShapeCambThickType,
    map_dv_to_camb_thick,
    ShapeCSTType,
    CSTSpecType,
    map_dv_to_cst_weights,
    cst_create_airfoil,
    cst_get_dv0,
    fit_cst_to_coordinates,
    is_hh_file,
    load_hh_airfoil,
    ShapeHHType,
    HHSpecType,
    map_dv_to_hhs,
    hh_get_dv0,
    hh_eval_side,
    nfunctions_to_ndv,
    hh_get_dv_inital_perturb,
    print_hh_spec,
)
from solver_xfoil import FlapSpecType

HICKS_HENNE, BEZIER, CAMB_THICK, CST = 1, 2, 3, 4


# =============================================================================
# EXACT MATHEMATICAL ENGINE: KULFAN CST WITH LEM
# =============================================================================
class CompositeCST:
    def __init__(self, nt=8, nb=8):
        self.nt, self.nb, self.ndv = nt, nb, nt + nb + 2
        self.w_bnd, self.le_bnd, self.te_bnd = 1.0, 1.0, 0.15
        self._cached_n_pts = None

    def _bernstein(self, x, n_w):
        N = n_w - 1
        return (
            comb(N, np.arange(N + 1))[:, None]
            * (x ** np.arange(N + 1)[:, None])
            * ((1.0 - x) ** (N - np.arange(N + 1))[:, None])
        )

    def _build_A(self, sx, is_u, nt, nb):
        C = (sx**0.5) * (1.0 - sx)
        Au, Ab = (
            np.where(is_u, C * self._bernstein(sx, nt), 0).T,
            np.where(~is_u, C * self._bernstein(sx, nb), 0).T,
        )
        Ale = (sx * np.maximum(1.0 - sx, 0.0) ** (np.where(is_u, nt, nb) + 0.5))[
            :, None
        ]
        return np.concatenate(
            [Ab, Au, Ale, np.where(is_u, sx / 2.0, -sx / 2.0)[:, None]], axis=1
        )

    def fit_seed(self, sx, sy):
        print_action("Executing Inverse Least-Squares mapping for Composite CST...")
        is_u, ty = np.arange(len(sx)) <= np.argmin(sx), sy.copy()
        if self.nt > 5 or self.nb > 5:
            print_action(
                "High-order CST detected. Executing Level-5 Cascade-Fit filter..."
            )
            Ai = self._build_A(sx, is_u, min(self.nt, 5), min(self.nb, 5))
            ty = Ai @ np.linalg.lstsq(Ai, ty, rcond=None)[0]

        xopt = np.linalg.lstsq(
            self._build_A(sx, is_u, self.nt, self.nb), ty, rcond=None
        )[0]
        lw, uw, le_w, te_t = (
            xopt[: self.nb],
            xopt[self.nb : self.nb + self.nt],
            xopt[-2],
            max(0.0, xopt[-1]),
        )

        dv = np.zeros(self.ndv)
        dv[: self.nb], dv[self.nb : self.nb + self.nt] = (
            (lw + self.w_bnd) / (2.0 * self.w_bnd),
            (uw + self.w_bnd) / (2.0 * self.w_bnd),
        )
        dv[-2], dv[-1] = (le_w + self.le_bnd) / (2.0 * self.le_bnd), te_t / self.te_bnd
        return np.clip(dv, 0.0, 1.0)

    def gen_foil(self, dv, foil, n_pts=150):
        if self._cached_n_pts != n_pts:
            self._cached_n_pts = n_pts
            self._x = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, n_pts)))
            self._cx = (self._x**0.5) * (1.0 - self._x)
            self._B_bot = self._bernstein(self._x, self.nb)
            self._B_top = self._bernstein(self._x, self.nt)
            self._le_bot = self._x * ((1.0 - self._x) ** (self.nb + 0.5))
            self._le_top = self._x * ((1.0 - self._x) ** (self.nt + 0.5))

        lw, uw = (
            dv[: self.nb] * 2.0 * self.w_bnd - self.w_bnd,
            dv[self.nb : self.nb + self.nt] * 2.0 * self.w_bnd - self.w_bnd,
        )
        le_w, te_t = dv[-2] * 2.0 * self.le_bnd - self.le_bnd, dv[-1] * self.te_bnd

        x = self._x.copy()
        yl = (
            self._cx * np.sum(lw[:, None] * self._B_bot, axis=0)
            + le_w * self._le_bot
            - x * (te_t / 2.0)
        )
        yu = (
            self._cx * np.sum(uw[:, None] * self._B_top, axis=0)
            + le_w * self._le_top
            + x * (te_t / 2.0)
        )

        # =======================================================
        # ABSOLUTE NORMALIZATION LOCKS (Anti-Crash Protection)
        # =======================================================
        # 1. Force exact (0,0) at the Leading Edge
        x[0], yu[0], yl[0] = 0.0, 0.0, 0.0

        # 2. Force exact X=1.0 at the Trailing Edge
        x[-1] = 1.0

        # 3. Force perfect Y-axis symmetry at the Trailing Edge
        avg_te = (abs(yu[-1]) + abs(yl[-1])) / 2.0
        yu[-1] = avg_te
        yl[-1] = -avg_te
        # =======================================================

        foil.x, foil.y, foil.name, foil.is_bezier_based = (
            np.concatenate((x[::-1], x[1:])),
            np.concatenate((yu[::-1], yl[1:])),
            "CST_Foil",
            False,
        )
        split_foil_into_sides(foil)


# =============================================================================
# DATA STRUCTURES & SETUP
# =============================================================================
class ShapeSpecType:
    def __init__(self):
        self.type, self.type_as_text, self.camber_type, self.ndv = (
            HICKS_HENNE,
            "hicks-henne",
            "",
            0,
        )
        self.hh, self.bezier, self.camb_thick, self.cst, self.flap_spec = (
            ShapeHHType(),
            ShapeBezierType(),
            ShapeCambThickType(),
            ShapeCSTType(),
            FlapSpecType(),
        )


_shape_spec, _seed_foil, composite_cst_handler = ShapeSpecType(), AirfoilType(), None


def set_shape_spec(sf, ss):
    global _seed_foil, _shape_spec, composite_cst_handler
    _seed_foil, _shape_spec = copy.deepcopy(sf), copy.deepcopy(ss)
    if _shape_spec.type == CST:
        composite_cst_handler = CompositeCST(
            nt=_shape_spec.cst.n_weights_top, nb=_shape_spec.cst.n_weights_bot
        )
        _shape_spec.dv0 = composite_cst_handler.fit_seed(_seed_foil.x, _seed_foil.y)
        _shape_spec.ndv = len(_shape_spec.dv0)
        print_action(
            f"Composite CST Active: {_shape_spec.cst.n_weights_top} Top, {_shape_spec.cst.n_weights_bot} Bot, +1 LE Weight, +1 TE Thick"
        )


def get_seed_foil():
    return copy.deepcopy(_seed_foil)


def get_shape_spec():
    return _shape_spec


def assess_shape():
    if not commons.show_details:
        return
    if _shape_spec.camber_type in ["reflexed", "rear-loading"]:
        print_note(
            f"1 reversal on {'Upper' if _shape_spec.camber_type == 'reflexed' else 'Lower'} side - Target assumed to be {_shape_spec.camber_type}",
            3,
        )
    print_action("Activating Parametric Synthesis Engine: ", no_crlf=True)
    print_colored(COLOR_FEATURE, _shape_spec.type_as_text)
    print()
    ndv, nf = 0, _shape_spec.flap_spec.ndv
    if _shape_spec.type == BEZIER:
        ndv = ncp_to_ndv_side(_shape_spec.bezier.ncp_top) + ncp_to_ndv_side(
            _shape_spec.bezier.ncp_bot
        )
    elif _shape_spec.type == HICKS_HENNE:
        ndv = nfunctions_to_ndv(_shape_spec.hh.nfunctions_top) + nfunctions_to_ndv(
            _shape_spec.hh.nfunctions_bot
        )
    elif _shape_spec.type == CAMB_THICK:
        ndv = _shape_spec.camb_thick.ndv
    elif _shape_spec.type == CST:
        ndv = _shape_spec.cst.n_weights_top + _shape_spec.cst.n_weights_bot
    if nf > 0:
        ndv += nf
        print_action(f"Flap Matrix Active: {nf} Variables")
    print_action(f"Total Topological Dimensions: {ndv}")


# =============================================================================
# GEOMETRY SYNTHESIS ENGINE
# =============================================================================
def create_airfoil_cst(dv, foil):
    composite_cst_handler.gen_foil(dv, foil, n_pts=(len(_seed_foil.x) // 2) + 1)


def create_airfoil_hicks_henne(dv, foil):
    nt = nfunctions_to_ndv(_shape_spec.hh.nfunctions_top)
    foil.top_hh.hhs = map_dv_to_hhs(dv[:nt])
    if not _seed_foil.symmetrical:
        foil.bot_hh.hhs = map_dv_to_hhs(dv[nt:])
    foil.hh_seed_x, foil.hh_seed_y, foil.hh_seed_name = (
        (
            _seed_foil.hh_seed_x.copy(),
            _seed_foil.hh_seed_y.copy(),
            _seed_foil.hh_seed_name,
        )
        if _seed_foil.is_hh_based
        else (_seed_foil.x.copy(), _seed_foil.y.copy(), _seed_foil.name)
    )
    foil.symmetrical = _seed_foil.symmetrical
    build_from_hh_seed(foil)


def build_from_hh_seed(f):
    il = np.argmin(f.hh_seed_x)
    stx, sty = f.hh_seed_x[il::-1], f.hh_seed_y[il::-1]
    tyn = hh_eval_side(f.top_hh, stx, sty)
    sbx, sby, byn = (
        (stx, -sty, -tyn)
        if f.symmetrical
        else (
            f.hh_seed_x[il:],
            f.hh_seed_y[il:],
            hh_eval_side(f.bot_hh, f.hh_seed_x[il:], f.hh_seed_y[il:]),
        )
    )
    f.top.x, f.top.y, f.bot.x, f.bot.y, f.is_hh_based = stx, tyn, sbx, byn, True
    build_from_sides(f)


def create_airfoil_bezier(dv, f):
    tg, nt = te_gap(_seed_foil) / 2.0, ncp_to_ndv_side(_shape_spec.bezier.ncp_top)
    map_dv_to_bezier("Top", dv[:nt], tg, f.top_bezier)
    if not _seed_foil.symmetrical:
        map_dv_to_bezier("Bot", dv[nt:], tg, f.bot_bezier)
    else:
        f.bot_bezier = copy.deepcopy(f.top_bezier)
        f.bot_bezier.py = -f.bot_bezier.py
    f.x, f.y = bezier_create_airfoil(f.top_bezier, f.bot_bezier, len(_seed_foil.x))
    f.is_bezier_based = True
    split_foil_into_sides(f)


def create_airfoil_camb_thick(dv, f):
    fmt, fxm, fmc, fxmc, flr, lb = map_dv_to_camb_thick(dv, _shape_spec.camb_thick)
    f.x, f.y, f.name = _seed_foil.x.copy(), _seed_foil.y.copy(), _seed_foil.name
    split_foil_into_sides(f)
    set_geometry_by_scale(f, fmt, fxm, fmc, fxmc, flr, lb)


# =============================================================================
# DESIGN VARIABLE MAPPER
# =============================================================================
def get_ndv_of_shape():
    return (
        _shape_spec.camb_thick.ndv
        if _shape_spec.type == CAMB_THICK
        else composite_cst_handler.ndv
        if _shape_spec.type == CST
        else (
            ncp_to_ndv_side(_shape_spec.bezier.ncp_top)
            + (
                0
                if _seed_foil.symmetrical
                else ncp_to_ndv_side(_shape_spec.bezier.ncp_bot)
            )
            if _shape_spec.type == BEZIER
            else nfunctions_to_ndv(_shape_spec.hh.nfunctions_top)
            + (
                0
                if _seed_foil.symmetrical
                else nfunctions_to_ndv(_shape_spec.hh.nfunctions_bot)
            )
        )
    )


def get_ndv_of_flaps():
    return _shape_spec.flap_spec.ndv


def get_dv0_of_shape():
    if _shape_spec.type == CAMB_THICK:
        return np.full(_shape_spec.camb_thick.ndv, 0.5)
    if _shape_spec.type == CST:
        return _shape_spec.dv0
    if _shape_spec.type == BEZIER:
        return (
            bezier_get_dv0("Top", _seed_foil.top_bezier)
            if _seed_foil.symmetrical
            else np.concatenate(
                (
                    bezier_get_dv0("Top", _seed_foil.top_bezier),
                    bezier_get_dv0("Bot", _seed_foil.bot_bezier),
                )
            )
        )
    from shape_functions_param import map_hhs_to_dv

    return (
        map_hhs_to_dv(_seed_foil.top_hh.hhs)
        if _seed_foil.symmetrical and _seed_foil.is_hh_based
        else (
            np.concatenate(
                (
                    map_hhs_to_dv(_seed_foil.top_hh.hhs),
                    map_hhs_to_dv(_seed_foil.bot_hh.hhs),
                )
            )
            if _seed_foil.is_hh_based
            else (
                hh_get_dv0(_shape_spec.hh.nfunctions_top)
                if _seed_foil.symmetrical
                else np.concatenate(
                    (
                        hh_get_dv0(_shape_spec.hh.nfunctions_top),
                        hh_get_dv0(_shape_spec.hh.nfunctions_bot),
                    )
                )
            )
        )
    )


def get_dv_initial_perturb_of_shape():
    if _shape_spec.type == CAMB_THICK:
        return np.full(
            _shape_spec.camb_thick.ndv, _shape_spec.camb_thick.initial_perturb
        )

    if _shape_spec.type == CST:
        # ===========================================================
        # SMART MICRO-SEEDING FOR CST (Fixes Dimensionality Curse)
        # ===========================================================
        ini = _shape_spec.cst.initial_perturb

        # Scale down standard weights so high-order polynomials don't ripple
        dv = np.full(composite_cst_handler.ndv, min(0.1, ini * 0.4))

        # The LE weight (dv[-2]) and TE thickness (dv[-1]) control massive traits.
        # Restrict these heavily so XFOIL doesn't crash on Gen 0.
        dv[-2] = min(0.05, ini * 0.1)  # Micro-perturb LE Radius Weight
        dv[-1] = min(0.05, ini * 0.2)  # Micro-perturb TE Thickness
        return dv
        # ===========================================================

    if _shape_spec.type == BEZIER:
        return (
            bezier_get_dv_inital_perturb(
                _shape_spec.bezier.initial_perturb, _seed_foil.top_bezier
            )
            if _seed_foil.symmetrical
            else np.concatenate(
                (
                    bezier_get_dv_inital_perturb(
                        _shape_spec.bezier.initial_perturb, _seed_foil.top_bezier
                    ),
                    bezier_get_dv_inital_perturb(
                        _shape_spec.bezier.initial_perturb, _seed_foil.bot_bezier
                    ),
                )
            )
        )

    # Hicks-Henne fallback
    from shape_functions_param import hh_get_dv_inital_perturb

    return (
        hh_get_dv_inital_perturb(
            _shape_spec.hh.initial_perturb, _shape_spec.hh.nfunctions_top
        )
        if _seed_foil.symmetrical
        else np.concatenate(
            (
                hh_get_dv_inital_perturb(
                    _shape_spec.hh.initial_perturb, _shape_spec.hh.nfunctions_top
                ),
                hh_get_dv_inital_perturb(
                    _shape_spec.hh.initial_perturb, _shape_spec.hh.nfunctions_bot
                ),
            )
        )
    )


def get_dv0_of_flaps():
    nf = _shape_spec.flap_spec.ndv
    return (
        np.array([])
        if nf == 0
        else np.full(nf, 0.5)
        if len(_shape_spec.flap_spec.start_flap_angle) != nf
        else np.clip(
            [
                (
                    (a - _shape_spec.flap_spec.min_flap_angle)
                    / (
                        _shape_spec.flap_spec.max_flap_angle
                        - _shape_spec.flap_spec.min_flap_angle
                    )
                )
                if _shape_spec.flap_spec.max_flap_angle
                != _shape_spec.flap_spec.min_flap_angle
                else 0.5
                for a in _shape_spec.flap_spec.start_flap_angle
            ],
            0.0,
            1.0,
        )
    )


def get_dv_initial_perturb_of_flaps():
    return (
        np.full(_shape_spec.flap_spec.ndv, 0.05)
        if _shape_spec.flap_spec.ndv > 0
        else np.array([])
    )


def get_flap_angles_optimized(dv):
    return (
        np.array([])
        if _shape_spec.flap_spec.ndv == 0
        else _shape_spec.flap_spec.min_flap_angle
        + dv[-_shape_spec.flap_spec.ndv :]
        * (_shape_spec.flap_spec.max_flap_angle - _shape_spec.flap_spec.min_flap_angle)
    )


# =============================================================================
# SEED PREPARATION & DIAGNOSTICS
# =============================================================================
_m_sd, _m_tx, _m_ty, _m_lc, _m_lw, _m_teg, _m_ev = None, None, None, 0.0, 0.0, 0.0, 0


def get_airfoil(fn, silent_mode=False):
    f = AirfoilType()
    if is_dat_file(fn):
        if not silent_mode:
            print_action("Reading coordinates", fn)
        from geom_core import airfoil_load

        f = airfoil_load(fn)
    elif is_bezier_file(fn):
        if not silent_mode:
            print_action("Reading Bezier", fn)
        f.is_bezier_based = True
        f.name, f.x, f.y, f.top_bezier, f.bot_bezier = load_bezier_airfoil(fn, 161)
    elif is_hh_file(fn):
        if not silent_mode:
            print_action("Reading Hicks-Henne", fn)
        f.is_hh_based = True
        f.name, f.top_hh, f.bot_hh, f.hh_seed_name, f.hh_seed_x, f.hh_seed_y = (
            load_hh_airfoil(fn)
        )
        build_from_hh_seed(f)
    else:
        my_stop(f"Unknown type: '{fn}'")
    return f


def prepare_seed_foil(fn, ev_sp, shp_sp):
    of = get_airfoil(fn)
    if not is_normalized_coord(of):
        normalize(of, basic=True)
    split_foil_into_sides(of)
    sf = AirfoilType()
    if of.is_bezier_based:
        repanel_bezier(of, sf, ev_sp.panel_options)
    elif of.is_hh_based:
        sf = copy.deepcopy(of)
    else:
        repanel_and_normalize(of, sf, ev_sp.panel_options)

    if ev_sp.geo_constraints.symmetrical:
        make_symmetrical(sf)
    if not (shp_sp.type == BEZIER and sf.is_bezier_based) and not (
        shp_sp.type == HICKS_HENNE and sf.is_hh_based
    ):
        preset_airfoil_to_targets(ev_sp.geo_targets, sf)

    if shp_sp.type == BEZIER:
        if sf.is_bezier_based:
            shp_sp.bezier.ncp_top, shp_sp.bezier.ncp_bot = (
                len(sf.top_bezier.px),
                len(sf.bot_bezier.px),
            )
        else:
            sf.name += f"-bezier{shp_sp.bezier.ncp_top}{shp_sp.bezier.ncp_bot}"
            transform_to_bezier_based(shp_sp.bezier, ev_sp.panel_options, sf)
        shp_sp.bezier.ndv = ncp_to_ndv_side(shp_sp.bezier.ncp_top) + ncp_to_ndv_side(
            shp_sp.bezier.ncp_bot
        )
    elif shp_sp.type == HICKS_HENNE:
        if sf.is_hh_based:
            shp_sp.hh.nfunctions_top, shp_sp.hh.nfunctions_bot = (
                len(sf.top_hh.hhs),
                len(sf.bot_hh.hhs),
            )
        elif shp_sp.hh.smooth_seed:
            transform_to_bezier_based(shp_sp.bezier, ev_sp.panel_options, sf)
            sf.name += "-smoothed"
            sf.is_bezier_based = True
        shp_sp.hh.ndv = nfunctions_to_ndv(shp_sp.hh.nfunctions_top) + nfunctions_to_ndv(
            shp_sp.hh.nfunctions_bot
        )

    check_seed(
        sf, shp_sp, ev_sp.curv_constraints, ev_sp.geo_constraints, ev_sp.xfoil_options
    )
    airfoil_write_with_shapes(sf, commons.design_subdir, highlight=False)
    return sf


def prepare_match_foil(sf, m_sp):
    mf = get_airfoil(m_sp.filename)
    if not is_normalized_coord(mf):
        normalize(mf, basic=True)
    split_foil_into_sides(mf)
    m_sp.foil = mf
    if abs(te_gap(sf) - te_gap(mf)) > 1e-4:
        print_warning("Topological conflict: TE gaps diverge.", 5)
    m_sp.target_top_x, m_sp.target_top_y = match_get_targets(mf.top)
    m_sp.target_bot_x, m_sp.target_bot_y = match_get_targets(mf.bot)


def preset_airfoil_to_targets(tgts, f):
    nt, nc, tg = None, None, te_gap(f)
    for g in tgts:
        if g.preset_to_target:
            if g.type == "thickness":
                nt = g.target_value
                print_action("Forcing thickness to target", f"{nt:.4f}")
                set_geometry(f, maxt=nt)
                set_te_gap(f, tg) if tg > 0 else None
            elif g.type == "camber":
                nc = g.target_value
                print_action("Forcing camber to target", f"{nc:.4f}")
                set_geometry(f, maxc=nc)
    if nt is not None or nc is not None:
        f.name += "-preset"


def check_seed(sf, shp_sp, cc, gc, xo):
    if cc.check_curvature:
        if shp_sp.type == HICKS_HENNE:
            print_action("Evaluating topology for HH perturbations")
            check_airfoil_curvature(cc, sf)
        if cc.auto_curvature:
            print_action("Automated Curvature Profiling: Calibrating exact constraints")
            auto_curvature_constraints(sf.top, cc.top)
            auto_curvature_constraints(sf.bot, cc.bot) if not sf.symmetrical else None
            if (
                shp_sp.type == BEZIER
                and abs(cc.max_le_curvature_diff - 5.0) < 1e-4
                and sf.is_bezier_based
            ):
                cc.max_le_curvature_diff = max(
                    abs(
                        bezier_curvature(sf.top_bezier, 0.0)
                        - bezier_curvature(sf.bot_bezier, 0.0)
                    )
                    * 1.1,
                    abs(
                        bezier_curvature(sf.top_bezier, 0.0)
                        - bezier_curvature(sf.bot_bezier, 0.0)
                    )
                    + 2.0,
                )
        if shp_sp.type == HICKS_HENNE:
            auto_check_curvature_bumps_side(sf.top, cc.top)
            auto_check_curvature_bumps_side(
                sf.bot, cc.bot
            ) if not sf.symmetrical else None
        else:
            cc.top.check_curvature_bumps = cc.bot.check_curvature_bumps = False
        check_handle_curve_violations(sf.top, cc.top)
        check_te_curvature_violations(sf.top, cc.top)
        if not sf.symmetrical:
            check_handle_curve_violations(sf.bot, cc.bot)
            check_te_curvature_violations(sf.bot, cc.bot)
    if gc.check_geometry:
        print_action("Validating physical geometric bounds ... ", no_crlf=True)
        hv, _, inf = eval_geometry_violations(sf, gc)
        if hv:
            print()
            print_warning(inf, 5)
            my_stop("FATAL: Seed violates constraints.")
        elif commons.show_details:
            print_colored(COLOR_NORMAL, "Ok\n")
    if cc.check_curvature:
        print_action("Validating analytical curvature limits ... ", no_crlf=True)
        hv, vid, inf = eval_curvature_violations(sf, cc)
        if vid == VIOL_LE_CURV_MONOTON:
            print()
            print_warning(inf, 5)
            print_note("Bypassing LE monotonicity check.")
            cc.top.check_le_curvature = cc.bot.check_le_curvature = False
        elif hv:
            print()
            my_stop(inf)
        elif commons.show_details:
            print_colored(COLOR_NORMAL, "Ok\n")


def check_airfoil_curvature(cc, f):
    qt, qb = (
        assess_surface(
            f.top,
            commons.show_details,
            cc.top.nskip_LE + 1,
            len(f.top.x),
            len(f.top.x),
            cc.top.curv_threshold,
            cc.top.spike_threshold,
        ),
        assess_surface(
            f.top,
            commons.show_details,
            cc.top.nskip_LE + 1,
            len(f.top.x),
            len(f.top.x),
            cc.top.curv_threshold,
            cc.top.spike_threshold,
        )
        if f.symmetrical
        else assess_surface(
            f.bot,
            commons.show_details,
            cc.bot.nskip_LE + 1,
            len(f.bot.x),
            len(f.bot.x),
            cc.bot.curv_threshold,
            cc.bot.spike_threshold,
        ),
    )
    oa = (qt + qb) // 2
    print_colored(COLOR_NOTE, "   Airfoil curvature assessment: ")
    if oa < Q_OK:
        print_colored(COLOR_NOTE, "Topology Quality: ")
        print_colored(COLOR_GOOD, "Perfect")
    elif oa < Q_BAD:
        print_colored(COLOR_NOTE, "Topology Quality: ")
        print_colored(COLOR_NORMAL, "Acceptable")
    elif oa < Q_PROBLEM:
        print_colored(COLOR_NOTE, "Topology Quality marginal. ")
        print_colored(COLOR_WARNING, "Consider a smoother seed.")
    else:
        print_colored(COLOR_ERROR, " CRITICAL: Curvature represents severe corruption.")
    print()
    return oa


def auto_curvature_constraints(s, c):
    th = min_threshold_for_reversals(
        c.nskip_LE + 1, len(s.x), s.curvature, 0.01, 4.0, c.max_curv_reverse
    )
    c.curv_threshold = th * 1.1
    if c.check_curvature_bumps:
        sp_th = min_threshold_for_reversals(
            c.nskip_LE + 1,
            len(s.x),
            derivative1(s.x, s.curvature),
            0.2,
            1.0,
            count_reversals(
                c.nskip_LE + 1,
                len(s.x),
                derivative1(s.x, s.curvature),
                c.spike_threshold,
            ),
        )
        c.spike_threshold = max(sp_th * 1.1, sp_th + 0.03)
        c.max_spikes = (
            count_reversals(
                c.nskip_LE + 1,
                len(s.x),
                derivative1(s.x, s.curvature),
                c.spike_threshold,
            )
            if c.max_spikes == 0
            else c.max_spikes
        )
    if abs(c.max_te_curvature - 4.9999) < 1e-4:
        c.max_te_curvature = max(
            max_curvature_at_te(s.curvature) * 1.1,
            max_curvature_at_te(s.curvature) + 0.05,
        )


def auto_check_curvature_bumps_side(s, c):
    c.check_curvature_bumps = (
        c.spike_threshold <= 0.5
        and c.max_spikes <= 5
        and count_reversals(
            c.nskip_LE + 1, len(s.x), derivative1(s.x, s.curvature), c.spike_threshold
        )
        <= c.max_spikes
    )


def check_handle_curve_violations(s, c):
    nrev, nspk = (
        count_reversals(c.nskip_LE + 1, len(s.x), s.curvature, c.curv_threshold),
        count_reversals(
            c.nskip_LE + 1, len(s.x), derivative1(s.x, s.curvature), c.spike_threshold
        )
        if c.check_curvature_bumps
        else 0,
    )
    if nrev > c.max_curv_reverse or nspk > c.max_spikes:
        print()
        print_warning(f"FATAL Curvature Violations on {s.name} Side:")
        if nrev > c.max_curv_reverse:
            print(
                f"          Found {nrev} Macro-Reversals (Allowed: {c.max_curv_reverse})"
            )
        if nspk > c.max_spikes:
            print(f"          Found {nspk} Micro-Spikes (Allowed: {c.max_spikes})")
        print()
        my_stop("Optimizer prevented from starting with violated limits.")


def check_te_curvature_violations(s, c):
    my_stop(
        f"TE mathematical curvature of {max_curvature_at_te(s.curvature):.2f} on {s.name} violates limit ({c.max_te_curvature})."
    ) if max_curvature_at_te(s.curvature) > c.max_te_curvature else None


# =============================================================================
# CURVE FITTING & TOPOLOGICAL MATCHING ENGINE
# =============================================================================
def transform_to_bezier_based(shpb, popt, f):
    if not is_normalized_coord(f):
        my_stop("Mathematical fitting requires pre-normalized coordinate systems.")
    split_foil_into_sides(f)
    print_action("Initializing Simplex Curve-Fitting Engine")
    lc = match_get_best_le_curvature(f)
    for w in [0.5, 1.0, 2.0, 4.0]:
        f.top_bezier, ok = match_bezier_side(f.top, lc, w, shpb.ncp_top)
        if ok:
            break
    for w in [0.5, 1.0, 2.0, 4.0]:
        f.bot_bezier, ok = match_bezier_side(f.bot, lc, w, shpb.ncp_bot)
        if ok:
            break
    f.x, f.y = bezier_create_airfoil(f.top_bezier, f.bot_bezier, popt.npoint)
    f.is_bezier_based = True
    split_foil_into_sides(f)


def match_get_targets(s):
    tx, ty, x = [], [], 0.02
    while x < 1.0:
        idx = find_closest_index(s.x, x)
        tx.append(s.x[idx])
        ty.append(s.y[idx])
        x += 0.03 if x > 0.8 else (0.04 if x > 0.25 else 0.04)
    return np.array(tx), np.array(ty)


def match_get_best_le_curvature(f):
    tc, bc = np.abs(f.top.curvature), np.abs(f.bot.curvature)
    at_le, mx_ar = tc[0], max(np.max(tc[:5]), np.max(bc[:5]))
    return (
        (mx_ar + at_le) / 2.0
        if mx_ar > at_le
        else (
            (at_le + tc[2]) / 2.0
            if tc[1] < tc[2]
            else ((at_le + bc[2]) / 2.0 if bc[1] < bc[2] else at_le)
        )
    )


def match_bezier_side(s, lc, lw, ncp):
    global _m_sd, _m_tx, _m_ty, _m_lc, _m_lw, _m_teg, _m_ev
    _m_sd, _m_lc, _m_lw, _m_teg, _m_ev, _m_tx, _m_ty = (
        s,
        lc,
        lw,
        s.y[-1],
        0,
        *match_get_targets(s),
    )
    tb, opt = BezierSpecType(), SimplexOptionsType()
    opt.min_radius, opt.max_iterations, opt.initial_step = 1e-5, 4000, 0.16
    get_initial_bezier(s.name, _m_tx, _m_ty, _m_teg, ncp, tb)
    xopt = simplexsearch(match_bezier_objective, bezier_get_dv0(s.name, tb), opt)[0]
    rb = BezierSpecType()
    map_dv_to_bezier(s.name, xopt, _m_teg, rb)
    return rb, True


def match_bezier_objective(dv):
    b = BezierSpecType()
    map_dv_to_bezier(_m_sd.name, dv, _m_teg, b)
    return (
        np.linalg.norm(
            [
                abs(bezier_eval_y_on_x(b, tx, eps=1e-8) - ty)
                for tx, ty in zip(_m_tx, _m_ty)
            ]
        )
        * 1000.0
        + (abs(_m_lc - abs(bezier_curvature(b, 0.0))) / 40.0) * _m_lw
    )
