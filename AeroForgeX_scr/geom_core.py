# ==============================================================================
# FILE: geom_core.py
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
from numba import njit
from math_accelerator import (
    norm_2,
    norm2p,
    linspace,
    diff_1D,
    spline_2D,
    spline_1D,
    eval_spline,
    eval_1D,
    eval_spline_curvature,
    NATURAL,
    _eval_1D,
    _spline_coeffs,
    _diff_1D,
    _trans_arccos,
)
from shape_functions_param import (
    bezier_eval_y_on_x,
    bezier_create_airfoil,
    write_bezier_file,
    BezierSpecType,
    write_hh_file,
    HHSpecType,
)
from utils_logger import (
    print_warning,
    print_action,
    print_colored,
    stri,
    strf,
    COLOR_NOTE,
    COLOR_NO,
    print_colored_i,
    print_colored_r,
    print_fixed,
    filename_stem,
    path_join,
    my_stop,
    delete_file,
    print_text,
    COLOR_NORMAL,
)

EPSILON, LE_PANEL_FACTOR = 1.0e-10, 0.4


# =============================================================================
# NUMBA COMPILED CORE (C-SPEED MATH ENGINE)
# =============================================================================
@njit(cache=True, fastmath=True)
def _get_panel_dist(nPts, le_b, te_b):
    u = 0.5 * (
        1.0
        - np.cos(np.linspace(max(0.0, min(0.5, 0.1 - le_b * 0.1)), 0.65, nPts) * np.pi)
    )
    du = np.array([u[i + 1] - u[i] for i in range(nPts - 1)], dtype=np.float64)
    ip, du_ip = len(du) - 1, (1.0 - te_b * 0.9) * du[-1]
    while du_ip < du[ip] and ip >= 0:
        du[ip], ip, du_ip = du_ip, ip - 1, du_ip * 1.2
    u_new, curr = np.zeros(nPts, np.float64), 0.0
    for i in range(len(du)):
        curr += du[i]
        u_new[i + 1] = curr
    return u_new / u_new[-1]


@njit(cache=True, fastmath=True)
def _le_eval_spl(sx, sa, sb, sc, sd, cx, sy, s_a, s_b, s_c, s_d, cy, s_arr, xt, yt, ig):
    sl, sm = s_arr[ig], s_arr[-1]
    for _ in range(50):
        sl = max(0.2, min(sl, sm * 0.8))
        xe = np.array([sl], np.float64)
        x, y = (
            _eval_1D(sx, sa, sb, sc, sd, cx, xe, 0)[0],
            _eval_1D(sy, s_a, s_b, s_c, s_d, cy, xe, 0)[0],
        )
        dx, dy = (
            _eval_1D(sx, sa, sb, sc, sd, cx, xe, 1)[0],
            _eval_1D(sy, s_a, s_b, s_c, s_d, cy, xe, 1)[0],
        )
        dot = dx * (x - xt) + dy * (y - yt)
        if abs(dot) < 1e-10:
            break
        ddx, ddy = (
            _eval_1D(sx, sa, sb, sc, sd, cx, xe, 2)[0],
            _eval_1D(sy, s_a, s_b, s_c, s_d, cy, xe, 2)[0],
        )
        ddot = (dx**2 + dy**2) + ((x - xt) * ddx + (y - yt) * ddy)
        if ddot == 0.0:
            break
        sl -= dot / ddot
    return sl


@njit(cache=True, fastmath=True)
def _eval_y_on_x_spl(
    xn, s0, s1, yb, sx, sa, sb, sc, sd, cx, sy, s_a, s_b, s_c, s_d, cy, top
):
    if xn == 0.0:
        return 0.0
    if xn == 1.0:
        return yb
    s = s0 + ((1.0 - xn) if top else xn) * (s1 - s0)
    for _ in range(50):
        s = max(s0, min(s1, s))
        xe = np.array([s], np.float64)
        delta = _eval_1D(sx, sa, sb, sc, sd, cx, xe, 0)[0] - xn
        if abs(delta) < 1e-10:
            break
        dx = _eval_1D(sx, sa, sb, sc, sd, cx, xe, 1)[0]
        if dx == 0.0:
            break
        s -= delta / dx
    return _eval_1D(sy, s_a, s_b, s_c, s_d, cy, np.array([s], np.float64), 0)[0]


