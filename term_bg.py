#!/usr/bin/env python3
"""
Figure out if the terminal has a light or dark background

We consult environment variables
- DARK_BG
- COLORFGBG
- TERM

If DARK_BG is set and it isn't 0, then we have a dark background.
Otherwise, we have a light background.

If DARK_BG is not set but COLORFGBG is set and it is '0;15' then we have a dark background
and if it is '15;0' then a light background.

If none of the above work but TERM is set and the terminal understands
xterm sequences for retrieving foreground and background, we'll
set based on those colors. Failing that we'll set defaults
for specific TERM values based on their default settings.


See https://github.com/rocky/bash-term-background for code
that works in bash.
"""

import os
import re
import select
import sys
import termios
import time
import tty
from os import environ
from typing import Optional

# from subprocess import check_output, check_call


def get_default_bg() -> bool:
    """
    Get background from
    default values based on the TERM environment variable.
    """
    term = environ.get("TERM", None)
    if term:
        if (
            term.startswith(
                "xterm",
            )
            or term.startswith("eterm")
            or term == "dtterm"
        ):
            return False
    return True


def is_dark_rgb(r, g, b) -> bool:
    """
    Pass as parameters R G B values in hex
    On return, variable is_dark_bg is set.
    """
    # 117963 = (* .6 (+ 65535 65535 65535))
    return (16 * 5 + 16 * g + 16 * b) < 117963


def is_dark_color_fg_bg() -> Optional[bool]:
    """
    Consult (environment) variables DARK_BG and COLORFGB
    On return, variable is_dark_bg is set
    """
    dark_bg = environ.get("DARK_BG", None)
    if dark_bg is not None:
        return dark_bg != "0"
    color_fg_bg = environ.get("COLORFGBG", None)
    if color_fg_bg:
        if color_fg_bg in ("15;0", "15;default;0"):
            return True
        elif color_fg_bg in ("0;15", "0;default;15"):
            return False
    else:
        return True
    return None


def is_dark_background():
    dark_bg = is_dark_color_fg_bg()
    if dark_bg is None:
        dark_bg = get_default_bg()
    # print("XXX ", dark_bg)
    return dark_bg


# From:
# http://unix.stackexchange.com/questions/245378/common-environment-variable-to-set-dark-or-light-terminal-background/245381#245381
# and:
# https://bugzilla.gnome.org/show_bug.cgi?id=733423#c1
def xterm_compatible_fg_bg():
    fi = sys.stdin
    fo = sys.stdout
    fdi = fi.fileno()
    fdo = fo.fileno()

    if os.isatty(fdi) and os.isatty(fdo):
        fg_str = "\033]10;"
        bg_str = "\033]11;"
        query_rgb = fg_str + "?\07" + bg_str + "?\07"
        bs = "\10" * len(query_rgb)

        old_settings_in = termios.tcgetattr(fdi)
        old_settings_out = termios.tcgetattr(fdo)
        try:
            tty.setraw(fdi)
            tty.setraw(fdo)
            fo.write(query_rgb + bs + "\n")
            time.sleep(0.01)
            r, w, e = select.select([fi], [], [], 0)
            if fi in r:
                data = fi.read(48)
                termios.tcsetattr(fdi, termios.TCSADRAIN, old_settings_in)
                termios.tcsetattr(fdo, termios.TCSADRAIN, old_settings_out)
                hex_pat = "([0-9a-f]{4})"
                rgb_pat = "/".join([hex_pat] * 3) + "\07"
                fg_bg_pat = "%srgb:%s%srgb:%s" % (fg_str, rgb_pat, bg_str, rgb_pat)
                m = re.match(fg_bg_pat, data)
                if m:
                    return (
                        (m.group(1), m.group(2), m.group(3)),
                        (m.group(4), m.group(5), m.group(6)),
                    )

            else:
                # print("no input available")
                return None, None
        finally:
            termios.tcsetattr(fdi, termios.TCSADRAIN, old_settings_in)
            termios.tcsetattr(fdo, termios.TCSADRAIN, old_settings_out)
    else:
        # print("Not a tty")
        return None, None

    return None, None


if __name__ == "__main__":
    fg, bg = xterm_compatible_fg_bg()
    if fg:
        print("fg: ", fg)
        print("bg: ", bg)
    else:
        print("No foreground value received.")
