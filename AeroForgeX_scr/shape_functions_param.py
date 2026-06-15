# ==============================================================================
# FILE: shape_functions_param.py
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
import os, math, numpy as np
from numba import njit

# from utils_logger import my_stop, print_error, print_colored, stri, strf, COLOR_NORMAL
from math_accelerator import linspace, find_closest_index


# =============================================================================
# NUMBA COMPILED CORE (C-SPEED MATH ENGINE)
# =============================================================================
@njit(cache=True, fastmath=True)
def _nCr(n, k):
    if k < 0 or k > n:
        return 0
    if k == 0 or k == n:
        return 1
    k, c = min(k, n - k), 1
    for i in range(k):
        c = c * (n - i) // (i + 1)
    return c


@njit(cache=True, fastmath=True)
def _diff_1D_njit(x):
    out = np.zeros(len(x) - 1, dtype=np.float64)
    for i in range(len(x) - 1):
        out[i] = x[i + 1] - x[i]
    return out


@njit(cache=True, fastmath=True)
def _hh_eval_tensor(st_arr, loc_arr, wid_arr, x):
    y = np.zeros_like(x)
    for k in range(len(st_arr)):
        st, loc, wid = st_arr[k], loc_arr[k], wid_arr[k]
        t1, t2 = max(0.001, min(0.999, loc)), max(0.01, min(50.0, wid))
        p = np.log10(0.5) / np.log10(t1)
        for i in range(len(x)):
            if 0.0 < x[i] < 1.0:
                v = st * (np.abs(np.sin(np.pi * (x[i] ** p))) ** t2)
                y[i] += v if abs(v) >= 1e-20 else 0.0
    return y


_bez_basis_cache = {}

@njit(cache=True, fastmath=True)
def _build_bez_basis(n, u):
    B = np.zeros((len(u), n + 1), np.float64)
    for j in range(len(u)):
        for i in range(n + 1):
            B[j, i] = _nCr(n, i) * (u[j]**i) * ((1.0 - u[j])**(n - i))
    return B

def _get_bez_basis(n, u):
    key = (n, len(u))
    if key not in _bez_basis_cache:
        _bez_basis_cache[key] = _build_bez_basis(n, u)
    return _bez_basis_cache[key]

def _bez_1d_arr(px, u, der):
    n, w = len(px) - 1, px.copy()
    if der > 0:
        for _ in range(der):
            w, n = _diff_1D_njit(w) * n, n - 1
    B = _get_bez_basis(n, u)
    return B @ w


@njit(cache=True, fastmath=True)
def _bez_1d_scl(px, u, der):
    n, w = len(px) - 1, px.copy()
    for _ in range(der):
        w, n = _diff_1D_njit(w) * n, n - 1
    res = 0.0
    for i in range(len(w)):
        res += _nCr(n, i) * (u**i) * ((1.0 - u) ** (n - i)) * w[i]
    return res


@njit(cache=True, fastmath=True)
def _bez_curv(px, py, u, is_u):
    dx, dy, ddx, ddy = (
        _bez_1d_scl(px, u, 1),
        _bez_1d_scl(py, u, 1),
        _bez_1d_scl(px, u, 2),
        _bez_1d_scl(py, u, 2),
    )
    den = (dx**2 + dy**2) ** 1.5
    return (
        (-(ddy * dx - ddx * dy) / den)
        if is_u
        else ((ddy * dx - ddx * dy) / den)
        if den != 0.0
        else 0.0
    )


@njit(cache=True, fastmath=True)
def _bez_inv(px, py, xt, eps):
    if xt <= px[0]:
        return py[0]
    if xt >= px[-1]:
        return py[-1]
    u = max(0.05, min(0.95, xt))
    for _ in range(100):
        u = max(1e-10, min(1.0, u))
        xn = _bez_1d_scl(px, u, 0) - xt
        if abs(xn) < eps:
            break
        dxn = _bez_1d_scl(px, u, 1)
        if dxn == 0.0:
            break
        u -= xn / dxn
    return _bez_1d_scl(py, u, 0)