@njit(cache=True, fastmath=True)
def _eval_bot_on_xnew(
    xn, s0, s1, yb, sx, sa, sb, sc, sd, cx, sy, s_a, s_b, s_c, s_d, cy
):
    y = np.zeros(len(xn), np.float64)
    for i in range(len(xn)):
        y[i] = _eval_y_on_x_spl(
            xn[i], s0, s1, yb, sx, sa, sb, sc, sd, cx, sy, s_a, s_b, s_c, s_d, cy, False
        )
    return y


@njit(cache=True, fastmath=True)
def _eval_hi_pt(lx, ly):
    im = np.argmax(ly)
    st, en = max(0, im - 5), min(len(ly), im + 6)
    xs, ys = lx[st:en], ly[st:en]
    if len(xs) < 3:
        return lx[im], ly[im]
    a, b, c, d = _spline_coeffs(xs, ys, _diff_1D(xs), 999, len(xs))
    x = lx[im]
    for _ in range(50):
        x = max(xs[0], min(xs[-1], x))
        xe = np.array([x], np.float64)
        dy = _eval_1D(xs, a, b, c, d, False, xe, 1)[0]
        if abs(dy) < 1e-10:
            break
        ddy = _eval_1D(xs, a, b, c, d, False, xe, 2)[0]
        if ddy == 0.0:
            break
        x -= dy / ddy
    return x, _eval_1D(xs, a, b, c, d, False, np.array([x], np.float64), 0)[0]


@njit(cache=True, fastmath=True)
def _mv_xmax(lx, ly, cxm, nxm):
    if cxm == nxm:
        return ly.copy()
    xk, yk = (
        np.array([lx[0], cxm, lx[-1]], np.float64),
        np.array([lx[0], max(0.1, min(0.9, nxm)), lx[-1]], np.float64),
    )
    a, b, c, d = _spline_coeffs(xk, yk, _diff_1D(xk), 999, 3)
    nxl = _eval_1D(xk, a, b, c, d, False, lx, 0)
    nxl[0], nxl[-1] = 0.0, 1.0
    for i in range(1, len(nxl)):
        nxl[i] = max(nxl[i], nxl[i - 1] + 1e-6)
    if nxl[-1] > 1.0:
        nxl *= 1.0 / nxl[-1]
    xt = _trans_arccos(nxl)
    a2, b2, c2, d2 = _spline_coeffs(xt, ly, _diff_1D(xt), -999, len(nxl))
    ny = _eval_1D(xt, a2, b2, c2, d2, True, lx, 0)
    ny[0], ny[-1] = ly[0], ly[-1]
    return ny


@njit(cache=True, fastmath=True)
def _set_le_rad(x, y, fac, xb):
    ny, srf = y.copy(), np.sqrt(abs(max(0.01, min(10.0, fac))))
    for i in range(1, len(x) - 1):
        ny[i] *= 1.0 - (1.0 - srf) * np.exp(-min(x[i] / max(0.001, min(1.0, xb)), 15.0))
    return ny


@njit(cache=True, fastmath=True)
def _norm_math(x, y, xl, yl, tg):
    nx, ny = x - xl, y - yl
    ang = np.arctan2((ny[0] + ny[-1]) / 2.0, (nx[0] + nx[-1]) / 2.0)
    c, s = np.cos(-ang), np.sin(-ang)
    nx, ny = nx * c - ny * s, nx * s + ny * c
    il = np.argmin(nx)
    su, sl = (
        1.0 / nx[0] if nx[0] != 0.0 else 1.0,
        1.0 / nx[-1] if nx[-1] != 0.0 else 1.0,
    )
    nx[: il + 1] *= su
    ny[: il + 1] *= su
    nx[il:] *= sl
    ny[il:] *= sl
    nx[0] = nx[-1] = 1.0
    if abs(ny[0]) < 1e-10:
        ny[0] = ny[-1] = 0.0
    elif abs(ny[0] - tg / 2.0) < 1e-4:
        ny[0], ny[-1] = tg / 2.0, -tg / 2.0
    return nx, ny


@njit(cache=True, fastmath=True)
def _set_tg(tx, ty, bx, by, dg, xb):
    xb = max(0.1, min(1.0, xb))
    nty, nby = ty.copy(), by.copy()
    for i in range(len(tx)):
        nty[i] += (
            0.5 * dg * tx[i] * np.exp(-min((1.0 - tx[i]) * (1.0 / xb - 1.0), 15.0))
        )
    for i in range(len(bx)):
        nby[i] -= (
            0.5 * dg * bx[i] * np.exp(-min((1.0 - bx[i]) * (1.0 / xb - 1.0), 15.0))
        )
    return nty, nby


# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================
class SideAirfoilType:
    def __init__(self, nm=""):
        self.name, self.x, self.y, self.curvature = (
            nm,
            np.array([]),
            np.array([]),
            np.array([]),
        )


class AirfoilType:
    def __init__(self):
        self.name, self.x, self.y, self.symmetrical = (
            "default",
            np.array([]),
            np.array([]),
            False,
        )
        self.top, self.bot, self.spl = (
            SideAirfoilType("Top"),
            SideAirfoilType("Bot"),
            None,
        )
        self.is_bezier_based, self.top_bezier, self.bot_bezier = (
            False,
            BezierSpecType(),
            BezierSpecType(),
        )
        self.is_hh_based, self.hh_seed_name, self.hh_seed_x, self.hh_seed_y = (
            False,
            "",
            np.array([]),
            np.array([]),
        )
        self.top_hh, self.bot_hh = HHSpecType(), HHSpecType()


class PanelOptionsType:
    def __init__(self):
        self.npoint, self.le_bunch, self.te_bunch = 161, 0.86, 0.6


# =============================================================================
# FILE I/O & PARSING ENGINE
# =============================================================================
def airfoil_load(fn):
    if not fn.strip():
        my_stop("No airfoil file defined")
    f, nm, x, y = AirfoilType(), *airfoil_read(fn)
    f.name, f.x, f.y = os.path.basename(nm), x, y
    if not len(x):
        my_stop(f"Airfoil {fn} has no points")
    if np.mean(f.y[: np.argmin(f.x)]) < np.mean(f.y[np.argmin(f.x) :]):
        print_warning("Converting to CCW ordering...")
        f.x, f.y = f.x[::-1], f.y[::-1]
    return f


def airfoil_read(fn):
    if not os.path.exists(fn):
        my_stop(f"Cannot find {fn}")
    with open(fn, "r") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines:
        my_stop(f"Empty file {fn}")
    nm, st = "Airfoil", 0
    try:
        if len(lines[0].split()) == 1:
            float(lines[0].split()[0])
            st = 1
        else:
            float(lines[0].split()[0])
            nm, st = filename_stem(fn), 0
    except:
        nm, st = os.path.basename(lines[0]), 1
    xl, yl = [], []
    for l in lines[st:]:
        try:
            p = l.split()
            xl.append(float(p[0]))
            yl.append(float(p[1]))
        except:
            continue
    return nm, np.array(xl), np.array(yl)


def is_dat_file(fn):
    return fn.lower().endswith(".dat")


def airfoil_write(pfn, f):
    try:
        with open(pfn, "w") as of:
            # Strip extensions properly to prevent Double Extensions (.dat.dat)
            of.write(f"{filename_stem(f.name)}\n")
            for x, y in zip(f.x, f.y):
                of.write(f"{x:12.7f} {y:12.7f}\n")
    except Exception as e:
        my_stop(f"Write err '{pfn}': {e}")


def print_airfoil_write(d, fn, tp, highlight=True):
    print_action(
        f"Writing {'bezier' if tp == 'bez' else ('hicks-henne' if tp == 'hicks' else 'airfoil')}     ",
        fn,
        no_crlf=True,
    )
    print_text(" to " + d) if d else print()


def airfoil_write_with_shapes(foil, output_dir, highlight=True):
    from utils_logger import commons, filename_stem

    # FIXED: Extract stem to prevent double extensions
    cn = filename_stem(foil.name)
    td = (
        output_dir
        if output_dir
        else (
            commons.output_dir_final
            if hasattr(commons, "output_dir_final") and commons.output_dir_final
            else os.path.dirname(foil.name)
        )
    )
    p = os.path.join(td, cn + ".dat") if td else cn + ".dat"
    print_airfoil_write(td, cn + ".dat", "dat", highlight)
    airfoil_write(p, foil)
    if foil.is_bezier_based:
        p = os.path.join(td, cn + ".bez") if td else cn + ".bez"
        print_airfoil_write(td, cn + ".bez", "bez", highlight)
        write_bezier_file(p, cn, foil.top_bezier, foil.bot_bezier)
    elif foil.is_hh_based:
        p = os.path.join(td, cn + ".hicks") if td else cn + ".hicks"
        print_airfoil_write(td, cn + ".hicks", "hicks", highlight)
        write_hh_file(
            p,
            cn,
            foil.top_hh,
            foil.bot_hh,
            foil.hh_seed_name,
            foil.hh_seed_x,
            foil.hh_seed_y,
        )


