import sys
from pathlib import Path

# Ensure modules under src can be imported without the `src.` prefix
sys.path.insert(0, str(Path(__file__).resolve().parent))
