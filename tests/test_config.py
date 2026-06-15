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
import os
import json
from config_manager import InputFileParser

def test_json_parsing(tmp_path):
    d = tmp_path / "test.json"
    content = {
        "opt_opts": {
            "solver": "neuralfoil",
            "verbose": True
        },
        "op_conds": {
            "num_pts": 2,
            "op_point": [1.0, 2.0]
        }
    }
    d.write_text(json.dumps(content))
    
    parser = InputFileParser(str(d))
    assert parser.get("opt_opts", "solver") == "neuralfoil"
    assert parser.get("opt_opts", "verbose") is True
    assert parser.get_arr("op_conds", "op_point", 2) == [1.0, 2.0]

def test_legacy_nml_parsing(tmp_path):
    d = tmp_path / "test.nml"
    content = """
    &opt_opts
        solver = 'xfoil'
        verbose = .true.
    /
    &op_conds
        num_pts = 2
        op_point(1) = 1.0
        op_point(2) = 2.0
    /
    """
    d.write_text(content)
    
    parser = InputFileParser(str(d))
    assert parser.get("opt_opts", "solver") == "xfoil"
    assert parser.get("opt_opts", "verbose") is True
    assert parser.get_arr("op_conds", "op_point", 2) == [1.0, 2.0]

def test_fault_tolerant_json(tmp_path):
    d = tmp_path / "bad.json"
    # Note the trailing comma before }
    content = '{"group": {"key": "val",}}'
    d.write_text(content)
    
    parser = InputFileParser(str(d))
    assert parser.get("group", "key") == "val"