def airfoil_name_flapped(f, a, bn=None):
    return (
        (bn if bn else filename_stem(f.name))
        + (f"_f{int(a):+d}" if a == int(a) else f"_f{a:+.1f}").strip()
        if a != 0
        else (bn if bn else filename_stem(f.name))
    )


# =============================================================================
# TOPOLOGY & NORMALIZATION MODULE
# =============================================================================
def is_normalized_coord(f):
    return (
        np.isclose(f.x[0], 1.0)
        and np.isclose(f.x[-1], 1.0)
        and np.isclose(f.y[0] + f.y[-1], 0.0, atol=1e-4)
        and np.isclose(f.x[np.argmin(f.x)], 0.0)
        and np.isclose(f.y[np.argmin(f.x)], 0.0)
    )


def split_foil_into_sides(f):
    if not is_normalized_coord(f):
        my_stop("split_foil: Not normalized")
    f.spl, il = spline_2D(f.x, f.y), np.argmin(f.x)
    cv = eval_spline_curvature(f.spl, f.spl.s)
    f.top.name, f.top.x, f.top.y, f.top.curvature = (
        "Top",
        f.x[il::-1],
        f.y[il::-1],
        cv[il::-1],
    )
    f.bot.name = "Bot"
    f.bot.x, f.bot.y, f.bot.curvature = (
        (f.top.x.copy(), -f.top.y.copy(), f.top.curvature.copy())
        if f.symmetrical
        else (f.x[il:], f.y[il:], cv[il:])
    )


def build_from_sides(f):
    f.x, f.y = (
        np.concatenate((f.top.x[::-1], f.bot.x[1:])),
        np.concatenate((f.top.y[::-1], f.bot.y[1:])),
    )
    f.spl = spline_2D(f.x, f.y)
    cv = eval_spline_curvature(f.spl, f.spl.s)
    nt = len(f.top.x)
    f.top.curvature, f.bot.curvature = cv[:nt][::-1], cv[nt - 1 :]


def make_symmetrical(f):
    print_note("Mirroring top half to enforce symmetry.")
    il = np.argmin(f.x)
    if not (np.isclose(f.x[il], 0.0) and np.isclose(f.y[il], 0.0)):
        my_stop("make_symmetrical: Not normalized.")
    f.bot.x, f.bot.y, f.symmetrical = f.top.x.copy(), -f.top.y.copy(), True
    build_from_sides(f)
    if f.is_bezier_based:
        f.bot_bezier.px, f.bot_bezier.py = (
            f.top_bezier.px.copy(),
            -f.top_bezier.py.copy(),
        )


# =============================================================================
# GEOMETRY MATHEMATICS & QUERIES
# =============================================================================
def te_gap(f):
    return np.sqrt((f.x[0] - f.x[-1]) ** 2 + (f.y[0] - f.y[-1]) ** 2)


def le_find(f):
    if f.spl is None or f.spl.s is None:
        f.spl = spline_2D(f.x, f.y)
    return eval_spline(f.spl, le_eval_spline(f), 0)


def le_eval_spline(f):
    if f.spl is None:
        f.spl = spline_2D(f.x, f.y)
    return _le_eval_spl(
        f.spl.splx.x,
        f.spl.splx.a,
        f.spl.splx.b,
        f.spl.splx.c,
        f.spl.splx.d,
        bool(f.spl.splx.arccos),
        f.spl.sply.x,
        f.spl.sply.a,
        f.spl.sply.b,
        f.spl.sply.c,
        f.spl.sply.d,
        bool(f.spl.sply.arccos),
        f.spl.s,
        float((f.x[0] + f.x[-1]) / 2.0),
        float((f.y[0] + f.y[-1]) / 2.0),
        int(np.argmin(f.x)),
    )


def le_check(f):
    xl, yl = le_find(f)
    d = np.sqrt((f.x - xl) ** 2 + (f.y - yl) ** 2)
    i = np.argmin(d)
    return i, d[i] < EPSILON


def is_normalized(f):
    return is_normalized_coord(f) and le_check(f)[1]


def eval_y_on_x_at_side(f, s, xn):
    if not is_normalized_coord(f):
        my_stop("eval_y_on_x: Not normalized.")
    return (
        bezier_eval_y_on_x(f.top_bezier if s == "Top" else f.bot_bezier, xn)
        if f.is_bezier_based
        else eval_y_on_x_at_side_spline(f, s, xn)
    )


