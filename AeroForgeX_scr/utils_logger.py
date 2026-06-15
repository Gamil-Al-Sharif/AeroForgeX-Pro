# ==============================================================================
# FILE: utils_logger.py
# PROJECT: AeroForgeX v4.0 Pro 
# DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# DEPARTMENT: Mechanical Engineering, Sana'a, Yemen
# CONTACT: mely104haja@gmail.com
# ==============================================================================
# ==============================================================================
# MIT License
# Copyright (c) 2022-2026 Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
# Based on Xoptfoil2 by Jochen Guenzel (MIT License)
# ==============================================================================
import os, sys, shutil, glob
import colorama
from colorama import Fore, Style
from tqdm import tqdm

colorama.init(autoreset=True)


# =============================================================================
# GLOBAL CONSTANTS & STATE
# =============================================================================
class Commons:
    PGM_NAME, MODE_NORMAL, MODE_AIRFOIL_OPTIMIZER, DESIGN_SUBDIR_POSTFIX = (
        "AeroForgeX v4.0 Pro",
        0,
        1,
        "_temp",
    )

    def __init__(self):
        self.run_mode, self.show_details, self.design_subdir, self.output_prefix = (
            self.MODE_NORMAL,
            False,
            None,
            None,
        )


commons = Commons()

NOT_DEF_I, NOT_DEF_D = -99999999, -99999999.0
COLOR_GOOD, COLOR_BAD, COLOR_NORMAL, COLOR_HIGH, COLOR_ERROR = 1, 2, 3, 4, 5
COLOR_WARNING, COLOR_NOTE, COLOR_FEATURE, COLOR_PALE, COLOR_FIXED, COLOR_NO = (
    6,
    7,
    8,
    9,
    10,
    16,
)
Q_GOOD, Q_OK, Q_BAD, Q_PROBLEM, Q_NEW, Q_NO = 0, 1, 2, 4, 8, 16

_myStop_out_to_console = True

_C_MAP = {
    1: Fore.LIGHTGREEN_EX,
    2: Fore.LIGHTRED_EX,
    3: Style.RESET_ALL,
    4: Style.BRIGHT,
    5: Fore.LIGHTRED_EX + Style.BRIGHT,
    6: Fore.YELLOW,
    7: Fore.LIGHTBLACK_EX,
    8: Fore.CYAN,
    9: Fore.LIGHTBLACK_EX,
    10: Fore.MAGENTA,
    16: Style.RESET_ALL,
}
_Q_MAP = {
    Q_GOOD: COLOR_GOOD,
    Q_OK: COLOR_NORMAL,
    Q_BAD: COLOR_WARNING,
    Q_NEW: COLOR_FEATURE,
    Q_PROBLEM: COLOR_BAD,
}


# =============================================================================
# FORMATTING & FILE OPS
# =============================================================================
def safe_print(t="", end="\n"):
    tqdm.write(str(t), end=end)


def to_lower(s):
    return s.lower()


def stri(i, L=None):
    return (
        str(int(i)).rjust(L)
        if L and len(str(int(i))) <= L
        else ("*" * L if L else str(int(i)))
    )


def strf(fmt, f, fix=True):
    p = fmt.lower().replace("(", "").replace(")", "").replace("sp", "+")
    try:
        s = fmt.format(f) if "{" in fmt else f"{f:{p}}"
    except:
        s = str(f)
    return s.strip() if fix else s


def make_directory(d, preserve=False):
    if not preserve and os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
    if not os.path.exists(d):
        os.makedirs(d)


def remove_directory(d):
    shutil.rmtree(d, ignore_errors=True)


def delete_file(fp):
    for f in glob.glob(fp):
        if os.path.isfile(f):
            try:
                os.remove(f)
            except Exception:
                pass


def path_join(d, f):
    return os.path.join(d, f)


def filename_stem(f):
    return os.path.splitext(os.path.basename(f))[0]


def filename_suffix(f):
    return os.path.splitext(f)[1]


# =============================================================================
# COLORED CONSOLE LOGGING
# =============================================================================
def print_colored(c, t, end=""):
    safe_print(f"{_C_MAP.get(c, Style.RESET_ALL)}{t}{Style.RESET_ALL}", end=end)


def i_quality(v, g, o, b):
    return Q_GOOD if v < g else (Q_OK if v < o else (Q_BAD if v < b else Q_PROBLEM))


