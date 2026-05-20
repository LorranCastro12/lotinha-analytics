# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para Lotinha Analytics.

Build:  pyinstaller lotinha.spec
"""

import site
import sysconfig
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── Localiza Tcl/Tk (necessário quando Python vem do uv/pyenv) ───────────────

def _tcl_binaries() -> list[tuple[str, str]]:
    lib_dir = Path(sysconfig.get_config_var("LIBDIR") or "")
    return [
        (str(lib_dir / n), ".")
        for n in ["libtcl9.0.so", "libtcl9tk9.0.so", "libtcl8.6.so", "libtk8.6.so"]
        if (lib_dir / n).exists()
    ]


def _tcl_datas() -> list[tuple[str, str]]:
    lib_dir = Path(sysconfig.get_config_var("LIBDIR") or "")
    return [
        (str(lib_dir / n), n)
        for n in ["tcl9.0", "tk9.0", "tcl8.6", "tk8.6"]
        if (lib_dir / n).is_dir()
    ]


def _dotlibs_datas() -> list[tuple[str, str]]:
    """Inclui pastas *.libs (numpy.libs, scipy.libs, etc.) como datas.

    O runtime hook pyi_rth_libs.py adiciona essas pastas ao LD_LIBRARY_PATH
    em tempo de execução para que as extensões C consigam carregar as libs.
    """
    result = []
    for sp in site.getsitepackages():
        for libs_dir in Path(sp).glob("*.libs"):
            for so in libs_dir.glob("*.so*"):
                result.append((str(so), libs_dir.name))
    return result


# ── Coletar ───────────────────────────────────────────────────────────────────

datas: list[tuple[str, str]] = []
datas += collect_data_files("customtkinter")
datas += _tcl_datas()
datas += _dotlibs_datas()      # numpy.libs, scipy.libs, etc.

binaries: list[tuple[str, str]] = []
binaries += _tcl_binaries()

hiddenimports: list[str] = [
    "customtkinter",
    "PIL._tkinter_finder",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    "scipy.special._ufuncs",
    "scipy.linalg.blas",
    "scipy.linalg.lapack",
    "lightgbm",
]
hiddenimports += collect_submodules("sklearn")

# ── Análise ───────────────────────────────────────────────────────────────────

block_cipher = None

a = Analysis(
    ["run_gui.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["installer/hooks/pyi_rth_libs.py"],
    excludes=["pytest", "mypy", "ruff", "IPython", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="lotinha-analytics",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
