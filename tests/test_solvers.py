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
from solver_xfoil import OpPointSpecType, ReType, OpPointResultType
from solver_router import run_neuralfoil_analysis
from solver_neuralfoil import _apply_geometric_flap

class MockFoil:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def test_apply_geometric_flap():
    # Simple flat plate airfoil
    x = np.array([0.0, 0.5, 1.0])
    y = np.array([0.0, 0.0, 0.0])
    foil = MockFoil(x, y)
    
    class FlapSpec:
        def __init__(self):
            self.x_flap = 0.5
            self.y_flap = 0.0
            
    fsp = FlapSpec()
    # Flap 90 degrees down (sin=1, cos=0)
    # x_new = x_flap + dx*0 + dy*1 = 0.5 + 0 = 0.5
    # y_new = y_flap - dx*1 + dy*0 = 0 - 0.5 = -0.5
    new_foil = _apply_geometric_flap(foil, fsp, 90.0)
    
    np.testing.assert_allclose(new_foil.x[1:], np.array([0.5, 0.5]), atol=1e-7)
    np.testing.assert_allclose(new_foil.y[1:], np.array([0.0, -0.5]), atol=1e-7)

def test_neuralfoil_analysis_batch_alpha():
    # Mock neuralfoil module
    with patch('solver_router.neuralfoil') as mock_nf:
        mock_nf.get_aero_from_coordinates.return_value = {
            "CL": np.array([0.5, 0.6]),
            "CD": np.array([0.01, 0.012]),
            "CM": np.array([-0.1, -0.11]),
            "analysis_confidence": np.array([1.0, 1.0])
        }
        
        foil = MockFoil(np.linspace(0, 1, 50), np.zeros(50))
        xo = MagicMock()
        
        op1 = OpPointSpecType()
        op1.spec_cl = False
        op1.value = 2.0
        op1.re.number = 1e6
        
        op2 = OpPointSpecType()
        op2.spec_cl = False
        op2.value = 4.0
        op2.re.number = 1e6
        
        results = run_neuralfoil_analysis(foil, xo, [op1, op2])
        
        assert len(results) == 2
        assert results[0].converged is True
        assert results[0].cl == 0.5
        assert results[1].cl == 0.6
        assert mock_nf.get_aero_from_coordinates.called

def test_neuralfoil_analysis_cl_targeting():
    with patch('solver_router.neuralfoil') as mock_nf:
        # First two calls for secant (ag1, ag2), third for final
        mock_nf.get_aero_from_coordinates.side_effect = [
            {"CL": np.array([0.4])}, # cl1
            {"CL": np.array([0.5])}, # cl2
            {                        # final
                "CL": np.array([0.45]),
                "CD": np.array([0.01]),
                "CM": np.array([-0.1]),
                "analysis_confidence": np.array([1.0])
            }
        ]
        
        foil = MockFoil(np.linspace(0, 1, 50), np.zeros(50))
        xo = MagicMock()
        
        op = OpPointSpecType()
        op.spec_cl = True
        op.value = 0.45
        op.re.number = 1e6
        
        results = run_neuralfoil_analysis(foil, xo, [op])
        
        assert results[0].converged is True
        assert results[0].cl == 0.45
        assert mock_nf.get_aero_from_coordinates.call_count == 3
