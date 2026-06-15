# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# ==============================================================================

import warnings

import dill as pickle
from dill import PicklingWarning

warnings.filterwarnings("ignore", category=PicklingWarning)
from codeflash.tracing.replay_test import get_next_arg_and_return

from AeroForgeX_scr.utils_logger import \
    Commons as AeroForgeX_scr_utils_logger_Commons

functions = ['Commons', 'PrintUtil', 'Spline1DType', 'Spline2DType']
trace_file_path = r"C:\Users\gamee\Documents\Antigravity\AeroForgeX\tests\test_AeroForgeX_scrmath_accelerator_py_y__replay_test_1.trace"

def test_AeroForgeX_scr_utils_logger_Commons___init__():
    for arg_val_pkl in get_next_arg_and_return(trace_file=trace_file_path, function_name="__init__", file_name=r"C:\Users\gamee\Documents\Antigravity\AeroForgeX\AeroForgeX_scr\utils_logger.py", class_name="Commons", num_to_get=100):
        args = pickle.loads(arg_val_pkl)
        args.pop("__class__", None)
        ret = AeroForgeX_scr_utils_logger_Commons(**args)

