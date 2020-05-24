import sys
from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"


options = {
    "build_exe": {
        "includes": ["atexit"],
        "include_files": ["./icons/", "./delete", "icons_rc.py"],
    },
}

executables = [Executable("wfs.py", base=base, icon="./icons/waifu_sort.ico",)]

setup(
    name="WaifuFileSort",
    version="1.5",
    description="finalfinal",
    options=options,
    executables=executables,
)
