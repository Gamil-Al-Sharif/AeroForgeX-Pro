#!/usr/bin/env python3
# ==============================================================================
# FILE: AeroForgeX_GUI.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================
# DESCRIPTION: Advanced Analytical Dashboard with Dynamic Worker UI & Deep Controls
# ==============================================================================

import os
import sys
import subprocess
import json
import glob
import threading
import re
import io
import traceback
import copy

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# -----------------------------------------------------------------------------
# STREAMLIT BOOTSTRAPPER (Auto-Launch)
# -----------------------------------------------------------------------------
try:
    from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
    if get_script_run_ctx() is None and os.environ.get("AEROFORGEX_STREAMLIT_RUNNING") != "true":
        print("\n🚀 AeroForgeX Streamlit Web Ecosystem is Bootstrapping...")
        print("🌐 Opening securely in your default web browser...\n")
        env = os.environ.copy()
        env["AEROFORGEX_STREAMLIT_RUNNING"] = "true"
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__] + sys.argv[1:], env=env)
        sys.exit(0)
except ImportError:
    pass

# -----------------------------------------------------------------------------
# ECOSYSTEM PATHS
# -----------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SCR_DIR = os.path.join(ROOT_DIR, "AeroForgeX_scr")
AIRFOILS_DIR = os.path.join(ROOT_DIR, "Airfoils")
JSON_DIR = os.path.join(ROOT_DIR, "json_Input")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "Outputs")

for d in [AIRFOILS_DIR, JSON_DIR, OUTPUTS_DIR]:
    os.makedirs(d, exist_ok=True)

if SCR_DIR not in sys.path:
    sys.path.insert(0, SCR_DIR)

# -----------------------------------------------------------------------------
# BACKEND IMPORTS
# -----------------------------------------------------------------------------
try:
    import aeroforgex_cli as cli
    from utils_logger import commons
    from geom_builder import get_airfoil
    from opt_utils import reset_run_control, delete_run_control
except ImportError as e:
    st.error(f"CRITICAL: Cannot load AeroForgeX backend modules. Ensure '{SCR_DIR}' exists.\n{e}")
    st.stop()

