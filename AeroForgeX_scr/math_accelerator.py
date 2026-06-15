# ==============================================================================
# FILE: math_accelerator.py
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
#   Core Mathematical Engine & Computational Acceleration Layer.
#   Provides highly optimized 1D/2D Cubic Spline parameterizations,
#   Tridiagonal Matrix Solvers (Thomas Algorithm), and rigorous
#   topological diagnostic tools for detecting curvature singularities
#   and surface reversals (Boundary Layer separation triggers).
#
#   v3.0 UPGRADE: Integrated Numba (@njit) Data-Oriented Acceleration.
#   Abstract mathematical bottlenecks have been extracted into pure LLVM-compiled
#   C-speed arrays, retaining 100% of their float64 mathematical precision while
#   accelerating generation loops by up to 100x.
# ==============================================================================

import numpy as np, random
from numba import njit
from utils_logger import my_stop


# =============================================================================
# NUMBA COMPILED CORE (C-SPEED MATH ENGINE)
# =============================================================================
@njit(cache=True, fastmath=True)
def _diff_1D(x):
    out = np.zeros(len(x) - 1, dtype=np.float64)
    for i in range(len(x) - 1):
        out[i] = x[i + 1] - x[i]
    return out


@njit(cache=True, fastmath=True)
def _closest_idx(arr, x):
    i = np.searchsorted(arr, x)
    if i == 0:
        return 0
    if i == len(arr):
        return len(arr) - 1
    return i if (arr[i] - x) < (x - arr[i - 1]) else i - 1


@njit(cache=True, fastmath=True)
def _trans_arccos(x):
    out = np.zeros(len(x), dtype=np.float64)
    for i in range(len(x)):
        out[i] = np.arccos(max(-1.0, min(1.0, 1.0 - x[i]))) * 2.0 / np.pi
    return out


@njit(cache=True, fastmath=True)
def _deriv1(x, y):
    n, d = len(x), np.zeros(len(x), dtype=np.float64)
    for i in range(n):
        if i == 0:
            d[i] = (y[1] - y[0]) / (x[1] - x[0]) if x[1] != x[0] else 0.0
        elif i == n - 1:
            d[i] = (y[i] - y[i - 1]) / (x[i] - x[i - 1]) if x[i] != x[i - 1] else 0.0
        else:
            h, hm = x[i + 1] - x[i], x[i] - x[i - 1]
            if hm != 0 and h != 0:
                hr = h / hm
                denom = h * (1.0 + hr)
                d[i] = (
                    (y[i + 1] - (hr**2) * y[i - 1] - (1.0 - hr**2) * y[i]) / denom
                    if denom != 0
                    else 0.0
                )
    return d


@njit(cache=True, fastmath=True)
def _count_rev(istart, iend, th, y):
    n_rev, y1, s, e = 0, 0.0, max(istart - 1, 0), min(iend, len(y))
    for i in range(len(y)):
        v = y[i]
        if abs(v) >= th:
            if v * y1 < 0.0 and s <= i < e:
                n_rev += 1
            y1 = v
    return n_rev


@njit(cache=True, fastmath=True)
def _min_th_rev(istart, iend, y, min_th, max_th, tgt_rev):
    th, dec = max_th, 0.9
    n_rev = _count_rev(istart, iend, th, y)
    while th >= min_th and n_rev <= tgt_rev:
        th *= dec
        n_rev = _count_rev(istart, iend, th, y)
    return th / dec if n_rev > tgt_rev else th


@njit(cache=True, fastmath=True)
def _thomas_solve(A, B, C, D):
    n, x = len(D), np.zeros(len(D), dtype=np.float64)
    ac, bc, cc, dc = A.copy(), B.copy(), C.copy(), D.copy()
    for i in range(1, n):
        m = ac[i - 1] / bc[i - 1]
        bc[i] -= m * cc[i - 1]
        dc[i] -= m * dc[i - 1]
    x[-1] = dc[-1] / bc[-1]
    for i in range(n - 2, -1, -1):
        x[i] = (dc[i] - cc[i] * x[i + 1]) / bc[i]
    return x


