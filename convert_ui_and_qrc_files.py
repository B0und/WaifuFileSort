import os
from pathlib import Path

# convert interface
for path in Path('').rglob('*.ui'):
    path_folder = path.parents[0]
    path_filename = path.stem
    res_path = Path(path_folder, path_filename + "_ui.py")
    os.system(f"python -m PyQt5.uic.pyuic -x {path} -o {res_path}")

# convert icons
for path in Path('').rglob('*.qrc'):
    path_folder = path.parents[0]
    path_filename = path.stem
    res_path = Path(path_folder, path_filename + "_rc.py")
    os.system(f"python -m PyQt5.pyrcc_main {path} -o {res_path}")