@njit(cache=True, fastmath=True)
def _u_dist_bez(n_pts):
    if n_pts < 2:
        return np.array([0.0], np.float64)
    du, dip, ip = np.ones(n_pts - 1, np.float64), 0.8, 0
    while dip < 1.0 and ip < len(du):
        du[ip], ip, dip = dip, ip + 1, dip * 1.1
    dip, ip = 0.5, len(du) - 1
    while dip < 1.0 and ip >= 0:
        du[ip], ip, dip = dip, ip - 1, dip * 1.4
    u = np.zeros(n_pts, np.float64)
    for i in range(len(du)):
        u[i + 1] = u[i] + du[i]
    return u / u[-1]


@njit(cache=True, fastmath=True)
def _dv_to_fac(dv, fmin, fmax):
    dvc = max(-0.5, min(0.5, dv - 0.5))
    return (
        1.0
        if dvc == 0.0
        else (
            1.0 - 2.0 * abs(dvc) * (1.0 - fmin)
            if dvc < 0.0
            else 1.0 + 2.0 * abs(dvc) * (fmax - 1.0)
        )
    )


@njit(cache=True, fastmath=True)
def _cst_eval(w, x, n1, n2, dz):
    c, n, s = (x**n1) * ((1.0 - x) ** n2), len(w) - 1, np.zeros_like(x)
    for i in range(len(w)):
        s += _nCr(n, i) * (x**i) * ((1.0 - x) ** (n - i)) * w[i]
    return c * s + x * dz


@njit(cache=True, fastmath=True)
def _build_cst_A(x, nw):
    A, d = np.zeros((len(x), nw), np.float64), nw - 1
    for j in range(len(x)):
        for i in range(nw):
            A[j, i] = _nCr(d, i) * (x[j] ** i) * ((1.0 - x[j]) ** (d - i))
    return A


# =============================================================================
# DATA STRUCTURES
# =============================================================================
class BoundType:
    def __init__(self, mn=0.0, mx=0.0): self.min, self.max = mn, mx
class HHType:
    def __init__(self, s=0.0, l=0.5, w=1.0): self.strength, self.location, self.width = s, l, w
class HHSpecType:
    def __init__(self): self.hhs = []
class ShapeHHType:
    def __init__(self): self.ndv, self.nfunctions_top, self.nfunctions_bot, self.initial_perturb, self.smooth_seed = 0, 3, 3, 0.1, False
class ShapeBezierType:
    def __init__(self): self.ndv, self.ncp_top, self.ncp_bot, self.initial_perturb = 0, 5, 5, 0.1
class BezierSpecType:
    def __init__(self): self.px, self.py = np.array([]), np.array([])
class ShapeCambThickType:
    def __init__(self): self.ndv, self.thickness, self.thickness_pos, self.camber, self.camber_pos, self.le_radius, self.le_radius_blend, self.initial_perturb = 0, False, False, False, False, False, False, 0.1
class CSTSpecType:
    def __init__(self): self.weights, self.N1, self.N2, self.dv_te = np.array([]), 0.5, 1.0, 0.0
class ShapeCSTType:
    def __init__(self): self.ndv, self.n_weights_top, self.n_weights_bot, self.initial_perturb, self.N1_top, self.N2_top, self.N1_bot, self.N2_bot = 0, 6, 6, 0.1, 0.5, 1.0, 0.5, 1.0

def filename_suffix(fn): return os.path.splitext(fn)[1]


# =============================================================================
# 1. HICKS-HENNE PARAMETERIZATION ENGINE
# =============================================================================
def hh_bounds(): return BoundType(-0.02, 0.02), BoundType(0.01, 0.99), BoundType(0.7, 4.0)


def hh_eval_side(hs, x, y):
    if not hs.hhs: return y.copy()
    sts = np.array([float(h.strength) for h in hs.hhs], np.float64)
    locs = np.array([float(h.location) for h in hs.hhs], np.float64)
    wids = np.array([float(h.width) for h in hs.hhs], np.float64)
    return y.copy() + _hh_eval_tensor(sts, locs, wids, np.array(x, np.float64))


def map_dv_to_hhs(dv):
    sb, lb, wb = hh_bounds()
    return [
        HHType(
            sb.min + dv[i] * (sb.max - sb.min),
            lb.min + dv[i + 1] * (lb.max - lb.min),
            wb.min + dv[i + 2] * (wb.max - wb.min),
        )
        for i in range(0, len(dv), 3)
    ]