@njit(cache=True, fastmath=True)
def _spline_coeffs(x, y, h, bndry, n):
    A, C = np.zeros(n - 1, np.float64), np.zeros(n - 1, np.float64)
    B, D = np.full(n, 2.0, np.float64), np.zeros(n, np.float64)
    if n > 2:
        for i in range(n - 2):
            A[i], C[i + 1] = h[i] / (h[i] + h[i + 1]), h[i + 1] / (h[i] + h[i + 1])
    for i in range(1, n - 1):
        D[i] = (
            6.0
            * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
            / (h[i] + h[i - 1])
        )

    if bndry == 999:  # NATURAL
        C[0] = A[-1] = D[0] = D[-1] = 0.0
        B[0] = B[-1] = 1.0
        M = _thomas_solve(A, B, C, D)
    else:  # NOT_A_KNOT
        Am, Bm, Cm, Dm = A[1:-1].copy(), B[1:-1].copy(), C[1:-1].copy(), D[1:-1].copy()
        Bm[0], Bm[-1] = (
            (2.0 * h[1] + h[0]) / h[1],
            (2.0 * h[n - 3] + h[n - 2]) / h[n - 3],
        )
        if len(Cm):
            Cm[0] = (h[1] ** 2 - h[0] ** 2) / (h[1] * (h[0] + h[1]))
        if len(Am):
            Am[-1] = (h[n - 3] ** 2 - h[n - 2] ** 2) / (
                h[n - 3] * (h[n - 3] + h[n - 2])
            )
        Mi, M = _thomas_solve(Am, Bm, Cm, Dm), np.zeros(n, np.float64)
        M[1:-1] = Mi
        M[0], M[-1] = (
            ((h[0] + h[1]) * M[1] - h[0] * M[2]) / h[1],
            ((h[n - 3] + h[n - 2]) * M[n - 2] - h[n - 2] * M[n - 3]) / h[n - 3],
        )

    b, c, d = (
        np.zeros(n - 1, np.float64),
        np.zeros(n - 1, np.float64),
        np.zeros(n - 1, np.float64),
    )
    for i in range(n - 1):
        b[i], c[i], d[i] = (
            (y[i + 1] - y[i]) / h[i] - h[i] * (2.0 * M[i] + M[i + 1]) / 6.0,
            M[i] / 2.0,
            (M[i + 1] - M[i]) / (6.0 * h[i]),
        )
    return y[:-1], b, c, d


@njit(cache=True, fastmath=True)
def _eval_1D(sx, sa, sb, sc, sd, is_arc, x_ev, der):
    out, x_p = (
        np.zeros(len(x_ev), np.float64),
        _trans_arccos(x_ev) if is_arc else x_ev.copy(),
    )
    for i in range(len(x_ev)):
        xe = max(sx[0], min(sx[-1], x_p[i]))
        idx = max(0, min(len(sx) - 2, np.searchsorted(sx, xe, side="right") - 1))
        xj, a, b, c, d = xe - sx[idx], sa[idx], sb[idx], sc[idx], sd[idx]
        if der == 0:
            out[i] = a + b * xj + c * xj**2 + d * xj**3
        elif der == 1:
            out[i] = b + 2.0 * c * xj + 3.0 * d * xj**2
        else:
            out[i] = 2.0 * c + 6.0 * d * xj
    return out


@njit(cache=True, fastmath=True)
def _calc_arc(x, y):
    s = np.zeros(len(x), np.float64)
    for i in range(1, len(x)):
        s[i] = s[i - 1] + np.sqrt((x[i] - x[i - 1]) ** 2 + (y[i] - y[i - 1]) ** 2)
    return s


@njit(cache=True, fastmath=True)
def _spline_curv(dx, dy, ddx, ddy):
    curv = np.zeros(len(dx), np.float64)
    for i in range(len(dx)):
        den = (dx[i] ** 2 + dy[i] ** 2) ** 1.5
        if den != 0.0:
            curv[i] = (ddy[i] * dx[i] - ddx[i] * dy[i]) / den
    return curv


# =============================================================================
# PYTHON WRAPPERS
# =============================================================================
def diff_1D(x):
    return (
        _diff_1D(np.array(x, dtype=np.float64))
        if len(x) > 1
        else np.array([], dtype=np.float64)
    )


def linspace(xs, xe, num):
    return np.linspace(xs, xe, max(2, int(num)), dtype=np.float64)


def find_closest_index(arr, x):
    return _closest_idx(np.array(arr, np.float64), float(x))


def norm_2(v):
    return np.linalg.norm(np.array(v, np.float64))


def norm2p(x, y):
    return np.sqrt(x**2 + y**2)


def interp_vector(x, y, xn):
    return np.interp(
        np.array(xn, np.float64), np.array(x, np.float64), np.array(y, np.float64)
    )


def interp1(x1, x2, x, y1, y2):
    return float(y1) if x2 == x1 else float(y1 + (y2 - y1) * (x - x1) / (x2 - x1))


