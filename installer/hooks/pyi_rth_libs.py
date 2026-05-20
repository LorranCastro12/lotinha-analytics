"""Runtime hook: adiciona diretórios *.libs ao LD_LIBRARY_PATH antes dos imports."""

import os
import sys
from pathlib import Path

if hasattr(sys, "_MEIPASS"):
    meipass = Path(sys._MEIPASS)
    extra = [str(d) for d in meipass.glob("*.libs") if d.is_dir()]
    extra.append(str(meipass))  # libs raiz também
    if extra:
        current = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(extra + ([current] if current else []))
