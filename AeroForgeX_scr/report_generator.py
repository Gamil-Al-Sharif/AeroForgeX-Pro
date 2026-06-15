# ==============================================================================
# FILE: report_generator.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
# DESCRIPTION: Advanced Interactive HTML & Static Matplotlib Report Generator.
# ==============================================================================

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# Import necessary types and utilities from existing modules
from utils_logger import (
    COLOR_GOOD,
    COLOR_BAD,
    COLOR_NORMAL,
    COLOR_WARNING,
    COLOR_NOTE,
    COLOR_ERROR,
    COLOR_PALE,
    COLOR_FEATURE,
    Q_GOOD,
    Q_OK,
    Q_BAD,
    Q_PROBLEM,
    Q_NEW,
    NOT_DEF_D,
    print_colored,
    print_colored_i,
    print_colored_r,
    print_text,
    print_action,
    path_join,
    commons,
)

def get_offline_plotly_js():
    """Returns the full Plotly JS source wrapped in <script> tags for offline HTML rendering."""
    try:
        import plotly.offline
        return f"<script>{plotly.offline.get_plotlyjs()}</script>"
    except ImportError:
        return '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'

# from utils_logger import print_colored, COLOR_WARNING, commons
from geom_core import (
    AirfoilType,
    eval_thickness_camber_lines,
    get_geometry,
    normalize,
    split_foil_into_sides,
)


