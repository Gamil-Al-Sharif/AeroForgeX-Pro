# ==============================================================================
# FILE: test_gui.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================

import os
import sys
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

# Ensure we bypass the bootstrapper to run test blocks safely in-memory
os.environ["AEROFORGEX_STREAMLIT_RUNNING"] = "true"

def test_config_matrix_deep_inputs():
    """
    Tests the Configuration Matrix page elements:
    - Verifies app loading and initial state.
    - Tests changing the Aerodynamic Solver and Parametrization.
    - Interacts with evolutionary swarm parameter inputs.
    - Asserts that UI changes propagate perfectly to the core session state.
    """
    at = AppTest.from_file("AeroForgeX_GUI.py").run(timeout=30)
    
    # 1. Assert baseline GUI structure
    assert not at.exception, "GUI crashed on load"
    assert "AeroForgeX Pro" in at.sidebar.markdown[0].value
    assert at.session_state.is_running is False
    assert "opt_opts" in at.session_state.current_config
    
    # 2. Query and modify the Aerodynamic Solver selectbox
    solver_box = next(b for b in at.selectbox if "Aerodynamic Solver" in b.label)
    assert solver_box.value == "xfoil"
    solver_box.set_value("neuralfoil").run(timeout=30)
    assert at.session_state.current_config["opt_opts"]["solver"] == "neuralfoil"

    # 3. Query and modify the Parametrization type selectbox
    param_box = next(b for b in at.selectbox if "Topological Parametrization" in b.label)
    assert param_box.value == "cst"
    param_box.set_value("bezier").run(timeout=30)
    assert at.session_state.current_config["opt_opts"]["shape_func"] == "bezier"

    # 4. Modify Evolutionary parameters (Swarm Pop, Crossover Rate)
    pop_input = next(n for n in at.number_input if "Population Swarm" in n.label)
    pop_input.set_value(75).run(timeout=30)
    assert at.session_state.current_config["optim_set"]["pop"] == 75

    cr_slider = next(s for s in at.slider if "Crossover Rate" in s.label)
    cr_slider.set_value(0.75).run(timeout=30)
    assert at.session_state.current_config["optim_set"]["cr"] == 0.75


def test_worker_utility_blend_mode():
    """
    Tests the Worker Utility tab specifically for Blending configuration.
    """
    at = AppTest.from_file("AeroForgeX_GUI.py").run(timeout=30)
    at.sidebar.radio[0].set_value("🔧 Worker Utility").run(timeout=30)
    assert not at.exception
    
    action_box = next(b for b in at.selectbox if "Directive" in b.label)
    action_box.set_value("blend").run(timeout=30)
    
    # Verify that the Morphing Ratio slider has rendered and modify it
    blend_slider = next(s for s in at.slider if "Morphing Ratio" in s.label)
    blend_slider.set_value(0.35).run(timeout=30)


def test_worker_utility_flap_mode():
    """
    Tests the Worker Utility tab specifically for Kinematic Flap configuration.
    """
    at = AppTest.from_file("AeroForgeX_GUI.py").run(timeout=30)
    at.sidebar.radio[0].set_value("🔧 Worker Utility").run(timeout=30)
    assert not at.exception
    
    action_box = next(b for b in at.selectbox if "Directive" in b.label)
    action_box.set_value("flap").run(timeout=30)
    
    # Verify numerical flap coords (Hinge X) is visible and modify it
    hinge_x_input = next(n for n in at.number_input if "Hinge X" in n.label)
    hinge_x_input.set_value(0.80).run(timeout=30)


def test_worker_utility_set_mode():
    """
    Tests the Worker Utility tab specifically for Property Mutation configuration.
    """
    at = AppTest.from_file("AeroForgeX_GUI.py").run(timeout=30)
    at.sidebar.radio[0].set_value("🔧 Worker Utility").run(timeout=30)
    assert not at.exception
    
    action_box = next(b for b in at.selectbox if "Directive" in b.label)
    action_box.set_value("set").run(timeout=30)
    
    # Verify Property mutation dropdown and modify it
    prop_box = next(b for b in at.selectbox if "Target Scalar" in b.label)
    prop_box.set_value("c").run(timeout=30)  # Target Camber


