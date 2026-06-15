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
from obj_evaluator import _map_opt_type, _map_geo_type

def test_map_opt_type():
    assert _map_opt_type("min-sink") == 1
    assert _map_opt_type("max-glide") == 2
    assert _map_opt_type("min-drag") == 3
    assert _map_opt_type("max-lift") == 4
    assert _map_opt_type("max-xtr") == 5
    assert _map_opt_type("target-drag") == 6
    assert _map_opt_type("target-glide") == 7
    assert _map_opt_type("target-lift") == 8
    assert _map_opt_type("target-moment") == 9
    assert _map_opt_type("unknown") == 0

def test_map_geo_type():
    assert _map_geo_type("thickness") == 1
    assert _map_geo_type("camber") == 2
    assert _map_geo_type("match-foil") == 3
    assert _map_geo_type("unknown") == 0