# Ensure Numpy types are safely encoded for JavaScript injection
class NumpyJSONEncoder(json.JSONEncoder):
    """Safely converts NumPy arrays to standard lists for HTML/JS injection."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return 0.0 if np.isnan(obj) or np.isinf(obj) else float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyJSONEncoder, self).default(obj)


def min_te_angle(thickness_line):
    """Fallback utility for TE angle extraction in the reporter."""
    from obj_utils import min_te_angle as exact_min_te

    return exact_min_te(thickness_line)


# =============================================================================
# MASTER DASHBOARD GENERATOR (OPTIMIZATION MODE)
# =============================================================================


def generate_report(out_dir, prefix, s_f, o_f, hist):
    """
    Generates a static Matplotlib PNG and an advanced offline HTML dashboard.
    Extracts physical coordinates, aerodynamics (CL, CD, CM, Flap), and topology
    (Thickness, Camber, TE Angle) for every generation.
    """
    c_p = os.path.basename(prefix)

    # -------------------------------------------------------------------------
    # 1. Base Generation Data (from the actual seed and final foils)
    # -------------------------------------------------------------------------
    iters = list(range(1, len(hist) + 1)) if hist else []
    imp = [(1.0 - v) * 100.0 for v in hist] if hist else []
    f_imp = imp[-1] if imp else 0.0

    s_mt, s_xmt, s_mc, s_xmc = get_geometry(s_f)
    o_mt, o_xmt, o_mc, o_xmc = get_geometry(o_f)

    s_thick, _ = eval_thickness_camber_lines(s_f)
    o_thick, _ = eval_thickness_camber_lines(o_f)
    s_te = min_te_angle(s_thick)
    o_te = min_te_angle(o_thick)

    # -------------------------------------------------------------------------
    # 2. STATIC MATPLOTLIB PNG (Legacy Fallback)
    # -------------------------------------------------------------------------
    try:
        plt.style.use("ggplot")
        fig = plt.figure(figsize=(15, 10))
        gs = gridspec.GridSpec(2, 2, figure=fig)

        ax = fig.add_subplot(gs[0, :])
        ax.plot(s_f.x, s_f.y, "--", color="gray", label="Seed Airfoil", lw=1.5)
        ax.plot(o_f.x, o_f.y, "-", color="red", label="Optimized", lw=2.0)
        ax.set_title(f"Optimization Topology: {c_p}", fontsize=14)
        ax.axis("equal")
        ax.legend()
        ax.grid(True)

        if hist and len(hist):
            ax_c = fig.add_subplot(gs[1, 0])
            ax_c.plot(iters, imp, "-", color="blue", lw=1.5)
            ax_c.fill_between(iters, imp, color="blue", alpha=0.1)
            ax_c.set(
                title="Convergence Gradient",
                xlabel="Generation",
                ylabel="Improvement (%)",
            )
            pd.DataFrame({"Gen": iters, "Obj": hist, "Imp_Pct": imp}).to_csv(
                os.path.join(out_dir, f"{c_p}_Conv.csv"), index=False
            )
        else:
            fig.add_subplot(gs[1, 0]).text(
                0.5, 0.5, "No convergence data", ha="center", va="center"
            )

        ax_d = fig.add_subplot(gs[1, 1])
        ax_d.axis("off")
        ax_d.text(
            0.1,
            0.5,
            f"Summary\n---\nSeed: {s_f.name}\nFinal: {o_f.name}\nGens: {len(hist)}\nImprov: {f_imp:.2f}%\n",
            fontsize=12,
            family="monospace",
            va="center",
        )
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, f"{c_p}_Report.png"), dpi=150)
        plt.close(fig)
    except Exception:
        plt.close("all")

    # -------------------------------------------------------------------------
    # 3. Build history_data from CSV files (if available)
    # -------------------------------------------------------------------------
    history_data = {}
    max_ops = len(commons.op_points_spec) if hasattr(commons, "op_points_spec") else 999

    try:
        coord_file = os.path.join(commons.design_subdir, "Design_Coordinates.csv")
        op_file = os.path.join(commons.design_subdir, "Design_OpPoints.csv")
        geo_file = os.path.join(commons.design_subdir, "Design_GeoTargets.csv")

        # A: Extract X/Y Coordinates
        if os.path.exists(coord_file):
            with open(coord_file, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            for line in lines[1:]:
                parts = line.split(";")
                if len(parts) < 4:
                    continue
                gen_idx = int(parts[0].strip())
                axis = parts[2].strip().lower()

                if gen_idx not in history_data:
                    history_data[gen_idx] = {
                        "x": [],
                        "y": [],
                        "ops": [],
                        "obj": 1.0,
                        "mt": None,
                        "mc": None,
                        "te": None,
                    }
                if axis == "x":
                    history_data[gen_idx]["x"] = [
                        float(v)
                        for v in parts[3:]
                        if v.strip() and v.strip().lower() != "nan"
                    ]
                elif axis == "y":
                    history_data[gen_idx]["y"] = [
                        float(v)
                        for v in parts[3:]
                        if v.strip() and v.strip().lower() != "nan"
                    ]

        # B: Extract Aerodynamics (CL, CD, CM, Flap)
        if os.path.exists(op_file):
            with open(op_file, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            for line in lines[1:]:
                parts = line.split(";")
                if len(parts) < 5:
                    continue
                gen_idx = int(parts[0].strip())
                if gen_idx not in history_data:
                    history_data[gen_idx] = {
                        "x": [],
                        "y": [],
                        "ops": [],
                        "obj": 1.0,
                        "mt": None,
                        "mc": None,
                        "te": None,
                    }
                if len(history_data[gen_idx]["ops"]) < max_ops:
                    try:
                        alpha = float(parts[2])
                        cl = float(parts[3])
                        cd = float(parts[4])
                        cm = float(parts[5]) if len(parts) > 5 else 0.0
                        flap = float(parts[10]) if len(parts) > 10 else 0.0
                        history_data[gen_idx]["ops"].append(
                            {
                                "cl": cl,
                                "cd": cd,
                                "ld": cl / cd if cd != 0 else 0.0,
                                "a": alpha,
                                "cm": cm,
                                "flap": flap,
                            }
                        )
                    except ValueError:
                        pass

        # C: Extract Soft-Target Geometry (Thickness, Camber)
        if os.path.exists(geo_file):
            with open(geo_file, "r") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            for line in lines[1:]:
                parts = line.split(";")
                if len(parts) < 4:
                    continue
                gen_idx = int(parts[0].strip())
                if gen_idx not in history_data:
                    history_data[gen_idx] = {
                        "x": [],
                        "y": [],
                        "ops": [],
                        "obj": 1.0,
                        "mt": None,
                        "mc": None,
                        "te": None,
                    }
                gtype = parts[2].strip().lower()
                val = float(parts[3].strip())
                if gtype == "thickness":
                    history_data[gen_idx]["mt"] = val * 100.0
                elif gtype == "camber":
                    history_data[gen_idx]["mc"] = val * 100.0

        # D: Backfill missing geometry from coordinates
        for gen_idx, data_dict in history_data.items():
            if (
                data_dict["mt"] is None
                or data_dict["mc"] is None
                or data_dict["te"] is None
            ):
                if (
                    len(data_dict["x"]) > 0
                    and len(data_dict["y"]) > 0
                    and len(data_dict["x"]) == len(data_dict["y"])
                ):
                    temp_foil = AirfoilType()
                    temp_foil.x = np.array(data_dict["x"], dtype=np.float64)
                    temp_foil.y = np.array(data_dict["y"], dtype=np.float64)
                    temp_foil.name = "hist"
                    try:
                        normalize(temp_foil, basic=True)
                        split_foil_into_sides(temp_foil)
                        mt, _, mc, _ = get_geometry(temp_foil)
                        thick, _ = eval_thickness_camber_lines(temp_foil)
                        te_ang = min_te_angle(thick)
                        data_dict["mt"], data_dict["mc"], data_dict["te"] = (
                            mt * 100.0,
                            mc * 100.0,
                            te_ang,
                        )
                    except BaseException:
                        data_dict["mt"] = (
                            np.max(temp_foil.y) - np.min(temp_foil.y)
                        ) * 100.0
                        data_dict["mc"] = (
                            np.max(temp_foil.y) + np.min(temp_foil.y)
                        ) * 50.0
                        data_dict["te"] = 0.0
                else:
                    data_dict["mt"], data_dict["mc"], data_dict["te"] = 0.0, 0.0, 0.0

            if gen_idx > 0:
                safe_index = min(gen_idx - 1, len(hist) - 1)
                data_dict["obj"] = hist[safe_index] if hist else 1.0

    except Exception as e:
        print_colored(COLOR_WARNING, f"Could not fully parse history CSVs: {e}")

    # -------------------------------------------------------------------------
    # 4. FORCE SEED DATA (generation 0) from the actual s_f foil and current state
    # -------------------------------------------------------------------------
    try:
        from obj_evaluator import get_eval_state
        from geom_builder import get_shape_spec
        from solver_neuralfoil import run_op_points

        _evs = get_eval_state()
        if _evs and hasattr(_evs, "op_points_spec") and len(_evs.op_points_spec) > 0:
            # Compute default flap angles for the seed
            seed_flap_angles = np.array(
                [op.flap_angle for op in _evs.op_points_spec], dtype=np.float64
            )

            # Run solver for the seed foil
            local_opts = type(
                "opts", (), {**_evs.xfoil_options.__dict__, "show_details": False}
            )()
            seed_op_results = run_op_points(
                s_f,
                local_opts,
                get_shape_spec().flap_spec,
                seed_flap_angles,
                _evs.op_points_spec,
            )

            # Convert to the format expected by the dashboard
            seed_ops_data = []
            for r, a in zip(seed_op_results, seed_flap_angles):
                seed_ops_data.append(
                    {
                        "cl": r.cl,
                        "cd": r.cd,
                        "ld": r.cl / r.cd if r.cd != 0 else 0.0,
                        "a": r.alpha,
                        "cm": r.cm,
                        "flap": a,
                    }
                )

            # Overwrite generation 0 in history_data
            history_data[0] = {
                "x": s_f.x.tolist(),
                "y": s_f.y.tolist(),
                "ops": seed_ops_data,
                "obj": 1.0,
                "mt": s_mt * 100.0,
                "mc": s_mc * 100.0,
                "te": s_te,
            }
        else:
            # Fallback: create minimal seed data from the foil geometry only
            history_data[0] = {
                "x": s_f.x.tolist(),
                "y": s_f.y.tolist(),
                "ops": [],
                "obj": 1.0,
                "mt": s_mt * 100.0,
                "mc": s_mc * 100.0,
                "te": s_te,
            }
    except Exception as e:
        print_colored(
            COLOR_WARNING,
            f"Could not recompute seed aero data: {e}. Using geometry-only seed.",
        )
        history_data[0] = {
            "x": s_f.x.tolist(),
            "y": s_f.y.tolist(),
            "ops": [],
            "obj": 1.0,
            "mt": s_mt * 100.0,
            "mc": s_mc * 100.0,
            "te": s_te,
        }

    # -------------------------------------------------------------------------
    # 5. Ensure the final generation is present
    # -------------------------------------------------------------------------
    last_g = len(hist)
    if last_g not in history_data:
        history_data[last_g] = {
            "x": o_f.x.tolist(),
            "y": o_f.y.tolist(),
            "ops": history_data.get(last_g - 1, history_data[0]).get("ops", []),
            "obj": hist[-1] if hist else 1.0,
            "mt": o_mt * 100.0,
            "mc": o_mc * 100.0,
            "te": o_te,
        }

    # Convert to JSON‑safe format
    json_history = json.dumps(history_data, cls=NumpyJSONEncoder)

    # -------------------------------------------------------------------------
    # 5. PROFESSIONAL INTERACTIVE HTML DASHBOARD
    # -------------------------------------------------------------------------
    try:
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.5, user-scalable=yes">
    <title>AeroForgeX · __TARGET_NAME__</title>
    __PLOTLY_JS__
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f6f9fc; color: #0b1e33; padding: 28px; display: flex; justify-content: center; }
        .dashboard { max-width: 1600px; width: 100%; display: flex; flex-direction: column; gap: 26px; }

        .header { display: flex; align-items: center; justify-content: space-between; background: #0b1e33; padding: 28px 36px; border-radius: 32px; color: white; flex-wrap: wrap; gap: 20px; box-shadow: 0 20px 35px -8px rgba(0,0,0,0.2); }
        .header-left h1 { font-weight: 700; font-size: 2.3rem; margin-bottom: 6px; }
        .header-left .subtitle { font-size: 0.9rem; opacity: 0.75; }
        .header-right { text-align: right; }
        .target-badge { background: rgba(255,255,255,0.1); padding: 12px 24px; border-radius: 48px; margin-bottom: 12px; }
        .target-badge span { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; font-weight: 500; }
        .target-badge h2 { font-size: 1.3rem; font-weight: 600; color: white; }
        .improvement-stat { background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 10px 24px; border-radius: 40px; font-weight: 600; font-size: 1rem; display: inline-block; }

        .nav-wrapper { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 18px; }
        .tabs { display: flex; gap: 8px; background: white; padding: 8px; border-radius: 48px; box-shadow: 0 8px 20px -6px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }
        .tab-btn { background: transparent; border: none; padding: 12px 24px; font-weight: 600; font-size: 0.95rem; border-radius: 40px; color: #334155; cursor: pointer; transition: all 0.2s; }
        .tab-btn.active { background: #0f172a; color: white; }
        
        .btn { padding: 12px 26px; border-radius: 40px; font-weight: 600; background: white; cursor: pointer; border: 1px solid #d0d9e8; transition: all 0.2s; }
        .btn-primary { background: #0f172a; color: white; border: none; }
        
        .card { background: white; border-radius: 28px; padding: 26px; box-shadow: 0 12px 28px -8px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.05); }
        .card-header { display: flex; justify-content: space-between; margin-bottom: 22px; }
        .card-header h3 { font-weight: 600; font-size: 1.35rem; color: #0b1e33; }

        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 18px; }
        .kpi-item { background: #f8fafc; padding: 22px 18px; border-radius: 24px; border: 1px solid #eef2f6; }
        .kpi-label { font-size: 0.7rem; text-transform: uppercase; color: #5b6c85; font-weight: 700; margin-bottom: 8px; }
        .kpi-value { font-size: 2.2rem; font-weight: 700; color: #0b1e33; }
        .kpi-delta { font-size: 0.85rem; margin-top: 8px; font-weight: 500; }
        .delta-positive { color: #059669; }
        .delta-negative { color: #dc2626; }

        .gen-control { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
        .gen-slider { flex: 1; min-width: 280px; }
        input[type=range] { width: 100%; height: 6px; background: #e0e7ef; border-radius: 10px; -webkit-appearance: none; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 24px; height: 24px; background: #0f172a; border-radius: 50%; cursor: pointer; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .gen-display { font-weight: 700; font-size: 1.1rem; min-width: 150px; }

        .plot-container { width: 100%; height: 380px; }
        .plot-container-sm { height: 200px; }
        .tab-pane { display: none; }
        .tab-pane.active { display: block; }

        .table-wrapper { overflow-x: auto; border-radius: 20px; border: 1px solid #e6ecf3; }
        table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
        th { background: #f8fafd; padding: 16px 20px; text-align: left; font-weight: 600; border-bottom: 2px solid #e0e7ef; }
        td { padding: 14px 20px; border-bottom: 1px solid #eef2f8; font-variant-numeric: tabular-nums; }
        tr:hover td { background: #fafcff; }

        .footer { text-align: center; color: #5b6c85; font-size: 0.85rem; padding-top: 24px; border-top: 1px solid rgba(0,0,0,0.05); }
    </style>
</head>
<body>
<div class="dashboard">

    <div class="header">
        <div class="header-left">
            <h1><i class="fas fa-fan"></i> AeroForgeX</h1>
            <div class="subtitle">Advanced Aerodynamic Optimization · Gamil Abdullah Al‑Sharif</div>
        </div>
        <div class="header-right">
            <div class="target-badge"><span>Optimization Target</span><h2>__TARGET_NAME__</h2></div>
            <div class="improvement-stat"><i class="fas fa-arrow-up"></i> __FINAL_IMP__% overall improvement</div>
        </div>
    </div>

    <div class="nav-wrapper">
        <div class="tabs">
            <button class="tab-btn active" data-tab="overview"><i class="fas fa-chart-pie"></i> Overview</button>
            <button class="tab-btn" data-tab="aero"><i class="fas fa-wind"></i> Aerodynamics</button>
            <button class="tab-btn" data-tab="geo"><i class="fas fa-shapes"></i> Geometry</button>
            <button class="tab-btn" data-tab="conv"><i class="fas fa-chart-line"></i> Convergence</button>
        </div>
        <div>
            <button class="btn btn-primary" onclick="downloadDat()"><i class="fas fa-download"></i> Export .dat</button>
        </div>
    </div>

    <div class="card">
        <div class="gen-control">
            <button class="btn btn-outline" onclick="stepGen(-1)"><i class="fas fa-chevron-left"></i> Prev</button>
            <div class="gen-slider"><input type="range" id="genSlider" min="0" max="100" value="0" oninput="updateDashboard(this.value)"></div>
            <button class="btn btn-outline" onclick="stepGen(1)">Next <i class="fas fa-chevron-right"></i></button>
            <div class="gen-display" id="genDisplay">Seed Airfoil</div>
        </div>
    </div>

    <!-- OVERVIEW TAB -->
    <div id="tab-overview" class="tab-pane active">
        <div class="card">
            <div class="card-header"><h3><i class="fas fa-layer-group"></i> Airfoil Comparison</h3></div>
            <div id="plot_geom_overview" class="plot-container"></div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top:24px;">
            <div class="card">
                <div class="card-header">
                    <h3 style="margin-bottom:0px; font-weight:600; font-size:1.2rem;"><i class="fas fa-tachometer-alt"></i> Key Metrics</h3>
                    <div style="display: flex; gap: 8px; align-items: center; background: #f8fafc; padding: 4px 12px; border-radius: 20px; border: 1px solid #e2e8f0;">
                        <button onclick="updateOpPoint(-1)" style="border:none; background:transparent; cursor:pointer; color:#64748b; font-weight:bold;">&larr;</button>
                        <span id="lbl_op_title" style="font-size:0.85rem; font-weight:600; color:#0f172a; min-width:80px; text-align:center;">OP Point 1</span>
                        <button onclick="updateOpPoint(1)" style="border:none; background:transparent; cursor:pointer; color:#64748b; font-weight:bold;">&rarr;</button>
                    </div>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-item"><div class="kpi-label">Thickness (%c)</div><div class="kpi-value" id="kpi_thk">-</div><div class="kpi-delta" id="kpi_thk_delta"></div></div>
                    <div class="kpi-item"><div class="kpi-label">Camber (%c)</div><div class="kpi-value" id="kpi_cam">-</div><div class="kpi-delta" id="kpi_cam_delta"></div></div>
                    <div class="kpi-item"><div class="kpi-label">CL (Primary)</div><div class="kpi-value" style="color:#2563eb;" id="kpi_cl">-</div><div class="kpi-delta" id="kpi_cl_delta"></div></div>
                    <div class="kpi-item"><div class="kpi-label">CD (Primary)</div><div class="kpi-value" style="color:#ef4444;" id="kpi_cd">-</div><div class="kpi-delta" id="kpi_cd_delta"></div></div>
                    <div class="kpi-item"><div class="kpi-label">L/D Ratio</div><div class="kpi-value" style="color:#8b5cf6;" id="kpi_maxLD">-</div><div class="kpi-delta" id="kpi_ld_delta"></div></div>
                </div>
            </div>
            <div class="card">
                <h3 style="margin-bottom:20px; font-weight:600; font-size:1.2rem;"><i class="fas fa-chart-bar"></i> Convergence Snapshot</h3>
                <div id="mini_conv" class="plot-container-sm"></div>
            </div>
        </div>
    </div>

    <!-- AERODYNAMICS TAB -->
    <div id="tab-aero" class="tab-pane">
        <div class="card">
            <div class="card-header"><h3><i class="fas fa-table"></i> Operating Point Performance</h3></div>
            <div class="table-wrapper">
                <table id="opTable">
                    <thead><tr><th>OP</th><th>α (&deg;)</th><th>CL</th><th>CD</th><th>CM</th><th>Flap (&deg;)</th><th>L/D</th><th>Δ CL</th><th>Δ CD</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- GEOMETRY TAB -->
    <div id="tab-geo" class="tab-pane">
        <div class="card">
            <div class="card-header"><h3><i class="fas fa-ruler-combined"></i> Geometric Parameters</h3></div>
            <div class="table-wrapper">
                <table style="width:100%; text-align:left;">
                    <thead><tr><th>Parameter</th><th>Seed Baseline</th><th>Current Shape</th><th>Delta</th></tr></thead>
                    <tbody>
                        <tr><td>Max Thickness</td><td id="geo_seed_thk">-</td><td id="geo_cur_thk">-</td><td id="geo_delta_thk">-</td></tr>
                        <tr><td>Max Camber</td><td id="geo_seed_cam">-</td><td id="geo_cur_cam">-</td><td id="geo_delta_cam">-</td></tr>
                        <tr><td>TE Wedge Angle</td><td id="geo_seed_te">-</td><td id="geo_cur_te">-</td><td id="geo_delta_te">-</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- CONVERGENCE TAB -->
    <div id="tab-conv" class="tab-pane">
        <div class="card">
            <div class="card-header"><h3><i class="fas fa-chart-line"></i> Convergence History</h3></div>
            <div id="plot_conv_full" class="plot-container" style="height:420px;"></div>
        </div>
    </div>

    <div class="footer"><i class="far fa-copyright"></i> AeroForgeX v4.0 · Mechanical Engineer, Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir</div>
</div>

<script>
    const histData = __HISTORY_DATA__;
    const gens = Object.keys(histData).map(Number).sort((a,b)=>a-b);
    let curIdx = gens.length - 1;
    let curGen = gens[curIdx];
    let curOpIdx = 0;

    const slider = document.getElementById('genSlider');
    slider.max = gens.length - 1;
    slider.value = curIdx;

    function getCurrentData() { return histData[curGen]; }
    function getSeedData() { return histData[0]; }

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-'+btn.dataset.tab).classList.add('active');
            updateDashboard(curIdx);
        });
    });

    function updateDashboard(idx) {
        curIdx = parseInt(idx);
        curGen = gens[curIdx];
        slider.value = curIdx;
        document.getElementById('genDisplay').innerText = curGen === 0 ? 'Seed Airfoil' : `Generation ${curGen}`;
        
        const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
        if(activeTab === 'overview') renderOverview();
        else if(activeTab === 'aero') renderAero();
        else if(activeTab === 'geo') renderGeo();
        else if(activeTab === 'conv') renderConv();
    }

    function stepGen(dir) {
        let newIdx = curIdx + dir;
        if(newIdx >= 0 && newIdx < gens.length) updateDashboard(newIdx);
    }

    function updateOpPoint(dir) {
        const ops = getCurrentData().ops;
        if(!ops || ops.length === 0) return;
        curOpIdx = (curOpIdx + dir + ops.length) % ops.length;
        renderOverview(); // Refresh KPIs with new OP point
    }

    function renderOverview() {
        const d = getCurrentData();
        const seed = getSeedData();
        const px = (d.x && d.x.length > 0) ? d.x : seed.x;
        const py = (d.y && d.y.length > 0) ? d.y : seed.y;
        
        Plotly.react('plot_geom_overview', [
            {x: seed.x, y: seed.y, name: 'Seed', line: {color: '#94a3b8', dash: 'dash', width: 2.5}, hoverinfo: 'none'},
            {x: px, y: py, name: curGen===0 ? 'Seed' : `Gen ${curGen}`, line: {color: '#2563eb', width: 3.2}, fill: 'toself', fillcolor: 'rgba(37,99,235,0.08)'}
        ], { 
            xaxis: {title: 'x/c', showgrid: false, zeroline: false}, 
            yaxis: {title: 'y/c', scaleanchor: 'x', scaleratio: 1, zeroline: false},
            margin: {t:10, l:50, r:20, b:40}, plot_bgcolor: 'rgba(0,0,0,0)', paper_bgcolor: 'rgba(0,0,0,0)', 
            showlegend: true, legend: {orientation: 'h', y: 1.1}
        }, {responsive: true});

        const thk = d.mt !== null ? d.mt : 0, cam = d.mc !== null ? d.mc : 0, te = d.te !== null ? d.te : 0;
        const sThk = seed.mt !== null ? seed.mt : 0, sCam = seed.mc !== null ? seed.mc : 0, sTe = seed.te !== null ? seed.te : 0;
        
        document.getElementById('kpi_thk').innerHTML = `${thk.toFixed(2)}%`;
        document.getElementById('kpi_cam').innerHTML = `${cam.toFixed(2)}%`;
        
        const dThk = thk - sThk, dCam = cam - sCam;
        document.getElementById('kpi_thk_delta').innerHTML = `<span class="${dThk>=0?'delta-positive':'delta-negative'}">${dThk>0?'+':''}${dThk.toFixed(2)}%</span> vs seed`;
        document.getElementById('kpi_cam_delta').innerHTML = `<span class="${dCam>=0?'delta-positive':'delta-negative'}">${dCam>0?'+':''}${dCam.toFixed(2)}%</span> vs seed`;

        const ops = d.ops || [];
        const sOps = seed.ops || [];
        document.getElementById('lbl_op_title').innerText = `OP Point ${curOpIdx + 1}/${ops.length || 1}`;
        
        if (ops.length > curOpIdx && sOps.length > curOpIdx) {
            const op = ops[curOpIdx], sOp = sOps[curOpIdx];
            document.getElementById('kpi_cl').innerText = op.cl.toFixed(4);
            document.getElementById('kpi_cd').innerText = op.cd.toFixed(5);
            document.getElementById('kpi_maxLD').innerText = op.ld.toFixed(1);
            
            const dCl = op.cl - sOp.cl, dCd = op.cd - sOp.cd, dLd = op.ld - sOp.ld;
            document.getElementById('kpi_cl_delta').innerHTML = `<span class="${dCl>=0?'delta-positive':'delta-negative'}">${dCl>0?'+':''}${dCl.toFixed(4)}</span> vs seed`;
            document.getElementById('kpi_cd_delta').innerHTML = `<span class="${dCd<=0?'delta-positive':'delta-negative'}">${dCd>0?'+':''}${dCd.toFixed(5)}</span> vs seed`;
            document.getElementById('kpi_ld_delta').innerHTML = `<span class="${dLd>=0?'delta-positive':'delta-negative'}">${dLd>0?'+':''}${dLd.toFixed(1)}</span> vs seed`;
        }

        const impVals = gens.filter(g => g > 0).map(g => (1.0 - histData[g].obj) * 100);
        Plotly.react('mini_conv', [{
            x: gens.filter(g=>g>0), y: impVals, type:'scatter', mode:'lines', 
            line:{color:'#10b981', width:3}, fill:'tozeroy', fillcolor:'rgba(16,185,129,0.1)'
        }], {
            margin:{t:5, l:40, r:10, b:30}, xaxis:{title:'Gen'}, yaxis:{title:'Imp %'}, 
            showlegend:false, plot_bgcolor:'rgba(0,0,0,0)', paper_bgcolor:'rgba(0,0,0,0)'
        }, {responsive:true});
    }

    function renderAero() {
        const d = getCurrentData();
        const seed = getSeedData();
        const ops = d.ops || [];
        const seedOps = seed.ops || [];
        
        const tbody = document.querySelector('#opTable tbody');
        tbody.innerHTML = '';
        
        ops.forEach((op, i) => {
            const sOp = seedOps[i] || {cl:0, cd:0, ld:0, a:0, cm:0, flap:0};
            const dCl = op.cl - sOp.cl;
            const dCd = op.cd - sOp.cd;
            
            const row = `<tr>
                <td><strong>${i+1}</strong></td>
                <td>${op.a.toFixed(2)}&deg;</td>
                <td>${op.cl.toFixed(4)}</td>
                <td>${op.cd.toFixed(5)}</td>
                <td>${op.cm !== undefined ? op.cm.toFixed(4) : '-'}</td>
                <td>${op.flap !== undefined ? op.flap.toFixed(1) : '-'}</td>
                <td><strong>${op.ld.toFixed(1)}</strong></td>
                <td class="${dCl>=0 ? 'delta-positive' : 'delta-negative'}">${dCl>0?'+':''}${dCl.toFixed(4)}</td>
                <td class="${dCd<=0 ? 'delta-positive' : 'delta-negative'}">${dCd>0?'+':''}${dCd.toFixed(5)}</td>
            </tr>`;
            tbody.innerHTML += row;
        });
    }

    function renderGeo() {
        const d = getCurrentData(), s = getSeedData();
        const sThk = s.mt||0, cThk = d.mt||0, sCam = s.mc||0, cCam = d.mc||0, sTe = s.te||0, cTe = d.te||0;
        
        // Use innerHTML to allow degree symbol, and use Unicode degree character directly
        document.getElementById('geo_seed_thk').innerHTML = sThk.toFixed(2) + '%';
        document.getElementById('geo_cur_thk').innerHTML = cThk.toFixed(2) + '%';
        document.getElementById('geo_delta_thk').innerHTML = `<span class="${cThk>=sThk?'delta-positive':'delta-negative'}">${cThk>sThk?'+':''}${(cThk-sThk).toFixed(2)}%</span>`;
        
        document.getElementById('geo_seed_cam').innerHTML = sCam.toFixed(2) + '%';
        document.getElementById('geo_cur_cam').innerHTML = cCam.toFixed(2) + '%';
        document.getElementById('geo_delta_cam').innerHTML = `<span class="${Math.abs(cCam)>=Math.abs(sCam)?'delta-positive':'delta-negative'}">${cCam>sCam?'+':''}${(cCam-sCam).toFixed(2)}%</span>`;
        
        document.getElementById('geo_seed_te').innerHTML = sTe.toFixed(2) + '°';
        document.getElementById('geo_cur_te').innerHTML = cTe.toFixed(2) + '°';
        document.getElementById('geo_delta_te').innerHTML = `<span class="${cTe>=sTe?'delta-positive':'delta-negative'}">${cTe>sTe?'+':''}${(cTe-sTe).toFixed(2)}°</span>`;
    }

    function renderConv() {
        const impVals = gens.filter(g => g > 0).map(g => (1.0 - histData[g].obj) * 100);
        Plotly.react('plot_conv_full', [{
            x: gens.filter(g=>g>0), y: impVals, type: 'scatter', mode: 'lines+markers',
            line: {color: '#2563eb', width: 3.5}, marker: {size: 9, color: '#0f172a', line: {width: 2, color: 'white'}},
        }], {
            xaxis:{title:'Generation', gridcolor: '#eef2f6'}, 
            yaxis:{title:'Improvement (%)', gridcolor: '#eef2f6'}, 
            margin:{t:20}, plot_bgcolor:'rgba(0,0,0,0)', paper_bgcolor:'rgba(0,0,0,0)'
        }, {responsive:true});
    }

    function downloadDat() {
        const d = getCurrentData();
        const px = (d.x && d.x.length > 0) ? d.x : histData[0].x;
        const py = (d.y && d.y.length > 0) ? d.y : histData[0].y;
        let content = `AeroForgeX_${curGen === 0 ? 'Seed' : 'Gen_' + curGen}\\n`;
        for(let i=0; i < px.length; i++) content += `${px[i].toFixed(7)}  ${py[i].toFixed(7)}\\n`;
        const blob = new Blob([content], {type:'text/plain'});
        const a = document.createElement('a'); 
        a.href = URL.createObjectURL(blob);
        a.download = `AeroForgeX_Gen_${curGen}.dat`; 
        a.click();
    }

    updateDashboard(curIdx);
    document.getElementById('plot_conv_full').on('plotly_click', data => {
        if(data.points.length){
            const gen = data.points[0].x;
            const idx = gens.indexOf(gen);
            if(idx !== -1) updateDashboard(idx);
        }
    });
    window.addEventListener('resize', () => { 
        Plotly.Plots.resize('plot_geom_overview'); 
        Plotly.Plots.resize('plot_conv_full'); 
        Plotly.Plots.resize('mini_conv');
    });
</script>
</body>
</html>"""
        html = (
            html.replace("__TARGET_NAME__", c_p)
            .replace("__FINAL_IMP__", f"{f_imp:.2f}")
            .replace("__HISTORY_DATA__", json_history)
            .replace("__PLOTLY_JS__", get_offline_plotly_js())
        )
        with open(
            os.path.join(out_dir, f"{c_p}_Interactive_Report.html"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(html)
    except Exception as e:
        print_colored(COLOR_WARNING, f"Failed to generate HTML report: {e}")


# =============================================================================
# WORKER DASHBOARD GENERATORS (unchanged)
# =============================================================================


# =============================================================================
# WORKER DASHBOARD GENERATORS (VERSION 1 IMPLEMENTATIONS)
# =============================================================================
def generate_worker_topology_report(output_dir, prefix, foil, curv_constraints):
    """
    Generates a professional Plotly.js HTML dashboard for the '-w check' tool.
    Visualizes the physical airfoil and its exact 2nd-Derivative Curvature gradient.
    """
    try:
        clean_prefix = os.path.basename(prefix)

        mt, xmt, mc, xmc = get_geometry(foil)
        thick, camb = eval_thickness_camber_lines(foil)
        te_ang = min_te_angle(thick)

        top_k = foil.top.curvature if foil.top.curvature is not None else []
        bot_k = foil.bot.curvature if foil.bot.curvature is not None else []

        data = {
            "x": foil.x.tolist(),
            "y": foil.y.tolist(),
            "top_x": foil.top.x.tolist(),
            "top_k": top_k.tolist() if isinstance(top_k, np.ndarray) else top_k,
            "bot_x": foil.bot.x.tolist(),
            "bot_k": bot_k.tolist() if isinstance(bot_k, np.ndarray) else bot_k,
            "mt": mt * 100.0,
            "xmt": xmt * 100.0,
            "mc": mc * 100.0,
            "xmc": xmc * 100.0,
            "te_ang": te_ang,
        }
        json_data = json.dumps(data, cls=NumpyJSONEncoder)

        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AeroForgeX Topology · __TARGET_NAME__</title>
    __PLOTLY_JS__
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f5f7fb; padding: 30px; display: flex; justify-content: center; }
        .dashboard { max-width: 1400px; width: 100%; display: flex; flex-direction: column; gap: 20px; }
        .header { background: #0f172a; padding: 20px 30px; border-radius: 16px; color: white; display: flex; justify-content: space-between; }
        .header h1 { font-size: 1.8rem; margin: 0; }
        .card { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 20px; }
        .kpi { background: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; }
        .kpi-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; font-weight: 600; }
        .kpi-val { font-size: 1.8rem; font-weight: 700; color: #0f172a; }
        .plot-box { height: 400px; }
    </style>
</head>
<body>
<div class="dashboard">
    <div class="header">
        <div><h1>AeroForgeX Topology Diagnostics</h1><div style="opacity:0.8">__TARGET_NAME__</div></div>
    </div>
    <div class="kpi-grid">
        <div class="kpi"><div class="kpi-label">Thickness</div><div class="kpi-val" id="kpi-mt">-</div></div>
        <div class="kpi"><div class="kpi-label">Thick Pos</div><div class="kpi-val" id="kpi-xmt">-</div></div>
        <div class="kpi"><div class="kpi-label">Camber</div><div class="kpi-val" id="kpi-mc">-</div></div>
        <div class="kpi"><div class="kpi-label">Camb Pos</div><div class="kpi-val" id="kpi-xmc">-</div></div>
        <div class="kpi"><div class="kpi-label">TE Wedge</div><div class="kpi-val" id="kpi-te">-</div></div>
    </div>
    <div class="card">
        <h3 style="margin-bottom:10px; color:#0f172a;">Physical Geometry</h3>
        <div id="plot-airfoil" class="plot-box" style="height:250px;"></div>
    </div>
    <div class="card">
        <h3 style="margin-bottom:10px; color:#0f172a;">2nd-Derivative Mathematical Curvature</h3>
        <div id="plot-curv" class="plot-box"></div>
    </div>
</div>
<script>
    const d = __FOIL_DATA__;
    document.getElementById('kpi-mt').innerText = d.mt.toFixed(2) + '%';
    document.getElementById('kpi-xmt').innerText = d.xmt.toFixed(1) + '%';
    document.getElementById('kpi-mc').innerText = d.mc.toFixed(2) + '%';
    document.getElementById('kpi-xmc').innerText = d.xmc.toFixed(1) + '%';
    document.getElementById('kpi-te').innerText = d.te_ang.toFixed(2) + '°';

    Plotly.newPlot('plot-airfoil', [{x: d.x, y: d.y, fill: 'toself', fillcolor: 'rgba(37,99,235,0.1)', line: {color: '#2563eb', width: 2}}], 
        {margin: {t:10, b:40, l:40, r:20}, yaxis: {scaleanchor: 'x', scaleratio: 1}});
        
    Plotly.newPlot('plot-curv', [
        {x: d.top_x, y: d.top_k, name: 'Upper Surface', line: {color: '#ef4444', width: 2}},
        {x: d.bot_x, y: d.bot_k, name: 'Lower Surface', line: {color: '#3b82f6', width: 2}}
    ], {margin: {t:10, b:40, l:50, r:20}, xaxis: {title: 'x/c'}, yaxis: {title: 'Curvature (k)'}});
</script>
</body>
</html>"""
        html = html_template.replace("__TARGET_NAME__", clean_prefix).replace(
            "__FOIL_DATA__", json_data
        ).replace("__PLOTLY_JS__", get_offline_plotly_js())
        with open(
            os.path.join(output_dir, f"{clean_prefix}_Topology_Report.html"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(html)
    except Exception as e:
        print_colored(COLOR_WARNING, f"Failed to generate Topology Dashboard: {e}")


def generate_worker_polar_dashboard(output_dir, prefix, csv_filepath):
    """
    Generates a highly professional Plotly.js HTML dashboard for the '-w polar-csv' tool.
    """
    try:
        clean_prefix = os.path.basename(prefix)
        df = pd.read_csv(csv_filepath, sep=";")
        df.columns = [c.strip() for c in df.columns]

        traces = []
        summary_stats = []

        if all(col in df.columns for col in ["Re", "Mach", "Flap"]):
            grouped = df.groupby(["Re", "Mach", "Flap"])
            for name, group in grouped:
                re_val, mach_val, flap_val = name
                re_k = f"{int(re_val / 1000)}k" if re_val >= 1000 else str(re_val)

                trace_name = f"Re {re_k}"
                if mach_val > 0.0:
                    trace_name += f" | M {mach_val}"
                if flap_val != 0.0:
                    trace_name += f" | Flap {flap_val}°"

                alpha = group["alpha"].tolist()
                cl = group["CL"].tolist()
                cd = group["CD"].tolist()
                cm = group["CM"].tolist()
                xtrt = (
                    group["XtrT"].tolist()
                    if "XtrT" in df.columns
                    else [1.0] * len(alpha)
                )
                xtrb = (
                    group["XtrB"].tolist()
                    if "XtrB" in df.columns
                    else [1.0] * len(alpha)
                )

                ld = [l / d if d > 1e-10 else 0.0 for l, d in zip(cl, cd)]

                max_cl = max(cl) if cl else 0.0
                min_cd = min([d for d in cd if d > 0.0], default=0.0)
                max_ld = max(ld) if ld else 0.0

                summary_stats.append(
                    {
                        "name": trace_name,
                        "re": re_val,
                        "mach": mach_val,
                        "flap": flap_val,
                        "max_cl": max_cl,
                        "min_cd": min_cd,
                        "max_ld": max_ld,
                    }
                )

                traces.append(
                    {
                        "name": trace_name,
                        "alpha": alpha,
                        "cl": cl,
                        "cd": cd,
                        "cm": cm,
                        "ld": ld,
                        "xtrt": xtrt,
                        "xtrb": xtrb,
                    }
                )
        else:
            alpha = df["alpha"].tolist()
            cl = df["CL"].tolist()
            cd = df["CD"].tolist()
            ld = [l / d if d > 1e-10 else 0.0 for l, d in zip(cl, cd)]
            traces.append(
                {
                    "name": "Polar Data",
                    "alpha": alpha,
                    "cl": cl,
                    "cd": cd,
                    "cm": df["CM"].tolist(),
                    "ld": ld,
                    "xtrt": [1.0] * len(alpha),
                    "xtrb": [1.0] * len(alpha),
                }
            )
            summary_stats.append(
                {
                    "name": "Polar Data",
                    "re": "-",
                    "mach": "-",
                    "flap": "-",
                    "max_cl": max(cl),
                    "min_cd": min(cd),
                    "max_ld": max(ld),
                }
            )

        json_data = json.dumps(traces, cls=NumpyJSONEncoder)
        json_stats = json.dumps(summary_stats, cls=NumpyJSONEncoder)

        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AeroForgeX Polars · __TARGET_NAME__</title>
    __PLOTLY_JS__
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f1f5f9; color: #0f172a; padding: 30px; display: flex; justify-content: center; }
        .dashboard { max-width: 1600px; width: 100%; display: flex; flex-direction: column; gap: 24px; }
        .header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 24px 32px; border-radius: 20px; color: white; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); }
        .header h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 12px; }
        .header h1 i { color: #3b82f6; }
        .subtitle { color: #94a3b8; font-size: 1rem; }
        .card { background: white; padding: 24px; border-radius: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
        .card-header { font-size: 1.25rem; font-weight: 600; margin-bottom: 16px; color: #1e293b; display: flex; align-items: center; gap: 8px; border-bottom: 2px solid #f1f5f9; padding-bottom: 12px; }
        table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
        th { text-align: left; padding: 12px 16px; background: #f8fafc; color: #475569; font-weight: 600; border-bottom: 2px solid #e2e8f0; }
        td { padding: 12px 16px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-variant-numeric: tabular-nums; }
        tr:hover td { background: #f8fafc; }
        .highlight-val { font-weight: 600; color: #0ea5e9; }
        .plot-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        .plot-box { height: 450px; width: 100%; }
        .plot-box-large { height: 500px; width: 100%; }
        .footer { text-align: center; padding: 20px; color: #64748b; font-size: 0.85rem; }
    </style>
</head>
<body>
<div class="dashboard">
    <div class="header">
        <div>
            <h1><i class="fas fa-chart-line"></i> AeroForgeX Aerodynamic Polars</h1>
            <div class="subtitle">Detailed performance analysis for: <strong style="color:white;">__TARGET_NAME__</strong></div>
        </div>
    </div>
    <div class="card">
        <div class="card-header"><i class="fas fa-list-ul"></i> Performance Summary Matrix</div>
        <div style="overflow-x: auto;">
            <table id="summary-table">
                <thead>
                    <tr>
                        <th>Configuration Profile</th>
                        <th>Reynolds</th>
                        <th>Mach</th>
                        <th>Flap (°)</th>
                        <th>Max CL</th>
                        <th>Min CD</th>
                        <th>Max L/D</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>
    <div class="plot-grid">
        <div class="card">
            <div class="card-header"><i class="fas fa-drafting-compass"></i> Drag Polar (CD vs CL)</div>
            <div id="plot-drag" class="plot-box-large"></div>
        </div>
        <div class="card">
            <div class="card-header"><i class="fas fa-angle-double-up"></i> Lift Curve (CL vs α)</div>
            <div id="plot-lift" class="plot-box-large"></div>
        </div>
    </div>
    <div class="plot-grid">
        <div class="card">
            <div class="card-header"><i class="fas fa-paper-plane"></i> Aerodynamic Efficiency (L/D vs α)</div>
            <div id="plot-glide" class="plot-box"></div>
        </div>
        <div class="card">
            <div class="card-header"><i class="fas fa-sync-alt"></i> Pitching Moment (CM vs α)</div>
            <div id="plot-moment" class="plot-box"></div>
        </div>
    </div>
    <div class="card">
        <div class="card-header"><i class="fas fa-stream"></i> Boundary Layer Transition (Xtr vs α)</div>
        <div id="plot-transition" class="plot-box" style="height: 350px;"></div>
    </div>
    <div class="footer">
        AeroForgeX v4.0 Worker Tool &middot; Generated by <b>Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir.py</b>
    </div>
</div>
<script>
    const traces = __POLAR_DATA__;
    const stats = __SUMMARY_STATS__;
    
    const tbody = document.querySelector('#summary-table tbody');
    stats.forEach(s => {
        let tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${s.name}</strong></td>
            <td>${s.re !== '-' ? s.re.toExponential(2) : '-'}</td>
            <td>${s.mach}</td>
            <td>${s.flap}</td>
            <td class="highlight-val">${s.max_cl.toFixed(4)}</td>
            <td class="highlight-val">${s.min_cd.toFixed(5)}</td>
            <td class="highlight-val">${s.max_ld.toFixed(1)}</td>
        `;
        tbody.appendChild(tr);
    });

    const dragData = [], liftData = [], glideData = [], momentData = [], transData = [];
    const colors = ['#2563eb', '#dc2626', '#10b981', '#f59e0b', '#8b5cf6', '#6366f1', '#ec4899', '#14b8a6'];

    traces.forEach((t, i) => {
        const color = colors[i % colors.length];
        const hoverTmpl = `<b>${t.name}</b><br>α: %{customdata[0]:.2f}°<br>CL: %{customdata[1]:.4f}<br>CD: %{customdata[2]:.5f}<extra></extra>`;
        const customData = t.alpha.map((a, idx) => [a, t.cl[idx], t.cd[idx]]);

        dragData.push({x: t.cd, y: t.cl, name: t.name, mode: 'lines+markers', line: {color: color, width: 2}, marker: {size: 4}, customdata: customData, hovertemplate: hoverTmpl});
        liftData.push({x: t.alpha, y: t.cl, name: t.name, mode: 'lines+markers', line: {color: color, width: 2}, marker: {size: 4}, customdata: customData, hovertemplate: hoverTmpl});
        glideData.push({x: t.alpha, y: t.ld, name: t.name, mode: 'lines+markers', line: {color: color, width: 2}, marker: {size: 4}, customdata: customData, hovertemplate: hoverTmpl});
        momentData.push({x: t.alpha, y: t.cm, name: t.name, mode: 'lines+markers', line: {color: color, width: 2}, marker: {size: 4}, customdata: customData, hovertemplate: hoverTmpl});
        transData.push({x: t.alpha, y: t.xtrt, name: `${t.name} (Top)`, mode: 'lines+markers', line: {color: color, width: 2}, marker: {symbol: 'circle', size: 5}, hovertemplate: `<b>${t.name} (Top)</b><br>α: %{x:.2f}°<br>Xtr: %{y:.3f}c<extra></extra>`});
        transData.push({x: t.alpha, y: t.xtrb, name: `${t.name} (Bot)`, mode: 'lines+markers', line: {color: color, width: 2, dash: 'dot'}, marker: {symbol: 'diamond', size: 5}, hovertemplate: `<b>${t.name} (Bot)</b><br>α: %{x:.2f}°<br>Xtr: %{y:.3f}c<extra></extra>`});
    });

    const layoutBase = {
        margin: {t:20, b:50, l:60, r:20}, hovermode: 'closest',
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: { gridcolor: '#f1f5f9', zerolinecolor: '#e2e8f0' },
        yaxis: { gridcolor: '#f1f5f9', zerolinecolor: '#e2e8f0' },
        legend: { orientation: "h", yanchor: "bottom", y: 1.02, xanchor: "right", x: 1 }
    };

    Plotly.newPlot('plot-drag', dragData, {...layoutBase, xaxis: {title: 'Drag Coefficient (CD)'}, yaxis: {title: 'Lift Coefficient (CL)'}}, {responsive: true});
    Plotly.newPlot('plot-lift', liftData, {...layoutBase, xaxis: {title: 'Angle of Attack (α)', ticksuffix: '°'}, yaxis: {title: 'Lift Coefficient (CL)'}}, {responsive: true});
    Plotly.newPlot('plot-glide', glideData, {...layoutBase, xaxis: {title: 'Angle of Attack (α)', ticksuffix: '°'}, yaxis: {title: 'Glide Ratio (L/D)'}}, {responsive: true});
    Plotly.newPlot('plot-moment', momentData, {...layoutBase, xaxis: {title: 'Angle of Attack (α)', ticksuffix: '°'}, yaxis: {title: 'Pitching Moment (CM)'}}, {responsive: true});
    Plotly.newPlot('plot-transition', transData, {...layoutBase, xaxis: {title: 'Angle of Attack (α)', ticksuffix: '°'}, yaxis: {title: 'Transition Location (x/c)', range: [0, 1.05]}, legend: { orientation: "v", yanchor: "top", y: 1, xanchor: "left", x: 1.02 }}, {responsive: true});
</script>
</body>
</html>"""
        html = (
            html_template.replace("__TARGET_NAME__", clean_prefix)
            .replace("__POLAR_DATA__", json_data)
            .replace("__SUMMARY_STATS__", json_stats)
            .replace("__PLOTLY_JS__", get_offline_plotly_js())
        )
        with open(
            os.path.join(output_dir, f"{clean_prefix}_Polar_Dashboard.html"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(html)
    except Exception as e:
        print_colored(COLOR_WARNING, f"Failed to generate Polar Dashboard: {e}")


def generate_worker_diagnostics(foil, output_prefix):
    """
    Worker Action: Generates a professional Dual PDF & HTML diagnostics report for a specific airfoil.
    """
    from utils_logger import print_action, print_colored, COLOR_GOOD, COLOR_WARNING
    print_action(f"Generating Dual HTML/PDF Diagnostics Report for {foil.name}")
    import numpy as np
    import matplotlib.pyplot as plt
    import copy
    import json
    from geom_core import (
        eval_thickness_camber_lines,
        split_foil_into_sides,
        normalize,
        is_normalized_coord,
    )
    from report_generator import get_offline_plotly_js

    foil_work = copy.deepcopy(foil)
    if not is_normalized_coord(foil_work):
        normalize(foil_work, basic=True)
    if not len(foil_work.top.x):
        split_foil_into_sides(foil_work)

    thick, camb = eval_thickness_camber_lines(foil_work)
    
    # Calculate Curvature safely
    dx, dy = np.gradient(foil_work.x), np.gradient(foil_work.y)
    ddx, ddy = np.gradient(dx), np.gradient(dy)
    curv = (dx * ddy - dy * ddx) / ((dx**2 + dy**2)**1.5 + 1e-8)

    # 1. PDF GENERATION
    try:
        fig = plt.figure(figsize=(10, 8))
        gs = plt.GridSpec(3, 1, height_ratios=[2, 1, 1])
        
        ax1 = fig.add_subplot(gs[0])
        ax1.plot(foil_work.x, foil_work.y, 'b-', label='Geometry', linewidth=1.5)
        ax1.plot(camb.x, camb.y, 'r--', label='Camber', linewidth=1.0)
        ax1.axis('equal')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_title(f"Geometry: {foil.name}")

        ax2 = fig.add_subplot(gs[1])
        ax2.plot(thick.x, thick.y, 'g-', linewidth=1.5)
        ax2.grid(True, alpha=0.3)
        ax2.set_title("Thickness Distribution")
        
        ax3 = fig.add_subplot(gs[2])
        ax3.plot(foil_work.x, curv, 'k-', linewidth=0.8)
        ax3.set_ylim(-150, 150)
        ax3.grid(True, alpha=0.3)
        ax3.set_title("Surface Curvature Spectrum")
        
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_diagnostics.pdf")
        plt.close(fig)
        print_colored(COLOR_GOOD, f"  -> Created PDF: {output_prefix}_diagnostics.pdf")
    except Exception as e:
        print_colored(COLOR_WARNING, f"Failed to generate PDF: {e}")

    # 2. HTML GENERATION
    try:
        # --- [FIX] Sanitize NumPy arrays to prevent JavaScript 'nan' ReferenceErrors ---
        x_safe = json.dumps(np.nan_to_num(foil_work.x, nan=0.0, posinf=0.0, neginf=0.0).tolist())
        y_safe = json.dumps(np.nan_to_num(foil_work.y, nan=0.0, posinf=0.0, neginf=0.0).tolist())
        cx_safe = json.dumps(np.nan_to_num(camb.x, nan=0.0, posinf=0.0, neginf=0.0).tolist())
        cy_safe = json.dumps(np.nan_to_num(camb.y, nan=0.0, posinf=0.0, neginf=0.0).tolist())
        tx_safe = json.dumps(np.nan_to_num(thick.x, nan=0.0, posinf=0.0, neginf=0.0).tolist())
        ty_safe = json.dumps(np.nan_to_num(thick.y, nan=0.0, posinf=0.0, neginf=0.0).tolist())
        k_safe = json.dumps(np.nan_to_num(curv, nan=0.0, posinf=0.0, neginf=0.0).tolist())

        html = f"""<!DOCTYPE html><html><head><title>Diagnostics: {foil.name}</title>
{get_offline_plotly_js()}
<style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; margin:20px; background:#f8fafc;}} .card{{background:white; padding:20px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1); margin-bottom:20px;}}</style>
</head><body>
<div class="card"><h2 style="color:#0f172a; margin-bottom:0;">Aerodynamic Surface Diagnostics</h2><p style="color:#64748b; margin-top:5px;">{foil.name}</p></div>
<div class="card"><div id="plot_geo" style="width:100%;height:400px;"></div></div>
<div class="card"><div id="plot_thick" style="width:100%;height:300px;"></div></div>
<div class="card"><div id="plot_curv" style="width:100%;height:300px;"></div></div>
<script>
var geo = [
  {{x: {x_safe}, y: {y_safe}, name: 'Surface', mode: 'lines', line: {{color: '#2563eb', width: 2}} }},
  {{x: {cx_safe}, y: {cy_safe}, name: 'Camber', mode: 'lines', line: {{dash: 'dot', color: '#dc2626', width: 2}} }}
];
Plotly.newPlot('plot_geo', geo, {{title: 'Profile Geometry', yaxis: {{scaleanchor: 'x'}} }});

var thick = [{{x: {tx_safe}, y: {ty_safe}, name: 'Thickness', mode: 'lines', line: {{color: '#16a34a', width: 2}}}}];
Plotly.newPlot('plot_thick', thick, {{title: 'Thickness Distribution'}});

var curv = [{{x: {x_safe}, y: {k_safe}, name: 'Curvature', mode: 'lines', line: {{color: '#475569', width: 1.5}}}}];
Plotly.newPlot('plot_curv', curv, {{title: 'Curvature Spectrum (2nd Derivative)', yaxis: {{range: [-150, 150]}} }});
</script></body></html>"""
        
        # Write safely using UTF-8 to prevent Windows charmap errors
        with open(f"{output_prefix}_diagnostics.html", "w", encoding="utf-8") as f:
            f.write(html)
        print_colored(COLOR_GOOD, f"  -> Created HTML: {output_prefix}_diagnostics.html")
    except Exception as e:
        print_colored(COLOR_WARNING, f"Failed to generate HTML: {e}")