def eval_y_on_x_at_side_spline(f, s, xn):
    if f.spl is None or f.spl.s is None:
        my_stop("eval_y_on_x: Spline engine not initialized.")
    sl = f.spl.s[np.argmin(f.x)]
    s0, s1 = (f.spl.s[0], sl) if s == "Top" else (sl, f.spl.s[-1])
    return _eval_y_on_x_spl(
        float(xn),
        float(s0),
        float(s1),
        float(f.y[0] if s == "Top" else f.y[-1]),
        f.spl.splx.x,
        f.spl.splx.a,
        f.spl.splx.b,
        f.spl.splx.c,
        f.spl.splx.d,
        bool(f.spl.splx.arccos),
        f.spl.sply.x,
        f.spl.sply.a,
        f.spl.sply.b,
        f.spl.sply.c,
        f.spl.sply.d,
        bool(f.spl.sply.arccos),
        bool(s == "Top"),
    )


def eval_bot_side_with_xnew(f, xn):
    return _eval_bot_on_xnew(
        np.array(xn, np.float64),
        float(f.spl.s[np.argmin(f.x)]),
        float(f.spl.s[-1]),
        float(f.y[-1]),
        f.spl.splx.x,
        f.spl.splx.a,
        f.spl.splx.b,
        f.spl.splx.c,
        f.spl.splx.d,
        bool(f.spl.splx.arccos),
        f.spl.sply.x,
        f.spl.sply.a,
        f.spl.sply.b,
        f.spl.sply.c,
        f.spl.sply.d,
        bool(f.spl.sply.arccos),
    )


def eval_thickness_camber_lines(f):
    byn, t, c = (
        eval_bot_side_with_xnew(f, f.top.x),
        SideAirfoilType("thickness"),
        SideAirfoilType("camber"),
    )
    t.x, t.y, c.x, c.y = (
        f.top.x.copy(),
        f.top.y - byn,
        f.top.x.copy(),
        (f.top.y + byn) / 2.0,
    )
    return t, c


def eval_highpoint_of_line(l):
    return _eval_hi_pt(l.x, l.y)


def get_geometry(f):
    if not is_normalized_coord(f):
        my_stop("get_geometry: Not normalized.")
    if not len(f.top.x):
        split_foil_into_sides(f)
    t, c = eval_thickness_camber_lines(f)
    xmt, mt = eval_highpoint_of_line(t)
    xmc, mc = eval_highpoint_of_line(c)
    return mt, xmt, mc, xmc


# =============================================================================
# REPANELING & MODIFICATION ENGINE
# =============================================================================
def normalize(f, basic=False):
    xl, yl = (f.x[np.argmin(f.x)], f.y[np.argmin(f.x)]) if basic else le_find(f)
    f.x, f.y = _norm_math(f.x, f.y, float(xl), float(yl), float(te_gap(f)))
    f.spl = spline_2D(f.x, f.y)


def get_panel_distribution(nPts, lb, tb):
    return _get_panel_dist(int(nPts), float(lb), float(tb))


def repanel(fi, po, fo):
    nb = (po.npoint - 1) // 2
    nt = nb if (po.npoint - 1) % 2 == 0 else nb + 1
    fo.name = fi.name
    if fi.spl is None or fi.spl.s is None:
        fi.spl = spline_2D(fi.x, fi.y)
    sl = le_eval_spline(fi)
    st = (
        fi.spl.s[0]
        + np.abs(get_panel_distribution(nt + 1, po.le_bunch, po.te_bunch)[::-1] - 1.0)
        * sl
    )
    sb = sl + get_panel_distribution(nb + 1, po.le_bunch, po.te_bunch) * (
        fi.spl.s[-1] - sl
    )
    fo.x, fo.y = eval_spline(fi.spl, np.concatenate((st, sb[1:])))
    fo.spl = spline_2D(fo.x, fo.y)


def repanel_and_normalize(fi, fo, po=None):
    po, tf = po or PanelOptionsType(), copy.deepcopy(fi)
    if tf.spl is None or tf.spl.s is None:
        tf.spl = spline_2D(tf.x, tf.y)
    repanel(tf, po, fo)
    lf = False
    for _ in range(50):
        normalize(fo)
        tf = copy.deepcopy(fo)
        repanel(tf, po, fo)
        xl, yl = le_find(fo)
        if norm2p(xl, yl) < EPSILON:
            normalize(fo)
            lf = True
            break
    if lf:
        i, is_l = le_check(fo)
        if is_l:
            fo.x[i], fo.y[i] = 0.0, 0.0
    else:
        print_warning("Iterative LE alignment failed to converge.")
    split_foil_into_sides(fo)
    fo.name = filename_stem(fi.name) + "_norm"
    print_action("Repaneling and normalizing. Res: ", f"{po.npoint} Pts")


