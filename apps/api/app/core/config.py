import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = ROOT / "scripts"
# shortcut: scripts/ is a flat set of modules, not a package; upgrade when it becomes one.
sys.path.insert(0, str(SCRIPTS_DIR))

OOF_PATH = ROOT / "results" / "research" / "pooled_abs_full" / "oof.csv.gz"
MODEL_DIR = ROOT / "models" / "ensemble3_pooled_1D"
LIVE_DIR = ROOT / "data" / "live" / "raw" / "1D"
INDEX_PATH = ROOT / "data" / "live" / "raw" / "index" / "1D" / "VNINDEX.csv"
LOG_PATH = ROOT / "results" / "live" / "predictions_log.csv"
PAPER_DB_PATH = Path(os.environ.get("PAPER_DB_PATH", ROOT / "data" / "live" / "paper.db"))
