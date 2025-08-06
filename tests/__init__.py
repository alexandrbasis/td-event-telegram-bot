import sys
from pathlib import Path

# Ensure src directory is on the Python path for tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