def map_hhs_to_dv(hhs):
    sb, lb, wb = hh_bounds()
    return np.array(
        [
            v
            for h in hhs
            for v in [
                (h.strength - sb.min) / (sb.max - sb.min),
                (h.location - lb.min) / (lb.max - lb.min),
                (h.width - wb.min) / (wb.max - wb.min),
            ]
        ]
    )


def nfunctions_to_ndv(nt, nb=None):
    return nt * 3 + (nb * 3 if nb else 0)


def hh_get_dv0(nf):
    sb, lb, wb = hh_bounds()
    return np.array(
        [
            v
            for i in range(1, nf + 1)
            for v in [
                -sb.min / (sb.max - sb.min),
                ((1.0 / (nf + 1)) * i - lb.min) / (lb.max - lb.min),
                (1.0 - wb.min) / (wb.max - wb.min),
            ]
        ]
    )


def hh_get_dv_inital_perturb(ini, nf):
    return np.array(
        [
            v
            for _ in range(nf)
            for v in [min(0.1, ini * 0.25), min(0.5, ini * 1.0), min(0.3, ini * 1.0)]
        ]
    )


def print_hh_spec(ip, s, hs):
    print(
        f"{ip:2d} {s}: "
        + "   ".join(
            f"{h.strength:7.4f} {h.location:7.4f} {h.width:7.4f}" for h in hs.hhs
        )
    )


# =============================================================================
# 2. BEZIER PARAMETERIZATION ENGINE
# =============================================================================
def combinations(n, k):
    return _nCr(int(n), int(k))


def basis_function(n, i, u):
    return _nCr(n, i) * (u**i) * ((1.0 - u) ** (n - i))


def bezier_eval_1D_array(px, u, der=0):
    return _bez_1d_arr(np.array(px, np.float64), np.array(u, np.float64), int(der))


def bezier_eval_1D_scalar(px, u, der=0):
    return _bez_1d_scl(np.array(px, np.float64), float(u), int(der))


def bezier_eval_1D(px, u, der=0):
    return (
        bezier_eval_1D_scalar(px, float(u), der)
        if np.isscalar(u)
        else bezier_eval_1D_array(px, u, der)
    )


def bezier_eval(bez, u, der=0):
    return bezier_eval_1D(bez.px, u, der), bezier_eval_1D(bez.py, u, der)


def bezier_curvature(bez, u):
    return _bez_curv(
        np.array(bez.px, np.float64),
        np.array(bez.py, np.float64),
        float(u),
        bool(np.sum(bez.py) > 0.0),
    )


def bezier_eval_y_on_x(bez, xt, eps=1e-10):
    return _bez_inv(
        np.array(bez.px, np.float64),
        np.array(bez.py, np.float64),
        float(xt),
        float(eps),
    )


def u_distribution_bezier(np_):
    return _u_dist_bez(int(np_))


def ndv_to_ncp(ndv):
    return 3 + (ndv - 2) // 2


def ncp_to_ndv_side(ncp):
    return (ncp - 3) * 2 + 2


def ncp_to_ndv(ncp):
    return (ncp - 3) * 2 + 2


def bezier_cp_bounds(s, ncp, tg):
    bx, by = (
        [BoundType(0.0, 1.0) for _ in range(ncp)],
        [BoundType(0.0, 1.0) for _ in range(ncp)],
    )

    # 1. Leading Edge constraints (P0 and P1)
    bx[0].max = by[0].max = bx[1].max = 0.0
    by[1].min, by[1].max = -0.30, 0.15

    # 2. Trailing Edge Gap Option (Pn) -> Allows up to 10% total blunt TE
    bx[-1].min = 1.0
    by[-1].min, by[-1].max = 0.0, 0.05

    # 3. Middle points: TOTAL FREEDOM RESTORED (Allows deep undercamber!)
    for i in range(2, ncp - 1):
        bx[i].min, bx[i].max = 0.01, 0.95
        by[i].min, by[i].max = -0.5, 0.9

    # 4. Auto-flip orientation for the lower surface mapping
    if s == "Bot":
        for i in range(1, ncp):
            by[i].min, by[i].max = -by[i].max, -by[i].min

    return bx, by


