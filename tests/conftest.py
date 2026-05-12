import sys
from pathlib import Path

# Make `import syntha` work without `pip install -e .`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
