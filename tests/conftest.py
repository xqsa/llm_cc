import os
import tempfile
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TMP_ROOT = Path(r"C:\tmp") / "codex" / "pytest"
TMP_ROOT.mkdir(parents=True, exist_ok=True)
for key in ("TMPDIR", "TEMP", "TMP"):
    os.environ[key] = str(TMP_ROOT)
tempfile.tempdir = str(TMP_ROOT)