def map_dv_to_bezier(s, dv_in, tg, bez):
    dv, ncp = np.clip(dv_in, 0.0, 1.0), ndv_to_ncp(len(dv_in))
    bx, by = bezier_cp_bounds(s, ncp, tg)
    px, py = np.zeros(ncp), np.zeros(ncp)

    px[0], py[0], px[-1], px[1] = bx[0].min, by[0].min, bx[-1].min, bx[1].min

    # P1 Y-coord
    py[1] = (
        by[1].min + dv[0] * (by[1].max - by[1].min)
        if s == "Top"
        else by[1].max - dv[0] * (by[1].max - by[1].min)
    )

    # Middle points (No artificial floors!)
    for i in range(2, ncp - 1):
        idv = (i - 2) * 2 + 1
        px[i] = bx[i].min + dv[idv] * (bx[i].max - bx[i].min)
        py[i] = (
            by[i].min + dv[idv + 1] * (by[i].max - by[i].min)
            if s == "Top"
            else by[i].max - dv[idv + 1] * (by[i].max - by[i].min)
        )

    # TRAILING EDGE Y-COORD (The optimizer option)
    idv_te = len(dv_in) - 1
    py[-1] = (
        by[-1].min + dv[idv_te] * (by[-1].max - by[-1].min)
        if s == "Top"
        else by[-1].max - dv[idv_te] * (by[-1].max - by[-1].min)
    )

    # Mild Anti-fishtail: Just prevents the curve from mathematically looping backward
    if s == "Top" and py[-2] < py[-1]:
        py[-2] = py[-1] + 0.001
    if s == "Bot" and py[-2] > py[-1]:
        py[-2] = py[-1] - 0.001

    bez.px, bez.py = np.round(px, 10), np.round(py, 10)


def bezier_get_dv0(s, bez):
    ncp = len(bez.px)
    dv = np.zeros(ncp_to_ndv_side(ncp))
    bx, by = bezier_cp_bounds(s, ncp, 0.0)

    # Extract TE variable first
    idv_te = len(dv) - 1
    dv[idv_te] = (
        (bez.py[-1] - by[-1].min) / (by[-1].max - by[-1].min)
        if s == "Top"
        else (by[-1].max - bez.py[-1]) / (by[-1].max - by[-1].min)
    )

    dv[0] = (
        (bez.py[1] - by[1].min) / (by[1].max - by[1].min)
        if s == "Top"
        else (by[1].max - bez.py[1]) / (by[1].max - by[1].min)
    )

    for i in range(2, ncp - 1):
        idv = (i - 2) * 2 + 1
        dv[idv] = (bez.px[i] - bx[i].min) / (bx[i].max - bx[i].min)
        dv[idv + 1] = (
            (bez.py[i] - by[i].min) / (by[i].max - by[i].min)
            if s == "Top"
            else (by[i].max - bez.py[i]) / (by[i].max - by[i].min)
        )

    return np.clip(dv, 0.0, 1.0)


def bezier_get_dv_inital_perturb(ini, bez):
    ncp = len(bez.px)
    dv = np.zeros(ncp_to_ndv_side(ncp))
    dv[0] = min(0.05, ini * 0.1)
    for i in range(2, ncp - 1):
        idv = (i - 2) * 2 + 1
        dv[idv], dv[idv + 1] = min(0.5, ini * 0.7), min(0.1, ini * 0.04)
    dv[-1] = min(0.1, ini * 0.2)
    return dv


def bezier_create_airfoil(tb, bb, np_):
    # Mathematically force symmetric control points at the TE
    avg_te = (abs(tb.py[-1]) + abs(bb.py[-1])) / 2.0
    tb.py[-1] = avg_te
    bb.py[-1] = -avg_te

    # Mild anti-fishtail protection
    if tb.py[-2] < tb.py[-1]:
        tb.py[-2] = tb.py[-1] + 0.001
    if bb.py[-2] > bb.py[-1]:
        bb.py[-2] = bb.py[-1] - 0.001

    n_bot, n_top = (np_ + 1) // 2, (np_ + 1) - (np_ + 1) // 2
    xt, yt = bezier_eval(tb, _u_dist_bez(n_top))
    xb, yb = bezier_eval(bb, _u_dist_bez(n_bot))

    # =======================================================
    # ABSOLUTE NORMALIZATION LOCKS
    # =======================================================
    # 1. Force exact (0,0) at the Leading Edge
    xt[0], yt[0] = 0.0, 0.0
    xb[0], yb[0] = 0.0, 0.0

    # 2. Force exact X=1.0 at the Trailing Edge
    xt[-1], xb[-1] = 1.0, 1.0

    # 3. Force perfect Y-axis symmetry at the Trailing Edge
    avg_eval_te = (abs(yt[-1]) + abs(yb[-1])) / 2.0
    yt[-1] = avg_eval_te
    yb[-1] = -avg_eval_te
    # =======================================================

    return np.concatenate((xt[::-1], xb[1:])), np.concatenate((yt[::-1], yb[1:]))


