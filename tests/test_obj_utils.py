# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from obj_utils import eval_geometry_violations, NO_VIOLATION, VIOL_LE_BLUNT, VIOL_LE_SHARP

class MockFoil:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.top = MagicMock()
        self.bot = MagicMock()
        self.symmetrical = True
        self.is_bezier_based = False

def test_eval_geometry_violations_clean():
    # Symmetric diamond-like airfoil (not blunt, not sharp)
    x = np.array([1.0, 0.5, 0.0, 0.5, 1.0])
    y = np.array([0.0, 0.05, 0.0, -0.05, 0.0])
    f = MockFoil(x, y)
    c = MagicMock()
    c.min_te_angle = 1.0
    c.max_camber = 10.0
    c.min_camber = -10.0
    c.max_thickness = 1.0
    c.min_thickness = 0.0
    
    # Patch dependencies that are hard to mock fully
    with patch('obj_utils.get_le_panel_angles', return_value=(5.0, 5.0)), \
         patch('obj_utils.eval_thickness_camber_lines', return_value=(np.zeros(5), np.zeros(5))), \
         patch('obj_utils.get_geometry', return_value=(0.1, 0.3, 0.02, 0.4)), \
         patch('obj_utils.min_te_angle', return_value=5.0), \
         patch('obj_utils.max_panels_angle', return_value=2.0), \
         patch('obj_utils.add_to_stats'):
        
        has, vid, info = eval_geometry_violations(f, c)
        assert has is False
        assert vid == NO_VIOLATION

def test_eval_geometry_violations_blunt():
    f = MagicMock()
    c = MagicMock()
    # Mocking get_le_panel_angles to return a vertical singularity
    with patch('obj_utils.get_le_panel_angles', return_value=(90.0, 0.0)), \
         patch('obj_utils.add_to_stats'):
        has, vid, info = eval_geometry_violations(f, c)
        assert has is True
        assert vid == VIOL_LE_BLUNT