def test_deployment_console_orchestration():
    """
    Tests the Subprocess Deployment Console:
    - Checks the execution launch controls.
    - Mocks the presence of the `run_control` file to prevent auto-reset of running state.
    - Toggles active running status and simulates process halt.
    """
    at = AppTest.from_file("AeroForgeX_GUI.py").run(timeout=30)
    
    # Navigate to the Deployment tab
    at.sidebar.radio[0].set_value("🚀 Deployment Console").run(timeout=30)
    assert not at.exception
    
    # Verify launch controls are visible and enabled
    start_btn = next(btn for btn in at.button if "Initiate Neural/XFOIL Engine" in btn.label)
    stop_btn = next(btn for btn in at.button if "Halt Execution" in btn.label)
    
    assert start_btn.disabled is False
    assert stop_btn.disabled is True  # Disabled because server is idle
    
    # Create the run_control file to mock active solver execution
    with open("run_control", "w") as f:
        f.write("RUN")
        
    try:
        # Simulate initiating run loop callbacks
        at.session_state.is_running = True
        at.run(timeout=30)
        
        # Stop button should now be active, start button disabled
        start_btn = next(btn for btn in at.button if "Initiate Neural/XFOIL Engine" in btn.label)
        stop_btn = next(btn for btn in at.button if "Halt Execution" in btn.label)
        assert start_btn.disabled is True
        assert stop_btn.disabled is False
    finally:
        if os.path.exists("run_control"):
            os.remove("run_control")


def test_analytical_dashboard_graceful_fallbacks():
    """
    Tests the Analytical Dashboard tab:
    - Navigates to the tab.
    - Verifies that if no datasets exist in the system, it renders a warning instead of throwing exceptions.
    - If dataset target dropdown renders, verifies the path selector lists items correctly.
    """
    at = AppTest.from_file("AeroForgeX_GUI.py").run(timeout=30)
    
    # Navigate to the Dashboard tab
    at.sidebar.radio[0].set_value("📊 Analytical Dashboard").run(timeout=30)
    assert not at.exception
    
    # The dashboard scans files. Let's verify it doesn't crash regardless of whether data is populated
    if len(at.selectbox) > 0:
        dataset_box = next((b for b in at.selectbox if "Select Target Dataset" in b.label), None)
        if dataset_box:
            assert dataset_box.value is not None
    else:
        # If no outputs, verify warning is visible
        assert "warning" in [w.type for w in at.warning]


def test_config_matrix_parallel_caching_inputs():
    """
    Tests the parallelization and cache rounding precision inputs in the configuration tab.
    """
    at = AppTest.from_file("AeroForgeX_GUI.py").run(timeout=30)
    assert not at.exception
    
    # Verify parallel sweeps checkbox
    parallel_checkbox = next(cb for cb in at.checkbox if "Parallel Multipoint Sweeps" in cb.label)
    assert parallel_checkbox.value is True
    parallel_checkbox.set_value(False).run(timeout=30)
    assert at.session_state.current_config["xfoil_opts"]["parallel_op"] is False
    
    # Verify cache hash rounding precision input
    cache_prec_input = next(n for n in at.number_input if "Cache Hash Precision" in n.label)
    assert cache_prec_input.value == 6
    cache_prec_input.set_value(8).run(timeout=30)
    assert at.session_state.current_config["xfoil_opts"]["cache_prec"] == 8

    # Verify SAP pre-filter checkbox
    sap_checkbox = next(cb for cb in at.checkbox if "Enable SAP AI Pre-Filter" in cb.label)
    assert sap_checkbox.value is True
    sap_checkbox.set_value(False).run(timeout=30)
    assert at.session_state.current_config["xfoil_opts"]["sap_enabled"] is False

    # Verify NeuralFoil confidence slider
    nf_slider = next(s for s in at.slider if "NeuralFoil Confidence" in s.label)
    assert nf_slider.value == 0.5
    nf_slider.set_value(0.7).run(timeout=30)
    assert at.session_state.current_config["xfoil_opts"]["nf_conf_threshold"] == 0.7