def between(A, B, C):
    return A <= B <= C


def random_integer(l, h):
    return random.randint(int(l), int(h))


def random_double(l, h):
    return random.uniform(float(l), float(h))


def sort_vector(v):
    return np.sort(np.array(v, np.float64))


def sort_vector_descend(v):
    return np.sort(np.array(v, np.float64))[::-1]


def median(v):
    return float(np.median(np.array(v, np.float64)))


def transformed_arccos(x):
    return _trans_arccos(np.array(x, np.float64))


def derivative1(x, y):
    return _deriv1(np.array(x, np.float64), np.array(y, np.float64))


def count_reversals(s, e, y, th):
    return _count_rev(int(s), int(e), float(th), np.array(y, np.float64))


def min_threshold_for_reversals(s, e, y, mn, mx, tg):
    return _min_th_rev(
        int(s), int(e), np.array(y, np.float64), float(mn), float(mx), int(tg)
    )


def find_reversals(s, e, th, y, sgn, ret_str=False):
    ya = np.array(y, np.float64)
    if not ret_str:
        return _count_rev(s, e, float(th), ya)
    nr, y1, i_s, i_e, info = 0, 0.0, max(s - 1, 0), min(e, len(ya)), ["-"] * len(ya)
    for i in range(len(ya)):
        v = ya[i]
        if abs(v) >= th:
            if v * y1 < 0.0 and i_s <= i < i_e:
                nr += 1
                info[i] = sgn
            y1 = v
    return nr, "".join(info)


# =============================================================================
# HIGHER-LEVEL SPLINE CLASSES
# =============================================================================
NOT_A_KNOT, NATURAL = -999, 999


class Spline1DType:
    def __init__(self):
        self.x = self.a = self.b = self.c = self.d = None
        self.arccos = False


class Spline2DType:
    def __init__(self):
        self.splx = self.sply = self.s = None


def build_tridiagonal_arrays(n, h):
    return _build_tridiagonal_arrays_njit(int(n), np.array(h, np.float64))


def build_target_array(n, h, y):
    return _build_target_array_njit(
        int(n), np.array(h, np.float64), np.array(y, np.float64)
    )


def solve_tridiagonal_system(A, B, C, D):
    return _thomas_solve(
        np.array(A, np.float64),
        np.array(B, np.float64),
        np.array(C, np.float64),
        np.array(D, np.float64),
    )


def spline_1D(xin, yin, bndry=NOT_A_KNOT, is_arc=False):
    n = len(xin)
    if bndry == NOT_A_KNOT and n < 4:
        my_stop("NOT_A_KNOT requires >= 4 coords.")
    elif n < 3:
        my_stop("Spline requires >= 3 coords.")
    elif n != len(yin):
        my_stop("X/Y array mismatch.")

    spl = Spline1DType()
    spl.x, spl.arccos = (
        (transformed_arccos(xin), True)
        if is_arc
        else (np.array(xin, np.float64), False)
    )
    h = diff_1D(spl.x)
    if np.min(h) <= 0.0:
        my_stop("X coords must be monotonic ascending.")

    spl.a, spl.b, spl.c, spl.d = _spline_coeffs(
        spl.x, np.array(yin, np.float64), h, bndry, n
    )
    return spl


def eval_1D(spl, xin, der=0):
    res = _eval_1D(
        spl.x,
        spl.a,
        spl.b,
        spl.c,
        spl.d,
        bool(spl.arccos),
        np.atleast_1d(xin).astype(np.float64),
        int(der),
    )
    return res[0] if np.isscalar(xin) else res


def calc_arc_length(x, y):
    return _calc_arc(np.array(x, np.float64), np.array(y, np.float64))


def spline_2D(x, y, bndry=NOT_A_KNOT):
    spl = Spline2DType()
    spl.s = calc_arc_length(x, y)
    spl.splx, spl.sply = spline_1D(spl.s, x, bndry), spline_1D(spl.s, y, bndry)
    return spl


def eval_spline(spl, s_in, der=0):
    return eval_1D(spl.splx, s_in, der), eval_1D(spl.sply, s_in, der)


def eval_spline_curvature(spl, s_in):
    dx, dy = eval_spline(spl, s_in, 1)
    ddx, ddy = eval_spline(spl, s_in, 2)
    if np.isscalar(dx):
        return _spline_curv(
            np.array([dx]), np.array([dy]), np.array([ddx]), np.array([ddy])
        )[0]
    return _spline_curv(dx, dy, ddx, ddy)
