#!/usr/bin/env python3
import os
import sys
import platform

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyInstaller.__main__ import run as run_pyinstaller

NAME = "SpotFetch"
ENTRY_POINT = "menu.py"

OS_NAME = sys.platform
MACHINE = platform.machine().lower()

if OS_NAME == "win32":
    SUFFIX = ""
    EXT = ".exe"
elif OS_NAME == "darwin":
    SUFFIX = "_macos"
    EXT = ""
else:
    SUFFIX = "_linux"
    EXT = ""

out_name = f"{NAME}{SUFFIX}{EXT}"
dist_path = os.path.join("dist", out_name)


def main():
    opts = [
        f"--name={NAME}",
        "--noconfirm",
        "--onefile",
        "--console",
        "--add-data=README.md:.",
        *sys.argv[1:],
        ENTRY_POINT,
    ]

    print(f"Building {out_name} for {sys.platform} {MACHINE}")
    print(f"Destination: {dist_path}")
    print(f"PyInstaller args: {opts}\n")

    run_pyinstaller(opts)

    final = dist_path if os.path.exists(dist_path) else f"dist/{NAME}{EXT}"
    print(f"\nDone: {final}")


if __name__ == "__main__":
    main()