def r_quality(v, g, o, b):
    return Q_GOOD if v < g else (Q_OK if v < o else (Q_BAD if v < b else Q_PROBLEM))


def print_colored_i(L, q, v):
    print_colored(_Q_MAP.get(q, COLOR_NOTE), stri(v, L) if L else str(v))


def print_colored_r(L, fmt, q, v):
    s = strf(fmt, v, False)
    s = s.rjust(L) if len(s) < L else s
    print_colored(
        _Q_MAP.get(q, COLOR_NOTE),
        (s.rstrip()[:-1] + " ")
        if s.strip().endswith(".") and len(s.strip()) > 1
        else s,
    )


def print_colored_s(q, t):
    print_colored(_Q_MAP.get(q, COLOR_NOTE), t)


def print_colored_rating(L, q):
    d = {
        Q_GOOD: ("perfect", COLOR_GOOD),
        Q_OK: ("ok", COLOR_NORMAL),
        Q_BAD: ("bad", COLOR_WARNING),
        Q_NEW: ("new", COLOR_FEATURE),
    }
    t, c = d.get(q, ("critical", COLOR_BAD))
    print_colored(c, t.ljust(L))


def set_my_stop_to_stderr(b):
    global _myStop_out_to_console
    _myStop_out_to_console = not b


def my_stop(msg):
    safe_print()
    if _myStop_out_to_console:
        print_colored(COLOR_ERROR, " Error: ")
        print_colored(COLOR_NORMAL, msg.strip())
        safe_print("\n")
    else:
        sys.stderr.write(f"Error: {msg}\n")
    sys.exit(1)


class PrintUtil:
    show_details = False

    @classmethod
    def set_show_details(cls, s):
        cls.show_details = s

    @classmethod
    def print_header(cls, t, h=None, no_crlf=False):
        if cls.show_details:
            safe_print()
        safe_print(
            f"{Fore.MAGENTA}{Style.BRIGHT}[ SYSTEM ]{Style.RESET_ALL} {t}"
            + (f" {Fore.WHITE}{Style.BRIGHT}{h}{Style.RESET_ALL}" if h else ""),
            end="" if no_crlf else "\n",
        )
        if not no_crlf and cls.show_details:
            safe_print()

    @classmethod
    def print_action(cls, t, h=None, no_crlf=False):
        if cls.show_details:
            safe_print(
                f"{Fore.CYAN}[ INFO ]{Style.RESET_ALL}   {t}"
                + (f" {Fore.WHITE}{Style.BRIGHT}{h}{Style.RESET_ALL}" if h else ""),
                end="" if no_crlf else "\n",
            )

    @classmethod
    def print_error(cls, t, i=1):
        safe_print(f"{Fore.RED}{Style.BRIGHT}[ FATAL ]{Style.RESET_ALL}  {t.strip()}\n")

    @classmethod
    def print_warning(cls, t, i=1):
        safe_print(
            f"{Fore.YELLOW}{Style.BRIGHT}[ WARN ]{Style.RESET_ALL}   {t.strip()}\n"
        )

    @classmethod
    def print_note(cls, t, i=5, no_crlf=False):
        if cls.show_details:
            safe_print(
                f"{Fore.LIGHTBLACK_EX}[ NOTE ]{Style.RESET_ALL}   {Fore.LIGHTBLACK_EX}{t}{Style.RESET_ALL}",
                end="" if no_crlf else "\n",
            )

    @classmethod
    def print_text(cls, t, i=1, no_crlf=False):
        safe_print(
            f"           {Fore.LIGHTBLACK_EX}{t}{Style.RESET_ALL}",
            end="" if no_crlf else "\n",
        )

    @classmethod
    def print_fixed(cls, t, L, r=False):
        tx = t.strip()
        safe_print(
            f"{Fore.LIGHTBLACK_EX}{tx[:L] if len(tx) >= L else (tx.rjust(L) if r else tx.ljust(L))}{Style.RESET_ALL}",
            end="",
        )

    @classmethod
    def quoted(cls, t):
        return f"'{t.strip()}'"


set_show_details, print_header, print_action = (
    PrintUtil.set_show_details,
    PrintUtil.print_header,
    PrintUtil.print_action,
)
print_error, print_warning, print_note = (
    PrintUtil.print_error,
    PrintUtil.print_warning,
    PrintUtil.print_note,
)
print_text, print_fixed, quoted = (
    PrintUtil.print_text,
    PrintUtil.print_fixed,
    PrintUtil.quoted,
)
