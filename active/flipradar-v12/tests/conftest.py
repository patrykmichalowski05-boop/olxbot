import sys
from pathlib import Path

V12_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V12_ROOT))
sys.path.insert(0, str(V12_ROOT.parents[1]))