def repanel_bezier(fi, fo, po):
    fo.name, fo.top_bezier, fo.bot_bezier, fo.is_bezier_based = (
        filename_stem(fi.name) + "_repan",
        fi.top_bezier,
        fi.bot_bezier,
        True,
    )
    print_action("Repaneling Bezier geometry to ", f"{po.npoint} Pts")
    fo.x, fo.y = bezier_create_airfoil(fi.top_bezier, fi.bot_bezier, po.npoint)
    split_foil_into_sides(fo)


def move_xmax_of_line(l, cxm, nxm):
    return _mv_xmax(l.x, l.y, float(cxm), float(nxm))


def set_le_radius(t, fac, xb):
    return _set_le_rad(t.x, t.y, float(fac), float(xb))


def build_from_thickness_camber(t, c, f):
    if not np.allclose(t.x, c.x):
        my_stop("Rebuild Fault: X-mesh mismatch.")
    f.top.x, f.top.y, f.bot.x, f.bot.y = t.x, (t.y / 2.0) + c.y, t.x, (-t.y / 2.0) + c.y
    build_from_sides(f)


def set_geometry_by_scale(f, fmt, fxm, fmc, fxmc, flr, lb):
    t, c = eval_thickness_camber_lines(f)
    if fmt != 1.0 or fxm != 1.0:
        xtc, tc = eval_highpoint_of_line(t)
        t.y *= fmt
        t.y = move_xmax_of_line(
            t, xtc, xtc * fxm if fxm < 1.0 else xtc + (fxm - 1.0) * (1.0 - xtc)
        )
    if fmc != 1.0 or fxmc != 1.0:
        xcc, cc = eval_highpoint_of_line(c)
        c.y *= fmc
        c.y = move_xmax_of_line(
            c, xcc, xcc * fxmc if fxmc < 1.0 else xcc + (fxmc - 1.0) * (1.0 - xcc)
        )
    if flr != 1.0:
        t.y = set_le_radius(t, flr, lb)
    build_from_thickness_camber(t, c, f)


def set_geometry(f, maxt=None, xmaxt=None, maxc=None, xmaxc=None):
    if not is_normalized_coord(f):
        normalize(f, basic=True)
    if not len(f.top.x):
        split_foil_into_sides(f)
    t, c = eval_thickness_camber_lines(f)
    if maxt is not None or xmaxt is not None:
        xtc, tc = eval_highpoint_of_line(t)
        if maxt is not None:
            t.y *= maxt / tc
        if xmaxt is not None:
            t.y = move_xmax_of_line(t, xtc, xmaxt)
    if maxc is not None or xmaxc is not None:
        xcc, cc = eval_highpoint_of_line(c)
        if maxc is not None and cc != 0:
            c.y *= maxc / cc
        if xmaxc is not None:
            c.y = move_xmax_of_line(c, xcc, xmaxc)
    build_from_thickness_camber(t, c, f)


def set_te_gap(f, gn, xb=0.8):
    if not is_normalized_coord(f):
        normalize(f, basic=True)
    if not len(f.top.x):
        split_foil_into_sides(f)
    dg = gn - (f.top.y[-1] - f.bot.y[-1])
    if dg != 0:
        f.top.y, f.bot.y = _set_tg(
            f.top.x, f.top.y, f.bot.x, f.bot.y, float(dg), float(xb)
        )
        build_from_sides(f)


def eval_deviation_at_side(f, s, tx, ty):
    return norm_2(
        np.array([abs(eval_y_on_x_at_side(f, s, x) - y) for x, y in zip(tx, ty)])
    )


def print_coordinate_data(foil1, foil2=None, foil3=None, indent=5):
    fs = [f for f in [foil1, foil2, foil3] if f]
    print_fixed("", indent, False)
    print_fixed("Name", 15, False)
    print_fixed("np", 5, True)
    print_fixed("xLE", 13, True)
    print_fixed("yLE", 11, True)
    print()
    for f in fs:
        xl, yl = le_find(f)
        print_fixed("", indent, False)
        print_fixed(os.path.basename(f.name), 15, False)
        print_colored_i(5, COLOR_NO, len(f.x))
        print_colored_r(13, "{:10.7f}", COLOR_NO, xl)
        print_colored_r(11, "{:10.7f}", COLOR_NO, yl)
        print()
