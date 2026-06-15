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
from math_accelerator import _diff_1D, _closest_idx, _trans_arccos, _deriv1

def test_diff_1d():
    x = np.array([0.0, 1.0, 3.0, 6.0])
    expected = np.array([1.0, 2.0, 3.0])
    np.testing.assert_allclose(_diff_1D(x), expected)

def test_closest_idx():
    arr = np.array([0.0, 0.5, 1.0, 2.0])
    assert _closest_idx(arr, 0.4) == 1
    assert _closest_idx(arr, 0.2) == 0
    assert _closest_idx(arr, 1.6) == 3
    assert _closest_idx(arr, -1.0) == 0
    assert _closest_idx(arr, 3.0) == 3

def test_trans_arccos():
    x = np.array([0.0, 1.0, 2.0])
    # 1 - x gives [1, 0, -1]
    # arccos([1, 0, -1]) gives [0, pi/2, pi]
    # * 2 / pi gives [0, 1, 2]
    expected = np.array([0.0, 1.0, 2.0])
    np.testing.assert_allclose(_trans_arccos(x), expected, atol=1e-7)

def test_deriv1():
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = x**2 # y = [0, 1, 4, 9]
    # dy/dx should be ~2x
    # At x=1, deriv is (4 - 0) / 2 = 2.0 (central diff)
    # At x=2, deriv is (9 - 1) / 2 = 4.0
    d = _deriv1(x, y)
    assert d[1] == 2.0
    assert d[2] == 4.0
    # Boundary: (y1-y0)/(x1-x0) = 1.0
    assert d[0] == 1.0
    assert d[3] == 5.0