def bezier_round_decimals(bez):
    bez.px, bez.py = np.round(bez.px, 10), np.round(bez.py, 10)


def get_initial_bezier(sn, x, y, y_te, ncp, bez):
    px, py, nb = np.zeros(ncp), np.zeros(ncp), ncp - 3
    px[-1], py[-1], dx, xi = 1.0, y_te, 0.35 if nb == 1 else 1.0 / (nb + 1), 0.0
    for i in range(nb):
        xi += dx
        idx = find_closest_index(x, xi)
        px[2 + i], py[2 + i] = x[idx], y[idx]
    py[1] = (
        min(np.min(y) * 1.8, -0.025)
        if sn == "Bot" and ncp == 3
        else (
            max(np.max(y) * 1.8, 0.025)
            if sn == "Top" and ncp == 3
            else y[find_closest_index(x, px[2] * 0.6)]
        )
    )
    py[1] = min(py[1], -0.025) if sn == "Bot" else max(py[1], 0.025)
    for i in range(2, ncp - 1):
        py[i] *= (
            1.2 if ncp == 6 else (1.3 if ncp == 5 else (1.6 if ncp == 4 else 1.15))
        ) * (1.2 if i == 2 else 1.0)
    bez.px, bez.py = px, py


def bezier_violates_constraints(bez):
    return any(v < 0.0 or v > 1.0 for v in bez.px) or any(
        (bez.px[i - 1] - bez.px[i]) > -0.05 for i in range(2, len(bez.px))
    )


def print_bezier_spec(ip, s, bez):
    print(
        f"{ip:4d} {s}: "
        + "   ".join(f"{x:7.4f} {y:7.4f}" for x, y in zip(bez.px, bez.py))
    )


# =============================================================================
# 3. CAMBER/THICKNESS SCALING PARAMETERIZATION
# =============================================================================
def dv_to_factor(dv, fmin, fmax):
    return _dv_to_fac(float(dv), float(fmin), float(fmax))


def map_dv_to_camb_thick(dv, ss):
    fmt, fxm, fmc, fxmc, flr, lb, i = 1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 0
    if ss.thickness:
        fmt = dv_to_factor(dv[i], 0.02, 5.0)
        i += 1
    if ss.thickness_pos:
        fxm = dv_to_factor(dv[i], 0.1, 1.9)
        i += 1
    if ss.camber:
        fmc = dv_to_factor(dv[i], 0.01, 5.0)
        i += 1
    if ss.camber_pos:
        fxmc = dv_to_factor(dv[i], 0.1, 1.9)
        i += 1
    if ss.le_radius:
        flr = dv_to_factor(dv[i], 0.3, 3.0)
        i += 1
    if ss.le_radius_blend:
        lb = 0.01 + dv[i] * 0.49
        i += 1
    return fmt, fxm, fmc, fxmc, flr, lb


# =============================================================================
# 4. KULFAN CST PARAMETERIZATION ENGINE
# =============================================================================
def factorial(n):
    return math.factorial(n)


def nCr(n, r):
    return _nCr(int(n), int(r))


def bernstein_poly(x, n, i):
    return _nCr(n, i) * (x**i) * ((1 - x) ** (n - i))


def class_function(x, n1, n2):
    xs = np.clip(x, 0.0, 1.0)
    return (xs**n1) * ((1.0 - xs) ** n2)


def shape_function(x, w):
    return sum(w[i] * bernstein_poly(x, len(w) - 1, i) for i in range(len(w)))


def cst_eval(w, x, n1, n2, dz=0.0):
    return _cst_eval(
        np.array(w, np.float64),
        np.clip(x, 0.0, 1.0).astype(np.float64),
        float(n1),
        float(n2),
        float(dz),
    )


def cst_get_dv0(nw):
    return np.full(nw, 0.5)


def map_dv_to_cst_weights(dv):
    return -0.8 + dv * 1.6


