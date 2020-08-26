import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"


options = {
    "build_exe": {
        # "includes": ["atexit"],
        "includes": ["PyQt5", "send2trash", "imagehash"],
        "include_files": ["./icons/", "icons_rc.py", "orange.css", "style_anime.css"],
    },
}

executables = [Executable("wfs.py", base=base, icon="./icons/waifu_sort.ico",)]

setup(
    name="WaifuFileSort",
    version="0.1.1",
    description="finalfinal",
    options=options,
    executables=executables,
)

# python setup.py build

# https://stackoverflow.com/questions/41994485/how-to-fix-could-not-find-or-load-the-qt-platform-plugin-windows-while-using-m