# -----------------------------------------------------------------------------
# STREAMLIT PAGE CONFIG & ADAPTIVE STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AeroForgeX v4.2 Pro", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input, .stTextArea>div>div>textarea { border-radius: 6px !important; }
    .stButton>button[kind="primary"] { border-radius: 8px; font-weight: 600; border: none; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; transition: all 0.2s ease; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .stButton>button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2); }
    .stDataFrame, [data-testid="stTable"] { border: 1px solid var(--secondary-background-color); border-radius: 8px; overflow: hidden; }
    [data-testid="stMetricValue"] { font-weight: 700; font-size: 2.2rem; }
    [data-testid="stMetricDelta"] { font-weight: 600; font-size: 1rem; }
    [data-testid="stMetric"] { background: var(--secondary-background-color); padding: 20px; border-radius: 12px; border: 1px solid rgba(128,128,128,0.2); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .stTabs [role="tab"] { border-radius: 8px 8px 0 0; padding: 0.5rem 1.2rem; font-weight: 600; border: 1px solid transparent;}
    .stTabs [role="tab"][aria-selected="true"] { background-color: #2563eb; color: white; border-color: #3b82f6; }
    .stTabs [role="tabpanel"] { background: var(--background-color); padding: 24px; border-radius: 0 8px 8px 8px; border: 1px solid rgba(128,128,128,0.2); border-top: none; }
    .streamlit-expanderHeader { font-size: 16px; font-weight: 600; color: #3b82f6; background: var(--secondary-background-color); border-radius: 8px; }
    hr { border-color: var(--secondary-background-color); margin: 2rem 0; }
    .card-header { font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
    .card-header i { color: #3b82f6; }
</style>""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# UTILITIES
# -----------------------------------------------------------------------------
def list_files(directory, extensions):
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(directory, f"*{ext}")))
    return sorted([os.path.basename(f) for f in files])

def apply_adaptive_theme(fig, title, xaxis_title, yaxis_title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        xaxis=dict(title=xaxis_title),
        yaxis=dict(title=yaxis_title),
        margin=dict(l=50, r=20, t=60, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

def log_path():
    return os.path.join(OUTPUTS_DIR, "live_log.txt")

# --- [CRITICAL FIX] THREAD-SAFE LOGGER TO PREVENT I/O AND SCRIPTCONTEXT CRASHES ---
class ThreadSafeLogger:
    def __init__(self, filename, original_stdout):
        self.filename = filename
        self.original_stdout = original_stdout
        self.terminal = sys.__stdout__  # Raw, un-hijacked terminal
        self.ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        self.f = open(self.filename, "w", encoding="utf-8")
        self.target_thread_id = threading.get_ident() # Lock to background thread

    def write(self, s):
        # If Streamlit (Main Thread) is trying to print, route it back to original safe stdout
        if threading.get_ident() != self.target_thread_id:
            try: self.original_stdout.write(s)
            except Exception: self.terminal.write(s)
            return

        # If it's our background thread, log it to file safely
        try:
            if not self.f.closed:
                clean = self.ansi_escape.sub('', s)
                self.f.write(clean)
                self.f.flush()
            # Still output to raw terminal so user can see it
            self.terminal.write(s)
            self.terminal.flush()
        except Exception:
            pass

    def flush(self):
        if threading.get_ident() != self.target_thread_id:
            try: self.original_stdout.flush()
            except Exception: pass
            return
        try:
            if not self.f.closed:
                self.f.flush()
        except Exception:
            pass

    def close(self):
        try:
            if not self.f.closed:
                self.f.close()
        except Exception:
            pass

def normalize_foil_path(value):
    if isinstance(value, list):
        return os.path.join(*value) if value else ""
    return str(value) if value else ""

# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
def init_default_config():
    return {
        "opt_opts": {"solver":"xfoil","shape_func":"cst","foil_file":"","out_dir":"Outputs","auto_dir":True,"out_prefix":"opt_run","threads":-1,"verbose":True},
        "cst_opts": {"n_t":6,"n_b":6,"n1_t":0.5,"n2_t":1.0,"n1_b":0.5,"n2_b":1.0,"init_pert":0.05},
        "bez_opts": {"ncp_t":5,"ncp_b":5,"init_pert":0.1},
        "hh_opts": {"n_t":5,"n_b":3,"smooth":True,"init_pert":0.05},
        "ct_opts": {"thk":True,"thk_pos":True,"cmb":True,"cmb_pos":True,"le_r":True,"le_b":True,"init_pert":0.1},
        "op_conds": {"num_pts":1,"re_def":500000.0,"ma_def":0.0,"use_flap":False,"x_flap":0.75,"y_flap":0.0,"y_flap_spec":"y/c","flap_def":0.0,"dyn_weight":True,"dyn_spec":{"min_w":0.2,"max_w":10.0,"extra_punch":2.0,"frequency":20,"start_with_design":5}},
        "geo_tgts": {"num_tgts":0,"type":[],"val":[],"weight":[],"preset":[],"str":[]},
        "progression_spec": {"active":False},
        "constr": {"chk_geo":True,"sym":False,"min_t":0.1,"max_t":0.3,"min_c":0.0,"max_c":0.1,"min_te_ang":5.0,"min_flap":-5.0,"max_flap":15.0},
        "curv": {"chk_curv":True,"auto_curv":True,"max_rev_t":0,"max_rev_b":0,"curv_thr":0.05,"spike_thr":0.3,"max_te_c":5.0,"max_le_diff":5.0,"max_spk_t":0,"max_spk_b":0},
        "panel_opts": {"npt":161,"le_clust":0.86,"te_clust":0.6},
        "xfoil_opts": {"visc":True,"iter":100,"ncrit":9.0,"vaccel":0.005,"reinit":False,"fix_unc":True,"trip_t":1.0,"trip_b":1.0,"parallel_op":True,"cache_prec":6,"sap_enabled":True,"nf_conf_threshold":0.5},
        "optim_set": {"type":3,"algo":"lshade","pop":50,"gen":300,"min_r":0.0001,"retry":3,"speed":0.021,"init_att":1000,"conv_prof":"exhaustive","rescue":True,"f":0.5,"cr":0.9}
    }

def default_op_df(num=1):
    df = pd.DataFrame({"mode": ["spec-al"]*num, "val": [2.0]*num, "re": [500000.0]*num, "ma": [0.0]*num, "ncrit": [9.0]*num, "opt_type": ["max-glide"]*num, "weight": [1.0]*num, "tgt_val": [0.0]*num, "allow_imp": [True]*num, "flap_opt": [False]*num, "flap_ang": [0.0]*num})
    return df.astype({"allow_imp":bool,"flap_opt":bool})

def default_geo_df(num=0):
    if num <= 0: return pd.DataFrame(columns=["type","val","weight","preset","str"])
    df = pd.DataFrame({"type": ["thickness"]*num, "val": [0.12]*num, "weight": [1.0]*num, "preset": [False]*num, "str": [""]*num})
    return df.astype({"preset":bool})

if 'current_config' not in st.session_state:
    st.session_state.current_config = init_default_config()
    st.session_state.op_df = default_op_df(1)
    st.session_state.geo_df = default_geo_df(0)
    st.session_state.is_running = False
    st.session_state.active_config_path = None

def cb_start_optimization(config_path):
    st.session_state.is_running = True
    reset_run_control()
    if os.path.exists(log_path()): os.remove(log_path())
    def run(path):
        old_stdout = sys.stdout
        logger = ThreadSafeLogger(log_path(), old_stdout)
        sys.stdout = logger
        sys.argv = ["aeroforgex_cli.py", "-i", path]
        try: 
            cli.run_optimization()
        except Exception as e:
            logger.write(f"\n[FATAL ERROR] {e}\n{traceback.format_exc()}\n")
        finally:
            sys.stdout = old_stdout  # Safely restore context
            logger.close()
            delete_run_control()
    threading.Thread(target=run, args=(config_path,), daemon=True).start()

def cb_stop_optimization():
    st.session_state.is_running = False
    with open("run_control", "w") as f: f.write("STOP")

def sync_config_from_ui():
    cfg = st.session_state.current_config
    op_df = st.session_state.op_df
    geo_df = st.session_state.geo_df
    for k in ["mode","val","re","ma","ncrit","opt_type","weight","tgt_val","allow_imp","flap_opt","flap_ang"]:
        cfg["op_conds"][k] = op_df[k].tolist()
    cfg["op_conds"]["num_pts"] = len(op_df)
    for k in ["type","val","weight","preset","str"]:
        cfg["geo_tgts"][k] = geo_df[k].tolist()
    cfg["geo_tgts"]["num_tgts"] = len(geo_df)
    cfg["opt_opts"]["foil_file"] = normalize_foil_path(cfg["opt_opts"]["foil_file"])

# -----------------------------------------------------------------------------
# 1. CONFIGURATION TAB
# -----------------------------------------------------------------------------
def render_configuration():
    st.title("⚙️ Professional Configuration Matrix")

    col1, col2 = st.columns([3, 1])
    json_files = list_files(JSON_DIR, ['.json'])
    selected_json = col1.selectbox("Load Configuration Blueprint", [""] + json_files)
    if col2.button("Load Blueprint", width='stretch') and selected_json:
        path = os.path.join(JSON_DIR, selected_json)
        try:
            with open(path, 'r') as f: data = json.load(f)
            cfg = st.session_state.current_config
            for grp, cont in data.items():
                if grp in cfg and isinstance(cfg[grp], dict) and isinstance(cont, dict): cfg[grp].update(cont)
                else: cfg[grp] = cont
            cfg["opt_opts"]["foil_file"] = normalize_foil_path(cfg["opt_opts"]["foil_file"])
            nop = cfg["op_conds"].get("num_pts", len(cfg["op_conds"].get("val",[])) or 1)
            st.session_state.op_df = default_op_df(nop)
            for k in ["mode","val","re","ma","ncrit","opt_type","weight","tgt_val","allow_imp","flap_opt","flap_ang"]:
                if k in cfg["op_conds"]:
                    arr = cfg["op_conds"][k]
                    if isinstance(arr, list):
                        for i, v in enumerate(arr[:nop]): st.session_state.op_df.loc[i, k] = v
            ngeo = cfg["geo_tgts"].get("num_tgts", len(cfg["geo_tgts"].get("val",[])) or 0)
            st.session_state.geo_df = default_geo_df(ngeo)
            for k in ["type","val","weight","preset","str"]:
                if k in cfg["geo_tgts"]:
                    arr = cfg["geo_tgts"][k]
                    if isinstance(arr, list):
                        for i, v in enumerate(arr[:ngeo]): st.session_state.geo_df.loc[i, k] = v
            st.session_state.active_config_path = path
            st.success(f"Blueprint injected: {selected_json}")
        except Exception as e: st.error(f"Integrity error loading JSON: {e}")

    col1, col2 = st.columns([3, 1])
    save_name = col1.text_input("Save Blueprint As", value="opt_config_advanced")
    if col2.button("Save Blueprint", type="primary", width='stretch'):
        sync_config_from_ui()
        path = os.path.join(JSON_DIR, f"{save_name}.json")
        with open(path, 'w') as f: json.dump(st.session_state.current_config, f, indent=2)
        st.session_state.active_config_path = path
        st.success(f"Architecture saved to {path}")

    st.divider()
    tabs = st.tabs(["🏗️ Core Engine", "📏 Operating Points", "📐 Geometry Targets", "🛡️ Penalty & Curvature", "🧠 Optimizer Hyper-Params"])
    cfg = st.session_state.current_config

    with tabs[0]:
        st.markdown("<div class='card-header'>Airfoil Seed & Solvers</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            cfg["opt_opts"]["solver"] = st.selectbox("Aerodynamic Solver", ["xfoil","neuralfoil"], index=0 if cfg["opt_opts"]["solver"]=="xfoil" else 1)
            shapes = ["cst","bezier","hicks-henne","camb-thick"]
            idx = shapes.index(cfg["opt_opts"]["shape_func"]) if cfg["opt_opts"]["shape_func"] in shapes else 0
            cfg["opt_opts"]["shape_func"] = st.selectbox("Topological Parametrization", shapes, index=idx)
            airfoil_files = list_files(AIRFOILS_DIR, ['.dat','.bez','.hicks'])
            current_foil = os.path.basename(cfg["opt_opts"].get("foil_file",""))
            idx2 = airfoil_files.index(current_foil) if current_foil in airfoil_files else 0
            selected = st.selectbox("Baseline Seed Airfoil", airfoil_files, index=idx2)
            cfg["opt_opts"]["foil_file"] = os.path.join(AIRFOILS_DIR, selected) if selected else ""

        with col2:
            st.markdown("<div class='card-header'>Live Seed Preview</div>", unsafe_allow_html=True)
            if cfg["opt_opts"]["foil_file"] and os.path.exists(cfg["opt_opts"]["foil_file"]):
                try:
                    f = get_airfoil(cfg["opt_opts"]["foil_file"], silent_mode=True)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=f.x, y=f.y, mode='lines', fill='toself', name=f.name))
                    apply_adaptive_theme(fig, "", "x/c", "y/c")
                    fig.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10))
                    fig.update_yaxes(scaleanchor="x", scaleratio=1)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    st.warning("Preview unavailable.")

        st.divider()
        st.markdown("<div class='card-header'>Parametrization DNA</div>", unsafe_allow_html=True)
        shape = cfg["opt_opts"]["shape_func"]
        if shape == "cst":
            c1,c2,c3 = st.columns(3)
            cfg["cst_opts"]["n_t"] = c1.number_input("Upper CST Weights", value=cfg["cst_opts"]["n_t"])
            cfg["cst_opts"]["n_b"] = c2.number_input("Lower CST Weights", value=cfg["cst_opts"]["n_b"])
            cfg["cst_opts"]["init_pert"] = c3.number_input("Initial Chaos (Perturbation)", value=float(cfg["cst_opts"]["init_pert"]), format="%.3f")
        elif shape == "bezier":
            c1,c2,c3 = st.columns(3)
            cfg["bez_opts"]["ncp_t"] = c1.slider("Upper Control Points", 2, 20, cfg["bez_opts"]["ncp_t"])
            cfg["bez_opts"]["ncp_b"] = c2.slider("Lower Control Points", 2, 20, cfg["bez_opts"]["ncp_b"])
            cfg["bez_opts"]["init_pert"] = c3.number_input("Initial Perturbation", value=cfg["bez_opts"]["init_pert"])


    with tabs[1]:
        st.markdown("<div class='card-header'>Flight Envelope Matrix</div>", unsafe_allow_html=True)
        nop = st.number_input("Multipoint Count", min_value=1, max_value=45, value=len(st.session_state.op_df))
        if nop != len(st.session_state.op_df):
            if nop > len(st.session_state.op_df):
                extra = default_op_df(nop - len(st.session_state.op_df))
                st.session_state.op_df = pd.concat([st.session_state.op_df, extra], ignore_index=True)
            else: st.session_state.op_df = st.session_state.op_df.iloc[:nop]
        
        # --- [NEW] DROPDOWN LISTS FOR OPERATING POINTS ---
        op_col_config = {
            "mode": st.column_config.SelectboxColumn(
                "Mode", 
                help="How the solver targets the point.", 
                options=["spec-al", "spec-cl"], 
                required=True
            ),
            "opt_type": st.column_config.SelectboxColumn(
                "Objective", 
                help="The aerodynamic goal.", 
                options=["max-glide", "min-sink", "min-drag", "max-lift", "max-xtr", "target-drag", "target-glide", "target-lift", "target-moment"], 
                required=True
            )
        }
        
        st.session_state.op_df = st.data_editor(st.session_state.op_df, column_config=op_col_config, num_rows="dynamic", use_container_width=True, key="op_editor")

    with tabs[2]:
        st.markdown("<div class='card-header'>Strict Geometrical Phantoms</div>", unsafe_allow_html=True)
        # Restricted max targets to 3 since there are only 3 available types
        ntg = st.number_input("Target Count", min_value=0, max_value=3, value=len(st.session_state.geo_df))
        if ntg != len(st.session_state.geo_df):
            if ntg > len(st.session_state.geo_df):
                extra = default_geo_df(ntg - len(st.session_state.geo_df))
                st.session_state.geo_df = pd.concat([st.session_state.geo_df, extra], ignore_index=True)
            else: st.session_state.geo_df = st.session_state.geo_df.iloc[:ntg]
        
        # --- [NEW] DROPDOWN LIST FOR GEOMETRY TARGETS ---
        geo_col_config = {
            "type": st.column_config.SelectboxColumn(
                "Target Type", 
                help="Select the geometric target constraint.", 
                options=["thickness", "camber", "match-foil"], 
                required=True
            )
        }
        
        st.session_state.geo_df = st.data_editor(st.session_state.geo_df, column_config=geo_col_config, num_rows="dynamic", use_container_width=True, key="geo_editor")

        # --- [NEW] UNIQUENESS VALIDATOR (Prevents duplicate selections) ---
        if not st.session_state.geo_df.empty:
            selected_types = st.session_state.geo_df["type"].dropna().tolist()
            if len(selected_types) != len(set(selected_types)):
                st.error("⚠️ **Duplicate Target Detected:** You can only select one of each type ('thickness', 'camber', 'match-foil'). Please change the duplicate row.")

    with tabs[3]:
        col1,col2 = st.columns(2)
        with col1:
            st.markdown("<div class='card-header'>Volumetric Penalties</div>", unsafe_allow_html=True)
            
            # --- [NEW] HIGH-PRECISION SLIDERS ---
            cfg["constr"]["min_t"], cfg["constr"]["max_t"] = st.slider(
                "Thickness Constraint (%c)", 
                min_value=0.0, 
                max_value=40.0, 
                value=(float(cfg["constr"]["min_t"]*100), float(cfg["constr"]["max_t"]*100)), 
                step=0.01, 
                format="%.2f%%"
            )
            cfg["constr"]["min_t"] /= 100.0; cfg["constr"]["max_t"] /= 100.0
            
            cfg["constr"]["min_c"], cfg["constr"]["max_c"] = st.slider(
                "Camber Constraint (%c)", 
                min_value=-10.0, 
                max_value=10.0, 
                value=(float(cfg["constr"]["min_c"]*100), float(cfg["constr"]["max_c"]*100)), 
                step=0.001, 
                format="%.3f%%"
            )
            cfg["constr"]["min_c"] /= 100.0; cfg["constr"]["max_c"] /= 100.0
            
            cfg["constr"]["min_te_ang"] = st.number_input("Min TE Wedge Angle (°)", value=float(cfg["constr"]["min_te_ang"]), step=0.1)
            
        with col2:
            st.markdown("<div class='card-header'>Mathematical Curvature Limits</div>", unsafe_allow_html=True)
            cfg["curv"]["auto_curv"] = st.checkbox("Auto-Calibrate Strict Flow Separation Curves", value=cfg["curv"]["auto_curv"])
            if not cfg["curv"]["auto_curv"]:
                cfg["curv"]["max_rev_t"] = st.number_input("Upper Reversals", value=int(cfg["curv"]["max_rev_t"]))
                cfg["curv"]["max_te_c"] = st.number_input("Max TE Curvature", value=float(cfg["curv"]["max_te_c"]))

    with tabs[4]:
        col1,col2 = st.columns(2)
        with col1:
            st.markdown("<div class='card-header'>PyMoo Evolutionary Mechanics</div>", unsafe_allow_html=True)
            
            engine_map = {1: "1: PyMoo Multi-Algorithm Engine (DE/NM)", 2: "2: Custom Self-Adaptive DE (jDE)", 3: "3: Custom Success-History DE (SHADE)"}
            cur_type = cfg["optim_set"].get("type", 1)
            cfg["optim_set"]["type"] = st.selectbox("Core Optimizer Engine", list(engine_map.keys()), format_func=lambda x: engine_map[x], index=list(engine_map.keys()).index(cur_type) if cur_type in engine_map else 0)

            algo_map = {"lshade":"L-SHADE (Self-Adaptive)","shade":"SHADE (Success-History)","jde":"jDE (Adaptive)","de":"Standard DE","nm-only":"Nelder-Mead Only (Local Refinement)"}
            cur_alg = cfg["optim_set"].get("algo","lshade")
            cfg["optim_set"]["algo"] = st.selectbox("PyMoo Algorithm Strategy (Engine 1)", list(algo_map.keys()), format_func=lambda x:algo_map[x], index=list(algo_map.keys()).index(cur_alg) if cur_alg in algo_map else 0, disabled=(cfg["optim_set"]["type"] != 1))
            c1,c2 = st.columns(2)
            cfg["optim_set"]["pop"] = c1.number_input("Population Swarm", value=cfg["optim_set"]["pop"])
            cfg["optim_set"]["gen"] = c2.number_input("Max Epochs", value=cfg["optim_set"]["gen"])
            st.markdown("**(DE Hyper-Parameters)**")
            cx, cy = st.columns(2)
            cfg["optim_set"]["f"] = cx.slider("Mutation Factor (F)", 0.0, 2.0, float(cfg["optim_set"].get("f", 0.5)))
            cfg["optim_set"]["cr"] = cy.slider("Crossover Rate (CR)", 0.0, 1.0, float(cfg["optim_set"].get("cr", 0.9)))
        with col2:
            st.markdown("<div class='card-header'>Boundary Layer Engine (XFOIL)</div>", unsafe_allow_html=True)
            c3, c4 = st.columns(2)
            cfg["xfoil_opts"]["iter"] = c3.number_input("Newton Iterations", value=cfg["xfoil_opts"]["iter"])
            cfg["xfoil_opts"]["ncrit"] = c4.number_input("N-Crit (Turbulence)", value=float(cfg["xfoil_opts"]["ncrit"]))
            cfg["panel_opts"]["npt"] = st.number_input("Computational Mesh Nodes", value=cfg["panel_opts"]["npt"], step=10)
            cfg["panel_opts"]["le_clust"] = st.slider("LE Clustering Density", 0.1, 2.0, float(cfg["panel_opts"].get("le_clust", 0.86)))
            
            st.markdown("**(Surrogate-Assisted Search & Caching)**")
            cx1, cx2 = st.columns(2)
            cfg["xfoil_opts"]["sap_enabled"] = cx1.checkbox("Enable SAP AI Pre-Filter", value=cfg["xfoil_opts"].get("sap_enabled", True))
            cfg["xfoil_opts"]["parallel_op"] = cx2.checkbox("Parallel Multipoint Sweeps", value=cfg["xfoil_opts"].get("parallel_op", True))
            cx3, cx4 = st.columns(2)
            cfg["xfoil_opts"]["nf_conf_threshold"] = cx3.slider("NeuralFoil Confidence", 0.1, 0.9, float(cfg["xfoil_opts"].get("nf_conf_threshold", 0.5)))
            cfg["xfoil_opts"]["cache_prec"] = cx4.number_input("Cache Hash Precision", min_value=1, max_value=16, value=int(cfg["xfoil_opts"].get("cache_prec", 6)))

# -----------------------------------------------------------------------------
# 2. DEPLOYMENT TAB
# -----------------------------------------------------------------------------
def render_deployment():
    st.title("🚀 Subprocess Deployment Console")
    if st.session_state.is_running: st_autorefresh(interval=3000, limit=None, key="live_refresh")
    if st.session_state.is_running and not os.path.exists("run_control"): st.session_state.is_running = False

    col1, col2 = st.columns(2)
    with col1: st.button("▶ Initiate Neural/XFOIL Engine", type="primary", disabled=st.session_state.is_running, width='stretch', on_click=lambda: _prep_and_start())
    with col2: st.button("⏹ Halt Execution", disabled=not st.session_state.is_running, width='stretch', on_click=cb_stop_optimization)

    def _prep_and_start():
        sync_config_from_ui()
        tmp = os.path.join(JSON_DIR, "_running_config.json")
        with open(tmp, 'w') as f: json.dump(st.session_state.current_config, f, indent=2)
        st.session_state.active_config_path = tmp
        cb_start_optimization(tmp)

    st.divider()
    if st.session_state.is_running: st.success("🔥 Distributed optimization swarm active...", icon="⏳")
    else: st.info("System Idle – Standby for deployment vector.", icon="⏸️")

    if os.path.exists(log_path()):
        try:
            with open(log_path(), 'r', encoding='utf-8') as f: st.code(f.read()[-10000:], language="bash")
        except: st.code("Log stream locked by Fortran subprocess...", language="bash")

# -----------------------------------------------------------------------------
# 3. DYNAMIC WORKER TAB
# -----------------------------------------------------------------------------
def render_worker():
    st.title("🔧 Advanced Worker Utility Matrix")
    
    action_map = {
        "polar": "Aerodynamic Polar Sweep (DAT)",
        "polar-csv": "Aerodynamic Polar Sweep (CSV + Dash)",
        "bezier": "Topological Simplex Match (Bezier)",
        "norm": "Absolute Coordinate Normalization & Repanel",
        "flap": "Kinematic Trailing Edge Deflection",
        "check": "Surface Diagnostics & Curvature Check",
        "set": "Hard Scalar Mutation (Set Property)",
        "blend": "Algorithmic Foil Blending",
        "generate": "Parametric Family Generation",
        "smooth": "Mathematical Smoothing Filter",
        "report": "Automated HTML/PDF Diagnostics"
    }

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("<div class='card-header'>Execution Directive</div>", unsafe_allow_html=True)
        raw_action = st.selectbox("Directive", list(action_map.keys()), format_func=lambda x: action_map[x])
        
        dirs = [AIRFOILS_DIR] + [os.path.join(AIRFOILS_DIR, d) for d in os.listdir(AIRFOILS_DIR) if os.path.isdir(os.path.join(AIRFOILS_DIR, d))]
        dir_opts = [f"[DIR] {d}" for d in dirs]
        airfoils = [""] + dir_opts + list_files(AIRFOILS_DIR, ['.dat','.bez','.hicks'])
        
        af_raw = st.selectbox("Primary Target (File or [DIR] for Batch)", airfoils)
        af = af_raw.replace("[DIR] ", "") if af_raw else ""
        
        # --- SMART AUTO-FOLDER GENERATION ---
        af_stem = os.path.splitext(os.path.basename(af))[0] if af else "Batch"
        rel_out_dir = os.path.join(OUTPUTS_DIR, "Worker_Mode", raw_action.capitalize(), af_stem)
        default_prefix = os.path.join(rel_out_dir, f"{af_stem}_{raw_action}")
        
        out_prefix = st.text_input("Output Prefix Path (-o)", value=default_prefix)
        
        # Dynamic UI Elements
        af2 = ""; val_arg = ""; extra_json = {}
        st.markdown("<div class='card-header'>Directive Parameters</div>", unsafe_allow_html=True)
        
        # --- SOLVER SELECTION ---
        selected_solver = "xfoil"
        if raw_action in ["polar", "polar-csv", "flap"]:
            selected_solver = st.selectbox("Aerodynamic Solver Engine", ["xfoil", "neuralfoil"], index=0)
            extra_json["opt_opts"] = {"solver": selected_solver, "aero_solver": selected_solver}

        if raw_action in ["polar", "polar-csv"]:
            re_val = st.number_input("Reynolds Number Default", 10000.0, 10000000.0, 500000.0, step=50000.0)
            a_start, a_end, a_step = st.columns(3)
            alpha_s = a_start.number_input("Alpha Min", -20.0, 30.0, -5.0)
            alpha_e = a_end.number_input("Alpha Max", -20.0, 30.0, 15.0)
            alpha_st = a_step.number_input("Alpha Step", 0.1, 5.0, 0.5)
            extra_json["polar_generation"] = {"op_point_range": [alpha_s, alpha_e, alpha_st], "generate_polar": True}
            
        elif raw_action == "blend":
            af2 = st.selectbox("Secondary Airfoil Matrix (-a2)", airfoils)
            ratio = st.slider("Morphing Ratio (0=Primary, 1=Secondary)", 0.0, 1.0, 0.5)
            val_arg = str(ratio)
            
        elif raw_action == "flap":
            cx, cy, ca = st.columns(3)
            hx = cx.number_input("Hinge X", 0.0, 1.0, 0.75)
            hy = cy.number_input("Hinge Y", -0.5, 0.5, 0.0)
            ang = ca.number_input("Deflect °", -45.0, 45.0, 5.0)
            extra_json["operating_conditions"] = {"x_flap": hx, "y_flap": hy, "flap_angle": [ang]}
            
        elif raw_action == "bezier":
            ncp_t = st.slider("Top Control Polynomials", 2, 20, 6)
            ncp_b = st.slider("Bottom Control Polynomials", 2, 20, 6)
            extra_json["bezier_options"] = {"ncp_t": ncp_t, "ncp_b": ncp_b}
            
        elif raw_action == "set":
            prop_map = {"t":"Thickness", "c":"Camber", "xt":"Max Thick X", "xc":"Max Camb X", "te":"TE Gap"}
            prop = st.selectbox("Target Scalar", list(prop_map.keys()), format_func=lambda x: prop_map[x])
            val = st.number_input("Percentage (%)", 0.0, 100.0, 12.0)
            val_arg = f"{prop}={val}"
            
        elif raw_action == "generate":
            prop_map = {"t":"Thickness", "c":"Camber", "xt":"Max Thick X", "xc":"Max Camb X", "te":"TE Gap"}
            prop = st.selectbox("Scaling Parameter", list(prop_map.keys()), format_func=lambda x: prop_map[x])
            c1, c2, c3 = st.columns(3)
            vmin = c1.number_input("Min (%)", 0.0, 100.0, 8.0)
            vmax = c2.number_input("Max (%)", 0.0, 100.0, 16.0)
            steps = c3.number_input("Steps", 2, 50, 5)
            val_arg = f"{prop}={vmin}:{vmax}:{steps}"
            
        elif raw_action == "smooth":
            window = st.slider("Savitzky-Golay Window Size", 5, 51, 11, step=2)
            val_arg = str(window)
            
        elif raw_action == "report":
            st.info("Generates dual HTML and PDF diagnostic reports mapping geometry and curvature.", icon="📊")
            val_arg = ""
            
        elif raw_action == "norm":
            pts = st.number_input("Repanel Nodes", 50, 400, 161)
            extra_json["panel_options"] = {"npt": pts}

        if st.button("🚀 Dispatch Worker Thread", type="primary", width='stretch'):
            af_path = os.path.join(AIRFOILS_DIR, af) if af else ""
            af2_path = os.path.join(AIRFOILS_DIR, af2) if af2 else ""
            
            # --- ENSURE OUTPUT DIRECTORY EXISTS PRE-DISPATCH ---
            out_dir_path = os.path.dirname(out_prefix)
            if out_dir_path:
                os.makedirs(out_dir_path, exist_ok=True)
            
            # Combine UI logic into a dynamically generated JSON for the backend
            base_json = st.session_state.current_config.copy()
            for k, v in extra_json.items():
                if k in base_json: base_json[k].update(v)
                else: base_json[k] = v
                
            if raw_action in ["polar", "polar-csv"]:
                base_json["polar_generation"]["polar_reynolds"] = st.session_state.polar_df["Reynolds"].tolist()
                base_json["polar_generation"]["polar_mach"] = st.session_state.polar_df["Mach"].tolist()
                base_json["polar_generation"]["polar_flap"] = st.session_state.polar_df["Flap Angle"].tolist()

            # --- ORGANIZE WORKER JSON FILES ---
            worker_json_dir = os.path.join(JSON_DIR, "Worker_Mode")
            os.makedirs(worker_json_dir, exist_ok=True)
            tmp_json = os.path.join(worker_json_dir, f"{af_stem}_{raw_action}_cfg.json")
            with open(tmp_json, 'w') as f: json.dump(base_json, f, indent=2)

            from argparse import Namespace
            a = Namespace(action=raw_action, input=tmp_json, output=out_prefix, airfoil=af_path, airfoil2=af2_path, reynolds=re_val if raw_action in ['polar','polar-csv'] else 0.0, value_argument=val_arg)

            def run_worker_task(args):
                # Save old stdout to prevent 'I/O operation on closed file' crash on exit
                old_stdout = sys.stdout 
                with open(log_path(), 'w') as f: f.write("")
                logger = ThreadSafeLogger(log_path(), old_stdout)
                sys.stdout = logger
                try: 
                    cli.run_worker(args)
                except Exception as e: 
                    logger.write(f"\n[ERROR] {e}\n{traceback.format_exc()}\n")
                finally: 
                    sys.stdout = old_stdout  # Critical Restore
                    logger.close()

            threading.Thread(target=run_worker_task, args=(a,), daemon=True).start()
            st.toast(f"Dispatched: {raw_action}")

    with col2:
        if raw_action in ["polar", "polar-csv"]:
            st.markdown("<div class='card-header'>Multi-Sweep Condition Matrix</div>", unsafe_allow_html=True)
            if 'polar_df' not in st.session_state: st.session_state.polar_df = pd.DataFrame({"Reynolds":[500000.0],"Mach":[0.0],"Flap Angle":[0.0]})
            st.session_state.polar_df = st.data_editor(st.session_state.polar_df, num_rows="dynamic", use_container_width=True)
            
        st.markdown("<br><div class='card-header'>Subprocess Telemetry</div>", unsafe_allow_html=True)
        if os.path.exists(log_path()):
            try:
                with open(log_path(), 'r', encoding='utf-8') as f: st.code(f.read()[-10000:], language="bash")
            except: pass


# -----------------------------------------------------------------------------
# 4. ANALYSIS DASHBOARD
# -----------------------------------------------------------------------------
def render_dashboard():
    st.title("📊 Commercial Analytical Dashboard")
    all_csvs = glob.glob(os.path.join(OUTPUTS_DIR, "**", "*.csv"), recursive=True)
    if not all_csvs: return st.warning("No telemetry data found. Deploy an optimization or worker task first.")
        
    run_folders = set([os.path.dirname(f) for f in all_csvs if "Design_Coordinates.csv" in f or "polar_master" in f])
    folder_map, folder_mtime = {}, {}
    for abs_path in run_folders:
        rel_path = os.path.relpath(abs_path, OUTPUTS_DIR)
        folder_map[rel_path] = abs_path
        folder_mtime[rel_path] = os.path.getmtime(abs_path)
        
    sorted_rel_paths = sorted(folder_map.keys(), key=lambda k: folder_mtime[k], reverse=True)
    if not sorted_rel_paths: return st.warning("No recognized AeroForgeX data structures found in the Outputs directory.")
        
    st.markdown("<div style='background: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.2); margin-bottom: 20px;'>", unsafe_allow_html=True)
    sel_rel_path = st.selectbox("Select Target Dataset for Analysis", sorted_rel_paths)
    st.markdown("</div>", unsafe_allow_html=True)
    sel_dir = folder_map[sel_rel_path]
    if any("Design_Coordinates" in fn for fn in os.listdir(sel_dir)): render_embedded_optimization_analysis(sel_dir)
    else: render_polar_analysis(sel_dir)

def render_embedded_optimization_analysis(opt_dir):
    st.subheader(f"Optimization Analysis: {os.path.basename(opt_dir)}")
    parent_dir = os.path.dirname(opt_dir)
    possible_htmls = glob.glob(os.path.join(opt_dir, "*_Interactive_Report.html")) + glob.glob(os.path.join(parent_dir, "*_Interactive_Report.html"))
    if possible_htmls:
        try:
            with open(possible_htmls[0], 'r', encoding='utf-8') as f: components.html(f.read(), height=1400, scrolling=True)
        except Exception as e: st.error(f"Failed to read the interactive report: {e}")
    else:
        st.warning("Interactive Report not found for this run. The run might be incomplete or crashed before final report generation.")
        st.info("Displaying fallback Convergence telemetry:")
        conv_files = glob.glob(os.path.join(opt_dir, "..", "*_Conv.csv")) + glob.glob(os.path.join(opt_dir, "*_Conv.csv"))
        if conv_files:
            try:
                df_cv = pd.read_csv(conv_files[0], on_bad_lines='skip')
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_cv['Gen'], y=df_cv['Imp_Pct'], mode='lines+markers', line=dict(color='#10b981', width=3), fill='tozeroy', fillcolor='rgba(16,185,129,0.1)'))
                apply_adaptive_theme(fig, "Live Convergence Trajectory", "Generation", "Improvement (%)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception: st.error("Could not load fallback convergence data.")

def render_polar_analysis(polar_dir):
    st.subheader(f"Polar Sweep Analysis: {os.path.basename(polar_dir)}")
    master_csv = glob.glob(os.path.join(polar_dir, "*polar_master*.csv"))
    if not master_csv: return st.error("No polar_master.csv found.")
    try:
        df = pd.read_csv(master_csv[0], sep=';', on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.lower()
        df['ld'] = df['cl'] / df['cd'].replace(0, np.nan)
        st.metric("Global Max L/D", f"{df['ld'].max():.1f}")
        colors = ['#3b82f6','#10b981','#ef4444','#f59e0b','#8b5cf6', '#ec4899', '#06b6d4']
        fig_l, fig_d = go.Figure(), go.Figure()
        for i, ((re, mach, flap), grp) in enumerate(df.groupby(['re','mach','flap'])):
            lbl = f"Re {int(re/1000)}k | M {mach} | F {flap}°"
            c = colors[i % len(colors)]
            fig_l.add_trace(go.Scatter(x=grp['alpha'], y=grp['cl'], mode='lines+markers', name=lbl, line=dict(color=c, width=2)))
            fig_d.add_trace(go.Scatter(x=grp['cd'], y=grp['cl'], mode='lines+markers', name=lbl, line=dict(color=c, width=2)))
        apply_adaptive_theme(fig_l, "Lift Curve Mapping (CL vs α)", "Alpha (°)", "Coefficient of Lift (CL)")
        apply_adaptive_theme(fig_d, "Drag Polar (CL vs CD)", "Coefficient of Drag (CD)", "Coefficient of Lift (CL)")
        c1, c2 = st.columns(2)
        c1.plotly_chart(fig_l, use_container_width=True)
        c2.plotly_chart(fig_d, use_container_width=True)
        st.markdown("<div class='card-header'>Raw Sweep Telemetry</div>", unsafe_allow_html=True)
        st.dataframe(df.style.background_gradient(cmap='viridis', subset=['ld']), use_container_width=True)
    except Exception as e: st.error(f"Failed to parse Worker Polar data: {e}")

# -----------------------------------------------------------------------------
# MASTER ROUTER
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<h1 style='color: #3b82f6; font-size: 2.2rem;'>AeroForgeX Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-weight: 600;'>Enterprise Optimization Suite</p>", unsafe_allow_html=True)
    st.divider()
    page = st.radio("System Modules", ["⚙️ Configuration Matrix", "🚀 Deployment Console", "🔧 Worker Utility", "📊 Analytical Dashboard"])
    st.divider()
    if sys.platform == "win32":
        if st.button("📁 Open Local Outputs", width='stretch'): os.startfile(OUTPUTS_DIR)
        if st.button("📚 Open Local Airfoils", width='stretch'): os.startfile(AIRFOILS_DIR)

if page == "⚙️ Configuration Matrix": render_configuration()
elif page == "🚀 Deployment Console": render_deployment()
elif page == "🔧 Worker Utility": render_worker()
elif page == "📊 Analytical Dashboard": render_dashboard()