def fit_cst_to_coordinates(xc, yc, nw, n1, n2):
    m = (xc > 0.001) & (xc < 0.999)
    xf, yf = xc[m], yc[m]
    return np.linalg.lstsq(
        _build_cst_A(np.array(xf, np.float64), int(nw)),
        yf / class_function(xf, n1, n2),
        rcond=None,
    )[0]


def cst_create_airfoil(ts, bs, np_):
    xd = (1.0 - np.cos(np.linspace(0, np.pi, (np_ // 2) + 1))) / 2.0
    return np.concatenate((xd[::-1], xd[1:])), np.concatenate(
        (
            cst_eval(ts.weights, xd[::-1], ts.N1, ts.N2),
            cst_eval(bs.weights, xd[1:], bs.N1, bs.N2),
        )
    )


# =============================================================================
# 5. PARAMETRIC FILE I/O SUBSYSTEM
# =============================================================================
def is_bezier_file(fn):
    return filename_suffix(fn).lower() == ".bez"


def read_bezier_file(fn, s, bez):
    with open(fn, "r") as f:
        lns = [l.strip() for l in f if l.strip()]
    nm, px, py, dr = lns[0], [], [], False
    for l in lns[1:]:
        if l in [f"{s} Start", "Bottom Start" if s == "Bot" else ""]:
            dr = True
            continue
        if dr and l in ["Top End", "Bottom End"]:
            break
        if dr:
            try:
                p = l.split()
                px.append(float(p[0]))
                py.append(float(p[1]))
            except:
                pass
    bez.px, bez.py = np.round(px, 10), np.round(py, 10)
    return nm, bez


def load_bezier_airfoil(fn, npt):
    tb, bb = BezierSpecType(), BezierSpecType()
    nm, tb = read_bezier_file(fn, "Top", tb)
    _, bb = read_bezier_file(fn, "Bot", bb)
    x, y = bezier_create_airfoil(tb, bb, npt)
    return nm, x, y, tb, bb


def write_bezier_file(fn, nm, tb, bb):
    with open(fn, "w") as f:
        f.write(f"{nm.strip()}\nTop Start\n")
        [f.write(f"{x:14.10f} {y:14.10f}\n") for x, y in zip(tb.px, tb.py)]
        f.write("Top End\nBottom Start\n")
        [f.write(f"{x:14.10f} {y:14.10f}\n") for x, y in zip(bb.px, bb.py)]
        f.write("Bottom End\n")


def is_hh_file(fn):
    return filename_suffix(fn).lower() == ".hicks"


def write_hh_file(fn, nm, ts, bs, sn, x, y):
    with open(fn, "w") as f:
        f.write(f"{nm.strip()}\n# Top Start\n")
        [
            f.write(f"{h.strength:14.10f} {h.location:14.10f} {h.width:14.10f}\n")
            for h in ts.hhs
        ]
        f.write("# Top End\n# Bottom Start\n")
        [
            f.write(f"{h.strength:14.10f} {h.location:14.10f} {h.width:14.10f}\n")
            for h in bs.hhs
        ]
        f.write(f"# Bottom End\n# Seedfoil Start\n{sn.strip()}\n")
        [f.write(f"{xi:12.7f} {yi:12.7f}\n") for xi, yi in zip(x, y)]


def load_hh_airfoil(fn):
    with open(fn, "r") as f:
        lns = [l.strip() for l in f if l.strip() and not l.strip().startswith("!")]
    ts, bs, xl, yl, st, sn = HHSpecType(), HHSpecType(), [], [], "H", ""
    for l in lns[1:]:
        if l == "Top Start":
            st = "T"
            continue
        elif l in ["Top End", "Bottom End"]:
            st = "H"
            continue
        elif l == "Bottom Start":
            st = "B"
            continue
        elif l == "Seedfoil Start":
            st = "S"
            continue
        if st == "T":
            p = l.split()
            ts.hhs.append(HHType(float(p[0]), float(p[1]), float(p[2]))) if len(
                p
            ) >= 3 else None
        elif st == "B":
            p = l.split()
            bs.hhs.append(HHType(float(p[0]), float(p[1]), float(p[2]))) if len(
                p
            ) >= 3 else None
        elif st == "S":
            sn, st = l, "C"
        elif st == "C":
            p = l.split()
            (xl.append(float(p[0])), yl.append(float(p[1]))) if len(p) >= 2 else None
    return lns[0], ts, bs, sn, np.array(xl), np.array(yl)
