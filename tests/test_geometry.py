# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================

import numpy as np
import pytest
from shape_functions_param import _bez_1d_arr, _hh_eval_tensor, BezierSpecType, HHType

def test_bezier_generation():
    # Test flat Bezier
    px = np.array([0.0, 0.5, 1.0])
    py = np.array([0.0, 0.0, 0.0])
    x_eval = np.linspace(0, 1, 11)
    
    # _bez_1d_arr(px, u, der)
    y_eval = _bez_1d_arr(py, x_eval, 0)
    assert np.all(y_eval == 0.0)
    assert len(y_eval) == 11

def test_hh_generation():
    # Test flat Hicks-Henne
    x = np.linspace(0.1, 0.9, 9) # Avoid 0 and 1 boundaries
    # _hh_eval_tensor(st_arr, loc_arr, wid_arr, x)
    # 0 strength bumps
    strengths = np.zeros(3)
    locs = np.array([0.3, 0.5, 0.7])
    widths = np.array([1.0, 1.0, 1.0])
    
    y_new = _hh_eval_tensor(strengths, locs, widths, x)
    assert np.all(y_new == 0.0)
    assert len(y_new) == 9

def test_hh_with_bumps():
    x = np.array([0.5])
    # Single bump at 0.5
    strengths = np.array([0.1])
    locs = np.array([0.5])
    widths = np.array([1.0]) 
    
    # _hh_eval_tensor(st_arr, loc_arr, wid_arr, x)
    # p = log10(0.5)/log10(0.5) = 1.0
    # v = 0.1 * (sin(pi * 0.5)^1.0) = 0.1 * 1.0 = 0.1
    y_new = _hh_eval_tensor(strengths, locs, widths, x)
    np.testing.assert_allclose(y_new, np.array([0.1]), atol=1e-7)
